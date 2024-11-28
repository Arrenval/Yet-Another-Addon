import os
import bpy
import json
import winreg
import shutil
import zipfile

from pathlib       import Path
from functools     import partial
from datetime      import datetime
from bpy.types     import Operator
from bpy.props     import StringProperty
from .penumbra     import ModGroups, ModMeta


def get_modpack_groups(context):
        return [(str(option.group_value), option.group_name, option.group_description) for option in context.scene.pmp_group_options]

def modpack_data(context):
    scene = context.scene
    scene.pmp_group_options.clear()
    modpack = scene.pmp_props.loadmodpack_directory

    new_option = scene.pmp_group_options.add()
    new_option.group_value = int(0)
    new_option.group_name = "Create New Group"  
    new_option.group_description = ""

    if os.path.exists(modpack):
        with zipfile.ZipFile(modpack, "r") as pmp:
            for file_name in pmp.namelist():
                if file_name.count('/') == 0 and file_name.startswith("group") and not file_name.endswith("bak"):
                    number = lambda name: ''.join(char for char in name if char.isdigit())
                    group_name = modpack_group_data(file_name, pmp, data="name")

                    new_option = context.scene.pmp_group_options.add()
                    new_option.group_value = int(number(file_name))
                    new_option.group_name = group_name
                    new_option.group_description = file_name
 
            with pmp.open("meta.json") as meta:
                meta_contents = json.load(meta)

                mod_meta = ModMeta(**meta_contents)
                scene.pmp_props.loadmodpack_version = mod_meta.Version
                scene.pmp_props.loadmodpack_author = mod_meta.Author
    
def modpack_group_data(file_name, pmp, data):
    try:
        with pmp.open(file_name) as file:
            file_contents = json.load(file)
                      
            group_data = ModGroups(**file_contents)

            if data == "name":
                return group_data.Name
            if data == "all":
                return group_data

    except Exception as e:
        print(f"ERROR: {file_name[10:-4]}")
        return f"ERROR: {file_name[10:-4]}"    
  
def sanitise_path(path:str):
        return path.lower().replace(" - ", "_").replace(" ", "")


class ModpackDirSelector(Operator):
    bl_idname = "ya.modpack_dir_selector"
    bl_label = "Select Folder"
    bl_description = "Select file or directory. Hold Alt to open the folder"
    
    directory: StringProperty() # type: ignore
    category: StringProperty() # type: ignore

    def invoke(self, context, event):
        actual_dir = Path(getattr(context.scene.pmp_props, f"{self.category}_directory", ""))     

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
            setattr(context.scene.pmp_props, actual_dir_prop, str(selected_file))
            setattr(context.scene.pmp_props, display_dir_prop, str(Path(*selected_file.parts[-3:])))
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
        textools = context.scene.pmp_props.textools_directory

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
            textools_folder = selected_file.parent
            context.scene.pmp_props.textools_directory = textools_folder
            context.scene.pmp_props.consoletools_status = "ConsoleTools Ready!"
            self.report({'INFO'}, f"Directory selected: {textools_folder}")
        
        else:
            self.report({'ERROR'}, "Not a valid ConsoleTools.exe!")
        
        return {'FINISHED'}
    

class PMPSelector(Operator):
    bl_idname = "ya.pmp_selector"
    bl_label = "Select Modpack"
    bl_description = "Select a modpack. If selected, hold Alt to open the folder, hold Shift to open modpack"
    
    filepath: StringProperty() # type: ignore
    category: StringProperty() # type: ignore

    def invoke(self, context, event):
        actual_file = Path(context.scene.pmp_props.loadmodpack_directory) 

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

        if selected_file.exists() and selected_file.suffix == ".pmp":
            
            context.scene.pmp_props.loadmodpack_directory = str(selected_file) 
            context.scene.pmp_props.loadmodpack_display_directory = selected_file.stem
            self.report({'INFO'}, f"{selected_file.stem} selected!")
        
        else:
            self.report({'ERROR'}, "Not a valid modpack!")
        
        return {'FINISHED'}
    

class CopyToFBX(Operator):
    bl_idname = "ya.directory_copy"
    bl_label = "Copy Path"
    bl_description = "Copies the export directory to your modpack directory. This should be where your FBX files are located"

    def execute(self, context):
        export_dir = Path(context.scene.devkit_props.export_directory)
        context.scene.pmp_props.savemodpack_directory = str(export_dir)
        context.scene.pmp_props.savemodpack_display_directory = str(Path(*export_dir.parts[-3:]))
    
        return {'FINISHED'}


