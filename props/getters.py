import bpy

from typing import TYPE_CHECKING, Literal

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
