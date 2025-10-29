
from typing          import TypedDict, Protocol, TypeVar, Iterator
from bpy.types       import Object, PropertyGroup
from collections.abc import Iterable


T = TypeVar('T')

Preset = TypedDict(
    "Preset",

    {
    "_version": int, 
    "_format" : str, 
    "preset"  : dict,
    },

    total = True
)

BlendEnum   = list[tuple[str, str, str]]
    
class BlendCollection(Protocol[T]):
    """
    Type hints to mimic Blender Collections.
    """
    
    def add(self) -> T:...

    def remove(self, index: int) -> None:...
    
    def clear(self) -> None:...

    def __iter__(self) -> Iterator[T]:...

    def __len__(self) -> int:...
        
    def __getitem__(self, index: int) -> T:...

# Classes from Yet Another Devkit

class CollectionState(PropertyGroup):
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

    def reset_legs(self, context) -> None:...

    gen       : str
    leg_size  : str
    rue       : bool
    small_butt: bool
    soft_butt : bool
    alt_hips  : bool
    squish    : str

class HandState(PropertyGroup):

    def reset_hands(self, context) -> None:...

    nails    : str
    hand_size: str
    clawsies : str

class FeetState(PropertyGroup):

    def reset_feet(self, context) -> None:...

    rue_feet: bool

class MannequinState(TorsoState, LegState, HandState, FeetState):
    pass

class DevkitProps(PropertyGroup):
    def export_state(self, category: str, piercings: bool, pubes: bool) -> None:...
    def reset_torso(self) -> None:...
    def reset_legs(self) -> None:...
    def reset_hands(self) -> None:...
    def reset_feet(self) -> None:...
    def get_shape_presets(self, size: str) -> dict[str, float]:...

    ALL_SHAPES         : dict[str, tuple[str, ...]]
    chest_shape_enum   : str
    shape_mq_chest_bool: bool
    shape_mq_legs_bool : bool
    shape_mq_other_bool: bool
    
    collection_state: CollectionState
    torso_state     : TorsoState
    leg_state       : LegState
    hand_state      : HandState
    feet_state      : FeetState
    yam_torso       : Object
    yam_legs        : Object
    yam_hands       : Object
    yam_feet        : Object
    yam_mannequin   : Object
    yam_shapes      : Object

    mannequin_state: MannequinState

class DevkitWindowProps(PropertyGroup):
    overview_ui: str
    devkit_triangulation: bool
    yas_storage: str
