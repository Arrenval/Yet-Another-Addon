import bpy

from bpy.props       import PointerProperty

from .file           import YAFileProps, CLASSES as FILE_CLS
from .outfit         import YAOutfitProps, YASStorage, YASUIList,  CLASSES as OUTFIT_CLS
from .window         import YAWindowProps, CLASSES as WIN_CLS
from .modpack        import CLASSES as MODPACK_CLS
from .getters        import get_file_properties, get_outfit_properties, get_window_properties, get_devkit_properties, get_devkit_win_props


def set_addon_properties() -> None:
    bpy.types.Scene.ya_file_props = PointerProperty(
        type=YAFileProps)
    
    bpy.types.WindowManager.ya_window_props = PointerProperty(
        type=YAWindowProps)

    bpy.types.Scene.ya_outfit_props = PointerProperty(
        type=YAOutfitProps)
    
    bpy.types.Object.yas = PointerProperty(name="YAS Weight Storage",
        type=YASStorage)
    
    YAWindowProps.ui_buttons()
    YAWindowProps.set_extra_options()
    
def remove_addon_properties() -> None:
    del bpy.types.Scene.ya_file_props
    del bpy.types.WindowManager.ya_window_props
    del bpy.types.Scene.ya_outfit_props
    del bpy.types.Object.yas

CLASSES = MODPACK_CLS + WIN_CLS + OUTFIT_CLS + FILE_CLS
