from numpy            import dtype
from collections      import defaultdict
     
from ...formats.model import VertexDeclaration, VertexUsage, get_vert_struct


def get_array_type(vert_decl: VertexDeclaration) -> dict[int, dtype]:
    streams: dict[int, list] = defaultdict(list)
    
    uv_channels  = 0
    col_channels = 0
    for element in vert_decl.vertex_elements:
        base_dtype, component_count = get_vert_struct(element.type, element.usage)

        suffix = ""
        if element.usage == VertexUsage.COLOUR:
            suffix        = col_channels
            col_channels += 1
        if element.usage == VertexUsage.UV:
            suffix       = uv_channels
            uv_channels += 1

        name = f"{element.usage.name.lower()}{suffix}"
        if component_count == 1:
            streams[element.stream].append((name, base_dtype))
        else:
            streams[element.stream].append((name, base_dtype, (component_count,)))
    
    array_types: dict[int, dtype] = {}
    for stream, types in streams.items():
        array_types[stream] = dtype(types)
    
    return array_types
