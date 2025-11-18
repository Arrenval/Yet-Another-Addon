from bpy.types             import Bone

from ....props            import Armature, CacheBone
from ....utils.serialiser import RNAPropertyIO


def synchronise_bone_list(armature: Armature) -> None:
    manager        = RNAPropertyIO(indexing=True)
    armature_bones = {bone.name for bone in armature.bones}
    bone_indices   = armature.kaos.get_bone_indices()
    missing_bones  = [bone for bone in armature_bones if bone not in bone_indices]

    manager.remove(armature.kaos.bone_list, filter=armature_bones)
    manager.remove(armature.kaos.bone_cache, filter=armature_bones)

    for layer in armature.kaos.anim_layers:
        manager.remove(layer.bone_list, filter=armature_bones)

    new_idx = len(armature.kaos.bone_list)
    for bone in missing_bones:
        new_bone = armature.kaos.bone_list.add()
        new_bone.name  = bone
        new_bone.index = new_idx
        new_idx += 1

def synchronise_bone_indices(armature: Armature) -> None:
    bone_indices = armature.kaos.get_bone_indices()

    for layer in armature.kaos.anim_layers:
        for bone in layer.bone_list:
            bone.index = bone_indices[bone.name]

def verify_cache(bone: Bone, cache_bone: CacheBone, threshold: float=1e-6) -> bool:
    mat = bone.matrix_local
    trs, rot, scale = mat.decompose()

    if (trs - cache_bone.get_trs()).length > threshold:
        return False
    if (rot - cache_bone.get_rot()).magnitude > threshold:
        return False
    if (scale - cache_bone.get_scl()).length > threshold:
        return False
    
    parent = bone.parent.name if bone.parent else ""
    if parent != cache_bone.parent:
        return False
    
    return True
