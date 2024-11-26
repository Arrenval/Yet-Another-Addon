import os
import bpy
import json
import winreg
import shutil
import zipfile


import penumbra   
import ya_utils    
from datetime      import datetime
from pathlib       import Path
from functools     import partial
from tools_ops     import ApplyShapes
from itertools     import combinations
from bpy.types     import Operator, PropertyGroup
from bpy.props     import StringProperty, EnumProperty, BoolProperty, PointerProperty

# Global variable for making sure all functions can properly track the current export.
is_exporting: bool = False

def force_yas(context):
    force_yas = context.scene.main_props.button_force_yas

    if force_yas:
        for obj in bpy.context.scene.objects:
            if obj.visible_get(view_layer=bpy.context.view_layer) and obj.type == "MESH":
                try:
                    obj.toggle_yas = True
                except:
                    continue

def check_triangulation(context):
    check_tris = context.scene.main_props.button_check_tris
    not_triangulated = []

    if check_tris:
        for obj in bpy.context.scene.objects:
            if obj.visible_get(view_layer=bpy.context.view_layer) and obj.type == "MESH":
                triangulated = False
                for modifier in reversed(obj.modifiers):
                    if modifier.type == "TRIANGULATE" and modifier.show_viewport:
                        triangulated = True
                        break
                if not triangulated:
                    not_triangulated.append(obj.name)
    
    if not_triangulated:
        return False, not_triangulated
    else:
        return True, ""

def get_modpack_groups(context):
        return [(str(option.group_value), option.group_name, option.group_description) for option in context.scene.modpack_group_options]

def modpack_data(context):
    scene = context.scene
    scene.modpack_group_options.clear()
    modpack = scene.file_props.loadmodpack_directory

    new_option = scene.modpack_group_options.add()
    new_option.group_value = int(0)
    new_option.group_name = "Create New Group"  
    new_option.group_description = ""

    if os.path.exists(modpack):
        with zipfile.ZipFile(modpack, "r") as pmp:
            for file_name in pmp.namelist():
                if file_name.count('/') == 0 and file_name.startswith("group") and not file_name.endswith("bak"):
                    number = lambda name: ''.join(char for char in name if char.isdigit())
                    group_name = modpack_group_data(file_name, pmp, data="name")

                    new_option = context.scene.modpack_group_options.add()
                    new_option.group_value = int(number(file_name))
                    new_option.group_name = group_name
                    new_option.group_description = file_name
 
            with pmp.open("meta.json") as meta:
                meta_contents = json.load(meta)

                mod_meta = penumbra.ModMeta(**meta_contents)
                scene.file_props.loadmodpack_version = mod_meta.Version
                scene.file_props.loadmodpack_author = mod_meta.Author
    
def modpack_group_data(file_name, pmp, data):
    try:
        with pmp.open(file_name) as file:
            file_contents = json.load(file)
                      
            group_data = penumbra.ModGroups(**file_contents)

            if data == "name":
                return group_data.Name
            if data == "all":
                return group_data

    except Exception as e:
        print(f"ERROR: {file_name[10:-4]}")
        return f"ERROR: {file_name[10:-4]}"    
  
def update_directory(category):
    prop = bpy.context.scene.file_props
    actual_prop = f"{category}_directory"
    display_prop = f"{category}_display_directory"

    display_directory = getattr(prop, display_prop, "")

    if os.path.exists(display_directory):  
        setattr(prop, actual_prop, display_directory)
        print (getattr(prop, actual_prop, ""))

def sanitise_path(path):
        return path.lower().replace(" - ", "_").replace(" ", "")


class ModpackGroups(PropertyGroup):
    group_value: bpy.props.IntProperty() # type: ignore
    group_name: bpy.props.StringProperty() # type: ignore
    group_description: bpy.props.StringProperty() # type: ignore


