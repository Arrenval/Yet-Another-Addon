import bpy

from typing          import Literal, TYPE_CHECKING
from mathutils       import Vector, Quaternion, Matrix
from bpy.types       import Object, PropertyGroup
from bpy.props       import (StringProperty, EnumProperty, CollectionProperty, BoolProperty,
                             FloatProperty, IntProperty, FloatVectorProperty, PointerProperty)
from collections     import defaultdict

from .enums          import get_racial_enum, SCALE_FROM_BASE
from .getters        import get_window_props
from ..utils.typings import BlendCollection


class HkBone(PropertyGroup):
    name : StringProperty(default="", name="", description="Name of bone") # type: ignore
    index: IntProperty(name="", description="Bone's index", default=0) # type: ignore

    if TYPE_CHECKING:
        name : str
        index: int

class MapBone(HkBone):
    pos    : FloatVectorProperty(size=3, default=(0, 0, 0)) # type: ignore
    rot    : FloatVectorProperty(size=4, default=(1, 0, 0, 0)) # type: ignore
    scale  : FloatVectorProperty(size=4, default=(1, 1, 1, 1)) # type: ignore
    unknown: FloatProperty(default=0.0, name="", description="Unknown, possibly radians") # type: ignore
    parent : StringProperty(default="", name="") # type: ignore

    def get_values(self, rotation=True) -> list[float]:
        floats = [0.0 for _ in range(12)]

        floats[:3]  = self.pos
        floats[4:8] = [self.rot[1], self.rot[2], self.rot[3], self.rot[0]] if rotation else [0, 0, 0, 1]
        floats[8:]  = self.scale
        floats[3]   = self.unknown

        return floats
    
    if TYPE_CHECKING:
        pos    : Vector
        rot    : Quaternion
        scale  : Vector
        unknown: float
        parent : str

class CacheBone(MapBone):
    ctrs: FloatVectorProperty(size=3, default=(0, 0, 0)) # type: ignore
    crot: FloatVectorProperty(size=4, default=(1, 0, 0, 0)) # type: ignore
    cscl: FloatVectorProperty(size=3, default=(0, 0, 0)) # type: ignore
    
    def get_trs(self) -> Vector:
        return Vector(self.ctrs)
    
    def get_rot(self) -> Quaternion:
        return Quaternion(self.crot)
    
    def get_scl(self) -> Vector:
        return Vector(self.cscl)
    
    def compare(mat: Matrix) -> bool:...

    if TYPE_CHECKING:
        trs: list[float]
        rot: list[float]
        scl: list[float]

class AnimLayer(PropertyGroup):
    name     : StringProperty(default="Layer", name="", description="") # type: ignore
    id       : IntProperty(default=0, name="", description="Name of bone") # type: ignore
    bone_list: CollectionProperty(type=HkBone) # type: ignore

    def get_bone_list(self, context) -> list[str]:
        return [bone.name for bone in self.bone_list]

    if TYPE_CHECKING:
        name : str
        id   : int
        bone_list: BlendCollection[HkBone]

class BoneMapping(PropertyGroup):
    bone_a: StringProperty(default="", name="", description="Base skeleton bone name") # type: ignore
    bone_b: StringProperty(default="", name="", description="Target skeleton bone name") # type: ignore

    pos    : FloatVectorProperty(size=3, default=(0, 0, 0), name="", description="Transform") # type: ignore
    rot    : FloatVectorProperty(size=4, default=(1, 0, 0, 0), name="", description="Quaternion") # type: ignore
    scale  : FloatVectorProperty(size=4, default=(1, 1, 1, 1), name="", description="Scaling") # type: ignore
    unknown: FloatProperty(default=0.0, name="", description="Unknown, possibly radians") # type: ignore

    def get_values(self, rotation=True) -> list[float]:
        floats = [0.0 for _ in range(12)]

        floats[:3]  = self.pos
        floats[4:8] = [self.rot[1], self.rot[2], self.rot[3], self.rot[0]] if rotation else [0, 0, 0, 1]
        floats[8:]  = self.scale
        floats[3]   = self.unknown

        return floats

    if TYPE_CHECKING:
        bone_a: str
        bone_b: str

        pos    : Vector
        rot    : Quaternion
        scale  : Vector
        unknown: float

