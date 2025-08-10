from io          import BytesIO
from struct      import pack
from dataclasses import dataclass

from .enums      import VertexType, VertexUsage
from ..utils     import BinaryReader, write_padding


@dataclass
class VertexElement:
    stream   : int = 0
    offset   : int = 0
    type           = VertexType(0)
    usage          = VertexUsage(0)
    usage_idx: int = 0
    PADDING  : int = 3

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
    
    def print_info(self) -> None:
        print("=" * 60)
        print("VERTEX DECLARATION")
        print("=" * 60)
        
        print("  #  | Stream | Offset | Type      | Usage")
        print("-----|--------|--------|-----------|------------------")
        
        for idx, element in enumerate(self.vertex_elements):
            print(f"  {idx + 1:2d} |   {element.stream:3d}  |   {element.offset:3d}  | {element.type.name:9s} | {element.usage.name} ({element.usage_idx})")
