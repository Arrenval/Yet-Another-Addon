import os
import re
import bpy
import json
import shutil
import sqlite3
import subprocess

from typing             import Dict, List
from pathlib            import Path
from functools          import partial
from datetime           import datetime
from bpy.types          import Operator
from bpy.props          import StringProperty, IntProperty, BoolProperty
from dataclasses        import dataclass, field
from ..util.props       import get_modpack_groups, modpack_data, modpack_group_data, CombiningOptions, CombiningFinal, CorrectionEntry, PMPShapeKeys
from ..util.penumbra    import ModGroups, ModMeta
from zipfile            import ZipFile, ZIP_DEFLATED

def sanitise_path(path:str) -> str:
        invalid = '<>:"/\|?*'

        for char in invalid:
            path = path.replace(char, '')
        
        if path[-1] == " ":
            path = path[0:-1]
            
        return path

class ModpackDirSelector(Operator):
    bl_idname = "ya.modpack_dir_selector"
    bl_label = "Select Folder"
    bl_description = "Select file or directory. Hold Alt to open the folder"
    
    directory: StringProperty() # type: ignore
    category: StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: bpy.props.StringProperty(
        subtype="DIR_PATH",
        options={'HIDDEN'}) # type: ignore

    def invoke(self, context, event):
        actual_dir = Path(getattr(context.scene.file_props, f"{self.category}_directory", ""))     

        if event.alt and event.type == "LEFTMOUSE" and actual_dir.is_dir():
            os.startfile(actual_dir)
        elif event.type == "LEFTMOUSE":
            context.window_manager.fileselect_add(self)

        else:
             self.report({"ERROR"}, "Not a directory!")
    
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        actual_dir_prop = f"{self.category}_directory"
        display_dir_prop = f"{self.category}_display_directory"
        selected_file = Path(self.directory)  

        if selected_file.is_dir():
            setattr(context.scene.file_props, actual_dir_prop, str(selected_file))
            setattr(context.scene.file_props, display_dir_prop, str(Path(*selected_file.parts[-3:])))
            self.report({"INFO"}, f"Directory selected: {selected_file}")
        
        else:
            self.report({"ERROR"}, "Not a valid path!")
        
        return {'FINISHED'}

class ConsoleToolsDirectory(Operator):
    bl_idname = "ya.consoletools_dir"
    bl_label = "Select File"
    bl_description = "Use this to manually find the TexTools directory and select ConsoleTools.exe. Hold Alt to open the TexTools folder if already found"
    
    filepath: StringProperty() # type: ignore
    filter_glob: bpy.props.StringProperty(
        default='*.exe',
        options={'HIDDEN'}) # type: ignore

    def invoke(self, context, event):
        textools = context.scene.file_props.textools_directory

        if event.alt and os.path.exists(textools):
            os.startfile(textools)

        elif event.type == 'LEFTMOUSE':
            context.window_manager.fileselect_add(self)

        else:
             self.report({'ERROR'}, "Not a directory!")
    
        return {'RUNNING_MODAL'}

    def execute(self, context):
        selected_file = Path(self.filepath)

        if selected_file.exists() and selected_file.name == "ConsoleTools.exe":
            textools_folder = str(selected_file.parent)
            context.scene.file_props.textools_directory = textools_folder
            context.scene.file_props.consoletools_status = "ConsoleTools Ready!"
            self.report({'INFO'}, f"Directory selected: {textools_folder}")
        
        else:
            self.report({'ERROR'}, "Not a valid ConsoleTools.exe!")
        
        return {'FINISHED'}
    
class PMPSelector(Operator):
    bl_idname = "ya.pmp_selector"
    bl_label = "Select Modpack"
    bl_description = "Select a modpack. If selected, hold Alt to open the folder, hold Shift to open modpack"
    
    filepath: StringProperty() # type: ignore
    category: StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: bpy.props.StringProperty(
        default='*.pmp',
        options={'HIDDEN'}) # type: ignore

    def invoke(self, context, event):
        actual_file = Path(context.scene.file_props.loadmodpack_directory) 

        if event.alt and event.type == "LEFTMOUSE" and actual_file.is_file():
            actual_dir = actual_file.parent

            os.startfile(str(actual_dir))

        elif event.shift and event.type == "LEFTMOUSE" and actual_file.is_file():
            os.startfile(str(actual_file))

        elif event.type == "LEFTMOUSE":
            context.window_manager.fileselect_add(self)

        else:
             self.report({"ERROR"}, "Not a valid modpack!")
    
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        selected_file = Path(self.filepath)
        try:
            current_option = int(context.scene.file_props.modpack_groups) + 1
        except:
            pass
        if selected_file.exists() and selected_file.suffix == ".pmp":
            context.scene.file_props.loadmodpack_directory = str(selected_file) 
            context.scene.file_props.loadmodpack_display_directory = selected_file.stem
            self.report({'INFO'}, f"{selected_file.stem} selected!")
            try:
                if current_option > len(context.scene.pmp_group_options):
                    context.scene.file_props.modpack_groups = "0"
            except:
                pass
        
        else:
            self.report({'ERROR'}, "Not a valid modpack!")
        
        return {'FINISHED'}
    
