# The code within this tool is made for the Blender API and follows its GPL3 licensing.

# The code's implentation is specifically tailored for my "Yet Another Devkit",
# and regarding its usage I do request that it does not be used for creating mods 
# or assets that are behind a permanent paywall, three months at the most.

bl_info = {
    "name": "Yet Another Addon",
    "author": "Aleks",
    "description": "Several tools to speed up XIV modding workflows.",
    "version": (0, 10, 3),
    "blender": (4, 2, 1),
    "category": "",
    }

import os
import sys
import bpy

sys.path.append(os.path.dirname(__file__))

from .ui            import panel
from .file          import export
from .file          import modpack
from .file          import ya_import
from .util          import props
from .util          import handlers
from .util          import penumbra
from .outfit        import mesh 
from .outfit        import shapes   
from .outfit        import weights  
from .outfit        import armature
from importlib      import reload
    
      
modules = [
    props,
    ya_import,
    export,
    modpack,
    weights,
    armature,
    shapes,
    mesh,
    panel
]

m_reload = [
    handlers,
    penumbra
]

def menu_emptyvgroup_append(self, context):
    self.layout.separator(type="LINE")
    self.layout.operator("ya.remove_empty_vgroups", text="Remove Empty Vertex Groups").preset = "menu"
    self.layout.operator("ya.remove_select_vgroups", text= "Remove Selected and Adjust Parent").preset = "menu"

def register():
    for module in modules + m_reload:
        reload(module)

    for module in modules:
        for cls in module.CLASSES:
            bpy.utils.register_class(cls)
        if module == props:
            props.set_addon_properties()
      
    handlers.set_handlers()
    bpy.types.Scene.ya_addon_ver = bl_info["version"]
    bpy.types.MESH_MT_vertex_group_context_menu.append(menu_emptyvgroup_append)

def unregister():
    handlers.remove_handlers()
    bpy.types.MESH_MT_vertex_group_context_menu.remove(menu_emptyvgroup_append)
    
    for module in reversed(modules):
        if module == props:
            props.remove_addon_properties()
        for cls in reversed(module.CLASSES):
            bpy.utils.unregister_class(cls)
