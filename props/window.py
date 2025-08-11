import bpy
import platform

from typing          import TYPE_CHECKING
from bpy.types       import PropertyGroup, Object, Context
from bpy.props       import StringProperty, EnumProperty, CollectionProperty, BoolProperty, IntProperty
from collections.abc import Iterable

from .getters        import get_outfit_properties, get_file_properties
from .modpack        import BlendModGroup, modpack_data
from ..utils.typings import BlendEnum


class YAWindowProps(PropertyGroup):
    
    ui_buttons_list = [
        ("backfaces",   "expand",     "Opens the category"),
        ("modifiers",   "expand",     "Opens the category"),
        ("transp",      "expand",     "Opens the category"),
        ("yas_man",     "expand",     "Opens the category"),
        
        ]
    
    extra_options = [
        ("overview", "category",    True,   "Enables part overview"),
        ("shapes",   "category",    False,  "Enables shape transfer menu"),
        ("mesh",     "category",    False,  "Enables mesh editing menu"),
        ("weights",  "category",    False,  "Enables weight editing menu"),
        ("armature", "category",    False,  "Enables animation playback and pose/scaling menu"),

        ("file",     "category",    True,  "General file utilities"),
        ("phyb",     "category",    False,  "Phyb file utilities"),
        ("model",    "category",    False,  "Model file utilities"),

        ("filter",   "vgroups",     True,   "Switches between showing all vertex groups or just YAS groups"),
        ("create",   "backfaces",   True,   "Creates backface meshes on export. Meshes need to be triangulated"),
        ("check",    "tris",        True,   "Verify that the meshes are triangulated"),
        ("keep",     "shapekeys",   True,   "Preserves game ready shape keys"),
        ("create",   "subfolder",   True,   "Creates a folder in your export directory for your exported body part"),
        ("rue",      "export",      True,   "Controls whether Rue is exported as a standalone body and variant, or only as a variant for Lava/Masc"),
        ("body",     "names",       False,  "Always add body names on exported files or depending on how many bodies you export"),
        ("chest",    "g_category",  False,  "Changes gamepath category"),
        ("hands",    "g_category",  False,  "Changes gamepath category"),
        ("legs",     "g_category",  False,  "Changes gamepath category"),
        ("feet",     "g_category",  False,  "Changes gamepath category"),
        ("scaling",   "armature",   False,   "Applies scaling to armature"),
        ("keep",      "modifier",   False,   "Keeps the modifier after applying. Unable to keep Data Transfers"),
        ("all",       "keys",       False,   "Transfers all shape keys from source to target"),
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

    yas_storage: EnumProperty(
        name="",
        description="Select what vertex groups to store",
        items=[
            ('ALL', "All Weights", "Store all YAS weights"),
            ('PHYS', "Physics", "Store all thigh/butt physics related weights"),
            ('GEN', "Genitalia", "Store all genitalia related weights")
        ]
        ) # type: ignore
    
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

    def _get_formats(self, context) -> None:
        if self.file_man_ui == 'IMPORT' or platform.system() == 'Windows':
            return [
            ('MDL', "MDL", "Export FBX and convert to MDL."),
            ('FBX', "FBX", "Export FBX."),
            ('GLTF', "GLTF", "Export GLTF"),
            ]
        
        else:
            return [
            ('FBX', "FBX", "Export FBX."),
            ('GLTF', "GLTF", "Export GLTF"),
            ]
        
    file_format: EnumProperty(
        name="",
        description="Switch file format", 
        items=_get_formats
        ) # type: ignore

    def check_gamepath_category(self, context) -> None:
        if self.valid_xiv_path:
            category = self.export_xiv_path.split("_")[-1].split(".")[0]
            return category
    
    def _check_valid_path(self, context):
        path: str        = self.export_xiv_path
        self.valid_xiv_path = path.startswith("chara") and path.endswith(".mdl")

    export_xiv_path: StringProperty(
                            default="Paste path here...", 
                            name="", 
                            description="Path to the in-game model you want to replace", 
                            update=_check_valid_path
                        ) # type: ignore
    
    valid_xiv_path: BoolProperty(default=False) # type: ignore
    
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
    
    def _shapes_type_validate(self, context) -> None:
        if not self.include_deforms and self.shapes_type == 'SINGLE':
            self.shapes_type = 'EXISTING'
    
    def _set_shape_enums(self, context):
        props = get_outfit_properties()

        if self.shapes_type == 'SINGLE':
            self.include_deforms = True
            props.validate_shapes_source_enum(context)
            props.validate_shapes_target_enum(context)

    shapes_type: EnumProperty(
        name= "",
        description= "Select which keys to transfer",
        default=0,
        items=[
                ('EXISTING', "Existing", "Transfer/link all keys that already exist on the target"),
                ('ALL', "All Keys", "Transfer/link all keys"),
                ('SINGLE', "Single", "Transfers/links the selected key"),
            ],
        update=_set_shape_enums
        )  # type: ignore
    
    include_deforms: BoolProperty(
        default=False, 
        name="", 
        description="Enable this to include deforms. If disabled only the shape key entries are added", 
        update=_shapes_type_validate
        ) # type: ignore
    
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
        )  # type: ignore
    
    shape_seam_base: EnumProperty(
        name= "",
        description= "Select the base size, only affects waist seam",
        items= [
            ("LARGE", "YAB", ""),
            ("Lavabod", "Lavabod", ""),
            ("Yanilla", "Yanilla", ""),
            ("Masc", "Masc", ""),
            ("Mini", "Mini", ""),
        ],
        )  # type: ignore
    
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

    shapes_source_enum: EnumProperty(
        name= "",
        description= "Select a shape key",
        items=lambda self, context: self.get_shape_key_enum(context, bpy.context.scene.ya_outfit_props.shapes_source)
        )  # type: ignore
    
    shapes_target_enum: EnumProperty(
        name= "",
        description= "Select a shape key",
        items=lambda self, context: self.get_shape_key_enum(context, bpy.context.scene.ya_outfit_props.shapes_target, new=True)
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
    
    def get_vertex_groups(self, context:Context, obj:Object) -> BlendEnum:
        if obj and obj.type == "MESH":
            return [("None", "None", "")] + [(group.name, group.name, "") for group in obj.vertex_groups]
        else:
            return [("None", "Select a target", "")]

    obj_vertex_groups: EnumProperty(
        name= "",
        description= "Select a group to pin, it will be ignored by any smoothing corrections",
        items=lambda self, context: self.get_vertex_groups(context, bpy.context.scene.ya_outfit_props.shapes_target)
        )  # type: ignore
    
    exclude_vertex_groups: EnumProperty(
        name= "",
        description= "Select a group to exclude from shrinkwrapping",
        items=lambda self, context: self.get_vertex_groups(context, bpy.context.scene.ya_outfit_props.shapes_target)
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

    insp_file1: StringProperty(
        name="",
        default="",
        description="File to inspect", 
        maxlen=255,
        )  # type: ignore
    
    insp_file2: StringProperty(
        name="",
        default="",
        description="File to inspect", 
        maxlen=255,
        )  # type: ignore
    
    sym_group_l: StringProperty(
        name="",
        default="_l",
        description="Left group suffix", 
        maxlen=10,
        )  # type: ignore
    
    sym_group_r: StringProperty(
        name="",
        default="_r",
        description="Right group suffix", 
        maxlen=10,
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
        
        yas_storage     : str
        file_man_ui     : str
        export_body_slot: str
        shape_modifiers : str
        waiting_import  : bool
        shape_source    : Object
        file_format     : str
        export_prefix   : str
        remove_yas      : str
        export_xiv_path : str
        valid_xiv_path  : bool

        obj_vertex_groups    : str
        exclude_vertex_groups: str
        shapes_source_enum   : str
        shapes_target_enum   : str
        shapes_corrections   : str
        shapes_method        : str
        shapes_type          : str
        shape_leg_base       : str
        shape_seam_base      : str
        modpack_replace      : bool
        modpack_display_dir  : str
        modpack_dir          : str
        modpack_version      : str
        modpack_author       : str
        modpack_rename_group : str
        new_mod_name         : str
        new_mod_version      : str
        author_name          : str
        animation_frame      : int  
        include_deforms : bool
 
        # Created at registration
        overview_category: bool
        shapes_category  : bool
        mesh_category    : bool
        weights_category : bool
        armature_category: bool
        filter_vgroups   : bool
        file_category    : bool
        phyb_category    : bool
        model_category   : bool

        button_backfaces_expand: bool
        button_modifiers_expand: bool
        button_transp_expand   : bool
        button_yas_man_expand  : bool

        create_backfaces: bool
        check_tris      : bool
        remove_nonmesh  : bool
        reorder_mesh_id : bool
        update_material : bool
        keep_shapekeys  : bool
        create_subfolder: bool
        rue_export      : bool
        body_names      : bool
        chest_g_category: bool
        hands_g_category: bool
        legs_g_category : bool
        feet_g_category : bool
        ui_size_category: str
        rename_import   : str
   
        scaling_armature: bool
        keep_modifier   : bool
        adjust_overhang : bool
        add_shrinkwrap  : bool
        seam_waist      : bool
        seam_wrist      : bool
        seam_ankle      : bool
        sub_shape_keys  : bool

        sym_group_l: str
        sym_group_r: str


CLASSES = [
    YAWindowProps,
]