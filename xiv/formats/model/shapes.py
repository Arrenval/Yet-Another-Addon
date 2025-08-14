from io          import BytesIO
from struct      import pack
from typing      import List
from dataclasses import dataclass, field

from ..utils     import BinaryReader


@dataclass
class Shape:
    name          : str       = ""
    mesh_start_idx: List[int] = field(default_factory=lambda: [0, 0, 0]) #ushort
    mesh_count    : List[int] = field(default_factory=lambda: [0, 0, 0]) #ushort

    @classmethod
    def from_bytes(cls, reader: BinaryReader, strings: list[str], offsets: list[int]) -> 'Shape':
        shape = cls()

        try:
            string_idx = offsets.index(reader.read_uint32())
        except ValueError:
            string_idx = -1
        
        shape.name           = strings[string_idx] if string_idx >= 0 else ""
        shape.mesh_start_idx = reader.read_array(3, format_str='H')
        shape.mesh_count     = reader.read_array(3, format_str='H')

        return shape
    
    def write(self, file: BytesIO, offset: int) -> None:
        file.write(pack('<I', offset))

        for idx in self.mesh_start_idx[:3]:
            file.write(pack('<H', idx))
        for count in self.mesh_count[:3]:
            file.write(pack('<H', count))

@dataclass
class ShapeMesh:
    mesh_idx_offset   : int = 0
    shape_value_count : int = 0
    shape_value_offset: int = 0

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'ShapeMesh':
        shape = cls()

        shape.mesh_idx_offset    = reader.read_uint32()
        shape.shape_value_count  = reader.read_uint32()
        shape.shape_value_offset = reader.read_uint32()

        return shape

    def write(self, file: BytesIO) -> None:
        file.write(pack('<I', self.mesh_idx_offset))
        file.write(pack('<I', self.shape_value_count))
        file.write(pack('<I', self.shape_value_offset))

@dataclass
class ShapeValue:
    base_indices_idx: int = 0
    replace_vert_idx: int = 0

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'ShapeValue':
        shape = cls()

        shape.base_indices_idx  = reader.read_uint16()
        shape.replace_vert_idx  = reader.read_uint16()

        return shape

    def write(self, file: BytesIO) -> None:
        file.write(pack('<H', self.base_indices_idx))
        file.write(pack('<H', self.replace_vert_idx))
