import os
import bpy
import json
import winreg
import shutil
import zipfile


from datetime      import datetime
from pathlib       import Path
from functools     import partial
from ..file        import penumbra 
from bpy.types     import Operator


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
  
def sanitise_path(path):
        return path.lower().replace(" - ", "_").replace(" ", "")

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
    ConsoleTools,
    Modpacker
]