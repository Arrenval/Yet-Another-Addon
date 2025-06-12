import bpy
import copy
import json
import shutil
import tempfile
import subprocess

from pathlib                import Path
from itertools              import chain
from functools              import partial, singledispatchmethod
from datetime               import datetime
from bpy.types              import Operator, Context, UILayout
from bpy.props              import StringProperty, IntProperty

from ..properties           import get_file_properties, modpack_data, BlendModGroup, BlendModOption, ModFileEntry, ModMetaEntry
from ..preferences          import get_prefs
from ..utils.penumbra       import Modpack, ModGroup, GroupOption, GroupContainer, ManipulationType, ManipulationEntry, sanitise_path
from ..utils.ya_exception   import ModpackFileError, ModpackGamePathError, ModpackValidationError
    

class ModelConverter(Operator):
    bl_idname = "ya.file_converter"
    bl_label = "Modpacker"
    bl_description = "FBX to MDL converter via ConsoleTools"
    
    def execute(self, context:Context):
        self.prefs                  = get_prefs()
        props                       = get_file_properties()
        self.game_path : str        = props.game_model_path
        self.output_dir             = Path(props.savemodpack_directory)
        self.console   : str        = props.consoletools_status
        if props.model_subfolder != "None":
            self.output_dir: Path       = self.output_dir / self.subfolder
        
        if not self.mdl_game:
            self.report({'ERROR'}, "Please input a path to an FFXIV model")
            return {'CANCELLED'}
        
        elif not self.mdl_game.startswith("chara") or not self.mdl_game.endswith("mdl"):
            self.report({'ERROR'}, "Verify that the model is an actual FFXIV path")
            return {'CANCELLED'}
        
        elif not self.output_dir.is_dir():
            self.report({'ERROR'}, "Please select an FBX directory")
            return {'CANCELLED'}
            
        if self.console != "ConsoleTools Ready!":
            self.report({'ERROR'}, "Verify that ConsoleTools is ready.")
            return {'CANCELLED'} 
        
        mdl_status, cmd = self.mdl_converter(context) 

        callback = partial(ModelConverter.delete_cmd_file, context, cmd, mdl_status)
        bpy.app.timers.register(callback, first_interval=0.5)
        return {"FINISHED"}
       
    def mdl_converter(self, context:Context) -> subprocess.Popen:
        blender_dir  = Path(bpy.app.binary_path).parent
        python_dir   = str([file for file in (blender_dir).glob("*/python/bin/python*")][0])
        script_dir   = Path(__file__).parent / "database.py"
        props_json   = self.output_dir / "MeshProperties.json"
        textools     = Path(self.prefs.textools_directory)
        game_path    = self.game_path
        model_props  = {}
        to_convert   = [file for file in (self.output_dir / self.subfolder).glob("*.fbx") if file.is_file()]

        if props_json.is_file():
            with open(props_json, "r") as file:
                model_props = json.load(file)

        cmd_name = "MDL.cmd"
        commands = ["@echo off", f"cd /d {textools.drive}", f"cd {textools}", "echo Please don't close this window..."]

        Path.mkdir(self.output_dir, exist_ok=True)
        cmd_path = self.output_dir / cmd_name

        cmds_added  = 0
        total_files = len(to_convert)
        for file in to_convert:
            commands.append(f"echo ({cmds_added + 1}/{total_files}) Converting: {file.stem}")
            source = str(self.output_dir / file.name)
            dest = str(self.output_dir / file.stem)
            
            if file.stem in model_props:
                commands.append("echo Writing model to database...")
                commands.append(rf"cd {textools}\converters\fbx")
                commands.append(f'converter.exe "{source}" >nul')
                commands.append("echo Updating model database tables...")
                commands.append(f'"{python_dir}" "{script_dir.resolve()}" "{textools}" "{file.stem}" "{props_json}" >nul')
                commands.append(f"cd {textools}")
                
                # Places all dbs in your export folder, uncomment for debugging and verifying output
                # source = str(self.output_dir / f"{file.stem}.db")
                # commands.append(rf'copy /y "{textools}\converters\fbx\result.db" "{source}" >nul')
                source = str(textools / "converters" / "fbx" / "result.db")

            commands.append("echo Finalising .mdl...")
            commands.append(f'ConsoleTools.exe /wrap "{source}" "{dest}.mdl" "{game_path}" >nul')

            cmds_added += 1
        
        commands.append("pause")

        with open(cmd_path, 'w') as file:
            for cmd in commands:
                file.write(f"{cmd}\n")

        mdl_status = subprocess.Popen([str(cmd_path)], creationflags=subprocess.CREATE_NEW_CONSOLE)

        return mdl_status, cmd_path
    
    def delete_cmd_file(context, cmd:Path, mdl_status: subprocess.Popen) -> None:
        if mdl_status is not None and mdl_status.poll() != 0:
            return 0.5
        
        Path.unlink(cmd, missing_ok=True)
        
