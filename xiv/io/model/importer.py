import bpy
import numpy as np
import random

from bpy.types        import Mesh, Material
from numpy            import ushort, byte, ubyte
from numpy.typing     import NDArray
from collections      import defaultdict

from .imp.accessors   import *
from .imp.streams     import get_submesh_streams, create_stream_arrays
from .imp.weights     import create_weight_matrix, set_weights
from .com.exceptions  import XIVMeshError
from ...formats.model import XIVModel, Submesh, VertexDeclaration, VertexUsage

    
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
    
    if name in bpy.data.materials.keys():
        return bpy.data.materials[name]
    else:
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

def get_shapes(model: XIVModel, lod: int) -> dict[int, list[tuple[str, NDArray]]]:
    shapes      = defaultdict(list)
    shape_dtype = [("base_indices_idx", np.uint32), ("replace_vert_idx", np.uint32)]
    for shape in model.shapes:
        start_idx = shape.mesh_start_idx[lod]
        for mesh in model.shape_meshes[start_idx: start_idx + shape.mesh_count[lod]]:
            offset = mesh.shape_value_offset
            count  = mesh.shape_value_count
            if not count:
                continue

            ushort_values = model.shape_values[offset: offset + count]
            mesh_values   = np.zeros(ushort_values.shape, dtype=shape_dtype)
            
            mesh_values["base_indices_idx"] = ushort_values["base_indices_idx"]
            mesh_values["replace_vert_idx"] = ushort_values["replace_vert_idx"]
            
            mesh_values["base_indices_idx"] += mesh.mesh_idx_offset
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
        mdl_buffer    = model.buffers
        lod_level     = 0
        mesh_count    = model.lods[lod_level].mesh_count

        indices = np.frombuffer(
                            mdl_buffer,
                            np.dtype(byte),
                            self.model.header.idx_buffer_size[lod_level],
                            self.model.header.idx_offset[lod_level]
                        ).view(ushort)
        lod_buffer = mdl_buffer[self.model.header.vert_offset[lod_level]:]

        if indices.shape[0] == 0:
            print(f"Model has no vertex indices.")
            return

        bpy.context.selected_objects.clear()
        self.shapes = get_shapes(self.model, lod_level)
        for mesh_idx, mesh in enumerate(self.model.meshes[:mesh_count]):
            self.mesh_idx, self.mesh = mesh_idx, mesh
            
            self._read_xiv_mesh(lod_buffer, indices)
            
    def _read_xiv_mesh(self, lod_buffer: bytes, indices: NDArray) -> None:
        if self.mesh.vertex_count == 0:
            print(f"Mesh #{self.mesh_idx}: Mesh has no vertices.")
            return
        
        vert_decl = self.model.vertex_declarations[self.mesh_idx]
        streams   = create_stream_arrays(lod_buffer, self.mesh, vert_decl, self.mesh_idx)
        if not streams:
            return
        self._verify_attributes(streams, vert_decl)

        material    = create_material(self.model.materials[self.mesh.material_idx], self.mesh.material_idx)
        submeshes   = self.model.submeshes[self.mesh.submesh_index: self.mesh.submesh_index + self.mesh.submesh_count]
        mesh_shapes = self.shapes[self.mesh.start_idx] if self.mesh.start_idx in self.shapes else []
        for submesh_idx, submesh in enumerate(submeshes):
            if submesh.idx_count == 0:
                continue
            self.submesh_idx, self.submesh = submesh_idx, submesh
            
            try:
                self._create_blend_obj(submesh, streams, indices, mesh_shapes, material)
            except XIVMeshError as e:
                print(f"Mesh #{self.mesh_idx}.{submesh_idx}: {e}")
                continue

    def _create_blend_obj(self, submesh: Submesh, streams: dict[int, NDArray], indices: NDArray[ushort], shapes: list[tuple[str, NDArray]], material: Material):

        def create_v_groups() -> list[int]:
            for bone_idx in bone_table:
                bone_name = self.model.bones[bone_idx]
                new_obj.vertex_groups.new(name=bone_name)

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

                pos = get_shape_positions(
                                    streams, 
                                    submesh_values["replace_vert_idx"], 
                                    submesh_shape_indices)

                submesh_pos = pos[vert_start: vert_start + vert_count].flatten()
                shape_key   = new_obj.shape_key_add(name=shape_name)
                shape_key.data.foreach_set("co", submesh_pos)

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
        blend_mesh = self._create_blend_mesh(submesh_streams, submesh_indices - vert_start, vert_count)
        new_obj    = bpy.data.objects.new(
                            name=obj_name, 
                            object_data=blend_mesh
                        )
        blend_mesh.name = obj_name
        
        if self.weights:
            bone_table = self.model.bone_tables[self.mesh.bone_table_idx].bone_idx
            create_v_groups()
            weight_matrix = create_weight_matrix(
                                        new_obj, 
                                        submesh_streams[0]["blend_weights"].astype(np.float32) / 255.0, 
                                        submesh_streams[0]["blend_indices"],
                                        bone_table
                                    )
            
            set_weights(new_obj, weight_matrix)

        create_shape_keys() 
        set_attributes(submesh.attribute_idx_mask)
        new_obj.data.materials.append(material)
        bpy.context.collection.objects.link(new_obj)
        new_obj.select_set(True)

    def _create_blend_mesh(self, streams: dict[int, NDArray], submesh_indices: NDArray, vert_count: int) -> Mesh:
        uvs    : list[NDArray] = []
        colours: list[NDArray] = get_colours(streams, self.col_count)
        new_mesh = bpy.data.meshes.new("temp_name")

        positions = get_positions(streams)
        new_mesh.vertices.add(vert_count)
        new_mesh.vertices.foreach_set("co", positions.flatten())
        
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

        if self.uv0:
            uvs.extend(get_uv0(streams))
        if self.uv1:
            uvs.append(get_uv1(streams))

        for idx, uv_arr in enumerate(uvs):
            layer = new_mesh.uv_layers.new(name=f"uv{idx}")
            layer.uv.foreach_set("vector", uv_arr[submesh_indices].ravel())

        for idx, col_arr in enumerate(colours):
            col_attr = new_mesh.color_attributes.new(name=f"vc{idx}", type='FLOAT_COLOR', domain='CORNER')
            col_attr.data.foreach_set("color", col_arr[submesh_indices].ravel())

        if self.normals:
            normals = get_normals(streams)
            new_mesh.normals_split_custom_set_from_vertices(normals)
        
        if all((self.normals, self.tangents, self.flow)):
            bitangents = get_bitangents(streams)
            flow       = get_flow(streams[1]["flow"], normals, bitangents)
            flow_attr  = new_mesh.color_attributes.new(name=f"xiv_flow", type='FLOAT_COLOR', domain='CORNER')
            flow_attr.data.foreach_set("color", flow[submesh_indices].ravel())
      
        return new_mesh
    
    def _verify_attributes(self, streams: dict[int, NDArray], vert_decl: VertexDeclaration) -> None:
        arr_fields = {field for stream in streams.values() for field in stream.dtype.fields}

        if "position" in arr_fields:
            self.positions = True
        else:
            raise XIVMeshError("No Position data.")
        
        self.weights   = all(field in streams[0].dtype.names for field in ("blend_weights", "blend_indices"))
        self.normals   = "normal" in arr_fields
        self.tangents  = "tangent" in arr_fields 
        self.flow      = "flow" in arr_fields
        self.uv0       = "uv0" in arr_fields
        self.uv1       = "uv1" in arr_fields
        self.col_count = vert_decl.usage_count(VertexUsage.COLOUR)
    