# Usage of this code, unless otherwise credited below, is only allowed for a limited commercial scope. Any meshes or products 
# made with these tools are subject to a maximum paywall of 3 (three) months whereafter they must become publicly available for free.

bl_info = {
    "name": "Yet Another Addon",
    "author": "Aleks",
    "description": "A set of tools made for ease of use with Yet Another Devkit.",
    "version": (0, 3, 0),
    "blender": (4, 2, 1),
    "category": "",
    }

import os
import sys
sys.path.append(os.path.dirname(__file__))

import bpy

from importlib  import reload
from .          import ya_utils
from .          import ui_ops
from .          import ui_main
from .          import penumbra  
from .          import tools_ops        

#Test
modules = [
    penumbra,
    ya_utils,
    tools_ops,
    ui_ops,
    ui_main,
]

def menu_emptyvgroup_append(self, context):
    self.layout.separator(type="LINE")
    self.layout.operator("ya.remove_empty_vgroups", text="Remove Empty Vertex Groups")

def register():
    for module in modules:
        reload(module)

    for module in modules:
        for cls in module.classes:
            bpy.utils.register_class(cls)
        if module == ya_utils:
            ya_utils.set_devkit_properties()
    

    ya_utils.addon_version = bl_info["version"]
    bpy.types.MESH_MT_vertex_group_context_menu.append(menu_emptyvgroup_append)

def unregister():
    del ya_utils.addon_version
    bpy.types.MESH_MT_vertex_group_context_menu.remove(menu_emptyvgroup_append)

    for module in reversed(modules):
        for cls in reversed(module.classes):
            bpy.utils.unregister_class(cls)

    del bpy.types.Scene.main_props
    del bpy.types.Scene.file_props
    del bpy.types.Scene.collection_state
    del bpy.types.Scene.modpack_group_options
    
if __name__ == "__main__":
    register()
