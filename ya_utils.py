import bpy
import os

from ya_file_manager import modpack_groups_list
from bpy.types import Operator, PropertyGroup
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty


#       Shapes:         (Name,          Slot/Misc,      Category, Description,                                           Body,             Shape Key)
all_shapes = {
        "Large":        ("Large",       "Chest",        "Large",  "Standard Large",                                      "",               ""),
        "Omoi":         ("Omoi",        "Chest",        "Large",  "Large, but saggier",                                  "",               ""),
        "Sugoi Omoi":   ("Sugoi Omoi",  "Chest",        "Large",  "Omoi, but saggier",                                   "",               ""),
        "Medium":       ("Medium",      "Chest",        "Medium", "Standard Medium",                                     "",               "MEDIUM ----------------------------"),
        "Sayonara":     ("Sayonara",    "Chest",        "Medium", "Medium with more separation",                         "",               ""),
        "Tsukareta":    ("Tsukareta",   "Chest",        "Medium", "Medium, but saggier",                                 "",               ""),
        "Tsukareta+":   ("Tsukareta+",  "Chest",        "Medium", "Tsukareta, but saggier",                              "",               ""),
        "Mini":         ("Mini",        "Chest",        "Medium", "Medium, but smaller",                                 "",               ""),
        "Small":        ("Small",       "Chest",        "Small",  "Standard Small",                                      "",               "SMALL ------------------------------"),
        "Rue":          ("Rue",         "Chest",        "",       "Adds tummy",                                          "",               "Rue"),
        "Buff":         ("Buff",        "Chest",        "",       "Adds muscle",                                         "",               "Buff"),
        "Piercings":    ("Piercings",   "Chest",        "",       "Adds piercings",                                      "",               ""),
        "Rue Legs":     ("Rue",         "Legs",         "",       "Adds tummy and hip dips.",                            "",               "Rue"),
        "Melon":        ("Melon",       "Legs",         "Legs",   "For crushing melons",                                 "",               ""),
        "Skull":        ("Skull",       "Legs",         "Legs",   "For crushing skulls",                                 "",               "Skull Crushers"),
        "Small Butt":   ("Small Butt",  "Legs",         "Butt",   "Not actually small",                                  "",               "Small Butt"),
        "Mini Legs":    ("Mini",        "Legs",         "Legs",   "Smaller legs",                                        "",               "Mini"),
        "Soft Butt":    ("Soft Butt",   "Legs",         "Butt",   "Less perky butt",                                     "",               "Soft Butt"),
        "Hip Dips":     ("Hip Dips",    "Legs",         "Hip",    "Removes hip dips on Rue, adds them on YAB",           "",               ""),
        "Gen A":        ("Gen A",       "Legs",         "Vagina", "Labia majora",                                        "",               ""),
        "Gen B":        ("Gen B",       "Legs",         "Vagina", "Visible labia minora",                                "",               "Gen B"),
        "Gen C":        ("Gen C",       "Legs",         "Vagina", "Open vagina",                                         "",               "Gen C"),
        "Gen SFW":      ("Gen SFW",     "Legs",         "Vagina", "Barbie doll",                                         "",               "Gen SFW"), 
        "Pubes":        ("Pubes",       "Legs",         "Pubes",  "Adds pubes",                                          "",               ""),
        "YAB Hands":    ("YAB",         "Hands",        "Hands",  "YAB hands",                                           "",               ""),
        "Rue Hands":    ("Rue",         "Hands",        "Hands",  "Changes hand shape to Rue",                           "",               "Rue"),
        "Long":         ("Long",        "Hands",        "Nails",  "They're long",                                        "",               ""),
        "Short":        ("Short",       "Hands",        "Nails",  "They're short",                                       "",               "Short Nails"),
        "Ballerina":    ("Ballerina",   "Hands",        "Nails",  "Some think they look like shoes",                     "",               "Ballerina"),
        "Stabbies":     ("Stabbies",    "Hands",        "Nails",  "You can stab someone's eyes with these",              "",               "Stabbies"),
        "Straight":     ("Straight",    "Hands",        "Nails",  "When you want to murder instead",                     "",               ""),
        "Curved":       ("Curved",      "Hands",        "Nails",  "If you want to murder them a bit more curved",        "",               "Curved"),
        "YAB Feet":     ("YAB",         "Feet",         "Feet",   "YAB feet",                                            "",               ""),
        "Rue Feet":     ("Rue",         "Feet",         "Feet",   "Changes foot shape to Rue",                           "",               "Rue"),
        "Clawsies":     ("Clawsies",    "Feet",         "Claws",  "Good for kicking",                                    "",               ""),
        }

