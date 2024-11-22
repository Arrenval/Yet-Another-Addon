import os
import bpy
import json
import winreg
import shutil
import zipfile
import ya_utils as utils


from pathlib import Path
from typing import List, Dict, Union
from functools import partial
from itertools import combinations
from dataclasses import dataclass, asdict, field
from bpy.types import Operator
from bpy.props import StringProperty
from ya_shape_ops import MESH_OT_YA_ApplyShapes as ApplyShapes

# Global variable for making sure all functions can properly track the current export.
# Ease of use alongside blender's timers.
is_exporting: bool = False

class FILE_OT_SimpleExport(Operator):
    bl_idname = "ya.simple_export"
    bl_label = "Open Export Window"
    bl_description = "Exports single model"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def execute(self, context):
        gltf = context.scene.ya_props.export_gltf 
        directory = context.scene.ya_props.export_directory
        export_path = os.path.join(directory, "untitled")
        export_settings = FILE_OT_YA_FileExport.get_export_settings(gltf)

        if gltf:
            bpy.ops.export_scene.gltf('INVOKE_DEFAULT', filepath=export_path + ".gltf", **export_settings)
        else:
            bpy.ops.export_scene.fbx('INVOKE_DEFAULT', filepath=export_path + ".fbx", **export_settings)
        
        return {'FINISHED'}


