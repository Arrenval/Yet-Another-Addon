import bpy

from mathutils      import Matrix
from ...props       import Armature, Object
from .com.integrity import synchronise_bone_list, synchronise_bone_indices


def get_bone_roll(obj: Object) -> dict[str, float]:
    bone_rolls = {}
    if obj is not bpy.context.view_layer.objects.active:
        bpy.context.view_layer.objects.active = obj

    try:
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in obj.data.edit_bones:
            bone_rolls[bone.name] = bone.roll
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
    
    return bone_rolls
      
def combine_sklb(source_obj: Object, target_obj: Object, scale_bones=False) -> None:
    target: Armature = target_obj.data
    source: Armature = source_obj.data

    synchronise_bone_list(source)
    synchronise_bone_list(target)

    existing_bones = {bone.name for bone in target.bones}
    source_cache   = source.kaos.get_cache()
    source_layers  = source.kaos.bone_to_layer_id()
    source_rolls   = get_bone_roll(source_obj)
    target_layers  = {layer.id: layer for layer in target.kaos.anim_layers}
    missing_parent = {}
    new_bones      = []

    if target_obj is not bpy.context.view_layer.objects.active:
        bpy.context.view_layer.objects.active = target_obj

    transform = target_obj.matrix_world.inverted() @ source_obj.matrix_world

    try:
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in source.kaos.bone_list:
            if bone.name in existing_bones:
                continue

            new_bones.append(bone.name)

            bone_data = source.bones.get(bone.name)
            new_bone  = target.edit_bones.new(bone.name)

            new_bone.head = transform @ bone_data.head_local
            new_bone.tail = transform @ bone_data.tail_local
            new_bone.roll = source_rolls[bone.name]
            
            new_bone.kaos_unk = bone_data.kaos_unk

            parent = target.edit_bones.get(source.bones[bone.name].parent.name)
            if not parent and source.bones[bone.name].parent:
                missing_parent[bone.name] = source.bones[bone.name].parent.name
            elif parent:
                new_bone.parent = parent

            new_idx = len(target.kaos.bone_list)
            hk_bone = target.kaos.bone_list.add()
            hk_bone.name  = bone.name
            hk_bone.index = new_idx

            if bone.name in source_layers:
                for id in source_layers[bone.name]:
                    if id not in target_layers:
                        new_layer = target.kaos.anim_layers.add()
                        new_layer.id = id

                        target_layers[id] = new_layer

                    layer_bone = target_layers[id].bone_list.add()
                    layer_bone.name = bone.name

            if bone.name in source_cache:
                cached_bone = source_cache[bone.name]
                new_cache   = target.kaos.bone_cache.add()

                new_cache.name   = bone.name
                new_cache.ctrs   = cached_bone.ctrs
                new_cache.crot   = cached_bone.crot
                new_cache.cscl   = cached_bone.cscl
                new_cache.parent = cached_bone.parent
        
        for bone, parent in missing_parent.items():
            target.bones[bone].parent = target.bones[parent]
        
        if scale_bones:
            processed_bones = set()
            for bone_name in new_bones:
                source_bone = source.bones.get(bone_name)
                root_bone   = not source_bone.parent or source_bone.parent.name in existing_bones

                if not root_bone:
                    continue
                _scale_bone(bone_name, source, target, processed_bones, source_rolls)

    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
    
    synchronise_bone_indices(target)

def _scale_bone(bone_name: str, source: Armature, target: Armature, processed_bones: set[str], source_rolls: dict[str, float]) -> None:
    if bone_name in processed_bones:
        return
    
    processed_bones.add(bone_name)
    
    source_bone = source.bones.get(bone_name)
    target_bone = target.edit_bones.get(bone_name)
    
    if not source_bone or not target_bone:
        return
    
    if not source_bone.parent:
        return
    
    parent_name   = source_bone.parent.name
    source_parent = source.bones.get(parent_name)
    target_parent = target.bones.get(parent_name)
    
    if not (source_parent or target_parent):
        return

    source_parent_mat = source_parent.matrix_local
    target_parent_mat = target_parent.matrix_local
    source_bone_mat   = source_bone.matrix_local
    
    relative_pos     = source_parent_mat.inverted() @ source_bone_mat
    target_bone_mat  = target_parent_mat @ relative_pos
    target_bone.head = target_bone_mat.translation
    
    bone_direction   = target_bone_mat.to_3x3() @ Matrix.Translation((0, source_bone.length, 0)).translation
    target_bone.tail = target_bone.head + bone_direction
    target_bone.roll = source_rolls[bone_name]
    
    for child_bone in source_bone.children:
        if child_bone.name in target.edit_bones:
            _scale_bone(child_bone.name, source, target, processed_bones, source_rolls)