def yas_state(self, context):
    show_modifier = self.toggle_yas
    
    modifier = self.modifiers.get("YAS Toggle")
    
    if modifier:
        modifier.show_viewport = show_modifier
        
def yas_gen_state(self, context):
    show_modifier = self.toggle_yas_gen
    
    modifier = self.modifiers.get("YAS Genitalia Toggle")
    
    if modifier:
        modifier.show_viewport = show_modifier

def get_object_from_mesh(mesh_name):
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.data.name == mesh_name:
            return obj
    return None

def get_chest_size_keys(chest_subsize):
    """category, sizekey"""
    chest_category = get_chest_category(chest_subsize)
    
    size_key = {
        "Large": "LARGE -------------------------------",
        "Medium": "MEDIUM ----------------------------",
        "Small": "SMALL ------------------------------"
    }
    return size_key[chest_category]

def get_chest_category(size):
    """subsize, category"""
    if all_shapes[size][1] == "Chest":
        return all_shapes[size][2]
    else:
        return None

def get_shape_presets(size):
        """subsize, [shapekey, value]"""
        shape_presets = {
        "Large":        {"Squeeze" : 0.3,    "Squish" : 0.0,  "Push-Up" : 0.0, "Omoi" : 0.0, "Sag" : 0.0, "Nip Nops" : 0.0},
        "Omoi":         {"Omoi" : 1.0, "Sag" : 0.0},
        "Sugoi Omoi":   {"Omoi" : 1.0, "Sag" : 1.0},
        "Medium":       {"Squeeze" : 0.0,  "Squish" : 0.0, "Push-Up" : 0.0, "Mini" : 0.0, "Sayonara" : 0.0, "Sag" : 0.0, "Nip Nops" : 0.0},
        "Sayonara":     {"Sayonara" : 1.0, "Sag" : 0.0},
        "Tsukareta":    {"Sag" : 0.6},
        "Tsukareta+":   {"Sag" : 1.0},
        "Mini":         {"Mini" : 1.0},
        "Small":        {"Squeeze" : 0.0, "Nip Nops" : 0.0}
        }
        return shape_presets[size]

def has_shape_keys(ob):
        if ob and ob.type == "MESH":
            if ob.data.shape_keys is not None:
                return True
        return False

def get_filtered_shape_keys(obj, key_filter: list):
        shape_keys = obj.shape_keys.key_blocks
        key_list = []
        
        for key in shape_keys:
            norm_key = key.name.lower().replace("-","").replace(" ","")
            if any(f_key == norm_key for f_key in key_filter):
                key_name = key.name
                category = key.relative_key.name
                category_lower = category.lower().replace("-","").replace(" ","")
                
                
                key_list.append((norm_key, category_lower, key_name))
        
        return key_list

def directory_short(directory, amount):
    if os.path.exists(directory):
        full_path = os.path.normpath(directory)

        path_parts = full_path.split(os.sep)

        last_folders = os.sep.join(path_parts[-amount:])

        return last_folders
    else:
        return None

def get_modpack_groups(context):
        return [(str(option.group_value), option.group_name, option.group_description) for option in context.scene.modpack_group_options]


class CollectionState(PropertyGroup):
    collection_name: bpy.props.StringProperty() # type: ignore


class ModpackGroups(PropertyGroup):
    group_value: bpy.props.IntProperty() # type: ignore
    group_name: bpy.props.StringProperty() # type: ignore
    group_description: bpy.props.StringProperty() # type: ignore


