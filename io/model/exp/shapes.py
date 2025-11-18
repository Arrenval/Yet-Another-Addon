import numpy as np

from numpy.typing     import NDArray

from .streams         import create_stream_arrays
from .validators      import USHORT_LIMIT

from ....xivpy.model  import XIVModel, Mesh as XIVMesh, VertexDeclaration, SHAPE_VALUE_DTYPE
from ..com.exceptions import XIVMeshError


def _set_shape_stream_values(shape_streams: dict[int, NDArray], submesh_streams: dict[int, NDArray], pos: NDArray, vert_mask: NDArray) -> None:
    for stream_idx, stream in submesh_streams.items():
        for field_name in stream.dtype.names:
            if field_name == "position":
                shape_streams[stream_idx][field_name] = pos[vert_mask]
            else:
                shape_streams[stream_idx][field_name] = stream[field_name][vert_mask]

def create_shape_data(mesh: XIVMesh, pos: NDArray, indices: NDArray, submesh_streams: dict[int, NDArray], vert_decl: VertexDeclaration, threshold: int=1e-6) -> tuple[NDArray, dict[int, NDArray]] | None:
    abs_diff   = np.abs(pos - submesh_streams[0]["position"])
    vert_mask  = np.any(abs_diff > threshold, axis=1)
    vert_count = np.sum(vert_mask)

    if vert_count == 0:
        return
    
    shape_indices = np.where(vert_mask)[0]
    indices_mask  = np.isin(indices, shape_indices)
    indices_idx   = np.where(indices_mask)[0]

    if len(indices_idx) == 0:
        return

    shape_streams = create_stream_arrays(vert_count, vert_decl)
    _set_shape_stream_values(shape_streams, submesh_streams, pos, vert_mask)

    if indices_idx.max() + mesh.idx_count > USHORT_LIMIT:
        raise XIVMeshError(f"Exceeds the {USHORT_LIMIT} indices limit for shape keys.")
    
    vert_map = np.full(len(submesh_streams[0]), -1, dtype=np.int32)
    vert_map[shape_indices] = np.arange(len(shape_indices))

    shape_values = np.zeros(len(indices_idx), dtype=SHAPE_VALUE_DTYPE)
    shape_values["base_indices_idx"] = indices_idx + mesh.idx_count
    shape_values["replace_vert_idx"] = vert_map[indices[indices_idx]]

    return shape_values, shape_streams

def submesh_to_mesh_shapes(mesh: XIVMesh, mesh_idx: int, mesh_shapes: dict[str, list[tuple[int, NDArray]]], submesh_shapes: dict[str, list[tuple[NDArray, dict[int, NDArray]]]], mesh_geo: list[NDArray], mesh_tex: list[NDArray], vert_offset: int) -> int:
    shape_verts = 0
    total_count = 0
    for name, arrays in submesh_shapes.items():
        shape_value_count = sum(len(values) for values, streams in arrays)
        mesh_shape_values = np.zeros(shape_value_count, dtype=SHAPE_VALUE_DTYPE)

        arr_offset = 0
        for values, streams in arrays:
            mesh.vertex_count += len(streams[0])
            if mesh.vertex_count > USHORT_LIMIT:
                raise XIVMeshError(f"Exceeds the {USHORT_LIMIT} vertices limit due to extra shape keys.")
            
            values["replace_vert_idx"] += vert_offset + shape_verts
            mesh_geo.append(streams[0])
            mesh_tex.append(streams[1])

            end_offset = arr_offset + len(values)
            mesh_shape_values[arr_offset: end_offset] = values

            shape_verts += len(streams[0])
            arr_offset   = end_offset

        mesh_shapes[name].append((mesh_idx, mesh_shape_values))
        total_count += shape_value_count
    
    return total_count

def create_face_data(model: XIVModel, position: NDArray) -> None:
    total_count = position.shape[0] + model.mesh_header.face_data_count
    
    arr_offset  = len(model.face_data)
    if arr_offset < total_count:
        model.face_data = np.resize(model.face_data, total_count)
    
    model.face_data["position"][arr_offset:] = position.copy()

    model.mesh_header.face_data_count = total_count
