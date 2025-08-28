
from io          import BytesIO
from struct      import pack
from typing      import List
from dataclasses import dataclass, field

from ..utils     import BinaryReader, write_padding


@dataclass
class Mesh:
    vertex_count        : int         = 0 #ushort    
    PADDING             : int         = 2      
    idx_count           : int         = 0     
    material_idx        : int         = 0 #ushort      
    submesh_index       : int         = 0 #ushort          
    submesh_count       : int         = 0 #ushort          
    bone_table_idx      : int         = 0 #ushort
    start_idx           : int         = 0            
    vertex_buffer_offset: List[int] = field(default_factory=lambda: [0, 0, 0])
    vertex_buffer_stride: List[int] = field(default_factory=lambda: [0, 0, 0]) #byte
    vertex_stream_count : int       = 0 #byte
    
    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'Mesh':
        mesh = cls()
        
        mesh.vertex_count = reader.read_uint16()
        reader.pos += mesh.PADDING  
        mesh.idx_count    = reader.read_uint32()
        
        mesh.material_idx     = reader.read_uint16()
        mesh.submesh_index    = reader.read_uint16()
        mesh.submesh_count    = reader.read_uint16()
        mesh.bone_table_idx   = reader.read_uint16()
        
        mesh.start_idx            = reader.read_uint32()
        mesh.vertex_buffer_offset = reader.read_array(3)  
        mesh.vertex_buffer_stride = reader.read_array(3, format_str='B')
        mesh.vertex_stream_count  = reader.read_byte()
        
        return mesh
    
    def write(self, file: BytesIO) -> None:
        file.write(pack('<H', self.vertex_count))
        file.write(write_padding(self.PADDING))
        file.write(pack('<I', self.idx_count))

        file.write(pack('<H', self.material_idx))
        file.write(pack('<H', self.submesh_index))
        file.write(pack('<H', self.submesh_count))
        file.write(pack('<H', self.bone_table_idx))

        file.write(pack('<I', self.start_idx))
        for offset in self.vertex_buffer_offset:
            file.write(pack('<I', offset))
        for stride in self.vertex_buffer_stride:
            file.write(pack('<B', stride))
        file.write(pack('<B', self.vertex_stream_count))

    def print_info(self) -> None:
        print("=" * 65)
        print("MESH")
        print("=" * 65)
        
        print("GEOMETRY:")
        print(f"  Vertices:             {self.vertex_count:,}")
        print(f"  Indices:              {self.idx_count:,}")
        print(f"  Triangles:            {self.idx_count // 3:,}") 
        print()
        
        print("RESOURCES:")
        print(f"  Material Index:       {self.material_idx}")
        print(f"  Bone Table Index:     {self.bone_table_idx}")
        print(f"  Submesh Range:        {self.submesh_index} to {self.submesh_index + self.submesh_count - 1}")
        print(f"  Submesh Count:        {self.submesh_count}")
        print()
        
        print("BUFFER:")
        print(f"  Index Start Position: {self.start_idx:,}")
        print(f"  Active Streams:       {self.vertex_stream_count}")
        print()
        
        print("VERTEX STREAM DETAILS:")
        for i in range(3):
            if i < self.vertex_stream_count:
                print(f"  Stream {i}:")
                print(f"    Buffer Offset:      {self.vertex_buffer_offset[i]:,} bytes")
                print(f"    Vertex Stride:      {self.vertex_buffer_stride[i]} bytes per vertex")

                stream_size = self.vertex_count * self.vertex_buffer_stride[i]
                print(f"    Total Stream Size:  {stream_size:,} bytes")

@dataclass
class Submesh:
    idx_offset        : int = 0
    idx_count         : int = 0
    attribute_idx_mask: int = 0 
    bone_start_idx    : int = 0 #ushort
    bone_count        : int = 0 #ushort

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'Submesh':
        mesh = cls()

        mesh.idx_offset          = reader.read_uint32()
        mesh.idx_count           = reader.read_uint32()
        mesh.attribute_idx_mask  = reader.read_uint32()

        mesh.bone_start_idx = reader.read_uint16()
        mesh.bone_count     = reader.read_uint16()

        return mesh

    def write(self, file: BytesIO) -> None:
        file.write(pack('<I', self.idx_offset))
        file.write(pack('<I', self.idx_count))
        file.write(pack('<I', self.attribute_idx_mask))

        file.write(pack('<H', self.bone_start_idx))
        file.write(pack('<H', self.bone_count))

@dataclass
class TerrainShadowMesh:
    idx_count         : int = 0
    start_idx         : int = 0
    vert_buffer_offset: int = 0 
    vert_count        : int = 0 #ushort
    sub_mesh_idx      : int = 0 #ushort
    sub_mesh_count    : int = 0 #ushort
    vert_buffer_stride: int = 0 #byte
    PADDING           : int = 1

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'TerrainShadowMesh':
        mesh = cls()

        mesh.idx_count          = reader.read_uint32()
        mesh.start_idx          = reader.read_uint32()
        mesh.vert_buffer_offset = reader.read_uint32()

        mesh.vert_count     = reader.read_uint16()
        mesh.sub_mesh_idx   = reader.read_uint16()
        mesh.sub_mesh_count = reader.read_uint16()

        mesh.vert_buffer_stride = reader.read_byte()

        reader.pos += mesh.PADDING

        return mesh
     
    def write(self, file: BytesIO) -> None:
        file.write(pack('<I', self.idx_count))
        file.write(pack('<I', self.start_idx))
        file.write(pack('<I', self.vert_buffer_offset))

        file.write(pack('<H', self.vert_count))
        file.write(pack('<H', self.sub_mesh_idx))
        file.write(pack('<H', self.sub_mesh_count))

        file.write(pack('<B', self.vert_buffer_stride))

        file.write(write_padding(self.PADDING))
                   
@dataclass
class TerrainShadowSubMesh:
    idx_offset: int = 0
    idx_count : int = 0
    UNKNOWN1  : int = 0 #ushort
    UNKNOWN2  : int = 0 #ushort

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'TerrainShadowSubMesh':
        mesh = cls()

        mesh.idx_offset = reader.read_uint32()
        mesh.idx_count  = reader.read_uint32()

        mesh.UNKNOWN1 = reader.read_uint16()
        mesh.UNKNOWN2 = reader.read_uint16()

        return mesh

    def write(self, file: BytesIO) -> None:
        file.write(pack('<I', self.idx_offset))
        file.write(pack('<I', self.idx_count))

        file.write(pack('<H', self.UNKNOWN1))
        file.write(pack('<H', self.UNKNOWN2))
