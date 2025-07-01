
from typing      import TypedDict, Iterable
from bpy.types   import Object, PropertyGroup


Preset = TypedDict(
    "Preset",

    {
    "_version": int, 
    "_format" : str, 
    "preset"  : dict,
    },

    total = True
)

ObjIterable = Iterable[Object]
BlendEnum   = list[tuple[str, str, str]]

# Classes from Yet Another Devkit

class CollectionState(PropertyGroup):

    def export_chest(self, piercings: bool) -> None:...
    def export_legs(self, pubes: bool) -> None:...
    def export_hands(self) -> None:...
    def export_feet(self) -> None:...

    skeleton        : bool
    chest           : bool
    nipple_piercings: bool
    legs            : bool
    pubes           : bool
    hands           : bool
    nails           : bool
    clawsies        : bool
    practical       : bool
    feet            : bool
    toenails        : bool
    toe_clawsies    : bool
    mannequin       : bool
    export          : bool

class SubKeyValues(PropertyGroup):
    name : str
    value: float

class TorsoState(PropertyGroup):
    MANNEQUIN: bool

    chest_size: str
    buff      : bool
    rue       : bool
    lavabod   : bool

    yab_keys : Iterable[SubKeyValues]
    lava_keys: Iterable[SubKeyValues]

class LegState(PropertyGroup):
    gen       : str
    leg_size  : str
    rue       : bool
    small_butt: bool
    soft_butt : bool
    alt_hips  : bool
    squish    : str

class HandState(PropertyGroup):
    nails    : str
    hand_size: str
    clawsies : str

class FeetState(PropertyGroup):
    rue_feet: bool

class MannequinState(TorsoState, LegState, HandState, FeetState):
    pass

class DevkitProps(PropertyGroup):
    ALL_SHAPES         : dict[str, tuple[str, ...]]
    chest_shape_enum   : str
    shape_mq_chest_bool: bool
    shape_mq_legs_bool : bool
    shape_mq_other_bool: bool
    
    collection_state   : CollectionState
    torso_state        : TorsoState
    leg_state          : LegState
    hand_state         : HandState
    feet_state         : FeetState
    yam_torso          : Object
    yam_legs           : Object
    yam_hands          : Object
    yam_feet           : Object
    yam_mannequin      : Object

    mannequin_state: MannequinState

class DevkitWindowProps(PropertyGroup):
    overview_ui: str
    devkit_triangulation: bool
    yas_storage: str