class CopyToFBX(Operator):
    bl_idname = "ya.directory_copy"
    bl_label = "Copy Path"
    bl_description = "Copies the export directory to your modpack directory. This should be where your FBX files are located"

    def execute(self, context):
        export_dir = Path(context.scene.file_props.export_directory)
        context.scene.file_props.savemodpack_directory = str(export_dir)
        context.scene.file_props.savemodpack_display_directory = str(Path(*export_dir.parts[-3:]))
        return {'FINISHED'}

class ConsoleTools(Operator):
    bl_idname = "ya.file_console_tools"
    bl_label = "Modpacker"
    bl_description = "Checks for a valid TexTools install with ConsoleTools"

    def execute(self, context):
        consoletools, textools = self.console_tools_location(context)

        if os.path.exists(consoletools):
            context.scene.file_props.textools_directory = textools
            context.scene.file_props.consoletools_status = "ConsoleTools Ready!"
        else:
            context.scene.file_props.textools_directory = ""
            context.scene.file_props.consoletools_status = "Not Found. Click Folder."
        
        return {"FINISHED"}
    
    def console_tools_location(self, context) -> tuple[str, str]:
        import winreg
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

        textools_install = Path(textools_install.strip('"'))
        consoletools = textools_install / "FFXIV_TexTools" / "ConsoleTools.exe"
        textools_folder = consoletools.parent
        
        return str(consoletools), str(textools_folder)

class GamepathCategory(Operator):
    bl_idname = "ya.gamepath_category"
    bl_label = "Modpacker"
    bl_description = "Changes gamepath category"

    category: StringProperty() # type: ignore

    def execute(self, context):
        gamepath: str = bpy.context.scene.file_props.game_model_path
        gamepath_split      = gamepath.split("_")
        category_split      = gamepath_split[-1].split(".")
        category_split[0]   = self.category
        gamepath_split[-1]  = ".".join(category_split)

        context.scene.file_props.game_model_path = "_".join(gamepath_split)
        bpy.context.view_layer.update()
        return {'FINISHED'}

