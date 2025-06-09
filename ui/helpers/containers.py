import bpy

from pathlib       import Path
from itertools     import chain
from bpy.types     import PropertyGroup, Context
from bpy.props     import StringProperty, EnumProperty, CollectionProperty, BoolProperty, IntProperty
from ...properties import get_file_properties, LoadedModpackGroup, safe_set_enum

class ModpackHelper(PropertyGroup):

    def check_valid_path(self):
        props           = get_file_properties()
        path:str        = self.game_path
        self.valid_path = path.startswith("chara") and path.endswith(tuple(props.GAME_SUFFIX))

    def get_subfolder(self) -> list[tuple[str, str, str]]:
        group_folder = Path(self.folder_path)
        if group_folder.is_dir():
            slot_dir = ["Chest", "Legs", "Hands", "Feet", "Chest & Legs"]
            subfolders = [dir for dir in group_folder.glob("*") if dir.is_dir() and any(slot in dir.name for slot in slot_dir)]

            subfolder_enum = [("None", "None", "")]
            for folder in subfolders:
                subfolder_enum.append((folder.name, folder.name, ""))

            return subfolder_enum
        else:
            return [("None", "None", "")]

    def final_folder(self):
        if self.subfolder != "None":
            folder = Path(self.folder_path) / Path(self.subfolder)
        else:
            folder = Path(self.folder_path)

        return str(folder)

    def get_folder_stats(self, model_check:bool=False) -> bool | dict:
        """Checks folder contents, if model_check is True, it only checks if there are any relevant model files."""

        model_suffix = [".fbx", ".mdl"]
        
        folder_stats = {}

        if self.subfolder == "None":
            folder = Path(self.folder_path)
        else:
            folder = Path(self.folder_path) / Path(self.subfolder)

        if model_check:
            return any(file.suffix in model_suffix for file in folder.glob("*") if file.is_file())
        else:
            files = [file for file in folder.glob("*") if file.is_file()]

            for file in files:
                folder_stats.setdefault(file.stem, {"fbx": 0, "mdl": 0})
                if file.suffix == ".fbx":
                    folder_stats[file.stem]["fbx"] = file.stat().st_mtime
                elif file.suffix == ".mdl":
                    folder_stats[file.stem]["mdl"] = file.stat().st_mtime

            return folder_stats

    def check_gamepath_category(self,) -> None:
        if self.valid_path:
            category = self.game_path.split("_")[-1].split(".")[0]
            return category
        
class ModMetaEntry(ModpackHelper):
    type          : StringProperty(default="", name="", description="Manipulation type") # type: ignore
    manip_ref     : StringProperty(default="", name="", description="Manipulation reference") # type: ignore

    slot               : EnumProperty(
        name= "",
        description= "Select a body slot",
        default="Body",
        items= [
            ("", "Gear", ""),
            ("Head", "Head", ""),
            ("Body", "Body", ""),
            ("Hands", "Hands", ""),
            ("Legs", "Legs", ""),
            ("Feet", "Feet", ""),
            ("", "Misc", ""),
            ("Ears", "Ears", ""),
            ("Neck", "Neck", ""),
            ("Wrists", "Wrists", ""),
            ("Right", "Right Finger", ""),
            ("Left", "Left Finger", ""),
            ("Glasses", "Glasses", ""),
            ("", "Customization", ""),
            ("Hair", "Hair", ""),
            ("Face", "Face", ""),
            ("Ears", "Ears", "")]
            ) # type: ignore
    race_condition     : EnumProperty(
        name= "",
        description= "Select a gender/race condition",
        items= [
            ("0", "None", ""),
            ("101", "101", ""),
            ("201", "201", ""),
            ("301", "301", ""),
            ("401", "401", ""),
            ("501", "501", ""),
            ("601", "601", ""),
            ("701", "701", ""),
            ("801", "801", ""),
            ("901", "901", ""),
            ("1001", "1001", ""),
            ("1101", "1101", ""),
            ("1201", "1201", ""),
            ("1301", "1301", ""),
            ("1401", "1401", ""),
            ("1501", "1501", ""),
            ("1601", "1601", ""),
            ("1701", "1701", ""),
            ("1801", "1801", ""),]
            ) # type: ignore
    connector_condition: EnumProperty(
        name= "",
        description= "Select a conditional connector",
        items= [
            ("None", "None", ""),
            ("Waist", "Waist", ""),
            ("Wrists", "Wrists", ""),
            ("Ankles", "Ankles", ""),]
            ) # type: ignore

    model_id: IntProperty(default=-1, min=-1, max=65535, name="", description="XIV model ID. -1 means all models") # type: ignore
    enable  : BoolProperty(default=True, name="", description="Enable/Disable the manipulation") # type: ignore

