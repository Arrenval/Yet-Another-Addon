from bpy.types              import UIList, UILayout, Context, VertexGroup
from ..properties           import get_outfit_properties


class MESH_UL_yas(UIList):
    bl_idname = "MESH_UL_yas"

    def draw_item(self, context:Context, layout:UILayout, data, item:VertexGroup, icon, active_data, active_propname):
        props = get_outfit_properties()
        ob = data
        vgroup = item
        icon = self.get_icon_value("GROUP_VERTEX")
        try:
            category = get_outfit_properties().YAS_BONES[vgroup.name]
        except:
            category = "Unknown"
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if len(props.yas_vgroups) == 1 and "has no " in vgroup.name:
                error = self.get_icon_value("INFO")
                layout.prop(vgroup, "name", text="", emboss=False, icon_value=error)
                layout.alignment = "CENTER"
            else:
                layout.prop(vgroup, "name", text=category, emboss=False, icon_value=icon)
                icon = 'LOCKED' if vgroup.lock_weight else 'UNLOCKED'
                layout.prop(vgroup, "lock_weight", text="", icon=icon, emboss=False)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)
    
    def get_icon_value(self, icon_name: str) -> int:
        icon_items = UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.items()
        icon_dict = {tup[1].identifier : tup[1].value for tup in icon_items}

        return icon_dict[icon_name]

class MESH_UL_shape(UIList):
    bl_idname = "MESH_UL_shape"

    def draw_item(self, context, layout:UILayout, data, item:VertexGroup, icon, active_data, active_propname):
        ob = data
        shape = item
        sizes = ["LARGE", "MEDIUM", "SMALL"]
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if shape.name.isupper() and not any(shape.name == size for size in sizes):
                layout.prop(shape, "name", text="", emboss=False, icon_value=self.get_icon_value("REMOVE"))
            else:
                layout.prop(shape, "name", text="", emboss=False, icon_value=icon)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)
    
    def get_icon_value(self, icon_name: str) -> int:
        icon_items = UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.items()
        icon_dict = {tup[1].identifier : tup[1].value for tup in icon_items}

        return icon_dict[icon_name]


CLASSES = [
    MESH_UL_yas,
    MESH_UL_shape,
] 