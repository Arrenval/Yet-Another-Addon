import os
import bpy

from typing          import Iterable, TYPE_CHECKING, Literal
from pathlib         import Path
from itertools       import chain
from bpy.types       import PropertyGroup, Object, Context, Armature
from bpy.props       import StringProperty, EnumProperty, CollectionProperty, PointerProperty, BoolProperty, IntProperty

from .utils.objects  import get_object_from_mesh
from .utils.typings  import BlendEnum, DevkitProps, DevkitWindowProps
from .utils.penumbra import Modpack


def modpack_data() -> None:
    window = get_window_properties()
    props  = get_file_properties()
    props.loaded_pmp_groups.clear()

    blender_groups = window.pmp_mod_groups
    modpack_path = Path(window.modpack_dir)

    if modpack_path.is_file():
        modpack = Modpack.from_archive(modpack_path)
    else:
        return

    for idx, group in enumerate(modpack.groups):
        new_option = props.loaded_pmp_groups.add()
        new_option.group_value = str(idx)
        new_option.group_name = group.Name
        new_option.group_description = group.Description
        new_option.group_page = group.Page
        new_option.group_priority = group.Priority

    window.modpack_author  = modpack.meta.Author
    window.modpack_version = modpack.meta.Version

    name_to_idx = {group.Name: str(idx) for idx, group in enumerate(modpack.groups)}
    for blend_group in blender_groups:
        try:
            blend_group.idx = name_to_idx[blend_group.name]
        except:
            blend_group.idx = "New"

class ModpackHelper(PropertyGroup):

    def check_valid_path(self):
        props           = get_file_properties()
        path:str        = self.game_path
        self.valid_path = path.startswith("chara") and path.endswith(tuple(props.GAME_SUFFIX))

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

    def final_folder(self) -> Path | Literal[False]:
        if self.subfolder != "None":
            folder = Path(self.folder_path) / Path(self.subfolder)
        else:
            folder = Path(self.folder_path)

        if str(folder).strip() != "" and folder.is_dir():
            return folder
        else:
            return False

    def get_folder_stats(self, model_check:bool=False) -> bool | dict:
        """Checks folder contents, if model_check is True, it only checks if there are any relevant model files."""

        model_suffix = [".fbx", ".mdl"]
        folder_stats = {}
        has_fbx      = False

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
                    has_fbx = True
                    folder_stats[file.stem]["fbx"] = file.stat().st_mtime
                elif file.suffix == ".mdl":
                    folder_stats[file.stem]["mdl"] = file.stat().st_mtime

            return folder_stats, has_fbx

    def check_gamepath_category(self) -> None:
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
         default="0",
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
    group_idx   : IntProperty(default=0) # type: ignore
    meta_entries: CollectionProperty(type=ModMetaEntry) # type: ignore
    file_entries: CollectionProperty(type=ModFileEntry) # type: ignore
    
    names: EnumProperty(
        name= "",
         default=0,
        description= "When these two groups are in the same combination, you can specify another entry to add",
        items= lambda self, context: self.get_possible_corrections(context)
        )  # type: ignore
    
    show_option     : BoolProperty(default=True, name="", description="Show the contents of the option") # type: ignore
    
    def get_possible_corrections(self, context:Context):
        props                = get_window_properties()
        group: BlendModGroup = props.pmp_mod_groups[self.group_idx]
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
    
    if TYPE_CHECKING:
        group_idx   : int
        file_entries: Iterable[ModFileEntry]
        meta_entries: Iterable[ModMetaEntry]
        names       : str
        show_option : bool 

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
        file_entries: Iterable[ModFileEntry]
        meta_entries: Iterable[ModMetaEntry]
        show_option : bool
    
