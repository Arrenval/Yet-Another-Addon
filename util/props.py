import os
import bpy
import json

from pathlib   import Path
from zipfile   import ZipFile
from .penumbra import ModGroups, ModMeta
from bpy.types import PropertyGroup, Object, Context
from bpy.props import StringProperty, EnumProperty, CollectionProperty, PointerProperty, BoolProperty, IntProperty, FloatProperty


def visible_meshobj() -> list[Object]:
    context = bpy.context
    visible_meshobj = [obj for obj in context.scene.objects if obj.visible_get(view_layer=context.view_layer) and obj.type == "MESH"]

    return sorted(visible_meshobj, key=lambda obj: obj.name)

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

class ModpackGroups(PropertyGroup):
    group_value: bpy.props.StringProperty() # type: ignore
    group_name: bpy.props.StringProperty() # type: ignore
    group_description: bpy.props.StringProperty(default="") # type: ignore
    group_page: bpy.props.IntProperty(default=0) # type: ignore

class FBXSubfolders(PropertyGroup):
    group_value: bpy.props.StringProperty(default="None") # type: ignore
    group_name: bpy.props.StringProperty(default="None") # type: ignore
    group_description: bpy.props.StringProperty(default="") # type: ignore

def modpack_data(context) -> None:
    scene = context.scene
    scene.pmp_group_options.clear()
    modpack = Path(scene.file_props.loadmodpack_directory)

    new_option = scene.pmp_group_options.add()
    new_option.group_value = str(0)
    new_option.group_name = "New Group"  
    new_option.group_description = ""

    if modpack.is_file():
        with ZipFile(modpack, "r") as pmp:
            for file_name in pmp.namelist():
                if file_name.count('/') == 0 and file_name.startswith("group") and file_name.endswith(".json"):
                    number = lambda name: ''.join(char for char in name if char.isdigit())
                    group_name, group_page = modpack_group_data(file_name, pmp, data="name")

                    new_option = context.scene.pmp_group_options.add()
                    new_option.group_value = str(number(file_name))
                    new_option.group_name = group_name
                    new_option.group_description = file_name
                    new_option.group_page = group_page
 
            with pmp.open("meta.json") as meta:
                meta_contents = json.load(meta)

                mod_meta = ModMeta.from_dict(meta_contents)
                scene.file_props.loadmodpack_version = mod_meta.Version
                scene.file_props.loadmodpack_author = mod_meta.Author
    
def modpack_group_data(file_name:str, pmp:ZipFile, data:str) -> str | tuple[str,int] | ModGroups:
    try:
        with pmp.open(file_name) as file:
            file_contents = json.load(file)
                     
            group_data = ModGroups.from_dict(file_contents)
     
            if data == "name":
                return str(group_data.Name), int(group_data.Page)
            if data == "all":
                return group_data

    except Exception as e:
        return f"ERROR: {file_name[10:-4]}" if data == "all" else f"ERROR: {file_name[10:-4]}", 0   
  
def get_modpack_groups() -> list[tuple[str, str, str]]:
        modpack = bpy.context.scene.pmp_group_options
        return [(option.group_value, option.group_name, option.group_description) for option in modpack]