class ModFileEntry(ModpackHelper):
    file_path: StringProperty(default="Select a file...", name="", description="Path to the local file you want to pack/convert") # type: ignore
    game_path: StringProperty(default="Paste path here...", name="", description="Path to the in-game file you want to replace", update=lambda self, context: self.check_valid_path()) # type: ignore

    valid_path: BoolProperty(default=False) # type: ignore

class CorrectionEntry(ModpackHelper):
    group_idx: IntProperty(default=0) # type: ignore
    meta_entries: CollectionProperty(type=ModMetaEntry) # type: ignore
    file_entries: CollectionProperty(type=ModFileEntry) # type: ignore

    names: EnumProperty(
        name= "",
        description= "When these two groups are in the same combination, you can specify another meta entry to add",
        items= lambda self, context: self.get_possible_corrections(context)
        )  # type: ignore
    
    show_option     : BoolProperty(default=True) # type: ignore

    def get_possible_corrections(self, context:Context):
        group: BlendModGroup = context.scene.pmp_mod_groups[self.group_idx]
        total_options        = [option.name for option in group.mod_options[:8]]
        combinations         = [[]]
    
        for option in total_options:
            combinations.extend([combo + [option] for combo in combinations])
        
        combinations[0] = ["None"]
        return [
            ('_'.join(combo), f"{' + '.join(combo)}", "") 
            for combo in combinations
            if 3 > len(combo) > 1 or "None" in combo
            ]

class BlendModOption(ModpackHelper):
    name       : StringProperty(default="", name="",) # type: ignore
    description: StringProperty(default="", name="", description="Write something sillier") # type: ignore
    priority   : IntProperty(default=0, name="Priority", description="Decides which option takes precedence in a Multi group if files conflict. Higher number wins") # type: ignore

    meta_entries: CollectionProperty(type=ModMetaEntry) # type: ignore
    file_entries: CollectionProperty(type=ModFileEntry) # type: ignore

    show_option     : BoolProperty(default=True) # type: ignore