class UsefulProperties(PropertyGroup):

    ui_buttons_list = [
        ("export",   "expand",   "Opens the category"),
        ("import",   "expand",   "Opens the category"),
        ("chest",    "shapes",   "Opens the category"),
        ("leg",      "shapes",   "Opens the category"),
        ("other",    "shapes",   "Opens the category"),
        ("chest",    "category", ""),
        ("yas",      "expand",   "Opens the category"),
        ("file",     "expand",   "Opens the category"),
        ("advanced", "expand",   "Switches between a simplified and full view of the shape keys"),
        ("dynamic",  "view",     "Toggles between a dynamic collection viewer and one constrained to the active object"),
        ]
   
    mesh_list = [
        "Torso",
        "Waist",
        "Hands",
        "Feet",
        "Mannequin",
    ]

    @staticmethod
    def ui_buttons():
        for (name, category, description) in UsefulProperties.ui_buttons_list:
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
            setattr(UsefulProperties, prop_name, prop)

    @staticmethod
    def export_bools():
        for shape, (name, slot, shape_category, description, body, key) in all_shapes.items():
            slot_lower = slot.lower().replace("/", " ")
            name_lower = name.lower().replace(" ", "_")
            
            prop_name = f"export_{name_lower}_{slot_lower}_bool"
            prop = BoolProperty(
                name="", 
                description=description,
                default=False, 
                )
            setattr(UsefulProperties, prop_name, prop)
    
    @staticmethod
    def chest_key_floats():
        # Creates float properties for chest shape keys controlled by values.
        # Automatically assigns drivers to the models to be controlled by the UI.
        key_filter = ["squeeze", "squish", "pushup", "omoi", "sag", "nipnops", "sayonara", "mini"]
        torso = bpy.data.meshes["Torso"]
        mq = bpy.data.meshes["Mannequin"]
        
        targets = {
             "torso": torso,
             "mq":    mq,
        }
        
        for name, obj in targets.items():
            key_list = get_filtered_shape_keys(obj, key_filter)

            for key, category, key_name in key_list:
                default = 0
                if key == "squeeze" and category != "small":
                    min = -50
                    if category == "large":
                        default = 30
                else:
                    min = 0
                
                prop_name = f"key_{key}_{category}_{name}"
                
                prop = FloatProperty(
                    name="",
                    default=default,
                    min=min,
                    max=100,
                    soft_min=0,
                    precision=0,
                    subtype="PERCENTAGE"    
                )
                if hasattr(UsefulProperties, prop_name):
                    return None
                else:
                    setattr(UsefulProperties, prop_name, prop)
                UsefulProperties.add_shape_key_drivers(obj, key_name, prop_name)

    @staticmethod
    def feet_key_floats():
        # Creates float properties for feet shape keys controlled by values.
        # Automatically assigns drivers to the models to be controlled by the UI.
        key_filter = ["heels", "cinderella", "miniheels"]
        feet = bpy.data.meshes["Feet"]
        mq = bpy.data.meshes["Mannequin"]
        
        targets = {
             "feet": feet,
             "mq":    mq,
        }
        
        for name, obj in targets.items():
            key_list = get_filtered_shape_keys(obj, key_filter)

            for key, category, key_name in key_list:      
                
                prop_name = f"key_{key}_{name}"
                
                prop = FloatProperty(
                    name="",
                    default=0,
                    min=0,
                    max=100,
                    precision=0,
                    subtype="PERCENTAGE"    
                )
                if hasattr(UsefulProperties, prop_name):
                    return None
                else:
                    setattr(UsefulProperties, prop_name, prop)
                UsefulProperties.add_shape_key_drivers(obj, key_name, prop_name)

    def add_shape_key_drivers(obj, key_name, prop_name):
        
        if key_name in obj.shape_keys.key_blocks:
            shape_key = obj.shape_keys.key_blocks[key_name]
          
            shape_key.driver_remove("value")
            driver = shape_key.driver_add("value").driver

            driver.type = "SCRIPTED"
            driver.expression = "round(key_value/100, 2)"

            var = driver.variables.new()
            var.name = "key_value"
            var.type = "SINGLE_PROP"
            
            var.targets[0].id_type = "SCENE"
            var.targets[0].id = bpy.data.scenes["Scene"]
            var.targets[0].data_path = f"ya_props.{prop_name}"  

    def get_listable_shapes(body_slot):
        items = []

        for shape, (name, slot, shape_category, description, body, key) in all_shapes.items():
            if body_slot.lower() == slot.lower() and description != "" and shape_category !="":
                items.append((name, name, description))
        return items

    def update_directory(category):
        prop = bpy.context.scene.ya_props
        actual_prop = f"{category}_directory"
        display_prop = f"{category}_display_directory"

        display_directory = getattr(prop, display_prop, "")

        if os.path.exists(display_directory):  
            setattr(prop, actual_prop, display_directory)
            print (getattr(prop, actual_prop, ""))

    chest_shape_enum: EnumProperty(
        name= "",
        description= "Select a size",
        items=lambda self, context: UsefulProperties.get_listable_shapes("Chest")
        )   # type: ignore
    
    modpack_groups: EnumProperty(
        name= "",
        description= "Select an option to replace",
        items= lambda self, context: get_modpack_groups(context)
        )   # type: ignore

    shape_mq_chest_bool: BoolProperty(
        name="",
        description="Switches to the mannequin", 
        default=False, 
        ) # type: ignore
    
    shape_mq_legs_bool: BoolProperty(
        name="",
        description="Switches to the mannequin", 
        default=False, 
        )  # type: ignore

    shape_mq_other_bool: BoolProperty(
        name="",
        description="Switches to the mannequin",  
        default=False, 
        )   # type: ignore

    export_display_directory: StringProperty(
        name="Export Folder",
        default="Select Export Directory",  
        maxlen=255,
        update=lambda self, context: UsefulProperties.update_directory('export'),
        ) # type: ignore
    
    export_directory: StringProperty(
        default="Select Export Directory",
        subtype="DIR_PATH", 
        maxlen=255,
        )  # type: ignore

    export_gltf: BoolProperty(
        name="",
        description="Switch export format", 
        default=False,
        ) # type: ignore
    
    ui_size_category: StringProperty(
        name="",
        subtype="DIR_PATH", 
        maxlen=255,
        )  # type: ignore
    
    export_body_slot: EnumProperty(
        name= "",
        description= "Select a body slot",
        items= [
            ("Chest", "Chest", "Chest export options."),
            ("Legs", "Legs", "Leg export options."),
            ("Hands", "Hands", "Hand export options."),
            ("Feet", "Feet", "Feet export options."),
            ("Chest/Legs", "Chest/Legs", "When you want to export Chest with Leg models.")]
        )  # type: ignore

    bpy.types.Object.toggle_yas = bpy.props.BoolProperty(
    name="",
    description="Enable yiggle weights",
    default=False,
    update=yas_state
    )

    bpy.types.Object.toggle_yas_gen = bpy.props.BoolProperty(
    name="",
    description="Enable IVCS weights for the genitalia. YAS needs to be enabled",
    default=False,
    update=yas_gen_state
    )

    collection_state: bpy.props.CollectionProperty(type=CollectionState) # type: ignore

    modpack_group_options: bpy.props.CollectionProperty(type=ModpackGroups) # type: ignore

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
        default="Paste path here.",
        maxlen=255

        )  # type: ignore
    
    loadmodpack_display_directory: StringProperty(
        name="Select PMP",
        default="Select Modpack",  
        maxlen=255,
        update=lambda self, context: UsefulProperties.update_directory('loadmodpack'),
        ) # type: ignore
    
    loadmodpack_directory: StringProperty(
        default="Select Modpack",
        subtype="DIR_PATH", 
        maxlen=255,
        update=modpack_groups_list
        )  # type: ignore


