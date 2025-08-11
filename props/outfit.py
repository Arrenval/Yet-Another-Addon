import os
import bpy

from typing          import TYPE_CHECKING
from bpy.types       import PropertyGroup, Object, Context
from bpy.props       import StringProperty, EnumProperty, CollectionProperty, PointerProperty, BoolProperty, IntProperty, FloatProperty
from collections.abc import Iterable

from .window         import YAWindowProps
from .getters        import get_window_properties, get_devkit_properties
from ..utils.typings import BlendEnum


class YASUIList(PropertyGroup):

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

class YASWeights(PropertyGroup):
    idx: IntProperty(name="Vertex Index") # type: ignore
    value: FloatProperty(name="Weight Value") # type: ignore

    if TYPE_CHECKING:
        idx  : int
        value: float

class YASGroup(PropertyGroup):
    name: StringProperty(name="Vertex Group") # type: ignore
    parent: StringProperty(name="Parent Group", description="Parent of the vertex group") # type: ignore
    vertices: CollectionProperty(type=YASWeights, description="Contains all vertices with weights in this group") # type: ignore

    if TYPE_CHECKING:
        name      : str
        parent    : str
        vertices  : Iterable[YASWeights]

class YASStorage(PropertyGroup):
    old_count : IntProperty(description="The vertex count of the mesh at the time of storage") # type: ignore

    all_groups: BoolProperty(default=False) # type: ignore
    genitalia : BoolProperty(default=False) # type: ignore
    physics   : BoolProperty(default=False) # type: ignore

    v_groups  :CollectionProperty(type=YASGroup, description="Contains all stored vertex groups") # type: ignore

    if TYPE_CHECKING:
        old_count : int
        all_groups: bool
        genitalia : bool
        physics   : bool
        v_groups  : Iterable[YASGroup]
        
class ShapeModifiers(PropertyGroup):
    name: StringProperty() # type: ignore
    icon: StringProperty() # type: ignore

    if TYPE_CHECKING:
        name: str
        icon: str
       
