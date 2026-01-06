from math            import radians
from bpy.types       import Bone
from functools       import singledispatch
from mathutils       import Vector, Quaternion, Matrix

from ....props       import Armature, SklbMapper, MapBone
from ..com.space     import blend_to_hkvec, blend_to_hkquat
from ..com.integrity import verify_cache


class BoneNode:
    local_trs: Vector     = None
    local_rot: Quaternion = None
    local_scl: Vector     = Vector([1, 1, 1, 1])
    parent   : int        = -1
    unknown  : float      = 0

    def to_list(self) -> list[float]:
        floats      = [0.0 for _ in range(12)]
        floats[:3]  = self.local_trs
        floats[4:8] = self.local_rot
        floats[8:]  = self.local_scl
        floats[3]   = self.unknown

        return floats

@singledispatch
def get_bone_data(bone_source: Armature | SklbMapper, bone_indices: dict[str, int]) -> dict[str, BoneNode]: ...
    
@get_bone_data.register
def _from_armature(armature: Armature, bone_indices: dict[str, int]):
    node_data  = {}
    cache      = armature.kaos.get_cache()
    cache_fail = set()
    
    for bone in armature.bones:
        valid_cache  = verify_cache(bone, cache[bone.name]) if bone.name in cache else False
        valid_parent = not bone.parent or bone.parent.name not in cache_fail

        if valid_cache and valid_parent:
            node_data[bone.name] = get_cached_bone(cache[bone.name], bone_indices)

        else:
            node_data[bone.name] = calc_bone_node(bone, bone_indices)
            if not valid_cache:
                cache_fail.add(bone.name)
    
    return node_data

@get_bone_data.register
def _from_mapper(mapper: SklbMapper, bone_indices: dict[str, int]):
    node_data = {}
    for bone in mapper.bone_list:
        print(bone.name)
        node_data[bone.name] = get_cached_bone(bone, bone_indices)

    return node_data

def calc_bone_node(bone: Bone, bone_indices: dict[str, int]) -> BoneNode:
    node = BoneNode()

    if bone.parent:
        node.parent = bone_indices[bone.parent.name]
        mat = bone.parent.matrix_local.inverted_safe() @ bone.matrix_local
    else:
        mat = Matrix.Rotation(radians(90), 4, 'Z') @ bone.matrix_local 

    trs, rot, scale = mat.decompose()
    if rot.w < 0: rot.negate()

    temp_rot       = blend_to_hkquat(rot)  
    node.local_trs = blend_to_hkvec(trs)
    node.local_rot = Quaternion([temp_rot.x, temp_rot.y, temp_rot.z, temp_rot.w])
    node.unknown   = bone.kaos_unk or 0

    if node.local_rot[3] < 0:  
        node.local_rot = [-component for component in node.local_rot]

    return node

def get_cached_bone(bone: MapBone, bone_indices: dict[str, int]):
    node = BoneNode()

    node.local_trs = Vector(bone.pos)
    node.local_rot = Quaternion([bone.rot[1], bone.rot[2], bone.rot[3], bone.rot[0]])
    node.local_scl = Vector(bone.scale)
    node.unknown   = bone.unknown
    node.parent    = bone_indices[bone.parent] if bone.parent else -1
    
    return node