class FILE_OT_YA_BatchQueue(Operator):
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
        self.size_options = None
        self.selected_directory = None
        self.filetype = None
        self.body_slot = None
        self.queue = []
        self.leg_queue = []
        
    def execute(self, context):
        prop = context.scene.ya_props
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

        if self.body_slot == "Legs" or self.body_slot == "Chest/Legs":
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
        FILE_OT_YA_BatchQueue.process_queue(context, self.queue, self.leg_queue, self.body_slot, gen_options)

        return {'FINISHED'}
    
    # The following functions is executed to establish the queue and valid options 
    # before handing all variables over to queue processing
    def collection_state(self, context):
        context.scene.ya_props.collection_state.clear()
        collections = []

        if self.body_slot == "Chest":
            collections = ["Chest"]
            if self.size_options["Piercings"]:
                collections.append("Nipple Piercings")

        elif self.body_slot == "Legs":
            collections = ["Legs"]
            if self.size_options["Pubes"]:
                collections.append("Pubes")

        elif self.body_slot == "Chest/Legs":
            collections = ["Chest", "Legs"]
            if self.size_options["Piercings"]:
                collections.append("Nipple Piercings")
            if self.size_options["Pubes"]:
                collections.append("Pubes")

        for name in collections:
            collection_state = context.scene.ya_props.collection_state.add()
            collection_state.collection_name = name

    def get_size_options(self, context):
        options = {}
        prop = context.scene.ya_props

        for shape, (name, slot, shape_category, description, body, key) in utils.all_shapes.items():
            slot_lower = slot.lower().replace("/", " ")
            name_lower = name.lower().replace(" ", "_")

            prop_name = f"export_{name_lower}_{slot_lower}_bool"

            if hasattr(prop, prop_name):
                options[shape] = getattr(prop, prop_name)

        return options

    def calculate_queue(self, body_slot):
        mesh = self.ob_mesh_dict[body_slot]
        target = utils.get_object_from_mesh(mesh).data.shape_keys.key_blocks

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
        for shape, (name, slot, category, description, body, key) in utils.all_shapes.items():
            if any(shape in possible_parts for parts in possible_parts) and body_slot == slot and self.size_options[shape]:
                actual_parts.append(shape)  

        for r in range(0, len(actual_parts) + 1):
            if body_slot == "Hands":
                r = 1
            all_combinations.update(combinations(actual_parts, r))

        all_combinations = tuple(all_combinations)  

        for shape, (name, slot, category, description, body, key) in utils.all_shapes.items():
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

        callback = partial(FILE_OT_YA_BatchQueue.export_queue, context, queue, leg_queue, body_slot, gen_options)
        
        bpy.app.timers.register(callback, first_interval=0.5) 

    def export_queue(context, queue, leg_queue, body_slot, gen_options):
        global is_exporting

        if is_exporting:
            return 0.1
        
        second_queue = leg_queue

        is_exporting = True
        options, size, gen, target = queue.pop()
        
        FILE_OT_YA_BatchQueue.reset_model_state(body_slot, target)

        main_name = FILE_OT_YA_BatchQueue.name_generator(options, size, gen, gen_options, body_slot)
        FILE_OT_YA_BatchQueue.apply_model_state(options, size, gen, body_slot, target)

        if body_slot == "Hands":

            if size == "Straight" or size == "Curved":
                collections = ["Hands", "Clawsies"]
                extra = json.dumps(collections)
                bpy.ops.utils.collection_manager(extra_json = extra)
    
            else:
                collections = ["Hands", "Nails"]
                extra = json.dumps(collections)
                bpy.ops.utils.collection_manager(extra_json = extra)
    
        if body_slot == "Feet":

            if "Clawsies" in options:
                collections = ["Feet", "Toe Clawsies"]
                extra = json.dumps(collections)
                bpy.ops.utils.collection_manager(extra_json = extra)
    
            else:
                collections = ["Feet", "Toenails"]
                extra = json.dumps(collections)
                bpy.ops.utils.collection_manager(extra_json = extra)
        
        if body_slot == "Chest/Legs":
            for leg_task in second_queue:
                options, size, gen, target = leg_task
                if FILE_OT_YA_BatchQueue.check_rue_match(options, main_name):
                    body_slot = "Legs"
                    
                    FILE_OT_YA_BatchQueue.reset_model_state(body_slot, target)
                    FILE_OT_YA_BatchQueue.apply_model_state(options, size, gen, body_slot, target)

                    leg_name = FILE_OT_YA_BatchQueue.name_generator(options, size, gen, gen_options, body_slot)
                    main_name = leg_name + " - " + main_name
                    main_name = FILE_OT_YA_BatchQueue.clean_file_name(main_name)

                    FILE_OT_YA_FileExport.export_template(context, file_name=main_name)
        
        else:
            FILE_OT_YA_FileExport.export_template(context, file_name=main_name)

        is_exporting = False

        if queue:
            return 0.1
        else:
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

        for shape, (name, slot, category, description, body, key) in utils.all_shapes.items():

            if shape == size and key != "":
                ob[key].mute = False

            if any(shape in options for option in options):
                if key != "":
                    ob[key].mute = False

        # Adds the shape value presets alongside size toggles
        if body_slot == "Chest":
            keys_to_filter = ["Squeeze", "Squish", "Push-Up", "Nip Nops"]
            preset = utils.get_shape_presets(size)
            filtered_preset = {}
           

            for key in preset.keys():
                if not any(key.endswith(sub) for sub in keys_to_filter):
                    filtered_preset[key] = preset[key]

            category = utils.all_shapes[size][2]
            ApplyShapes.mute_chest_shapes(ob, category)
            ApplyShapes.apply_shape_values("torso", category, filtered_preset)
            bpy.context.view_layer.objects.active = utils.get_object_from_mesh("Torso")
            bpy.context.view_layer.update()
                
        
        if gen != None and gen.startswith("Gen") and gen != "Gen A":
            ob[gen].mute = False
                        
    def name_generator(options, size, gen, gen_options, body_slot):
        if body_slot == "Chest/Legs":
            body_slot = "Chest"
        file_names = []
        gen_name = None

        #Loops over the options and applies the shapes name to file_names
        for shape, (name, slot, category, description, body, key) in utils.all_shapes.items():
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

        for shape, (name, slot, shape_category, description, body, key) in utils.all_shapes.items():
            if key != "" and slot == body_slot:
                if shape == "Hip Dips":
                    reset_shape_keys.append("Hip Dips (for YAB)")
                    reset_shape_keys.append("Less Hip Dips (for Rue)")
                else:
                    reset_shape_keys.append(key)

        for key in reset_shape_keys:   
            ob[key].mute = True

    
class FILE_OT_YA_FileExport(Operator):
    bl_idname = "ya.file_export"
    bl_label = "Export"
    bl_description = ""
    bl_options = {'UNDO'}

    file_name: StringProperty() # type: ignore

    def execute(self, context):
            FILE_OT_YA_FileExport.export_template(context, self.file_name)

    def export_template(context, file_name):
        gltf = context.scene.ya_props.export_gltf
        selected_directory = context.scene.ya_props.export_directory

        export_path = os.path.join(selected_directory, file_name)
        export_settings = FILE_OT_YA_FileExport.get_export_settings(gltf)

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


class FILE_OT_YA_ConsoleTools(Operator):
    bl_idname = "ya.file_console_tools"
    bl_label = "Modpacker"
    bl_description = "Checks for a valid TexTools install with ConsoleTools"
    bl_options = {'UNDO'}

    def execute(self, context):
        consoletools, textools = self.console_tools_location(context)

        if os.path.exists(consoletools):
            context.scene.ya_props.textools_directory = textools
            context.scene.ya_props.consoletools_status = "ConsoleTools Ready!"
        else:
            context.scene.ya_props.textools_directory = ""
            context.scene.ya_props.consoletools_status = "Not Found. Click Folder."
        
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


