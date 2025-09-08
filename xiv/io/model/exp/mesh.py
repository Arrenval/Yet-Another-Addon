import numpy as np

from numpy             import ushort, single, ubyte
from bpy.types         import Object
from numpy.typing      import NDArray
from collections       import defaultdict

from .norm             import normalised_int_array 
from .weights          import sort_weights, normalise_weights, empty_vertices
from ...logging        import YetAnotherLogger
from .streams          import create_stream_arrays, get_submesh_streams
from .accessors        import get_weights
from .validators       import clean_material_name  
from ..com.exceptions  import XIVMeshError
from ....formats.model import (XIVModel, Mesh as XIVMesh, Submesh, 
                              BoundingBox, VertexDeclaration, 
                              VertexUsage, VertexType)


USHORT_LIMIT = np.iinfo(ushort).max

class MeshHandler:

    def __init__(self, model: XIVModel, lod_bones: list[str], mesh_idx: int=0, idx_offset: int=0, stream_offset: int=0, shape_value_count: int=0, logger: YetAnotherLogger=None):
        self.model     = model
        self.idx       = mesh_idx
        self.lod_bones = lod_bones
        self.logger    = logger

        self.mesh = XIVMesh()
        self.bbox = BoundingBox()

        self.bone_limit = 4
        self.idx_buffer = b''

        self.idx_offset        = idx_offset
        self.stream_offset     = stream_offset
        self.shape_value_count = shape_value_count

        self.submeshes   : list[Submesh]        = []
        self.vert_buffers: list[NDArray]        = []
        self.shape_meshes: dict[str, NDArray]   = {}
        self.export_stats: dict[str, list[str]] = defaultdict(list)

    def create_mesh(self, blend_objs: list[Object], lod_level: int) -> None:
        self.mesh.vertex_count = sum(len(obj.data.vertices) for obj in blend_objs)
        if self.mesh.vertex_count > USHORT_LIMIT:
            raise XIVMeshError(f"Mesh #{self.idx} exceeds the {USHORT_LIMIT} vertices limit.")
        
        self.mesh.submesh_index       = len(self.model.submeshes)
        self.mesh.bone_table_idx      = lod_level
        self.mesh.vertex_stream_count = 2 

        vert_decl = VertexDeclaration.from_blend_mesh(blend_objs)
        self.model.vertex_declarations.append(vert_decl)

        mesh_geo: list[NDArray] = []
        mesh_tex: list[NDArray] = []
        
        vert_offset = 0
        self.shape_arrays: dict[str, list[tuple[NDArray, dict[int, NDArray]]]] = defaultdict(list)
        for submesh_idx, obj in enumerate(blend_objs):
            if self.logger:
                self.logger.last_item = f"{obj.name}"
                self.logger.log(f"Processing {obj.name}...", 4)

            if submesh_idx == 0:
                self.mesh.material_idx = self._get_material_idx(obj)
            if len(obj.data.vertices) == 0:
                continue

            self._create_submesh(obj, vert_decl, vert_offset, mesh_geo, mesh_tex)
            vert_offset += len(obj.data.vertices)
            self.mesh.submesh_count += 1
        
        if self.logger:
            self.logger.last_item = f"Mesh #{self.idx}"
            self.logger.log(f"Finalising Mesh #{self.idx}...", 3)

        if self.bone_limit < 5:
            vert_decl.update_usage_type(VertexUsage.BLEND_WEIGHTS, VertexType.UBYTE4)
            vert_decl.update_usage_type(VertexUsage.BLEND_INDICES, VertexType.UBYTE4)
        
        if self.shape_arrays:
            self._sort_shape_arrays(self.shape_arrays, mesh_geo, mesh_tex, vert_offset)
        
        if self.shape_value_count > USHORT_LIMIT:
            raise XIVMeshError(f"Model exceeds the {USHORT_LIMIT} shape values limit. Consider removing unneeded shape keys.")

        mesh_streams = create_stream_arrays(self.mesh.vertex_count, vert_decl)
        self._mesh_streams(mesh_streams, mesh_geo, mesh_tex)

        self.bbox = BoundingBox.from_array(mesh_streams[0]["position"])
        self._bone_bounding_box(
                        mesh_streams[0]["position"], 
                        mesh_streams[0]["blend_indices"], 
                        mesh_streams[0]["blend_weights"] > 0
                    )
        
        self.vert_buffers.append(mesh_streams[0])
        self.vert_buffers.append(mesh_streams[1])

    def _get_material_idx(self, submesh: Object) -> int:
        material_name = clean_material_name(submesh.material_slots[0].name)

        if material_name in self.model.materials:
            material_idx = self.model.materials.index(material_name)
        else:
            material_idx = len(self.model.materials)
            self.model.materials.append(material_name)
        
        return material_idx

    def _sort_shape_arrays(self, shape_arrays: dict[str, list[tuple[NDArray, dict[int, NDArray]]]], mesh_geo: list[NDArray], mesh_tex: list[NDArray], vert_offset: int) -> None:
        shape_verts = 0
        for name, arrays in shape_arrays.items():
            shape_value_count = sum(len(values) for values, streams in arrays)
            mesh_shape_values = np.zeros(shape_value_count, dtype=self.model.shape_values.dtype)

            arr_offset = 0
            for values, streams in arrays:
                self.mesh.vertex_count += len(streams[0])
                if self.mesh.vertex_count > USHORT_LIMIT:
                    raise XIVMeshError(f"Mesh #{self.idx} exceeds the {USHORT_LIMIT} vertices limit due to extra shape keys.")
                
                values["replace_vert_idx"] += vert_offset + shape_verts
                mesh_geo.append(streams[0])
                mesh_tex.append(streams[1])

                end_offset = arr_offset + len(values)
                mesh_shape_values[arr_offset: end_offset] = values

                shape_verts += len(streams[0])
                arr_offset   = end_offset

            self.shape_meshes[name] = mesh_shape_values
            self.shape_value_count += shape_value_count

    def _mesh_streams(self, mesh_streams: dict[int, NDArray], mesh_geo: list[NDArray], mesh_tex: list[NDArray]) -> None:
        
        def update_geo_stream(mesh_geo_stream: NDArray, submesh_geo_stream: NDArray):
            if self.bone_limit < 5:
                for field in geo_stream.dtype.names:
                    if field in ["blend_weights", "blend_indices"]:
                        mesh_geo_stream[field][:] = submesh_geo_stream[field][:, :4]
                    else:
                        mesh_geo_stream[field][:] = submesh_geo_stream[field]
            else:
                mesh_geo_stream[:] = geo_stream

        for stream, mesh_arr in mesh_streams.items():
            stride = mesh_arr.dtype.itemsize
            self.mesh.vertex_buffer_offset[stream] = self.stream_offset
            self.mesh.vertex_buffer_stride[stream] = stride
            self.stream_offset += stride * len(mesh_arr)
            
        offset = 0
        for geo_stream, tex_stream in zip(mesh_geo, mesh_tex):
            update_geo_stream(mesh_streams[0][offset: offset + len(geo_stream)], geo_stream)
            mesh_streams[1][offset: offset + len(tex_stream)] = tex_stream
            offset += len(geo_stream)

    def _bone_bounding_box(self, positions: NDArray, blend_indices: NDArray, nonzero_mask: NDArray) -> None:
        bone_bboxes = self.model.bone_bounding_boxes
        for bone_idx, bone_name in enumerate(self.model.bones):
            if bone_name not in self.lod_bones:
                continue
  
            table_idx    = self.lod_bones.index(bone_name)
            bone_indices = (blend_indices == table_idx) & nonzero_mask
            valid_verts  = np.any(bone_indices, axis=1)
            if not np.any(valid_verts):
                continue 
            
            bone_pos  = positions[valid_verts]
            bone_bbox = BoundingBox.from_array(bone_pos)
            
            if bone_bboxes[bone_idx]:
                bone_bboxes[bone_idx].merge(bone_bbox)
            else:
                bone_bboxes[bone_idx] = bone_bbox

    def _create_submesh(self, obj: Object, vert_decl: VertexDeclaration, vert_offset: int, mesh_geo: list[NDArray], mesh_tex: list[NDArray]) -> None:

        def attribute_bitmask(obj: Object) -> int:
            bitmask = 0
            for idx, attr in enumerate(self.model.attributes):
                if attr in obj.keys() and obj[attr]:
                    bitmask |= (1 << idx)
            
            return bitmask
        
        submesh = Submesh()
        indices, submesh_streams, shapes = get_submesh_streams(obj, vert_decl)
        submesh.attribute_idx_mask       = attribute_bitmask(obj)

        if obj.vertex_groups:
            bonemap = self._create_blend_arrays(obj, submesh_streams)
            submesh.bone_start_idx = len(self.model.submesh_bonemaps)
            submesh.bone_count     = len(bonemap)
        
        if shapes:
            self._create_shape_arrays(shapes, submesh_streams, indices, vert_decl)
    
        self.idx_buffer += (indices + vert_offset).tobytes()

        submesh.idx_offset   = self.idx_offset
        submesh.idx_count    = len(indices)
        self.mesh.idx_count += len(indices)
        self.idx_offset     += len(indices)

        mesh_geo.append(submesh_streams[0])
        mesh_tex.append(submesh_streams[1]) 
        self.submeshes.append(submesh)
        
    def _create_blend_arrays(self, obj: Object, streams: dict[int, NDArray], ) -> tuple[int, int]:

        def check_empty() -> list[int]:
            empty_groups    : list[int] = []
            for v_group in obj.vertex_groups:
                if not np.any(weight_matrix[:, v_group.index] > 0.0):
                    empty_groups.append(v_group.index)
                    continue
                
            return empty_groups

        def vgroup_to_bone_list(idx_with_weights: set[int]) -> dict[int, int]:
            vgroup_to_table: dict[int, int] = {}
            for vgroup in obj.vertex_groups:
                if vgroup.index not in idx_with_weights:
                    continue

                if vgroup.name not in self.model.bones:
                    self.model.bone_bounding_boxes.append(BoundingBox())
                    self.model.bones.append(vgroup.name)
                
                if vgroup.name not in self.lod_bones:
                    vgroup_to_table[vgroup.index] = len(self.lod_bones)
                    self.lod_bones.append(vgroup.name)
                else:
                    vgroup_to_table[vgroup.index] = self.lod_bones.index(vgroup.name)
            
            return vgroup_to_table

        def submesh_to_model_bone_idx() -> list[int]:
            bonemap: list[int] = []
            
            for group_idx, bone_idx in vgroup_to_table.items():
                bonemap.append(bone_idx)
                mask = (top_indices == group_idx) & nonzero
                blend_indices[:, :bone_limit][mask] = bone_idx
            
            return bonemap
        
        vert_count    = len(obj.data.vertices)
        group_count   = len(obj.vertex_groups)
        weight_matrix = get_weights(obj, vert_count, group_count)
        empty_groups  = check_empty()

        blend_weights = np.zeros((vert_count, 8), dtype=single)
        blend_indices = np.zeros((vert_count, 8), dtype=ubyte)
        
        masked_weights, sorted_weights, sorted_indices = sort_weights(weight_matrix, empty_groups)
        bone_limit  = min(8, sorted_weights.shape[1])
        top_indices = sorted_indices[:, :bone_limit]

        weight_sums, norm_weights     = normalise_weights(sorted_weights, bone_limit) 
        empty_verts                   = empty_vertices(norm_weights, top_indices)
        blend_weights[:, :bone_limit] = normalised_int_array(norm_weights)

        nonzero = blend_weights[:, :bone_limit] > 0
        idx_with_weights = set(np.unique(top_indices[nonzero]))

        vgroup_to_table = vgroup_to_bone_list(idx_with_weights)
        bonemap         = submesh_to_model_bone_idx()

        streams[0]["blend_weights"] = blend_weights
        streams[0]["blend_indices"] = blend_indices

        bone_per_vert = np.sum(masked_weights > 0.0, axis=1)
        exceeds_limit = np.sum(bone_per_vert > 8)
        normalised    = np.sum((weight_sums < 0.99) | (weight_sums > 1.01))

        if empty_verts:
            self.export_stats[obj.name].append(f"{empty_verts} empty vertices had major weight corrections.")
        if normalised:
            self.export_stats[obj.name].append(f"{normalised} vertices had weight corrections.")
        if exceeds_limit:
            self.export_stats[obj.name].append(f"Corrected {exceeds_limit} vertices that exceeded the bone limt.")

        self.bone_limit = max(self.bone_limit, np.max(np.sum(nonzero, axis=1)))

        self.model.submesh_bonemaps.extend(bonemap)

        return bonemap
    
    def _create_shape_arrays(self, shapes: dict[str, NDArray], submesh_streams: dict[int, NDArray], indices: NDArray, vert_decl: VertexDeclaration, threshold: int=1e-6) -> None:
        
        def set_shape_stream_values(shape_streams: dict[int, NDArray], submesh_streams: dict[int, NDArray]) -> None:
            for stream_idx, stream in submesh_streams.items():
                for field_name in stream.dtype.names:
                    if field_name == "position":
                        shape_streams[stream_idx][field_name] = pos[vert_mask]
                    else:
                        shape_streams[stream_idx][field_name] = stream[field_name][vert_mask]

        for shape_name, pos in shapes.items():
            abs_diff      = np.abs(pos - submesh_streams[0]["position"])
            vert_mask     = np.any(abs_diff > threshold, axis=1)
            vert_count    = np.sum(vert_mask)

            if vert_count == 0:
                continue
            
            shape_indices = np.where(vert_mask)[0]
            indices_mask  = np.isin(indices, shape_indices)
            indices_idx   = np.where(indices_mask)[0]

            if len(indices_idx) == 0:
                continue

            shape_streams = create_stream_arrays(vert_count, vert_decl)
            set_shape_stream_values(shape_streams, submesh_streams)

            if indices_idx.max() + self.mesh.idx_count > USHORT_LIMIT:
                raise XIVMeshError(f"Mesh #{self.idx} exceeds the {USHORT_LIMIT} indices limit for shape keys.")
            
            vert_map = np.full(len(submesh_streams[0]), -1, dtype=np.int32)
            vert_map[shape_indices] = np.arange(len(shape_indices))

            shape_values = np.zeros(len(indices_idx), dtype=self.model.shape_values.dtype)
            shape_values["base_indices_idx"] = indices_idx + self.mesh.idx_count
            shape_values["replace_vert_idx"] = vert_map[indices[indices_idx]]

            self.shape_arrays[shape_name].append((shape_values, shape_streams))
        