from mathutils      import Vector, Quaternion

from ...props       import Armature, SklbMapper
from .exp.bones     import get_bone_data
from .com.integrity import synchronise_bone_list


def calculate_mapping(armature: Armature, parent_idx: int, existing=False) -> None:
    mapper = armature.kaos.mappers[parent_idx]
    if mapper.new_source:
        mapper_from_armature(mapper, mapper.new_source.data)

    existing_maps = {bone.bone_a for bone in mapper.bone_maps} if not existing else set()
    parent_bones  = get_bone_data(mapper, mapper.get_bone_indices())
    base_bones    = get_bone_data(armature, armature.kaos.get_bone_indices())
    bone_list     = [bone.name for bone in armature.kaos.bone_list 
                     if bone.name in parent_bones and bone.name not in existing_maps]
    
    if existing:
        mapper.bone_maps.clear()
    
    for bone in bone_list:
        new_map  = mapper.bone_maps.add()
        p_bone   = parent_bones[bone]
        b_bone   = base_bones[bone]

        new_map.bone_a = bone
        new_map.bone_b = bone

        p_bone.local_rot = Quaternion([p_bone.local_rot.z, p_bone.local_rot.w, p_bone.local_rot.x, p_bone.local_rot.y])
        b_bone.local_rot = Quaternion([b_bone.local_rot.z, b_bone.local_rot.w, b_bone.local_rot.x, b_bone.local_rot.y])

        scale = b_bone.local_trs.length / p_bone.local_trs.length if p_bone.local_trs.length > 0.01 else 1
        new_map.scale   = Vector([scale for _ in range(4)])
        new_map.pos     = b_bone.local_trs - (p_bone.local_trs * scale)
        new_map.unknown = b_bone.unknown - (p_bone.unknown * scale)
        new_rot         = b_bone.local_rot @ p_bone.local_rot.inverted()

        if new_rot.w < 0: new_rot.negate()

        new_map.rot = new_rot

def mapper_from_armature(mapper: SklbMapper, armature: Armature) -> None:
    synchronise_bone_list(armature)
    mapper.race_id = armature.kaos.race_id

    bone_indices = armature.kaos.get_bone_indices()
    bone_data    = get_bone_data(armature, bone_indices)

    mapper.bone_list.clear()
    for bone_name in bone_indices:
        if bone_name not in bone_data:
            continue

        data   = bone_data[bone_name]
        bone   = mapper.bone_list.add()
        parent = armature.bones[bone_name].parent

        bone.name    = bone_name
        bone.parent  = parent.name if parent else ""
        bone.pos     = data.local_trs
        bone.rot     = Quaternion([data.local_rot.z, data.local_rot.w, data.local_rot.x, data.local_rot.y])
        bone.scale   = data.local_scl
        bone.unknown = data.unknown

    mapper.bone_maps.clear()
