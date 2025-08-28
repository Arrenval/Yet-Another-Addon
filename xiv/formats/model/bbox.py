from io           import BytesIO
from copy         import deepcopy
from struct       import pack
from typing       import List
from dataclasses  import dataclass, field
from numpy.typing import NDArray
from mathutils    import Vector

from ..utils      import BinaryReader


@dataclass
class BoundingBox:
    min: List[float] = field(default_factory=lambda: [0.0] * 4)
    max: List[float] = field(default_factory=lambda: [0.0] * 4)

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'BoundingBox':
        box = cls()

        box.min = reader.read_array(4, 'f')
        box.max = reader.read_array(4, 'f')

        return box
    
    @classmethod
    def from_array(cls, positions: NDArray) -> 'BoundingBox':
        box = cls()

        for col in range(3):
            box.min[col] = positions[:, col].min()
            box.max[col] = positions[:, col].max()
        
        box.min[3] = 1
        box.max[3] = 1
        
        return box

    def merge(self, new_box: 'BoundingBox') -> 'BoundingBox':
        for idx, (current_min, current_max) in enumerate(zip(self.min[:3], self.min[:3])):
            self.min[idx] = min(new_box.min[idx], current_min)
            self.max[idx] = max(new_box.max[idx], current_max)

        self.min[3] = 1
        self.max[3] = 1
        
        return self
    
    def radius(self) -> float:
        abs_bbox: list[int] = []
        for i in range(3):
            abs_bbox.append(max(abs(self.max[i]), abs(self.min[i])))
        
        return Vector(abs_bbox).length
    
    def copy(self) -> 'BoundingBox':
        return deepcopy(self)

    def write(self, file: BytesIO) -> None:
        for pos in self.min[:4]:
            file.write(pack('<f', pos))

        for pos in self.max[:4]:
            file.write(pack('<f', pos))
    
    def __bool__(self) -> bool:
        return any(pos != 0.0 for pos in self.min + self.max)
        