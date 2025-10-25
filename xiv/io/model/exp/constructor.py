import numpy as np

from numpy             import single, ubyte
from bpy.types         import Object
from numpy.typing      import NDArray
from collections       import defaultdict

from .shapes           import create_shape_data, submesh_to_mesh_shapes, create_face_data
from .weights          import sort_weights, normalise_weights, empty_vertices
from .streams          import create_stream_arrays, get_submesh_streams, update_mesh_streams
from .accessors        import get_weights
from ...logging        import YetAnotherLogger
from .validators       import clean_material_path, USHORT_LIMIT
from ..com.helpers     import normalised_int_array 
from ..com.exceptions  import XIVMeshError
from ....formats.model import (XIVModel, Mesh as XIVMesh, Submesh,
                               VertexDeclaration, VertexType, VertexUsage,
                               BoneTable, Lod, ShapeMesh, BoundingBox)


def get_material_idx(obj: Object, material_list: list[str]) -> int:
    material = obj["xiv_material"] if "xiv_material" in obj else obj.material_slots[0].name
    material_name = clean_material_path(material)

    if material_name in material_list:
        material_idx = material_list.index(material_name)
    else:
        material_idx = len(material_list)
        material_list.append(material_name)
    
    return material_idx

def bone_bounding_box(positions: NDArray, blend_indices: NDArray, nonzero_mask: NDArray, bone_list: list[str], lod_bones: list[str], bone_bboxes: list[BoundingBox]) -> None:
    for bone_idx, bone_name in enumerate(bone_list):
        if bone_name not in lod_bones:
            continue

        table_idx    = lod_bones.index(bone_name)
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

