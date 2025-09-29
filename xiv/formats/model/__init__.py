from .lod    import Lod
from .file   import XIVModel, BoundingBox, BoneTable
from .mesh   import Mesh, Submesh
from .face   import NeckMorph, FACE_DATA_DTYPE
from .enums  import VertexType, VertexUsage, ModelFlags1, ModelFlags2, ModelFlags3
from .shapes import ShapeMesh, SHAPE_VALUE_DTYPE
from .vertex import VertexDeclaration, VertexElement, get_vert_struct, XIV_COL, XIV_UV

XIV_ATTR = ("atr", "heels_offset", "skin_suffix")
