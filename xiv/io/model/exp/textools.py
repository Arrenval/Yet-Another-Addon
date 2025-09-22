import sqlite3
import subprocess

from pathlib     import Path
from bpy.types   import Object

from .scene      import get_mesh_ids
from .validators import clean_material_path


def get_mesh_props(blend_obj: list[Object]) -> tuple[dict[str, str], dict[int, str]]:
        attributes = {}
        materials  = {}

        for obj in blend_obj:
            obj_attr    = []
            group, part = get_mesh_ids(obj)

            for attr in obj.keys():
                attr: str
                if attr.startswith("atr") and obj[attr]:
                    obj_attr.append(attr.strip())
                if attr.startswith("heels_offset") and obj[attr]:
                    obj_attr.append(attr.strip())    
            attributes[obj.name] = ",".join(obj_attr)

            if part == 0:
                materials[group] = clean_material_path(obj["xiv_material"])

        return attributes, materials

def update_database(db_path: str, blend_obj: list[Object]) -> None:
    attributes, materials = get_mesh_props(blend_obj)

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

def consoletools_mdl(file_path: str, blend_obj: list[Object], textools_dir: str, export_xiv_path: str):
    textools      = Path(textools_dir)
    converter_dir = textools / "converters" / "fbx"
    fbx_path      = file_path + ".fbx"
    mdl_path      = file_path + ".mdl"
    db_path       = converter_dir / "result.db"

    subprocess.run(
        [converter_dir / "converter.exe", fbx_path], 
        check=True,
        cwd=converter_dir
    )
    
    update_database(str(db_path), blend_obj)
    
    subprocess.run(
        [
            textools / "ConsoleTools.exe",  
            "/wrap",
            db_path,  
            mdl_path, 
            export_xiv_path,
            "/mats",
            "/attributes"
        ],
        check=True,  
        cwd=textools  
        )