class ShapeKeyOptions(Operator):
    bl_idname = "ya.shape_key_options"
    bl_label = "Shp"
    bl_description = ""

    add: BoolProperty() # type: ignore
    category: StringProperty() # type: ignore
    preset: StringProperty() # type: ignore
    option_idx: IntProperty() # type: ignore
    shp_idx: IntProperty() # type: ignore

    @classmethod
    def description(cls, context, properties):
        if properties.category == "OPTION":
            if properties.add == True:
                return "Add toggleable option"
            else:
                return "Remove option"
        elif properties.category == "SHAPE_KEY" or properties.category == "CORRECTION":
            if properties.add == True:
                return "Add shape key entry"
            else:
                return "Remove shape key entry"
        elif properties.category == "RESET":
            return "Remove all options/entries"
        elif properties.category == "PRESET":
            return "Add selected preset"

        
    def execute(self, context):
        scene = context.scene
        self.props = scene.file_props
        self.combining_options = scene.pmp_combining_options
        self.combined_options = scene.pmp_combining_final
        self.corrections = scene.pmp_correction_entries
        self.correction_selection:str = self.props.shape_correction
        
        if self.category == "OPTION":
            self.change_options(context)

        elif self.category == "SHAPE_KEY":
            self.change_shape_keys(context)

        elif self.category == "CORRECTION":
            self.change_corrections(context)
        
        elif self.category == "PRESET":
            self.set_preset(context)
        
        elif self.category == "RESET":
            self.combining_options.clear()
            self.corrections.clear()

        self.calculate_final_options(context)

        return {'FINISHED'}
    
    def change_options(self, context) -> None:
        if self.add:
            if any(self.props.shape_option_name in option.name for option in self.combining_options):
                self.report({'ERROR'}, "Option already exists.")
                return {'CANCELLED'} 
            new_option = self.combining_options.add()
            new_option.name = self.props.shape_option_name
        else:
            temp_options = []
            for index, option in enumerate(self.combining_options):
                temp_entries = []
                if index == self.option_idx:
                    continue
                for entry in option.entries:
                    temp_entries.append((entry.slot, entry.modelid, entry.condition, entry.shape))
                temp_options.append((option.name, temp_entries))
            self.combining_options.clear()
            for option, entries in temp_options:
                new_option = self.combining_options.add()
                new_option.name = option
                for entry in entries:
                    new_shape = new_option.entries.add()
                    new_shape.slot = entry[0]
                    new_shape.modelid = entry[1]
                    new_shape.condition = entry[2]
                    new_shape.shape = entry[3]
    
    def change_shape_keys(self,context) -> None:
        if self.add:
            new_shape = self.combining_options[self.option_idx].entries.add()
            new_shape.modelid = self.get_model_id_from_path(context)
        else:
            temp_shp = []
            for index, shp in enumerate(self.combining_options[self.option_idx].entries):
                if index == self.shp_idx:
                    continue
                temp_shp.append((shp.slot, shp.modelid, shp.condition, shp.shape))
            self.combining_options[self.option_idx].entries.clear()
            for shp in temp_shp:
                new_shape = self.combining_options[self.option_idx].entries.add()
                new_shape.slot = shp[0]
                new_shape.modelid = shp[1]
                new_shape.condition = shp[2]
                new_shape.shape = shp[3]

    def change_corrections(self, context) -> None:
        if self.add:
            if self.correction_selection == "None":
                    self.report({'ERROR'}, "Please select a valid combination.")
                    return {'CANCELLED'} 
            add_corrections = self.corrections.add()
            add_corrections.name = self.correction_selection
            add_corrections.entry.modelid = self.get_model_id_from_path(context)
            total_options = [option.name for option in self.combining_options]
            idx_list = []
            split = self.correction_selection.replace("_", " ").split("/")

            for option in split:
                idx = total_options.index(option)
                idx_list.append(idx)
            for idx in idx_list:
                item = add_corrections.option_idx.add()
                item.value = idx
        else:
            temp_corrections = []
            for index, option in enumerate(self.corrections):
                temp_idx = []
                if index == self.shp_idx:
                    continue
                for entry in option.option_idx:
                    temp_idx.append(entry)
                temp_corrections.append(((option.name), (option.entry.slot, option.entry.modelid, option.entry.condition, option.entry.shape), temp_idx))
            self.corrections.clear()
            for name, entry, temp_idx in temp_corrections:
                new_option = self.corrections.add()
                new_shape = new_option.entry
            
                new_option.name = name
                new_shape.slot = entry[0]
                new_shape.modelid = entry[1]
                new_shape.condition = entry[2]
                new_shape.shape = entry[3]

                for idx in temp_idx:
                    new_idx = new_option.option_idx.add()
                    new_idx.value = idx.value

    def calculate_final_options(self, context) -> None:
        total_options = [option.name for option in self.combining_options]
        combinations = ["None"]
    
        for entry in total_options:
            new_combinations = []
            for combo in combinations:
                if combo == "None":
                    new_combinations.append(entry)
                else:
                    new_combinations.append(f"{combo} + {entry}")
            
            combinations.extend(new_combinations)

        self.combined_options.clear()
        for combo in combinations:
            idx_list = []
            add_combined_options = self.combined_options.add()
            add_combined_options.name = combo

            split_combo = combo.split(" + ")
            for option in split_combo:
                if option == "None":
                    continue
                idx = total_options.index(option)
                idx_list.append(idx)
            for idx in idx_list:
                item = add_combined_options.option_idx.add()
                item.value = idx
            for index, correction in enumerate(self.corrections):
                corr_idx = []
                for option_idx in correction.option_idx:
                    corr_idx.append(option_idx.value)
                if set(corr_idx).issubset(set(idx_list)):
                    add_corr_idx = add_combined_options.corr_idx.add()
                    add_corr_idx.value = index

    def get_model_id_from_path(self, context) -> None:
        path = str(context.scene.file_props.game_model_path)
        pattern = "e\d+"
        match = re.search(pattern, path)

        if match:
            return int(match.group()[1:])
        else:
            return 0
    
    def set_preset(self, context) -> None:
        model_id = self.get_model_id_from_path(context)
        prefix = "shpx_"
        
        slot, options, corrections = self.get_preset(context, self.preset)

        idx = len(self.combining_options)
        for option, key_data in options.items():
            new_option = self.combining_options.add()
            new_option.name = option

            for entries in key_data:
                new_shape = self.combining_options[idx].entries.add()
                new_shape.slot = slot
                new_shape.modelid = model_id
                new_shape.condition = entries["Conditional"]
                new_shape.shape = prefix + entries["Shape"]
            idx +=1
        for correction in corrections:
            add_corrections = self.corrections.add()
            add_corrections.name = "Alt Hips/Soft Butt"
            add_corrections.entry.slot = slot
            add_corrections.entry.modelid = model_id
            add_corrections.entry.condition = correction["Conditional"]
            add_corrections.entry.shape = prefix + correction["Shape"]

            total_options = [option.name for option in self.combining_options]

            idx_list = []
            split = "Alt Hips/Soft Butt".split("/")
            for option in split:
                idx = total_options.index(option)
                idx_list.append(idx)
            for idx in idx_list:
                item = add_corrections.option_idx.add()
                item.value = idx

    def get_preset(self, context, preset):
        slot = "Legs"

        options = {"Alt Hips":  [{"Shape": "yab_hip", "Conditional": "None"},
                                 {"Shape": "rue_hip", "Conditional": "None"}],

                   "Soft Butt": [{"Shape": "softbutt", "Conditional": "None"},
                                 {"Shape": "yabc_waist", "Conditional": "Waist"}]}
        
        corrections = [{"Shape": "yabc_hipsoft", "Conditional": "None"},
                       {"Shape": "ruec_hipsoft", "Conditional": "None"}]
        
        return slot, options, corrections

