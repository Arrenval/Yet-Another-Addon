import re
import bpy

from typing    import Literal
from bpy.types import Object, Depsgraph


def xiv_mesh_check(obj: Object) -> bool:
    return (re.search(r"^\d+.\d+\s", obj.name) or re.search(r"\s\d+.\d+$", obj.name))

def visible_meshobj(mesh_id=False) -> list[Object]:
    """
    Checks all visible objects and returns them if they contain a mesh. 
    If looking for xiv mesh IDs it will also hide non-xiv meshes
    """

    visible_meshobj = []
    for obj in bpy.context.scene.objects:
        if not obj.visible_get(view_layer=bpy.context.view_layer):
            continue
        if not obj.type == 'MESH':
            continue
        if mesh_id and not xiv_mesh_check(obj):
            obj.hide_set(state=True)
            continue

        visible_meshobj.append(obj)

    return sorted(visible_meshobj, key=lambda obj: obj.name)

def get_collection_obj(collection_name: str, type='ANY', sub_collections=False) -> list[Object]:
    collection = bpy.data.collections.get(collection_name)

    all_objects = []
    if type == 'ANY':
        all_objects.extend[collection.objects]

    else:
        objects = [obj for obj in collection.objects if obj.type == type]
        all_objects.extend(objects)
    
    if sub_collections:
        for children in collection.children:
            sub_obj = get_collection_obj(children.name, type=type, sub_collections=True)
            all_objects.extend(sub_obj)
    
    return all_objects

def get_object_from_mesh(mesh_name:str) -> Object | Literal[False]:
    """Returns the object bashed on mesh name."""
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.data.name == mesh_name:
            return obj
    return False

def safe_object_delete(obj: Object) -> None:
    """Safely delete an object with proper reference cleanup."""
    if not obj or obj.name not in bpy.data.objects:
        return
        
    try:
        if obj.parent:
            obj.parent = None

        if obj.animation_data:
            obj.animation_data_clear()
            
        if obj.data and obj.data.shape_keys:
            if obj.data.shape_keys.animation_data:
                obj.data.shape_keys.animation_data_clear()
        
        for collection in obj.users_collection:
            collection.objects.unlink(obj)
        
        # If it's a mesh type and its sole user, we just delete the object from the data level.
        if obj.data and obj.type == "MESH" and obj.data.users == 1:
            bpy.data.meshes.remove(obj.data, do_unlink=True, do_id_user=True, do_ui_user=True)
        else:
            bpy.data.objects.remove(obj, do_unlink=True, do_id_user=True, do_ui_user=True)
        
    except Exception as e:
        print(f"Error deleting object {obj.name}: {e}")

def copy_mesh_object(source_obj: Object, depsgraph: Depsgraph, export=True) -> Object:
    """Fast evaluated mesh copy without depsgraph update."""

    eval_obj  = source_obj.evaluated_get(depsgraph)

    new_obj      = source_obj.copy()
    new_obj.data = bpy.data.meshes.new_from_object(
                    eval_obj, 
                    preserve_all_data_layers=True, 
                    depsgraph=depsgraph
                    )
    
    for collection in source_obj.users_collection:
        collection.objects.link(new_obj)

    new_obj.parent = source_obj.parent
    
    # If we don't do this, we will crash later if the original mesh had an invalid driver.
    if new_obj.animation_data:
        new_obj.animation_data_clear()
        
    if new_obj.data.shape_keys:
        if new_obj.data.shape_keys.animation_data:
            new_obj.data.shape_keys.animation_data_clear()
        
    # This is just cleanup
    new_obj.modifiers.clear()
    new_obj.shape_key_clear()

    # Assuming TT FBX import needs an armature modifier.
    if export:
        armature        = new_obj.modifiers.new(name="Armature", type="ARMATURE")
        armature.object = source_obj.parent

    return new_obj

def quick_copy(source_obj: Object, key_name: str=None) -> Object:
    temp_obj      = source_obj.copy()
    temp_obj.data = source_obj.data.copy()

    # When using these you will need to call a despgraph update afterwards if you want to evaluate them
    if key_name:
        temp_obj.data.shape_keys.key_blocks[key_name].mute = False
        temp_obj.data.shape_keys.key_blocks[key_name].value = 1

    for collection in source_obj.users_collection:
        collection.objects.link(temp_obj)

    if temp_obj.animation_data:
        temp_obj.animation_data_clear()
        
    if temp_obj.data.shape_keys:
        if temp_obj.data.shape_keys.animation_data:
            temp_obj.data.shape_keys.animation_data_clear()

    return temp_obj

def evaluate_obj(obj: Object, depsgraph: Depsgraph) -> Object:
        eval_obj  = obj.evaluated_get(depsgraph)
        obj.data = bpy.data.meshes.new_from_object(
                        eval_obj,
                        preserve_all_data_layers=True,
                        depsgraph=depsgraph)
        