class FILE_OT_YA_Modpacker(Operator):
    bl_idname = "ya.file_modpacker"
    bl_label = "Modpacker"
    bl_description = "Packages FFXIV model files into a Penumbra Modpack"
    bl_options = {'UNDO'}

    def execute(self, context):
        ya_props = context.scene.ya_props
        textools = ya_props.textools_directory
        game_model = ya_props.game_model_path

        if not game_model:
            self.report({'ERROR'}, "Please input a path to an FFXIV model")
            return {'CANCELLED'} 
        
        fbx_folder = ya_props.export_directory
        mdl_folder = os.path.join(fbx_folder, "MDL")
        temp_folder = os.path.join(fbx_folder, "temp_pmp")
        folders = (fbx_folder, mdl_folder, temp_folder)
        
        selected_option = ya_props.modpack_groups
        modpack_path = ya_props.loadmodpack_directory
        modpack_groups = utils.get_modpack_groups(context)
        mod_data = (selected_option, modpack_path, modpack_groups)
        
        self.fbx_to_mdl(textools, folders, game_model)
        self.mdl_conversion_wait(context, folders, game_model, mod_data)

        return {"FINISHED"}
    
    
    def fbx_to_mdl(self, textools, folders, game_model):
        fbx_folder, mdl_folder, temp_folder = folders
        to_convert = [file.name for file in Path(fbx_folder).glob(f'*.fbx') if file.is_file()]

        cmd_name = "FBXtoMDL.cmd"
        sys_drive = textools.split(os.sep)[0]
        commands = ["@echo off", f"cd /d {sys_drive}", f"cd {textools}"]

        cmd_path = os.path.join(fbx_folder, cmd_name)
        if not os.path.isdir(mdl_folder):
            os.mkdir(os.path.join(fbx_folder, "MDL"))

        cmds_added = 0
        total_files = len(to_convert)
        for file in to_convert:
            files_left = total_files - cmds_added    
            fbx_to_mdl = f'"{os.path.join(fbx_folder, file)}" "{os.path.join(mdl_folder, file[:-3])}mdl" "{game_model}"'
            
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

    def mdl_conversion_wait(self, context, folders, game_model, mod_data):
        global is_converting
        is_converting = True

        callback = partial(FILE_OT_YA_Modpacker.create_modpack, context, folders, game_model, mod_data)
        
        bpy.app.timers.register(callback, first_interval=0.5)

    def create_modpack(context, folders, game_model, mod_data):
        fbx_folder, mdl_folder, temp_folder = folders
        selected_option, mod_path, mod_groups = mod_data

        is_cmd = [file.name for file in Path(fbx_folder).glob(f'FBXtoMDL.cmd') if file.is_file()]
       
       # the .cmd file deletes itself when done, this makes the packing process
       # wait until it has finished converting the fbx
        if is_cmd:
            return 0.5      
             
        if not os.path.isdir(temp_folder):
            os.mkdir(os.path.join(fbx_folder, "temp_pmp"))

        with zipfile.ZipFile(mod_path, "r") as pmp:
             pmp.extractall(temp_folder)

        for group in mod_groups:
            if selected_option == group[0]:
                group_name, group_to_replace = group[1], group[2]       
        
        new_group = os.path.join(temp_folder, group_to_replace)
        FILE_OT_YA_Modpacker.json_and_copy(mdl_folder, temp_folder, game_model, group_name, new_group)

        backup = os.path.join(fbx_folder, "Backup.pmp")
        shutil.copy(mod_path, backup)

        with zipfile.ZipFile(mod_path, 'w', zipfile.ZIP_DEFLATED) as pmp:
            for root, dir, files in os.walk(temp_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    pmp.write(file_path, os.path.relpath(file_path, temp_folder))

    
        if os.path.isdir(temp_folder):
            shutil.rmtree(temp_folder)
  
    def json_and_copy(mdl_folder, temp_folder, game_model, group_name, new_group):
        to_pack = [file.name for file in Path(mdl_folder).glob(f'*.mdl') if file.is_file()]

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

        group_data = {
            "Name": group_name,
            "Description": "Test",
            "Priority": 0,
            "Image": "",
            "Page": 1,
            "Type": "Single",
            "DefaultSettings": 0,
            "Options": options,
            }
 
        for file in to_pack:
            option_name = file[:-4]
            option = {
                "Files": {},
                "FileSwaps": {},
                "Manipulations": [],
                "Priority": 0,
                "Name": "",
                "Description": "",
                "Image": ""
                }

            file_path = f"{group_name}\\{option_name}\\{file}"
            option["Files"] = {game_model: file_path}
            option["Name"] = option_name
            
            options.append(option)

        with open(new_group, "w") as file:
            file.write(PenumbraGroups(**group_data).to_json())

        for file in to_pack:
            option_name = file[:-4]
            target_path = os.path.join(temp_folder, group_name, option_name)
            os.makedirs(target_path, exist_ok=True)
        
            shutil.copy(os.path.join(mdl_folder, file), target_path)

        

        
    

def modpack_groups_list(self, context):
    scene = context.scene
    scene.modpack_group_options.clear()
    modpack = scene.ya_props.loadmodpack_directory
    
    new_option = scene.modpack_group_options.add()
    new_option.group_value = int(0)
    new_option.group_name = "Create new option"  
    new_option.group_description = ""

    with zipfile.ZipFile(modpack, "r") as pmp:
        for file_name in pmp.namelist():
            if file_name.count('/') == 0 and file_name.startswith("group"):
                number = lambda name: ''.join(char for char in name if char.isdigit())
                group_name = modpack_groups_name(file_name, pmp)

                new_option = context.scene.modpack_group_options.add()
                new_option.group_value = int(number(file_name))
                new_option.group_name = group_name  
                new_option.group_description = file_name
    
def modpack_groups_name(file_name, pmp):
    
    with pmp.open(file_name) as file:
        file_contents = json.load(file)
        
        try:
            
            group_json = PenumbraGroups(**file_contents)
            return group_json.Name

        except Exception as e:
            print(f"{file_name} has an unknown json entry.")
            return f"{file_name[10:-4]}*"        

@dataclass
class MetaManip:
    Entry: Union[int, float, dict] = None
    #EQDP, EQP, Est
    Gender: str = None
    Race: str = None
    SetID: str = None
    Slot: str = None
    #Rsp
    SubRace: str = None
    Attribute: str = None
    #GlobalEqp
    Type: str = None
    Condition: str = None
    #Imc
    ObjectType: str = None
    PrimaryId: int = None
    SecondaryId: int = None
    Variant: int = None
    EquipSlot: str = None
    BodySlot: str = None

@dataclass
class PenumbraManipulations:
    Type: str = ""
    Manipulation: List[MetaManip] = None
    
    def __post_init__(self):
        self.Manipulation = MetaManip(self.Manipulation)

@dataclass
class ImcDefaultEntry:
    MaterialId: int = 0
    DecalId: int = 0
    VfxId: int = 0
    MaterialAnimationId: int = 0
    AttributeAndSound: int = 0
    AttributeMask: int = 0
    SoundId: int = 0

@dataclass
class ImcIdentifier:
    ObjectType: str = ""
    PrimaryId: int = 0
    SecondaryId: int = 0
    Variant: int = 0
    EquipSlot: str = ""
    BodySlot: str = ""

@dataclass
class GroupOptions:
    Files: Dict[str, str] = None
    FileSwaps: Dict[str, str] = None
    Manipulations: List[PenumbraManipulations] = None
    Priority: int = 0
    AttributeMask: int = None
    Name: str = ""
    Description: str = ""
    Image: str = ""

    def __post_init__(self):
        if self.Manipulations != None:
            self.Manipulations = [PenumbraManipulations(**manip) for manip in self.Manipulations]
        
@dataclass
class PenumbraGroups:
    Version: int = 0
    DefaultEntry: ImcDefaultEntry = None
    Identifier: ImcIdentifier = None
    AllVariants: bool = None
    OnlyAttributes: bool = None
    Name: str = ""
    Description: str = ""
    Priority: int = 0
    Image: str = ""
    Page: int = 0
    Type: str = None
    DefaultSettings: int = 0
    Options: List[GroupOptions] = None
    Manipulations: List[PenumbraManipulations] = None

    def __post_init__(self):
        if self.Options != None:
            self.Options = [GroupOptions(**option) for option in self.Options]
        elif self.Manipulations != None:
            self.Manipulations = [PenumbraManipulations(**manip) for manip in self.Manipulations]
        

    def to_json(self):
        return json.dumps(self.remove_none(asdict(self)), indent=4)
    
    def remove_none(self, obj):
        if isinstance(obj, dict):
            return {k: self.remove_none(v) for k, v in obj.items() if v is not None}
        
        elif isinstance(obj, list):
            return [self.remove_none(i) for i in obj if i is not None]
        
        return obj         


@dataclass
class PenumbraMeta:
    FileVersion: int = 3
    Name: str = ""
    Author: str = ""
    Description: str = ""
    Image: str = ""
    Version: str = ""
    Website: str = ""
    ModTags: list = field(default_factory=list)
    Description: str = ""

    def to_json(self):
        return json.dumps(asdict(self), indent=4)
    
    
