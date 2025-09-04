import re
import bpy
import bmesh
import numpy as np

from numpy               import ushort, single, ubyte
from bpy.types           import Object
from numpy.typing        import NDArray
from collections         import defaultdict
   
from .exp.norm           import normalised_int_array 
from .exp.weights        import sort_weights, normalise_weights, empty_vertices
from .exp.streams        import create_stream_arrays, get_submesh_streams
from .exp.accessors      import get_weights
from .com.scene          import get_mesh_ids     
from .com.exceptions     import XIVMeshError, XIVMeshIDError
from ...formats.model    import (XIVModel, Mesh as XIVMesh, Submesh, BoneTable, Lod, 
                              ShapeMesh, BoundingBox, VertexDeclaration, 
                              VertexUsage, VertexType, ModelFlags1)

from ....mesh.transforms import apply_transforms


def sort_submeshes(export_obj: list[Object], model_attributes: list[str], lod_level: int) -> list[list[Object]]:
 
    mesh_dict: dict[int, dict[int, Object]] = defaultdict(dict)
    for obj in export_obj:
        if len(obj.data.vertices) == 0:
            continue
        elif lod_level == 0 and obj.name[-4:-1] == "LOD":
            continue
        elif lod_level != 0 and not obj.name.endswith(f"LOD{lod_level}"):
            continue

        group, part = get_mesh_ids(obj)
        if part in mesh_dict[group]:
            raise XIVMeshIDError(f'{obj.name}: Submesh already exists as "{mesh_dict[group][part].name}".')
        
        for attr in get_attributes(obj):
            if attr in model_attributes:
                continue
            model_attributes.append(attr)

        apply_transforms(obj)
        remove_loose_verts(obj)
        split_seams(obj)
        mesh_dict[group][part] = obj

    sorted_meshes = [submesh_dict for mesh_idx, submesh_dict in sorted(mesh_dict.items(), key=lambda x: x[0])]

    final_sort: list[list[Object]] = []
    for submesh_dict in sorted_meshes:
        sorted_submeshes = [obj for submesh_idx, obj in sorted(submesh_dict.items(), key=lambda x: x[0])]
        final_sort.append(sorted_submeshes)
    
    return final_sort

def remove_loose_verts(obj: Object) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    loose_verts = [vert for vert in bm.verts if len(vert.link_faces) == 0]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context='VERTS')
    
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.to_mesh(obj.data)

    bm.free()
    obj.data.update()

def split_seams(obj: Object):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, scale=True, rotation=True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.reveal(select=False)
    bpy.ops.mesh.select_all(action='SELECT')
    
    for uv_layer in obj.data.uv_layers:
        uv_layer.active = True
        bpy.ops.uv.seams_from_islands()

    bpy.ops.mesh.select_all(action='DESELECT')

    bm = bmesh.from_edit_mesh(obj.data)

    for edge in bm.edges:
        if edge.seam or not edge.smooth:
            edge.select = True
    
    bmesh.update_edit_mesh(obj.data, destructive=False, loop_triangles=False)
    bpy.ops.mesh.edge_split()
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.data.update()

def get_attributes(obj: Object) -> list[str]:
    attributes: list[str] = []
    for attr in obj.keys():
        attr: str
        if attr.startswith("atr") and obj[attr]:
            attributes.append(attr.strip())
        if attr.startswith("heels_offset") and obj[attr]:
            attributes.append(attr.strip())   

    return attributes 