class FileProps(PropertyGroup):
    
    @staticmethod
    def export_bools():
        for shape, (name, slot, shape_category, description, body, key) in ya_utils.all_shapes.items():
            slot_lower = slot.lower().replace("/", " ")
            name_lower = name.lower().replace(" ", "_")
            
            prop_name = f"export_{name_lower}_{slot_lower}_bool"
            prop = BoolProperty(
                name="", 
                description=description,
                default=False, 
                )
            setattr(FileProps, prop_name, prop)

    extra_buttons_list = [
        ("check",    "tris",     True, "Verify that the meshes have an active triangulation modifier"),
        ("force",    "yas",      False, "This force enables YAS on any exported model and appends 'Yiggle' to their file name. Use this if you already exported regular models and want YAS alternatives"),
        ]
   
    @staticmethod
    def extra_options():
        for (name, category, default, description) in FileProps.extra_buttons_list:
            category_lower = category.lower()
            name_lower = name.lower()
            
            prop_name = f"{name_lower}_{category_lower}"
            prop = BoolProperty(
                name="", 
                description=description,
                default=default, 
                )
            setattr(FileProps, prop_name, prop)

    export_body_slot: EnumProperty(
        name= "",
        description= "Select a body slot",
        items= [
            ("Chest", "Chest", "Chest export options."),
            ("Legs", "Legs", "Leg export options."),
            ("Hands", "Hands", "Hand export options."),
            ("Feet", "Feet", "Feet export options."),
            ("Chest/Legs", "Chest/Legs", "When you want to export Chest with Leg models.")]
        )  # type: ignore


    modpack_groups: EnumProperty(
        name= "",
        description= "Select an option to replace",
        items= lambda self, context: get_modpack_groups(context)
        )   # type: ignore
    
    mod_group_type: EnumProperty(
        name= "",
        description= "Single or Multi",
        items= [
            ("Single", "Single", "Exclusive options in a group"),
            ("Multi", "Multi", "Multiple selectable options in a group")

        ]
        )   # type: ignore
    
    modpack_group_options: bpy.props.CollectionProperty(type=ModpackGroups) # type: ignore

    textools_directory: StringProperty(
        name="ConsoleTools Directory",
        subtype="FILE_PATH", 
        maxlen=255,
        options={'HIDDEN'},
        )  # type: ignore
    
    consoletools_status: StringProperty(
        default="Check for ConsoleTools:",
        maxlen=255

        )  # type: ignore
    
    game_model_path: StringProperty(
        name="",
        description="Path to the model you want to replace",
        default="Paste path here",
        maxlen=255

        )  # type: ignore
    
    loadmodpack_display_directory: StringProperty(
        name="Select PMP",
        default="Select Modpack",  
        maxlen=255,
        update=lambda self, context: update_directory('loadmodpack'),
        ) # type: ignore
    
    loadmodpack_directory: StringProperty(
        default="Select Modpack",
        subtype="FILE_PATH", 
        maxlen=255,
        update=lambda self, context: modpack_data(context)
        )  # type: ignore
    
    loadmodpack_version: StringProperty(
        name="",
        description="Use semantic versioning",
        default="", 
        maxlen=255,
        )  # type: ignore
    
    loadmodpack_author: StringProperty(
        default="", 
        maxlen=255,
        )  # type: ignore

    savemodpack_display_directory: StringProperty(
        name="",
        default="FBX folder",
        description="FBX location and/or mod export location", 
        maxlen=255,
        update=lambda self, context: update_directory('loadmodpack')
        )  # type: ignore
    
    savemodpack_directory: StringProperty(
        default="FBX folder", 
        maxlen=255,
        )  # type: ignore
    
    modpack_rename_group: StringProperty(
        name="",
        default="",
        description="Choose a name for the target group", 
        maxlen=255,
        )  # type: ignore
    
    modpack_progress: StringProperty(
        default="",
        description="Keeps track of the modpack progress", 
        maxlen=255,
        )  # type: ignore

    new_mod_name: StringProperty(
        name="",
        default="",
        description="The name of your mod", 
        maxlen=255,
        )  # type: ignore
    
    new_mod_version: StringProperty(
        name="",
        default="0.0.0",
        description="Use semantic versioning", 
        maxlen=255,
        )  # type: ignore
   
    author_name: StringProperty(
        name="",
        default="",
        description="Some cool person", 
        maxlen=255,
        )  # type: ignore

    export_display_directory: StringProperty(
        name="Export Folder",
        default="Select Export Directory",  
        maxlen=255,
        update=lambda self, context: update_directory('export'),
        ) # type: ignore
    
    export_directory: StringProperty(
        default="Select Export Directory",
        subtype="DIR_PATH", 
        maxlen=255,
        )  # type: ignore

    export_gltf: BoolProperty(
        name="",
        description="Switch export format", 
        default=False,
        ) # type: ignore
    
    ui_size_category: StringProperty(
        name="",
        subtype="DIR_PATH", 
        maxlen=255,
        )  # type: ignore


class SimpleExport(Operator):
    bl_idname = "ya.simple_export"
    bl_label = "Open Export Window"
    bl_description = "Exports single model"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def execute(self, context):
        triangulated, obj = check_triangulation(context)
        if not triangulated:
            self.report({'ERROR'}, f"Not Triangulated: {', '.join(obj)}")
            return {'CANCELLED'} 
        
        gltf = context.scene.file_props.export_gltf 
        directory = context.scene.file_props.export_directory
        export_path = os.path.join(directory, "untitled")
        export_settings = FileExport.get_export_settings(gltf)

        force_yas(context)

        if gltf:
            bpy.ops.export_scene.gltf('INVOKE_DEFAULT', filepath=export_path + ".gltf", **export_settings)
        else:
            bpy.ops.export_scene.fbx('INVOKE_DEFAULT', filepath=export_path + ".fbx", **export_settings)
        
        return {'FINISHED'}