class UTILS_OT_YA_CollectionManager(Operator):
    bl_idname = "ya.collection_manager"
    bl_label = "Export"
    bl_description = "Combines chest options and exports them"
    bl_options = {'UNDO'}

    def __init__(self):
        self.coll = bpy.data.collections
        self.collections_to_keep = [
            self.coll["Skeleton"],
            self.coll["Resources"],
            self.coll["Data Sources"],
            self.coll["UV/Weights"],
            self.coll["Nail UVs"],
            self.coll["Rue"],
            self.coll["YAS"],
            self.coll["Piercings"]
        ]
   
    def execute(self, context): 
        collections = bpy.context.scene.ya_props.collection_state
        
        for state in collections:
            name = state.collection_name
            new_collection = self.coll[name]
            self.collections_to_keep.append(new_collection)
        
        self.collections_to_keep = set(self.collections_to_keep)

        self.exclude_collections()
        bpy.context.view_layer.layer_collection.children['Resources'].hide_viewport = True
        return {"FINISHED"}

    def exclude_collections(self):
        # Eclude all collections except those to keep
        all_collections = bpy.data.collections
        
        # First set visible to avoid children being enabled
        for collection in self.collections_to_keep:
            self.toggle_collection_exclude(collection, exclude=False)

        # Exclude remaining collections
        for collection in all_collections:
            if collection not in self.collections_to_keep:
                self.toggle_collection_exclude(collection, exclude=True)
    
    def toggle_collection_exclude(self, collection, exclude=True):
            # Get the layer collections for the current scene and context
            for layer_collection in bpy.context.view_layer.layer_collection.children:
                self.recursively_toggle_exclude(layer_collection, collection, exclude)

    def recursively_toggle_exclude(self, layer_collection, collection, exclude):
        # check all layers for children and apply exclude state
        if layer_collection.collection == collection:
            layer_collection.exclude = exclude
        
        # Recursive check for child collections
        for child in layer_collection.children:
            self.recursively_toggle_exclude(child, collection, exclude)


