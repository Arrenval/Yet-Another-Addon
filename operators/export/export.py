import bpy
import time
import json

from pathlib                  import Path
from itertools                import combinations
from bpy.props                import StringProperty
from bpy.types                import Operator, Object, Context, ShapeKey, LayerCollection
    
from .mesh_handler            import MeshHandler
from ...properties            import get_file_properties, get_devkit_properties, get_window_properties
from ...preferences           import get_prefs
from ...utils.objects         import visible_meshobj, get_object_from_mesh, safe_object_delete
from ...utils.logging         import YetAnotherLogger
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
   
def save_sizes() -> dict[str, dict[str, float]]:
        devkit_props = get_devkit_properties()
        obj          = get_object_from_mesh("Torso").data.shape_keys.key_blocks
        saved_sizes  = [{"Large":  {}, "Medium": {}, "Small":  {}, "Masc": {}} for i in range(2)]
       
        if obj["Lavabod"].mute:
            index  = 0
            saved_sizes[1] = devkit_props.torso_floats[1]
            saved_sizes[1].setdefault("Masc", {})
        else:
            index  = 1
            saved_sizes[0] = devkit_props.torso_floats[0]
            saved_sizes[0].setdefault("Masc", {})

        for key in obj:
            if key.name.startswith("- "):
                name = key.name[2:]
                saved_sizes[index]["Large"][name] = round(key.value, 2)
            if key.name.startswith("-- "):
                name = key.name[3:]
                saved_sizes[index]["Medium"][name] = round(key.value, 2)
            if key.name.startswith("--- "):
                name = name = key.name[4:]
                saved_sizes[index]["Small"][name] = round(key.value, 2)
            if key.name.startswith("---- "):
                name = name = key.name[4:]
                saved_sizes[0]["Masc"][name] = round(key.value, 2)
                saved_sizes[1]["Masc"][name] = round(key.value, 2)
        
        return saved_sizes

def reset_chest_values(saved_sizes) -> None:
    devkit       = bpy.context.scene.ya_devkit
    devkit_props = get_devkit_properties()
    obj          = get_object_from_mesh("Torso").data.shape_keys.key_blocks
    base_size    = ["Large", "Medium", "Small", "Masc"]

    if obj["Lavabod"].mute:
            index  = 0
            saved_sizes[1] = devkit_props.torso_floats[1]
    else:
        index  = 1
        saved_sizes[0] = devkit_props.torso_floats[0]

    for size in base_size:
        preset      = saved_sizes[index][size]
        if size == "Masc":
            size = "Flat"
        category    = devkit_props.ALL_SHAPES[size][2]
        devkit.ApplyShapes.apply_shape_values("torso", category, preset)
    
    bpy.context.view_layer.objects.active = get_object_from_mesh("Torso")
    bpy.context.view_layer.update()

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
        self.file_format = format
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
        if self.file_format:
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

    def invoke(self, context, event):
        self.props       = get_file_properties()
        self.window      = get_window_properties()
        self.check_tris  = self.props.check_tris
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

