from typing      import List
from dataclasses import dataclass, field

from .chain      import PhybChain
from ..utils     import BinaryReader


class DataSizes:
    COLLISION      = 36
    CONNECTOR      = 32
    ATTRACT        = 52
    PIN            = 48
    SPRING         = 16
    POST_ALIGNMENT = 36

def read_item(item_size: int, reader: BinaryReader) -> bytes:
        return reader.read_bytes(item_size)

@dataclass
class PhybSimulator:

    HEADER_SIZE = 72
    SIM_OFFSET  = 0xCCCCCCCC

    params              : bytes           = b''
    collisions          : List[bytes]     = field(default_factory=list)
    collision_connectors: List[bytes]     = field(default_factory=list)  
    chains              : List[PhybChain] = field(default_factory=list)  
    connectors          : List[bytes]     = field(default_factory=list)
    attracts            : List[bytes]     = field(default_factory=list)
    pins                : List[bytes]     = field(default_factory=list)
    springs             : List[bytes]     = field(default_factory=list)
    post_alignments     : List[bytes]     = field(default_factory=list)
    
    def get_collision_names(self) -> set[str]:
        names = set()
        for collision in self.collisions:
            name = BinaryReader(collision).read_string(32)
            names.add(name)
        
        return names
    
    @classmethod
    def from_bytes(cls, sim_reader: BinaryReader) -> 'PhybSimulator':
        simulator = cls()

        counts: list[int] = []
        for _ in range(8):
            counts.append(sim_reader.read_byte())
        
        simulator.params = sim_reader.read_bytes(32)
        
        slices: list[BinaryReader] = []
        for _ in range(8):
            offset = sim_reader.read_uint32()

            if offset == simulator.SIM_OFFSET:
                offset = 4
            else:
                offset += 4
            
            slices.append(sim_reader.slice_from(offset, len(sim_reader.data) - offset))

        size = DataSizes
        for collision in range(counts[0]):
            simulator.collisions.append(slices[0].read_bytes(size.COLLISION))

        for collision_connector in range(counts[1]):
            simulator.collision_connectors.append(slices[1].read_bytes(size.COLLISION))

        for chain in range(counts[2]):
            simulator.chains.append(PhybChain.from_bytes(slices[2], sim_reader.data))

        for connector in range(counts[3]):
            simulator.connectors.append(slices[3].read_bytes(size.CONNECTOR))

        for attract in range(counts[4]):
            simulator.attracts.append(slices[4].read_bytes(size.ATTRACT))

        for pin in range(counts[5]):
            simulator.pins.append(slices[5].read_bytes(size.PIN))

        for spring in range(counts[6]):
            simulator.springs.append(slices[6].read_bytes(size.SPRING))

        for post_alignment in range(counts[7]):
            simulator.post_alignments.append(slices[7].read_bytes(size.POST_ALIGNMENT))
        
        return simulator

    