def create_vert_declaration(submeshes: list[Object]) -> VertexDeclaration:

    decl = VertexDeclaration()

    decl.create_element(VertexType.SINGLE3, VertexUsage.POSITION, 0)
    decl.create_element(VertexType.USHORT4, VertexUsage.BLEND_WEIGHTS, 0)
    decl.create_element(VertexType.USHORT4, VertexUsage.BLEND_INDICES, 0)

    decl.create_element(VertexType.SINGLE3, VertexUsage.NORMAL, 1)
    decl.create_element(VertexType.NBYTE4, VertexUsage.TANGENT, 1)

    col_count = 0
    uv_count  = 0
    for obj in submeshes:
        col_count = max(col_count, len([layer for layer in obj.data.color_attributes 
                                        if layer.name.lower().startswith("vc")]))
        
        uv_count  = max(uv_count, len([layer for layer in obj.data.uv_layers 
                                       if layer.name.lower().startswith("uv")]))

    col_count = min(col_count, 2)
    uv_count  = min(uv_count, 3)

    for i in range(col_count):
        if i > 1:
            break
        decl.create_element(VertexType.NBYTE4, VertexUsage.COLOUR, 1, i)

    for i in range(uv_count):
        if uv_count == 1:
            decl.create_element(VertexType.SINGLE2, VertexUsage.UV, 1)
        elif i == 0:
            decl.create_element(VertexType.SINGLE4, VertexUsage.UV, 1)
        elif i == 2:
            decl.create_element(VertexType.SINGLE2, VertexUsage.UV, 1, 1)
        elif i > 2:
            break

    return decl

