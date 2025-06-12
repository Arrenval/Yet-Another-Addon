
from typing      import TypedDict, Iterable, Required, NotRequired, TypeAlias
from bpy.types   import Object
from collections import namedtuple


Preset = TypedDict(
    "Preset",

    {
    "_version": int, 
    "_format" : str, 
    "preset"  : dict,

    "corrections": NotRequired[dict]
    }
)

ObjIterable = Iterable[Object]
BlendEnum   = list[tuple[str, str, str]]