class FileProps(PropertyGroup):

    ui_buttons_list = [
    ("modpack",  "expand",   "Opens the category"),
    ("modpack",  "replace",  "Make new or update existing mod")
    ]
    
    extra_buttons_list = [
        ("create",   "backfaces",  True,   "Creates backface meshes on export based on existing vertex groups"),
        ("check",    "tris",       True,   "Verify that the meshes are triangulated"),
        ("force",    "yas",        False,  "This force enables YAS on any exported model and appends 'Yiggle' to their file name. Use this if you already exported regular models and want YAS alternatives"),
        ("remove",   "nonmesh",    True,   "Removes objects without any meshes. Cleans up unnecessary files from TT imports"),
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
    def extra_options() -> None:
        for (name, category, default, description) in FileProps.extra_buttons_list:
            category_lower = category.lower()
            name_lower = name.lower()
            
            prop_name = f"{name_lower}_{category_lower}"
            prop = BoolProperty(
                name="", 
                description=description,
                default=default, 
                )
            setattr(FileProps, prop_name, prop)

    @staticmethod
    def ui_buttons() -> None:
        for (name, category, description) in FileProps.ui_buttons_list:
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
            setattr(FileProps, prop_name, prop)
    
    def update_directory(self, context:Context, category:str) -> None:
        prop = context.scene.file_props
        actual_prop = f"{category}_directory"
        display_prop = f"{category}_display_directory"

        display_directory = getattr(prop, display_prop, "")

        if os.path.exists(display_directory):  
            setattr(prop, actual_prop, display_directory)
           
    def update_fbx_subfolder(self, context:Context) -> None:
        folder = Path(context.scene.file_props.savemodpack_directory)
        props = context.scene.fbx_subfolder
        props.clear()
        slot_dir = ["Chest", "Legs", "Hands", "Feet", "Chest & Legs"]
        
        subfolders = [dir for dir in folder.glob("*") if dir.is_dir() and any(slot in dir.name for slot in slot_dir)]

        new_option = props.add()
        new_option.group_value = "None"
        new_option.group_name = "None"  
        new_option.group_description = ""

        for subfolder in subfolders:
            new_option = props.add()
            new_option.group_value = subfolder.name
            new_option.group_name = subfolder.name  
            new_option.group_description = ""

    def get_groups_page(self, context:Context) -> list[tuple[str, str, str]]:
        pages = set([option.group_page for option in context.scene.pmp_group_options])
        return [(str(page), f"Pg: {page:<3}", "") for page in pages]

    def get_fbx_subfolder(self, context:Context) -> list[tuple[str, str, str]]:
        return [(option.group_value, option.group_name, option.group_description) for option in context.scene.fbx_subfolder]

    def get_groups_page_ui(self, context:Context) -> list[tuple[str, str, str]]:
        selection = context.scene.file_props.modpack_groups
        groups = [(option.group_value, option.group_page) for option in context.scene.pmp_group_options]
        for group in groups:
            if selection == group[0]:
                    return [(str(group[1]), f"Pg: {group[1]:<3}", "")]
    
    def check_gamepath_category(self, context:Context) -> None:
        self.game_model_path:str
        if self.game_model_path.startswith("chara") and self.game_model_path.endswith("mdl"):
            category = self.game_model_path.split("_")[-1].split(".")[0]
            match category:
                case "top":
                    context.scene.file_props.chest_g_category = True
                    context.scene.file_props.hands_g_category = False
                    context.scene.file_props.legs_g_category  = False
                    context.scene.file_props.feet_g_category  = False
                case "glv":
                    context.scene.file_props.chest_g_category = False
                    context.scene.file_props.hands_g_category = True
                    context.scene.file_props.legs_g_category  = False
                    context.scene.file_props.feet_g_category  = False
                case "dwn":
                    context.scene.file_props.chest_g_category = False
                    context.scene.file_props.hands_g_category = False
                    context.scene.file_props.legs_g_category  = True
                    context.scene.file_props.feet_g_category  = False
                case "sho":
                    context.scene.file_props.chest_g_category = False
                    context.scene.file_props.hands_g_category = False
                    context.scene.file_props.legs_g_category  = False
                    context.scene.file_props.feet_g_category  = True

    armatures: EnumProperty(
        name="Armatures",
        description="Select an armature from the scene to parent meshes to",
        items=lambda self, context: scene_armatures(),
        default= 0,
    ) # type: ignore
 
    fbx_subfolder: EnumProperty(
        name= "",
        description= "Alternate folder for fbx/mdl files",
        items= lambda self, context: self.get_fbx_subfolder(context)
        )  # type: ignore

    modpack_groups: EnumProperty(
        name= "",
        description= "Select an option to replace",
        items= lambda self, context: get_modpack_groups()
        )   # type: ignore
    
    modpack_page: EnumProperty(
        name= "",
        description= "Select a page for your option",
        items= lambda self, context: self.get_groups_page(context)
        )   # type: ignore
    
    modpack_ui_page: EnumProperty(
        name= "",
        description= "Option's page #",
        items= lambda self, context: self.get_groups_page_ui(context)
        )   # type: ignore
    
    mod_group_type: EnumProperty(
        name= "",
        description= "Single or Multi",
        items= [
            ("Single", "Single", "Exclusive options in a group"),
            ("Multi", "Multi ", "Multiple selectable options in a group")

        ]
        )   # type: ignore
    
    pmp_group_options: CollectionProperty(type=ModpackGroups) # type: ignore

    textools_directory: StringProperty(
        name="ConsoleTools Directory",
        subtype="FILE_PATH", 
        maxlen=255,
        options={'HIDDEN'},
        )  # type: ignore
    
    consoletools_status: StringProperty(
        default="Check for ConsoleTools:",
        maxlen=255

        )  # type: ignore
    
    game_model_path: StringProperty(
        name="",
        description="Path to the model you want to replace",
        default="Paste path here",
        maxlen=255,
        update=lambda self, context: self.check_gamepath_category(context)

        )  # type: ignore
    
    loadmodpack_display_directory: StringProperty(
        name="Select PMP",
        default="Select Modpack",  
        maxlen=255,
        update=lambda self, context: self.update_directory(context, 'loadmodpack'),
        ) # type: ignore
    
    loadmodpack_directory: StringProperty(
        default="Select Modpack",
        subtype="FILE_PATH", 
        maxlen=255,
        update=lambda self, context: modpack_data(context)
        )  # type: ignore
    
    loadmodpack_version: StringProperty(
        name="",
        description="Use semantic versioning",
        default="", 
        maxlen=255,
        )  # type: ignore
    
    loadmodpack_author: StringProperty(
        default="", 
        maxlen=255,
        )  # type: ignore

    savemodpack_display_directory: StringProperty(
        name="",
        default="FBX folder",
        description="FBX location and/or mod export location", 
        maxlen=255,
        update=lambda self, context: self.update_directory(context, 'loadmodpack')
        )  # type: ignore
    
    savemodpack_directory: StringProperty(
        default="FBX folder", 
        maxlen=255,
        update=lambda self, context: self.update_fbx_subfolder(context)
        )  # type: ignore
    
    modpack_rename_group: StringProperty(
        name="",
        default="",
        description="Choose a name for the target group. Can be left empty if replacing an existing one", 
        maxlen=255,
        )  # type: ignore
    
    modpack_progress: StringProperty(
        default="",
        description="Keeps track of the modpack progress", 
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

    export_display_directory: StringProperty(
        name="Export Folder",
        default="Select Export Directory",  
        maxlen=255,
        update=lambda self, context: self.update_directory(context, 'export'),
        ) # type: ignore
    
    export_directory: StringProperty(
        default="Select Export Directory",
        subtype="DIR_PATH", 
        maxlen=255,
        )  # type: ignore
    
    export_total: IntProperty(default=0) # type: ignore

    export_progress: FloatProperty(default=0) # type: ignore

    export_step: IntProperty(default=0) # type: ignore

    export_time: FloatProperty(default=0) # type: ignore

    export_file_name: StringProperty(name="",
        default="",  
        maxlen=255,
        ) # type: ignore

    import_display_directory: StringProperty(
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
    
    ui_size_category: StringProperty(
        name="",
        subtype="DIR_PATH", 
        maxlen=255,
        )  # type: ignore

def selected_yas_vgroup() -> None:
    obj = bpy.context.active_object
    if bpy.context.scene.yas_vgroups[0].name != "Mesh has no YAS Groups":
        try:
            obj.vertex_groups.active = obj.vertex_groups.get(bpy.context.scene.yas_vgroups[bpy.context.scene.yas_vindex].name)
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

class OutfitProps(PropertyGroup):

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
        ("adjust",    "overhang",   False,   "Tries to adjust for clothing that hangs off of the breasts"),
        ("add",       "shrinkwrap", False,   "Applies a shrinkwrap modifier when deforming the mesh. Remember to exclude parts of the mesh overlapping with the body"),
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
        for (name, category, default, description) in OutfitProps.outfit_buttons:
            category_lower = category.lower()
            name_lower = name.lower()
            
            prop_name = f"{name_lower}_{category_lower}"
            prop = BoolProperty(
                name="", 
                description=description,
                default=default, 
                )
            setattr(OutfitProps, prop_name, prop)
    
    @staticmethod
    def ui_buttons() -> None:
        for (name, category, description) in OutfitProps.ui_buttons_list:
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
            setattr(OutfitProps, prop_name, prop)

    def chest_controller_update(self, context:Context) -> None:
        props = context.scene.outfit_props
        key_blocks = get_object_from_mesh("Chest Controller").data.shape_keys.key_blocks
        for key in key_blocks:
            key.mute = True

        key_blocks[props.shape_key_base.upper()].mute = False

    def get_vertex_groups(self, context:Context) -> list[tuple[str, str, str]]:
        obj = context.active_object

        if obj and obj.type == "MESH":
            return [("None", "None", "")] + [(group.name, group.name, "") for group in obj.vertex_groups]
        else:
            return [("None", "Select a mesh", "")]

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

        if hasattr(OutfitProps, "animation_frame"):
            del OutfitProps.animation_frame
        
        prop = IntProperty(
            name="Current Frame",
            default=0,
            max=int(action.frame_end),
            min=0,
            update=lambda self, context: self.animation_frames(context)
            ) 
        setattr(OutfitProps, "animation_frame", prop)

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

    shape_key_source: EnumProperty(
        name= "",
        description= "Select an overview",
        items= [
            ("Selected", "Selected", "Uses the selected mesh as the source"),
            ("Chest", "Chest", "Uses the YAB Chest mesh as source"),
            ("Legs", "Legs", "Uses the YAB leg mesh as source"),
        ]
        )  # type: ignore
    
    shape_key_base: EnumProperty(
        name= "",
        description= "Select the base size",
        items= [
            ("Large", "Large", ""),
            ("Medium", "Medium", ""),
            ("Small", "Small", ""),
        ],
        update=lambda self, context: self.chest_controller_update(context)
        )  # type: ignore
    
    obj_vertex_groups: EnumProperty(
        name= "",
        description= "Select a group to pin",
        items=lambda self, context: self.get_vertex_groups(context)
        )  # type: ignore
    
    exclude_vertex_groups: EnumProperty(
        name= "",
        description= "Select a group to exclude from shrinkwrapping",
        items=lambda self, context: self.get_vertex_groups(context)
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

CLASSES = [
    ModpackGroups,
    FBXSubfolders,
    FileProps,
    AnimationOptimise,
    YASVGroups,
    ShapeModifiers,
    OutfitProps
]

def set_addon_properties() -> None:
    bpy.types.Scene.file_props = PointerProperty(
        type=FileProps)

    bpy.types.Scene.outfit_props = PointerProperty(
        type=OutfitProps)

    bpy.types.Scene.yas_vgroups = CollectionProperty(
        type=YASVGroups)
    
    bpy.types.Scene.yas_vindex = IntProperty(name="YAS Group Index", description="Index of the YAS groups on the active object", update=lambda self, context:selected_yas_vgroup())
    
    bpy.types.Scene.pmp_group_options = bpy.props.CollectionProperty(
        type=ModpackGroups)
    
    bpy.types.Scene.animation_optimise = bpy.props.CollectionProperty(
        type=AnimationOptimise)
    
    bpy.types.Scene.fbx_subfolder = bpy.props.CollectionProperty(
        type=FBXSubfolders)
    
    bpy.types.Scene.shape_modifiers = bpy.props.CollectionProperty(
        type=ShapeModifiers)
    
    FileProps.ui_buttons()
    FileProps.extra_options()
    OutfitProps.extra_options()
    OutfitProps.ui_buttons()

def remove_addon_properties() -> None:
    del bpy.types.Scene.file_props
    del bpy.types.Scene.outfit_props
    del bpy.types.Scene.yas_vgroups
    del bpy.types.Scene.yas_vindex
    del bpy.types.Scene.pmp_group_options
    del bpy.types.Scene.animation_optimise
    del bpy.types.Scene.fbx_subfolder
    del bpy.types.Scene.shape_modifiers