@dataclass  
class UserInput:
    selection      :str  = ""
    mdl_game       :str  = ""
    update         :bool = False
    model          :bool = True
    pmp            :Path = ""
    fbx            :Path = ""
    temp           :Path = ""
    mdl_folder     :Path = ""
    subfolder      :Path = ""

    update_group   :str  = ""
    pmp_name       :str  = ""
    group_type     :str  = ""
    load_mod_ver   :str  = ""

    new_page       :int  = 0
    group_new_name :str  = ""
    group_old_name :str  = ""

    new_meta       :dict = field(default_factory=dict)
    
    combining_options : List[CombiningOptions] = None
    combining_entries : List[CombiningFinal]   = None
    correction_entries: List[CorrectionEntry]  = None


    def __post_init__(self):
        props               = bpy.context.scene.file_props
        scene               = bpy.context.scene
        subfolder           = props.fbx_subfolder
        time                = datetime.now().strftime("%H%M%S")

        self.selection      = props.modpack_groups
        self.mdl_game       = props.game_model_path
        self.update         = props.button_modpack_replace
        if subfolder != "None":
            self.subfolder  = subfolder
        self.fbx            = Path(props.savemodpack_directory)
        self.mdl_folder     = self.fbx / self.subfolder / "MDL"
        self.temp           = self.fbx / f"temp_pmp_{time}"
        self.group_new_name = props.modpack_rename_group
        self.group_type     = props.mod_group_type
        self.load_mod_ver   = props.loadmodpack_version
        self.new_page       = 0 if props.modpack_page == "" else int(props.modpack_page)
        self.model          = props.button_modpack_model

        if self.update:
            self.pmp_name = props.loadmodpack_display_directory
            self.pmp      = Path(props.loadmodpack_directory)
        else:
            self.pmp_name = props.new_mod_name
            self.new_meta = {
                "Name"   : self.pmp_name,
                "Author" : props.author_name,
                "Version": props.new_mod_version
            }
            
        for group in get_modpack_groups():
            if self.selection == group[0]:
                    self.group_old_name, self.update_group = group[1], group[2]

        if not self.model:
            self.combining_options = scene.pmp_combining_options
            self.combining_entries = scene.pmp_combining_final
            self.correction_entries = scene.pmp_correction_entries
            
