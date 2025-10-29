from typing            import TYPE_CHECKING, Literal
from pathlib           import Path
from itertools         import chain
from bpy.types         import PropertyGroup, Context
from bpy.props         import StringProperty, EnumProperty, CollectionProperty, BoolProperty, IntProperty

from .enums            import get_racial_enum
from .getters          import get_file_props, get_window_props
from ..utils.typings   import BlendEnum, BlendCollection
from ..xiv.formats.pmp import Modpack


def modpack_data() -> None:
    window = get_window_props()
    props  = get_file_props()
    props.loaded_pmp_groups.clear()

    blender_groups = window.file.modpack.pmp_mod_groups
    modpack_path = Path(window.file.modpack.modpack_dir)

    if modpack_path.is_file():
        modpack = Modpack.from_archive(modpack_path)
    else:
        return

    for idx, group in enumerate(modpack.groups):
        new_option = props.loaded_pmp_groups.add()
        new_option.group_value       = str(idx)
        new_option.group_name        = group.Name
        new_option.group_description = group.Description
        new_option.group_page        = group.Page
        new_option.group_priority    = group.Priority

    window.file.modpack.modpack_author  = modpack.meta.Author
    window.file.modpack.modpack_version = modpack.meta.Version

    name_to_idx = {group.Name: str(idx) for idx, group in enumerate(modpack.groups)}
    for blend_group in blender_groups:
        try:
            blend_group.idx = name_to_idx[blend_group.name]
        except:
            blend_group.idx = "New"

def yet_another_sort(files:list[Path]) -> list[Path]:
    '''It's stupid but it works.'''
    ranking   : dict[Path, int] = {}
    final_sort: list[Path]      = []
    
    for file in files:
        ranking[file] = 0
        if "Small" in file.stem:
            ranking[file] += 3
        if "Cupcake" in file.stem:
            ranking[file] += 3
        if "Sugar" in file.stem:
            ranking[file] += 4
        if "Medium" in file.stem:
            ranking[file] += 5
        if "Teardrop" in file.stem:
            ranking[file] += 5
        if "Sayonara" in file.stem:
            ranking[file] += 6
        if "Tsukareta" in file.stem:
            ranking[file] += 7
        if "Tsukareta+" in file.stem:
            ranking[file] += 1
        if "Mini" in file.stem:
            ranking[file] += 9
        if "Large" in file.stem:
            ranking[file] += 10
        if "Omoi" in file.stem:
            ranking[file] += 11
        if "Sugoi" in file.stem:
            ranking[file] += 1
        if "Uranus" in file.stem:
            ranking[file] += 13
        if "Skull" in file.stem:
            ranking[file] += 1
        if "Yanilla" in file.stem:
            ranking[file] += 2
        if "Lava" in file.stem:
            ranking[file] += 3
        if "Buff" in file.stem:
            ranking[file] += 20
        if "Rue" in file.stem:
            ranking[file] += 42
        if "Lava" in file.stem:
            ranking[file] += 420
        if "Masc" in file.stem:
            ranking[file] += 1337
        if "Yiggle" in file.stem:
            ranking[file] += 69*420
        if "Long" in file.stem:
            ranking[file] += 1
        if "Ballerina" in file.stem:
            ranking[file] += 2
        if "Stabbies" in file.stem:
            ranking[file] += 3

    sorted_rank = sorted(ranking.items(), key=lambda x: x[1])
    
    for tuples in sorted_rank:
        final_sort.append(tuples[0])

    return final_sort


class ModpackHelper(PropertyGroup):

    def check_valid_path(self):
        path: str       = self.game_path
        self.valid_path = path.startswith("chara") and path.endswith(tuple(get_file_props().GAME_SUFFIX))

    def get_subfolder(self) -> BlendEnum:
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

    def check_gamepath_category(self) -> None:
        if self.valid_path:
            category = self.game_path.split("_")[-1].split(".")[0]
            return category
        
class ModMetaEntry(PropertyGroup):
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
        default=1,
        description= "Select a gender/race condition",
        items=lambda self, context: get_racial_enum()
            ) # type: ignore
    connector_condition: EnumProperty(
        name= "",
         default="None",
        description= "Select a conditional connector",
        items= [
            ("None", "None", ""),
            ("Waist", "Waist", ""),
            ("Wrists", "Wrists", ""),
            ("Ankles", "Ankles", ""),]
            ) # type: ignore

    model_id: IntProperty(default=-1, min=-1, max=65535, name="", description="XIV model ID. -1 means all models") # type: ignore
    enable  : BoolProperty(default=True, name="", description="Enable/Disable the manipulation") # type: ignore

    if TYPE_CHECKING:
        type                : str
        manip_ref           : str
        slot                : str
        race_condition      : str
        connector_condition : str
        model_id            : int
        enable              : bool