class BatchQueue(Operator):
    bl_idname = "ya.batch_queue"
    bl_label = "Export"
    bl_description = "Exports your files based on your selections"
    bl_options = {'UNDO'}

    ob_mesh_dict = {
            "Chest": "Torso", 
            "Legs": "Waist", 
            "Hands": "Hands",
            "Feet": "Feet"
            }
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def __init__(self):
        self.queue = []
        self.leg_queue = []
        
    def execute(self, context):
        triangulated, obj = check_triangulation(context)
        if not triangulated:
            self.report({'ERROR'}, f"Not Triangulated: {', '.join(obj)}")
            return {'CANCELLED'} 
        
        prop = context.scene.file_props
        selected_directory = prop.export_directory
        self.gltf = prop.export_gltf
        self.body_slot = prop.export_body_slot
        
        if not os.path.exists(selected_directory):
            self.report({'ERROR'}, "No directory selected for export!")
            return {'CANCELLED'} 

        self.size_options = self.get_size_options(context)

        if self.body_slot == "Chest/Legs":
            self.actual_combinations = self.shape_combinations("Chest")
            self.calculate_queue("Chest")
            self.actual_combinations = self.shape_combinations("Legs")
            self.calculate_queue("Legs")
        else:
            self.actual_combinations = self.shape_combinations(self.body_slot)
            self.calculate_queue(self.body_slot)

        if "Legs" in self.body_slot:
            gen_options = len(self.actual_combinations.keys())
        else:
            gen_options = 0

        if self.queue == []:
            self.report({'ERROR'}, "No valid combinations!")
            return {'CANCELLED'} 
        
        if self.body_slot == "Chest/Legs":
            if self.leg_queue == []:
                self.report({'ERROR'}, "No valid combinations!")
                return {'CANCELLED'} 
            
        self.collection_state(context)
        bpy.ops.ya.collection_manager()

        force_yas(context)
        if "Chest" in self.body_slot:
            obj = ya_utils.get_object_from_mesh("Torso")
            yas = obj.modifiers["YAS Toggle"].show_viewport
            BatchQueue.ivcs_mune(context, yas)

        BatchQueue.process_queue(context, self.queue, self.leg_queue, self.body_slot, gen_options)
        return {'FINISHED'}
    
    # The following functions is executed to establish the queue and valid options 
    # before handing all variables over to queue processing

    def collection_state(self, context):
        context.scene.main_props.collection_state.clear()
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

            case "Chest/Legs":
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
            collection_state = context.scene.main_props.collection_state.add()
            collection_state.collection_name = name

    def get_size_options(self, context):
        options = {}
        prop = context.scene.file_props

        for shape, (name, slot, shape_category, description, body, key) in ya_utils.all_shapes.items():
            slot_lower = slot.lower().replace("/", " ")
            name_lower = name.lower().replace(" ", "_")

            prop_name = f"export_{name_lower}_{slot_lower}_bool"

            if hasattr(prop, prop_name):
                options[shape] = getattr(prop, prop_name)

        return options

    def calculate_queue(self, body_slot):
        mesh = self.ob_mesh_dict[body_slot]
        target = ya_utils.get_object_from_mesh(mesh).data.shape_keys.key_blocks

        leg_sizes = {
            "Melon": self.size_options["Melon"],
            "Skull": self.size_options["Skull"], 
            "Mini Legs": self.size_options["Mini Legs"]
            }

        if body_slot != "Legs":
            gen = None             
            for size, options_groups in self.actual_combinations.items(): 
                for options in options_groups:
                    self.queue.append((options, size, gen, target))
            return "Main queue finished."

        # Legs need different handling due to genitalia combos     
        for size, enabled in leg_sizes.items():
            if enabled:
                for gen, options_groups in self.actual_combinations.items(): 
                    for options in options_groups:
                        if self.body_slot == "Chest/Legs":
                            self.leg_queue.append((options, size, gen, target))
                        else:
                            self.queue.append((options, size, gen, target))
        if self.leg_queue != []:
            return "No leg options selected."
        
        return "Leg queue finished."
 
    def shape_combinations(self, body_slot):
        possible_parts  = [
            "Rue Legs", "Small Butt", "Soft Butt", "Hip Dips",
            "Buff", "Rue", 
            "Rue Hands", "YAB Hands", 
            "Clawsies"
            ]
        actual_parts = []
        all_combinations = set()
        actual_combinations = {}

        
        #Excludes possible parts based on which body slot they belong to
        for shape, (name, slot, category, description, body, key) in ya_utils.all_shapes.items():
            if any(shape in possible_parts for parts in possible_parts) and body_slot == slot and self.size_options[shape]:
                actual_parts.append(shape)  

        for r in range(0, len(actual_parts) + 1):
            if body_slot == "Hands":
                r = 1
            all_combinations.update(combinations(actual_parts, r))

        all_combinations = tuple(all_combinations)  

        for shape, (name, slot, category, description, body, key) in ya_utils.all_shapes.items():
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

    # These functions are responsible for processing the queue.
    # Export queue is running on a timer interval until the queue is empty.

    def process_queue(context, queue, leg_queue, body_slot, gen_options):
        global is_exporting
        is_exporting = False

        callback = partial(BatchQueue.export_queue, context, queue, leg_queue, body_slot, gen_options)
        
        bpy.app.timers.register(callback, first_interval=0.5) 

    def export_queue(context, queue, leg_queue, body_slot, gen_options):
        collection = bpy.context.view_layer.layer_collection.children
        global is_exporting

        if is_exporting:
            return 0.1
        
        second_queue = leg_queue

        is_exporting = True
        options, size, gen, target = queue.pop()
        
        BatchQueue.reset_model_state(body_slot, target)

        main_name = BatchQueue.name_generator(options, size, gen, gen_options, body_slot)
        BatchQueue.apply_model_state(options, size, gen, body_slot, target)

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
        
        if body_slot == "Chest/Legs":
            for leg_task in second_queue:
                options, size, gen, leg_target = leg_task
                if BatchQueue.check_rue_match(options, main_name):
                    body_slot = "Legs"
                    
                    BatchQueue.reset_model_state(body_slot, leg_target)
                    BatchQueue.apply_model_state(options, size, gen, body_slot, leg_target)

                    leg_name = BatchQueue.name_generator(options, size, gen, gen_options, body_slot)
                    main_name = leg_name + " - " + main_name
                    main_name = BatchQueue.clean_file_name(main_name)

                    FileExport.export_template(context, file_name=main_name)
        
        else:
            FileExport.export_template(context, file_name=main_name)

        is_exporting = False

        if queue:
            return 0.1
        else:
            if "Chest" in body_slot:
                obj = ya_utils.get_object_from_mesh("Torso")
                BatchQueue.ivcs_mune(context, obj)
            return None

    # These functions are responsible for applying the correct model state and appropriate file name.
    # They are called from the export_queue function.

    def check_rue_match (options, file_name):
        
        if "Rue" in file_name:
            if any("Rue" in option for option in options):
                return True
            else:
                return False
    
        return True

    def clean_file_name (file_name):
        first = file_name.find("Rue - ")

        second = file_name.find("Rue - ", first + len("Rue - "))

        if second == -1:
            return file_name
        
        return file_name[:second] + file_name[second + len("Rue - "):]

    def apply_model_state(options, size, gen, body_slot, ob):
        if body_slot == "Chest/Legs":
            body_slot = "Chest"

        for shape, (name, slot, category, description, body, key) in ya_utils.all_shapes.items():

            if shape == size and key != "":
                ob[key].mute = False

            if any(shape in options for option in options):
                if key != "":
                    ob[key].mute = False

        # Adds the shape value presets alongside size toggles
        if body_slot == "Chest":
            keys_to_filter = ["Squeeze", "Squish", "Push-Up", "Nip Nops"]
            preset = ya_utils.get_shape_presets(size)
            filtered_preset = {}
           

            for key in preset.keys():
                if not any(key.endswith(sub) for sub in keys_to_filter):
                    filtered_preset[key] = preset[key]

            category = ya_utils.all_shapes[size][2]
            ApplyShapes.mute_chest_shapes(ob, category)
            ApplyShapes.apply_shape_values("torso", category, filtered_preset)
            bpy.context.view_layer.objects.active = ya_utils.get_object_from_mesh("Torso")
            bpy.context.view_layer.update()
                
        
        if gen != None and gen.startswith("Gen") and gen != "Gen A":
            ob[gen].mute = False
                        
    def name_generator(options, size, gen, gen_options, body_slot):
        yiggle = bpy.context.scene.main_props.button_force_yas

        if body_slot == "Chest/Legs":
            body_slot = "Chest"
        if yiggle:
            file_names = ["Yiggle"]
        else:
            file_names = []
        
        gen_name = None

        #Loops over the options and applies the shapes name to file_names
        for shape, (name, slot, category, description, body, key) in ya_utils.all_shapes.items():
            if any(shape in options for option in options) and not shape.startswith("Gen") and name != "YAB":
                if name == "Hip Dips":
                    name = "Alt Hip" 
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

        file_names.append(size_name)

        if body_slot == "Feet":
            file_names = reversed(file_names)

        if gen_name != None:
            file_names.append(gen_name)
        
        return " - ".join(list(file_names))
    
    def reset_model_state(body_slot, ob):
        if body_slot == "Chest/Legs":
            body_slot = "Chest"

        reset_shape_keys = []

        for shape, (name, slot, shape_category, description, body, key) in ya_utils.all_shapes.items():
            if key != "" and slot == body_slot:
                if shape == "Hip Dips":
                    reset_shape_keys.append("Hip Dips (for YAB)")
                    reset_shape_keys.append("Less Hip Dips (for Rue)")
                else:
                    reset_shape_keys.append(key)

        for key in reset_shape_keys:   
            ob[key].mute = True

    def ivcs_mune(context, yas=False):
        for obj in bpy.context.scene.objects:
            if obj.visible_get(view_layer=bpy.context.view_layer) and obj.type == "MESH":
                for group in obj.vertex_groups:
                    try:
                        if yas:
                            if group.name == "j_mune_r":
                                group.name = "iv_c_mune_r"
                            if group.name == "j_mune_l":
                                group.name = "iv_c_mune_l"
                        else:
                            if group.name == "iv_c_mune_r":
                                    group.name = "j_mune_r"
                            if group.name == "iv_c_mune_l":
                                group.name = "j_mune_l"
                    except:
                        continue
      
    