class Modpacker(Operator):
    bl_idname = "ya.file_modpacker"
    bl_label = "Modpacker"

    preset: StringProperty()  # type: ignore # convert_pack, pack, convert are valid presets
    
    @classmethod
    def description(cls, context, properties):
        if properties.preset == "convert_pack":
            return "Converts FBX to MDL and packages MDLs into a Penumbra Modpack"
        if properties.preset == "convert":
            return "Converts FBX to MDL"
        else:
            return "Packages MDLs into a Penumbra Modpack"

    def execute(self, context):
        props                    = context.scene.file_props
        self.pmp                 = Path(props.loadmodpack_directory)
        self.update: bool        = props.button_modpack_replace
        self.mdl_game: str       = props.game_model_path
        self.fbx                 = Path(props.savemodpack_directory)
        self.pmp_name: str       = props.new_mod_name
        self.group_new_name: str = props.modpack_rename_group
        self.author: str         = props.author_name
        self.console: str        = props.consoletools_status
        
        if not self.pmp.is_file() and self.update:
            self.report({'ERROR'}, "Please select a modpack.")
            return {'CANCELLED'} 

        elif not self.mdl_game:
            self.report({'ERROR'}, "Please input a path to an FFXIV model")
            return {'CANCELLED'}
        
        elif not self.mdl_game.startswith("chara") or not self.mdl_game.endswith("mdl"):
            self.report({'ERROR'}, "Verify that the model is an actual FFXIV path")
            return {'CANCELLED'}
        
        elif not self.fbx.is_dir():
            self.report({'ERROR'}, "Please select an FBX directory")
            return {'CANCELLED'}
        
        if not self.update and self.preset != "convert":
            if not self.pmp_name:
                self.report({'ERROR'}, "Please enter a mod name")
                return {'CANCELLED'}
            elif not self.author:
                self.report({'ERROR'}, "Please enter an author.")
                return {'CANCELLED'}
            elif not self.group_new_name:
                self.report({'ERROR'}, "Please enter a group name.")
                return {'CANCELLED'}
            
        user_input = UserInput()
        
        mdl_status = None
        if self.preset != "pack":
            if self.console != "ConsoleTools Ready!":
                self.report({'ERROR'}, "Verify that ConsoleTools is ready.")
                return {'CANCELLED'} 
            context.scene.file_props.modpack_progress = "Converting FBX to MDL..."
            mdl_status = self.mdl_converter(context, user_input) 

        if self.update and self.preset != "convert":
            if user_input.selection == "0" and not self.group_new_name:
                self.report({'ERROR'}, "Please enter a group name.")
                return {'CANCELLED'}
            
            mod_data, mod_meta = self.current_mod_data(user_input.update, user_input.pmp)
        else:
            mod_data, mod_meta = {}, {}
        
        callback = partial(Modpacker.create_modpack, context, user_input, mod_data, mod_meta, self.preset, mdl_status)
        bpy.app.timers.register(callback, first_interval=0.5)

        return {"FINISHED"}
   
    def current_mod_data(self, update:bool, pmp:Path) -> tuple[dict, ModMeta]:
        if not update or self.preset == "convert":
            return None
        current_mod_data = {}

        with ZipFile(pmp, "r") as archive:
            for file_name in sorted(archive.namelist()):
                if file_name.count('/') == 0 and file_name.startswith("group") and file_name.endswith(".json"):
                    group_data = modpack_group_data(file_name, archive, data="all")
                    
                    current_mod_data[file_name] = group_data 
            with archive.open("meta.json") as meta:
                meta_contents = json.load(meta)

                current_mod_meta = ModMeta.from_dict(meta_contents)
            
        
        return current_mod_data, current_mod_meta  
 
    def mdl_converter(self, context, user_input:UserInput) -> subprocess.Popen:
        blender_dir  = Path(bpy.app.binary_path).parent
        python_dir   = str([file for file in (blender_dir).glob("*/python/bin/python*")][0])
        script_dir   = Path(__file__).parent / "database.py"
        props_json   = user_input.fbx / user_input.subfolder / "MeshProperties.json"
        textools     = Path(context.scene.file_props.textools_directory)
        game_path    = str(user_input.mdl_game)
        model_props  = {}
        to_convert   = [file for file in (user_input.fbx / user_input.subfolder).glob("*.fbx") if file.is_file()]

        if props_json.is_file():
            with open(props_json, "r") as file:
                model_props = json.load(file)

        cmd_name = "MDL.cmd"
        commands = ["@echo off", f"cd /d {textools.drive}", f"cd {textools}", "echo Please don't close this window..."]

        Path.mkdir(user_input.fbx / user_input.subfolder / "MDL", exist_ok=True)
        cmd_path = user_input.mdl_folder / cmd_name

        cmds_added  = 0
        total_files = len(to_convert)
        for file in to_convert:
            commands.append(f"echo ({cmds_added + 1}/{total_files}) Converting: {file.stem}")
            source = str(user_input.fbx / user_input.subfolder / file.name)
            dest = str(user_input.mdl_folder / file.stem)
            
            if file.stem in model_props:
                commands.append("echo Writing model to database...")
                commands.append(rf"cd {textools}\converters\fbx")
                commands.append(f'converter.exe "{source}" >nul')
                commands.append("echo Updating model database tables...")
                commands.append(f'"{python_dir}" "{script_dir.resolve()}" "{textools}" "{file.stem}" "{props_json}" >nul')
                commands.append(f"cd {textools}")
                
                # Places all dbs in your export folder, uncomment for debugging and verifying output
                # source = str(user_input.fbx / user_input.subfolder / f"{file.stem}.db")
                # commands.append(rf'copy /y "{textools}\converters\fbx\result.db" "{source}" >nul')
                source = str(textools / "converters" / "fbx" / "result.db")

            commands.append("echo Finalising .mdl...")
            commands.append(f'ConsoleTools.exe /wrap "{source}" "{dest}.mdl" "{game_path}" >nul')

            cmds_added += 1
        
        commands.append("pause")

        with open(cmd_path, 'w') as file:
            for cmd in commands:
                file.write(f"{cmd}\n")

        mdl_status = subprocess.Popen([str(cmd_path)], 
                       creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        return mdl_status

    def create_modpack(context, user_input:UserInput, mod_data:Dict[str, ModGroups], mod_meta:ModMeta, preset:str, mdl_status:subprocess.Popen) -> int | None:
        if mdl_status is not None and mdl_status.poll() != 0:
            return 0.5
        
        Path.unlink(user_input.mdl_folder / "MDL.cmd", missing_ok=True)
        if preset == "convert" and mdl_status.poll() == 0:
            context.scene.file_props.modpack_progress = f"Complete! ({datetime.now().strftime('%H:%M:%S')})"
            return None
        
        context.scene.file_props.modpack_progress = "Creating modpack..." 

        to_pack = [file for file in user_input.mdl_folder.glob(f'*.mdl') if file.is_file()]
        if not to_pack:
            context.scene.file_props.modpack_progress = "No MDLs to pack..."
            return None
        to_pack = Modpacker.yet_another_sort(to_pack)

        Path.mkdir(user_input.temp, exist_ok=True)

        if mod_data:
            Modpacker.rolling_backup(user_input)
            with ZipFile(user_input.pmp, "r") as pmp:
                pmp.extractall(user_input.temp)
            Modpacker.update_mod(user_input, mod_data, to_pack, mod_meta)    
        else:
            Modpacker.new_mod(user_input, to_pack)
        
        with ZipFile(user_input.fbx / f"{user_input.pmp_name}.pmp", 'w', ZIP_DEFLATED) as pmp:
            for root, dir, files in os.walk(user_input.temp):
                for file in files:
                    file_path = os.path.join(root, file)
                    pmp.write(file_path, os.path.relpath(file_path, user_input.temp))

        bpy.app.timers.register(partial(Modpacker.schedule_cleanup, user_input.temp), first_interval=0.1)

        try:
            current_option = int(context.scene.file_props.modpack_groups) + 1
        except:
            pass

        if (user_input.fbx / f"{user_input.pmp_name}.pmp").is_file():
            context.scene.file_props.loadmodpack_directory = str(user_input.fbx / f"{user_input.pmp_name}.pmp")
        else:
            modpack_data(context)
        try:
            if current_option > len(context.scene.pmp_group_options):
                    context.scene.file_props.modpack_groups = "0"
        except:
            pass
        context.scene.file_props.modpack_progress = f"Complete! ({datetime.now().strftime('%H:%M:%S')})"
        return None

    def yet_another_sort(items:list[Path]) -> list:
        ranking = {}
        final_sort = []
        
        for item in items:
            ranking[item] = 0
            if "Small" in item.stem:
                ranking[item] += 2
            if "Cupcake" in item.stem:
                ranking[item] += 2
            if "Medium" in item.stem:
                ranking[item] += 3
            if "Teardrop" in item.stem:
                ranking[item] += 3
            if "Sayonara" in item.stem:
                ranking[item] += 4
            if "Tsukareta" in item.stem:
                ranking[item] += 5
            if "Tsukareta+" in item.stem:
                ranking[item] += 1
            if "Mini" in item.stem:
                ranking[item] += 8
            if "Large" in item.stem:
                ranking[item] += 9
            if "Omoi" in item.stem:
                ranking[item] += 10
            if "Sugoi" in item.stem:
                ranking[item] += 1
            if "Uranus" in item.stem:
                ranking[item] += 12
            if "Skull" in item.stem:
                ranking[item] += 1
            if "Yanilla" in item.stem:
                ranking[item] += 2
            if "Lava" in item.stem:
                ranking[item] += 3
            if "Buff" in item.stem:
                ranking[item] += 20
            if "Rue" in item.stem:
                ranking[item] += 42
            if "Lava" in item.stem:
                ranking[item] += 420
            if "Masc" in item.stem:
                ranking[item] += 1337
            if "Yiggle" in item.stem:
                ranking[item] += 69*420
            if "Long" in item.stem:
                ranking[item] += 1
            if "Ballerina" in item.stem:
                ranking[item] += 2
            if "Stabbies" in item.stem:
                ranking[item] += 3

        sorted_rank = sorted(ranking.items(), key=lambda x: x[1])
        
        for tuples in sorted_rank:
            final_sort.append(tuples[0])

        return final_sort

    def rolling_backup(user_input:UserInput) -> None:
        bpy.context.scene.file_props.modpack_progress = "Creating backup..."
        folder_bak = user_input.fbx / "BACKUP"
        time = datetime.now().strftime("%Y-%m-%d - %H%M%S")
        pmp_bak = folder_bak / f"{time}.pmp"
        
        Path.mkdir(folder_bak, exist_ok=True)

        existing_bak = sorted([file.name for file in folder_bak.glob("*.pmp") if file.is_file()], reverse=True)

        while len(existing_bak) >= 5:
            oldest_backup = existing_bak.pop()
            Path.unlink(folder_bak / oldest_backup)

        shutil.copy(user_input.pmp, pmp_bak)

    def new_mod(user_input:UserInput, to_pack:list[Path]) -> None:
        meta_content = ModMeta(**user_input.new_meta)
        group_data = Modpacker.get_group_data_template(user_input)

        with open(os.path.join(user_input.temp, "meta.json"), "w") as file:
                file.write(meta_content.to_json())

        default_mod = ModGroups()

        with open(os.path.join(user_input.temp, "default_mod.json"), "w") as file:
                file.write(default_mod.to_json())

        file_name = f"group_001_{user_input.group_new_name.lower()}.json"
        create_group = {file_name: (user_input.mdl_game, user_input.group_new_name, group_data)}
        Modpacker.write_group_json(user_input, to_pack, create_group, user_input.group_new_name)

        for file in to_pack:
            target_path = user_input.temp / sanitise_path(user_input.group_new_name) / sanitise_path(file.stem)   
            Path.mkdir(target_path, parents=True, exist_ok=True)
        
            shutil.copy(user_input.mdl_folder / sanitise_path(file.name), target_path / sanitise_path(file.name))

    def update_mod (user_input:UserInput, mod_data:Dict[str, ModGroups], to_pack:list[Path], mod_meta:ModMeta) -> None:
        group_dir = user_input.group_new_name if user_input.group_new_name else user_input.group_old_name
        group_data = Modpacker.get_group_data_template(user_input, mod_data)
        update_page = False
        
        if user_input.selection != "0":
            Path.unlink(user_input.temp / user_input.update_group)
            Modpacker.delete_orphans(user_input.temp, mod_data[user_input.update_group])
        else:
            group_data["Page"] = user_input.new_page
            update_page = True

        file_name, group_name = Modpacker.update_file_name(user_input, mod_data, update_page)
        create_group = {file_name: (user_input.mdl_game, group_name, group_data)}
        
        if user_input.update_group in mod_data:
                to_replace:ModGroups = mod_data[user_input.update_group]
        else:
            to_replace = ""
        
        Modpacker.write_group_json(user_input, to_pack, create_group, group_dir, to_replace)

        mod_meta.Version = user_input.load_mod_ver

        with open(user_input.temp / "meta.json", "w") as file:
                file.write(mod_meta.to_json())
        
        for file in to_pack:
            target_path = user_input.temp / sanitise_path(group_dir) / sanitise_path(file.stem)   
            Path.mkdir(target_path, parents=True, exist_ok=True)
        
            shutil.copy(user_input.mdl_folder / sanitise_path(file.name), target_path / sanitise_path(file.name))

    def get_group_data_template(user_input:UserInput, mod_data={}) -> dict:
        if mod_data and user_input.selection != "0":
            return {
            "Name": "",
            "Description": mod_data[user_input.update_group].Description,
            "Priority": mod_data[user_input.update_group].Priority,
            "Image": mod_data[user_input.update_group].Image,
            "Page": mod_data[user_input.update_group].Page,
            "Type": user_input.group_type,
            "DefaultSettings": mod_data[user_input.update_group].DefaultSettings,
            "Options": [],
            "Containers": []
            }
        
        else:
            return {
            "Name": user_input.group_new_name,
            "Description": "",
            "Priority": 0,
            "Image": "",
            "Page": 0,
            "Type": user_input.group_type,
            "DefaultSettings": 0,
            "Options": [],
            "Containers": []
            }

    def write_group_json(user_input:UserInput, to_pack:list[Path], create_group:dict, group_dir:str, to_replace:ModGroups="") -> None:

        def save_models():
            for file in to_pack:
                option_name = file.stem
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

                rel_path = f"{sanitise_path(group_dir)}\\{sanitise_path(option_name)}\\{sanitise_path(file.name)}"
                new_option["Files"] = {mdl_game: rel_path}
                new_option["Name"] = option_name
                    
                options.append(new_option)

        def save_shape_keys():
            for combi_option in user_input.combining_options:
                    options.append({"Name": combi_option.name, "Description": ""})
            for entry in user_input.combining_entries:
                manips = []
                for idx in entry.option_idx:
                    for option_entry in user_input.combining_options[idx.value].entries:
                        manip = {"Type": "Shp", "Manipulation": {}}
                        shape_key:PMPShapeKeys = option_entry
                        manip["Manipulation"]["Entry"] = True
                        manip["Manipulation"]["Slot"]  = shape_key.slot
                        manip["Manipulation"]["Id"]    = int(shape_key.modelid)
                        manip["Manipulation"]["Shape"] = shape_key.shape
                        manip["Manipulation"]["ConnectorCondition"] = None if shape_key.condition == "None" else shape_key.condition
                        manips.append(manip)
                for idx in entry.corr_idx:
                    manip = {"Type": "Shp", "Manipulation": {}}
                    shape_key:PMPShapeKeys = user_input.correction_entries[idx.value].entry
                    manip["Manipulation"]["Entry"] = True
                    manip["Manipulation"]["Slot"]  = shape_key.slot
                    manip["Manipulation"]["Id"]    = int(shape_key.modelid)
                    manip["Manipulation"]["Shape"] = shape_key.shape
                    manip["Manipulation"]["ConnectorCondition"] = None if shape_key.condition == "None" else shape_key.condition
                    manips.append(manip)

                containers.append({"Files": {}, "FileSwaps": {}, "Manipulations": manips})
        
        bpy.context.scene.file_props.modpack_progress = "Writing json..."
        for file_name, (mdl_game, group_name, group_data) in create_group.items():
            options = []
            containers = []
            
            none_option = {
                "Files": {},
                "FileSwaps": {},
                "Manipulations": [],
                "Priority": 0,
                "Name": "None",
                "Description": "",
                "Image": ""
                }
            
            if group_data["Type"] == "Single":
                options.append(none_option)
            
            if user_input.model:
                save_models()
            else:
                save_shape_keys()
                
            group_data["Options"] = options
            group_data["Name"] = group_name
            group_data["Containers"] = containers

            new_group = user_input.temp / sanitise_path(file_name)

            with open(new_group, "w") as file:
                file.write(ModGroups.from_dict(group_data).to_json())

    def update_file_name(user_input:UserInput, mod_data:Dict[str, ModGroups], update_page) -> tuple[str, str]:
        final_digits:str = ""

        if user_input.update_group:
            split_name = user_input.update_group.split("_")
            final_digits = split_name[1]  
        
        if update_page:
            page_match = False  
            for json, contents in mod_data.items():
                bak = json + ".bak"
                if contents.Page == user_input.new_page and not page_match:
                    page_match = True
                    parts = json.split("_")
                    final_digits = f"{parts[1]:03}"
                if page_match:
                    parts = json.split("_")
                    new_digits = int(parts[1]) + 1
                    parts[1] = f"{new_digits:03}"
                    new_json = "_".join(parts)
                    shutil.copy(user_input.temp / json, user_input.temp / new_json)
                    Path.unlink(user_input.temp / json)
                ## removes .bak files if there are any as their names won't match anymore
                try:
                    try:
                        Path.unlink(user_input.temp / bak)
                    except:
                        bak_parts = bak.split("_")
                        bak_start = "_".join(bak_parts[:2])
                        bak_end = "-".join(bak_parts[2:])
                        bak = bak_start + "_" + bak_end
                        Path.unlink(user_input.temp / bak)
                except:
                    continue


        if user_input.group_new_name:
                file_name = f"group_{final_digits}_{sanitise_path(user_input.group_new_name).lower()}.json"

                return file_name, user_input.group_new_name
        else:
            return user_input.update_group, user_input.group_old_name
   
    def check_duplicate_groups(user_input:UserInput, mod_data:Dict[str, ModGroups]) -> dict:
        bpy.context.scene.file_props.modpack_progress = "Checking for duplicate groups..."
        # Duplicate groups might use the same files, but on different items, typically Smallclothes/Emperor's.
        # This is to prevent breaking groups that use the same files. Will not catch similar groups. 
        relative_paths = []
        dupe_rel_paths = []
        duplicate_groups = {}
        
        for options in mod_data[user_input.update_group].Options:
            for gamepath, relpath in options.Files.items():
                relative_paths.append(relpath)
        for group in mod_data:
            dupe_mdl = set()
            file_contents = mod_data[group]
            if group != user_input.update_group:
                try:
                    for option in file_contents.Options:
                        for gamepath, relpath in option.Files.items():
                            if any(relpath in relative_paths for path in relative_paths):
                                dupe_rel_paths.append(relpath)
                                dupe_mdl.add(gamepath)
                except:
                    continue
        
            if sorted(dupe_rel_paths) == sorted(relative_paths) and len(dupe_mdl) == 1:
                duplicate_groups[group] = ("".join(dupe_mdl), file_contents.Name)
                dupe_rel_paths = []
            dupe_rel_paths = []
        return duplicate_groups

    def delete_orphans(temp_folder:Path, update_group:ModGroups) -> None:
        bpy.context.scene.file_props.modpack_progress = "Deleting orphans...." 
        for options in update_group.Options:
            if options.Files is None:
                continue
            for gamepath, relpath in options.Files.items():
                try:
                    absolute_path = os.path.join(temp_folder, relpath)
                    Path.unlink(absolute_path)
                    # print(f"Deleted file: {absolute_path}")
                except:
                    continue

        for dir in sorted(temp_folder.rglob("*"), reverse=True):
            if dir.is_dir():
                if not any(dir.iterdir()):
                    try: 
                        dir.rmdir() 
                        # print(f"Deleted empty directory: {dir}")
                    except:
                        continue

    def schedule_cleanup(temp_folder:Path) -> None:
        retries = 5
        def cleanup_attempt():
            nonlocal retries
            if retries != 0:
                try:
                    if temp_folder.is_dir():
                        shutil.rmtree(temp_folder)
                        return None
                except FileNotFoundError as e:
                    return None
                except PermissionError as e:
                    pass
            retries -= 1
            if retries > 0:
                return 5 - retries
            else:
                bpy.context.scene.file_props.modpack_progress = "Failed to delete temp folder..."
                return None
        cleanup_attempt()
        if retries == 0:
            return None
        return cleanup_attempt()

CLASSES = [
    ModpackDirSelector,
    ConsoleToolsDirectory,
    PMPSelector,
    CopyToFBX,
    GamepathCategory,
    ShapeKeyOptions,
    ConsoleTools,
    Modpacker
]