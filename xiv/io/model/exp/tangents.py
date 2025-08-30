import numpy as np

from numpy        import single, ubyte
from bpy.types    import Object
from numpy.typing import NDArray

from ..com.space  import blend_to_xiv_space
    

def tangent_bytes(float_tangents: NDArray) -> NDArray:
    clamped_tan = np.clip(float_tangents, -1.0, 1.0)
    compressed  = (clamped_tan + 1) * (255.0 * 0.5)
    
    return compressed.round().astype(ubyte) 

def get_bitangents(obj: Object, indices: NDArray, loop_count: NDArray, uv_layer: str) -> NDArray:
    obj.data.calc_tangents(uvmap=uv_layer)

    loop_bitan = np.zeros(loop_count * 3, single)
    obj.data.loops.foreach_get("bitangent", loop_bitan)
    loop_bitan = blend_to_xiv_space(loop_bitan.reshape(-1, 3))

    loop_bi_sign = np.zeros(loop_count, single)
    obj.data.loops.foreach_get("bitangent_sign", loop_bi_sign)
    loop_bi_sign = np.where(loop_bi_sign < 0, 0, -1)

    # Broadcast loop values based on our indices back into the vertex array.
    # Note that this requires that any UV seams and sharp edges were split earlier.
    unique_verts, first_indices = np.unique(indices, return_index=True)

    temp_vert_bitan  = loop_bitan[first_indices]
    temp_vert_bisign = loop_bi_sign[first_indices]
    
    num_vertices = len(obj.data.vertices)
    vert_tan     = np.zeros((num_vertices, 3), dtype=single)
    vert_bisign  = np.zeros(num_vertices, dtype=single)
    
    vert_tan[unique_verts]    = temp_vert_bitan
    vert_bisign[unique_verts] = temp_vert_bisign

    byte_tan = np.zeros((len(vert_tan), 4), dtype=ubyte)
    byte_tan[:, :3] = tangent_bytes(vert_tan)  
    byte_tan[:, 3]  = vert_bisign.astype(ubyte)

    return byte_tan