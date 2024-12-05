import os
import bpy

from pathlib        import Path
from bpy.types      import PropertyGroup
from .file_manager  import get_modpack_groups, modpack_data
from bpy.props      import StringProperty, EnumProperty, CollectionProperty, PointerProperty, BoolProperty


def update_directory(category):
    prop = bpy.context.scene.pmp_props
    actual_prop = f"{category}_directory"
    display_prop = f"{category}_display_directory"

    display_directory = getattr(prop, display_prop, "")

    if os.path.exists(display_directory):  
        setattr(prop, actual_prop, display_directory)
        print (getattr(prop, actual_prop, ""))

def update_fbx_subfolder():
    folder = Path(bpy.context.scene.pmp_props.savemodpack_directory)
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
    selection = bpy.context.scene.pmp_props.modpack_groups
    groups = [(option.group_value, option.group_page) for option in bpy.context.scene.pmp_group_options]
    for group in groups:
        if selection == group[0]:
                return [(str(group[1]), f"Pg: {group[1]:<3}", "")]

def get_groups_page():
    pages = set([option.group_page for option in bpy.context.scene.pmp_group_options])
    return [(str(page), f"Pg: {page:<3}", "") for page in pages]

def get_fbx_subfolder():
    return [(option.group_value, option.group_name, option.group_description) for option in bpy.context.scene.fbx_subfolder]

class ModpackGroups(PropertyGroup):
    group_value: bpy.props.StringProperty() # type: ignore
    group_name: bpy.props.StringProperty() # type: ignore
    group_description: bpy.props.StringProperty() # type: ignore
    group_page: bpy.props.IntProperty() # type: ignore

class FBXSubfolders(PropertyGroup):
    group_value: bpy.props.StringProperty() # type: ignore
    group_name: bpy.props.StringProperty() # type: ignore
    group_description: bpy.props.StringProperty() # type: ignore

class ModpackProps(PropertyGroup):

    ui_buttons_list = [
    ("modpack",  "expand",   "Opens the category"),
    ("modpack",  "replace",  "Make new or update existing mod")
    ]
   
    @staticmethod
    def ui_buttons():
        for (name, category, description) in ModpackProps.ui_buttons_list:
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
            setattr(ModpackProps, prop_name, prop)
    
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
 
classes = [
    ModpackGroups,
    FBXSubfolders,
    ModpackProps
]

def set_addon_properties():
    bpy.types.Scene.pmp_props = PointerProperty(
        type=ModpackProps)
    
    bpy.types.Scene.pmp_group_options = bpy.props.CollectionProperty(
        type=ModpackGroups)
    
    bpy.types.Scene.fbx_subfolder = bpy.props.CollectionProperty(
        type=FBXSubfolders)
    
    ModpackProps.ui_buttons()