class ModFileEntry(ModpackHelper):
    file_path: StringProperty(default="Select a file...", name="", description="Path to the local file you want to pack/convert") # type: ignore
    game_path: StringProperty(default="Paste path here...", name="", description="Path to the in-game file you want to replace", update=lambda self, context: self.check_valid_path()) # type: ignore

    valid_path: BoolProperty(default=False) # type: ignore

    if TYPE_CHECKING:
        file_path : str
        game_path : str
        valid_path: bool

class CorrectionEntry(ModpackHelper):

    def get_possible_corrections(self, context: Context):
        props         = get_window_props()
        group         = props.file.modpack.pmp_mod_groups[self.group_idx]
        total_options = [option.name for option in group.mod_options[:8]]
        combinations  = [[]]
    
        for option in total_options:
            combinations.extend([combo + [option] for combo in combinations])
        
        combinations[0] = ["None"]
        return [
            ('_'.join(combo), f"{' + '.join(combo)}", "") 
            for combo in combinations
            if 3 > len(combo) > 1 or "None" in combo
            ]
    
    group_idx   : IntProperty(default=0) # type: ignore
    meta_entries: CollectionProperty(type=ModMetaEntry) # type: ignore
    file_entries: CollectionProperty(type=ModFileEntry) # type: ignore
    
    names: EnumProperty(
        name= "",
        default=0,
        description= "When these two groups are in the same combination, you can specify another entry to add",
        items=get_possible_corrections
        )  # type: ignore
    
    show_option     : BoolProperty(default=True, name="", description="Show the contents of the option") # type: ignore
    
    if TYPE_CHECKING:
        group_idx   : int
        file_entries: BlendCollection[ModFileEntry]
        meta_entries: BlendCollection[ModMetaEntry]
        names       : str
        show_option : bool 

class BasePhyb(ModpackHelper):

    def check_valid_path(self, context):
        path: str       = self.game_path
        self.valid_path = path.startswith("chara") and path.endswith(".phyb")

        file_name = Path(self.game_path).stem
        if not file_name.startswith("phy_") or not self.valid_path:
            self.race = '0'
            return
        
        try:
            race_code = file_name[5:9]
            category  = file_name[9]
        except:
            self.race = '0'
            return
        
        if category in ('h', 'b'):
            self.race = race_code
        else:
            self.race = '0'

    def _assign_phyb_path(self, context):
        file_name = Path(self.file_path).stem
        if not file_name.startswith("phy_"):
            return
        try:
            item_type = file_name[4]
            race_code = file_name[5:9]
            category  = file_name[9]
            slot      = file_name[10:14]
        except:
            return
        
        category_str   = {'h': "hair", 'b': "base", 'w': "weapon"}
        self.game_path = f"chara/human/{item_type}{race_code}/skeleton/{category_str[category]}/{category}{slot}/phy_{item_type}{race_code}{category}{slot}.phyb"

        if category in ('h', 'b'):
            self.race = race_code
        else:
            self.race = '0'

    file_path: StringProperty(
                    default="Select a phyb...", 
                    name="" , 
                    description="File to be used as base",
                    update=_assign_phyb_path
                    ) # type: ignore
    
    game_path: StringProperty(
                    default="Paste path here...", 
                    name="", 
                    description="Path to the in-game file you want to replace", 
                    update=check_valid_path
                    ) # type: ignore
    
    race: EnumProperty(
        name= "",
        default=1,
        description= "",
        items=lambda self, context: get_racial_enum()
            ) # type: ignore

    valid_path: BoolProperty(default=False) # type: ignore

    if TYPE_CHECKING:
        file_path : str
        game_path : str
        valid_path: bool

class GroupFile(PropertyGroup):
    path    : StringProperty(default="", name="", description="") # type: ignore
    category:  EnumProperty(
                    name="Category",
                    description="Only simulators with unique categories will be added to the same base",
                    default="ALL",
                    items=[
                        ('ALL', "All", "Will be combined with all categories"),
                        ('BOOB', "Breasts", "Will not be combined with other simulators of this category"),
                        ('BUTT', "Butt", "Will not be combined with other simulators of this category"),
                        ('BELLY', "Belly", "Will not be combined with other simulators of this category"),
                        ('THIGHS', "Thighs", "Will not be combined with other simulators of this category"),
                    ]
                ) # type: ignore
    
    if TYPE_CHECKING:
        path    : str
        category: str
    