class ModPackager(Operator):
    bl_idname = "ya.mod_packager"
    bl_label = "Modpacker"
    bl_description = "Penumbra modpack creator"

    category: StringProperty() # type: ignore
    group   : IntProperty() # type: ignore
    
    @classmethod
    def description(cls, context:Context, properties):
        if properties.category == "ALL":
            return "Pack all configured groups"
        else:
            return "Pack selected group"
        
    def execute(self, context:Context):
        self.props = get_file_properties()
        self.prefs = get_prefs()

        time  = datetime.now().strftime("%H%M%S")
        
        self.pmp_source       = Path(self.props.modpack_dir)
        self.pmp_name  : str  = self.props.modpack_display_dir
        self.author    : str  = self.props.modpack_author
        self.version   : str  = self.props.modpack_version
        
        self.output_dir: Path = Path(self.prefs.modpack_output_dir)
        self.temp_dir  : Path = self.output_dir / f"temp_pmp_{time}"
        self.update    : bool = self.props.modpack_replace
        
        if not self.prefs.is_property_set("modpack_output_dir") or not self.output_dir.is_dir():
            self.report({'ERROR'}, "Please select an output directory.")
            return {'CANCELLED'}
        
        if not self.pmp_source.is_file() and self.update:
            self.report({'ERROR'}, "Please select a modpack.")
            return {'CANCELLED'} 
        
        if not self.pmp_name:
            self.report({'ERROR'}, "Please enter a mod name")
            return {'CANCELLED'}
        elif not self.author:
            self.report({'ERROR'}, "Please enter an author.")
            return {'CANCELLED'}
        
        self.blender_groups: list[BlendModGroup] = self.props.pmp_mod_groups
        if self.category == "SINGLE":
            self.blender_groups = [self.blender_groups[self.group]]

        try:
            return self.create_modpack(context)
        except (ModpackFileError, ModpackGamePathError, ModpackValidationError) as e:
            self.report({"ERROR"}, f"Failed to create modpack. {e}")
            return {'CANCELLED'}

    def create_modpack(self, context:Context) -> int | None:
        if self.update:
            pmp = Modpack.from_archive(self.pmp_source)  
        else:
            pmp = Modpack()

        pmp.meta.Name    = self.pmp_name
        pmp.meta.Author  = self.author
        pmp.meta.Version = self.version
        
        self.checked_files: dict[Path, str] = {}
        for blend_group in self.blender_groups:
            self.blend_group = blend_group
            self.validate_container(blend_group)

            # Modpack instance is passed on and manipulated in this function chain
            self.create_group(pmp)

        with tempfile.TemporaryDirectory(prefix=f"modpack_{self.pmp_name}_", ignore_cleanup_errors=True) as temp_dir:
            temp_path = Path(temp_dir)
            if self.update:
                pmp.extract_archive(self.pmp_source, temp_path)
                self.rolling_backup()

            orphans, duplicates = pmp.to_folder(temp_path, self.checked_files)

            pmp.to_archive(temp_path, self.output_dir, self.pmp_name)

        if (self.output_dir / f"{self.pmp_name}.pmp").is_file():
            self.props.modpack_dir = str(self.output_dir / f"{self.pmp_name}.pmp")
            modpack_data(context)

        setattr(self.props, "modpack_replace", True)

        self.report({"INFO"}, f"{self.pmp_name} created succesfully!")

        pmp_name = self.pmp_name
        groups   = self.blender_groups

        def draw_popup(self, context):
            layout:UILayout = self.layout
            layout.label(text=f"Groups created:")
            for group in groups:
                layout.label(text=group.name)
            
            if orphans:
                layout.separator(type="LINE")
                plural = "s" if len(orphans) > 1 else ""
                layout.label(text=f"Removed {len(orphans)} file{plural} without file references.")
            
            if duplicates:
                layout.separator(type="LINE")
                plural = "s" if len(duplicates) > 1 else ""
                layout.label(text=f"Removed {len(duplicates)} duplicate file{plural}.")

        context.window_manager.popup_menu(draw_popup, title=f"{pmp_name}.pmp created succesfully!", icon='CHECKMARK')
        return {"FINISHED"}
   
    def create_group(self, pmp: Modpack):
        if self.blend_group.idx == "New":
                new_group = True
                mod_group = ModGroup()
                old_group = None
        else:
            new_group = False
            mod_group = pmp.groups[int(self.blend_group.idx)]
            old_group = copy.deepcopy(mod_group)

        mod_group.Name     = self.blend_group.name
        mod_group.Priority = self.blend_group.priority
        mod_group.Type     = self.blend_group.group_type
        mod_group.Options  = []

        if self.blend_group.use_folder:
            self.options_from_folder(mod_group, old_group=old_group)

        else:
            self.resolve_option_structure(mod_group, old_group)
                
        if int(self.blend_group.page) != mod_group.Page or new_group:
            pmp.update_group_page(int(self.blend_group.page), mod_group, new_group)
        elif new_group:
            pmp.groups.append(mod_group)
        else:
            pmp.groups[int(self.blend_group.idx)] = mod_group

    def resolve_option_structure(self, mod_group: ModGroup, old_group: ModGroup):
        combining_group = self.blend_group.group_type == "Combining"
        combinations    = self.blend_group.get_combinations()
        container_list  = [GroupContainer() for combo in combinations] if combining_group else []

        for option_idx, option in enumerate(self.blend_group.mod_options):
            self.option_name = option.name
            self.validate_container(option)

            new_option = self.create_option(option)

            if old_group is not None and not option.description.strip():
                self.try_keep_description(option, container_list[idx], old_group, idx)

            if combining_group:
                mod_group.Options.append(new_option)
            else:
                container_list.append(new_option)
        
            container_indices  = [
                idx for idx, combo in enumerate(combinations) 
                if option.name in combo
                ]

            for idx in container_indices:
                for entry in chain(option.file_entries, option.meta_entries):
                    self.update_container(entry, container_list[idx])

        if combining_group:
            for correction in self.blend_group.corrections:

                correction_indices = [
                idx for idx, combo in enumerate(combinations) 
                if set(correction.names.split("_")) <= set(combo)
                ]
                for idx in correction_indices:
                    for entry in chain(correction.file_entries, correction.meta_entries):
                        self.update_container(entry, container_list[idx])

            mod_group.Containers = container_list
        else:
            mod_group.Options = container_list

    def create_option(self, option:BlendModOption) -> GroupOption:
        new_option               = GroupOption()
        new_option.Name          = option.name
        new_option.Description   = option.description

        new_option.Priority = option.priority if self.blend_group.group_type == "Multi" else None

        return new_option
    
    def try_keep_description(self, option:BlendModOption, new_option:GroupOption, old_group: ModGroup, option_idx:int):
        # Checks to see if the Options at the same indices match via name.
        if option_idx < len(old_group.Options or []) and old_group.Options[option_idx].Name == option.name:
            new_option.Description = old_group.Options[option_idx].Description

    @singledispatchmethod
    def update_container(self, 
                         entry: ModMetaEntry | ModFileEntry, 
                         new_option : GroupOption | GroupContainer,
                         ): ...
                       
    @update_container.register
    def file_entry(self, entry: ModFileEntry, new_option: GroupOption | GroupContainer):
        file                = Path(entry.file_path)
        corrected_game_path = entry.game_path.replace("/", "\\")
        
        if file in self.checked_files:
            relative_path = self.checked_files[file]
        else:
            relative_path = f"{sanitise_path(self.blend_group.name)}\\{sanitise_path(self.option_name)}\\{corrected_game_path}"
            self.checked_files[file] = relative_path
        
        new_option.Files[entry.game_path] = relative_path

    @update_container.register
    def meta_entry(self, entry: ModMetaEntry, new_option: GroupOption | GroupContainer):
        new_manip = ManipulationType()
        new_entry = ManipulationEntry()

        new_entry.Entry               = entry.enable
        new_entry.Slot                = entry.slot
        new_entry.Id                  = None if entry.model_id == -1 else entry.model_id
        new_entry.GenderRaceCondition = int(entry.race_condition)

        if entry.type == "SHP":
            new_manip.Type = "Shp"

            new_entry.Shape = entry.manip_ref
            new_entry.ConnectorCondition  = entry.connector_condition

        if entry.type == "ATR":
            new_manip.Type = "Atr"

            new_entry.Attribute = entry.manip_ref
            
        new_manip.Manipulation = new_entry
        new_option.Manipulations.append(new_manip)

    def options_from_folder(self, mod_group:ModGroup, old_group:ModGroup=None):
        ''' Takes a folder and sorts files into mod options'''
        game_path:str       = self.blend_group.game_path
        file_format         = Path(game_path).suffix
        corrected_game_path = game_path.replace("/", "\\")
        
        file_folder = Path(self.blend_group.folder_path) if self.blend_group.subfolder == "None" else Path(self.blend_group.folder_path) / Path(self.blend_group.subfolder)
        files = [file for file in file_folder.glob(f"*{file_format}") if file.is_file()]

        if file_format == ".mdl" and self.prefs.ya_sort:
            files = self.yet_another_sort(files)

        option_idx = 0
        if self.blend_group.group_type == "Single":
            new_option              = GroupOption()
            new_option.Name         = "None"
            new_option.Description  = ""
            new_option.Priority     = 0 
            new_option.Files        = {}

            mod_group.Options.append(new_option)
            option_idx += 1

        for file in files:
            new_option              = GroupOption()
            new_option.Name         = file.stem
            new_option.Priority     = option_idx if self.blend_group.group_type == "Multi" else None
            new_option.Files        = {}

            if old_group:
                if option_idx < len(old_group.Options or []) and old_group.Options[option_idx].Name == file.stem:
                    new_option.Description = old_group.Options[option_idx].Description

            if file in self.checked_files:
                relative_path = self.checked_files[file]
            else:
                relative_path = f"{sanitise_path(self.blend_group.name)}\\{sanitise_path(file.stem)}\\{corrected_game_path}"
                self.checked_files[file] = relative_path
            
            new_option.Files[self.blend_group.game_path] = relative_path
            mod_group.Options.append(new_option)
            option_idx = 1

    def validate_container(self, container):
        match container:
            case BlendModGroup():
                if container.name.strip() == "":
                    raise ModpackValidationError("A Group is missing a name.")
                if container.use_folder and not container.valid_path:
                    raise ModpackGamePathError(f'Group "{container.name}": XIV path is not valid.')
                
            case BlendModOption():
                if container.name.strip() == "":
                    raise ModpackValidationError(f'Group "{self.blend_group.name}": An option is missing a name.')
                
            case ModMetaEntry():
                if container.type == "SHP" and not container.manip_ref.startswith("shp"):
                    raise ModpackValidationError(f'Group "{self.blend_group.name}": SHP entry expected reference to start with "shp".')
                if container.type == "ATR" and not container.manip_ref.startswith("atrx_"):
                    raise ModpackValidationError(f'Group "{self.blend_group.name}": ATR entry expected reference to start with "atrx_".')

            case ModFileEntry():
                file      = Path(container.file_path)
                game_path = Path(container.game_path)
                if not file.is_file():
                    raise ModpackFileError(f"{file} is not a invalid file path.")
                if file.suffix not in game_path.suffix:
                    raise ModpackFileError(f'Group "{self.blend_group.name}": {file.name} type does not match in-game file. Expected an {game_path.suffix}.')
                if not container.valid_path:
                    raise ModpackGamePathError(f'Group "{self.blend_group.name}": XIV path is not valid.')

    def yet_another_sort(self, items:list[Path]) -> list[Path]:
        '''It's stupid but it works.'''
        ranking: dict[Path, int] = {}
        final_sort: list[Path] = []
        
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

    def rolling_backup(self) -> None:
        folder_bak = self.output_dir / "BACKUP"
        time = datetime.now().strftime("%Y-%m-%d - %H%M%S")
        pmp_bak = folder_bak / f"{time}.pmp"
        
        Path.mkdir(folder_bak, exist_ok=True)

        existing_bak = sorted([file for file in folder_bak.glob("*.pmp") if file.is_file()], reverse=True)

        for old_backup in existing_bak[4:]:
            old_backup.unlink()

        shutil.copy(self.pmp_source, pmp_bak)


CLASSES = [
    ModelConverter,
    ModPackager
]
