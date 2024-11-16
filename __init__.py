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
import ya_ui_main as UI
import ya_operators as operators
import ya_file_manager as file

classreg = [
    utils.UsefulProperties,
    file.FILE_OT_simple_export,
    file.FILE_OT_YA_CollectionManager,
    file.FILE_OT_YA_BatchExport,  
    operators.MESH_OT_YA_RemoveEmptyVGroups, 
    operators.MESH_OT_YA_ApplyShapes, 
    operators.MESH_OT_YA_ApplySizeCategoryLarge, 
    operators.MESH_OT_YA_ApplySizeCategoryMedium, 
    operators.MESH_OT_YA_ApplySizeCategorySmall,
    operators.YA_OBJECT_OT_SetBodyPart,
    ]

uireg = [ 
    UI.VIEW3D_PT_YA_OVERVIEW, 
    UI.VIEW3D_PT_YA_WEIGHTS, 
    UI.VIEW3D_PT_YA_FILE_MANAGER,
    ]

def register():
    for cls in classreg:
        bpy.utils.register_class(cls)

    bpy.types.Scene.ya_props = PointerProperty(
        type=utils.UsefulProperties)

    utils.UsefulProperties.export_bools()
    utils.UsefulProperties.ui_buttons()
    utils.UsefulProperties.mesh_pointers()
    utils.UsefulProperties.torso_key_floats()
    utils.UsefulProperties.mq_chest_key_floats()
    
    for cls in uireg:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classreg + uireg):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.ya_props
       

if __name__ == "__main__":
    register()