class CreateLOD:
    def __init__(self, model: XIVModel, lod_level: int, face_data: bool, shape_value_count: int = 0, logger: YetAnotherLogger = None):
        self.model     = model
        self.logger    = logger
        self.lod_level = lod_level
        self.face_data = face_data

        self.bbox          = BoundingBox()
        self.idx_offset    = 0
        self.stream_offset = 0
        
        self.lod_bones      : list[str]     = []
        self.vertex_buffers : list[NDArray] = []
        self.indices_buffers: list[bytes]   = []
        self.shape_meshes   : dict[str, list[tuple[int, NDArray]]] = defaultdict(list)

        self.shape_value_count = shape_value_count

        self.shape_meshes: dict[str, list[tuple[int, NDArray]]] = defaultdict(list)
        self.export_stats: dict[str, list[str]]                 = defaultdict(list)

    @classmethod
    def construct(cls, model: XIVModel, lod_level: int, active_lod: Lod, face_data: bool, sorted_meshes: list[list[Object]], shape_value_count: int = 0, logger: YetAnotherLogger = None ) -> 'CreateLOD':
        lod = cls(model, lod_level, face_data, shape_value_count, logger=logger)
        lod._construct(active_lod, sorted_meshes)
        return lod

    def _construct(self, active_lod: Lod, sorted_meshes: list[list[Object]]):

        def bone_name_to_table(bone_names: list[str]) -> None:
            bone_table = BoneTable()
            for bone in bone_names:
                if bone in self.model.bones:
                    bone_table.bone_idx.append(self.model.bones.index(bone))
                else:
                    print(f"LOD{self.lod_level}: Couldn't find {bone}, bone table might not be accurate.")
            
            bone_table.bone_count = len(bone_table.bone_idx)
            self.model.bone_tables.append(bone_table)

        for mesh_scene_idx, blend_objs in enumerate(sorted_meshes):
            mesh_idx = active_lod.mesh_idx + mesh_scene_idx
            if self.logger:
                self.logger.last_item = f"Mesh #{mesh_idx}"
                self.logger.log(f"Processing Mesh #{mesh_idx}...", 3)
                
            self._create_mesh(mesh_idx, blend_objs)
   
            active_lod.mesh_count            += 1
            # Vanilla models increment these even when not used.
            active_lod.water_mesh_idx        += 1
            active_lod.shadow_mesh_idx       += 1
            active_lod.vertical_fog_mesh_idx += 1
        
        if self.model.mdl_bounding_box:
            self.model.mdl_bounding_box.merge(self.bbox)
        else:
            self.model.mdl_bounding_box = self.bbox

        bone_name_to_table(self.lod_bones)
        
        self.model.buffers += self._lod_buffer(active_lod, self.lod_level)

        if self.shape_meshes:
            self._create_shape_meshes(self.lod_level)

    def _lod_buffer(self, active_lod: Lod, lod_level: int) -> bytes:

        def update_submesh_offsets(mesh: XIVMesh, padding: int) -> None:
            start = mesh.submesh_index
            count = mesh.submesh_count

            for submesh in self.model.submeshes[start: start + count]:
                submesh.idx_offset += padding

        if self.logger:
            self.logger.last_item = f"LOD{lod_level} buffers"

        header = self.model.header
        current_offset = len(self.model.buffers)
        lod_buffer     = b''
        
        vert_buffer_size = 0
        for buffer in self.vertex_buffers:
            byte_buffer = buffer.tobytes()
            lod_buffer += byte_buffer
            vert_buffer_size += len(byte_buffer)

        idx_offset = current_offset + vert_buffer_size
        header.vert_buffer_size[lod_level] = vert_buffer_size
        header.vert_offset[lod_level]      = current_offset
        header.idx_offset[lod_level]       = idx_offset

        active_lod.vertex_buffer_size        = vert_buffer_size
        active_lod.idx_data_offset           = idx_offset
        active_lod.edge_geometry_data_offset = idx_offset

        idx_buffer_size = 0
        added_padding   = 0
        mesh_start      = active_lod.mesh_idx
        for mesh_idx, mesh_buffer in enumerate(self.indices_buffers):
            mesh = self.model.meshes[mesh_start + mesh_idx]
            mesh.start_idx = idx_buffer_size // 2

            if added_padding:
                update_submesh_offsets(mesh, added_padding // 2)

            lod_buffer += mesh_buffer

            current_size   = len(lod_buffer)
            padding        = (16 - (current_size % 16)) % 16 
            lod_buffer    += bytes(padding)
            added_padding += padding

            idx_buffer_size += len(mesh_buffer) + padding

        active_lod.idx_buffer_size        = idx_buffer_size
        header.idx_buffer_size[lod_level] = idx_buffer_size

        return lod_buffer

    def _create_shape_meshes(self, lod_level: int) -> None:
        if self.logger:
            self.logger.last_item = f"LOD{lod_level} shape meshes"

        arr_offset = len(self.model.shape_values)
        if arr_offset < self.shape_value_count:
            self.model.shape_values = np.resize(self.model.shape_values, self.shape_value_count)

        current_count = arr_offset
        for shape_name, arrays in self.shape_meshes.items():
            shape = self.model.get_shape(shape_name, create_missing=True)
            shape.mesh_start_idx[lod_level] = len(self.model.shape_meshes)
            
            shape_mesh_count = 0
            for mesh_idx, shape_values in arrays:
                shape_mesh = ShapeMesh()
                shape_mesh.mesh_idx_offset    = self.model.meshes[mesh_idx].start_idx
                shape_mesh.shape_value_offset = current_count
                shape_mesh.shape_value_count  = len(shape_values)

                end_offset = current_count + len(shape_values)
                self.model.shape_values[current_count: end_offset] = shape_values
                self.model.shape_meshes.append(shape_mesh)

                current_count     = end_offset
                shape_mesh_count += 1
                
            shape.mesh_count[lod_level] = shape_mesh_count

    def _create_mesh(self, mesh_idx: int, blend_objs: list[Object]) -> None:
        self.mesh         = XIVMesh()
        self.mesh_idx     = mesh_idx
        self.bone_limit   = 4
        self.mesh_indices = b''

        self.mesh.vertex_count = sum(len(obj.data.vertices) for obj in blend_objs)
        if self.mesh.vertex_count > USHORT_LIMIT:
            raise XIVMeshError(f"Mesh #{self.mesh_idx}: Exceeds the {USHORT_LIMIT} vertices limit.")
        
        self.mesh.submesh_index       = len(self.model.submeshes)
        self.mesh.bone_table_idx      = self.lod_level
        self.mesh.vertex_stream_count = 2
        try:
            self.mesh.material_idx    = get_material_idx(blend_objs[0], self.model.materials) 
        except:
            raise XIVMeshError(f"Mesh #{self.mesh_idx} is missing a material path.")

        mesh_flow = blend_objs[0]["xiv_flow"] if "xiv_flow" in blend_objs[0] else False
        vert_decl = VertexDeclaration.from_blend_mesh(blend_objs, mesh_flow)
        self.model.vertex_declarations.append(vert_decl)

        mesh_geo: list[NDArray] = []
        mesh_tex: list[NDArray] = []
        
        vert_offset = 0
        self.shape_arrays: dict[str, list[tuple[NDArray, dict[int, NDArray]]]] = defaultdict(list)
        for obj in blend_objs:
            if self.logger:
                self.logger.last_item = f"{obj.name}"
                self.logger.log(f"Processing {obj.name}...", 4)

            submesh_vert_count = len(obj.data.vertices)
            if submesh_vert_count == 0:
                continue
            try:
                self._create_submesh(obj, vert_decl, vert_offset, mesh_geo, mesh_tex, mesh_flow)
            except XIVMeshError as e:
                raise XIVMeshError(f"Mesh #{self.mesh_idx}: {e}")
            
            vert_offset             += submesh_vert_count
            self.mesh.submesh_count += 1
        
        if self.logger:
            self.logger.last_item = f"Mesh #{self.mesh_idx}"
            self.logger.log(f"Finalising Mesh #{self.mesh_idx}...", 3)

        if self.bone_limit < 5:
            vert_decl.update_usage_type(VertexUsage.BLEND_WEIGHTS, VertexType.UBYTE4)
            vert_decl.update_usage_type(VertexUsage.BLEND_INDICES, VertexType.UBYTE4)
        
        if self.shape_arrays:
            try:
                self.shape_value_count += submesh_to_mesh_shapes(
                                                            self.mesh, 
                                                            self.mesh_idx, 
                                                            self.shape_meshes, 
                                                            self.shape_arrays, 
                                                            mesh_geo, 
                                                            mesh_tex, 
                                                            vert_offset
                                                        )
            except XIVMeshError as e:
                raise XIVMeshError(f"Mesh #{self.mesh_idx}: {e}")
        
        if self.shape_value_count > USHORT_LIMIT:
            raise XIVMeshError(f"Model exceeds the {USHORT_LIMIT} shape values limit. Consider removing unneeded shape keys.")

        mesh_streams       = create_stream_arrays(self.mesh.vertex_count, vert_decl)
        self.stream_offset = update_mesh_streams(self.mesh, mesh_streams, mesh_geo, mesh_tex, self.stream_offset, self.bone_limit)

        if self.bbox:
            self.bbox.merge(BoundingBox.from_array(mesh_streams[0]["position"]))
        else:
            self.bbox = BoundingBox.from_array(mesh_streams[0]["position"])
 
        bone_bounding_box(
                mesh_streams[0]["position"], 
                mesh_streams[0]["blend_indices"], 
                mesh_streams[0]["blend_weights"] > 0,
                self.model.bones,
                self.lod_bones,
                self.model.bone_bounding_boxes
            )
        
        if self.face_data:
            create_face_data(self.model, mesh_streams[0]["position"])
    
        self.vertex_buffers.append(mesh_streams[0])
        self.vertex_buffers.append(mesh_streams[1])
        self.indices_buffers.append(self.mesh_indices)
        self.model.meshes.append(self.mesh)

    def _create_submesh(self, obj: Object, vert_decl: VertexDeclaration, vert_offset: int, mesh_geo: list[NDArray], mesh_tex: list[NDArray], mesh_flow: bool) -> None:

        def attribute_bitmask(obj: Object) -> int:
            bitmask = 0
            for idx, attr in enumerate(self.model.attributes):
                if attr in obj.keys() and obj[attr]:
                    bitmask |= (1 << idx)
            
            return bitmask
        
        submesh = Submesh()
        indices, submesh_streams, shapes = get_submesh_streams(obj, vert_decl, mesh_flow)
        submesh.attribute_idx_mask       = attribute_bitmask(obj)

        if obj.vertex_groups:
            bonemap = self._create_blend_arrays(obj, submesh_streams)
            submesh.bone_start_idx = len(self.model.submesh_bonemaps)
            submesh.bone_count     = len(bonemap)
        
        for shape_name, pos in shapes.items():
            shape_data = create_shape_data(self.mesh, pos, indices, submesh_streams, vert_decl)
            if shape_data is None:
                continue
            
            self.shape_arrays[shape_name].append(shape_data)
    
        self.mesh_indices += (indices + vert_offset).tobytes()

        submesh.idx_offset   = self.idx_offset
        submesh.idx_count    = len(indices)
        self.mesh.idx_count += len(indices)
        self.idx_offset     += len(indices)

        mesh_geo.append(submesh_streams[0])
        mesh_tex.append(submesh_streams[1]) 
        self.model.submeshes.append(submesh)
        
    def _create_blend_arrays(self, obj: Object, streams: dict[int, NDArray], ) -> tuple[int, int]:

        def check_empty() -> list[int]:
            empty_groups: list[int] = []
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
            self.export_stats[obj.name].append(f"Corrected {exceeds_limit} vertices that exceeded the bone limit.")

        self.bone_limit = max(self.bone_limit, np.max(np.sum(nonzero, axis=1)))

        self.model.submesh_bonemaps.extend(bonemap)

        return bonemap
        