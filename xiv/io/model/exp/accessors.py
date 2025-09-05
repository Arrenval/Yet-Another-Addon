import numpy as np

from numpy        import single, byte, ubyte
from bpy.types    import Object
from numpy.typing import NDArray

from .norm        import average_vert_normals
from ..com.space  import blend_to_xiv_space


def _loop_to_vert(loop_arr: NDArray, indices: NDArray, vert_count: int, shape: int) -> NDArray:
    unique_verts, first_indices = np.unique(indices, return_index=True)

    temp_arr = loop_arr[first_indices]
    vert_arr = np.zeros((vert_count, shape), dtype=single)
    vert_arr[unique_verts] = temp_arr

    return vert_arr

def _tangent_bytes(float_tangents: NDArray) -> NDArray:
    clamped_tan = np.clip(float_tangents, -1.0, 1.0)
    compressed  = (clamped_tan + 1) * (255.0 * 0.5)
    
    return compressed.round().astype(ubyte)

def get_space_data(obj: Object, indices: NDArray, vert_count: int, loop_count: int) -> tuple[NDArray]:
    pos = np.zeros(vert_count * 3, single)
    obj.data.vertices.foreach_get("co", pos)
    pos = blend_to_xiv_space(pos.reshape(-1, 3))

    nor = np.zeros(loop_count * 3, single)
    obj.data.loops.foreach_get("normal", nor)
    loop_nor = blend_to_xiv_space(nor.reshape(-1, 3))

    return pos, average_vert_normals(indices, loop_nor)

def get_shape_co(obj: Object, vert_count: int) -> dict[str, NDArray]:
    shapes: dict[str, NDArray] = {}
    if obj.data.shape_keys:
        for shape_key in obj.data.shape_keys.key_blocks[1:] or []:
            shape_pos = np.zeros(vert_count * 3, single)
            shape_key.data.foreach_get("co", shape_pos)
            shapes[shape_key.name] = blend_to_xiv_space(shape_pos.reshape(-1, 3))
    
    return shapes

def get_uvs(obj: Object, indices: NDArray, vert_count: int, loop_count: int, uv_count: int) -> tuple[list[NDArray], NDArray]:
    uv_arrays: list[NDArray]    = []
    for uv_layer in obj.data.uv_layers[:uv_count]:
        if not uv_layer.name.lower().startswith("uv"):
            continue
        loop_uvs = np.zeros(loop_count * 2, single)
        vert_uvs = np.zeros((vert_count, 2), single)

        uv_layer.uv.foreach_get("vector", loop_uvs)
        loop_uvs = loop_uvs.reshape(-1, 2)
        loop_uvs[:, 1] = 1 - loop_uvs[:, 1]

        vert_uvs = _loop_to_vert(loop_uvs, indices, vert_count, 2)
        uv_arrays.append(vert_uvs)
    
    return uv_arrays

def get_col_attributes(obj: Object, indices: NDArray, vert_count: int, loop_count: int, col_count: int) -> list[NDArray]:
    col_arrays: list[NDArray] = []
    for layer in obj.data.color_attributes[:col_count]:
        if not layer.name.lower().startswith("vc"):
            continue
        
        loop_col = np.zeros(loop_count * 4, single)
        layer.data.foreach_get("color", loop_col)
        loop_col = loop_col.clip(0.0, 1.0)
        loop_col = loop_col.reshape(-1, 4) * 255

        vert_col = _loop_to_vert(loop_col, indices, vert_count, 4)
        col_arrays.append(vert_col.astype(byte))
    
    return col_arrays

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
    byte_tan[:, :3] = _tangent_bytes(vert_tan)  
    byte_tan[:, 3]  = vert_bisign.astype(ubyte)

    return byte_tan

def get_weights(obj: Object, vert_count: int, group_count: int) -> NDArray:
    weight_matrix = np.zeros((vert_count, group_count), dtype=np.float32)
    for vertex_idx, vertex in enumerate(obj.data.vertices):
        for group in vertex.groups:
            weight_matrix[vertex_idx, group.group] = group.weight

    return weight_matrix
