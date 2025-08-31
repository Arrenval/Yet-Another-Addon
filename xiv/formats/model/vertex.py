import numpy as np

from io          import BytesIO
from numpy       import short, ushort, half, single, ubyte
from struct      import pack
from dataclasses import dataclass

from .enums      import VertexType, VertexUsage
from ..utils     import BinaryReader, write_padding


def get_vert_struct(vertex_type: VertexType, vertex_usage: VertexUsage) -> tuple[np.dtype, int]:
    weights = vertex_usage in (VertexUsage.BLEND_INDICES, VertexUsage.BLEND_WEIGHTS)
    
    # This will default to the endianness of your system, in Blender this should always default to little-endian
    type_mapping = {
        VertexType.SINGLE1: (single), 
        VertexType.SINGLE2: (single, 2), 
        VertexType.SINGLE3: (single, 3), 
        VertexType.SINGLE4: (single, 4), 
        
        VertexType.UBYTE4:  (ubyte, 4),  
        VertexType.SHORT2:  (short, 2),  
        VertexType.SHORT4:  (short, 4),  
        
        VertexType.NBYTE4:  (ubyte, 4),   
        VertexType.NSHORT2: (short, 2),  
        VertexType.NSHORT4: (short, 4),  
        
        VertexType.HALF2:   (half, 2),   
        VertexType.HALF4:   (half, 4),   
        
        VertexType.USHORT2: (ushort, 2), 
        VertexType.USHORT4: (ubyte, 8) if weights else (ushort, 4), 
    }
    
    return type_mapping.get(vertex_type)

@dataclass
class VertexElement:
    stream   : int         = 0
    offset   : int         = 0
    type     : VertexType  = VertexType(0)
    usage    : VertexUsage = VertexUsage(0)

    # The third uv and second colour channel have a usage_idx of 1
    usage_idx: int         = 0
    PADDING  : int         = 3

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'VertexElement':
        vertex = cls()

        vertex.stream    = reader.read_byte()
        vertex.offset    = reader.read_byte()
        vertex.type      = VertexType(reader.read_byte())
        vertex.usage     = VertexUsage(reader.read_byte())
        vertex.usage_idx = reader.read_byte()

        reader.pos += vertex.PADDING

        return vertex
    
    def write(self, file: BytesIO) -> None:
        file.write(pack('<B', self.stream))
        file.write(pack('<B', self.offset))
        file.write(pack('<B', self.type.value))
        file.write(pack('<B', self.usage.value))
        file.write(pack('<B', self.usage_idx))

        file.write(write_padding(self.PADDING))
    
    @property
    def size(self) -> int:
        return np.dtype(get_vert_struct(self.type, self.usage)).itemsize

class VertexDeclaration:
    def __init__(self):
        self.vertex_elements: list[VertexElement] = []

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'VertexDeclaration':
        decl = cls()

        element = VertexElement.from_bytes(reader)
        while element.stream != 255:
            decl.vertex_elements.append(element)
            element = VertexElement.from_bytes(reader)

        # The file always reserves space for 17 declarations. We skip ahead equal to what we didn't have to read.
        reader.pos += 17 * 8 - (len(decl.vertex_elements) + 1) * 8

        return decl
    
    def write(self, file: BytesIO) -> None:
        for element in self.vertex_elements:
            element.write(file)
        
        VertexElement(stream=255).write(file)
        file.seek((17 - 1 - len(self.vertex_elements)) * 8, 1)

    def create_element(self, type: VertexType, usage: VertexUsage, stream: int, usage_idx: int=0) -> None:
        element = VertexElement()
        element.stream = stream
        element.offset = self.stream_size(stream)
        element.type   = type
        element.usage  = usage 

        element.usage_idx = usage_idx

        self.vertex_elements.append(element)

    def stream_size(self, stream: int) -> int:
        size = 0
        for element in self.vertex_elements:
            if element.stream == stream:
                size += element.size
        
        return size
    
    def usage_count(self, usage: VertexUsage) -> int:
        count = 0
        for element in self.vertex_elements:
            if element.usage == usage:
                if usage == VertexUsage.UV:
                    count += int(element.type.name[-1]) // 2
                else:
                    count += 1 
        
        return count
    
    def update_usage_type(self, usage: VertexUsage, new_type: VertexType) -> None:
        for element in self.vertex_elements:
            if element.usage == usage:
                element.type = new_type
        
        self.update_offsets()
    
    def update_offsets(self) -> None:
        stream_size = [0, 0, 0]
        for element in self.vertex_elements:
            stream = element.stream
            element.offset = stream_size[stream]
            stream_size[stream] += element.size

    def print_info(self) -> None:
        print("=" * 60)
        print("VERTEX DECLARATION")
        print("=" * 60)
        
        print("  #  | Stream | Offset | Type      | Usage")
        print("-----|--------|--------|-----------|------------------")
        
        for idx, element in enumerate(self.vertex_elements):
            print(f"  {idx + 1:2d} |   {element.stream:3d}  |   {element.offset:3d}  | {element.type.name:9s} | {element.usage.name} ({element.usage_idx})")
    
