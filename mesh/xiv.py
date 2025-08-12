import bpy
import numpy as np
import random

from bpy.types            import Object, Mesh, Material
from numpy                import short, ushort, half, single, byte, ubyte, uint8
from numpy.typing         import NDArray
from collections          import defaultdict
     
from .weights             import add_to_vgroup
from ..formats.model      import XIVModel, Mesh as XIVMesh, Submesh, VertexDeclaration, VertexUsage, VertexType
from ..utils.ya_exception import XIVMeshError


def bone_map_correction(model: XIVModel, buffer: bytes, indices: NDArray, mesh_count: int) -> None:
    submesh_bonemaps = []
    for mesh_idx, mesh in enumerate(model.meshes[:mesh_count]):
        if mesh.vertex_count == 0:
            continue

        streams = create_stream_arrays(buffer, mesh, model.vertex_declarations[mesh_idx], mesh_idx)
        if not streams:
            continue

        submeshes = model.submeshes[mesh.submesh_index: mesh.submesh_index + mesh.submesh_count]
        for submesh in submeshes:
            if submesh.idx_count == 0:
                continue

            submesh_indices = indices[submesh.idx_offset: submesh.idx_offset + submesh.idx_count]
            submesh_streams, vert_start, vert_count = get_submesh_streams(streams, submesh_indices)

            nonzero_mask = submesh_streams[0]["blend_weights"].nonzero()
            bone_indices = np.unique(submesh_streams[0]["blend_indices"][nonzero_mask])
            
            submesh.bone_start_idx = len(submesh_bonemaps)
            submesh.bone_count     = len(bone_indices)
            
            submesh_bonemaps.extend(bone_indices.tolist())
    
    model.submesh_bonemaps = submesh_bonemaps

def get_vertex_struct(vertex_type: VertexType, vertex_usage: VertexUsage) -> tuple[np.dtype, int]:
    # This will default to the endianness of your system, in Blender this should always default to little-endian
    weights = vertex_usage in (VertexUsage.BLEND_INDICES, VertexUsage.BLEND_WEIGHTS)

    type_mapping = {
        VertexType.SINGLE1: (single), 
        VertexType.SINGLE2: (single, 2), 
        VertexType.SINGLE3: (single, 3), 
        VertexType.SINGLE4: (single, 4), 
        
        VertexType.UBYTE4:  (ubyte, 4),  
        VertexType.SHORT2:  (short, 2),  
        VertexType.SHORT4:  (short, 4),  
        
        VertexType.NBYTE4:  (byte, 4),   
        VertexType.NSHORT2: (short, 2),  
        VertexType.NSHORT4: (short, 4),  
        
        VertexType.HALF2:   (half, 2),   
        VertexType.HALF4:   (half, 4),   
        
        VertexType.USHORT2: (ushort, 2), 
        VertexType.USHORT4: (ubyte, 8) if weights else (ushort, 4), 
    }
    
    return type_mapping.get(vertex_type)

def get_array_type(vert_decl: VertexDeclaration) -> dict[int, np.dtype]:
    streams: dict[int, list] = defaultdict(list)
    
    uv_channels  = 0
    col_channels = 0
    for element in vert_decl.vertex_elements:
        base_dtype, component_count = get_vertex_struct(element.type, element.usage)

        suffix = ""
        if element.usage == VertexUsage.COLOUR:
            suffix        = col_channels
            col_channels += 1
        if element.usage == VertexUsage.UV:
            suffix       = uv_channels
            uv_channels += 1

        name = f"{element.usage.name.lower()}{suffix}"
        if component_count == 1:
            streams[element.stream].append((name, base_dtype))
        else:
            streams[element.stream].append((name, base_dtype, (component_count,)))
    
    array_types: dict[int, np.dtype] = {}
    for stream, types in streams.items():
        array_types[stream] = np.dtype(types)
    
    return array_types

def create_stream_arrays(buffer: bytes, mesh: XIVMesh, vert_decl: VertexDeclaration, mesh_idx: int, blend_space: bool=True) -> dict[int, NDArray]:

    def xiv_to_blend_space(array: NDArray) -> NDArray:
        y_axis = array[:, 1].copy()
        z_axis = array[:, 2].copy()

        array[:, 1] = -z_axis
        array[:, 2] = y_axis

        return array
    
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

    if blend_space:
        streams[0]['position'] = xiv_to_blend_space(streams[0]['position'])
        streams[1]['normal']   = xiv_to_blend_space(streams[1]['normal'])

    return streams

