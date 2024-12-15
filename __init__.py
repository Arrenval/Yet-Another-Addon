# Usage of this code, unless otherwise credited below, is only allowed for a limited commercial scope. Any meshes or products 
# made with these tools are subject to a maximum paywall of 3 (three) months whereafter they must become publicly available for free.

bl_info = {
    "name": "Yet Another Addon",
    "author": "Aleks",
    "description": "A set of tools made for ease of use with Yet Another Devkit.",
    "version": (0, 3, 1),
    "blender": (4, 2, 1),
    "category": "",
    }

DEVKIT_VER = (0, 0, 0)

import os
import sys
import ast
import bpy

sys.path.append(os.path.dirname(__file__))

from importlib  import reload
from .ui        import panel
from .file      import ya_import
from .file      import export
from .file      import modpack
from .util      import props    
from .outfit    import shapes  
from .outfit    import mesh  
from .outfit    import weights        
      
modules = [
    ya_import,
    export,
    modpack,
    weights,
    shapes,
    mesh,
    props,
    panel
]

def menu_emptyvgroup_append(self, context):
    self.layout.separator(type="LINE")
    self.layout.operator("ya.remove_empty_vgroups", text="Remove Empty Vertex Groups")

def devkit_check():
    global DEVKIT_VER
    if bpy.data.texts.get("devkit.py"):
        devkit = bpy.data.texts["devkit.py"].as_module()
        DEVKIT_VER = devkit.DEVKIT_VER
        bpy.types.Scene.devkit = devkit
    else:
        return None

def register():
    for module in modules:
        reload(module)

    for module in modules:
        for cls in module.CLASSES:
            bpy.utils.register_class(cls)
        if module == props:
            props.set_addon_properties()

    bpy.app.timers.register(devkit_check, first_interval=0.1)
    bpy.types.Scene.ya_addon_ver = bl_info["version"]
    bpy.types.MESH_MT_vertex_group_context_menu.append(menu_emptyvgroup_append)

def unregister():
    bpy.types.MESH_MT_vertex_group_context_menu.remove(menu_emptyvgroup_append)

    for module in reversed(modules):
        for cls in reversed(module.CLASSES):
            if cls == props:
                props.remove_addon_properties()
            bpy.utils.unregister_class(cls)

    del bpy.types.Scene.ya_addon_ver
    if hasattr(bpy.context.scene, "devkit"):
        del bpy.types.Scene.devkit
    
if __name__ == "__main__":
    register()
