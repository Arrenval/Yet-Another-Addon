import numpy as np

from bpy.types         import Object
from numpy.typing      import NDArray
 
from .accessors        import *
from ..com.schema      import get_array_type
from ..com.helpers     import vector_to_bytes, byte_sign
from ....formats.model import VertexDeclaration, VertexUsage, Mesh as XIVMesh


def get_submesh_streams(obj: Object, vert_decl: VertexDeclaration, mesh_flow: bool) -> tuple[NDArray, dict[int, NDArray], dict[str, NDArray]]:
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
        bitangents = get_bitangents(obj, indices, loop_count, obj.data.uv_layers[0].name)

        streams = create_stream_arrays(vert_count, vert_decl)
        
        streams[0]["position"] = pos
        streams[1]["normal"]   = nor
        streams[1]["tangent"]  = np.c_[vector_to_bytes(bitangents[:, :3].copy()), byte_sign(bitangents[:, 3].copy())]
        if mesh_flow:
            streams[1]["flow"] = get_flow(obj, nor, bitangents, indices, vert_count, loop_count)

        for col_idx, col in enumerate(col_arrays):
            streams[1][f"colour{col_idx}"] = col

        for uv_idx, uvs in enumerate(uv_arrays):
            if uv_idx < 2:
                start = uv_idx * 2
                stop  = start + 2
                streams[1]["uv0"][:, start: stop] = uvs
            elif uv_idx == 2:
                streams[1]["uv1"] = uvs

        return indices, streams, shapes

def update_mesh_streams(mesh: XIVMesh, mesh_streams: dict[int, NDArray], mesh_geo: list[NDArray], mesh_tex: list[NDArray], stream_offset: int, bone_limit: int) -> int:
        
    def update_geo_stream(mesh_geo_stream: NDArray, submesh_geo_stream: NDArray):
        if bone_limit < 5:
            for field in geo_stream.dtype.names:
                if field in ["blend_weights", "blend_indices"]:
                    mesh_geo_stream[field][:] = submesh_geo_stream[field][:, :4]
                else:
                    mesh_geo_stream[field][:] = submesh_geo_stream[field]
        else:
            mesh_geo_stream[:] = geo_stream

    for stream, mesh_arr in mesh_streams.items():
        stride = mesh_arr.dtype.itemsize
        mesh.vertex_buffer_offset[stream] = stream_offset
        mesh.vertex_buffer_stride[stream] = stride
        stream_offset += stride * len(mesh_arr)
        
    offset = 0
    for geo_stream, tex_stream in zip(mesh_geo, mesh_tex):
        update_geo_stream(mesh_streams[0][offset: offset + len(geo_stream)], geo_stream)
        mesh_streams[1][offset: offset + len(tex_stream)] = tex_stream
        offset += len(geo_stream)

    return stream_offset

def create_stream_arrays(vert_count: int, vert_decl: VertexDeclaration) -> dict[int, NDArray]:
    array_types = get_array_type(vert_decl)
    streams     = {}
    for stream, array_type in array_types.items():
        vert_array = np.zeros(vert_count, array_type)
        if "flow" in vert_array.dtype.names:
            vert_array["flow"][:, 2:] = 255
        if "colour0" in vert_array.dtype.names:
            vert_array["colour0"][:]  = 255
        if "colour1" in vert_array.dtype.names:
            vert_array["colour1"][:, 3] = 255
            
        streams[stream] = vert_array

    return streams
