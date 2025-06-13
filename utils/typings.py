
from typing      import TypedDict, Iterable
from bpy.types   import Object


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

class CollectionState:
    name: str

class ObjectState:
    name: str
    hide: bool

class DevkitProps:
    chest_shape_enum   : str
    shape_mq_chest_bool: bool
    shape_mq_legs_bool : bool
    shape_mq_other_bool: bool
    collection_state   : Iterable[CollectionState]
    object_state       : Iterable[ObjectState]
    overview_ui        : str
    is_exporting       : bool

    ALL_SHAPES  : dict[str, tuple]
    torso_floats: list[dict[str, dict[str, float]]]        
    mq_floats   : list[dict[str, dict[str, float]]]  
    is_exporting: bool 
    mesh_list   : list[str]