class SklbMapper(PropertyGroup):

    def set_scale(self, context) -> None:
        if get_window_props().skeleton.ui_tab != 'CONFIG':
            return
        
        base       = int(context.active_object.data.kaos.race_id)
        scale      = SCALE_FROM_BASE[base] / SCALE_FROM_BASE[int(self.race_id)]
        self.scale = [scale for _ in range(4)]

    race_id: EnumProperty(
                name= "",
                default=1,
                description="This is a secondary skeleton which acts as the base of the mapper",
                items=lambda self, context: get_racial_enum(optional=False),
                update=set_scale
                ) # type: ignore
    
    pos    : FloatVectorProperty(size=3, default=(0, 0, 0), name="", description="Transform") # type: ignore
    rot    : FloatVectorProperty(size=4, default=(1, 0, 0, 0), name="", description="Quaternion") # type: ignore
    scale  : FloatVectorProperty(size=4, default=(1, 1, 1, 1), name="", description="Scaling") # type: ignore
    unknown: FloatProperty(default=0.0, name="", description="Unknown, possibly radians") # type: ignore

    bone_list: CollectionProperty(type=MapBone) # type: ignore
    bone_maps: CollectionProperty(type=BoneMapping) # type: ignore

    existing  : BoolProperty(
        default=False, 
        name="", 
        description="Generates mappings for existing bones if enabled. Generates only missing ones when disabled", 
        options={'HIDDEN', 'SKIP_SAVE'}
        ) # type: ignore
    
    new_source: PointerProperty(
        type= Object,
        name= "",
        description= "Select a new armature to use as mapping parent",
        poll=lambda self, obj: obj.type == "ARMATURE"
        )  # type: ignore


    def get_bone_indices(self) -> dict[str, int]:
        return {bone.name: idx for idx, bone in enumerate(self.bone_list)}
    
    def get_values(self, rotation=True) -> list[float]:
        floats = [0.0 for _ in range(12)]

        floats[:3]  = self.pos
        floats[4:8] = [self.rot[1], self.rot[2], self.rot[3], self.rot[0]] if rotation else [0, 0, 0, 1]
        floats[8:]  = self.scale
        floats[3]   = self.unknown

        return floats
    
    if TYPE_CHECKING:
        name   : str
        race_id: Literal['0101', '0201', '0301', '0401', '0501', '0601', 
                         '0701', '0801', '0901', '1001', '1101', '1201',
                         '1301', '1401', '1501', '1601', '1701', '1801']
        
        pos    : Vector
        rot    : Quaternion
        scale  : Vector
        unknown: float

        bone_list: BlendCollection[MapBone]
        bone_maps: BlendCollection[BoneMapping]

        new_source: Object

class KaosArmature(PropertyGroup):
    race_id: EnumProperty(
                name= "",
                default=1,
                description= "",
                items=lambda self, context: get_racial_enum(optional=False)
                ) # type: ignore
    
    mappers    : CollectionProperty(type=SklbMapper) # type: ignore
    anim_layers: CollectionProperty(type=AnimLayer) # type: ignore
    bone_list  : CollectionProperty(type=HkBone) # type: ignore
    bone_cache : CollectionProperty(type=CacheBone) # type: ignore

    def get_mappers(self) -> list[int]:
        ids = []
        for mapper in self.mappers:
            if not mapper.bone_maps:
                continue
            ids.append(int(mapper.race_id))
        
        return ids
    
    def get_bone_indices(self) -> dict[str, int]:
        return {bone.name: idx for idx, bone in enumerate(self.bone_list)}
    
    def get_cache(self) -> dict[str, CacheBone]:
        return {bone.name: bone for bone in self.bone_cache}
    
    def bone_to_layer_id(self) -> dict[str, set[int]]:
        bmap = defaultdict(set)
        for layer in self.anim_layers:
            for bone in layer.bone_list:
                bmap[bone.name].add(layer.id)
        
        return bmap

    if TYPE_CHECKING:
        mappers    : BlendCollection[SklbMapper]
        anim_layers: BlendCollection[AnimLayer]
        bone_list  : BlendCollection[HkBone]
        bone_cache : BlendCollection[CacheBone]

        race_id: Literal['0101', '0201', '0301', '0401', '0501', '0601', 
                         '0701', '0801', '0901', '1001', '1101', '1201',
                         '1301', '1401', '1501', '1601', '1701', '1801']

class SkeletonProps(PropertyGroup):

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

    source: PointerProperty(
        type= Object,
        name= "",
        description= "Select an armature from the scene",
        poll=lambda self, obj: obj.type == "ARMATURE" and obj is not bpy.context.active_object
        )  # type: ignore
    
    bone_idx   : IntProperty(name="", description="Active Bone", default=0) # type: ignore
    layer_idx  : IntProperty(name="", description="Active Layer", default=0) # type: ignore
    layer_b_idx: IntProperty(name="", description="Active Bone", default=0) # type: ignore
    map_idx    : IntProperty(name="", description="Active Bone Map", default=0) # type: ignore
    
    if TYPE_CHECKING:
        source     : Object
        bone_idx   : int
        layer_idx  : int
        layer_b_idx: int
        map_idx    : int


CLASSES = [
    HkBone,
    MapBone,
    CacheBone,
    AnimLayer,
    BoneMapping,
    SklbMapper,
    KaosArmature,
    SkeletonProps
]