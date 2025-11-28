from math         import radians
from mathutils    import Vector, Matrix, Quaternion
from dataclasses  import dataclass, field
from collections  import defaultdict
from numpy.typing import NDArray


CONNECTING_BONES: dict[str, str] = {
                                        "j_ude_a_r": "j_ude_b_r",
                                        "j_ude_a_l": "j_ude_b_l",
                                        "j_ude_b_r": "j_te_r",
                                        "j_ude_b_l": "j_te_l",
                                        "j_sebo_b" : "j_sebo_c",
                                        "j_sebo_c" : "j_kubi"
                                    }

BASE_BONES: set[str] = {"n_root", "n_throw", "n_hara", "n_hara_noanim_trans"}

@dataclass
class BoneData:
    local_trs: Vector      = None
    local_rot: Quaternion  = None
    local_scl: Vector      = None
    arma_mat : Matrix      = None
    length   : Vector      = None
    parent   : str | None  = None
    children : list[str]   = field(default_factory=list)
    unknown  : int         = None
    raw      : list[float] = field(default_factory=list)       

def calc_bone_data(bone_list: list[str], bone_parents: list[int], bone_values: NDArray) -> dict[str, BoneData]:
    child_bones = defaultdict(list)
    bone_data: dict[str, BoneData] = {}
    for bone_idx, bone_name in enumerate(bone_list):
        bone = BoneData()
        parent_idx  = bone_parents[bone_idx]
        bone.parent = bone_list[parent_idx] if parent_idx > -1 else None
        values      = bone_values[bone_idx]
        
        pos = Vector(values[:3])
        rot = Quaternion([
                    values[7],
                    values[4], 
                    values[5], 
                    values[6],])
        
        scale = Vector(values[8:])
        
        bone.local_trs = pos
        bone.local_rot = rot 
        bone.local_scl = scale.xzyw
        bone.unknown   = values[3]
        bone.raw       = values
        
        bone_data[bone_name] = bone
        if bone.parent:
            child_bones[bone.parent].append(bone_name)

    for bone_name in bone_list:
        bone_data[bone_name].children = child_bones.get(bone_name, [])

    return bone_data

# References Khronos Group's GLTF vnode implementation:
# https://github.com/KhronosGroup/glTF-Blender-IO/blob/main/addons/io_scene_gltf2/blender/imp/vnode.py

def blend_bones(bone_list: list[str], bone_data: dict[str, BoneData]) -> None:

    def visit(bone_name):
        data        = bone_data[bone_name]
        data.length = pick_bone_length(bone_name, bone_data)
        calc_arma_matrix(data, bone_data)

        for name in data.children:
            visit(name)
    
    for bone_name in bone_list:
        if bone_data[bone_name].parent is None:
            visit(bone_name)

def calc_arma_matrix(data: BoneData, bone_data: dict[str, BoneData]) -> None:
        local_matrix = (
                        Matrix.Translation(data.local_trs) @ 
                        data.local_rot.to_matrix().to_4x4()
                        )
        
        if data.parent is None:
            correction = Matrix.Rotation(radians(90), 4, 'X')
            data.arma_mat = correction @ local_matrix
        else:
            parent_arma   = bone_data[data.parent].arma_mat
            data.arma_mat = parent_arma @ local_matrix

MIN_BONE_LENGTH = 0.001  

def pick_bone_length(bone_name: str, bone_data: dict[str, BoneData]):

    def find_chain() -> list[Vector]:
        stem_idx = -2 if bone_name.endswith(("_l", "_r")) else -1
        split    = bone_name.split("_")[:stem_idx]
        if len(split) < 2:
            return []
        
        stem  = "_".join(split)
        chain = [bone_data[child].local_trs
                for child in data.children
                if child.startswith(stem)]
        
        chain = [loc for loc in chain if loc.length > MIN_BONE_LENGTH]

        return chain
 
    data = bone_data[bone_name]
    
    if bone_name in CONNECTING_BONES:
        return bone_data[CONNECTING_BONES[bone_name]].local_trs.length
    
    if bone_name in BASE_BONES:
        return 0.1
    
    chain = find_chain()
    if chain:
        return chain[0].length
    
    child_locs = [bone_data[child].local_trs
                  for child in data.children]
    
    child_locs = [loc for loc in child_locs if loc.length > MIN_BONE_LENGTH]
    
    if child_locs:
        
        return min(loc.length for loc in child_locs)
    
    if data.parent is not None:
        parent_length = bone_data[data.parent].length
        if parent_length is not None:
            if bone_name.startswith(("n_", "iv_", "ya_")):
                return parent_length * 0.3
            else:
                return parent_length
    
    if data.local_trs.length > MIN_BONE_LENGTH:
        return data.local_trs.length
     
    return 0.1
