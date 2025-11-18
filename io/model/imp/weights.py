import numpy as np

from bpy.types        import Object
from numpy.typing     import NDArray

from ....mesh.weights import add_to_vgroup


def create_weight_matrix(obj: Object, weight_array: NDArray, bone_indices: NDArray, bone_table: list[int]) -> NDArray:
    weight_matrix = np.zeros((len(obj.data.vertices), len(bone_table)), dtype=np.float32)

    num_verts, bone_count = bone_indices.shape
    flat_indices = np.repeat(np.arange(num_verts), bone_count)
    flat_weights = weight_array.flatten()   
    nonzero_mask = flat_weights != 0
    
    weight_matrix[flat_indices[nonzero_mask], bone_indices.flatten()[nonzero_mask]] += flat_weights[nonzero_mask]

    return weight_matrix

def set_weights(obj: Object, weight_matrix: NDArray) -> None:
    empty_groups = []
    for v_group in obj.vertex_groups:
        if not np.any(weight_matrix[:, v_group.index] > 0.0):
            empty_groups.append(v_group)
            continue
        add_to_vgroup(weight_matrix, v_group)
    
    for v_group in empty_groups:
        obj.vertex_groups.remove(v_group)
        