class ModelExport:
    
    def __init__(self):
        self.export_stats: dict[str, list[str]] = defaultdict(list)
        self.mdl_shape_value_count = 0

    @classmethod
    def export_scene(cls, export_obj: list[Object], file_path: str) -> None:
        exporter = cls()
        exporter.create_model(export_obj, file_path)

    def create_model(self, export_obj: list[Object], file_path: str, max_lod: int=1) -> dict[str, list[str]]:
        self.model      = XIVModel()
        self.model.lods = [Lod() for _ in range(3)]
        origin          = 0.0
        
        for lod_level, active_lod in enumerate(self.model.lods[:max_lod]):
            sorted_meshes       = sort_submeshes(export_obj, self.model.attributes, lod_level)
            active_lod.mesh_idx = len(self.model.meshes)
            
            self.configure_lod(active_lod, lod_level, max_lod, sorted_meshes)
            self.model.set_lod_count(lod_level + 1)

        self.model.mesh_header.flags1 |= ModelFlags1.WAVING_ANIMATION_DISABLED

        self.model.bounding_box        = self.model.mdl_bounding_box.copy()
        self.model.bounding_box.min[1] = origin
        self.model.mesh_header.radius  = self.model.bounding_box.radius()

        self.model.to_file(file_path)

        return self.export_stats

    def configure_lod(self, active_lod: Lod, lod_level:int, max_lod: int, sorted_meshes: list[list[Object]]):

        def get_lod_range(lod_level: int) -> float:
            ranges = {
                0: 38.0,
                1: 126.0,
                2: 0
            }

            return ranges[lod_level]

        def bone_name_to_table(bone_names: list[str]) -> None:
            bone_table = BoneTable()
            for bone in bone_names:
                if bone in self.model.bones:
                    bone_table.bone_idx.append(self.model.bones.index(bone))
                else:
                    print(f"LOD{lod_level}: Couldn't find {bone}, bone table might not be accurate.")
            
            bone_table.bone_count = len(bone_table.bone_idx)
            self.model.bone_tables.append(bone_table)

        self.vertex_buffers : list[NDArray] = []
        self.indices_buffers: list[bytes]   = []
        self.shape_meshes   : dict[str, dict[int, NDArray]] = defaultdict(defaultdict)

        self.stream_offset      = 0
        self.submesh_idx_offset = 0

        self.lod_bone_names: list[str]   = []
        for mesh_idx, blend_objs in enumerate(sorted_meshes):
            self.mesh_idx = mesh_idx
            self.create_mesh(blend_objs, lod_level)

            active_lod.mesh_count            += 1
            active_lod.water_mesh_idx        += 1
            active_lod.shadow_mesh_idx       += 1
            active_lod.vertical_fog_mesh_idx += 1
           
        bone_name_to_table(self.lod_bone_names)
        lod_range = 0.0 if max_lod == 1 else get_lod_range(lod_level)
        active_lod.model_lod_range   = lod_range
        active_lod.texture_lod_range = lod_range

        self.model.buffers += self._lod_buffer(active_lod, lod_level)

        if self.shape_meshes:
            self._create_shape_meshes(lod_level)

    def _lod_buffer(self, active_lod: Lod, lod_level: int) -> bytes:

        def update_submesh_offsets(mesh: XIVMesh, padding: int) -> None:
            start = mesh.submesh_index
            count = mesh.submesh_count

            for submesh in self.model.submeshes[start: start + count]:
                submesh.idx_offset += padding

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
        arr_offset = len(self.model.shape_values)
        if arr_offset < self.mdl_shape_value_count:
            self.model.shape_values = np.resize(self.model.shape_values, self.mdl_shape_value_count)

        current_count = arr_offset
        for shape in self.model.shapes:
            shape_mesh_arrays               = self.shape_meshes[shape.name]
            shape.mesh_start_idx[lod_level] = len(self.model.shape_meshes)
            
            shape_mesh_count = 0
            for mesh_idx, shape_values in shape_mesh_arrays.items():
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

    def create_mesh(self, blend_objs: list[Object], lod_level:int) -> None:
        
        def sort_shape_arrays(shape_arrays: dict[str, list[tuple[NDArray, dict[int, NDArray]]]], mesh_geo: list[NDArray], mesh_tex: list[NDArray]) -> None:
            shape_verts = 0
            for name, arrays in shape_arrays.items():
                shape_value_count  = sum(len(values) for values, streams in arrays)
                mesh_shape_values  = np.zeros(shape_value_count, dtype=self.model.shape_values.dtype)
                shape_value_offset = 0
                for values, streams in arrays:
                    mesh.vertex_count += len(streams[0])
                    if mesh.vertex_count > ushort_limit:
                        raise XIVMeshError(f"Mesh #{self.mesh_idx} exceeds the {ushort_limit} vertices limit due to extra shape keys.")
                    
                    values["replace_vert_idx"] += vert_offset + shape_verts
                    
                    mesh_geo.append(streams[0])
                    mesh_tex.append(streams[1])

                    end_offset = shape_value_offset + len(values)
                    mesh_shape_values[shape_value_offset: end_offset] = values
                    shape_verts       += len(streams[0])
                    shape_value_offset = end_offset
                    
                self.shape_meshes[name][self.mesh_idx] = (mesh_shape_values)
                self.mdl_shape_value_count += shape_value_count
            
        def calc_bbox(pos: NDArray) -> None:
            mesh_bbox = BoundingBox.from_array(pos)
            if not self.model.mdl_bounding_box:
                self.model.mdl_bounding_box     = mesh_bbox
            else:
                self.model.mdl_bounding_box.merge(mesh_bbox)
        
        mesh              = XIVMesh()
        ushort_limit      = np.iinfo(ushort).max
        mesh.vertex_count = sum(len(obj.data.vertices) for obj in blend_objs)
        if mesh.vertex_count > ushort_limit:
            raise XIVMeshError(f"Mesh #{self.mesh_idx} exceeds the {ushort_limit} vertices limit.")
        
        mesh.submesh_index       = len(self.model.submeshes)
        mesh.vertex_stream_count = 2
        mesh.bone_table_idx      = lod_level 
        
        vert_decl = create_vert_declaration(blend_objs)
        self.model.vertex_declarations.append(vert_decl)
    
        vert_offset           = 0
        self.mesh_idx_count   = 0
        self.mesh_bone_limit  = 4
        self.mesh_geo: list[NDArray] = []
        self.mesh_tex: list[NDArray] = []
        self.mesh_idx_buffer         = b''
        self.shape_arrays: dict[str, list[tuple[NDArray, dict[int, NDArray]]]] = defaultdict(list)
        for submesh_idx, obj in enumerate(blend_objs):
            if submesh_idx == 0:
                mesh.material_idx = self._get_material_idx(obj)
            if len(obj.data.vertices) == 0:
                continue

            self.create_submesh(obj, vert_decl, vert_offset, ushort_limit)
            vert_offset        += len(obj.data.vertices)
            mesh.submesh_count += 1

        mesh.idx_count = self.mesh_idx_count
        self.indices_buffers.append(self.mesh_idx_buffer)
         
        if self.mesh_bone_limit < 5:
            vert_decl.update_usage_type(VertexUsage.BLEND_WEIGHTS, VertexType.UBYTE4)
            vert_decl.update_usage_type(VertexUsage.BLEND_INDICES, VertexType.UBYTE4)
        
        if self.shape_arrays:
            sort_shape_arrays(self.shape_arrays, self.mesh_geo, self.mesh_tex)

        mesh_streams = create_stream_arrays(mesh.vertex_count, vert_decl)
        self._mesh_streams(mesh, mesh_streams, self.mesh_geo, self.mesh_tex)

        calc_bbox(mesh_streams[0]["position"])
        self.vertex_buffers.append(mesh_streams[0])
        self.vertex_buffers.append(mesh_streams[1])
        self.model.meshes.append(mesh)

    def _get_material_idx(self, submesh: Object) -> int:

        def clean_material_name(name: str):
            
            name = re.sub(r'\.\d{3}$', "", name)
            if not name.endswith(".mtrl"):
                name = name + ".mtrl"
            if not name.startswith("/"):
                name = "/" + name
            return name.strip()
        
        material_name = clean_material_name(submesh.material_slots[0].name)

        if material_name in self.model.materials:
            material_idx = self.model.materials.index(material_name)
        else:
            material_idx = len(self.model.materials)
            self.model.materials.append(material_name)
        
        return material_idx

    def _mesh_streams(self, mesh: XIVMesh, mesh_streams: dict[int, NDArray], mesh_geo: list[NDArray], mesh_tex: list[NDArray]) -> None:
        
        def update_geo_stream(mesh_geo_stream: NDArray):
            if self.mesh_bone_limit < 5:
                for field in geo_stream.dtype.names:
                    if field in ["blend_weights", "blend_indices"]:
                        mesh_geo_stream[field][:] = geo_stream[field][:, :4]
                    else:
                        mesh_geo_stream[field][:] = geo_stream[field]
            else:
                mesh_geo_stream[:] = geo_stream

        for stream, mesh_arr in mesh_streams.items():
            stride = mesh_arr.dtype.itemsize
            mesh.vertex_buffer_offset[stream] = self.stream_offset
            mesh.vertex_buffer_stride[stream] = stride
            self.stream_offset += stride * len(mesh_arr)
            
        offset = 0
        for geo_stream, tex_stream in zip(mesh_geo, mesh_tex):
            update_geo_stream(mesh_streams[0][offset: offset + len(geo_stream)])
            mesh_streams[1][offset: offset + len(tex_stream)] = tex_stream
            offset += len(geo_stream)

    def create_submesh(self, obj: Object, vert_decl: VertexDeclaration, vert_offset: int, ushort_limit: int) -> None:

        def attribute_bitmask() -> int:
            bitmask = 0
            for idx, attr in enumerate(self.model.attributes):
                if attr in obj.keys() and obj[attr]:
                    bitmask |= (1 << idx)
            
            return bitmask
        
        submesh = Submesh()
        indices, submesh_streams, shapes = get_submesh_streams(obj, vert_decl)
        submesh.attribute_idx_mask       = attribute_bitmask()

        if obj.vertex_groups:
            bonemap = self._get_blend_arrays(obj, submesh_streams)
            submesh.bone_start_idx = len(self.model.submesh_bonemaps)
            submesh.bone_count     = len(bonemap)
        
        if shapes:
            self._get_shape_arrays(shapes, submesh_streams, indices, vert_decl, ushort_limit)
            
        self.mesh_idx_buffer += (indices + vert_offset).tobytes()

        submesh.idx_offset       = self.submesh_idx_offset
        submesh.idx_count        = len(indices)
        self.mesh_idx_count     += len(indices)
        self.submesh_idx_offset += len(indices)

        self.model.submeshes.append(submesh)
        self.mesh_geo.append(submesh_streams[0])
        self.mesh_tex.append(submesh_streams[1]) 
     
    def _get_blend_arrays(self, obj: Object, streams: dict[int, NDArray], ) -> tuple[int, int]:

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
                
                if vgroup.name not in self.lod_bone_names:
                    vgroup_to_table[vgroup.index] = len(self.lod_bone_names)
                    self.lod_bone_names.append(vgroup.name)
                else:
                    vgroup_to_table[vgroup.index] = self.lod_bone_names.index(vgroup.name)
            
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

        self._bone_bounding_box(
                        streams[0]["position"], 
                        blend_indices[:, :bone_limit], 
                        nonzero 
                    )

        streams[0]["blend_weights"] = blend_weights
        streams[0]["blend_indices"] = blend_indices

        bone_per_vert = np.sum(masked_weights > 0.0, axis=1)
        exceeds_limit = np.sum(bone_per_vert > 8)
        normalised    = np.sum((weight_sums < 0.99) | (weight_sums > 1.01))

        if empty_verts:
            self.export_stats[obj.name].append(f"{empty_verts} empty vertices had major corrections.")
        if normalised:
            self.export_stats[obj.name].append(f"{normalised} vertices had weight corrections.")
        if exceeds_limit:
            self.export_stats[obj.name].append(f"Corrected {exceeds_limit} vertices for exceeding bone limt.")

        self.mesh_bone_limit = max(self.mesh_bone_limit, np.max(np.sum(nonzero, axis=1)))

        self.model.submesh_bonemaps.extend(bonemap)

        return bonemap
    
    def _get_shape_arrays(self, shapes: dict[str, NDArray], submesh_streams: dict[int, NDArray], indices: NDArray, vert_decl: VertexDeclaration, ushort_limit: int, threshold: int=1e-6) -> None:
        
        def set_shape_stream_values(shape_streams: dict[int, NDArray], submesh_streams: dict[int, NDArray]) -> None:
            for stream_idx, stream in submesh_streams.items():
                for field_name in stream.dtype.names:
                    if field_name == "position":
                        shape_streams[stream_idx][field_name] = pos[vert_mask]
                    else:
                        shape_streams[stream_idx][field_name] = stream[field_name][vert_mask]

        mesh_idx_offset = self.mesh_idx_count
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
            self.model.get_shape(shape_name, create_missing=True)

            if indices_idx.max() + mesh_idx_offset > ushort_limit:
                raise XIVMeshError(f"Mesh #{self.mesh_idx} exceeds the {ushort_limit} indices limit for shape keys.")
            
            vert_map = np.full(len(submesh_streams[0]), -1, dtype=np.int32)
            vert_map[shape_indices] = np.arange(len(shape_indices))

            shape_values = np.zeros(len(indices_idx), dtype=self.model.shape_values.dtype)
            shape_values["base_indices_idx"] = indices_idx + mesh_idx_offset
            shape_values["replace_vert_idx"] = vert_map[indices[indices_idx]]

            self.shape_arrays[shape_name].append((shape_values, shape_streams))

    def _bone_bounding_box(self, positions: NDArray, blend_indices: NDArray, nonzero_mask:NDArray) -> None:
        bone_bboxes = self.model.bone_bounding_boxes
        for bone_idx, bone_name in enumerate(self.model.bones):
            if bone_name not in self.lod_bone_names:
                continue
  
            table_idx    = self.lod_bone_names.index(bone_name)
            bone_indices = (blend_indices == table_idx) & nonzero_mask
            valid_verts  = np.any(bone_indices, axis=1)
            if not np.any(valid_verts):
                continue 
            
            bone_positions = positions[valid_verts]
            bone_bbox   = BoundingBox.from_array(bone_positions)
            
            if bone_bboxes[bone_idx]:
                bone_bboxes[bone_idx].merge(bone_bbox)
            else:
                bone_bboxes[bone_idx] = bone_bbox
