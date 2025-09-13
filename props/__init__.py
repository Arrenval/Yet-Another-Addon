import bpy

from bpy.props import PointerProperty

from .file     import YAFileProps, CLASSES as FILE_CLS
from .studio   import YAStudioProps, YASStorage, YASUIList,  CLASSES as STUDIO_CLS
from .window   import YAWindowProps, CLASSES as WIN_CLS
from .modpack  import CLASSES as MODPACK_CLS
from .getters  import get_file_props, get_studio_props, get_window_props, get_devkit_props, get_devkit_win_props, get_xiv_meshes
from .handlers import set_handlers, remove_handlers


def set_addon_properties() -> None:
    bpy.types.Scene.ya_file_props = PointerProperty(
        type=YAFileProps)
    
    bpy.types.WindowManager.ya_window_props = PointerProperty(
        type=YAWindowProps)

    bpy.types.Scene.ya_studio_props = PointerProperty(
        type=YAStudioProps)
    
    bpy.types.Object.yas = PointerProperty(name="YAS Weight Storage",
        type=YASStorage)
    
    YAWindowProps.ui_buttons()
    YAWindowProps.set_extra_options()
    
def remove_addon_properties() -> None:
    del bpy.types.Scene.ya_file_props
    del bpy.types.WindowManager.ya_window_props
    del bpy.types.Scene.ya_studio_props
    del bpy.types.Object.yas

CLASSES = MODPACK_CLS + WIN_CLS + STUDIO_CLS + FILE_CLS
