import numpy as np

from numpy         import single, ubyte
from numpy.typing  import NDArray
            
from ..com.helpers import byte_to_vector, normalise_vectors, calc_tangents_with_bitangent, quantise_flow
from ..com.space   import xiv_to_blend_space, tangent_to_world_space


def get_positions(streams: dict[int, NDArray]) -> NDArray:
    return xiv_to_blend_space(streams[0]["position"])

def get_shape_positions(streams: dict[int, NDArray], shape_vertices: NDArray, shape_indices: NDArray) -> NDArray:
    pos     = streams[0]["position"].copy()
    new_pos = pos[shape_vertices]
    pos[shape_indices] = xiv_to_blend_space(new_pos)

    return pos

def get_normals(streams: dict[int, NDArray]) -> NDArray | None:
    return xiv_to_blend_space(normalise_vectors(streams[1]["normal"][:, :3]))

def get_uv0(streams: dict[int, NDArray]) -> list[NDArray]:
    uv_arrays = []
    
    uv0       = streams[1]["uv0"].copy()
    uv0[:, 1] = 1 - uv0[:, 1] 
    uv_arrays.append(uv0[:, :2])
    if uv0.shape[1] == 4:
        uv0[:, 3] = 1 - uv0[:, 3] 
        uv_arrays.append(uv0[:, 2:])

    return uv_arrays

def get_uv1(streams: dict[int, NDArray]) -> NDArray:
    uv1       = streams[1]["uv1"].copy()
    uv1[:, 1] = 1 - uv1[:, 1] 
    return uv1

def get_colours(streams: dict[int, NDArray], count: int) -> list[NDArray]:
    col_arrays = []
    for idx in range(count):
        field = f"colour{idx}"
        col_arrays.append(streams[1][field].view(ubyte) / 255.0)

    return col_arrays

def get_bitangents(streams: dict[int, NDArray]) -> NDArray:
    stream_tangents   = xiv_to_blend_space(streams[1]["tangent"])
    bitangents        = np.zeros(stream_tangents.shape, dtype=single)
    bitangents[:, :3] = byte_to_vector(stream_tangents[:, :3])
    bitangents[:, 3]  = np.where(stream_tangents[:, 3] == 255, -1.0, 1.0)

    return normalise_vectors(bitangents)
    
def get_flow(flow_vectors: NDArray, normals: NDArray, bitangents: NDArray) -> NDArray:
    flow_vectors = xiv_to_blend_space(byte_to_vector(flow_vectors))[:, :3]
    signs        = bitangents[:, 3]
    bitangents   = bitangents[:, :3]
    tangents     = calc_tangents_with_bitangent(normals, bitangents, signs)
    world_flow   = tangent_to_world_space(flow_vectors, tangents, bitangents, normals)
    quantised    = quantise_flow(world_flow[:, :2])
   
    return _flow_colour(quantised)
    
def _flow_colour(world_flow: NDArray) -> NDArray:
    rg_col = (normalise_vectors(world_flow) + 1.0) / 2.0
    ba_col = np.ones((len(world_flow), 2))
    
    return np.c_[rg_col, ba_col]
           