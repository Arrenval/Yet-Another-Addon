from functools import cache
from bpy.types import UIList, UILayout, Context, VertexGroup, ShapeKey

from ..props   import get_studio_props, get_window_props, YASUIList


@cache
def get_icon_value(icon_name: str) -> int:
        return UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items[icon_name].value

class MESH_UL_YAS(UIList):
    bl_idname = "MESH_UL_YAS"

    def draw_item(self, context:Context, layout:UILayout, data, item: VertexGroup | YASUIList, icon, active_data, active_propname):
        window = get_window_props()
        if isinstance(item, YASUIList) and getattr(window, "yas_empty", False):
            error = get_icon_value("INFO")
            if self.layout_type in {"DEFAULT", "COMPACT"}:
                layout.prop(item, "name", text="", emboss=False, icon_value=error)
                layout.alignment = "CENTER"

            elif self.layout_type == "GRID":
                layout.alignment = "CENTER"
                layout.label(text="", icon_value=error)
        else:
            self.draw_vertex_group(layout, item) 

    def draw_vertex_group(self, layout: UILayout, item: VertexGroup):
        icon     = get_icon_value("GROUP_VERTEX")
        category = get_studio_props().YAS_BONES.get(item.name, "Unknown")
   
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(item, "name", text=category, emboss=False, icon_value=icon)
            icon = "LOCKED" if item.lock_weight else "UNLOCKED"
            layout.prop(item, "lock_weight", text="", icon=icon, emboss=False)

        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)

    
class MESH_UL_YA_SHAPE(UIList):
    bl_idname = "MESH_UL_YA_SHAPE"

    def draw_item(self, context, layout: UILayout, data, item: ShapeKey, icon, active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            if item.name[-1] == ":":
                layout.prop(item, "name", text="", emboss=False, icon_value=get_icon_value("REMOVE"))
            else:
                layout.prop(item, "name", text="", emboss=False, icon_value=icon)
     

CLASSES = [
    MESH_UL_YAS,
    MESH_UL_YA_SHAPE,
] 