class BlendModGroup(ModpackHelper):
    idx             : EnumProperty(
                        name= "",
                        default=1,
                        update=lambda self, context: self.set_group_values(),
                        description= "Select an option to replace",
                        items= lambda self, context: self.get_modpack_groups(context)
                        )   # type: ignore   
    page            : EnumProperty(
                        name= "",
                        default=0,
                        description= "Select a page for your group",
                        items= lambda self, context: self.get_groups_page(context)
                        )   # type: ignore 
    group_type      : EnumProperty(
                        name= "",
                        default="Single",
                        description= "Single, Multi or Combining",
                        update=lambda self, context: self.group_type_change(),
                        items= [
                            ("Single", "Single", "Exclusive options in a group"),
                            ("Multi", "Multi ", "Multiple selectable options in a group"),
                            ("Combining", "Combi ", "Combine multiple selectable groups")
                        ]
                        )   # type: ignore
    
    name            : StringProperty(default="New Group", name="", description="Name of the group", update=lambda self, context: self.set_name()) # type: ignore
    description     : StringProperty(default="", name="", description="Write something silly") # type: ignore
    game_path       : StringProperty(default="Paste path here...", name="", description="Path to the in-game file you want to replace", update=lambda self, context: self.check_valid_path()) # type: ignore
    folder_path     : StringProperty(default="Select a folder...", name="" , description="Folder with files top pack/convert", ) # type: ignore
    priority        : IntProperty(default=0, name="Priority", description="Decides which group takes precedence in the modpack if files conflict. Higher number wins") # type: ignore

    mod_options     : CollectionProperty(type=BlendModOption) # type: ignore
    corrections     : CollectionProperty(type=CorrectionEntry) # type: ignore

    show_folder     : BoolProperty(default=False, name="", description="Show the contents of the target folder") # type: ignore
    show_group      : BoolProperty(default=True, name="", description="Show the contents of the group") # type: ignore

    use_folder      : BoolProperty(default=True, name="", description="Creates an option for each file in the folder", update=lambda self, context: self.use_folder_change()) # type: ignore
    valid_path      : BoolProperty(default=False) # type: ignore
    shared_game_path: BoolProperty(default=False) # type: ignore
    name_set        : BoolProperty(default=False) # type: ignore

    subfolder  : EnumProperty(
        name= "",
        default=0,
        description= "Alternate folder for model files",
        items= lambda self, context: self.get_subfolder()
        )  # type: ignore

    def set_group_values(self):
        props   = get_file_properties()
        window  = get_window_properties()
        replace = window.modpack_replace

        modpack: list[LoadedModpackGroup] = props.loaded_pmp_groups
        
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

    def set_name(self):
        props = get_file_properties()
        self.name: str
        scene_groups: list[LoadedModpackGroup] = props.loaded_pmp_groups

        existing_names = [group.group_name.lower() for group in scene_groups]

        if self.name.lower() in chain(("", "new group"), existing_names) or not self.name.strip():
            self.name_set = False
        else:
            self.name_set = True

    def get_groups_page(self, context:Context) -> BlendEnum:
        props = get_file_properties()
        pages = set([option.group_page for option in props.loaded_pmp_groups])

        if len(pages) >= 1:
            return [(str(page), f"Pg: {page:<3}", "") for page in pages]
        else:
            return [("0", f"Pg: 0", "")]
        
    def get_modpack_groups(self, context:Context) -> BlendEnum:
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
        if self.group_type == "Combining":
            total_options = [option.name for option in self.mod_options[:8]]
            combinations = [[]]
        
            for option in total_options:
                combinations.extend([combo + [option] for combo in combinations])

            return combinations
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
        mod_options     : Iterable[BlendModOption]
        corrections     : Iterable[CorrectionEntry]
        show_folder     : bool
        show_group      : bool
        use_folder      : bool
        valid_path      : bool
        shared_game_path: bool
        name_set        : bool
        subfolder       : str
       

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

class YASVGroups(PropertyGroup):
    def update_lock_weight(self, context:Context) -> None:
        obj = context.active_object
        if obj.type == "MESH":
            group = obj.vertex_groups.get(self.name)
            if group:
                group.lock_weight = self.lock_weight

    name       : StringProperty() # type: ignore
    lock_weight: BoolProperty(
        name="",
        default=False,
        description="Maintain the relative weights for the group",
        update=update_lock_weight
        ) # type: ignore
    
    if TYPE_CHECKING:
        name       : str
        lock_weight: bool

class ShapeModifiers(PropertyGroup):
    name: StringProperty() # type: ignore
    icon: StringProperty() # type: ignore

    if TYPE_CHECKING:
        name: str
        icon: str

class AnimationOptimise(PropertyGroup):
    triangulation: BoolProperty() # type: ignore
    show_armature: BoolProperty() # type: ignore

    if TYPE_CHECKING:
        triangulation: bool
        show_armature: bool

