import os
import bpy

from itertools      import chain
from pathlib        import Path
from bpy.types      import PropertyGroup, Object, Context
from bpy.props      import StringProperty, EnumProperty, CollectionProperty, PointerProperty, BoolProperty, IntProperty, FloatProperty
from .util.penumbra import Modpack

def visible_meshobj() -> list[Object]:
    """Checks all visible objects and returns them if they contain a mesh."""
    context = bpy.context
    visible_meshobj = [obj for obj in context.scene.objects if obj.visible_get(view_layer=context.view_layer) and obj.type == "MESH"]

    return sorted(visible_meshobj, key=lambda obj: obj.name)

def safe_set_enum(obj, prop_name:str, value:str, default=""):
    """Safely set an enum property, falling back to default if value is invalid."""
    try:
        setattr(obj, prop_name, value)
    except TypeError:
        # Value not in enum items, use default
        try:
            setattr(obj, prop_name, default)
        except TypeError:
            # Even default failed, skip setting this property
            pass

def get_object_from_mesh(mesh_name:str) -> Object | None:
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.data.name == mesh_name:
            return obj
    return None

def scene_armatures() -> list[tuple[str, str, str]]:
        armatures = [("None", "None", ""), None]
        
        for obj in bpy.context.scene.objects:
            if obj.type == 'ARMATURE':
                armatures.append((obj.name, obj.name, "Armature"))
        
        return armatures

def modpack_data(context) -> None:
    props = get_file_properties()
    scene = context.scene
    props.loaded_pmp_groups.clear()

    blender_groups = props.pmp_mod_groups
    modpack_path = Path(props.modpack_dir)

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

    props.modpack_author  = modpack.meta.Author
    props.modpack_version = modpack.meta.Version

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
        props                = get_file_properties()
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

    name       : StringProperty(default="New Group", name="", description="Name of the group", update=lambda self, context: self.set_name()) # type: ignore
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
 
class LoadedModpackGroup(PropertyGroup):
    group_value      : StringProperty() # type: ignore
    group_name       : StringProperty() # type: ignore
    group_description: StringProperty(default="") # type: ignore
    group_page       : IntProperty(default=0) # type: ignore
    group_priority   : IntProperty(default=0) # type: ignore
    