class YAOutfitProps(PropertyGroup):

    shape_modifiers_group: CollectionProperty(type=ShapeModifiers) # type: ignore

    yas_ui_vgroups : CollectionProperty(type=YASUIList) # type: ignore

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
    

    def _chest_controller_update(self, context: Context) -> None:
        key_blocks = get_devkit_properties().yam_shapes.data.shape_keys.key_blocks
        for key in key_blocks:
            key.mute = True

        if self.shape_chest_base == "Lavabod":
            key_name = "Lavatop"
        elif self.shape_chest_base == "Teardrop":
            key_name = "-- " + self.shape_chest_base
        elif self.shape_chest_base == "Cupcake":
            key_name = "--- " + self.shape_chest_base
        else:
            key_name = self.shape_chest_base
        key_blocks[key_name].mute = False
        if self.shape_chest_base in ("Teardrop", "Cupcake"):
            key_blocks["Lavatop"].mute = False

    def scene_actions(self, context) -> BlendEnum: 
        armature_actions = [("None", "None", ""), None]
    
        for action in bpy.data.actions:
            if action.id_root == "OBJECT":
                armature_actions.append((action.name , action.name, "Action"))
        return armature_actions
    
    def set_action(self, context: Context) -> None:
        window = get_window_properties()
        if not self.outfit_armature:
            return
        if self.actions == "None":
            self.outfit_armature.animation_data.action = None
            for bone in self.outfit_armature.pose.bones:
                bone.location = (0.0, 0.0, 0.0)
                if bone.rotation_mode == "QUATERNION":
                    bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
                else:
                    bone.rotation_euler = (0.0, 0.0, 0.0)
            return
    
        action = bpy.data.actions.get(self.actions)

        self.outfit_armature.animation_data.action = action
        if bpy.app.version >= (4, 4, 0):
            self.outfit_armature.animation_data.action_slot = action.slots[0]
        context.scene.frame_end = int(action.frame_end)

        if hasattr(YAWindowProps, "animation_frame"):
            del YAWindowProps.animation_frame
        
        prop = IntProperty(
            name="Current Frame",
            default=0,
            max=int(action.frame_end),
            min=0,
            update=lambda self, context: window.animation_frames(context)
            ) 
        
        setattr(YAWindowProps, "animation_frame", prop)

    def update_directory(self, context: Context, category: str) -> None:
        prop = context.scene.file_props
        actual_prop = f"{category}_directory"
        display_prop = f"{category}_display_directory"

        display_directory = getattr(prop, display_prop, "")

        if os.path.exists(display_directory):  
            setattr(prop, actual_prop, display_directory)

    def validate_shapes_source_enum(self, context) -> None:
        window = get_window_properties()
        window.shapes_source_enum = self.shapes_source.data.shape_keys.key_blocks[0].name if self.shapes_source else "None"

    def validate_shapes_target_enum(self, context) -> None:
        window = get_window_properties()
        window.shapes_target_enum = "None"

    shapes_source: PointerProperty(
        type= Object,
        name= "",
        description= "Shape key/driver source",
        update=validate_shapes_source_enum
        )  # type: ignore
    
    shapes_target: PointerProperty(
        type= Object,
        name= "",
        description= "Shape key/driver source",
        update=validate_shapes_target_enum
        )  # type: ignore

    shape_chest_base: EnumProperty(
        name= "",
        description= "Select the base size",
        items= [
            ("LARGE", "Large", "Standard Large"),
            ("MEDIUM", "Medium", "Standard Medium"),
            ("SMALL", "Small", "Standard Small"),
            ("MASC", "Masc", "Yet Another Masc"),
            None,
            ("Lavabod", "Omoi", "Biggest Lavatiddy"),
            ("Teardrop", "Teardrop", "Medium Lavatiddy"),
            ("Cupcake", "Cupcake", "Small Lavatiddy"),
        ],
        update=_chest_controller_update
        )  # type: ignore
    
    actions: EnumProperty(
        name="Animations",
        description="Select an animation from the scene",
        items=scene_actions,
        default= 0,
        update=set_action
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

    def set_yas_ui_vgroups(self, context):
        obj = self.yas_source
        window = get_window_properties()
        update_groups = (window.weights_category and window.filter_vgroups and obj)

        if update_groups:
            self.yas_ui_vgroups.clear()

            yas_groups = [group for group in obj.vertex_groups if group.name.startswith(("iv_", "ya_"))]
            if yas_groups:
                self.yas_empty = False
                for group in yas_groups:
                    new_group = self.yas_ui_vgroups.add()
                    new_group.name = group.name
                    new_group.lock_weight = group.lock_weight

            else:
                new_group = self.yas_ui_vgroups.add()
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
                window.shape_modifiers = self.shape_modifiers_group[0].name

        else:
            self.shape_modifiers_group.clear()

    yas_source: PointerProperty(
        type= Object,
        name= "",
        description= "YAS source",
        update=set_yas_ui_vgroups,

        )  # type: ignore
    
    yas_empty: BoolProperty(
        name="",
        default=False,
        ) # type: ignore
    
    def selected_yas_vgroup(self, context) -> None:
        obj = bpy.context.active_object
        if len(self.yas_ui_vgroups) == 1 and self.yas_ui_vgroups[0].name != "Mesh has no YAS Groups":
            try:
                obj.vertex_groups.active = obj.vertex_groups.get(self.yas_ui_vgroups[self.yas_vindex].name)
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
        shape_modifiers_group  : Iterable[ShapeModifiers]
        
        pose_display_directory : str
        
        shape_chest_base       : str
        
        actions                : str
        
        shapes_source          : Object
        shapes_target          : Object
        outfit_armature        : Object

        yas_source       : Object
        yas_vindex       : int
        yas_ui_vgroups   : Iterable[YASUIList]
        yas_empty        : bool
        mod_shapes_source: Object



CLASSES = [    
    YASUIList,
    YASWeights,
    YASGroup,
    YASStorage,
    ShapeModifiers,
    YAOutfitProps
]




