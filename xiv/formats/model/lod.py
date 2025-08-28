from io          import BytesIO
from struct      import pack
from dataclasses import dataclass, fields

from ..utils     import BinaryReader


@dataclass
class Lod:
    mesh_idx                 : int   = 0                    
    mesh_count               : int   = 0                        
    model_lod_range          : float = 0.0           
    texture_lod_range        : float = 0.0              
    water_mesh_idx           : int   = 0            
    water_mesh_count         : int   = 0
    shadow_mesh_idx          : int   = 0             
    shadow_mesh_count        : int   = 0
    terrain_shadow_mesh_idx  : int   = 0     
    terrain_shadow_mesh_count: int   = 0
    vertical_fog_mesh_idx    : int   = 0       
    vertical_fog_mesh_count  : int   = 0
  
    edge_geometry_size       : int   = 0 #uint           
    edge_geometry_data_offset: int   = 0 #uint
    polygon_count            : int   = 0 #uint              
    neck_morph_offset        : int   = 0 #byte                 
    neck_morph_count         : int   = 0 #byte                
    unknown1                 : int   = 0                    
    vertex_buffer_size       : int   = 0 #uint        
    idx_buffer_size          : int   = 0 #uint             
    vertex_data_offset       : int   = 0 #uint            
    idx_data_offset          : int   = 0 #uint            
    
    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'Lod':
        lod = cls()
        
        lod.mesh_idx   = reader.read_uint16()
        lod.mesh_count = reader.read_uint16()

        lod.model_lod_range   = reader.read_float()
        lod.texture_lod_range = reader.read_float()
        
        lod.water_mesh_idx    = reader.read_uint16()
        lod.water_mesh_count  = reader.read_uint16()
        lod.shadow_mesh_idx   = reader.read_uint16()
        lod.shadow_mesh_count = reader.read_uint16()

        lod.terrain_shadow_mesh_idx   = reader.read_uint16()
        lod.terrain_shadow_mesh_count = reader.read_uint16()
        lod.vertical_fog_mesh_idx     = reader.read_uint16()
        lod.vertical_fog_mesh_count   = reader.read_uint16()
        
        lod.edge_geometry_size        = reader.read_uint32()
        lod.edge_geometry_data_offset = reader.read_uint32()
        
        lod.polygon_count     = reader.read_uint32()
        lod.neck_morph_offset = reader.read_byte()
        lod.neck_morph_count  = reader.read_byte()
        lod.unknown1          = reader.read_uint16()
        
        lod.vertex_buffer_size = reader.read_uint32()
        lod.idx_buffer_size    = reader.read_uint32()
        lod.vertex_data_offset = reader.read_uint32()
        lod.idx_data_offset    = reader.read_uint32()
        
        return lod
    
    def write(self, file: BytesIO) -> None:
        file.write(pack('<H', self.mesh_idx))
        file.write(pack('<H', self.mesh_count))

        file.write(pack('<f', self.model_lod_range))
        file.write(pack('<f', self.texture_lod_range))

        file.write(pack('<H', self.water_mesh_idx))
        file.write(pack('<H', self.water_mesh_count))
        file.write(pack('<H', self.shadow_mesh_idx))
        file.write(pack('<H', self.shadow_mesh_count))

        file.write(pack('<H', self.terrain_shadow_mesh_idx))
        file.write(pack('<H', self.terrain_shadow_mesh_count))
        file.write(pack('<H', self.vertical_fog_mesh_idx))
        file.write(pack('<H', self.vertical_fog_mesh_count))

        file.write(pack('<I', self.edge_geometry_size))
        file.write(pack('<I', self.edge_geometry_data_offset))

        file.write(pack('<I', self.polygon_count))
        file.write(pack('<B', self.neck_morph_offset))
        file.write(pack('<B', self.neck_morph_count))
        file.write(pack('<H', self.unknown1))

        file.write(pack('<I', self.vertex_buffer_size))
        file.write(pack('<I', self.idx_buffer_size))
        file.write(pack('<I', self.vertex_data_offset))
        file.write(pack('<I', self.idx_data_offset))
    
    def size() -> int:
        return 60

@dataclass
class ExtraLod:
    light_shaft_mesh_index    : int = 0       
    light_shaft_mesh_count    : int = 0
    glass_mesh_index          : int = 0             
    glass_mesh_count          : int = 0
    material_change_mesh_index: int = 0    
    material_change_mesh_count: int = 0
    crest_change_mesh_index   : int = 0       
    crest_change_mesh_count   : int = 0
    
    unknown1 : int = 0                      
    unknown2 : int = 0                    
    unknown3 : int = 0
    unknown4 : int = 0
    unknown5 : int = 0
    unknown6 : int = 0
    unknown7 : int = 0
    unknown8 : int = 0
    unknown9 : int = 0
    unknown10: int = 0
    unknown11: int = 0
    unknown12: int = 0
    
    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'ExtraLod':
        extra_lod = cls()

        for field in fields(cls):
            setattr(extra_lod, field.name, reader.read_uint16())
        
        return extra_lod
    
    def write(self, file: BytesIO) -> None:
        for field in fields(self):
            file.write(
                    pack(
                        '<H', 
                        getattr(self, field.name)
                    )
                )
        