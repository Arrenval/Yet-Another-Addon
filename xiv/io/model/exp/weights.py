import numpy as np

from numpy.typing import NDArray


def sort_weights(weight_matrix: NDArray, empty_groups: list[int]) -> tuple[NDArray, NDArray, NDArray]:
    vert_count, group_count = weight_matrix.shape
    
    valid_group_mask = np.ones(group_count, dtype=bool)
    valid_group_mask[empty_groups] = False
    
    masked_weights = weight_matrix * valid_group_mask[np.newaxis, :]
    
    sorted_indices = np.argsort(masked_weights, axis=1)[:, ::-1]
    row_indices    = np.arange(vert_count)[:, np.newaxis]
    sorted_weights = masked_weights[row_indices, sorted_indices]
    
    return masked_weights, sorted_weights, sorted_indices
    
def normalise_weights(sorted_weights:NDArray, bone_limit: int, threshold: float=1e-6) -> tuple[NDArray, NDArray] :
    top_weights = np.where(
                        sorted_weights > threshold, 
                        sorted_weights, 
                        0
                    )[:, :bone_limit]
    
    weight_sums  = np.sum(top_weights, axis=1, keepdims=True)
    norm_weights = np.where(
                        (weight_sums != 1.0) & (weight_sums > 0),
                        top_weights / weight_sums,
                        top_weights
                    )
    
    return weight_sums, norm_weights

def empty_vertices(blend_weights: NDArray, blend_indices: NDArray) -> int:
    empty_vertices = np.all(blend_weights == 0, axis=1)
    blend_indices[empty_vertices, 0] = 0
    blend_weights[empty_vertices, 0] = 1.0

    return np.sum(empty_vertices)