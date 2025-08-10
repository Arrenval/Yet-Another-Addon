from io          import BytesIO
from enum        import Flag
from struct      import pack
from typing      import List
from dataclasses import dataclass, field

from .enums      import ModelFlags1, ModelFlags2
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
        
    def print_info(self) -> None:
        print("=" * 60)
        print("FILE HEADER INFORMATION")
        print("=" * 60)
        
        print(f"Version:                    0x{self.version:08X} ({self.version})")
        print(f"Stack Size:                 {self.stack_size:,} bytes")
        print(f"Runtime Size:               {self.runtime_size:,} bytes")
        print()
        
        print("STRUCTURE COUNTS:")
        print(f"  Vertex Declarations:      {self.vertex_declaration_count}")
        print(f"  Materials:                {self.material_count}")
        print(f"  LOD Levels:               {self.lod_count}")
        print()
        
        print("BUFFER LAYOUT:")
        for i in range(3):
            if i < self.lod_count:
                print(f"  LOD {i}:")
                print(f"    Vertex Offset:        {self.vert_offset[i]:,} bytes")
                print(f"    Index Offset:         {self.idx_offset[i]:,} bytes") 
                print(f"    Vertex Buffer Size:   {self.vert_buffer_size[i]:,} bytes")
                print(f"    Index Buffer Size:    {self.idx_buffer_size[i]:,} bytes")
            else:
                print(f"  LOD {i}:                (unused)")
        print()
        
        print("STREAMING FEATURES:")
        print(f"  Index Buffer Streaming:   {'ENABLED' if self.enable_idx_buffer_stream else 'DISABLED'}")
        print(f"  Edge Geometry:            {'ENABLED' if self.enable_edge_geometry else 'DISABLED'}")

@dataclass
class MeshHeader:
    # All ints are ushorts unless specified
    radius                      : float = 0.0            #from source model
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
    model_clip_distance         : float = 0.0            #from source model
    shadow_clip_distance        : float = 0.0            #from source model
    culling_grid_count          : int   = 0              #from source model
    terrain_shadow_submesh_count: int   = 0 
    flags3                      : int   = 0              #from source model #byte
    bg_change_material_idx      : int   = 0              #from source model #byte
    bg_crest_change_material_idx: int   = 0              #from source model #byte
    UNKOWN6                     : int   = 0              #from source model #byte
    bone_table_array_count_total: int   = 0 
    UNKOWN8                     : int   = 0              #from source model
    UNKOWN9                     : int   = 0              #from source model
    PADDING                             = 6

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

        header.flags3                       = reader.read_byte()
        header.bg_change_material_idx       = reader.read_byte()
        header.bg_crest_change_material_idx = reader.read_byte()
        header.UNKOWN6                      = reader.read_byte()

        header.bone_table_array_count_total = reader.read_uint16()
        header.UNKOWN8                      = reader.read_uint16()
        header.UNKOWN9                      = reader.read_uint16()

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

        file.write(pack('<B', self.flags3))
        file.write(pack('<B', self.bg_change_material_idx))
        file.write(pack('<B', self.bg_crest_change_material_idx))
        file.write(pack('<B', self.UNKOWN6))

        file.write(pack('<H', self.bone_table_array_count_total))
        file.write(pack('<H', self.UNKOWN8))
        file.write(pack('<H', self.UNKOWN9))

        file.write(write_padding(self.PADDING))

    def print_info(self) -> None:
        print("=" * 60)
        print("MESH HEADER INFORMATION")
        print("=" * 60)
        
        print("MODEL PROPERTIES:")
        print(f"  Radius:                   {self.radius:.6f}")
        print(f"  Model Clip Distance:      {self.model_clip_distance:.6f}")
        print(f"  Shadow Clip Distance:     {self.shadow_clip_distance:.6f}")
        print(f"  Culling Grid Count:       {self.culling_grid_count}")
        print()
        
        print("GEOMETRY STRUCTURE:")
        print(f"  Meshes:                   {self.mesh_count}")
        print(f"  Submeshes:                {self.submesh_count}")
        print(f"  LOD Count:                {self.lod_count}")
        print(f"  Materials:                {self.material_count}")
        print(f"  Attributes:               {self.attribute_count}")
        print(f"  Shapes:                   {self.shape_count}")
        print(f"  Shape Meshes:             {self.shape_mesh_count}")
        print(f"  Shape Values:             {self.shape_value_count}")
        print()
        
        print("BONE DATA:")
        print(f"  Bones:                    {self.bone_count}")
        print(f"  Bone Tables:              {self.bone_table_count}")
        print(f"  Bone Table Array Total:   {self.bone_table_array_count_total}")
        print()
        
        print("RENDERING FEATURES:")
        print(f"  Element IDs:              {self.element_id_count}")
        print(f"  Terrain Shadow Meshes:    {self.terrain_shadow_mesh_count}")
        print(f"  Terrain Shadow Submeshes: {self.terrain_shadow_submesh_count}")
        print(f"  BG Change Material:       {self.bg_change_material_idx}")
        print(f"  BG Crest Change Material: {self.bg_crest_change_material_idx}")
        print()
        
        print("ACTIVE FLAGS:")
        self._print_flags("  Flags1", self.flags1)
        self._print_flags("  Flags2", self.flags2)
        print()
        
        print("RAW DATA:")
        print(f"  Flags3:                   {self.flags3}")
        print(f"  Unknown6:                 {self.UNKOWN6}")
        print(f"  Unknown8:                 {self.UNKOWN8}")
        print(f"  Unknown9:                 {self.UNKOWN9}")

    def _print_flags(self, label: str, flags: Flag) -> None:
        all_flags = list(flags.__class__)
    
        print(f"{label}:")
        for flag in all_flags:
            is_active = flag in flags
            status = "O" if is_active else "X"
            print(f"    {status} {flag.name}")
