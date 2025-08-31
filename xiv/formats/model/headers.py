from io          import BytesIO
from struct      import pack
from typing      import List
from dataclasses import dataclass, field

from .enums      import ModelFlags1, ModelFlags2, ModelFlags3
from ..utils     import BinaryReader, write_padding


@dataclass
class FileHeader:
    version                 : int       = 0
    stack_size              : int       = 0
    runtime_size            : int       = 0
    vertex_declaration_count: int       = 0 #ushort
    material_count          : int       = 0 #ushort
    vert_offset             : List[int] = field(default_factory=lambda: [0, 0, 0])
    idx_offset              : List[int] = field(default_factory=lambda: [0, 0, 0])
    vert_buffer_size        : List[int] = field(default_factory=lambda: [0, 0, 0])
    idx_buffer_size         : List[int] = field(default_factory=lambda: [0, 0, 0])
    lod_count               : int       = 0 #byte
    enable_idx_buffer_stream: bool      = False
    enable_edge_geometry    : bool      = False
    PADDING                             = 1

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'FileHeader':
        header = cls()

        header.version                  = reader.read_uint32()
        header.stack_size               = reader.read_uint32()
        header.runtime_size             = reader.read_uint32()

        header.vertex_declaration_count = reader.read_uint16()
        header.material_count           = reader.read_uint16()

        header.vert_offset              = reader.read_array(3)
        header.idx_offset               = reader.read_array(3)
        header.vert_buffer_size         = reader.read_array(3)
        header.idx_buffer_size          = reader.read_array(3)

        header.lod_count                = reader.read_byte()

        header.enable_idx_buffer_stream = reader.read_bool()
        header.enable_edge_geometry     = reader.read_bool()

        reader.pos += header.PADDING

        return header

    def write(self, file: BytesIO) -> None:
        file.write(pack('<I', self.version))
        file.write(pack('<I', self.stack_size))
        file.write(pack('<I', self.runtime_size))

        file.write(pack('<H', self.vertex_declaration_count))
        file.write(pack('<H', self.material_count))

        for offset in self.vert_offset[:3]:
            file.write(pack('<I', offset))
        for offset in self.idx_offset[:3]:
            file.write(pack('<I', offset))
        for buffer in self.vert_buffer_size[:3]:
            file.write(pack('<I', buffer))
        for buffer in self.idx_buffer_size[:3]:
            file.write(pack('<I', buffer))

        file.write(pack('<B', self.lod_count))

        file.write(pack('<?', self.enable_idx_buffer_stream))
        file.write(pack('<?', self.enable_edge_geometry))

        file.write(write_padding(self.PADDING))


@dataclass
class MeshHeader:
    # All ints are ushorts unless specified
    radius                      : float = 1.0            
    mesh_count                  : int   = 0
    attribute_count             : int   = 0
    submesh_count               : int   = 0
    material_count              : int   = 0
    bone_count                  : int   = 0
    bone_table_count            : int   = 0
    shape_count                 : int   = 0
    shape_mesh_count            : int   = 0
    shape_value_count           : int   = 0
    lod_count                   : int   = 0              #byte
    flags1                              = ModelFlags1(0)
    element_id_count            : int   = 0
    terrain_shadow_mesh_count   : int   = 0              #byte
    flags2                              = ModelFlags2(0)
    model_clip_distance         : float = 0.0           
    shadow_clip_distance        : float = 0.0           
    culling_grid_count          : int   = 0             
    terrain_shadow_submesh_count: int   = 0 
    flags3                              = ModelFlags3(0)
    bg_change_material_idx      : int   = 0              #byte
    bg_crest_change_material_idx: int   = 0              #byte
    neck_morph_count            : int   = 0              #byte
    bone_table_array_count_total: int   = 0 
    UNKOWN8                     : int   = 0             
    shadow_data_count           : int   = 0             
    PADDING                             = 4

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'MeshHeader':
        header = cls()

        header.radius            = reader.read_float()
        header.mesh_count        = reader.read_uint16()
        header.attribute_count   = reader.read_uint16()
        header.submesh_count     = reader.read_uint16()
        header.material_count    = reader.read_uint16()
        header.bone_count        = reader.read_uint16()
        header.bone_table_count  = reader.read_uint16()
        header.shape_count       = reader.read_uint16()
        header.shape_mesh_count  = reader.read_uint16()
        header.shape_value_count = reader.read_uint16()

        header.lod_count                 = reader.read_byte()
        header.flags1                    = ModelFlags1(reader.read_byte())
        header.element_id_count          = reader.read_uint16()
        header.terrain_shadow_mesh_count = reader.read_byte()
        header.flags2                    = ModelFlags2(reader.read_byte())

        header.model_clip_distance       = reader.read_float()
        header.shadow_clip_distance      = reader.read_float()

        header.culling_grid_count           = reader.read_uint16()
        header.terrain_shadow_submesh_count = reader.read_uint16()

        header.flags3                       = ModelFlags3(reader.read_byte())
        header.bg_change_material_idx       = reader.read_byte()
        header.bg_crest_change_material_idx = reader.read_byte()
        header.neck_morph_count             = reader.read_byte()

        header.bone_table_array_count_total = reader.read_uint16()
        header.UNKOWN8                      = reader.read_uint16()
        header.shadow_data_count              = reader.read_uint32()

        reader.pos += header.PADDING

        return header
    
    def write(self, file: BytesIO) -> None:
        file.write(pack('<f', self.radius))

        file.write(pack('<H', self.mesh_count))
        file.write(pack('<H', self.attribute_count))
        file.write(pack('<H', self.submesh_count))
        file.write(pack('<H', self.material_count))
        file.write(pack('<H', self.bone_count))
        file.write(pack('<H', self.bone_table_count))
        file.write(pack('<H', self.shape_count))
        file.write(pack('<H', self.shape_mesh_count))
        file.write(pack('<H', self.shape_value_count))

        file.write(pack('<B', self.lod_count))
        file.write(pack('<B', self.flags1.value))
        file.write(pack('<H', self.element_id_count))
        file.write(pack('<B', self.terrain_shadow_mesh_count))
        file.write(pack('<B', self.flags2.value))

        file.write(pack('<f', self.model_clip_distance))
        file.write(pack('<f', self.shadow_clip_distance))

        file.write(pack('<H', self.culling_grid_count))
        file.write(pack('<H', self.terrain_shadow_submesh_count))

        file.write(pack('<B', self.flags3.value))
        file.write(pack('<B', self.bg_change_material_idx))
        file.write(pack('<B', self.bg_crest_change_material_idx))
        file.write(pack('<B', self.neck_morph_count))

        file.write(pack('<H', self.bone_table_array_count_total))
        file.write(pack('<H', self.UNKOWN8))
        file.write(pack('<I', self.shadow_data_count))

        file.write(write_padding(self.PADDING))
