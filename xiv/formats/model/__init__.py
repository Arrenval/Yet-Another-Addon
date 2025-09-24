from .lod    import Lod
from .file   import XIVModel, BoundingBox, BoneTable
from .mesh   import Mesh, Submesh
from .face   import NeckMorph
from .enums  import VertexType, VertexUsage, ModelFlags1, ModelFlags2, ModelFlags3
from .shapes import ShapeMesh
from .vertex import VertexDeclaration, VertexElement, get_vert_struct, XIV_COL, XIV_UV

XIV_ATTR = ("atr", "heels_offset", "skin_suffix")
