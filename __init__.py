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

DEVKIT_SCR_VER = (0, 0, 0)

import os
import sys
import ast
import bpy

sys.path.append(os.path.dirname(__file__))

from importlib  import reload
from .modpack   import props
from .modpack   import panel         as pmp_panel
from .modpack   import file_manager  
from .modpack   import penumbra  
from .          import operators 
from .          import panel         as ops_panel 
      

#Test
modules = [
    penumbra,
    file_manager,
    operators,
    props,
    pmp_panel,
    ops_panel,
]

def menu_emptyvgroup_append(self, context):
    self.layout.separator(type="LINE")
    self.layout.operator("ya.remove_empty_vgroups", text="Remove Empty Vertex Groups")

def devkit_check():
    global DEVKIT_SCR_VER
    devkit = bpy.data.texts.get("devkit.py")

    if devkit:
        first_line = devkit.lines[0].body.strip()
        
        if first_line.startswith("DEVKIT_SCR_VER"):
            version = ast.literal_eval(first_line.split('=')[1].strip())
                
            if isinstance(version, tuple) and len(version) == 3:
                DEVKIT_SCR_VER = version
                try:
                    bpy.utils.unregister_class(pmp_panel.ModpackManager)
                except:
                    pass
                return None
    else:
        return None

def register():
    for module in modules:
        reload(module)

    for module in modules:
        for cls in module.classes:
            bpy.utils.register_class(cls)
        if module == props:
            props.set_addon_properties()
                 
    bpy.app.timers.register(devkit_check, first_interval=0.5)

    props.addon_version = bl_info["version"]
    bpy.types.MESH_MT_vertex_group_context_menu.append(menu_emptyvgroup_append)

def unregister():
    del props.addon_version
    bpy.types.MESH_MT_vertex_group_context_menu.remove(menu_emptyvgroup_append)

    for module in reversed(modules):
        for cls in reversed(module.classes):
            if DEVKIT_SCR_VER > (0, 0, 0) and cls == pmp_panel.ModpackManager:
                continue
            bpy.utils.unregister_class(cls)

    del bpy.types.Scene.pmp_props
    del bpy.types.Scene.pmp_group_options
    
if __name__ == "__main__":
    register()
