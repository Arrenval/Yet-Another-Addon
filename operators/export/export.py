import bpy
import time
import json
import random

from pathlib          import Path
from functools        import partial
from itertools        import combinations
from bpy.props        import StringProperty
from bpy.types        import Operator, Object, Context, ShapeKey, LayerCollection

from .mesh_handler    import MeshHandler
from ...properties    import get_file_properties, get_devkit_properties, get_window_properties, get_outfit_properties
from ...preferences   import get_prefs
from ...utils.objects import visible_meshobj, get_object_from_mesh


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
   
def armature_visibility(export=False) -> None:
    # Makes sure armatures are enabled in scene's space data
    # Will not affect armatures that are specifically hidden
    context = bpy.context
    outfit = get_outfit_properties()
    if export:
        outfit.animation_optimise.clear()
        optimise = outfit.animation_optimise.add()
        optimise.show_armature = context.space_data.show_object_viewport_armature
        context.space_data.show_object_viewport_armature = True
    else:
        try:
            area = [area for area in context.screen.areas if area.type == 'VIEW_3D'][0]
            view3d = [space for space in area.spaces if space.type == 'VIEW_3D'][0]

            with context.temp_override(area=area, space=view3d):
                context.space_data.show_object_viewport_armature = optimise[0].show_armature
        except:
            pass

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

