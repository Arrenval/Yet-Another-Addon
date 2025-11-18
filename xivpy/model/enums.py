from enum    import Enum, Flag


class VertexType(Enum):
    SINGLE1 = 0      
    SINGLE2 = 1      
    SINGLE3 = 2      
    SINGLE4 = 3   

    UNK4    = 4
    UBYTE4  = 5       
    SHORT2  = 6       
    SHORT4  = 7       
    NBYTE4  = 8       
    NSHORT2 = 9      
    NSHORT4 = 10 

    UNK11   = 11
    UNK12   = 12
    HALF2   = 13       
    HALF4   = 14       
    UNK15   = 15

    USHORT2 = 16     
    USHORT4 = 17     
    
class VertexUsage(Enum):
    POSITION      = 0
    BLEND_WEIGHTS = 1
    BLEND_INDICES = 2

    NORMAL        = 3
    UV            = 4
    FLOW          = 5 #Tangent data, but used for hair anisotropy
    TANGENT       = 6
    COLOUR        = 7

class ModelFlags1(Flag):
    DUST_OCCLUSION_ENABLED      = 0x80 
    SNOW_OCCLUSION_ENABLED      = 0x40
    RAIN_OCCLUSION_ENABLED      = 0x20
    UNKNOWN1                    = 0x10
    LIGHTING_REFLECTION_ENABLED = 0x08
    WAVING_ANIMATION_DISABLED   = 0x04
    LIGHT_SHADOW_DISABLED       = 0x02
    SHADOW_DISABLED             = 0x01

class ModelFlags2(Flag):
    STATIC_MESH                 = 0x80 # TT refers to this as HasBonelessParts, possibly used for furniture
    BG_UV_SCROLL_ENABLED        = 0x40
    ENABLE_FORCE_NON_RESIDENT   = 0x20
    EXTRA_LOD_ENABLED           = 0x10
    SHADOW_MASK_ENABLED         = 0x08
    FORCE_LOD_RANGE_ENABLED     = 0x04
    EDGE_GEOMETRY_ENABLED       = 0x02
    UNKNOWN2                    = 0x01

# Taken from TT, not tested
class ModelFlags3(Flag):
    UNKNOWN8                    = 0x80 
    UNKNOWN7                    = 0x40
    UNKNOWN6                    = 0x20
    UNKNOWN5                    = 0x10
    UNKNOWN4                    = 0x08
    USE_CREST_CHANGE            = 0x04
    USE_MATERIAL_CHANGE         = 0x02
    UNKNOWN3                    = 0x01