class BlendModGroup(ModpackHelper):
    idx        : EnumProperty(
        name= "",
        update=lambda self, context: self.set_group_values(),
        description= "Select an option to replace",
        items= lambda self, context: self.get_modpack_groups(context)
        )   # type: ignore   
    page       : EnumProperty(
        name= "",
        description= "Select a page for your group",
        items= lambda self, context: self.get_groups_page(context)
        )   # type: ignore 
    group_type : EnumProperty(
        name= "",
        description= "Single, Multi or Combining",
        update=lambda self, context: self.group_type_change(),
        items= [
            ("Single", "Single", "Exclusive options in a group"),
            ("Multi", "Multi ", "Multiple selectable options in a group"),
            ("Combining", "Combi ", "Combine multiple selectable groups")
        ]
        )   # type: ignore
    subfolder  : EnumProperty(
        name= "",
        description= "Alternate folder for model files",
        items= lambda self, context: self.get_subfolder()
        )  # type: ignore

    name       : StringProperty(default="", name="", description="Name of the group", update=lambda self, context: self.set_name()) # type: ignore
    description: StringProperty(default="", name="", description="Write something silly") # type: ignore
    game_path  : StringProperty(default="Paste path here...", name="", description="Path to the in-game file you want to replace", update=lambda self, context: self.check_valid_path()) # type: ignore
    folder_path: StringProperty(default="Select a folder...", name="" , description="Folder with files top pack/convert", ) # type: ignore
    priority   : IntProperty(default=0, name="Priority", description="Decides which group takes precedence in the modpack if files conflict. Higher number wins") # type: ignore

    mod_options: CollectionProperty(type=BlendModOption) # type: ignore
    corrections: CollectionProperty(type=CorrectionEntry) # type: ignore

    show_folder: BoolProperty(default=True, name="", description="Show the contents of the target folder") # type: ignore
    show_group : BoolProperty(default=True, name="", description="Show the contents of the group") # type: ignore

    use_folder      : BoolProperty(default=True, name="", description="Creates an option for each file in the folder", update=lambda self, context: self.use_folder_change()) # type: ignore
    valid_path      : BoolProperty(default=False) # type: ignore
    shared_game_path: BoolProperty(default=False) # type: ignore
    name_set        : BoolProperty(default=False) # type: ignore

    def set_group_values(self):
        props                                  = get_file_properties()
        replace                                = props.modpack_replace
        scene_groups: list[LoadedModpackGroup] = props.loaded_pmp_groups
        
        if self.idx != "New":
            if self.name == "" or not self.name_set and replace:
                self.name = scene_groups[int(self.idx)].group_name

            safe_set_enum(self, "page", str(scene_groups[int(self.idx)].group_page), "0")
            self.description = scene_groups[int(self.idx)].group_description
            self.priority    = scene_groups[int(self.idx)].group_priority
        else:
            if not self.name_set and replace:
                self.name = "New Group"
            safe_set_enum(self, "page", "0")
            self.description = ""

    def set_name(self):
        props = get_file_properties()
        self.name: str
        scene_groups: list[LoadedModpackGroup] = props.loaded_pmp_groups

        existing_names = [group.group_name.lower() for group in scene_groups]
        if self.name.lower() in chain(("", "new group"), existing_names) or not self.name.strip():
            self.name_set = False
        else:
            self.name_set = True

    def get_groups_page(self, context:Context) -> list[tuple[str, str, str]]:
        props = get_file_properties()
        pages = set([option.group_page for option in props.loaded_pmp_groups])

        if len(pages) >= 1:
            return [(str(page), f"Pg: {page:<3}", "") for page in pages]
        else:
            return [("0", f"Pg: 0", "")]
        
    def get_modpack_groups(self, context:Context) -> list[tuple[str, str, str]]:
        props   = get_file_properties()
        modpack = props.loaded_pmp_groups
        groups  = [("", "New:", ""), ("New", "New Group", "")]
        page    = 0
        
        for option in modpack:
            if page == option.group_page:
                groups.append(("", f"Page {page}:", ""))
                page += 1
            groups.append((option.group_value, option.group_name, option.group_description))
        return groups

    def use_folder_change(self):
        if self.use_folder == True:
            self.group_type = "Single"

    def group_type_change(self):
        if self.group_type == "Combining":
            self.use_folder = False

    def get_combinations(self):
        total_options = [option.name for option in self.mod_options[:8]]
        combinations = [[]]
    
        for option in total_options:
            combinations.extend([combo + [option] for combo in combinations])

        return combinations

CLASSES = [
    ModpackHelper,
    ModMetaEntry,
    ModFileEntry,
    CorrectionEntry,
    BlendModOption,
    BlendModGroup,
    ]

def set_ui_containers() -> None:
    bpy.types.Scene.pmp_mod_groups = CollectionProperty(
        type=BlendModGroup)
    
def remove_ui_containers() -> None:
    del bpy.types.Scene.pmp_mod_groups