class ConsoleTools(Operator):
    bl_idname = "ya.file_console_tools"
    bl_label = "Modpacker"
    bl_description = "Checks for a valid TexTools install with ConsoleTools"
    bl_options = {'UNDO'}

    def execute(self, context):
        consoletools, textools = self.console_tools_location(context)

        if os.path.exists(consoletools):
            context.scene.pmp_props.textools_directory = textools
            context.scene.pmp_props.consoletools_status = "ConsoleTools Ready!"
        else:
            context.scene.pmp_props.textools_directory = ""
            context.scene.pmp_props.consoletools_status = "Not Found. Click Folder."
        
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

        textools_install = Path(textools_install.strip('"'))
        consoletools = textools_install / "FFXIV_TexTools" / "ConsoleTools.exe"
        textools_folder = consoletools.parent
        
        return str(consoletools), str(textools_folder)
    

class Modpacker(Operator):
    bl_idname = "ya.file_modpacker"
    bl_label = "Modpacker"
    bl_description = "Converts FBX and/or packages FFXIV model files into a penumbra Modpack"
    bl_options = {'UNDO'}

    preset: StringProperty()  # type: ignore # convert_pack, pack, convert are valid presets

    def __init__(self):
        self.props         = bpy.context.scene.pmp_props
        self.selected:str  = self.props.modpack_groups
        self.replace :bool = self.props.button_modpack_replace
        self.pmp_dir       = Path(self.props.loadmodpack_directory)
        self.gamepath:str  = self.props.game_model_path
        self.fbx_dir       = Path(self.props.savemodpack_directory)
        
    def execute(self, context):
        paths, user_input = self.store_user_input(context)

        if not self.gamepath:
            self.report({'ERROR'}, "Please input a path to an FFXIV model")
            return {'CANCELLED'}
        
        elif not self.gamepath.startswith("chara") or not self.gamepath.endswith("mdl"):
            self.report({'ERROR'}, "Verify that the model is an actual FFXIV path")
            return {'CANCELLED'}
            
        if self.preset != "pack":
            if context.scene.pmp_props.consoletools_status != "ConsoleTools Ready!":
                self.report({'ERROR'}, "Verify that ConsoleTools is ready.")
                return {'CANCELLED'} 

            context.scene.pmp_props.modpack_progress = "Converting fbx to mdl..."
            self.fbx_to_mdl(context, paths)
            context.scene.pmp_props.modpack_progress = "Converting Complete!" 

        if self.replace:
            if not paths["pmp"]:
                self.report({'ERROR'}, "Please select a modpack.")
                return {'CANCELLED'} 
            
            if user_input["selected"] == "0" and not user_input["new_group_name"]:
                self.report({'ERROR'}, "Please enter a group name.")
                return {'CANCELLED'}
            mod_data, mod_meta = self.current_mod_data(self.replace, paths["pmp"])
        else:
            if  not user_input["new_group_name"]:
                self.report({'ERROR'}, "Please enter a group name.")
                return {'CANCELLED'}
            
            mod_data, mod_meta = {}, {}

        self.mdl_timer(context, paths, user_input, self.preset, mod_data, mod_meta)

        return {"FINISHED"}

    def store_user_input(self, context):
        group_name  :str = ""
        update_group:str = ""
        modpack_name:str = ""
        time = datetime.now().strftime("%H%M%S")
        
        for group in get_modpack_groups(context):
                if self.selected == group[0]:
                    group_name, update_group = group[1], group[2]
    
        
        paths = {
            "fbx": self.fbx_dir,
            "mdl": self.fbx_dir / "MDL",
            "temp": self.fbx_dir / f"temp_pmp_{time}",
            "gamepath": self.gamepath.lower(),
            "pmp": self.pmp_dir,
        }

        if self.replace:
            modpack_name = self.props.loadmodpack_display_directory
        else:
            modpack_name = self.props.new_mod_name
            paths["pmp"] = ""
            
        mod_meta = {
                "Author": self.props.author_name,
                "Version": self.props.new_mod_version
            }
        
        user_input = {
            "selected": self.selected,
            "new_group_name": self.props.modpack_rename_group,
            "old_group_name": group_name,
            "meta": mod_meta,
            "pmp_name": modpack_name,
            "update_group": update_group,
            "group_type": self.props.mod_group_type,
            "load_mod_ver": self.props.loadmodpack_version
        }

        return paths, user_input
   
    def current_mod_data(self, replace:bool, pmp:Path):
        if not replace or self.preset == "convert":
            return None
        current_mod_data = {}

        with zipfile.ZipFile(pmp, "r") as archive:
            for file_name in sorted(archive.namelist()):
                if file_name.count('/') == 0 and file_name.startswith("group") and file_name.endswith(".json"):
                    group_data = modpack_group_data(file_name, archive, data="all")
                    
                    current_mod_data[file_name] = group_data 
            with archive.open("meta.json") as meta:
                meta_contents = json.load(meta)

                current_mod_meta = ModMeta(**meta_contents)
            
        
        return current_mod_data, current_mod_meta  
 
    def fbx_to_mdl(self, context, paths:dict):
        textools = Path(context.scene.pmp_props.textools_directory)
        to_convert = [file for file in Path(paths["fbx"]).glob(f'*.fbx') if file.is_file()]

        cmd_name = "FBXtoMDL.cmd"
        sys_drive = textools.root
        commands = ["@echo off", f"cd /d {sys_drive}", f"cd {textools}"]

        cmd_path = paths["fbx"] / cmd_name
        Path.mkdir(paths["fbx"] / "MDL")

        cmds_added = 0
        total_files = len(to_convert)
        for file in to_convert:
            files_left = total_files - cmds_added    
            fbx_to_mdl = f'"{paths["fbx"] / file.name}" "{paths["mdl"] / file.stem}.mdl" "{paths["gamepath"]}"'
            
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

    def mdl_timer(self, context, paths:dict, user_input:dict, preset:str, mod_data:ModGroups, mod_meta:ModMeta):
        # Calls a timer to wait for mdl conversion to finish

        callback = partial(Modpacker.create_modpack, context, paths, user_input, preset, mod_data, mod_meta)
        
        bpy.app.timers.register(callback, first_interval=0.5)

    def create_modpack(context, paths:dict, user_input:dict, preset:str, mod_data:ModGroups, mod_meta:ModMeta):
        is_cmd = [file.name for file in Path(paths["fbx"]).glob(f'FBXtoMDL.cmd') if file.is_file()]
       
       # the .cmd file deletes itself when done, this makes the packing process wait until it has finished converting the fbx
        if is_cmd:
            return 0.5 
        if not is_cmd and preset == "convert":
            context.scene.pmp_props.modpack_progress = "Complete!"
        context.scene.pmp_props.modpack_progress = "Creating modpack..."  
        to_pack = [file for file in Path(paths["mdl"]).glob(f'*.mdl') if file.is_file()]
        to_pack = Modpacker.custom_sort(to_pack)

        Path.mkdir(paths["temp"], exist_ok=True)

        if mod_data:
            Modpacker.rolling_backup(paths)
            with zipfile.ZipFile(paths["pmp"], "r") as pmp:
                pmp.extractall(paths["temp"])
            Modpacker.update_mod(paths, user_input, mod_data, to_pack, mod_meta)    
        else:
            Modpacker.new_mod(paths, user_input, to_pack)
        
        with zipfile.ZipFile(paths["fbx"] / f"{user_input['pmp_name']}.pmp", 'w', zipfile.ZIP_DEFLATED) as pmp:
            for root, dir, files in os.walk(paths["temp"]):
                for file in files:
                    file_path = os.path.join(root, file)
                    pmp.write(file_path, os.path.relpath(file_path, paths["temp"]))

        bpy.app.timers.register(partial(Modpacker.schedule_cleanup, paths["temp"]), first_interval=0.1)
        modpack_data(context)
        context.scene.pmp_props.modpack_progress = "Complete!"

    def custom_sort(items:list):
        ranking = {}
        final_sort = []
        
        for item in items:
            ranking[item] = 0
            if "Small" in item.stem:
                ranking[item] += 0
            if "Medium" in item.stem:
                ranking[item] += 1
            if "Large" in item.stem:
                ranking[item] += 2
            if "Buff" in item.stem:
                ranking[item] += 3
            if "Rue" in item.stem:
                ranking[item] += 4
            if "Yiggle" in item.stem:
                ranking[item] += 5

        sorted_rank = sorted(ranking.items(), key=lambda x: x[1])
        
        for tuples in sorted_rank:
            final_sort.append(tuples[0])

        return final_sort

    def rolling_backup(paths:dict):
        folder_bak = paths["fbx"] / "BACKUP"
        time = datetime.now().strftime("%Y-%m-%d - %H%M%S")
        pmp_bak = folder_bak / f"{time}.pmp"
        
        Path.mkdir(folder_bak, exist_ok=True)

        existing_bak = sorted([file.name for file in Path(folder_bak).glob("*.pmp") if file.is_file()], reverse=True)

        while len(existing_bak) >= 5:
            oldest_backup = existing_bak.pop()
            Path.unlink(folder_bak / oldest_backup)

        shutil.copy(paths["pmp"], pmp_bak)

    def new_mod(paths:dict, user_input:dict, to_pack:list):
        meta_content = ModMeta(**user_input["meta"])
        meta_content.Name = user_input["pmp_name"]
        group_data = Modpacker.get_group_data_template(user_input)

        with open(os.path.join(paths["temp"], "meta.json"), "w") as file:
                file.write(meta_content.to_json())

        default_mod = ModGroups()

        with open(os.path.join(paths["temp"], "default_mod.json"), "w") as file:
                file.write(default_mod.to_json())

        file_name = f"group_001_{user_input['new_group_name'].lower()}.json"
        create_group = {file_name: (paths["gamepath"], user_input["new_group_name"], group_data)}
        Modpacker.write_group_json(paths, user_input, to_pack, create_group, user_input["new_group_name"])

        for file in to_pack:
            target_path = paths["temp"] / sanitise_path(user_input["new_group_name"]) / sanitise_path(file.stem)   
            Path.mkdir(target_path, parents=True, exist_ok=True)
        
            shutil.copy(paths["mdl"] / file.name, target_path / sanitise_path(file.name))

    def update_mod (paths:dict, user_input:dict, mod_data:ModGroups, to_pack:ModMeta, mod_meta:dict):
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
        
        Path.unlink(paths["temp"] / user_input["update_group"])
        Modpacker.write_group_json(paths, user_input, to_pack, create_group, group_dir, mod_data)

        mod_meta.Version = user_input["load_mod_ver"]

        with open(paths["temp"] / "meta.json", "w") as file:
                file.write(mod_meta.to_json())
        
        for file in to_pack:
            target_path = paths["temp"] / sanitise_path(group_dir) / sanitise_path(file.stem)   
            Path.mkdir(target_path, parents=True, exist_ok=True)
        
            shutil.copy(paths["mdl"] / file.name, target_path / sanitise_path(file.name))

    def get_group_data_template(user_input:dict, mod_data={}):
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

    def write_group_json(paths:dict, user_input:dict, to_pack:list, create_group:dict, group_dir:str, mod_data={}):
        
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
                new_option["Files"] = {gamepath: sanitise_path(rel_path)}
                new_option["Name"] = option_name
                    
                options.append(new_option)

            group_data["Options"] = options
            group_data["Name"] = group_name

            new_group = paths["temp"] / file_name


            with open(new_group, "w") as file:
                file.write(ModGroups(**group_data).to_json())

    def update_file_name(temp_folder:Path, user_input:dict, previous_group=""):
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
   
    def check_duplicate_groups(temp_folder:Path, mod_data:ModGroups, user_input:ModMeta):
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

    def delete_orphans(temp_folder:Path, update_group:str): 
        for options in update_group.Options:
            for gamepath, relpath in options.Files.items():
                try:
                    absolute_path = os.path.join(temp_folder, relpath)
                    Path.unlink(absolute_path)
                    print(f"Deleted file: {absolute_path}")
                except:
                    continue

        for dir in sorted(temp_folder.rglob("*"), reverse=True):
            if dir.is_dir():
                if not any(dir.iterdir()):
                    try: 
                        dir.rmdir() 
                        print(f"Deleted empty directory: {dir}")
                    except:
                        continue

    def schedule_cleanup(temp_folder:Path, retries=5):
        for attempts in range(retries):
            try:
                if temp_folder.is_dir():
                    shutil.rmtree(temp_folder)
                    return None
            except FileNotFoundError as e:
                return None
            except PermissionError as e:
                break
            return 5 - retries


classes = [
    ModpackDirSelector,
    ConsoleToolsDirectory,
    PMPSelector,
    CopyToFBX,
    ConsoleTools,
    Modpacker
]