def create_material(name: str, col_idx) -> Material:
    colours = { 
                0: (0.03, 0.15, 0.3, 1.0),   # indigo  
                1: (0.3, 0.03, 0.03, 1.0),   # red
                2: (0.18, 0.03, 0.3, 1.0),   # purple
                3: (0.3, 0.18, 0.03, 1.0),   # orange
                4: (0.3, 0.3, 0.03, 1.0),    # yellow
                5: (0.03, 0.3, 0.3, 1.0),    # cyan
                6: (0.03, 0.03, 0.3, 1.0),   # blue
                7: (0.9, 0.04, 0.5, 1.0),    # pink
                8: (0.18, 0.3, 0.03, 1.0),   # lime
                9: (0.03, 0.3, 0.03, 1.0),   # green
            }
    
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.node_tree.nodes.clear()

    principled = material.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    principled.location = (0, 0)
    
    output = material.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    material.node_tree.links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    principled.inputs['Base Color'].default_value = colours.get(col_idx, random.randint(0, 9))
    
    principled.inputs['Roughness'].default_value = 0.6
    principled.inputs['Metallic'].default_value = 0.0

    material.surface_render_method = 'DITHERED'
    material.use_backface_culling  = True

    return material

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

def get_shapes(model: XIVModel, indices: NDArray, lod: int) -> dict[int, list[tuple[str, NDArray]]]:
    shapes = defaultdict(list)
    for shape in model.shapes:
        start_idx = shape.mesh_start_idx[lod]
        for idx, mesh in enumerate(model.shape_meshes[start_idx: start_idx + shape.mesh_count[lod]]):
            offset = mesh.shape_value_offset
            count  = mesh.shape_value_count

            mesh_values = model.shape_values[offset: offset + count].copy()
            if len(mesh_values) == 0:
                continue
                
            shape_indices = mesh_values["base_indices_idx"]
            ### Testing code from when indices buffer calculation was off
            # valid_mask = (shape_indices + mesh.mesh_idx_offset) < len(indices)
            # if np.sum(~valid_mask) > 0:
            #     print(f"Mesh #{idx}: {shape.name} has {np.sum(~valid_mask)} out of bounds values.")
            #     mesh_values = mesh_values[valid_mask]
            #     shape_indices = shape_indices[valid_mask]
            
            mesh_values["base_indices_idx"] = shape_indices + mesh.mesh_idx_offset
            shapes[mesh.mesh_idx_offset].append((shape.name, mesh_values))
    
    return shapes