class BlendModOption(ModpackHelper):
    name       : StringProperty(default="", name="",) # type: ignore
    description: StringProperty(default="", name="", description="Write something sillier") # type: ignore
    priority   : IntProperty(default=0, name="Priority", description="Decides which option takes precedence in a Multi group if files conflict. Higher number wins") # type: ignore

    meta_entries: CollectionProperty(type=ModMetaEntry) # type: ignore
    file_entries: CollectionProperty(type=ModFileEntry) # type: ignore

    show_option : BoolProperty(default=True, name="", description="Show the contents of the option") # type: ignore

    if TYPE_CHECKING:
        name        : str
        description : str
        priority    : int
        file_entries: BlendCollection[ModFileEntry]
        meta_entries: BlendCollection[ModMetaEntry]
        show_option : bool
    
class BlendModGroup(ModpackHelper):

    def final_folder(self) -> Path | Literal[False]:
        if self.subfolder != "None" and self.group_type in ("Single", "Multi"):
            folder = Path(self.folder_path) / Path(self.subfolder)
        else:
            folder = Path(self.folder_path)

        if str(folder).strip() != "" and folder.is_dir():
            return folder
        else:
            return False
    
    def get_files(self, context):
        folder = Path(self.folder_path)
        suffix = get_file_props().GAME_SUFFIX if self.group_type != "Phyb" else ".phyb"
        if self.group_type == "Phyb":
            existing = {file.path: file.category for file in self.group_files}
            files    = [file for file in folder.glob("*") if file.is_file() and file.suffix in suffix]

            self.group_files.clear()
            for file in files[:8]:
                file_path = str(file)

                new_file = self.group_files.add()
                new_file.path = file_path
                new_file.category  = existing[file_path] if file_path in existing else 'ALL'
        else:
            files = [file for file in folder.glob("*") if file.is_file() and file.suffix in suffix]
            if self.ya_sort:
                files = yet_another_sort(files)

            self.group_files.clear()
            for file in files:
                new_file = self.group_files.add()
                new_file.path = str(file)

    def _set_group_values(self, context):
        props   = get_file_props()
        window  = get_window_props()
        replace = window.file.modpack.modpack_replace

        modpack = props.loaded_pmp_groups
        
        if self.idx != "New":
            # idx = self.idx - 1
            group = modpack[int(self.idx)]
            if self.name == "" or not self.name_set and replace:
                self.name = group.group_name

            try:
                self.page = str(group.group_page)
            except:
                self.property_unset("page")

            self.description = group.group_description
            self.priority    = group.group_priority
        else:
            if not self.name_set and replace:
                self.name = "New Group"
            self.property_unset("page")
            self.description = ""

    def _get_modpack_groups(self, context: Context) -> BlendEnum:
        props   = get_file_props()
        modpack = props.loaded_pmp_groups
        groups  = [("", "New:", ""), ("New", "New Group", "")]
        page    = 0
        
        for option in modpack:
            if page == option.group_page:
                groups.append(("", f"Page {page}:", ""))
                page += 1
            groups.append((option.group_value, option.group_name, option.group_description))
   
        return groups

    def _get_groups_page(self, context: Context) -> BlendEnum:
        props = get_file_props()
        pages = set([option.group_page for option in props.loaded_pmp_groups])

        if len(pages) >= 1:
            return [(str(page), f"Pg: {page:<3}", "") for page in pages]
        else:
            return [("0", f"Pg: 0", "")]
    
    def _group_type_change(self, context):
        if self.group_type in ("Combining", "Phyb") and self.use_folder:
            self.use_folder = False
        if self.use_folder or self.group_type == "Phyb":
            self.get_files(context)

    def _set_name(self, context):
        props = get_file_props()
        self.name: str
        scene_groups = props.loaded_pmp_groups

        existing_names = [group.group_name.lower() for group in scene_groups]

        if self.name.lower() in chain(("", "new group"), existing_names) or not self.name.strip():
            self.name_set = False
        else:
            self.name_set = True

    def _use_folder_change(self, context):
        if self.use_folder and self.group_type in ("Combining", "Phyb"):
            self.group_type = "Single"
        if self.use_folder:
            self.get_files(context)
    
    idx             : EnumProperty(
                        name= "",
                        default=1,
                        update=_set_group_values,
                        description= "Select an option to replace",
                        items=_get_modpack_groups
                        )   # type: ignore 
      
    page            : EnumProperty(
                        name= "",
                        default=0,
                        description= "Select a page for your group",
                        items=_get_groups_page
                        )   # type: ignore 
    
    group_type      : EnumProperty(
                        name= "",
                        default="Single",
                        description= "Single, Multi, Combining or Phyb",
                        update=_group_type_change,
                        items= [
                            ("Single", "Single", "Exclusive options in a group"),
                            ("Multi", "Multi ", "Multiple selectable options in a group"),
                            ("Combining", "Combi ", "Combine multiple selectable groups"),
                            ("Phyb", "Phyb ", "Specialised combining group for phyb combinations")
                        ]
                        )   # type: ignore
    
    name            : StringProperty(default="New Group", name="", description="Name of the group", update=_set_name) # type: ignore
    description     : StringProperty(default="", name="", description="Write something silly") # type: ignore
    game_path       : StringProperty(default="Paste path here...", name="", description="Path to the in-game file you want to replace", update=lambda self, context: self.check_valid_path()) # type: ignore
    folder_path     : StringProperty(default="Select a folder...", name="" , description="Folder with files to pack/append", update=get_files) # type: ignore
    priority        : IntProperty(default=0, name="Priority", description="Decides which group takes precedence in the modpack if files conflict. Higher number wins") # type: ignore

    group_files     : CollectionProperty(type=GroupFile) # type: ignore
    mod_options     : CollectionProperty(type=BlendModOption) # type: ignore
    corrections     : CollectionProperty(type=CorrectionEntry) # type: ignore
    base_phybs      : CollectionProperty(type=BasePhyb) # type: ignore
    sim_append      : StringProperty(
                            default="(Optional) Select a phyb...", 
                            name="Optional" , 
                            description="Simulator to append to all phybs"
                        ) # type: ignore

    show_folder     : BoolProperty(default=False, name="", description="Show the contents of the target folder") # type: ignore
    show_group      : BoolProperty(default=True, name="", description="Show the contents of the group") # type: ignore

    use_folder      : BoolProperty(default=True, name="", description="Creates an option for each file in the folder", update=_use_folder_change) # type: ignore
    valid_path      : BoolProperty(default=False) # type: ignore
    shared_game_path: BoolProperty(default=False) # type: ignore
    name_set        : BoolProperty(default=False) # type: ignore
    ya_sort         : BoolProperty(
                            name="Yet Another Sort",
                            description="When enabled, the group sorts model sizes according to YAB's regular size sorting",
                            default=True,
                            update=get_files
                        ) # type: ignore

    subfolder       : EnumProperty(
                            name= "",
                            default=0,
                            description= "Alternate folder for model files",
                            items= lambda self, context: self.get_subfolder()
                        )  # type: ignore
       
    def get_combinations(self) -> list[list[str]]:

        def calc_combinations(total_options: list) -> list[list]:
            combinations = [[]]
        
            for option in total_options:
                combinations.extend([combo + [option] for combo in combinations])
            
            return combinations
        
        if self.group_type == "Combining":
            total_options = [option.name for option in self.mod_options[:8]]
            return calc_combinations(total_options)
            
        elif self.group_type == "Phyb":
            total_options = [Path(phyb.path).stem for phyb in self.group_files[:8]]
            return calc_combinations(total_options)
        
        else:
            return [[option.name] for option in self.mod_options]
            
    
    if TYPE_CHECKING:
        idx             : str
        page            : str
        group_type      : str
        name            : str
        description     : str
        game_path       : str
        folder_path     : str
        priority        : int
        mod_options     : BlendCollection[BlendModOption]
        corrections     : BlendCollection[CorrectionEntry]
        base_phybs      : BlendCollection[BasePhyb]
        group_files     : BlendCollection[GroupFile]
        sim_append      : str
        show_folder     : bool
        show_group      : bool
        use_folder      : bool
        valid_path      : bool
        shared_game_path: bool
        name_set        : bool
        subfolder       : str
        ya_sort         : bool

class LoadedModpackGroup(PropertyGroup):
    group_value      : StringProperty() # type: ignore
    group_name       : StringProperty() # type: ignore
    group_description: StringProperty(default="") # type: ignore
    group_page       : IntProperty(default=0) # type: ignore
    group_priority   : IntProperty(default=0) # type: ignore

    if TYPE_CHECKING:
        group_value      : str
        group_name       : str
        group_description: str
        group_page       : int
        group_priority   : int


CLASSES = [    
    ModpackHelper,
    ModMetaEntry,
    ModFileEntry,
    CorrectionEntry,
    BasePhyb,
    GroupFile,
    BlendModOption,
    BlendModGroup,
    LoadedModpackGroup,
]