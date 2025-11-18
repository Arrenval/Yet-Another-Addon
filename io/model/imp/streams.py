import numpy as np

from numpy.typing    import NDArray
 
from ..com.schema    import get_array_type
from ....xivpy.model import Mesh as XIVMesh, VertexDeclaration


def get_submesh_streams(streams: dict[int, NDArray], indices: NDArray) -> tuple[dict[int, NDArray], int]:

    def submesh_vertex_range() -> tuple[int, int]:
        min_idx = np.min(indices)
        max_idx = np.max(indices)
        
        vert_start = min_idx
        vert_count = max_idx - min_idx + 1
        return vert_start, vert_count

    submesh_streams        = {}
    vert_start, vert_count = submesh_vertex_range()
    
    for stream, array in streams.items():
        submesh_streams[stream] = array[vert_start: vert_start + vert_count]
    
    return submesh_streams, vert_start, vert_count

def create_stream_arrays(buffer: bytes, mesh: XIVMesh, vert_decl: VertexDeclaration, mesh_idx: int, blend_space: bool=True) -> dict[int, NDArray]:
    array_types = get_array_type(vert_decl)
    streams     = {}
    for stream, array_type in array_types.items():
        if array_type.itemsize != mesh.vertex_buffer_stride[stream]:
            print(f"Couldn't read Vertex Buffer of Mesh #{mesh_idx}. Array/Buffer: {array_type.itemsize}/{mesh.vertex_buffer_stride[stream]}.")
            return {}
        
        vert_array = np.frombuffer(
                            buffer, 
                            array_type, 
                            mesh.vertex_count, 
                            mesh.vertex_buffer_offset[stream],
                        ).copy()
        
        streams[stream] = vert_array

    return streams
