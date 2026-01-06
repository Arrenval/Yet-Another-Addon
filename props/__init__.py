import bpy

from typing    import TYPE_CHECKING
from bpy.types import Armature, Object
from bpy.props import PointerProperty,FloatProperty

from .file     import YAFileProps, CLASSES as FILE_CLS
from .studio   import YAStudioProps, YASStorage, YASUIList,  CLASSES as STUDIO_CLS
from .window   import YAWindowProps, CLASSES as WIN_CLS
from .modpack  import CLASSES as MODPACK_CLS
from .skeleton import SkeletonProps, KaosArmature, SklbMapper,  AnimLayer, HkBone, MapBone, CacheBone, CLASSES as SKLT_CLS

from .getters  import get_file_props, get_studio_props, get_window_props, get_devkit_props, get_devkit_win_props, get_xiv_meshes, get_skeleton_props
from .handlers import set_handlers, remove_handlers

if TYPE_CHECKING:
    from bpy.types import Armature as _Armature, Object as _Object
    
    class Object(_Object):
        """Blender Object with YASStorage"""
        yas: YASStorage

    class Armature(_Armature):
        """Blender Armature with KaosArmature"""
        kaos: KaosArmature


def set_addon_properties() -> None:
    bpy.types.Scene.ya_file_props = PointerProperty(
        type=YAFileProps)
    
    bpy.types.WindowManager.ya_window_props = PointerProperty(
        type=YAWindowProps)

    bpy.types.Scene.ya_studio_props = PointerProperty(
        type=YAStudioProps)
    
    bpy.types.Scene.ya_skeleton_props = PointerProperty(
        type=SkeletonProps)
    
    bpy.types.Object.yas = PointerProperty(name="YAS Weight Storage",
        type=YASStorage)
    
    bpy.types.Armature.kaos = PointerProperty(name="XIV Skeleton Properties",
        type=KaosArmature)
    
    bpy.types.EditBone.kaos_unk = FloatProperty(name="XIV Skeleton Value",
        description="Unknown radian") # type: ignore
    
    bpy.types.Bone.kaos_unk = FloatProperty(name="XIV Skeleton Value",
        description="Unknown radian") # type: ignore
    
    YAWindowProps.ui_buttons()
    YAWindowProps.set_extra_options()
    
def remove_addon_properties() -> None:
    del bpy.types.Scene.ya_file_props
    del bpy.types.Scene.ya_skeleton_props
    del bpy.types.WindowManager.ya_window_props
    del bpy.types.Scene.ya_studio_props
    del bpy.types.Object.yas
    del bpy.types.Armature.kaos
    del bpy.types.EditBone.kaos_unk
    del bpy.types.Bone.kaos_unk

CLASSES = MODPACK_CLS + WIN_CLS + STUDIO_CLS + FILE_CLS + SKLT_CLS
