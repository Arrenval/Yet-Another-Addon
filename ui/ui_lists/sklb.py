from bpy.types import UIList, UILayout

from ...props  import HkBone, AnimLayer


class MESH_UL_YA_BONES(UIList):
    bl_idname = "MESH_UL_YA_BONES"

    def draw_item(self, context, layout: UILayout, data, item: HkBone, icon, active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(item, "name", text=str(item.index), emboss=False, icon_value=icon)

class MESH_UL_YA_LAYER(UIList):
    bl_idname = "MESH_UL_YA_LAYER"

    def draw_item(self, context, layout: UILayout, data, item: AnimLayer, icon, active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(item, "name", text="", emboss=False, icon_value=icon)

class MESH_UL_YA_MAPPER(UIList):
    bl_idname = "MESH_UL_YA_MAPPER"

    def draw_item(self, context, layout: UILayout, data, item: HkBone, icon, active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(item, "bone_a", text="", emboss=False, icon_value=icon)
    

CLASSES = [
    MESH_UL_YA_BONES,
    MESH_UL_YA_LAYER,
    MESH_UL_YA_MAPPER
]