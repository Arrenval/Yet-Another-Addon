
from io           import BytesIO
from numpy        import ushort, single, empty
from struct       import pack
from typing       import List
from dataclasses  import dataclass, field
from numpy.typing import NDArray
 
from .lod         import Lod, ExtraLod
from .bbox        import BoundingBox
from .mesh        import Mesh, Submesh, TerrainShadowMesh, TerrainShadowSubMesh
from .face        import NeckMorph
from .enums       import ModelFlags2
from ..utils      import BinaryReader, write_padding
from .shapes      import Shape, ShapeMesh
from .vertex      import VertexDeclaration
from .headers     import FileHeader, MeshHeader
 

@dataclass
class BoneTable:

    bone_idx  : List[int] = field(default_factory=list) #ushort
    bone_count: int       = 0 

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'BoneTable':
        table = cls()

        start_pos  = reader.pos
        offset     = reader.read_uint16()
        size       = reader.read_uint16()
        return_pos = reader.pos

        reader.pos       = start_pos + offset * 4
        table.bone_idx   = reader.read_array(size, format_str='H')
        table.bone_count = len(table.bone_idx)

        reader.pos = return_pos

        return table
    
    def write(self, file: BytesIO, current_offset: int) -> int:
        file.write(pack('<H', current_offset))
        file.write(pack('<H', self.bone_count))
        header_pos = file.tell()
        
        file.seek((current_offset - 1) * 4, 1)
        for bone in self.bone_idx:
            file.write(pack('<H', bone))
        
        if (self.bone_count & 1) == 1:
            file.write(write_padding(2))
        
        file.seek(header_pos)

        return ((self.bone_count + 1) // 2) - 1

@dataclass
class ElementID:
    element_id : int = 0
    parent_bone: int = 0
    translate  : List[int] = field(default_factory=[])
    rotate     : List[int] = field(default_factory=[])

    @classmethod
    def from_bytes(cls, reader: BinaryReader) -> 'ElementID':
        element = cls()

        element.element_id  = reader.read_uint32()
        element.parent_bone = reader.read_uint32()
        element.translate   = reader.read_array(3, format_str="f")
        element.rotate      = reader.read_array(3, format_str="f")

        return element
    
    def write(self, file: BytesIO) -> None:
        file.write(pack('<I', self.element_id))
        file.write(pack('<I', self.parent_bone))

        for pos in self.translate:
            file.write(pack('<f', pos))
        for rot in self.rotate:
            file.write(pack('<f', rot))


class XIVModel:
    V5                  = 0x01000005
    V6                  = 0x01000006
    NUM_VERTICES        = 17
    FILE_HEADER_SIZE    = 0x44
    VERTEX_BUFFER_LIMIT = 8388608

    def __init__(self):
        shape_value_dtype = [
                                ("base_indices_idx", '<u2'), 
                                ("replace_vert_idx", '<u2')
                            ]
        face_data_dtype = [
                                ("positions", '<f4', (3,)), 
                                ("sign",      '<u4')
                            ]

        self.header         = FileHeader()
        self.mesh_header    = MeshHeader()
        self.header.version = self.V6

        self.attributes: list[str] = []
        self.bones     : list[str] = []
        self.materials : list[str] = []

        self.vertex_declarations     : list[VertexDeclaration]    = []
        self.element_ids             : list[ElementID]            = []
        self.lods                    : list[Lod]                  = [Lod() for _ in range(3)]
        self.extra_lods              : list[ExtraLod]             = []
        self.meshes                  : list[Mesh]                 = []
        self.terrain_shadow_meshes   : list[TerrainShadowMesh]    = []
        self.submeshes               : list[Submesh]              = []
        self.terrain_shadow_submeshes: list[TerrainShadowSubMesh] = []
        self.bone_tables             : list[BoneTable]            = []

        self.shapes                  : list[Shape]                = []
        self.shape_meshes            : list[ShapeMesh]            = []
        # We use numpy for efficiency, the python class can still be found in the "shapes" module
        self.shape_values            : NDArray[ushort]            = empty(0, dtype=shape_value_dtype)

        self.submesh_bonemaps        : list[int]                  = [] #ushort
        self.neck_morphs             : list[NeckMorph]            = []
        # We use numpy for efficiency, the python class can still be found in the "face" module
        self.face_data               : NDArray[single]            = empty(0, dtype=face_data_dtype)

        self.bounding_box                           = BoundingBox()
        self.mdl_bounding_box                       = BoundingBox()
        self.water_bounding_box                     = BoundingBox()
        self.vertical_fog_bounding_box              = BoundingBox()
        self.bone_bounding_boxes: list[BoundingBox] = []

        self.buffers: bytes = b''

    @classmethod
    def from_file(cls, file_path: str) -> 'XIVModel':
        with open(file_path, 'rb') as model:
            return cls.from_bytes(model.read())

    @classmethod
    def from_bytes(cls, data: bytes) -> 'XIVModel':
        
        def read_all_strings(reader: BinaryReader) -> tuple[list[str], list[int]]:
            string_count = reader.read_uint16()
            reader.read_uint16()
            string_size  = reader.read_uint32()
            string_data  = reader.read_bytes(string_size)

            strings: list[str] = []
            offsets: list[int] = []
            start = 0
            for _ in range(string_count):
                string_span = BinaryReader(string_data[start:])
                string_end  = string_span.data.index(b'\0')

                strings.append(string_span.read_string(string_end))
                offsets.append(start)

                start += string_end + 1

            return strings, offsets
        
        def get_strings(count: int) -> list[str]:
            strings: list[str] = []
            for _ in range(count):
                attr_offset = reader.read_uint32()
                try:
                    string_idx = offsets.index(attr_offset)
                except ValueError:
                    string_idx = -1

                string = all_strings[string_idx] if string_idx >= 0 else ""
                strings.append(string)
            
            return strings

        model  = cls()
        reader = BinaryReader(data)

        model.header = FileHeader.from_bytes(reader)

        if model.header == cls.V5:
            raise Exception("Model version not supported. Please use Dawntrail models.")

        data_offset = model._get_data_offset()

        for i in range(model.header.lod_count):
            model.header.vert_offset[i] -= data_offset
            model.header.idx_offset[i]  -= data_offset
        
        model.vertex_declarations = [VertexDeclaration.from_bytes(reader) for _ in range(model.header.vertex_declaration_count)]

        all_strings, offsets = read_all_strings(reader)

        model.mesh_header = MeshHeader.from_bytes(reader)

        model.element_ids = [ElementID.from_bytes(reader) for _ in range(model.mesh_header.element_id_count)]

        model.lods = []
        for i in range(3):
            lod = Lod.from_bytes(reader)
            if i < model.header.lod_count: 
                lod.vertex_data_offset -= data_offset 
                lod.idx_data_offset    -= data_offset
                if lod.edge_geometry_data_offset:
                    lod.edge_geometry_data_offset -= data_offset 
            
            model.lods.append(lod)

        if ModelFlags2.EXTRA_LOD_ENABLED in model.mesh_header.flags2:
            for i in range(3):
                model.extra_lods.append(ExtraLod.from_bytes(reader))
        
        model.meshes = [Mesh.from_bytes(reader) for _ in range(model.mesh_header.mesh_count)]
        
        model.attributes = get_strings(model.mesh_header.attribute_count)

        model.terrain_shadow_meshes    = [TerrainShadowMesh.from_bytes(reader) for _ in range(model.mesh_header.terrain_shadow_mesh_count)]
        model.submeshes                = [Submesh.from_bytes(reader) for _ in range(model.mesh_header.submesh_count)]
        model.terrain_shadow_submeshes = [TerrainShadowSubMesh.from_bytes(reader) for _ in range(model.mesh_header.terrain_shadow_submesh_count)]

        model.materials = get_strings(model.mesh_header.material_count)
        model.bones     = get_strings(model.mesh_header.bone_count)

        model.bone_tables = [BoneTable.from_bytes(reader) for _ in range(model.mesh_header.bone_table_count)]
        reader.pos       += model.mesh_header.bone_table_array_count_total * 2

        model.shapes       = [Shape.from_bytes(reader, all_strings, offsets) for _ in range(model.mesh_header.shape_count)]
        model.shape_meshes = [ShapeMesh.from_bytes(reader) for _ in range(model.mesh_header.shape_mesh_count)]
        model.shape_values = reader.read_to_ndarray(model.shape_values.dtype, model.mesh_header.shape_value_count)

        submesh_bonemap_size   = reader.read_uint32()
        model.submesh_bonemaps = reader.read_array(submesh_bonemap_size // 2, format_str='H')

        model.neck_morphs      = [NeckMorph.from_bytes(reader) for _ in range (model.mesh_header.neck_morph_count)]
        model.face_data        = reader.read_to_ndarray(model.face_data.dtype, model.mesh_header.face_data_count)

        padding     = reader.read_byte()
        reader.pos += padding

        model.bounding_box              = BoundingBox.from_bytes(reader)
        model.mdl_bounding_box          = BoundingBox.from_bytes(reader)
        model.water_bounding_box        = BoundingBox.from_bytes(reader)
        model.vertical_fog_bounding_box = BoundingBox.from_bytes(reader)
        model.bone_bounding_boxes       = [BoundingBox.from_bytes(reader) for _ in range(model.mesh_header.bone_count)]
    
        reader.pos = data_offset
        model.buffers = reader.read_bytes(len(reader.data) - reader.pos)

        return model
    
    def to_file(self, file_path: str) -> None:
        with open(file_path, 'wb') as model:
            model.write(self.to_bytes())

    def to_bytes(self) -> bytes:

        def write_strings(file: BytesIO) -> list[int]:
            start_pos = file.tell()
            base_pos  = start_pos + 8
            count     = len(self.attributes) + len(self.bones) + len(self.materials) + len(self.shapes)

            file.write(pack('<H', count))
            file.seek(base_pos)

            all_strings        = self.attributes + self.bones + self.materials + [shape.name for shape in self.shapes]
            offsets: list[int] = []
            for i, string in enumerate(all_strings):
                current_pos = file.tell()
                file.write(string.encode())
                file.write(write_padding(1))
                offsets.append(current_pos - base_pos)

            padding     = (file.tell() & ~0b11) + 4 if (file.tell() & 0b11) > 0 else file.tell()
            current_pos = file.tell()
            for _ in range(current_pos, padding):
                file.write(write_padding(1))
            size = file.tell() - base_pos

            file.seek(start_pos + 4)
            file.write(pack('<I', size))
            file.seek(base_pos + size)
      
            return offsets

        self.header.stack_size = len(self.vertex_declarations) * self.NUM_VERTICES * 8
        self.set_counts()
        
        file = BytesIO()
        file.seek(self.FILE_HEADER_SIZE)

        for decl in self.vertex_declarations:
            decl.write(file)
        
        offsets = write_strings(file)
        self.mesh_header.write(file)

        for element in self.element_ids:
            element.write(file)
        
        lod_pos = file.tell()
        file.seek(Lod.size() * 3, 1)

        if ModelFlags2.EXTRA_LOD_ENABLED in self.mesh_header.flags2:
            for extra_lod in self.extra_lods:
                extra_lod.write(file)
        
        for mesh in self.meshes:
            mesh.write(file)
        
        for i in range(len(self.attributes)):
            file.write(pack('<I', offsets[i]))
        
        for mesh in self.terrain_shadow_meshes:
            mesh.write(file)
        for mesh in self.submeshes:
            mesh.write(file)
        for mesh in self.terrain_shadow_submeshes:
            mesh.write(file)
        
        start_idx = len(self.bones) + len(self.attributes)
        for i in range(len(self.materials)):
            file.write(pack('<I', offsets[start_idx + i]))

        start_idx = len(self.attributes)
        for i in range(len(self.bones)):
            file.write(pack('<I', offsets[start_idx + i]))
        
        current_offset = len(self.bone_tables)
        for table in self.bone_tables:
            current_offset += table.write(file, current_offset)
        
        file.seek(self.mesh_header.bone_table_array_count_total * 2, 1)

        start_idx = len(self.bones) + len(self.attributes) + len(self.materials)
        for idx, shape in enumerate(self.shapes):
            shape.write(file, offsets[start_idx + idx])

        for mesh in self.shape_meshes:
            mesh.write(file)
        file.write(self.shape_values.tobytes())
        
        file.write(pack('<I', len(self.submesh_bonemaps) * 2))
        for bone in self.submesh_bonemaps:
            file.write(pack('<H', bone))
        
        for morph in self.neck_morphs:
            morph.write(file)

        file.write(self.face_data.tobytes())

        padding = ((file.tell() + 1) & 0b111)
        if padding > 0:
            padding = 8 - padding
    
        file.write(pack('<B', padding))
        if padding > 0:
            magic = 0xDEADBEEFF00DCAFE
            
            magic_bytes = magic.to_bytes(8) 
            file.write(magic_bytes[:padding])

        self.bounding_box.write(file)
        self.mdl_bounding_box.write(file)
        self.water_bounding_box.write(file)
        self.vertical_fog_bounding_box.write(file)
        for box in self.bone_bounding_boxes:
            box.write(file)
        
        total_size = file.tell()
        file.write(self.buffers)

        file.seek(0)

        self.header.runtime_size = total_size - self.header.stack_size - self.FILE_HEADER_SIZE
        self._update_offsets(total_size)
        self.header.write(file)

        file.seek(lod_pos)
        for lod in self.lods:
            lod.write(file)

        self.validate()
        return file.getvalue()

    def _update_offsets(self, total_size: int) -> None:
        for i in range(self.header.lod_count):
            self.header.vert_offset[i]      += total_size
            self.header.idx_offset[i]       += total_size
            self.lods[i].vertex_data_offset += total_size 
            self.lods[i].idx_data_offset    += total_size

            self.lods[i].edge_geometry_data_offset += total_size 

    def get_shape(self, name: str, create_missing: bool=False) -> Shape:
        for shape in self.shapes:
            if shape.name == name:
                return shape
        
        if create_missing:
            new_shape = Shape(name=name)
            self.shapes.append(new_shape)
            return new_shape
        else:
            raise ValueError("Shape name not found.")
         
    def set_counts(self) -> None:
        self.header.vertex_declaration_count = len(self.vertex_declarations)
        self.header.material_count           = len(self.materials)

        self.mesh_header.mesh_count          = len(self.meshes)
        self.mesh_header.attribute_count     = len(self.attributes)
        self.mesh_header.submesh_count       = len(self.submeshes)
        self.mesh_header.material_count      = len(self.materials)
        self.mesh_header.bone_count          = len(self.bones)
        self.mesh_header.bone_table_count    = len(self.bone_tables)
        self.mesh_header.shape_count         = len(self.shapes)
        self.mesh_header.shape_mesh_count    = len(self.shape_meshes)
        self.mesh_header.shape_value_count   = len(self.shape_values)
        self.mesh_header.element_id_count    = len(self.element_ids)
        self.mesh_header.neck_morph_count    = len(self.neck_morphs)
        self.mesh_header.face_data_count     = len(self.face_data)

        self.mesh_header.terrain_shadow_mesh_count    = len(self.terrain_shadow_meshes)
        self.mesh_header.terrain_shadow_submesh_count = len(self.terrain_shadow_submeshes)

        self.mesh_header.bone_table_array_count_total = sum(
                            (table.bone_count + 1) if (table.bone_count & 1) == 1 else table.bone_count 
                            for table in self.bone_tables
                        )
    
    def set_lod_count(self, count: int) -> None:
        self.header.lod_count      = count
        self.mesh_header.lod_count = count
    
    def validate(self) -> None:
        size_limit = any([size > self.VERTEX_BUFFER_LIMIT for size in self.header.vert_buffer_size])
        if size_limit:
            raise ValueError(f"Vertex buffer is too large.")

    def _get_data_offset(self) -> int:
        return self.FILE_HEADER_SIZE + self.header.runtime_size + self.header.stack_size
    