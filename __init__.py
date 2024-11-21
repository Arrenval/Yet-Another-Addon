# Usage of this code, unless otherwise credited below, is only allowed for a limited commercial scope. Any meshes or products 
# made with these tools are subject to a maximum paywall of 3 (three) months whereafter they must become publicly available for free.

import bpy
from bpy.props import PointerProperty

bl_info = {
    "name": "Yet Another Toolbag",
    "author": "Aleks",
    "description": "A set of tools made for ease of use with Yet Another Devkit.",
    "version": (0, 3, 0),
    "blender": (4, 2, 1),
    "category": "",
    }

import ya_utils as utils
import ya_ui_ops as ui_ops
import ya_tool_ops as tool_ops
import ya_shape_ops as shape_ops
import ya_file_manager as file
import ya_ui_main as ui

classreg = [
    utils.CollectionState,
    utils.UsefulProperties,
    utils.UTILS_OT_YA_CollectionManager,
    file.FILE_OT_SimpleExport,
    file.FILE_OT_YA_BatchQueue,
    file.FILE_OT_YA_ConsoleTools,
    tool_ops.MESH_OT_YA_RemoveEmptyVGroups,
    shape_ops.MESH_OT_YA_ApplyShapes, 
    shape_ops.MESH_OT_YA_ApplyChestCategory,
    shape_ops.MESH_OT_YA_ApplyOther,
    shape_ops.MESH_OT_YA_ApplyLegSizes,
    shape_ops.MESH_OT_YA_ApplyGen,
    shape_ops.MESH_OT_YA_ApplyNails,
    shape_ops.MESH_OT_YA_ApplyVisibility,
    ]

uireg = [
    ui_ops.UI_OT_YA_SetBodyPart,
    ui_ops.UI_OT_YA_DirSelector,   
    ui_ops.UI_OT_YA_ConsoleToolsDirectory,    
    ui.YAOverview, 
    ui.YATools, 
    ui.YAFileManager,
    ]

def menu_emptyvgroup_append(self, context):
    self.layout.separator(type="LINE")
    self.layout.operator("mesh.remove_empty_vgroups", text="Remove Empty Vertex Groups")

def register():

    for cls in classreg:
        bpy.utils.register_class(cls)

    bpy.types.Scene.ya_props = PointerProperty(
        type=utils.UsefulProperties)
    
    bpy.types.Scene.collection_state = bpy.props.CollectionProperty(
        type=utils.CollectionState)
    
    
    utils.addon_version = bl_info["version"]
    utils.UsefulProperties.export_bools()
    utils.UsefulProperties.ui_buttons()
    utils.UsefulProperties.mesh_pointers()
    utils.UsefulProperties.chest_key_floats()
    utils.UsefulProperties.feet_key_floats()
    
    for cls in uireg:
        bpy.utils.register_class(cls)

    bpy.types.MESH_MT_vertex_group_context_menu.append(menu_emptyvgroup_append)

def unregister():

    for cls in reversed(classreg + uireg):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.ya_props
    del utils.addon_version
    del bpy.types.Scene.collection_state
    bpy.types.MESH_MT_vertex_group_context_menu.remove(menu_emptyvgroup_append)

    

    
if __name__ == "__main__":
    register()