import io
import struct

from typing      import List
from dataclasses import dataclass, field

from ..utils     import BinaryReader

vector = tuple[float, float, float]
    
@dataclass
class PhybChain:
    HEADER_SIZE = 48

    dampening          : float  = 0
    max_speed          : float  = 0
    friction           : float  = 0
    collision_dampening: float  = 0
    repulsion_strength : float  = 0
    last_bone_offset   : vector = (0, 0, 0)
    type               : int    = 0

    collisions: List[bytes] = field(default_factory=list)
    nodes     : List[bytes] = field(default_factory=list)

    @classmethod
    def from_bytes(cls, reader: BinaryReader, sim_data: bytes) -> 'PhybChain':
        chain  = cls()

        num_collisions = reader.read_uint16()
        num_nodes      = reader.read_uint16()

        chain.dampening = reader.read_float()
        chain.max_speed = reader.read_float()
        chain.friction  = reader.read_float()

        chain.collision_dampening = reader.read_float()
        chain.repulsion_strength  = reader.read_float()

        chain.last_bone_offset = reader.read_array(3, format_str='f')
        chain.type             = reader.read_uint32()

        collision_offset = reader.read_uint32() + 4
        node_offset      = reader.read_uint32() + 4

        collision_data = sim_data[collision_offset:]
        collision_reader = BinaryReader(collision_data)
        for _ in range(num_collisions):
            chain.collisions.append(collision_reader.read_bytes(36))

        node_data = sim_data[node_offset:]
        node_reader = BinaryReader(node_data)
        for _ in range(num_nodes):
            chain.nodes.append(node_reader.read_bytes(84))

        return chain
    
    def write_header(self, file: io.BytesIO) -> None:
        file.write(struct.pack(
            '<HH', 
            len(self.collisions), 
            len(self.nodes)
            )
        )

        file.write(struct.pack(
            '<fffff', 
            self.dampening, 
            self.max_speed, 
            self.friction, 
            self.collision_dampening,
            self.repulsion_strength
            )
        )
        
        file.write(struct.pack('<fff', *self.last_bone_offset))

        file.write(struct.pack('<I', self.type))

        file.write(struct.pack('<II', 0, 0))

    