class FileExport:

    def __init__(self):
        self.props = get_file_properties()
        self.prefs = get_prefs()
        self.gltf = self.props.file_gltf
        self.subfolder = self.props.create_subfolder
        self.selected_directory = Path(self.prefs.export_dir)

    def export_template(self, file_name:str, body_slot:str):
        if self.subfolder:
            export_path = self.selected_directory / body_slot / file_name
        else:
            export_path = self.selected_directory / file_name
        export_settings = self.get_export_settings()

        # self.write_mesh_props(export_path)
        
        if self.gltf:
            bpy.ops.export_scene.gltf(filepath=str(export_path) + ".gltf", **export_settings)
        else:
            bpy.ops.export_scene.fbx(filepath=str(export_path) + ".fbx", **export_settings)
        
    def get_export_settings(self) -> dict[str, str | int | bool]:
        if self.gltf:
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
                "use_mesh_modifiers": True,
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
        self.props              = get_file_properties()
        self.check_tris         = self.props.check_tris
        self.force_yas          = self.props.force_yas
        self.directory          = Path(get_prefs().export_dir)

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
        mesh_handler = MeshHandler()
        armature_visibility(export=True)

        if devkit:
            collection_state = devkit.collection_state
            self.save_current_state(context, collection_state)
            bpy.ops.yakit.collection_manager(preset="Export")

        mesh_handler.prepare_meshes()
        try:
            mesh_handler.process_meshes()
        except Exception as e:
            mesh_handler.restore_meshes()
            self.report({"ERROR"}, f"Mesh handler failed: {e}")
            return {"CANCELLED"}
        
        FileExport().export_template(self.user_input, "")
        mesh_handler.restore_meshes()

        if hasattr(context.scene, "devkit_props"):
            bpy.ops.yakit.collection_manager(preset="Restore")

        armature_visibility()
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
        bpy.context.scene.update_tag()
        bpy.context.view_layer.update()

        props                        = get_file_properties()
        window                       = get_window_properties()
        prefs                        = get_prefs()
        self.check_tris:bool         = props.check_tris
        self.force_yas:bool          = props.force_yas
        self.subfolder:bool          = props.create_subfolder
        self.export_directory        = Path(prefs.export_dir)
        self.body_slot:str           = window.export_body_slot
        self.size_options            = self.get_size_options()

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
        
        if not Path.is_dir(self.export_directory):
            self.report({'ERROR'}, "No directory selected for export!")
            return {'CANCELLED'} 
        
        if self.subfolder:
            Path.mkdir(self.export_directory / self.body_slot, exist_ok=True)
        
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

        props.export_total = len(self.queue)
        armature_visibility(export=True)
        self.process_queue(context)
        return {'FINISHED'}
    
    # The following functions is executed to establish the queue and valid options 
    # before handing all variables over to queue processing

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
     
    # These functions are responsible for processing the queue.
    # Export queue is running on a timer interval until the queue is empty.

    def process_queue(self, context:Context) -> None:
        start_time = time.time()
        devkit_props = get_devkit_properties()
        setattr(devkit_props, "is_exporting", False)

        # randomising the list gives a much better time estimate
        random.shuffle(self.queue)
        BatchQueue.progress_tracker(self.queue)
        saved_sizes = save_sizes()

        callback = partial(BatchQueue.export_queue, context, self.queue, self.leg_queue, self.body_slot, saved_sizes, start_time)
        bpy.app.timers.register(callback, first_interval=0.5) 
        
    def export_queue(context:Context, queue:list, leg_queue:list, body_slot:str, saved_sizes, start_time: float) -> int | None:

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

        def queue_exit() -> None:
            if body_slot == "Chest" or body_slot == "Chest & Legs":
                reset_chest_values(saved_sizes)
            
            bpy.ops.yakit.collection_manager(preset="Restore")
            BatchQueue.progress_reset(props)
            armature_visibility()

        props        = get_file_properties()
        devkit_props = get_devkit_properties()
        collection   = context.view_layer.layer_collection.children
        
        if getattr(devkit_props, "is_exporting"):
            return 0.3
        setattr(devkit_props, "is_exporting", True)
        
        mesh_handler = MeshHandler()
        main_name, options, size, gen, target = queue.pop()

        reset_model_state(body_slot, target)
        apply_model_state(options, size, gen, body_slot, target, saved_sizes)
        props.export_file_name = main_name

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
            for leg_task in leg_queue:
                leg_name, options, size, gen, leg_target = leg_task
                # rue_match stops non-rue tops to be used with rue legs and vice versa
                if check_rue_match(options, main_name):
                    reset_model_state("Legs", leg_target)
                    apply_model_state(options, size, gen, "Legs", leg_target, saved_sizes)

                    combined_name = main_name + " - " + leg_name
                    final_name = clean_file_name(combined_name)
                    if not any(final_name in name for name in exported):
                        exported.append(final_name)
                        mesh_handler.prepare_meshes()
                        try:
                            mesh_handler.process_meshes()
                        except Exception as e:
                            mesh_handler.restore_meshes()
                            queue_exit()
                            BatchQueue.ErrorMessage(message="MeshHandler has failed.")
                            raise e
                        FileExport().export_template(final_name, "Chest & Legs")
        
        else:
            mesh_handler.prepare_meshes()
            try:
                mesh_handler.process_meshes()
            except Exception as e:
                mesh_handler.restore_meshes()
                queue_exit()
                BatchQueue.ErrorMessage(message="MeshHandler has failed. Check logs for error message.")
                raise e

            FileExport().export_template(main_name, body_slot)

        setattr(devkit_props, "is_exporting", False)

        mesh_handler.restore_meshes()
        if queue:
            end_time = time.time()
            duration = end_time - start_time
            props.export_time = duration
            BatchQueue.progress_tracker(queue)
            return 0.3
        else:
            queue_exit()
            return None

    # These functions are responsible for applying the correct model state and appropriate file name.
    # They are called from the export_queue function.

    def hide_export_obj(size, export_obj:dict[str, Object], devkit_props) -> Object:
        category = devkit_props.ALL_SHAPES[size][2]
        for key, obj in export_obj.items():
            if key == category:
                # print(f"Showing {obj.name}")
                obj.hide_set(state=False)
            else:
                # print(f"Hiding {obj.name}")
                obj.hide_set(state=True)
     
    def progress_tracker(queue) -> None:
        props = get_file_properties()
        props.export_progress = (props.export_total - len(queue)) / props.export_total
        props.export_step = (props.export_total - len(queue)) 
        props.export_file_name = queue[-1][0]
        bpy.context.view_layer.update()

    def progress_reset(props) -> None:
        props.export_total = 0
        props.export_progress = 0
        props.export_step = 0
        props.export_time = 0
        props.export_file_name = ""

    def ErrorMessage(message = "", title = "ERROR"):

        def draw(self, context):
            self.layout.label(text=message)

        bpy.context.window_manager.popup_menu(draw, title = title, icon = "ERROR")


CLASSES = [
    SimpleExport,
    BatchQueue
]
