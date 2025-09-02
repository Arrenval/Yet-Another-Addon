import numpy as np

from numpy        import single, byte
from bpy.types    import Object
from numpy.typing import NDArray

from .norm        import average_vert_normals
from ..com.space  import blend_to_xiv_space


def loop_to_vert(loop_arr: NDArray, indices: NDArray, vert_count: int, shape: int) -> NDArray:
    unique_verts, first_indices = np.unique(indices, return_index=True)

    temp_arr = loop_arr[first_indices]
    vert_arr = np.zeros((vert_count, shape), dtype=single)
    vert_arr[unique_verts] = temp_arr

    return vert_arr

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

        vert_uvs = loop_to_vert(loop_uvs, indices, vert_count, 2)
        uv_arrays.append(vert_uvs)
    
    return uv_arrays

def get_col_attributes(obj: Object, indices: NDArray, vert_count: int, loop_count: int, col_count: int) -> list[NDArray]:
    col_arrays: list[NDArray] = []
    for layer in obj.data.color_attributes[:col_count]:
        if not layer.name.lower().startswith("vc"):
            continue
        if layer.name == "vc0":
            loop_col = np.zeros(loop_count * 4, single)
        else:
            loop_col = np.ones(loop_count * 4, single)
            loop_col[3::4] = 0

        layer.data.foreach_get("color", loop_col)
        loop_col = loop_col.reshape(-1, 4) * 255

        vert_col = loop_to_vert(loop_col, indices, vert_count, 4)
        col_arrays.append(vert_col.astype(byte))
    
    return col_arrays

def get_weights(obj: Object, vert_count: int, group_count: int) -> NDArray:
    weight_matrix = np.zeros((vert_count, group_count), dtype=np.float32)
    for vertex_idx, vertex in enumerate(obj.data.vertices):
        for group in vertex.groups:
            weight_matrix[vertex_idx, group.group] = group.weight

    return weight_matrix
