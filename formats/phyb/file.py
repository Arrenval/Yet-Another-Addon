import io
import copy
import struct
import itertools

from typing     import List, Optional, BinaryIO, Callable

from ..utils    import BinaryReader
from .simulator import PhybSimulator


class CollisionData:
    CAPSULES      = 124
    ELLIPSOID     = 116
    NORMAL_PLANE  = 92
    THREE_P_PLANE = 158
    SPHERES       = 80

class PhybFile:
    MAGIC_EXTENDED_DATA_PRE  = 0x42485045 
    MAGIC_EXTENDED_DATA_POST = 0x4B434150
    
    def __init__(self):
        self.version       : int                 = 0
        self.data_type     : int                 = 0
        self.collision_data: bytes               = b''
        self.simulators    : List[PhybSimulator] = []
        self.extended_data : Optional[bytes]     = None
    
    @classmethod
    def from_file(cls, file_path: str) -> 'PhybFile':
        with open(file_path, 'rb') as phyb:
            return cls.from_bytes(phyb.read())
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'PhybFile':
        phyb   = cls()
        reader = BinaryReader(data)
    
        phyb.version     = reader.read_uint32()
        phyb.data_type   = reader.read_uint32() if phyb.version > 0 else 0
        collision_offset = reader.read_uint32()
        sim_offset       = reader.read_uint32()

        collision_size      = sim_offset - collision_offset
        phyb.collision_data = data[collision_offset:collision_offset + collision_size]

        extended_pos    = data.find(struct.pack('<I', cls.MAGIC_EXTENDED_DATA_PRE))
        extended_offset = extended_pos if extended_pos != -1 else len(data)
        phyb.extended_data = data[extended_offset:] if extended_pos != -1 else None
    
        sim_size = extended_offset - sim_offset
        if sim_size > 0:
            phyb._read_simulators(data[sim_offset:sim_offset + sim_size])
        
        return phyb
    
    def _read_simulators(self, sim_data: bytes) -> None:
        sim_reader = BinaryReader(sim_data)
        num_simulators = sim_reader.read_uint32()

        for _ in range(num_simulators):
            self.simulators.append(PhybSimulator.from_bytes(sim_reader))

    def append_simulator(self, simulator: PhybSimulator):
        self.simulators.append(simulator)
    
    def get_collision_names(self) -> set[str]:

        def get_name_list(counts: BinaryReader, structs: BinaryReader, length: int) -> list[str]:
            name_list = []
            count     = counts.read_byte()
            for _ in range(count):
                name_list.append(structs.read_string(32))
                structs.pos += length - 32
            return name_list
        
        size = CollisionData

        counts  = BinaryReader(self.collision_data)
        structs = BinaryReader(self.collision_data[8:])

        capsules      = get_name_list(counts, structs, size.CAPSULES)
        ellipsoid     = get_name_list(counts, structs, size.ELLIPSOID)
        normal_plane  = get_name_list(counts, structs, size.NORMAL_PLANE)
        three_p_plane = get_name_list(counts, structs, size.THREE_P_PLANE)
        spheres       = get_name_list(counts, structs, size.SPHERES)

        return {name for name in itertools.chain(capsules, ellipsoid, normal_plane, three_p_plane, spheres)}
    
    def to_bytes(self) -> bytes:
        file = io.BytesIO()
        
        if self.version == 0:
            file.write(struct.pack('<III', 0, 0x0C, 0x0C))
            return file.getvalue()
        
        file.write(struct.pack('<II', self.version, self.data_type))
        
        collision_offset = file.tell() + 8 
        file.write(struct.pack('<I', collision_offset))
        
        sim_offset_pos = file.tell()
        file.write(struct.pack('<I', 0))  
        
        file.write(self.collision_data)
        
        sim_offset = file.tell()
        file.write(struct.pack('<I', len(self.simulators)))
        self._write_simulators(file)
        
        if self.extended_data:
            file.write(self.extended_data)
        
        current_pos = file.tell()
        file.seek(sim_offset_pos)
        file.write(struct.pack('<I', sim_offset))
        file.seek(current_pos)
        
        return file.getvalue()
    
    def _write_simulators(self, file: BinaryIO):

        def write_list(selector: Callable[[PhybSimulator], list[bytes]], slot: int, filler=0):
            for sim_index, simulator in enumerate(self.simulators):
                item_list = selector(simulator)
                offsets[sim_index][slot] = file.tell() - sims_start if len(item_list) > 0 else filler
                for item in item_list:
                    file.write(item)

        sims_start = file.tell()
        data_pos   = sims_start + len(self.simulators) * PhybSimulator.HEADER_SIZE
        offsets    = [[0 for _ in range(8)] for _ in range(len(self.simulators))]
        
        file.seek(data_pos)

        write_list(lambda sim: sim.collisions, 0)
        write_list(lambda sim: sim.collision_connectors, 1)

        chain_pos  = file.tell()
        num_chains = 0
        for idx, simulator in enumerate(self.simulators):
            num_chains += len(simulator.chains)
            offsets[idx][2] = file.tell() - sims_start if len(simulator.chains) > 0 else 0
            for chain in simulator.chains:
                chain.write_header(file)

        write_list(lambda sim: sim.connectors, 3)
        write_list(lambda sim: sim.attracts, 4)
        write_list(lambda sim: sim.pins, 5)
        write_list(lambda sim: sim.springs, 6)
        write_list(lambda sim: sim.post_alignments, 7, PhybSimulator.SIM_OFFSET)

        chain_offsets = [[0, 0] for _ in range(num_chains)]
        all_chains    = [chain for simulator in self.simulators for chain in simulator.chains]    
        for idx, chain in enumerate(all_chains):
            chain_offsets[idx][0] = file.tell() - sims_start if len(chain.collisions) > 0 else 0

            for collision in chain.collisions:
                file.write(collision)

        for idx, chain in enumerate(all_chains):
            chain_offsets[idx][1] = file.tell() - sims_start if len(chain.nodes) > 0 else 0

            for node in chain.nodes:
                file.write(node)

        data_end_pos = file.tell()

        file.seek(sims_start)
        for idx, simulator in enumerate(self.simulators):
            file.write(struct.pack('<B', len(simulator.collisions)))
            file.write(struct.pack('<B', len(simulator.collision_connectors)))
            file.write(struct.pack('<B', len(simulator.chains)))
            file.write(struct.pack('<B', len(simulator.connectors)))
            file.write(struct.pack('<B', len(simulator.attracts)))
            file.write(struct.pack('<B', len(simulator.pins)))
            file.write(struct.pack('<B', len(simulator.springs)))
            file.write(struct.pack('<B', len(simulator.post_alignments)))
            file.write(simulator.params)

            for item in range(8):
                file.write(struct.pack('<I', offsets[idx][item]))
        
        file.seek(chain_pos)
        for collision_offset, node_offset in chain_offsets:
            file.seek(40, 1)
            file.write(struct.pack('<I', collision_offset))
            file.write(struct.pack('<I', node_offset))

        file.seek(data_end_pos)
            
    def to_file(self, file_path: str) -> None:
        with open(file_path, 'wb') as phyb:
            phyb.write(self.to_bytes())
    
    def copy(self) -> 'PhybFile':
        return copy.deepcopy(self)