class FileExport(Operator):
    bl_idname = "ya.file_export"
    bl_label = "Export"
    bl_description = ""
    bl_options = {'UNDO'}

    file_name: StringProperty() # type: ignore

    def execute(self, context):
            FileExport.export_template(context, self.file_name)

    def export_template(context, file_name):
        gltf = context.scene.file_props.export_gltf
        selected_directory = context.scene.file_props.export_directory

        export_path = os.path.join(selected_directory, file_name)
        export_settings = FileExport.get_export_settings(gltf)

        if gltf:
            bpy.ops.export_scene.gltf(filepath=export_path + ".gltf", **export_settings)
        else:
            bpy.ops.export_scene.fbx(filepath=export_path + ".fbx", **export_settings)
        
    def get_export_settings(gltf):
        if gltf:
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
                "export_try_sparse_sk": False,
                "export_attributes": True,
                "export_tangents": True,
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


class ConsoleTools(Operator):
    bl_idname = "ya.file_console_tools"
    bl_label = "Modpacker"
    bl_description = "Checks for a valid TexTools install with ConsoleTools"
    bl_options = {'UNDO'}

    def execute(self, context):
        consoletools, textools = self.console_tools_location(context)

        if os.path.exists(consoletools):
            context.scene.file_props.textools_directory = textools
            context.scene.file_props.consoletools_status = "ConsoleTools Ready!"
        else:
            context.scene.file_props.textools_directory = ""
            context.scene.file_props.consoletools_status = "Not Found. Click Folder."
        
        return {"FINISHED"}
    
    def console_tools_location(self, context):
        textools = "FFXIV TexTools"
        textools_install = ""
        
        registry_path = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        
        reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path)
        
        for i in range(0, winreg.QueryInfoKey(reg_key)[0]):
            subkey_name = winreg.EnumKey(reg_key, i)
            
            subkey = winreg.OpenKey(reg_key, subkey_name)
            
            try:
                display_name, type = winreg.QueryValueEx(subkey, "DisplayName")
                
                if textools.lower() in display_name.lower():
                    textools_install, type = winreg.QueryValueEx(subkey, "InstallLocation")
                    break
                
            except FileNotFoundError:
                continue
            
            finally:
                winreg.CloseKey(subkey)
        
        winreg.CloseKey(reg_key)

        textools_install = textools_install.strip('"')
        consoletools_path = os.path.join(textools_install, "FFXIV_TexTools", "ConsoleTools.exe")
        path_parts = consoletools_path.split(os.sep)
        textools_folder = os.sep.join(path_parts[:-1])
        
        
        return consoletools_path, textools_folder