class YAWindowProps(PropertyGroup):
    
    ui_buttons_list = [
        ("backfaces",   "expand",     "Opens the category"),
        ("modifiers",   "expand",     "Opens the category"),
        ("transp",      "expand",     "Opens the category"),
        
        ]
    
    extra_options = [
        ("overview", "category",   True,  "Enables part overview"),
        ("shapes",   "category",   False, "Enables shape transfer menu"),
        ("mesh",     "category",   False, "Enables mesh editing menu"),
        ("weights",  "category",   False, "Enables weight editing menu"),
        ("armature", "category",   False, "Enables animation playback and pose/scaling menu"),
        ("filter",   "vgroups",    True,  "Switches between showing all vertex groups or just YAS groups"),
        ("create",   "backfaces",  True,   "Creates backface meshes on export. Meshes need to be triangulated"),
        ("check",    "tris",       True,   "Verify that the meshes are triangulated"),
        ("keep",     "shapekeys",  True,   "Preserves game ready shape keys"),
        ("create",   "subfolder",  True,   "Creates a folder in your export directory for your exported body part"),
        ("rue",      "export",     True,   "Controls whether Rue is exported as a standalone body and variant, or only as a variant for Lava/Masc"),
        ("body",     "names",      False,  "Always add body names on exported files or depending on how many bodies you export"),
        ("chest",    "g_category", False,  "Changes gamepath category"),
        ("hands",    "g_category", False,  "Changes gamepath category"),
        ("legs",     "g_category", False,  "Changes gamepath category"),
        ("feet",     "g_category", False,  "Changes gamepath category"),
    ]

    @staticmethod
    def set_extra_options() -> None:
        for (name, category, default, description) in YAWindowProps.extra_options:
            category_lower = category.lower()
            name_lower = name.lower()
            
            prop_name = f"{name_lower}_{category_lower}"
            prop = BoolProperty(
                name="", 
                description=description,
                default=default, 
                )
            setattr(YAWindowProps, prop_name, prop)

    pmp_mod_groups: CollectionProperty(
        type=BlendModGroup
        ) # type: ignore
    
    animation_optimise: CollectionProperty(type=AnimationOptimise) # type: ignore


    export_prefix: StringProperty(
        name="",
        description="This will be prefixed to all your exported filenames",
        maxlen=255,
        )  # type: ignore

    file_man_ui: EnumProperty(
        name= "",
        description= "Select a manager",
        items= [
            ("IMPORT", "Import", "Import Files", "IMPORT", 0),
            ("EXPORT", "Export", "Export models", "EXPORT", 1),
            ("MODPACK", "Modpack", "Package mods", "NEWFOLDER", 2),
        ]
        )  # type: ignore

    export_body_slot: EnumProperty(
        name= "",
        description= "Select a body slot",
        items= [
            ("Chest", "Chest", "Chest export options.", "MOD_CLOTH", 0),
            ("Legs", "Legs", "Leg export options.", "BONE_DATA", 1),
            ("Hands", "Hands", "Hand export options.", "VIEW_PAN", 2),
            ("Feet", "Feet", "Feet export options.", "VIEW_PERSPECTIVE", 3),
            ("Chest & Legs", "Chest & Legs", "When you want to export Chest with Leg models.", "ARMATURE_DATA", 4)]
        )  # type: ignore

    remove_yas: EnumProperty(
        name= "",
        description= "Decides what modded bones to keep",
        items= [
            ("KEEP", "Keep", "Retains all modded bones"),
            ("NO_GEN", "No Genitalia", "Removes non-clothing related genitalia weights"),
            ("REMOVE", "Remove", "Removes all IVCS/YAS bones"),
        ]
        
        )  # type: ignore

    file_format: EnumProperty(
        name="",
        description="Switch file format", 
        items= [
            ("FBX", "FBX", "Export FBX."),
            ("GLTF", "GLTF", "Export modelsGLTF"),
        ]
        ) # type: ignore

    def update_ui(self, context:Context):
        for area in context.screen.areas:
            area.tag_redraw()

    waiting_import: BoolProperty(default=False, options={"SKIP_SAVE"}, update=update_ui) # type: ignore

    def get_deform_modifiers(self, context:Context) -> BlendEnum:
        modifiers = get_outfit_properties().shape_modifiers_group
        if not modifiers:
            return [("None", "No Valid Modifiers", "")]
        return [(modifier.name, modifier.name, "", modifier.icon, index) for index, modifier in enumerate(modifiers)]

    shape_modifiers: EnumProperty(
        name= "",
        description= "Select a deform modifier",
        items=get_deform_modifiers
        )  # type: ignore
    
    rename_import: StringProperty(
        name="",
        description="Renames the prefix of the selected meshes",
        default="",
        maxlen=255,
        )  # type: ignore
    

    def animation_frames(self, context:Context) -> None:
        if context.screen.is_animation_playing:
            return None
        else:
            context.scene.frame_current = self.animation_frame
    
    animation_frame: IntProperty(
        default=0,
        max=500,
        min=0,
        update=lambda self, context: self.animation_frames(context),
    ) # type: ignore

    ui_size_category: StringProperty(
        name="",
        maxlen=255,
        )  # type: ignore

    def update_mod_enums(self, context):
        file = get_file_properties()
        if self.modpack_replace:
            modpack_data()

        else:
            blender_groups = self.pmp_mod_groups
            for blend_group in blender_groups:
                blend_group.idx = "New"

            file.loaded_pmp_groups.clear()

    modpack_replace: BoolProperty(
        default=False, name="", 
        description="Make new or update existing mod", 
        update=update_mod_enums
        ) # type: ignore

    modpack_display_dir: StringProperty(
        name="Modpack name.",
        default="",  
        maxlen=255,
        ) # type: ignore
    
    modpack_dir: StringProperty(
        default="Select Modpack",
        subtype="FILE_PATH", 
        maxlen=255,
        update=lambda self, context: modpack_data()
        )  # type: ignore
    
    modpack_version: StringProperty(
        name="",
        description="Use semantic versioning",
        default="0.0.0", 
        maxlen=255,
        )  # type: ignore
    
    modpack_author: StringProperty(
        name="",
        default="", 
        description="Some cool person", 
        maxlen=255,
        )  # type: ignore

    modpack_rename_group: StringProperty(
        name="",
        default="",
        description="Choose a name for the target group. Can be left empty if replacing an existing one", 
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

    @staticmethod
    def ui_buttons() -> None:
        for (name, category, description) in YAWindowProps.ui_buttons_list:
            category_lower = category.lower()
            name_lower = name.lower()

            default = False
            if name_lower == "advanced":
                default = True
            
            prop_name = f"button_{name_lower}_{category_lower}"
            prop = BoolProperty(
                name="", 
                description=description,
                default=default, 
                )
            setattr(YAWindowProps, prop_name, prop)

    if TYPE_CHECKING:
        pmp_mod_groups   : Iterable[BlendModGroup]
        
        file_man_ui     : str
        export_body_slot: str
        shape_modifiers : str
        waiting_import  : bool
        shape_source    : Object
        file_format     : str
        export_prefix   : str
        remove_yas      : str

        modpack_replace     : bool
        modpack_display_dir : str
        modpack_dir         : str
        modpack_version     : str
        modpack_author      : str
        modpack_rename_group: str
        new_mod_name        : str
        new_mod_version     : str
        author_name         : str

        animation_optimise  : Iterable[AnimationOptimise]
        animation_frame     : int  

        # Created at registration
        overview_category: bool
        shapes_category  : bool
        mesh_category    : bool
        weights_category : bool
        armature_category: bool
        filter_vgroups   : bool

        button_backfaces_expand: bool
        button_modifiers_expand: bool
        button_transp_expand   : bool

        create_backfaces    : bool
        check_tris          : bool
        remove_nonmesh      : bool
        reorder_mesh_id     : bool
        update_material     : bool
        keep_shapekeys      : bool
        create_subfolder    : bool
        rue_export          : bool
        body_names          : bool
        chest_g_category    : bool
        hands_g_category    : bool
        legs_g_category     : bool
        feet_g_category     : bool
        ui_size_category    : str
        rename_import       : str

class YAFileProps(PropertyGroup):

    GAME_SUFFIX = {".mdl", ".tex", ".phyb"}

    # Used to define operator behaviour.
    #   Keyword      Keyword       Default  Description
    
    def update_directory(self, context:Context, category:str) -> None:
        prop = context.scene.file_props
        actual_prop = f"{category}_dir"
        display_prop = f"{category}_display_dir"

        display_dir = getattr(prop, display_prop, "")

        if os.path.exists(display_dir):  
            setattr(prop, actual_prop, display_dir)
            
    loaded_pmp_groups: CollectionProperty(
        type=LoadedModpackGroup
        ) # type: ignore
    
    import_armature: PointerProperty(
        type= Object,
        name= "",
        description= "New armature for imports",
        poll=lambda self, obj: obj.type == "ARMATURE"
        )  # type: ignore

    import_display_dir: StringProperty(
        name="Export Folder",
        default="Select Export Directory",  
        maxlen=255,
        update=lambda self, context: self.update_directory(context, 'import'),
        ) # type: ignore
    
    if TYPE_CHECKING:
        import_display_dir: str
        import_armature   : Object
        
class YAOutfitProps(PropertyGroup):

    shape_modifiers_group: CollectionProperty(type=ShapeModifiers) # type: ignore

    yas_vgroups : CollectionProperty(type=YASVGroups) # type: ignore

    YAS_BONES = {
    'n_root':              'Root', 
    'n_hara':              'Abdomen', 
    'j_kosi':              'Waist',

    'j_asi_a_l':           'Leg',              'j_asi_b_l':            'Knee',         'j_asi_c_l':            'Shin',           
    'j_asi_d_l':           'Foot',             'j_asi_e_l':            'Foot',     
    'j_asi_a_r':           'Leg',              'j_asi_b_r':            'Knee',         'j_asi_c_r':            'Shin',           
    'j_asi_d_r':           'Foot',             'j_asi_e_r':            'Foot', 

    'n_hizasoubi_l':       'Knee Pad',         'iv_daitai_phys_l':     'Back Thigh',   'ya_daitai_phys_l':     'Front Thigh',
    'n_hizasoubi_r':       'Knee Pad',         'iv_daitai_phys_r':     'Back Thigh',   'ya_daitai_phys_r':     'Front Thigh', 
    
    'iv_asi_oya_a_l':      'Toe',              'iv_asi_oya_b_l':       'Toe',              
    'iv_asi_hito_a_l':     'Toe',              'iv_asi_hito_b_l':      'Toe',  
    'iv_asi_naka_a_l':     'Toe',              'iv_asi_naka_b_l':      'Toe',  
    'iv_asi_kusu_a_l':     'Toe',              'iv_asi_kusu_b_l':      'Toe',  
    'iv_asi_ko_a_l':       'Toe',              'iv_asi_ko_b_l':        'Toe',

    'iv_asi_oya_a_r':      'Toe',              'iv_asi_oya_b_r':       'Toe',              
    'iv_asi_hito_a_r':     'Toe',              'iv_asi_hito_b_r':      'Toe',  
    'iv_asi_naka_a_r':     'Toe',              'iv_asi_naka_b_r':      'Toe',  
    'iv_asi_kusu_a_r':     'Toe',              'iv_asi_kusu_b_r':      'Toe',  
    'iv_asi_ko_a_r':       'Toe',              'iv_asi_ko_b_r':        'Toe',  

    'j_buki2_kosi_l':      'Weapon',           'j_buki2_kosi_r':       'Weapon',       'j_buki_kosi_l':        'Weapon',       'j_buki_kosi_r':        'Weapon',
    'j_buki_sebo_l':       'Weapon',           'j_buki_sebo_r':        'Weapon', 
    'n_buki_l':            'Weapon',           'n_buki_tate_l':        'Shield',
    'n_buki_r':            'Weapon',           'n_buki_tate_r':        'Shield',

    'j_sk_b_a_l':          'Skirt',            'j_sk_b_b_l':           'Skirt',        'j_sk_b_c_l':           'Skirt', 
    'j_sk_f_a_l':          'Skirt',            'j_sk_f_b_l':           'Skirt',        'j_sk_f_c_l':           'Skirt',           
    'j_sk_s_a_l':          'Skirt',            'j_sk_s_b_l':           'Skirt',        'j_sk_s_c_l':           'Skirt', 
    'j_sk_b_a_r':          'Skirt',            'j_sk_b_b_r':           'Skirt',        'j_sk_b_c_r':           'Skirt', 
    'j_sk_f_a_r':          'Skirt',            'j_sk_f_b_r':           'Skirt',        'j_sk_f_c_r':           'Skirt',  
    'j_sk_s_a_r':          'Skirt',            'j_sk_s_b_r':           'Skirt',        'j_sk_s_c_r':           'Skirt',

    'n_sippo_a':           'Tail',             'n_sippo_b':            'Tail',         'n_sippo_c':            'Tail',         'n_sippo_d':            'Tail',            'n_sippo_e':     'Tail',

    'iv_kougan_l':         'Balls',            'iv_kougan_r':          'Balls',    
    'iv_ochinko_a':        'Penis',            'iv_ochinko_b':         'Penis',        'iv_ochinko_c':         'Penis',        'iv_ochinko_d':         'Penis',           'iv_ochinko_e':  'Penis',        'iv_ochinko_f': 'Penis', 
    'iv_kuritto':          'Clitoris',         'iv_inshin_l':          'Labia',        'iv_inshin_r':          'Labia',        'iv_omanko':            'Vagina', 
    'iv_koumon':           'Anus',             'iv_koumon_l':          'Anus',         'iv_koumon_r':          'Anus', 

    'iv_shiri_l':          'Buttocks',         'iv_shiri_r':           'Buttocks', 
    'iv_kintama_phys_l':   'Balls',            'iv_kintama_phys_r':    'Balls',        
    'iv_funyachin_phy_a':  'Penis',            'iv_funyachin_phy_b':   'Penis',        'iv_funyachin_phy_c':   'Penis',        'iv_funyachin_phy_d':   'Penis', 
    'ya_fukubu_phys':      'Belly',            'ya_shiri_phys_l':      'Buttocks',     'ya_shiri_phys_r':      'Buttocks',
    'iv_fukubu_phys':      'Belly',            'iv_fukubu_phys_l':     'Abs',          'iv_fukubu_phys_r':     'Abs', 

    'j_sebo_a':            'Spine',            'j_sebo_b':             'Spine',        'j_sebo_c':             'Spine',
    'j_mune_l':            'Breasts',          'iv_c_mune_l':          'Breasts',      'j_mune_r':             'Breasts',      'iv_c_mune_r':          'Breasts', 
    'iv_kyokin_phys_l':    'Pecs',             'iv_kyokin_phys_r':     'Pecs',

    'j_kubi':              'Neck',             'j_kao':                'Face',         'j_ago':                'Chin', 
    'j_mimi_l':            'Ear',              'n_ear_a_l':            'Earring',      'n_ear_b_l':            'Earring',      
    'j_mimi_r':            'Ear',              'n_ear_a_r':            'Earring',      'n_ear_b_r':            'Earring', 
    'j_kami_a':            'Hair',             'j_kami_b':             'Hair',         
    'j_kami_f_l':          'Hair',             'j_kami_f_r':           'Hair', 

    'j_sako_l':            'Collar',           'j_ude_a_l':            'Arm',          'j_ude_b_l':            'Forearm',      'j_te_l':               'Hand', 
    'n_hkata_l':           'Shoulder',         'n_hhiji_l':            'Elbow',        'n_hte_l':              'Wrist',        'iv_nitoukin_l':        'Bicep',
    
    'j_sako_r':            'Collar',           'j_ude_a_r':            'Arm',          'j_ude_b_r':            'Forearm',      'j_te_r':               'Hand', 
    'n_hkata_r':           'Shoulder',         'n_hhiji_r':            'Elbow',        'n_hte_r':              'Wrist',        'iv_nitoukin_r':        'Bicep',

    'j_hito_a_l':          'Finger',           'j_hito_b_l':           'Finger',       'iv_hito_c_l':          'Finger', 
    'j_ko_a_l':            'Finger',           'j_ko_b_l':             'Finger',       'iv_ko_c_l':            'Finger', 
    'j_kusu_a_l':          'Finger',           'j_kusu_b_l':           'Finger',       'iv_kusu_c_l':          'Finger', 
    'j_naka_a_l':          'Finger',           'j_naka_b_l':           'Finger',       'iv_naka_c_l':          'Finger', 
    'j_oya_a_l':           'Finger',           'j_oya_b_l':            'Finger',

    'j_hito_a_r':          'Finger',           'j_hito_b_r':           'Finger',       'iv_hito_c_r':          'Finger', 
    'j_ko_a_r':            'Finger',           'j_ko_b_r':             'Finger',       'iv_ko_c_r':            'Finger', 
    'j_kusu_a_r':          'Finger',           'j_kusu_b_r':           'Finger',       'iv_kusu_c_r':          'Finger', 
    'j_naka_a_r':          'Finger',           'j_naka_b_r':           'Finger',       'iv_naka_c_r':          'Finger', 
    'j_oya_a_r':           'Finger',           'j_oya_b_r':            'Finger', 
    
    'n_hijisoubi_l':       'Elbow Pad',        'n_kataarmor_l':        'Shoulder Pad',
    'n_hijisoubi_r':       'Elbow Pad',        'n_kataarmor_r':        'Shoulder Pad',  
    
    'j_ex_top_a_l':        'Clothing',         'j_ex_top_b_l':         'Clothing',
    
    'n_throw': 'Throw'
    }

    outfit_buttons = [
        ("scaling",   "armature",   False,   "Applies scaling to armature"),
        ("keep",      "modifier",   False,   "Keeps the modifier after applying. Unable to keep Data Transfers"),
        ("all",       "keys",       False,   "Transfers all shape keys from source to target"),
        ("include",   "deforms",    False,   "Enable this to include deforms. If disabled only the shape key entries are added"),
        ("existing",  "only",       False,   "Only updates deforms of shape keys that already exist on the target"),
        ("adjust",    "overhang",   False,   "Tries to adjust for clothing that hangs off of the breasts"),
        ("add",       "shrinkwrap", False,   "Applies a shrinkwrap modifier when deforming the mesh. Remember to exclude parts of the mesh overlapping with the body"),
        ("seam",      "waist",      False,   "Applies the selected seam shape key to your mesh"),
        ("seam",      "wrist",      False,   "Applies the selected seam shape key to your mesh"),
        ("seam",      "ankle",      False,   "Applies the selected seam shape key to your mesh"),
        ("sub",       "shape_keys", False,   """Includes minor shape keys without deforms:
        - Squeeze
        - Push-Up
        - Omoi
        - Sag
        - Nip Nops"""),
        ]
    
    attr_dict = {
           "atr_nek": "Neck",
           "atr_ude": "Elbow",
           "atr_hij": "Wrist",
           "atr_arm": "Glove",
           "atr_kod": "Waist",
           "atr_hiz": "Knee",
           "atr_sne": "Shin",
           "atr_leg": "Boot",
           "atr_lpd": "Knee Pad",
        }
    
    @staticmethod
    def extra_options() -> None:
        for (name, category, default, description) in YAOutfitProps.outfit_buttons:
            category_lower = category.lower()
            name_lower = name.lower()
            
            prop_name = f"{name_lower}_{category_lower}"
            prop = BoolProperty(
                name="", 
                description=description,
                default=default, 
                )
            setattr(YAOutfitProps, prop_name, prop)
    
    def chest_controller_update(self, context:Context) -> None:
        props = context.scene.outfit_props
        key_blocks = get_object_from_mesh("Chest Controller").data.shape_keys.key_blocks
        for key in key_blocks:
            key.mute = True

        key_blocks[props.shape_chest_base.upper()].mute = False

    def get_vertex_groups(self, context:Context, obj:Object) -> BlendEnum:
        if obj and obj.type == "MESH":
            return [("None", "None", "")] + [(group.name, group.name, "") for group in obj.vertex_groups]
        else:
            return [("None", "Select a target", "")]

    def scene_actions(self) -> BlendEnum: 
        armature_actions = [("None", "None", ""), None]
    
        for action in bpy.data.actions:
            if action.id_root == "OBJECT":
                armature_actions.append((action.name , action.name, "Action"))
        return armature_actions
    
    def set_action(self, context:Context) -> None:
        if not self.armature:
            return
        if self.actions == "None":
            self.armature.animation_data.action = None
            return
    
        action = bpy.data.actions.get(self.actions)

        self.armature.animation_data.action = action
        if bpy.app.version >= (4, 4, 0):
            self.armature.animation_data.action_slot = action.slots[0]
        context.scene.frame_end = int(action.frame_end)

        if hasattr(YAWindowProps, "animation_frame"):
            del YAWindowProps.animation_frame
        
        prop = IntProperty(
            name="Current Frame",
            default=0,
            max=int(action.frame_end),
            min=0,
            update=lambda self, context: self.animation_frames(context)
            ) 
        setattr(YAWindowProps, "animation_frame", prop)

    def update_directory(self, context:Context, category:str) -> None:
        prop = context.scene.file_props
        actual_prop = f"{category}_directory"
        display_prop = f"{category}_display_directory"

        display_directory = getattr(prop, display_prop, "")

        if os.path.exists(display_directory):  
            setattr(prop, actual_prop, display_directory)

    def get_shape_key_enum(self, context:Context, obj:Object, new:bool=False) -> None:
        if obj is not None and obj.data.shape_keys:
            shape_keys = []
            if new:
                shape_keys.extend([("", "NEW:", ""),("None", "New Key", "")])
            shape_keys.append(("", "BASE:", ""))
            for index, key in enumerate(obj.data.shape_keys.key_blocks):
                if key.name.endswith(":"):
                    shape_keys.append(("", key.name, ""))
                    continue
                shape_keys.append((key.name, key.name, ""))
            return shape_keys
        else:
            return [("None", "New Key", "")]

    shapes_method: EnumProperty(
        name= "",
        description= "Select an overview",
        items= [
            ("Selected", "Selection", "Uses the selected mesh as the source"),
            ("Chest", "Chest", "Uses the YAB Chest mesh as source"),
            ("Legs", "Legs", "Uses the YAB leg mesh as source"),
            ("Seams", "Seams", "Transfer seam related shape keys"),
        ]
        )  # type: ignore
    
    shapes_source: PointerProperty(
        type= Object,
        name= "",
        description= "Shape key/driver source",
        )  # type: ignore
    
    shapes_target: PointerProperty(
        type= Object,
        name= "",
        description= "Shape key/driver source"
        )  # type: ignore

    shapes_source_enum: EnumProperty(
        name= "",
        description= "Select a shape key",
        items=lambda self, context: self.get_shape_key_enum(context, self.shapes_source)
        )  # type: ignore
    
    shapes_target_enum: EnumProperty(
        name= "",
        description= "Select a shape key",
        items=lambda self, context: self.get_shape_key_enum(context, self.shapes_target, new=True)
        )  # type: ignore

    shapes_corrections: EnumProperty(
        name= "",
        default= "None",
        description= "Choose level of Corrective Smooth",
        items= [("", "Select degree of smoothing", ""),
                ("None", "None", ""),
                ("Smooth", "Smooth", ""),
                ("Aggressive", "Aggresive", ""),]
        )  # type: ignore
    
    shape_chest_base: EnumProperty(
        name= "",
        description= "Select the base size",
        items= [
            ("Large", "Large", ""),
            ("Medium", "Medium", ""),
            ("Small", "Small", ""),
            ("Masc", "Masc", ""),
        ],
        update=lambda self, context: self.chest_controller_update(context)
        )  # type: ignore
    
    shape_leg_base: EnumProperty(
        name= "",
        description= "Select the base size",
        items= [
            ("Melon", "Watermelon Crushers", ""),
            ("Skull", "Skull Crushers", ""),
            ("Yanilla", "Yanilla", ""),
            ("Mini", "Mini", ""),
            ("Lavabod", "Lavabod", ""),
            ("Masc", "Masc", ""),
        ],
        update=lambda self, context: self.chest_controller_update(context)
        )  # type: ignore
    
    shape_seam_base: EnumProperty(
        name= "",
        description= "Select the base size, only affects waist seam",
        items= [
            ("YAB", "YAB", ""),
            ("Lavabod", "Lavabod", ""),
            ("Yanilla", "Yanilla", ""),
            ("Masc", "Masc", ""),
            ("Mini", "Mini", ""),
        ],
        update=lambda self, context: self.chest_controller_update(context)
        )  # type: ignore
    
    obj_vertex_groups: EnumProperty(
        name= "",
        description= "Select a group to pin, it will be ignored by any smoothing corrections",
        items=lambda self, context: self.get_vertex_groups(context, self.shapes_target)
        )  # type: ignore
    
    exclude_vertex_groups: EnumProperty(
        name= "",
        description= "Select a group to exclude from shrinkwrapping",
        items=lambda self, context: self.get_vertex_groups(context, self.shapes_target)
        )  # type: ignore
    
    actions: EnumProperty(
        name="Animations",
        description="Select an animation from the scene",
        items=lambda self, context: self.scene_actions(),
        default= 0,
        update=lambda self, context: self.set_action(context)
    ) # type: ignore

    outfit_armature: PointerProperty(
        type= Object,
        name= "",
        description= "Select an armature from the scene",
        poll=lambda self, obj: obj.type == "ARMATURE"
        )  # type: ignore

    pose_display_directory: StringProperty(
        default="Select .pose file",
        subtype="FILE_PATH", 
        maxlen=255,
        )  # type: ignore

    def set_yas_vgroups(self, context):
        obj = self.yas_source
        window = get_window_properties()
        update_groups = (window.weights_category and window.filter_vgroups and obj)

        if update_groups:
            self.yas_vgroups.clear()

            yas_groups = [group for group in obj.vertex_groups if group.name.startswith(("iv_", "ya_"))]
            if yas_groups:
                self.yas_empty = False
                for group in yas_groups:
                    new_group = self.yas_vgroups.add()
                    new_group.name = group.name
                    new_group.lock_weight = group.lock_weight

            else:
                new_group = self.yas_vgroups.add()
                new_group.name  = "Mesh has no YAS Groups"
                self.yas_empty = True

    def set_modifiers(self, context):
        obj    = self.mod_shape_source
        window = get_window_properties()

        update_modifiers = (window.mesh_category and window.button_modifiers_expand and obj)

        if update_modifiers:
            mod_types = {
                    "ARMATURE", "DISPLACE", "LATTICE", "MESH_DEFORM", "SIMPLE_DEFORM",
                    "WARP", "SMOOTH", "SHRINKWRAP", "SURFACE_DEFORM", "CORRECTIVE_SMOOTH",
                    "DATA_TRANSFER"
                }
            
            self.shape_modifiers_group.clear()
            modifiers = [modifier for modifier in obj.modifiers if modifier.type in mod_types]
            for modifier in modifiers:
                new_modifier = self.shape_modifiers_group.add()
                new_modifier.name = modifier.name
                new_modifier.icon = "MOD_SMOOTH" if "SMOOTH" in modifier.type else \
                                    "MOD_MESHDEFORM" if "DEFORM" in modifier.type else \
                                    f"MOD_{modifier.type}"
            
            if self.shape_modifiers_group and window.shape_modifiers == "":
                self.shape_modifiers = self.shape_modifiers_group[0].name

        else:
            self.shape_modifiers_group.clear()

    yas_source: PointerProperty(
        type= Object,
        name= "",
        description= "YAS source",
        update=set_yas_vgroups,

        )  # type: ignore
    
    yas_empty: BoolProperty(
        name="",
        default=False,
        ) # type: ignore
    
    def selected_yas_vgroup(self, context) -> None:
        obj = bpy.context.active_object
        if len(self.yas_vgroups) == 1 and self.yas_vgroups[0].name != "Mesh has no YAS Groups":
            try:
                obj.vertex_groups.active = obj.vertex_groups.get(self.yas_vgroups[self.yas_vindex].name)
            except:
                pass

    yas_vindex: IntProperty(name="YAS Group Index", description="Index of the YAS groups on the active object", update=selected_yas_vgroup) # type: ignore

    mod_shape_source: PointerProperty(
        type= Object,
        name= "",
        description= "YAS source",
        update=set_modifiers,

        )  # type: ignore

    if TYPE_CHECKING:
        loaded_pmp_groups      : Iterable[LoadedModpackGroup]
        shape_modifiers_group  : Iterable[ShapeModifiers]
        
        pose_display_directory : str
        
        shapes_method          : str
        shapes_source_enum     : str
        shapes_target_enum     : str
        shapes_corrections     : str
        shape_chest_base       : str
        shape_leg_base         : str
        shape_seam_base        : str
        obj_vertex_groups      : str
        exclude_vertex_groups  : str
        actions                : str
        
        shapes_source          : Object
        shapes_target          : Object
        outfit_armature        : Object

        yas_source       : Object
        yas_vindex       : int
        yas_vgroups      : Iterable[YASVGroups]
        yas_empty        : bool
        mod_shapes_source: Object
        
        # Created at registration
        scaling_armature       : bool
        keep_modifier          : bool
        all_keys               : bool
        include_deforms        : bool
        existing_only          : bool
        adjust_overhang        : bool
        add_shrinkwrap         : bool
        seam_waist             : bool
        seam_wrist             : bool
        seam_ankle             : bool
        sub_shape_keys         : bool


def get_window_properties() -> YAWindowProps:
    return bpy.context.window_manager.ya_window_props

def get_file_properties() -> YAFileProps:
    return bpy.context.scene.ya_file_props

def get_outfit_properties() -> YAOutfitProps:
    return bpy.context.scene.ya_outfit_props

def get_devkit_properties() -> DevkitProps | Literal[False]:
    if hasattr(bpy.context.scene, "ya_devkit_props"):
        return bpy.context.scene.ya_devkit_props
    elif hasattr(bpy.context.scene, "devkit_props"):
        return bpy.context.scene.devkit_props
    else:
        return False
    
def get_devkit_win_props() -> DevkitWindowProps | Literal[False]:
    if hasattr(bpy.context.window_manager, "ya_devkit_window"):
        return bpy.context.window_manager.ya_devkit_window
    elif hasattr(bpy.context.scene, "devkit_props"):
        return bpy.context.scene.devkit_props
    else:
        return False

def set_addon_properties() -> None:
    bpy.types.Scene.ya_file_props = PointerProperty(
        type=YAFileProps)
    
    bpy.types.WindowManager.ya_window_props = PointerProperty(
        type=YAWindowProps)

    bpy.types.Scene.ya_outfit_props = PointerProperty(
        type=YAOutfitProps)

    YAWindowProps.ui_buttons()
    YAWindowProps.set_extra_options()
    YAOutfitProps.extra_options()
    
def remove_addon_properties() -> None:
    del bpy.types.Scene.ya_file_props
    del bpy.types.WindowManager.ya_window_props
    del bpy.types.Scene.ya_outfit_props


CLASSES = [    
    ModpackHelper,
    ModMetaEntry,
    ModFileEntry,
    CorrectionEntry,
    BlendModOption,
    BlendModGroup,
    LoadedModpackGroup,
    YASVGroups,
    ShapeModifiers,
    AnimationOptimise,
    YAWindowProps,
    YAFileProps,
    YAOutfitProps
]




