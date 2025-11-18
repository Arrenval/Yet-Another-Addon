import shutil
import tempfile

from pathlib          import Path
from datetime         import datetime
from itertools        import chain
from functools        import singledispatchmethod
from bpy.types        import Operator, Context, UILayout
from bpy.props        import StringProperty, IntProperty

from ...props         import get_window_props
from ...io.model      import ModpackError, ModpackFileError, ModpackGamePathError, ModpackValidationError, ModpackPhybCollisionError, ModpackFolderError
from ...xivpy.pmp     import *
from ...xivpy.phyb    import PhybFile
from ...preferences   import get_prefs
from ...props.modpack import BlendModGroup, BlendModOption, ModFileEntry, ModMetaEntry, modpack_data, yet_another_sort


def get_binary_name(all_options: list, options: set[str]) -> str:
    option_name = ""
    for option in reversed(all_options):
        if option in options:
            option_name += "1"
        else:
            option_name += "0"

    return option_name

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
        
    def execute(self, context: Context):
        self.props = get_window_props()
        self.prefs = get_prefs()

        self.pmp_source       = Path(self.props.file.modpack.modpack_dir)
        self.pmp_name  : str  = self.props.file.modpack.modpack_display_dir
        self.author    : str  = self.props.file.modpack.modpack_author
        self.version   : str  = self.props.file.modpack.modpack_version
        
        self.output_dir: Path = Path(self.prefs.modpack_output_dir)
        self.update    : bool = self.props.file.modpack.modpack_replace
        
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
        
        self.blender_groups = self.props.file.modpack.pmp_mod_groups
        if self.category == "SINGLE":
            self.blender_groups = [self.blender_groups[self.group]]

        self.temp_dir: list[Path] = []
        context.window.cursor_set('WAIT')
        try:
            self.create_modpack(context)
        except (ModpackError) as e:
            self.report({"ERROR"}, f"Failed to create modpack. {e}")
            return {'CANCELLED'}
        finally:
            for dir in self.temp_dir:
                shutil.rmtree(dir, ignore_errors=True)
            context.window.cursor_set('DEFAULT')

        return {'FINISHED'}

    def create_modpack(self, context: Context) -> int | None:
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
            self.create_group(pmp)   

        with tempfile.TemporaryDirectory(prefix=f"modpack_{self.pmp_name}_", ignore_cleanup_errors=True) as temp_dir:
            temp_path = Path(temp_dir)
            if self.update:
                pmp.extract_archive(self.pmp_source, temp_path)
                self.rolling_backup()

            orphans, duplicates = pmp.to_folder(temp_path, self.checked_files)

            pmp.to_archive(temp_path, self.output_dir, self.pmp_name)

        if (self.output_dir / f"{self.pmp_name}.pmp").is_file():
            self.props.file.modpack.modpack_dir = str(self.output_dir / f"{self.pmp_name}.pmp")
            modpack_data()

        setattr(self.props.file.modpack, "modpack_replace", True)

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

    def create_group(self, pmp: Modpack) -> None:
        if self.blend_group.idx == "New":
            new_group = True
            mod_group = ModGroup()
            old_group = None
        else:
            new_group = False
            mod_group = pmp.groups[int(self.blend_group.idx)]
            old_group = mod_group.copy()

        mod_group.Name        = self.blend_group.name
        mod_group.Description = self.blend_group.description
        mod_group.Priority    = self.blend_group.priority
        mod_group.Type        = self.blend_group.group_type if self.blend_group.group_type != 'Phyb' else "Combining"
        mod_group.Options     = []

        if self.blend_group.group_type == "Phyb":
            self.create_phyb_group(mod_group, old_group)

        elif self.blend_group.use_folder:
            self.options_from_folder(mod_group, old_group=old_group)

        else:
            self.resolve_option_structure(mod_group, old_group=old_group)
                
        if int(self.blend_group.page) != mod_group.Page or new_group:
            pmp.update_group_page(int(self.blend_group.page), mod_group, new_group)
        else:
            pmp.groups[int(self.blend_group.idx)] = mod_group

    def resolve_option_structure(self, mod_group: ModGroup, old_group: ModGroup=None) -> None:
        combining_group = mod_group.Type == "Combining"
        combinations    = self.blend_group.get_combinations()
        container_list  = [GroupContainer() for combo in combinations] if combining_group else []
        container       = mod_group.Options if combining_group else container_list

        old_options = {option.Name: option.Description for option in old_group.Options if option.Description} if old_group else {}
        for option in self.blend_group.mod_options:
            self.validate_container(option)

            new_option             = self.create_option(option, mod_group, combining_group)
            new_option.Description = old_options[option] if option in old_options and not option.description.strip() else ""
            
            container.append(new_option)

            container_indices  = [
                idx for idx, combo in enumerate(combinations) 
                if option.name in combo
            ]

            for idx in container_indices:
                for entry in chain(option.file_entries, option.meta_entries):
                    self.update_container(entry, container_list[idx], option.name)

        if not combining_group:
            mod_group.Options = container_list
            return
        
        all_options = [option.name for option in self.blend_group.mod_options]
        for correction in self.blend_group.corrections:
            correction_indices = [
                idx for idx, combo in enumerate(combinations) 
                if set(correction.names.split("_")) <= set(combo)
            ]

            for idx in correction_indices:
                option_name = get_binary_name(all_options, set(combinations[idx]))
                for entry in chain(correction.file_entries, correction.meta_entries):
                    self.update_container(entry, container_list[idx], option_name)

        mod_group.Containers = container_list

    def options_from_folder(self, mod_group:ModGroup, old_group:ModGroup=None) -> None:
        ''' Takes a folder and sorts files into mod options'''
        game_path   = self.blend_group.game_path
        file_format = Path(game_path).suffix
        
        file_folder = self.blend_group.final_folder()
        if not file_folder:
            raise ModpackFolderError("Could not find folder.")
        
        files = [file for file in file_folder.glob(f"*{file_format}") if file.is_file()]

        if file_format == ".mdl" and self.blend_group.ya_sort:
            files = yet_another_sort(files)

        option_idx = 0
        if self.blend_group.group_type == "Single":
            new_option             = GroupOption()
            new_option.Name        = "None"
            new_option.Description = ""
            new_option.Priority    = 0 
            new_option.Files       = {}

            mod_group.Options.append(new_option)
            option_idx += 1

        old_options = {option.Name: option.Description for option in old_group.Options if option.Description} if old_group else {}
        for file in files:
            new_option             = GroupOption()
            new_option.Name        = file.stem
            new_option.Priority    = option_idx if mod_group.Type == "Multi" else None
            new_option.Files       = {}
            new_option.Description = old_options[file.stem] if file.stem in old_options else ""

            new_option.Files[self.blend_group.game_path] = self._get_relative_path(file, file.stem, game_path)
            mod_group.Options.append(new_option)
            option_idx += 1

    def create_phyb_group(self, mod_group: ModGroup, old_group: ModGroup) -> None:

        def duplicate_sim_category(options: list[str]) -> bool:
            categories = [new_phybs[option][1] for option in options if new_phybs[option][1] != 'ALL']
            return len(categories) != len(set(categories))
        
        base_phybs, new_phybs = self._get_phybs(mod_group, old_group)

        combinations   = self.blend_group.get_combinations()
        container_list = [GroupContainer() for combo in combinations]

        temp_dir = Path(tempfile.mkdtemp())
        self.temp_dir.append(temp_dir)
        all_options = [name for name in new_phybs]
        for idx, options in enumerate(combinations):
            if idx == 0:
                continue
            if duplicate_sim_category(options):
                continue
            
            option_name = get_binary_name(all_options, set(options))
            option_dir  = temp_dir / option_name
            Path.mkdir(option_dir)

            phyb_copies = {game_path: phyb.copy() for game_path, phyb in base_phybs.items()}
            new_sims    = [sim for option in options for sim in new_phybs[option][0].simulators]

            for game_path, phyb in phyb_copies.items():
                file_path = option_dir / Path(game_path).name

                phyb.simulators.extend(new_sims)
                phyb.to_file(str(file_path))

                container_list[idx].Files[game_path] = self._get_relative_path(file_path, option_name, game_path)
        
        mod_group.Containers = container_list

    def _get_phybs(self, mod_group: ModGroup, old_group: ModGroup) -> tuple[dict[str, PhybFile], dict[str, tuple[PhybFile, str]]]:
        base_phybs: dict[str, PhybFile]             = {}
        new_phybs : dict[str, tuple[PhybFile, str]] = {}

        base_sim = PhybFile.from_file(self.blend_group.sim_append) if Path(self.blend_group.sim_append).is_file() else None
        base_collisions = set()
        for phyb in self.blend_group.base_phybs:
            base_phyb = PhybFile.from_file(phyb.file_path)
            if base_sim:
                base_phyb.simulators.extend(base_sim.simulators)

            base_phybs[phyb.game_path] = base_phyb
            base_collisions.update(base_phyb.get_collision_names())

        undefined_collisions = set()
        old_options = {option.Name: option.Description for option in old_group.Options if option.Description} if old_group else {}
        for phyb in self.blend_group.group_files:
            sim_phyb               = PhybFile.from_file(phyb.path)
            option_name            = Path(phyb.path).stem
            description            = old_options[option_name] if option_name in old_options else ""
            new_phybs[option_name] = (sim_phyb, phyb.category)
            
            mod_group.Options.append(GroupOption(Name=option_name, Description=description))
            for collision_obj in sim_phyb.get_collision_names():
                if collision_obj in base_collisions:
                    continue
                undefined_collisions.add(collision_obj)
        
        if undefined_collisions:
            raise ModpackPhybCollisionError(
                f"Collision Objects not defined in all base phybs: {', '.join(undefined_collisions)}."
            )
        
        return base_phybs, new_phybs
        
    def create_option(self, option: BlendModOption, mod_group: ModGroup, combining: bool) -> GroupOption:
        new_option               = GroupOption()
        new_option.Name          = option.name
        new_option.Description   = option.description
        if not combining:
            new_option.Files         = {}
            new_option.Manipulations = []

        new_option.Priority = option.priority if mod_group.Type == "Multi" else None

        return new_option
    
    @singledispatchmethod
    def update_container(self, 
                         entry: ModMetaEntry | ModFileEntry, 
                         new_option: GroupOption | GroupContainer,
                         option_name: str
                         ): ...
                       
    @update_container.register
    def file_entry(self, entry: ModFileEntry, new_option: GroupOption | GroupContainer, option_name: str) -> None:
        file                = Path(entry.file_path)

        new_option.Files[entry.game_path] = self._get_relative_path(file, option_name, entry.game_path)

    @update_container.register
    def meta_entry(self, entry: ModMetaEntry, new_option: GroupOption | GroupContainer, option_name: str) -> None:
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

        elif entry.type == "ATR":
            new_manip.Type = "Atr"

            new_entry.Attribute = entry.manip_ref
            
        new_manip.Manipulation = new_entry
        new_option.Manipulations.append(new_manip)

    def _get_relative_path(self, file: Path, option_name: str, game_path: str) -> str:
        corrected_game_path = game_path.replace("/", "\\")

        if file in self.checked_files:
            relative_path = self.checked_files[file]
        else:
            relative_path = f"{sanitise_path(self.blend_group.name)}\\{sanitise_path(option_name)}\\{corrected_game_path}"
            self.checked_files[file] = relative_path

        return relative_path

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
    ModPackager
]
