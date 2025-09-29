from io           import BytesIO
from struct       import pack
from typing       import List
from dataclasses  import dataclass, field

from ..utils      import BinaryReader


FACE_DATA_DTYPE = [
                    ("positions", '<f4', (3,)), 
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

# Unclear what this is used for, the data is handed off to some game function that seem to generate an in memory texture. 
# It contains positional data per vertex and a sign.
# In the models I've looked at the positional data matches the base position of the model.
# Without a model with any obvious differences it's hard to know what it exactly is used for.
# It is possible that this is considered as base data before any form of lighting interactions and shape keys are ignored (?).
# Sign is always 0 (except the first one).
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