class ModelImport:

    @classmethod
    def from_file(cls, file_path: str, import_name: str) -> None:
        importer = cls()
        importer.import_mdl(XIVModel.from_file(file_path), import_name)

    @classmethod
    def from_bytes(cls, data: bytes, import_name: str) -> None:
        importer = cls()
        importer.import_mdl(XIVModel.from_bytes(data), import_name)

    def import_mdl(self, model: XIVModel, import_name: str) -> None:
        self.model    = model
        self.obj_name = import_name
        mdl_buffer    = model.remaining_data
        lod_level     = 0
        mesh_count    = model.lods[lod_level].mesh_count

        indices = np.frombuffer(
                        mdl_buffer,
                        np.dtype(byte),
                        self.model.header.idx_buffer_size[lod_level],
                        self.model.header.idx_offset[lod_level]
                    ).view(ushort)

        if indices.shape[0] == 0:
            print(f"Model has no vertex indices.")
            return

        if len(self.model.submesh_bonemaps) < sum(submesh.bone_count for submesh in self.model.submeshes):
            print("Correcting Bone Maps...")
            bone_map_correction(self.model, mdl_buffer, indices, mesh_count)

        bpy.context.selected_objects.clear()
        shapes = get_shapes(self.model, indices, lod_level)
        for mesh_idx, mesh in enumerate(model.meshes[:mesh_count]):
            self.mesh_idx, self.mesh = mesh_idx, mesh
            if mesh.vertex_count == 0:
                print(f"Mesh #{mesh_idx}: Mesh has no vertices.")
                continue

            streams = create_stream_arrays(mdl_buffer, mesh, model.vertex_declarations[mesh_idx], mesh_idx)
            if not streams:
                continue
            
            material = create_material(self.model.materials[mesh.material_idx], mesh.material_idx)
            submeshes = model.submeshes[mesh.submesh_index: mesh.submesh_index + mesh.submesh_count]
            for submesh_idx, submesh in enumerate(submeshes):
                if submesh.idx_count == 0:
                    continue
                self.submesh_idx, self.submesh = submesh_idx, submesh
                
                mesh_shapes = shapes[mesh.start_idx] if mesh.start_idx in shapes else []
                try:
                    self.create_blend_obj(submesh, streams, indices, mesh_shapes, material)
                except XIVMeshError as e:
                    print(f"Mesh #{mesh_idx}.{submesh_idx}: {e}.")
                    continue
    
    def create_blend_obj(self, submesh: Submesh, streams: dict[int, NDArray], indices: NDArray[ushort], shapes: list[tuple[str, NDArray]], material: Material):

        def create_shape_keys() -> None:
            for shape_name, shape_values in shapes:
                shape_indices = indices[shape_values["base_indices_idx"]]
                submesh_mask  = np.isin(shape_indices, submesh_indices)
                
                submesh_values        = shape_values[submesh_mask]
                submesh_shape_indices = shape_indices[submesh_mask]
                
                if len(submesh_values) == 0:
                    continue

                if not new_obj.data.shape_keys:
                    new_obj.shape_key_add(name="Basis")
                
                positions = streams[0]["position"].copy()
                
                new_pos = positions[submesh_values["replace_vert_idx"]]
                positions[submesh_shape_indices] = new_pos
                
                submesh_positions = positions[vert_start: vert_start + vert_count].flatten()
                shape_key = new_obj.shape_key_add(name=shape_name)
                shape_key.data.foreach_set("co", submesh_positions)

        def set_attributes(attribute_mask: int) -> None:
            while attribute_mask:
                bit = attribute_mask & -attribute_mask
                
                position = bit.bit_length() - 1
                if position < len(self.model.attributes):
                    attr_name = self.model.attributes[position]
                    new_obj[attr_name] = True
            
                attribute_mask ^= bit
        
        submesh_indices = indices[submesh.idx_offset: submesh.idx_offset + submesh.idx_count]
        submesh_streams, vert_start, vert_count = get_submesh_streams(streams, submesh_indices)

        obj_name   = f"{self.mesh_idx}.{self.submesh_idx} {self.obj_name}"
        blend_mesh = self.create_blend_mesh(submesh_streams, submesh_indices - vert_start)
        new_obj    = bpy.data.objects.new(
                            name=obj_name, 
                            object_data=blend_mesh
                        )
        blend_mesh.name = obj_name
        
        if all(field in submesh_streams[0].dtype.names for field in ("blend_weights", "blend_indices")):
            self.resolve_weights(
                        new_obj, 
                        submesh_streams[0]["blend_weights"].astype(np.float32) / 255.0, 
                        submesh_streams[0]["blend_indices"]
                    )

        create_shape_keys() 
        set_attributes(submesh.attribute_idx_mask)
        new_obj.data.materials.append(material)
        bpy.context.collection.objects.link(new_obj)
        new_obj.select_set(True)

    def create_blend_mesh(self, streams, submesh_indices: NDArray) -> Mesh:
        co_arr, no_arr, uv_arrays, col_arrays = self.sort_arrays(streams)
        new_mesh = bpy.data.meshes.new("temp_name")

        new_mesh.vertices.add(len(co_arr) // 3)
        new_mesh.vertices.foreach_set("co", co_arr)
        
        loop_count = submesh_indices.shape[0]
        new_mesh.loops.add(loop_count)
        new_mesh.loops.foreach_set("vertex_index", submesh_indices)

        triangle_count = loop_count // 3
        loop_start     = np.arange(0, loop_count, 3, dtype=np.uint32)
        loop_total     = np.full(triangle_count, 3, dtype=np.uint32)
        new_mesh.polygons.add(triangle_count)
        new_mesh.polygons.foreach_set("loop_start", loop_start)
        new_mesh.polygons.foreach_set("loop_total", loop_total)

        new_mesh.update()
        new_mesh.validate()

        for idx, uv_arr in enumerate(uv_arrays):
            layer = new_mesh.uv_layers.new(name=f"uv{idx}")
            layer.uv.foreach_set("vector", uv_arr[submesh_indices].ravel())

        for idx, col_arr in enumerate(col_arrays):
            col_attr = new_mesh.color_attributes.new(name=f"vc{idx}", type='BYTE_COLOR', domain='CORNER')
            col_attr.data.foreach_set("color", col_arr[submesh_indices].ravel())
             
        if no_arr is not None:
            new_mesh.normals_split_custom_set_from_vertices(no_arr)
      
        return new_mesh
    
    def sort_arrays(self, streams: dict[int, NDArray]) -> tuple[NDArray, NDArray, list[NDArray], list[NDArray]]:

        def set_normal_array() -> NDArray | None:
            if "normal" not in arr_fields:
                return None
            
            normals = streams[1]["normal"]
            if normals.shape[1] < 3:
                print(f"Mesh#{self.mesh_idx}.{self.submesh_idx}: Missing normal coordinates.")
                return None
            
            return normals[:, :3]

        def set_uv_arrays() -> list[NDArray]:
            uv_arrays = []
            if "uv0" in arr_fields:
                uv0_data = streams[1]["uv0"].copy()

                uv0_data[:, 1] = 1.0 - uv0_data[:, 1]  
                uv0_data[:, 3] = 1.0 - uv0_data[:, 3]

                uv_arrays.append(uv0_data[:, 0:2])
                uv_arrays.append(uv0_data[:, 2:4])

            if "uv" in arr_fields:
                uv1_data = streams[1]["uv1"].copy()

                uv1_data = 1.0 - uv1_data

                uv_arrays.append(uv1_data)
            
            return uv_arrays

        def set_col_array() -> list[NDArray]:
            col_arrays = []
            if "colour0" in arr_fields:
                col_arrays.append(streams[1]["colour0"].view(uint8) / 255.0)

            if "colour1" in arr_fields:
                col_arrays.append(streams[1]["colour1"].view(uint8) / 255.0)

            return col_arrays
            
        arr_fields = [field for stream in streams.values() for field in stream.dtype.fields]

        co_arr     = None
        nor_arr    = None
        # ta_arr   = None 
        # fl_arr   = None
        uv_arrays  = []
        col_arrays = []

        if "position" in arr_fields:
            co_arr = streams[0]["position"].flatten()
        else:
            raise XIVMeshError("No Position data")

        nor_arr    = set_normal_array()
        uv_arrays  = set_uv_arrays()
        col_arrays = set_col_array()

        return co_arr, nor_arr, uv_arrays, col_arrays
    
    def resolve_weights(self, obj: Object, weight_array: NDArray, bone_indices: NDArray) -> None:
        bone_table = self.model.bone_tables[self.mesh.bone_table_idx].bone_idx
        bone_count = self.submesh.bone_count
        start_idx  = self.submesh.bone_start_idx

        bones: dict[int, str] = {}
        for bone_idx in self.model.submesh_bonemaps[start_idx: start_idx + bone_count]:
            bone_name = self.model.bones[bone_table[bone_idx]]
            bones[bone_idx] = bone_name
        
        bone_names = [bones[idx] for idx in sorted(bones.keys())]
        for name in bone_names:
            obj.vertex_groups.new(name=name)
        
        weight_matrix  = np.zeros((len(obj.data.vertices), len(bones)), dtype=single)
        mdl_indices    = np.array(sorted(bones.keys()), dtype=ushort)
        matrix_indices = np.searchsorted(mdl_indices, bone_indices).flatten()

        valid_indices = matrix_indices < len(mdl_indices)

        num_verts, bone_count = bone_indices.shape
        flat_indices    = np.repeat(np.arange(num_verts), bone_count)
        flat_weights    = weight_array.flatten()   
        nonzero_indices = np.flatnonzero(flat_weights)

        valid_nonzero = nonzero_indices[valid_indices[nonzero_indices]]

        weight_matrix[flat_indices[valid_nonzero], matrix_indices[valid_nonzero]] += flat_weights[valid_nonzero]
        
        empty_groups = []
        for v_group in obj.vertex_groups:
            if not np.any(weight_matrix[:, v_group.index]):
                empty_groups.append(v_group)
                continue
            add_to_vgroup(weight_matrix, v_group)
        
        for v_group in empty_groups:
            obj.vertex_groups.remove(v_group)
   