class BatchQueue(Operator):
    # Currently very messy, will refactor later

    bl_idname = "ya.batch_queue"
    bl_label = "Export"
    bl_description = "Exports your scene based on your selections"
    bl_options = {'UNDO'}

    ob_mesh_dict = {
            "Chest": "Torso", 
            "Legs" : "Waist", 
            "Hands": "Hands",
            "Feet" : "Feet"
            }
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        self.props            = get_file_properties()
        self.window           = get_window_properties()
        self.prefs            = get_prefs()
        self.devkit_props     = get_devkit_properties()
        self.check_tris:bool  = self.props.check_tris
        self.force_yas:bool   = self.props.force_yas
        self.subfolder:bool   = self.props.create_subfolder
        self.export_dir       = Path(self.prefs.export_dir)
        self.file_format      = self.window.file_format
        self.body_slot:str    = self.window.export_body_slot
        self.size_options     = self.get_size_options()

        self.leg_sizes = {
            "Melon": self.size_options["Melon"],
            "Skull": self.size_options["Skull"], 
            "Yanilla": self.size_options["Yanilla"], 
            "Mini Legs": self.size_options["Mini Legs"]
            }

        self.queue = []
        self.leg_queue = []

        if self.check_tris:
            not_triangulated= check_triangulation()
            if not_triangulated:
                self.report({'ERROR'}, f"Not Triangulated: {', '.join(not_triangulated)}")
                return {'CANCELLED'} 
        
        if not self.export_dir.is_dir():
            self.report({'ERROR'}, "No directory selected for export!")
            return {'CANCELLED'} 
        
        if self.subfolder:
            Path.mkdir(self.export_dir / self.body_slot, exist_ok=True)
        
        if self.body_slot == "Chest & Legs":
            self.actual_combinations = self.shape_combinations("Chest")
            self.calculate_queue("Chest")
            self.actual_combinations = self.shape_combinations("Legs")
            self.calculate_queue("Legs")
        else:
            self.actual_combinations = self.shape_combinations(self.body_slot)
            self.calculate_queue(self.body_slot)

        if self.queue == []:
            self.report({'ERROR'}, "No valid combinations!")
            return {'CANCELLED'} 
        
        if self.body_slot == "Chest & Legs" and self.leg_queue == []:
            self.report({'ERROR'}, "No valid combinations!")
            return {'CANCELLED'} 

        self.collection_state()
        bpy.ops.yakit.collection_manager(preset="Export")
        self.saved_sizes = save_sizes()

        with SceneOptimiser(context, optimisation_level="high"):
            self.logger = YetAnotherLogger(total=len(self.queue), output_dir=self.export_dir, start_time=time.time())
            self.logger.start_terminal()
            try:
                for item in self.queue:
                    self.logger.log_progress(operation="Exporting files")
                    self.logger.log_separator()
                    self.logger.log(f"Size: {item[0]}")
                    self.logger.log_separator()
                    self.logger.log("Applying sizes...", 2)
                    self.export_queue(context, item, self.body_slot)
                    
            except Exception as e:
                self.logger.close(e)
                self.report({"ERROR"}, f"Export has run into an error. A log has been saved in your export directory.")
            finally:
                if self.logger:
                    self.logger.close()

        reset_chest_values(self.saved_sizes)
        bpy.ops.yakit.collection_manager(preset="Restore")

        return {'FINISHED'}

    def collection_state(self) -> None:
        devkit_props = get_devkit_properties()
        collection_state = devkit_props.collection_state
        collection_state.clear()
        collections = []
        match self.body_slot:
            case "Chest":
                collections = ["Chest"]
                if self.size_options["Piercings"]:
                    collections.append("Nipple Piercings")

            case "Legs":
                collections = ["Legs"]
                if self.size_options["Pubes"]:
                    collections.append("Pubes")

            case "Chest & Legs":
                collections = ["Chest", "Legs"]
                if self.size_options["Piercings"]:
                    collections.append("Nipple Piercings")
                if self.size_options["Pubes"]:
                    collections.append("Pubes")

            case "Hands":
                collections = ["Hands"]

            case "Feet":
                collections = ["Feet"]

        for name in collections:
            state = collection_state.add()
            state.name = name

    def get_size_options(self) -> dict[str, bool]:
        options = {}
        devkit = get_devkit_properties()
        
        for shape, (name, slot, shape_category, description, body, key) in devkit.ALL_SHAPES.items():
            slot_lower = slot.lower().replace("/", " ")
            name_lower = name.lower().replace(" ", "_")

            prop_name = f"export_{name_lower}_{slot_lower}_bool"

            if hasattr(devkit, prop_name):
                options[shape] = getattr(devkit, prop_name)

        return options

    def calculate_queue(self, body_slot:str) -> None:

        def get_body_key(body:str, body_slot:str) -> str:
            if body == "Masc" and body_slot == "Chest":
                body = "Flat"
            if body_slot == "Chest":
                body_key = body
            else:
                body_key = f"{body} {body_slot}"

            return body_key
        
        def exception_handling(size:str, gen:str, gen_options:int) -> None:
            if body_key == "Lava" and size not in lava_sizes:
                return 
            if body_key != "Lava" and size == "Sugar":
                return 
            if body_key != "Flat" and size in masc_sizes:
                return
            if body_key == "Flat" and size not in masc_sizes:
                return 
            for options in options_groups:
                if (size == "Mini Legs" or body == "Lava") and any("Hip Dips" in option for option in options):
                    continue
                if body == "YAB" and any("Rue" in option for option in options):
                    continue
                if body_slot == "Chest" and body == "Rue" and "Rue" not in options:
                    continue
                if body_slot =="Legs" and body == "Rue" and "Rue Legs" not in options:
                    continue
                if body == "Lava" or body_key == "Masc Legs":
                    options = (*options, body_key)

                name = self.name_generator(options, size, body, len(enabled_bodies), gen, gen_options, body_slot)
                if (body_slot == "Feet" or body_slot == "Hands") and any(name in entry[0] for entry in self.queue):
                    continue
            
                if self.body_slot == "Chest & Legs" and body_slot == "Legs":
                    self.leg_queue.append((name, options, size, gen, target))
                else:
                    self.queue.append((name, options, size, gen, target))
                
        devkit          = get_devkit_properties()
        mesh            = self.ob_mesh_dict[body_slot]
        rue_export      = get_file_properties().rue_export
        target          = get_object_from_mesh(mesh).data.shape_keys.key_blocks
        leg_sizes       = [key for key in self.leg_sizes.keys() if self.leg_sizes[key]]
        gen_options     = len(self.actual_combinations.keys())
        all_bodies      = ["YAB", "Rue", "Lava", "Masc"]
        lava_sizes      = ["Large", "Medium", "Small", "Sugar"]
        masc_sizes      = ["Flat", "Pecs"]
        enabled_bodies  = []

        for shape, (name, slot, category, description, body, key) in devkit.ALL_SHAPES.items():
            if body and slot == body_slot and self.size_options[shape]:
                enabled_bodies.append(shape)
    
        for body in all_bodies:
            body_key = get_body_key(body, body_slot)
            if body_key not in self.size_options:
                continue
            if self.size_options[body_key] == False:
                continue
            if not rue_export and body == "Rue":
                continue
            if body_slot != "Legs":
                for size, options_groups in self.actual_combinations.items():
                    exception_handling(size, "", 0)
            else:
                for size in leg_sizes:
                    if (body == "Lava" or body == "Masc") and (size == "Skull" or size == "Mini Legs" or size == "Yanilla"):
                        continue
                    for gen, options_groups in self.actual_combinations.items(): 
                        exception_handling(size, gen, gen_options)
                      
    def shape_combinations(self, body_slot:str) -> dict[str, set[tuple]]:
        devkit              = get_devkit_properties()
        possible_parts      = [ 
            "Small Butt", "Soft Butt", "Hip Dips", "Rue Legs",
            "Buff", "Rue",
            "Clawsies"
            ]
        actual_parts        = []
        all_combinations    = set()
        actual_combinations = {}

        #Excludes possible parts based on which body slot they belong to
        for shape, (name, slot, category, description, body, key) in devkit.ALL_SHAPES.items():
            if any(shape in possible_parts for parts in possible_parts) and body_slot == slot and self.size_options[shape]:
                actual_parts.append(shape)  

        for r in range(0, len(actual_parts) + 1):
            all_combinations.update(combinations(actual_parts, r))

        for shape, (name, slot, category, description, body, key) in devkit.ALL_SHAPES.items():
            if body_slot == "Legs":
                if self.size_options[shape] and category == "Vagina":
                    actual_combinations[shape] = all_combinations

            elif body_slot == "Chest" and slot == "Chest":
                if self.size_options[shape] and category != "":
                    actual_combinations[shape] = all_combinations

            elif body_slot == "Hands":
                if self.size_options[shape] and category == "Nails":
                    actual_combinations[shape] = all_combinations

            elif body_slot == "Feet":
                if self.size_options[shape] and category == "Feet":
                    actual_combinations[shape] = all_combinations

        return actual_combinations
                       
    def name_generator(self, options:tuple[str, ...], size:str, body:str, bodies:int, gen:str, gen_options:int, body_slot:str) -> str:
        devkit      = get_devkit_properties()
        yiggle      = get_file_properties().force_yas
        body_names  = get_file_properties().body_names
        gen_name    = None

        if body_names or (bodies > 1 and "YAB" != body and body_slot != "Feet"):
            file_names = [body]
        elif bodies == 1 and body_slot == "Legs" and (body == "Lava" or body == "Masc"):
            file_names = [body]
        else:
            file_names = []

        #Loops over the options and applies the shapes name to file_names
        for shape, (name, slot, category, description, body_bool, key) in devkit.ALL_SHAPES.items():
            if any(shape in options for option in options) and not shape.startswith("Gen"):
                if body_bool == True and not("Rue" not in body and "Rue" == name):
                    continue
                if name in file_names:
                    continue
                if name == "Hip Dips":
                    name = "Alt Hip"
                if name.endswith("Butt"):
                    name = name[:-len(" Butt")]
                file_names.append(name)
        
        # Checks if any Genitalia shapes and applies the shortened name 
        # Ignores gen_name if only one option is selected
        if gen != None and gen.startswith("Gen") and gen_options > 1:
            gen_name = gen.replace("Gen ","")       
        
        # Tweaks name output for the sizes
        size_name = size.replace(" Legs", "").replace("YAB ", "")
        if size == "Skull":
            size_name = "Skull Crushers"
        if size == "Melon":
            size_name = "Watermelon Crushers"
        if size == "Short" or size == "Long":
            size_name = size + " Nails"

        if body == "Lava":
            if size_name == "Large":
                size_name = "Omoi"
            if size_name == "Medium":
                size_name = "Teardrop"
            if size_name == "Small":
                size_name = "Cupcake"

        if not (body_slot == "Legs" and (body == "Lava" or body == "Masc")):
            file_names.append(size_name)

        if body_slot == "Feet":
            file_names = reversed(file_names)

        if gen_name != None:
            file_names.append(gen_name)

        if yiggle:
            return "Yiggle - " + " - ".join(list(file_names))
        
        return " - ".join(list(file_names))
        
    def export_queue(self, context:Context, item: tuple, body_slot:str) -> int | None:

        def clean_file_name (file_name: str) -> str:
            parts = file_name.split(" - ")
            rue_match = False
            new_parts = []

            for part in parts:
                if part == "Rue":
                    if rue_match:
                        continue
                    rue_match = True
                new_parts.append(part)
                
            
            file_name = " - ".join(new_parts)

            return file_name
        
        def check_rue_match (options, file_name) -> bool:
            '''This function checks the name of the leg export vs the chest export and makes sure only 
            rue tops and bottoms are combined'''
            if "Rue" in file_name:
                if any("Rue Legs" in option for option in options):
                    return True
                else:
                    return False
            elif any("Rue Legs" in option for option in options):
                return False
        
            return True

        def apply_model_state(options: tuple[str], size:str , gen: str, body_slot: str, obj, saved_sizes: dict[str, dict[str, float]]) -> None:
            Devkit = bpy.context.scene.ya_devkit
            devkit_props = get_devkit_properties()
            if body_slot == "Chest & Legs":
                body_slot = "Chest"

            for shape, (name, slot, category, description, body, key) in devkit_props.ALL_SHAPES.items():
                if shape == size and key != "":
                    obj[key].mute = False

                if any(shape in options for option in options):
                    if key != "":
                        obj[key].mute = False

            # Adds the shape value presets alongside size toggles
            if body_slot == "Chest":
                keys_to_filter  = ["Nip Nops"]
                preset          = {}
                filtered_preset = {}
                index           = 1 if any(option == "Lava" for option in options) else 0

                try:
                    preset = saved_sizes[index][size]
                except:
                    preset = Devkit.get_shape_presets(size)
                
                for key in preset.keys():
                    if not any(key.endswith(sub) for sub in keys_to_filter):
                        filtered_preset[key] = preset[key]

                category = devkit_props.ALL_SHAPES[size][2]
                Devkit.ApplyShapes.mute_chest_shapes(obj, category)
                Devkit.ApplyShapes.apply_shape_values("torso", category, filtered_preset)
                bpy.context.view_layer.objects.active = get_object_from_mesh("Torso")
                bpy.context.view_layer.update()
                    
            if gen != None and gen.startswith("Gen") and gen != "Gen A":
                obj[gen].mute = False

        def reset_model_state(body_slot: str, key_block) -> None:
            devkit = get_devkit_properties()
            if body_slot == "Chest & Legs":
                body_slot = "Chest"

            reset_shape_keys = []

            for shape, (name, slot, shape_category, description, body, key) in devkit.ALL_SHAPES.items():
                if key != "" and slot == body_slot:
                    if shape == "Hip Dips":
                        reset_shape_keys.append("Hip Dips (for YAB)")
                        reset_shape_keys.append("Less Hip Dips (for Rue)")
                    else:
                        reset_shape_keys.append(key)

            for key in reset_shape_keys:   
                key_block[key].mute = True

        collection   = context.view_layer.layer_collection.children
    
        main_name, options, size, gen, target = item

        reset_model_state(body_slot, target)
        apply_model_state(options, size, gen, body_slot, target, self.saved_sizes)

        if body_slot == "Hands":

            if size == "Straight" or size == "Curved":
                collection["Hands"].children["Clawsies"].exclude = False
                collection["Hands"].children["Nails"].exclude = True
                collection["Hands"].children["Nails"].exclude = True
    
            else:
                collection["Hands"].children["Clawsies"].exclude = True
                collection["Hands"].children["Nails"].exclude = False
                collection["Hands"].children["Nails"].children["Practical Uses"].exclude = False
        
        if body_slot == "Feet":

            if "Clawsies" in options:
                collection["Feet"].children["Toe Clawsies"].exclude = False
                collection["Feet"].children["Toenails"].exclude = True
                
            else:
                collection["Feet"].children["Toe Clawsies"].exclude = True
                collection["Feet"].children["Toenails"].exclude = False
        
        if body_slot == "Chest & Legs":
            exported = []
            for leg_task in self.leg_queue:
                leg_name, options, size, gen, leg_target = leg_task
                # rue_match stops non-rue tops to be used with rue legs and vice versa
                if check_rue_match(options, main_name):
                    reset_model_state("Legs", leg_target)
                    apply_model_state(options, size, gen, "Legs", leg_target, self.saved_sizes)

                    combined_name = main_name + " - " + leg_name
                    final_name = clean_file_name(combined_name)
                    if not any(final_name in name for name in exported):
                        exported.append(final_name)
                        file_path = get_export_path(self.export_dir, final_name, self.subfolder, self.body_slot)
                        export_result(file_path, self.file_format, self.logger)
        
        else:
            file_path = get_export_path(self.export_dir, main_name, self.subfolder, self.body_slot)
            export_result(file_path, self.file_format, self.logger)
      

CLASSES = [
    SimpleExport,
    BatchQueue
]
