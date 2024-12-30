import os
import bpy
import json
import shutil

from typing             import Dict
from pathlib            import Path
from functools          import partial
from datetime           import datetime
from bpy.types          import Operator
from bpy.props          import StringProperty
from dataclasses        import dataclass, field
from ..util.props       import get_modpack_groups, modpack_data, modpack_group_data
from ..util.penumbra    import ModGroups, ModMeta
from zipfile            import ZipFile, ZIP_DEFLATED

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
    
@dataclass  
class UserInput:
    selection      :str  = ""
    mdl_game       :str  = ""
    update         :bool = False
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


    def __post_init__(self):
        props               = bpy.context.scene.file_props
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

    def __init__(self):
        props               = bpy.context.scene.file_props
        self.pmp            = Path(props.loadmodpack_directory)
        self.update         = props.button_modpack_replace
        self.mdl_game       = props.game_model_path
        self.fbx            = Path(props.savemodpack_directory)
        self.pmp_name       = props.new_mod_name
        self.group_new_name = props.modpack_rename_group
        self.author         = props.author_name
        self.console        = props.consoletools_status
        

    def execute(self, context):
        
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
        
        if self.preset != "pack":
            if self.console != "ConsoleTools Ready!":
                self.report({'ERROR'}, "Verify that ConsoleTools is ready.")
                return {'CANCELLED'} 
            context.scene.file_props.modpack_progress = "Converting FBX to MDL..."
            self.fbx_to_mdl(context, user_input) 

        if self.update and self.preset != "convert":
            if user_input.selection == "0" and not self.group_new_name:
                self.report({'ERROR'}, "Please enter a group name.")
                return {'CANCELLED'}
            
            mod_data, mod_meta = self.current_mod_data(user_input.update, user_input.pmp)
        else:
            mod_data, mod_meta = {}, {}
        
        callback = partial(Modpacker.create_modpack, context, user_input, mod_data, mod_meta, self.preset)
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

                current_mod_meta = ModMeta(**meta_contents)
            
        
        return current_mod_data, current_mod_meta  
 
    def fbx_to_mdl(self, context, user_input:UserInput) -> None:
        textools = Path(context.scene.file_props.textools_directory)
        to_convert = [file for file in (user_input.fbx / user_input.subfolder).glob(f'*.fbx') if file.is_file()]

        cmd_name = "FBXtoMDL.cmd"
        sys_drive = textools.drive
        commands = ["@echo off", f"cd /d {sys_drive}", f"cd {textools}", "echo Please don't close this window..."]

        cmd_path = user_input.fbx / cmd_name
        Path.mkdir(user_input.fbx / user_input.subfolder / "MDL", exist_ok=True)

        cmds_added = 0
        total_files = len(to_convert)
        for file in to_convert:
            files_left = total_files - cmds_added    
            fbx_to_mdl = f'"{user_input.fbx / user_input.subfolder / file.name}" "{user_input.mdl_folder / file.stem}.mdl" "{user_input.mdl_game}"'
            
            # if cmds_added % 5 == 0 and cmds_added == 0:
            #     commands.append(f"echo {files_left} files to convert...")
            
            # elif cmds_added % 5 == 0:
            #     commands.append(f"echo {files_left} files left...")
            
            commands.append(f"echo ({cmds_added + 1}/{total_files}) Converting: {file.stem}")
            commands.append(f"ConsoleTools.exe /wrap {fbx_to_mdl} >nul")
            cmds_added += 1
        
        commands.append("ping 127.0.0.1 -n 2 >nul")
        commands.append('start "" /min cmd /c "del \"%~f0\""')
        commands.append("exit")

        with open(cmd_path, 'w') as file:
            for cmd in commands:
                file.write(f"{cmd}\n")

        os.startfile(cmd_path)    

    def create_modpack(context, user_input:UserInput, mod_data:Dict[str, ModGroups], mod_meta:ModMeta, preset:str) -> int | None:
        is_cmd = [file.name for file in user_input.fbx.glob(f'FBXtoMDL.cmd') if file.is_file()]
       
       #checks for the .cmd to see if the conversion process is over
        if is_cmd:
            return 0.5 
        if not is_cmd and preset == "convert":
            context.scene.file_props.modpack_progress = "Complete!"
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
        modpack_data(context)
        try:
            if current_option > len(context.scene.pmp_group_options):
                    context.scene.file_props.modpack_groups = "0"
        except:
            pass
        context.scene.file_props.modpack_progress = "Complete!"
        return None

    def yet_another_sort(items:list[Path]) -> list:
        ranking = {}
        final_sort = []
        
        for item in items:
            ranking[item] = 0
            if "Small" in item.stem:
                ranking[item] += 2
            if "Medium" in item.stem:
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
            if "Skull" in item.stem:
                ranking[item] += 1
            if "Soft" in item.stem:
                ranking[item] += 4
            if "Buff" in item.stem:
                ranking[item] += 20
            if "Rue" in item.stem:
                ranking[item] += 42
            if "Yiggle" in item.stem:
                ranking[item] += 69

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
            target_path = user_input.temp / user_input.group_new_name / file.stem   
            Path.mkdir(target_path, parents=True, exist_ok=True)
        
            shutil.copy(user_input.mdl_folder / file.name, target_path / file.name)

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
            target_path = user_input.temp / group_dir / file.stem   
            Path.mkdir(target_path, parents=True, exist_ok=True)
        
            shutil.copy(user_input.mdl_folder / file.name, target_path / file.name)

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
            }

    def write_group_json(user_input:UserInput, to_pack:list[Path], create_group:dict, group_dir:str, to_replace:ModGroups="") -> None:
        bpy.context.scene.file_props.modpack_progress = "Writing json..."
        for file_name, (mdl_game, group_name, group_data) in create_group.items():
            
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

                rel_path = f"{group_dir}\\{option_name}\\{file.name}"
                new_option["Files"] = {mdl_game: rel_path}
                new_option["Name"] = option_name
                    
                options.append(new_option)

            group_data["Options"] = options
            group_data["Name"] = group_name

            new_group = user_input.temp / file_name


            with open(new_group, "w") as file:
                file.write(ModGroups(**group_data).to_json())

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
                file_name = f"group_{final_digits}_{user_input.group_new_name.lower()}.json"

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
    ConsoleTools,
    Modpacker
]