class YAFileProps(PropertyGroup):

    GAME_SUFFIX = {".mdl", ".tex", ".phyb"}

    pmp_mod_groups: CollectionProperty(
        type=BlendModGroup
        ) # type: ignore
    
    loaded_pmp_groups: CollectionProperty(
        type=LoadedModpackGroup
        ) # type: ignore

    # Used to define operator behaviour.
    #   Keyword      Keyword       Default  Description
    extra_options = [
        ("create",   "backfaces",  True,   "Creates backface meshes on export based on existing vertex groups"),
        ("check",    "tris",       True,   "Verify that the meshes are triangulated"),
        ("force",    "yas",        False,  "This force enables YAS on any exported model and appends 'Yiggle' to their file name. Use this if you already exported regular models and want YAS alternatives"),
        ("remove",   "nonmesh",    True,   "Removes objects without any meshes. Cleans up unnecessary files from TT imports"),
        ("reorder",  "mesh_id",    True,   "Moves mesh identifier to the front of the object name"),
        ("update",   "material",   True,   "Changes material rendering and enables backface culling. Tries to normalise metallic and roughness values of TT materials"),
        ("keep",     "shapekeys",  True,   "Preserves vanilla clothing shape keys"),
        ("create",   "subfolder",  True,   "Creates a folder in your export directory for your exported body part"),
        ("rue",      "export",     True,   "Controls whether Rue is exported as a standalone body and variant, or only as a variant for Lava/Masc"),
        ("body",     "names",      False,  "Alwyays add body names on exported files or depending on how many bodies you export"),
        ("chest",    "g_category", False,  "Changes gamepath category"),
        ("hands",    "g_category", False,  "Changes gamepath category"),
        ("legs",     "g_category", False,  "Changes gamepath category"),
        ("feet",     "g_category", False,  "Changes gamepath category"),
    ]

    @staticmethod
    def set_extra_options() -> None:
        for (name, category, default, description) in YAFileProps.extra_options:
            category_lower = category.lower()
            name_lower = name.lower()
            
            prop_name = f"{name_lower}_{category_lower}"
            prop = BoolProperty(
                name="", 
                description=description,
                default=default, 
                )
            setattr(YAFileProps, prop_name, prop)

    def update_directory(self, context:Context, category:str) -> None:
        prop = context.scene.file_props
        actual_prop = f"{category}_dir"
        display_prop = f"{category}_display_dir"

        display_dir = getattr(prop, display_prop, "")

        if os.path.exists(display_dir):  
            setattr(prop, actual_prop, display_dir)

    def update_mod_enums(self, context):
        if self.modpack_replace:

            modpack_data(context)
        else:
            blender_groups = context.scene.pmp_mod_groups
            for blend_group in blender_groups:
                # old_value = blend_group.name_set
                # blend_group.name_set = True

                blend_group.idx = "New"
                # blend_group.name_set
            bpy.context.scene.loaded_pmp_groups.clear()
            
    ui_size_category: StringProperty(
        name="",
        subtype="DIR_PATH", 
        maxlen=255,
        )  # type: ignore

    file_man_ui: EnumProperty(
        name= "",
        description= "Select a manager",
        items= [
            ("IMPORT", "Import", "Import Files"),
            ("EXPORT", "Export", "Export models"),
            ("MODPACK", "Modpack", "Package mods"),
        ]
        )  # type: ignore




    armatures: EnumProperty(
        name="Armatures",
        description="Select an armature from the scene to parent meshes to",
        items=lambda self, context: scene_armatures(),
        default= 0,
    ) # type: ignore

    import_display_dir: StringProperty(
        name="Export Folder",
        default="Select Export Directory",  
        maxlen=255,
        update=lambda self, context: self.update_directory(context, 'import'),
        ) # type: ignore
    
    rename_import: StringProperty(
        name="",
        description="Renames the prefix of the selected meshes",
        default="",
        maxlen=255,
        )  # type: ignore

    file_gltf: BoolProperty(
        name="",
        description="Switch file format", 
        default=False,
        ) # type: ignore
    



    export_body_slot: EnumProperty(
        name= "",
        description= "Select a body slot",
        items= [
            ("Chest", "Chest", "Chest export options."),
            ("Legs", "Legs", "Leg export options."),
            ("Hands", "Hands", "Hand export options."),
            ("Feet", "Feet", "Feet export options."),
            ("Chest & Legs", "Chest & Legs", "When you want to export Chest with Leg models.")]
        )  # type: ignore

    export_total: IntProperty(default=0) # type: ignore

    export_progress: FloatProperty(default=0) # type: ignore

    export_step: IntProperty(default=0) # type: ignore

    export_time: FloatProperty(default=0) # type: ignore

    export_file_name: StringProperty(name="",
        default="",  
        maxlen=255,
        ) # type: ignore




    modpack_replace: BoolProperty(default=False, name="", description="Make new or update existing mod", update=lambda self, context: self.update_mod_enums(context)) # type: ignore

    modpack_display_dir: StringProperty(
        name="Modpack name.",
        default="",  
        maxlen=255,
        ) # type: ignore
    
    modpack_dir: StringProperty(
        default="Select Modpack",
        subtype="FILE_PATH", 
        maxlen=255,
        update=lambda self, context: modpack_data(context)
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

def selected_yas_vgroup() -> None:
    props = get_outfit_properties
    obj = bpy.context.active_object
    if props.yas_vgroups[0].name != "Mesh has no YAS Groups":
        try:
            obj.vertex_groups.active = obj.vertex_groups.get(props.yas_vgroups[props.yas_vindex].name)
        except:
            pass

class AnimationOptimise(PropertyGroup):
    triangulation: BoolProperty() # type: ignore
    show_armature: BoolProperty() # type: ignore

class YASVGroups(PropertyGroup):
    name: StringProperty() # type: ignore
    lock_weight: BoolProperty(
        name="",
        default=False,
        description="Maintain the relative weights for the group",
        update=lambda self, context: self.update_lock_weight(context)
        ) # type: ignore
    
    def update_lock_weight(self, context:Context) -> None:
        obj = context.active_object
        if obj.type == 'MESH':
            group = obj.vertex_groups.get(self.name)
            if group:
                group.lock_weight = self.lock_weight

class ShapeModifiers(PropertyGroup):
    name: StringProperty() # type: ignore
    icon: StringProperty() # type: ignore

class YAOutfitProps(PropertyGroup):

    animation_optimise    : CollectionProperty(type=AnimationOptimise) # type: ignore

    shape_modifiers_group : CollectionProperty(type=ShapeModifiers) # type: ignore

    yas_vgroups : CollectionProperty(type=YASVGroups) # type: ignore

    yas_vindex: IntProperty(name="YAS Group Index", description="Index of the YAS groups on the active object", update=lambda self, context:selected_yas_vgroup()) # type: ignore

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
        ("overview",  "category",   True,    "Enables part overview"),
        ("shapes",    "category",   False,   "Enables shape transfer menu"),
        ("mesh",      "category",   False,   "Enables mesh editing menu"),
        ("weights",   "category",   False,   "Enables weight editing menu"),
        ("armature",  "category",   False,   "Enables animation playback and pose/scaling menu"),
        ("scaling",   "armature",   False,   "Applies scaling to armature"),
        ("keep",      "modifier",   False,   "Keeps the modifier after applying. Unable to keep Data Transfers"),
        ("filter",    "vgroups",    True,    "Switches between showing all vertex groups or just YAS groups"),
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
    
    ui_buttons_list = [
    ("backfaces",   "expand",     "Opens the category"),
    ("modifiers",   "expand",     "Opens the category"),
    ("transp",      "expand",     "Opens the category"),
    
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
    
    @staticmethod
    def ui_buttons() -> None:
        for (name, category, description) in YAOutfitProps.ui_buttons_list:
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
            setattr(YAOutfitProps, prop_name, prop)

    def chest_controller_update(self, context:Context) -> None:
        props = context.scene.outfit_props
        key_blocks = get_object_from_mesh("Chest Controller").data.shape_keys.key_blocks
        for key in key_blocks:
            key.mute = True

        key_blocks[props.shape_chest_base.upper()].mute = False

    def get_vertex_groups(self, context:Context, obj:Object) -> list[tuple[str, str, str]]:
        if obj and obj.type == "MESH":
            return [("None", "None", "")] + [(group.name, group.name, "") for group in obj.vertex_groups]
        else:
            return [("None", "Select a target", "")]

    def scene_actions(self) -> list[tuple[str, str, str]]: 
        armature_actions = [("None", "None", ""), None]
    
        for action in bpy.data.actions:
            if action.id_root == "OBJECT":
                armature_actions.append((action.name , action.name, "Action"))
        return armature_actions
    
    def get_deform_modifiers(self, context:Context) -> list[tuple[str, str, str]]:
        modifiers = context.scene.shape_modifiers
        if not modifiers:
            return [("None", "No Valid Modifiers", "")]
        return [(modifier.name, modifier.name, "", modifier.icon, index) for index, modifier in enumerate(modifiers)]

    def set_action(self, context:Context) -> None:
        if self.armatures == "None":
            return
        if self.actions == "None":
            bpy.data.objects[self.armatures].animation_data.action = None
            return
    
        action = bpy.data.actions.get(self.actions)

        bpy.data.objects[self.armatures].animation_data.action = action
        if bpy.app.version >= (4, 4, 0):
            bpy.data.objects[self.armatures].animation_data.action_slot = action.slots[0]
        context.scene.frame_end = int(action.frame_end)

        if hasattr(YAOutfitProps, "animation_frame"):
            del YAOutfitProps.animation_frame
        
        prop = IntProperty(
            name="Current Frame",
            default=0,
            max=int(action.frame_end),
            min=0,
            update=lambda self, context: self.animation_frames(context)
            ) 
        setattr(YAOutfitProps, "animation_frame", prop)

    def animation_frames(self, context:Context) -> None:
        if context.screen.is_animation_playing:
            return None
        else:
            context.scene.frame_current = self.animation_frame
    
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
        description= "Select an overview",
        )  # type: ignore
    
    shapes_target: PointerProperty(
        type= Object,
        name= "",
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
    
    shape_modifiers: EnumProperty(
        name= "",
        description= "Select a deform modifier",
        items=lambda self, context: self.get_deform_modifiers(context)
        )  # type: ignore
    
    armatures: EnumProperty(
        name="Armatures",
        description="Select an armature from the scene",
        items=lambda self, context: scene_armatures(),
        default= 0,
    ) # type: ignore

    actions: EnumProperty(
        name="Animations",
        description="Select an animation from the scene",
        items=lambda self, context: self.scene_actions(),
        default= 0,
        update=lambda self, context: self.set_action(context)
    ) # type: ignore

    animation_frame: IntProperty(
        default=0,
        max=500,
        min=0,
        update=lambda self, context: self.animation_frames(context),
    ) # type: ignore

    pose_display_directory: StringProperty(
        default="Select .pose file",
        subtype="FILE_PATH", 
        maxlen=255,
        )  # type: ignore

def get_file_properties() -> YAFileProps:
    return bpy.context.scene.ya_file_props

def get_outfit_properties() -> YAOutfitProps:
    return bpy.context.scene.ya_outfit_props

CLASSES = [    
    ModpackHelper,
    ModMetaEntry,
    ModFileEntry,
    CorrectionEntry,
    BlendModOption,
    BlendModGroup,
    LoadedModpackGroup,
    YAFileProps,
    AnimationOptimise,
    YASVGroups,
    ShapeModifiers,
    YAOutfitProps
]

def set_addon_properties() -> None:
    bpy.types.Scene.ya_file_props = PointerProperty(
        type=YAFileProps)

    bpy.types.Scene.ya_outfit_props = PointerProperty(
        type=YAOutfitProps)

    YAFileProps.set_extra_options()
    YAOutfitProps.extra_options()
    YAOutfitProps.ui_buttons()

def remove_addon_properties() -> None:
    del bpy.types.Scene.ya_file_props
    del bpy.types.Scene.ya_outfit_props




