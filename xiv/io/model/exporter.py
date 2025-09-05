import numpy as np

from bpy.types        import Object
from numpy.typing     import NDArray
from collections      import defaultdict

from .exp.mesh        import MeshHandler
from .exp.scene       import prepare_submeshes
from ...formats.model import XIVModel, Mesh as XIVMesh, BoneTable, Lod, ShapeMesh, ModelFlags1


class ModelExport:
    
    def __init__(self):
        self.model = XIVModel()
        self.shape_value_count = 0
        
        self.export_stats: dict[str, list[str]] = defaultdict(list)

    @classmethod
    def export_scene(cls, export_obj: list[Object], file_path: str) -> None:
        exporter = cls()
        exporter.create_model(export_obj, file_path)

    def create_model(self, export_obj: list[Object], file_path: str, max_lod: int=1) -> dict[str, list[str]]:
        origin = 0.0

        for lod_level, active_lod in enumerate(self.model.lods[:max_lod]):
            sorted_meshes       = prepare_submeshes(export_obj, self.model.attributes, lod_level)
            active_lod.mesh_idx = len(self.model.meshes)
            
            self._configure_lod(active_lod, lod_level, max_lod, sorted_meshes)
            self.model.set_lod_count(lod_level + 1)

        self.model.mesh_header.flags1 |= ModelFlags1.WAVING_ANIMATION_DISABLED

        self.model.bounding_box        = self.model.mdl_bounding_box.copy()
        self.model.bounding_box.min[1] = origin
        self.model.mesh_header.radius  = self.model.bounding_box.radius()

        self.model.to_file(file_path)

        return self.export_stats

    def _configure_lod(self, active_lod: Lod, lod_level:int, max_lod: int, sorted_meshes: list[list[Object]]):

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

        vertex_buffers : list[NDArray] = []
        indices_buffers: list[bytes]   = []
        shape_meshes   : dict[str, list[tuple[int, NDArray]]] = defaultdict(list)

        stream_offset      = 0
        submesh_idx_offset = 0

        lod_bones: list[str] = []
        for mesh_idx, blend_objs in enumerate(sorted_meshes):
            mesh_idx = active_lod.mesh_idx + mesh_idx
            handler = MeshHandler(
                            self.model, 
                            lod_bones, 
                            mesh_idx, 
                            submesh_idx_offset,
                            stream_offset,
                            self.shape_value_count
                        )
            
            handler.create_mesh(blend_objs, lod_level)

            self.model.meshes.append(handler.mesh)
            self.model.submeshes.extend(handler.submeshes)

            vertex_buffers.extend(handler.vert_buffers)
            indices_buffers.append(handler.idx_buffer)

            lod_bones              = handler.lod_bones
            stream_offset          = handler.stream_offset
            submesh_idx_offset     = handler.idx_offset
            self.shape_value_count = handler.shape_value_count
            
            for shape_name, array in handler.shape_meshes.items():
                shape_meshes[shape_name].append((handler.idx, array))
            
            if self.model.mdl_bounding_box:
                self.model.mdl_bounding_box.merge(handler.bbox)
            else:
                self.model.mdl_bounding_box = handler.bbox

            active_lod.mesh_count            += 1
            # Vanilla models increment these even when not used.
            active_lod.water_mesh_idx        += 1
            active_lod.shadow_mesh_idx       += 1
            active_lod.vertical_fog_mesh_idx += 1
           
        bone_name_to_table(lod_bones)
        lod_range = 0.0 if max_lod == 1 else get_lod_range(lod_level)
        active_lod.model_lod_range   = lod_range
        active_lod.texture_lod_range = lod_range

        self.model.buffers += self._lod_buffer(active_lod, lod_level, vertex_buffers, indices_buffers)

        if shape_meshes:
            self._create_shape_meshes(lod_level, shape_meshes)

    def _lod_buffer(self, active_lod: Lod, lod_level: int, vertex_buffers: list[NDArray], indices_buffers: list[NDArray]) -> bytes:

        def update_submesh_offsets(mesh: XIVMesh, padding: int) -> None:
            start = mesh.submesh_index
            count = mesh.submesh_count

            for submesh in self.model.submeshes[start: start + count]:
                submesh.idx_offset += padding

        header = self.model.header
        current_offset = len(self.model.buffers)
        lod_buffer     = b''
        
        vert_buffer_size = 0
        for buffer in vertex_buffers:
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
        for mesh_idx, mesh_buffer in enumerate(indices_buffers):
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

    def _create_shape_meshes(self, lod_level: int, shape_meshes: dict[str, list[tuple[int, NDArray]]]) -> None:
        arr_offset = len(self.model.shape_values)
        if arr_offset < self.shape_value_count:
            self.model.shape_values = np.resize(self.model.shape_values, self.shape_value_count)

        current_count = arr_offset
        for shape_name, arrays in shape_meshes.items():
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
