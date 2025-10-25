from io           import BytesIO
from struct       import pack
from typing       import List
from dataclasses  import dataclass, field

from ..utils      import BinaryReader


FACE_DATA_DTYPE = [
                    ("position", '<f4', (3,)), 
                    ("sign",      '<u4')
                ]

@dataclass
class NeckMorph:
    positions: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    UNKNOWN1 : int         = 0x00006699
    normals  : List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    bone_idx : List[int]   = field(default_factory=lambda: [0, 0, 0, 0])

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'NeckMorph':
        morph = cls()
        morph.positions = reader.read_array(3, 'f')
        morph.UNKNOWN1  = reader.read_uint32()
        morph.normals   = reader.read_array(3, 'f')
        morph.bone_idx  = reader.read_array(4, 'B')

        return morph
    
    def write(self, file: BytesIO) -> 'NeckMorph':
        for pos in self.positions:
            file.write(pack('<f', pos))
        
        file.write(pack('<I', self.UNKNOWN1))

        for nor in self.normals:
            file.write(pack('<f', nor))

        for idx in self.bone_idx:
            file.write(pack('<B', idx))

# First entry in the face data array always has a sign of 1.
@dataclass
class FaceData:
    pos : list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    sign: int         = 0

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'FaceData':
        data = cls()
        data.pos = reader.read_array(3, 'f')
        data.sign   = reader.read_uint32()

        return data
    
    def write(self, file: BytesIO) -> None:
        for value in self.pos:
            file.write(pack('<f', value))
        
        file.write(pack('<I', self.sign))
