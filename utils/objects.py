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

def safe_object_delete(obj: Object):
    """Safely delete an object with proper reference cleanup."""
    if not obj or obj.name not in bpy.data.objects:
        return
        
    try:
        if obj.parent:
            obj.parent = None

        if obj.animation_data:
            obj.animation_data_clear()
            
        if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys:
            if obj.data.shape_keys.animation_data:
                obj.data.shape_keys.animation_data_clear()
        
        for collection in obj.users_collection:
            collection.objects.unlink(obj)
        
        bpy.data.objects.remove(obj, do_unlink=True, do_id_user=True, do_ui_user=True)
        
    except Exception as e:
        print(f"Error deleting object {obj.name}: {e}")
