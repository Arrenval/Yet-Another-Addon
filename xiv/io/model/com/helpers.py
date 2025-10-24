import numpy as np

from numpy        import single, ubyte
from numpy.typing import NDArray


def byte_to_vector(byte_vectors: NDArray) -> NDArray:
    floats = (byte_vectors.astype(single) / (255.0 * 0.5)) - 1
    return normalise_vectors(floats)

def vector_to_bytes(float_tangents: NDArray) -> NDArray:
    clamped_tan = np.clip(float_tangents, -1.0, 1.0)
    compressed  = (clamped_tan + 1) * (255.0 * 0.5)
    
    return compressed.round().astype(ubyte)

def byte_sign(float_signs: NDArray) -> NDArray:
    return np.where(float_signs < 0, 0, -1).astype(ubyte)

def quantise_flow(flow_vectors: NDArray) -> NDArray:
    # 128 steps, align with byte format limitations
    precision = np.pi / 64 
    angles    = np.arctan2(flow_vectors[:, 1], flow_vectors[:, 0])
    quantised = np.round(angles / precision) * precision

    return np.c_[np.cos(quantised), np.sin(quantised)]

def calc_tangents_with_bitangent(normals: NDArray, bitangents: NDArray, signs: NDArray):
    raw_tangents = np.cross(normals, bitangents)
    tangents     = raw_tangents * signs[:, np.newaxis]
    
    return normalise_vectors(tangents)

def calc_tangents(positions: NDArray, uvs: NDArray, indices: NDArray, normals: NDArray) -> tuple[NDArray, NDArray]:
    triangles     = indices.reshape(-1, 3)
    num_triangles = len(triangles)
    
    tri_pos = positions[triangles] 
    tri_uvs = uvs[triangles]       
    
    edge1_3d = tri_pos[:, 1] - tri_pos[:, 0] 
    edge2_3d = tri_pos[:, 2] - tri_pos[:, 0] 
    
    edge1_uv = tri_uvs[:, 1] - tri_uvs[:, 0] 
    edge2_uv = tri_uvs[:, 2] - tri_uvs[:, 0] 
    
    uv_determinants = edge1_uv[:, 0] * edge2_uv[:, 1] - edge2_uv[:, 0] * edge1_uv[:, 1]
    valid_mask      = np.abs(uv_determinants) > 1e-6
    
    tri_tan   = np.zeros((num_triangles, 3), dtype=single)
    tri_bitan = np.zeros((num_triangles, 3), dtype=single)
    
    if np.any(valid_mask):
        valid_determinants = uv_determinants[valid_mask]
        
        tri_tan[valid_mask] = (
            (edge2_uv[valid_mask, 1:2] * edge1_3d[valid_mask]) - (edge1_uv[valid_mask, 1:2] * edge2_3d[valid_mask])
        ) / valid_determinants[:, np.newaxis]
        
        tri_bitan[valid_mask] = (
            (edge1_uv[valid_mask, 0:1] * edge2_3d[valid_mask]) - (edge2_uv[valid_mask, 0:1] * edge1_3d[valid_mask])
        ) / valid_determinants[:, np.newaxis]
    
    if np.any(~valid_mask):
        tri_tan[~valid_mask]   = np.array([1.0, 0.0, 0.0])
        tri_bitan[~valid_mask] = np.array([0.0, 1.0, 0.0])
    
    vert_tan    = np.zeros_like(positions)
    vert_bitan  = np.zeros_like(positions)
    vert_counts = np.zeros(len(positions))
    
    for i in range(3):  
        np.add.at(vert_tan, triangles[:, i], tri_tan)
        np.add.at(vert_bitan, triangles[:, i], tri_bitan)
        np.add.at(vert_counts, triangles[:, i], 1)
    
    vert_counts = np.maximum(vert_counts, 1)
    tangents    = vert_tan / vert_counts[:, np.newaxis]
    bitangents  = vert_bitan / vert_counts[:, np.newaxis]
    
    tangents   = normalise_vectors(tangents)
    bitangents = normalise_vectors(bitangents)
    
    signs = calc_sign(vert_tan, vert_bitan, normals)
    bitangents = vert_bitan * signs[:, np.newaxis]
    
    return tangents, bitangents

def calc_sign(tangents: NDArray, bitangents: NDArray, normals: NDArray) -> NDArray:
    dot_product = np.sum(tangents * np.cross(normals, bitangents), axis=1)

    return np.where(dot_product >= 0, -1.0, 1.0)

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
        nor_sums = np.bincount(inverse_indices, weights=loop_normals[:, axis])
        vert_nor[:, axis] = nor_sums / counts
    
    vert_nor = normalise_vectors(vert_nor)

    return vert_nor

def normalised_int_array(float_array: NDArray) -> NDArray:
    int_values = float_array * 255
    
    base_values = np.floor(int_values).astype(np.int16)
    remainders  = 255 - base_values.sum(axis=1) 
    fractions   = int_values - base_values    
    col_pos     = np.arange(float_array.shape[1])
    incr_mask   = col_pos < remainders[:, None]
    
    sorted_col_indices = np.argpartition(
                                    -fractions, 
                                    kth=col_pos, 
                                    axis=1
                                )

    result    = base_values.copy()
    incr_pos  = sorted_col_indices[incr_mask]
    incr_rows = np.where(incr_mask)[0]
    
    np.add.at(result, (incr_rows, incr_pos), 1)
    
    return result.astype(np.uint8)
