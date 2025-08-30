import numpy as np

from numpy.typing import NDArray

from .norm        import normalised_int_array   


def sort_weights(weight_matrix: NDArray, empty_groups: list[int]):
    vert_count, group_count = weight_matrix.shape
    
    valid_group_mask = np.ones(group_count, dtype=bool)
    valid_group_mask[empty_groups] = False
    
    masked_weights = weight_matrix * valid_group_mask[np.newaxis, :]
    
    sorted_indices = np.argsort(masked_weights, axis=1)[:, ::-1]
    row_indices    = np.arange(vert_count)[:, np.newaxis]
    sorted_weights = masked_weights[row_indices, sorted_indices]
    
    return masked_weights, sorted_weights, sorted_indices
    
def normalise_weights(sorted_weights:NDArray, bone_limit: int, threshold: float=1e-6):
    top_weights = np.where(
                        sorted_weights > threshold, 
                        sorted_weights, 
                        0
                    )[:, :bone_limit]
    
    nonzero_mask = top_weights > 0
    weight_sums  = np.sum(top_weights * nonzero_mask, axis=1, keepdims=True)
    
    normalised_weights = np.where(
                                weight_sums != 1.0,
                                top_weights / weight_sums,
                                top_weights
                            ) * nonzero_mask

    return weight_sums, normalised_int_array(normalised_weights)
