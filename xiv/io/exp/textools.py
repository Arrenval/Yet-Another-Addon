import sqlite3
import subprocess

from pathlib           import Path

from ....props        import get_window_properties
from ..com.scene      import get_mesh_ids
from ....preferences  import get_prefs
from ....mesh.objects import visible_meshobj


def get_mesh_props() -> tuple[dict[str, str], dict[int, str]]:
        
        def clean_material_name(name: str):
            if not name.startswith("/"):
                name = "/" + name
            if not name.endswith(".mtrl"):
                name = name + ".mtrl"
            return name.strip()
        
        visible = visible_meshobj()
        attributes = {}
        materials  = {}

        for obj in visible:
            obj_attr = []
            group, part = get_mesh_ids(obj)

            for attr in obj.keys():
                attr: str
                if attr.startswith("atr") and obj[attr]:
                    obj_attr.append(attr.strip())
                if attr.startswith("heels_offset") and obj[attr]:
                    obj_attr.append(attr.strip())    
            attributes[obj.name] = ",".join(obj_attr)

            if part == 0:
                materials[group] = clean_material_name(obj.material_slots[0].name)

        return attributes, materials

def update_database(db_path: str) -> None:
    attributes, materials = get_mesh_props()

    try:
        conn   = sqlite3.connect(db_path)
        cursor = conn.cursor() 

        for mesh_name, attr in attributes.items():
            if attr == "":
                continue
            cursor.execute(f"UPDATE parts SET attributes = '{attr}' WHERE name = '{mesh_name}'")

        for mesh_id, material in materials.items():
            cursor.execute(f"INSERT INTO materials (material_id, name) VALUES ({mesh_id}, '{material}')")
            cursor.execute(f"UPDATE meshes SET material_id = {mesh_id} WHERE mesh = {mesh_id}")
    
        conn.commit()

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

def consoletools_mdl(file_path: str):
    textools      = Path(get_prefs().textools_directory)
    converter_dir = textools / "converters" / "fbx"
    fbx_path      = file_path + ".fbx"
    mdl_path      = file_path + ".mdl"
    db_path       = converter_dir / "result.db"

    subprocess.run(
        [converter_dir / "converter.exe", fbx_path], 
        check=True,
        cwd=converter_dir
    )
    
    update_database(str(db_path))
    
    subprocess.run(
        [
            textools / "ConsoleTools.exe",  
            "/wrap",
            db_path,  
            mdl_path, 
            get_window_properties().export_xiv_path.strip(),
            "/mats",
            "/attributes"
        ],
        check=True,  
        cwd=textools  
        )
