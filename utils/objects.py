import bpy

from typing    import Literal
from bpy.types import Object

from .typings import ObjIterable

def visible_meshobj() -> ObjIterable:
    """Checks all visible objects and returns them if they contain a mesh."""

    visible_meshobj = [
        obj for obj in bpy.context.scene.objects 
        if obj.visible_get(view_layer=bpy.context.view_layer) and obj.type == "MESH"
        ]

    return sorted(visible_meshobj, key=lambda obj: obj.name)

def get_object_from_mesh(mesh_name:str) -> Object | Literal[False]:
    """Returns the object bashed on mesh name."""
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.data.name == mesh_name:
            return obj
    return False
