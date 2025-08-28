import numpy as np

from bpy.types        import Object
from numpy.typing     import NDArray

from .tangents        import get_bitangents
from .accessors       import *
from ..com.accessors  import get_array_type
from ...formats.model import VertexDeclaration, VertexUsage


def get_submesh_streams(obj: Object, vert_decl: VertexDeclaration) -> tuple[NDArray, dict[int, NDArray], dict[str, NDArray]]:
        vert_count = len(obj.data.vertices)
        loop_count = len(obj.data.loops)
        uv_count   = vert_decl.usage_count(VertexUsage.UV)
        col_count  = vert_decl.usage_count(VertexUsage.COLOUR)

        indices = np.zeros(loop_count, np.uint16)
        obj.data.loops.foreach_get("vertex_index", indices)

        pos, nor   = get_space_data(obj, indices, vert_count, loop_count)
        shapes     = get_shape_co(obj, vert_count)
        uv_arrays  = get_uvs(obj, indices, vert_count, loop_count, uv_count)
        col_arrays = get_col_attributes(obj, indices, vert_count, loop_count, col_count)

        streams = create_stream_arrays(vert_count, vert_decl)
        
        streams[0]["position"] = pos
        streams[1]["normal"]   = nor
        streams[1]["tangent"]  = get_bitangents(obj, indices, loop_count, obj.data.uv_layers[0].name)

        for col_idx, col in enumerate(col_arrays):
            streams[1][f"colour{col_idx}"] = col

        for uv_idx, uvs in enumerate(uv_arrays):
            if uv_idx < 2:
                start = uv_idx * 2
                stop  = (uv_idx*2) + 2
                streams[1]["uv0"][:, start: stop] = uvs
            elif uv_idx == 2:
                streams[1]["uv1"] = uvs

        return indices, streams, shapes

def create_stream_arrays(vert_count: int, vert_decl: VertexDeclaration) -> dict[int, NDArray]:
    array_types = get_array_type(vert_decl)
    streams     = {}
    for stream, array_type in array_types.items():

        vert_array = np.zeros(vert_count, array_type)
        
        streams[stream] = vert_array

    return streams
