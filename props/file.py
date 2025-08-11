import os
import bpy

from typing    import TYPE_CHECKING
from bpy.types import PropertyGroup, Object, Context
from bpy.props import StringProperty, CollectionProperty, PointerProperty

from .modpack  import LoadedModpackGroup


class YAFileProps(PropertyGroup):

    GAME_SUFFIX = {".mdl", ".tex", ".phyb"}

    # Used to define operator behaviour.
    #   Keyword      Keyword       Default  Description
    
    def update_directory(self, context:Context, category:str) -> None:
        prop = context.scene.file_props
        actual_prop = f"{category}_dir"
        display_prop = f"{category}_display_dir"

        display_dir = getattr(prop, display_prop, "")

        if os.path.exists(display_dir):  
            setattr(prop, actual_prop, display_dir)
            
    loaded_pmp_groups: CollectionProperty(
        type=LoadedModpackGroup
        ) # type: ignore
    
    import_armature: PointerProperty(
        type= Object,
        name= "",
        description= "New armature for imports",
        poll=lambda self, obj: obj.type == "ARMATURE"
        )  # type: ignore

    import_display_dir: StringProperty(
        name="Export Folder",
        default="Select Export Directory",  
        maxlen=255,
        update=lambda self, context: self.update_directory(context, 'import'),
        ) # type: ignore
    
    export_armature: PointerProperty(
        type= Object,
        name= "",
        description= "Armature for exports",
        poll=lambda self, obj: obj.type == "ARMATURE"
        )  # type: ignore
    
    if TYPE_CHECKING:
        loaded_pmp_groups : LoadedModpackGroup
        import_display_dir: str
        import_armature   : Object
        export_armature   : Object


CLASSES = [    
    YAFileProps,
]
 