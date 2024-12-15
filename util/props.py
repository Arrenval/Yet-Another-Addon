import os
import bpy

from pathlib              import Path
from bpy.types            import PropertyGroup
from ..file.modpack       import get_modpack_groups, modpack_data
from bpy.props            import StringProperty, EnumProperty, CollectionProperty, PointerProperty, BoolProperty, IntProperty, FloatProperty


def visible_meshobj():
    context = bpy.context
    visible_meshobj = [obj for obj in context.scene.objects if obj.visible_get(view_layer=context.view_layer) and obj.type == "MESH"]

    return sorted(visible_meshobj, key=lambda obj: obj.name)

def update_directory(category):
    prop = bpy.context.scene.file_props
    actual_prop = f"{category}_directory"
    display_prop = f"{category}_display_directory"

    display_directory = getattr(prop, display_prop, "")

    if os.path.exists(display_directory):  
        setattr(prop, actual_prop, display_directory)
        print (getattr(prop, actual_prop, ""))

def update_fbx_subfolder():
    folder = Path(bpy.context.scene.file_props.savemodpack_directory)
    props = bpy.context.scene.fbx_subfolder
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

def get_groups_page_ui():
    selection = bpy.context.scene.file_props.modpack_groups
    groups = [(option.group_value, option.group_page) for option in bpy.context.scene.pmp_group_options]
    for group in groups:
        if selection == group[0]:
                return [(str(group[1]), f"Pg: {group[1]:<3}", "")]

def get_groups_page():
    pages = set([option.group_page for option in bpy.context.scene.pmp_group_options])
    return [(str(page), f"Pg: {page:<3}", "") for page in pages]

def get_fbx_subfolder():
    return [(option.group_value, option.group_name, option.group_description) for option in bpy.context.scene.fbx_subfolder]

def get_object_from_mesh(mesh_name:str):
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.data.name == mesh_name:
            return obj
    return None

class ModpackGroups(PropertyGroup):
    group_value: bpy.props.StringProperty() # type: ignore
    group_name: bpy.props.StringProperty() # type: ignore
    group_description: bpy.props.StringProperty() # type: ignore
    group_page: bpy.props.IntProperty() # type: ignore

class FBXSubfolders(PropertyGroup):
    group_value: bpy.props.StringProperty() # type: ignore
    group_name: bpy.props.StringProperty() # type: ignore
    group_description: bpy.props.StringProperty() # type: ignore

class FileProps(PropertyGroup):

    ui_buttons_list = [
    ("modpack",  "expand",   "Opens the category"),
    ("modpack",  "replace",  "Make new or update existing mod")
    ]
    
    extra_buttons_list = [
        ("create",   "backfaces",  True,   "Creates backface meshes on export based on existing vertex groups"),
        ("check",    "tris",       True,   "Verify that the meshes have an active triangulation modifier"),
        ("force",    "yas",        False,  "This force enables YAS on any exported model and appends 'Yiggle' to their file name. Use this if you already exported regular models and want YAS alternatives"),
        ("fix",      "parent",     True,   "Parents the meshes to the devkit skeleton and removes non-mesh objects"),
        ("update",   "material",   True,   "Changes material rendering and enables backface culling"),
        ("keep",     "shapekeys",  True,   "Preserves vanilla clothing shape keys"),
        ("create",   "subfolder",  True,   "Creates a folder in your export directory for your exported body part"),
    ]

    @staticmethod
    def extra_options():
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
    def ui_buttons():
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
    
    fbx_subfolder: EnumProperty(
        name= "",
        description= "Alternate folder for fbx/mdl files",
        items= lambda self, context: get_fbx_subfolder()
        )  # type: ignore

    modpack_groups: EnumProperty(
        name= "",
        description= "Select an option to replace",
        items= lambda self, context: get_modpack_groups()
        )   # type: ignore
    
    modpack_page: EnumProperty(
        name= "",
        description= "Select a page for your option",
        items= lambda self, context: get_groups_page()
        )   # type: ignore
    
    modpack_ui_page: EnumProperty(
        name= "",
        description= "Option's page #",
        items= lambda self, context: get_groups_page_ui()
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
        maxlen=255

        )  # type: ignore
    
    loadmodpack_display_directory: StringProperty(
        name="Select PMP",
        default="Select Modpack",  
        maxlen=255,
        update=lambda self, context: update_directory('loadmodpack'),
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
        update=lambda self, context: update_directory('loadmodpack')
        )  # type: ignore
    
    savemodpack_directory: StringProperty(
        default="FBX folder", 
        maxlen=255,
        update=lambda self, context: update_fbx_subfolder()
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
            ("Import", "Import", "Import Files"),
            ("Export", "Export", "Export models"),
            ("Modpack", "Modpack", "Package mods"),
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
        update=lambda self, context: update_directory('export'),
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
        update=lambda self, context: update_directory('import'),
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

def chest_controller_update():
    props = bpy.context.scene.outfit_props
    key_blocks = get_object_from_mesh("Chest Controller").data.shape_keys.key_blocks
    for key in key_blocks:
        key.mute = True

    key_blocks[props.shape_key_base.upper()].mute = False

def get_vertex_groups():
    obj = bpy.context.active_object

    if obj and obj.type == "MESH":
        return [("None", "None", "")] + [(group.name, group.name, "") for group in obj.vertex_groups]
    else:
        return [("None", "Select a mesh", "")]

class OutfitProps(PropertyGroup):

    outfit_buttons = [
        ("add",      "shrinkwrap", False,  "Applies a shrinkwrap modifier when deforming the mesh. Remember to exclude parts of the mesh overlapping with the body"),
        ("sub",      "shape_keys", False,  """Includes minor shape keys without deforms:
        - Squeeze
        - Push-Up
        - Omoi
        - Sag
        - Nip Nops"""),
        ]
    
    @staticmethod
    def extra_options():
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

    outfit_ui: EnumProperty(
        name= "",
        description= "Select a manager",
        items= [
            ("Overview", "Overview", ""),
            ("Shapes", "Shapes", ""),
            ("Mesh", "Mesh", ""),
            ("Weights", "Weights", ""),
        ]
        )  # type: ignore
    
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
        update=lambda self, context: chest_controller_update()
        )  # type: ignore
    
    obj_vertex_groups: EnumProperty(
        name= "",
        description= "Select a group to pin",
        items=lambda self, context: get_vertex_groups()
        )  # type: ignore
    
    exclude_vertex_groups: EnumProperty(
        name= "",
        description= "Select a group to exclude from shrinkwrapping",
        items=lambda self, context: get_vertex_groups()
        )  # type: ignore
    

CLASSES = [
    ModpackGroups,
    FBXSubfolders,
    FileProps,
    OutfitProps
]

def set_addon_properties():
    bpy.types.Scene.file_props = PointerProperty(
        type=FileProps)
    
    bpy.types.Scene.outfit_props = PointerProperty(
        type=OutfitProps)
    
    bpy.types.Scene.pmp_group_options = bpy.props.CollectionProperty(
        type=ModpackGroups)
    
    bpy.types.Scene.fbx_subfolder = bpy.props.CollectionProperty(
        type=FBXSubfolders)
    
    FileProps.ui_buttons()
    FileProps.extra_options()
    OutfitProps.extra_options()

def remove_addon_properties():
    del bpy.types.Scene.file_props
    del bpy.types.Scene.pmp_group_options
    del bpy.types.Scene.outfit_props
    del bpy.types.Scene.fbx_subfolder
