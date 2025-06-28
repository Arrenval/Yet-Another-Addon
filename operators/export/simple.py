import bpy
import time
import json

from pathlib                  import Path
from itertools                import combinations
from bpy.props                import StringProperty
from bpy.types                import Operator, Object, Context, ShapeKey, LayerCollection
    
from ...properties            import get_file_properties, get_devkit_properties, get_window_properties, get_devkit_win_props
from ...preferences           import get_prefs
from ...utils.objects         import visible_meshobj, get_object_from_mesh, safe_object_delete
from ...utils.logging         import YetAnotherLogger
from ...utils.mesh_handler    import MeshHandler
from ...utils.scene_optimiser import SceneOptimiser


def add_driver(shape_key:ShapeKey, source:Object) -> None:
            shape_key.driver_remove("value")
            shape_key.driver_remove("mute")
            value = shape_key.driver_add("value").driver
            mute = shape_key.driver_add("mute").driver
            
            value.type = "AVERAGE"
            value_var = value.variables.new()
            value_var.name = "key_value"
            value_var.type = "SINGLE_PROP"

            value_var.targets[0].id_type = "KEY"
            value_var.targets[0].id = source.data.shape_keys
            value_var.targets[0].data_path = f'key_blocks["{shape_key.name}"].value'

            mute.type = "AVERAGE"
            mute_var = mute.variables.new()
            mute_var.name = "key_mute"
            mute_var.type = "SINGLE_PROP"
            
            mute_var.targets[0].id_type = "KEY"
            mute_var.targets[0].id = source.data.shape_keys
            mute_var.targets[0].data_path = f'key_blocks["{shape_key.name}"].mute'

def check_triangulation() -> list[str]:
    visible = visible_meshobj()
    not_triangulated = []

    for obj in visible:
        tri_modifier = False
        for modifier in reversed(obj.modifiers):
            if modifier.type == "TRIANGULATE" and modifier.show_viewport:
                tri_modifier = True
                break
        if "xiv_transparency" in obj and obj["xiv_transparency"]:
            tri_modifier = True
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
   
def get_export_path(directory: Path, file_name: str, subfolder: bool, body_slot:str ="") -> Path:
    if subfolder:
        export_path = directory / body_slot / file_name
    else:
        export_path = directory / file_name

    return export_path

def export_result(file_path: Path, file_format: str, logger: YetAnotherLogger=None):
    export = FileExport(file_path, file_format, logger)
    export.export_template()

class FileExport:
    def __init__(self, file_path: Path, file_format: str, logger: YetAnotherLogger=None):
        self.props       = get_file_properties()
        self.prefs       = get_prefs()
        self.logger      = logger
        self.file_format = file_format
        self.file_path   = file_path
        self.selected_directory = Path(self.prefs.export_dir)
 
    def export_template(self):
        export_settings = self.get_export_settings()
    
        try:
            mesh_handler = MeshHandler(logger=self.logger)

            mesh_handler.prepare_meshes()
            mesh_handler.process_meshes()

            if self.logger:
                self.logger.log_separator()
                self.logger.log(f"Exporting {self.file_path.stem}")
                self.logger.log_separator()

            if self.file_format == "GLTF":
                bpy.ops.export_scene.gltf(filepath=str(self.file_path) + ".gltf", **export_settings)
            elif self.file_format == "FBX":
                bpy.ops.export_scene.fbx(filepath=str(self.file_path) + ".fbx", **export_settings)
        
        except Exception as e:
            if self.logger:
                self.logger.close(e)
            else:
                print(f"ERROR in export: {e}")
            try:
                if mesh_handler:
                    for obj in mesh_handler.delete:
                        safe_object_delete(obj)
                    
                    for obj in mesh_handler.reset:
                        try:
                            obj.hide_set(False)
                        except:
                            pass
                        
            except Exception as cleanup_error:
                print(f"Emergency cleanup error: {cleanup_error}")

            raise e
        finally:
            if mesh_handler:
                try:
                    mesh_handler.restore_meshes()
                except Exception as e:
                    if self.logger:
                        self.logger.close(e)
                    else:
                        print(f"Restore error: {e}")
            else:
                if self.logger:
                    self.logger.close()
        
    def get_export_settings(self) -> dict[str, str | int | bool]:
        if self.file_format == "GLTF":
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
        
        if self.file_format == "FBX":
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

    def write_mesh_props(self, export_path:Path):
        prop_json = export_path.parent / "MeshProperties.json"
        visible = visible_meshobj()
        attributes = {}
        materials  = {}

        if prop_json.is_file():
            with open(prop_json, "r") as file:
                props = json.load(file)
        else:
            props = {}

        for obj in visible:
            obj_attr = []
            name_parts = obj.name.split(" ")
            group = int(name_parts[-1].split(".")[0])
            part  = int(name_parts[-1].split(".")[1])
            for attr in obj.keys():
                attr:str
                if attr.startswith("atr_") and obj[attr]:
                    obj_attr.append(attr)
            attributes[obj.name] = ",".join(obj_attr)

            if part == 0:
                materials[group] = obj.material_slots[0].name

        if export_path.stem in props:
            del props[export_path.stem]
        props.setdefault(export_path.stem, {})
        props[export_path.stem]["attributes"] = attributes 
        props[export_path.stem]["materials"]  = materials

        with open(prop_json, "w") as file:
                file.write(json.dumps(props, indent=4))

class SimpleExport(Operator):
    bl_idname = "ya.simple_export"
    bl_label = "Simple Export"
    bl_description = "Exports single model based on visible objects"
    bl_options = {"UNDO", "REGISTER"}

    user_input: StringProperty(name="File Name", default="") # type: ignore
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def invoke(self, context: Context, event):
        self.props       = get_file_properties()
        self.window      = get_window_properties()
        self.check_tris  = self.window.check_tris
        self.directory   = Path(get_prefs().export_dir)
        self.file_format = self.window.file_format

        if not self.directory.is_dir():
            self.report({'ERROR'}, "No export directory selected.")
            return {'CANCELLED'}
        
        if self.check_tris:
            not_triangulated = check_triangulation()
            if not_triangulated:
                self.report({'ERROR'}, f"Not Triangulated: {', '.join(not_triangulated)}")
                return {'CANCELLED'} 
            
        bpy.context.window_manager.invoke_props_dialog(self, confirm_text="Export")
        return {'RUNNING_MODAL'}

    def execute(self, context):
        devkit = get_devkit_properties()

        if devkit:
            collection_state = devkit.collection_state
            self.save_current_state(context, collection_state)
            bpy.ops.yakit.collection_manager(preset="Export")
        
        export_result(self.directory / self.user_input, self.file_format)
   
        if devkit:
            bpy.ops.yakit.collection_manager(preset="Restore")

        return {'FINISHED'}

    def save_current_state(self, context:Context, collection_state):

        def save_current_state_recursive(layer_collection:LayerCollection):
            if not layer_collection.exclude:
                    state = collection_state.add()
                    state.name = layer_collection.name
            for child in layer_collection.children:
                save_current_state_recursive(child)

        collection_state.clear()
        for layer_collection in context.view_layer.layer_collection.children:
            save_current_state_recursive(layer_collection)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "user_input")     


CLASSES = [
    SimpleExport,
]
