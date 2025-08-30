import re

from bpy.types   import Object

from .exceptions import XIVMeshIDError


def get_mesh_ids(obj: Object) -> tuple[int, int]:
    try:
        name_parts = obj.name.split(" ")
        if re.search(r"^\d+\.\d+\s", obj.name):
            group = int(name_parts[0].split(".")[0])
            part  = int(name_parts[0].split(".")[1])
        else:
            group = int(name_parts[-1].split(".")[0])
            part  = int(name_parts[-1].split(".")[1])
    except:
        raise XIVMeshIDError(f"{obj.name}: Couldn't parse Mesh IDs.")
    
    return group, part