class Modpacker(Operator):
    bl_idname = "ya.file_modpacker"
    bl_label = "Modpacker"
    bl_description = "Converts FBX and/or packages FFXIV model files into a penumbra Modpack"
    bl_options = {'UNDO'}

    preset: StringProperty()  # type: ignore # convert_pack, pack, convert are valid presets

    def execute(self, context):
        paths, user_input = self.get_user_input(context)
        replace = context.scene.main_props.button_modpack_replace

        if not paths["gamepath"]:
            self.report({'ERROR'}, "Please input a path to an FFXIV model")
            return {'CANCELLED'}
        
        elif not paths["gamepath"].startswith("chara") or not paths["gamepath"].endswith("mdl"):
            self.report({'ERROR'}, "Verify that the model is an actual FFXIV path")
            return {'CANCELLED'}

        if replace:
            if not paths["pmp"]:
                self.report({'ERROR'}, "Please select a modpack.")
                return {'CANCELLED'} 
        
        if replace:
            if user_input["selected"] == "0" and not user_input["new_group_name"]:
                self.report({'ERROR'}, "Please enter a group name.")
                return {'CANCELLED'}
            
        if not replace:
            if  not user_input["new_group_name"]:
                self.report({'ERROR'}, "Please enter a group name.")
                return {'CANCELLED'}
        
        if self.preset != "pack":
            if context.scene.file_props.consoletools_status != "ConsoleTools Ready!":
                self.report({'ERROR'}, "Verify that ConsoleTools is ready.")
                return {'CANCELLED'} 

            context.scene.file_props.modpack_progress = "Converting fbx to mdl..."
            self.fbx_to_mdl(context, paths)
            context.scene.file_props.modpack_progress = "Converting Complete!" 

        if replace:
            mod_data, mod_meta = self.current_mod_data(replace, paths["pmp"])
        else:
            mod_data, mod_meta = {}, {}

        self.mdl_timer(context, paths, user_input, self.preset, mod_data, mod_meta)

        return {"FINISHED"}

    def get_user_input(self, context):
        file_props = context.scene.file_props
        fbx_folder = file_props.savemodpack_directory
        selected = file_props.modpack_groups
        gamepath = file_props.game_model_path
        group_name = ""
        update_group = ""
        selected = ""

        for group in get_modpack_groups(context):
                if selected == group[0]:
                    group_name, update_group = group[1], group[2]

        paths = {
            "fbx": fbx_folder,
            "mdl": os.path.join(fbx_folder, "MDL"),
            "temp": os.path.join(fbx_folder, "temp_pmp"),
            "gamepath": gamepath.lower(),
            "pmp": file_props.loadmodpack_directory,
        }

        if context.scene.main_props.button_modpack_replace:
            modpack_name = file_props.loadmodpack_display_directory
        else:
            modpack_name = file_props.new_mod_name
            paths["pmp"] = None
            
        mod_meta = {
                "Author": file_props.author_name,
                "Version": file_props.new_mod_version
            }
        
        user_input = {
            "selected": selected,
            "new_group_name": file_props.modpack_rename_group,
            "old_group_name": group_name,
            "meta": mod_meta,
            "pmp_name": modpack_name,
            "update_group": update_group,
            "group_type": file_props.mod_group_type,
            "load_mod_ver": file_props.loadmodpack_version
        }

        return paths, user_input
   
    def current_mod_data(self, replace, pmp):
        if not replace or self.preset == "convert":
            return None
        current_mod_data = {}

        with zipfile.ZipFile(pmp, "r") as pmp:
            for file_name in sorted(pmp.namelist()):
                if file_name.count('/') == 0 and file_name.startswith("group") and file_name.endswith(".json"):
                    group_data = modpack_group_data(file_name, pmp, data="all")
                    
                    current_mod_data[file_name] = group_data 
            with pmp.open("meta.json") as meta:
                meta_contents = json.load(meta)

                current_mod_meta = penumbra.ModMeta(**meta_contents)
            
        
        return current_mod_data, current_mod_meta  
 
    def fbx_to_mdl(self, context, paths):
        textools = context.scene.file_props.textools_directory
        to_convert = [file.name for file in Path(paths["fbx"]).glob(f'*.fbx') if file.is_file()]

        cmd_name = "FBXtoMDL.cmd"
        sys_drive = textools.split(os.sep)[0]
        commands = ["@echo off", f"cd /d {sys_drive}", f"cd {textools}"]

        cmd_path = os.path.join(paths["fbx"], cmd_name)
        if not os.path.isdir(paths["mdl"]):
            os.mkdir(os.path.join(paths["fbx"], "MDL"))

        cmds_added = 0
        total_files = len(to_convert)
        for file in to_convert:
            files_left = total_files - cmds_added    
            fbx_to_mdl = f'"{os.path.join(paths["fbx"], file)}" "{os.path.join(paths["mdl"], file[:-3])}mdl" "{paths["gamepath"]}"'
            
            if cmds_added % 5 == 0 and cmds_added == 0:
                commands.append(f"echo {files_left} files to convert...")
            
            elif cmds_added % 5 == 0:
                commands.append(f"echo {files_left} files left...")
            
            commands.append(f"echo Converting: {file[0:-4]}")
            commands.append(f"ConsoleTools.exe /wrap {fbx_to_mdl} >nul")
            cmds_added += 1
        
        commands.append("ping 127.0.0.1 -n 2 >nul")
        commands.append('start "" /min cmd /c "del \"%~f0\""')
        commands.append("exit")

        with open(cmd_path, 'w') as file:
            for cmd in commands:
                file.write(f"{cmd}\n")

        os.startfile(cmd_path)

    def mdl_timer(self, context, paths, user_input, preset, mod_data, mod_meta):
        # Calls a timer to wait for mdl conversion to finish

        callback = partial(Modpacker.create_modpack, context, paths, user_input, preset, mod_data, mod_meta)
        
        bpy.app.timers.register(callback, first_interval=0.5)

    def create_modpack(context, paths, user_input, preset, mod_data, mod_meta):
        is_cmd = [file.name for file in Path(paths["fbx"]).glob(f'FBXtoMDL.cmd') if file.is_file()]
       
       # the .cmd file deletes itself when done, this makes the packing process wait until it has finished converting the fbx
        if is_cmd:
            return 0.5 
        if not is_cmd and preset == "convert":
            context.scene.file_props.modpack_progress = "Complete!"
        context.scene.file_props.modpack_progress = "Creating modpack..."  
        to_pack = [file.name for file in Path(paths["mdl"]).glob(f'*.mdl') if file.is_file()]
        to_pack = Modpacker.custom_sort(to_pack)
        Modpacker.rolling_backup(paths)

        if not os.path.isdir(paths["temp"]):
            os.mkdir(os.path.join(paths["fbx"], "temp_pmp"))

        if mod_data:
            with zipfile.ZipFile(paths["pmp"], "r") as pmp:
                pmp.extractall(paths["temp"])
            Modpacker.update_mod(paths, user_input, mod_data, to_pack, mod_meta)    
        else:
            Modpacker.new_mod(paths, user_input, to_pack)
        
        with zipfile.ZipFile(os.path.join(paths["fbx"], user_input["pmp_name"]) + ".pmp", 'w', zipfile.ZIP_DEFLATED) as pmp:
            for root, dir, files in os.walk(paths["temp"]):
                for file in files:
                    file_path = os.path.join(root, file)
                    pmp.write(file_path, os.path.relpath(file_path, paths["temp"]))

        bpy.app.timers.register(partial(Modpacker.schedule_cleanup, paths["temp"]), first_interval=0.1)
        modpack_data(context)
        context.scene.file_props.modpack_progress = "Complete!"

    def custom_sort(list):
        ranking = {}
        final_sort = []
        
        for item in list:
            ranking[item] = 0
            if "Small" in item:
                ranking[item] += 0
            if "Medium" in item:
                ranking[item] += 1
            if "Large" in item:
                ranking[item] += 2
            if "Buff" in item:
                ranking[item] += 3
            if "Rue" in item:
                ranking[item] += 4
            if "Yiggle" in item:
                ranking[item] += 5

        sorted_rank = sorted(ranking.items(), key=lambda x: x[1])
        
        for tuples in sorted_rank:
            final_sort.append(tuples[0])

        return final_sort

    def rolling_backup(paths):
        folder_bak = os.path.join(paths["fbx"], "BACKUP")
        time = datetime.now().strftime("%Y-%m-%d - %H%M%S")
        pmp_bak = os.path.join(folder_bak, time + ".pmp")
        
        if not os.path.isdir(folder_bak):
            os.mkdir(folder_bak)

        existing_bak = sorted([file.name for file in Path(folder_bak).glob("*.pmp") if file.is_file()], reverse=True)

        while len(existing_bak) >= 5:
            oldest_backup = existing_bak.pop()
            os.remove(os.path.join(folder_bak, oldest_backup))

        
        shutil.copy(paths["pmp"], pmp_bak)

    def new_mod(paths, user_input, to_pack):
        meta_content = penumbra.ModMeta(**user_input["meta"])
        meta_content.Name = user_input["pmp_name"]
        group_data = Modpacker.get_group_data_template(user_input)

        with open(os.path.join(paths["temp"], "meta.json"), "w") as file:
                file.write(meta_content.to_json())

        default_mod = penumbra.ModGroups()

        with open(os.path.join(paths["temp"], "default_mod.json"), "w") as file:
                file.write(default_mod.to_json())

        file_name = f"group_001_{user_input['new_group_name'].lower()}.json"
        create_group = {file_name: (paths["gamepath"], user_input["new_group_name"], group_data)}
        Modpacker.write_group_json(paths, user_input, to_pack, create_group, user_input["new_group_name"])

        for file in to_pack:
            option_name = file[:-4] 
            rel_path = sanitise_path(os.path.join(user_input["new_group_name"], option_name))
            target_path = os.path.join(paths["temp"], rel_path)   
            os.makedirs(target_path, exist_ok=True)
        
            shutil.copy(os.path.join(paths["mdl"], file), os.path.join(target_path, sanitise_path(file)))

    def update_mod (paths, user_input, mod_data, to_pack, mod_meta):
        group_dir = user_input["new_group_name"] if user_input["new_group_name"] else user_input["old_group_name"]
        group_data = Modpacker.get_group_data_template(user_input, mod_data)
        duplicate_groups = {} 
        previous_group = None
        
        if user_input["selected"] != "0":
            duplicate_groups = Modpacker.check_duplicate_groups(paths["temp"],mod_data, user_input)
            
            Modpacker.delete_orphans(paths["temp"], mod_data[user_input["update_group"]])
        else:
            if len(mod_data) != 0:
                previous_group, contents = mod_data.popitem()

                group_data["Page"] = contents.Page

        file_name, group_name = Modpacker.update_file_name(paths["temp"], user_input, previous_group)
        create_group = {file_name: (paths["gamepath"], group_name, group_data)}
        
        if duplicate_groups:
            for dupe_group, (other_gamepath, dupe_group_name) in duplicate_groups.items():
                    create_group[dupe_group] = (other_gamepath, dupe_group_name, group_data)
        
        os.remove(os.path.join(paths["temp"], user_input["update_group"]))
        Modpacker.write_group_json(paths, user_input, to_pack, create_group, group_dir, mod_data)

        mod_meta.Version = user_input["load_mod_ver"]

        with open(os.path.join(paths["temp"], "meta.json"), "w") as file:
                file.write(mod_meta.to_json())
        
        for file in to_pack:
            option_name = file[:-4] 
            rel_path = sanitise_path(os.path.join(group_dir, option_name))
            target_path = os.path.join(paths["temp"], rel_path)   
            os.makedirs(target_path, exist_ok=True)
        
            shutil.copy(os.path.join(paths["mdl"], file), os.path.join(target_path, sanitise_path(file)))

    def get_group_data_template(user_input, mod_data=None):
        if mod_data and user_input["selected"] != "0":
            return {
            "Name": "",
            "Description": mod_data[user_input["update_group"]].Description,
            "Priority": mod_data[user_input["update_group"]].Priority,
            "Image": mod_data[user_input["update_group"]].Image,
            "Page": mod_data[user_input["update_group"]].Page,
            "Type": mod_data[user_input["update_group"]].Type,
            "DefaultSettings": mod_data[user_input["update_group"]].DefaultSettings,
            "Options": [],
            }
        
        else:
            return {
            "Name": user_input["new_group_name"],
            "Description": "",
            "Priority": 0,
            "Image": "",
            "Page": 0,
            "Type": user_input["group_type"],
            "DefaultSettings": 0,
            "Options": [],
            }

    def write_group_json(paths, user_input, to_pack, create_group, group_dir, mod_data={}):
        
        for file_name, (gamepath, group_name, group_data) in create_group.items():
            
            options = [
                {
                "Files": {},
                "FileSwaps": {},
                "Manipulations": [],
                "Priority": 0,
                "Name": "None",
                "Description": "",
                "Image": ""
                }
                ]
            
            if user_input["update_group"] in mod_data:
                to_replace = mod_data[user_input["update_group"]]
            else:
                to_replace = ""
 
            for file in to_pack:
                option_name = file[:-4]
                new_option = {
                        "Files": {},
                        "FileSwaps": {},
                        "Manipulations": [],
                        "Priority": 0,
                        "Name": "",
                        "Description": "",
                        "Image": ""
                        }

                if to_replace:
                    for option in to_replace.Options:
                        if option.Name == option_name:
                            new_option["Description"] = option.Description
                            new_option["Priority"] = to_replace.Priority

                rel_path = f"{group_dir}\\{option_name}\\{file}"
                new_option["Files"] = {gamepath: sanitise_path(rel_path)}
                new_option["Name"] = option_name
                    
                options.append(new_option)

            group_data["Options"] = options
            group_data["Name"] = group_name

            new_group = os.path.join(paths["temp"], file_name)


            with open(new_group, "w") as file:
                file.write(penumbra.ModGroups(**group_data).to_json())

    def update_file_name(temp_folder, user_input, previous_group=None):
        old_group_name = user_input["old_group_name"]
        new_group_name = user_input["new_group_name"]
        old_file_name = user_input["update_group"]
        split_name = old_file_name.split("_")
        final_digits = int(split_name[1])  
        
        if previous_group:
            split_name = previous_group.split("_")
            final_digits = int(split_name[1]) + 1   

        if new_group_name:
                file_name = f"group_{final_digits:03}_{new_group_name.lower()}.json"

                return file_name, new_group_name
        else:
            return old_file_name, old_group_name
   
    def check_duplicate_groups(temp_folder, mod_data, user_input):
        # Duplicate groups might use the same files, but on different items, typically Smallclothes/Emperor's.
        # This is to prevent breaking groups that use the same files. Will not catch similar groups. 
        relative_paths = []
        dupe_rel_paths = []
        duplicate_groups = {}

        for options in mod_data[user_input["update_group"]].Options:
            for gamepath, relpath in options.Files.items():
                relative_paths.append(relpath)

        for group in mod_data:
            file_contents = mod_data[group]
            if group != user_input["update_group"]:
                try:
                    for option in file_contents.Options:
                        for gamepath, relpath in option.Files.items():
                            if any(relpath in relative_paths for path in relative_paths):
                                dupe_rel_paths.append(relpath)
                                
                    if len(dupe_rel_paths) == len(relative_paths):
                        duplicate_groups[group] = (gamepath, file_contents.Name)
                        dupe_rel_paths = []     
                except:
                    continue
        
        return duplicate_groups

    def delete_orphans(temp_folder, update_group): 
        for options in update_group.Options:
            for gamepath, relpath in options.Files.items():
                try:
                    absolute_path = os.path.join(temp_folder, relpath)
                    os.remove(absolute_path)
                    print(f"Deleted file: {absolute_path}")
                except:
                    continue

        for root, dirs, files in os.walk(temp_folder, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                if not os.listdir(dir_path):
                    try: 
                        os.rmdir(dir_path) 
                        print(f"Deleted empty directory: {dir_path}")
                    except:
                        continue

    def schedule_cleanup(temp_folder, retries=5):
        for attempts in range(retries):
            try:
                if os.path.isdir(temp_folder):
                    
                    shutil.rmtree(temp_folder)
                    break
            except FileNotFoundError as e:
                break
            return 1


classes = [
    ModpackGroups,
    FileProps,
    SimpleExport,
    BatchQueue,
    FileExport,
    ConsoleTools,
    Modpacker
]

def set_file_properties():
    bpy.types.Scene.file_props = PointerProperty(
        type=FileProps)

    bpy.types.Scene.modpack_group_options = bpy.props.CollectionProperty(
        type=ModpackGroups)
    
    FileProps.export_bools()
    FileProps.extra_options()
