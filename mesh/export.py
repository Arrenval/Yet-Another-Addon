import bpy

from pathlib         import Path

from .objects        import visible_meshobj
from ..xiv.io.model  import ModelExport, MeshHandler, consoletools_mdl
from ..preferences   import get_prefs
from ..utils.logging import YetAnotherLogger


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

def export_result(file_path: Path, file_format: str, logger: YetAnotherLogger=None, batch=False):
    bpy.context.evaluated_depsgraph_get().update()
    export = FileExport(file_path, file_format, logger=logger, batch=batch)
    export.export_template()

class FileExport:
    def __init__(self, file_path: Path, file_format: str, logger: YetAnotherLogger=None, batch=False):
        self.logger      = logger
        self.file_format = file_format
        self.file_path   = file_path
        self.tt_mdl      = get_prefs().export.mdl_export == 'TT' and file_format == 'MDL'
        self.batch       = batch
 
    def export_template(self):
        export_settings = self._get_export_settings()
    
        try:
            mesh_handler = MeshHandler(logger=self.logger, batch=self.batch)

            mesh_handler.prepare_meshes()
            export_obj = mesh_handler.process_meshes()

            if self.logger:
                self.logger.log_separator()
                self.logger.log(f"Exporting {self.file_path.stem}")
                self.logger.log_separator()
                self.logger.last_item = None

            if self.file_format == 'GLTF':
                bpy.ops.export_scene.gltf(filepath=str(self.file_path) + ".gltf", **export_settings)
            elif self.file_format == 'FBX' or self.tt_mdl:
                bpy.ops.export_scene.fbx(filepath=str(self.file_path) + ".fbx", **export_settings)
                if self.file_format == 'MDL':
                    if self.logger:
                        self.logger.log(f"Converting to MDL...", 2)
                    consoletools_mdl(str(self.file_path))
            else:
                ModelExport.export_scene(export_obj, str(self.file_path) + ".mdl")
        
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
        
        elif self.file_format == 'FBX' or self.tt_mdl:
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

    