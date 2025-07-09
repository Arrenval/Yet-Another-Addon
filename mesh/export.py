import re
import bpy
import sqlite3
import subprocess

from pathlib              import Path

from .handler             import MeshHandler
from ..properties         import get_window_properties
from ..preferences        import get_prefs
from ..utils.objects      import visible_meshobj
from ..utils.logging      import YetAnotherLogger
from ..utils.ya_exception import XIVMeshIDError


def check_triangulation() -> list[str]:
    visible = visible_meshobj()
    not_triangulated = []

    for obj in visible:
        tri_modifier = False
        for modifier in reversed(obj.modifiers):
            if modifier.type == "TRIANGULATE" and modifier.show_viewport:
                tri_modifier = True
                break

        if not tri_modifier:
            triangulated = True
            for poly in obj.data.polygons:
                verts = len(poly.vertices)
                if verts > 3:
                    triangulated = False
                    break

            if not triangulated:
                not_triangulated.append(obj.name)

    return not_triangulated
   
def get_export_path(directory: Path, file_name: str, subfolder: bool, body_slot:str ="") -> str:
    if subfolder:
        export_path = directory / body_slot / file_name
    else:
        export_path = directory / file_name

    return export_path

def export_result(file_path: Path, file_format: str, logger: YetAnotherLogger=None):
    export = FileExport(file_path, file_format, logger)
    export.export_template()

def get_mesh_props() -> tuple[dict[str, str], dict[int, str]]:
        
        def clean_material_name(name: str):
            if not name.startswith("/"):
                name = "/" + name
            return name.strip()
        
        visible = visible_meshobj()
        attributes = {}
        materials  = {}

        for obj in visible:
            obj_attr = []
            name_parts = obj.name.split(" ")
            try:
                if re.search(r"^\d+\.\d+\s", obj.name):
                    group = int(name_parts[0].split(".")[0])
                    part  = int(name_parts[0].split(".")[1])
                else:
                    group = int(name_parts[-1].split(".")[0])
                    part  = int(name_parts[-1].split(".")[1])
            except:
                raise XIVMeshIDError(f"{obj.name}: Couldn't parse Mesh IDs.")

            for attr in obj.keys():
                attr: str
                if attr.startswith("atr_") and obj[attr]:
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
        

class FileExport:
    def __init__(self, file_path: Path, file_format: str, logger: YetAnotherLogger=None):
        self.logger      = logger
        self.file_format = file_format
        self.file_path   = file_path
 
    def export_template(self):
        export_settings = self._get_export_settings()

        if self.file_format == 'MDL':
            visible_meshobj(mesh_id=True)
    
        try:
            mesh_handler = MeshHandler(logger=self.logger)

            mesh_handler.prepare_meshes()
            mesh_handler.process_meshes()

            if self.logger:
                self.logger.log_separator()
                self.logger.log(f"Exporting {self.file_path.stem}")
                self.logger.log_separator()
                self.logger.last_item = None

            if self.file_format == 'GLTF':
                bpy.ops.export_scene.gltf(filepath=str(self.file_path) + ".gltf", **export_settings)
            else:
                bpy.ops.export_scene.fbx(filepath=str(self.file_path) + ".fbx", **export_settings)
                if self.file_format == 'MDL':
                    if self.logger:
                        self.logger.log(f"Converting to MDL...", 2)
                    consoletools_mdl(str(self.file_path))
        
        except Exception as e:
            raise e

        finally:
            if mesh_handler:
                mesh_handler.restore_meshes()
        
    def _get_export_settings(self) -> dict[str, str | int | bool]:
        if self.file_format == 'GLTF':
            return {
                "export_format": "GLTF_SEPARATE", 
                "export_texture_dir": "GLTF Textures",
                "use_selection": False,
                "use_active_collection": False,
                "export_animations": False,
                "export_extras": True,
                "export_leaf_bone": False,
                "export_apply": True,
                "use_visible": True,
                "export_morph_normal": False,
                "export_try_sparse_sk": False,
                "export_attributes": True,
                "export_normals": True,
                "export_tangents": True,
                "export_skins": True,
                "export_influence_nb": 8,
                "export_active_vertex_color_when_no_material": True,
                "export_all_vertex_colors": True,
                "export_image_format": "NONE"
            }
        
        else:
            return {
                "use_selection": False,
                "use_active_collection": False,
                "bake_anim": False,
                "use_custom_props": True,
                "use_triangles": False,
                "add_leaf_bones": False,
                "use_mesh_modifiers": False,
                "use_visible": True,
            }

    