import re
import bpy


from typing              import TYPE_CHECKING, Literal
from bpy.types           import Object
from collections         import defaultdict

from ..xiv.formats.model import XIV_ATTR

if TYPE_CHECKING:
    from .file           import YAFileProps
    from .studio         import YAStudioProps
    from .window         import YAWindowProps
    from ..utils.typings import DevkitProps, DevkitWindowProps
    

def get_file_props() -> 'YAFileProps':
    return bpy.context.scene.ya_file_props

def get_studio_props() -> 'YAStudioProps':
    return bpy.context.scene.ya_studio_props

def get_window_props() -> 'YAWindowProps':
    return bpy.context.window_manager.ya_window_props

def get_devkit_props() -> 'DevkitProps' | Literal[False]:
    return getattr(bpy.context.scene, "ya_devkit_props", False)

def get_devkit_win_props() -> 'DevkitWindowProps' | Literal[False]:
    return getattr(bpy.context.window_manager, "ya_devkit_window", False)

def get_xiv_meshes(objs: list[Object]) -> list[list[tuple[Object, int, str, list[str]]]] :
    
    def get_mesh_id(obj: Object) -> tuple[int | None, int | None, int, str | None]:
        name_parts = obj.name.strip().split(" ")
        lod_level  = 0
        if re.search(r"^\d+.\d+\s", obj.name):
            mesh_id   = name_parts[0]
            name      = name_parts[1:]
            lod_level = int(obj.name[-1]) if obj.name[-4:-1] == "LOD" else 0
        elif re.search(r"\s\d+.\d+$", obj.name):
            mesh_id = name_parts[-1]

            if name_parts[-2] == "Part":
                name_parts.pop()
            name = name_parts[:-1]
        else:
            return None, None, None, None
        
        mesh       = int(mesh_id.split(".")[0])
        submesh    = int(mesh_id.split(".")[1])
        clean_name = " ".join(name)  
        return mesh, submesh, lod_level, clean_name

    mesh_dict: dict[int, list[tuple[Object, int, str, list[str]]]] = defaultdict(list)
    for obj in objs:
        mesh, submesh, lod, name = get_mesh_id(obj)
        if mesh is None or submesh is None:  
            continue
        elif lod > 2:
            continue

        obj_props = [key for key, value in obj.items() if key.startswith(XIV_ATTR) and value]
        mesh_dict[mesh].append((obj, submesh, lod, name, obj_props))

    mesh_indices = sorted(mesh_dict.keys())
    sorted_meshes: list[list[tuple[Object, int, str, list[str]]]] = []
    for mesh_idx in mesh_indices:
        submeshes = sorted(mesh_dict[mesh_idx], key=lambda x: (x[2], x[1]))
        sorted_meshes.append(submeshes)
    
    return sorted_meshes
