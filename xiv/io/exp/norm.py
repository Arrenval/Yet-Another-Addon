import numpy as np

from numpy.typing import NDArray


def normalise_vectors(vectors: NDArray) -> NDArray:
    """Assumes float vectors."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)

    return vectors / norms

def average_vert_normals(indices:NDArray, loop_normals: NDArray):
    unique_verts, inverse_indices, counts = np.unique(
            indices, return_inverse=True, return_counts=True
        )

    vert_nor = np.zeros((len(unique_verts), 3), dtype=np.float32)

    for axis in range(3):
        nor_sums   = np.bincount(inverse_indices, weights=loop_normals[:, axis])
        vert_nor[:, axis] = nor_sums / counts
    
    vert_nor = normalise_vectors(vert_nor)

    return vert_nor

def normalised_int_array(float_array: NDArray) -> NDArray:
    int_values = float_array * 255
    
    base_values = np.floor(int_values).astype(np.int16)
    remainders  = 255 - base_values.sum(axis=1) 
    fractional_parts = int_values - base_values    

    rows, cols  = float_array.shape
    row_indices = np.arange(rows)[:, None] 
    
    sorted_col_indices = np.argpartition(
                                    -fractional_parts, 
                                    kth=np.arange(cols), 
                                    axis=1
                                )

    col_pos   = np.arange(cols)
    incr_mask = col_pos < remainders[:, None] 
    
    result    = base_values.copy()
    incr_pos  = sorted_col_indices[incr_mask]
    incr_rows = np.repeat(row_indices.ravel(), remainders)
    
    np.add.at(result, (incr_rows, incr_pos), 1)
    
    return result.astype(np.uint8)
