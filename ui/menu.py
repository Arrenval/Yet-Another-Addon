from bpy.types import UILayout, Context

def menu_vertex_group_append(self, context: Context):
    layout: UILayout = self.layout
    layout.separator(type="LINE")
    layout.operator("ya.add_yas_vgroups", text= "Add YAS Groups")
    layout.separator(type="LINE")
    layout.operator("ya.remove_empty_vgroups", text="Remove Empty Vertex Groups")
    layout.operator("ya.remove_select_vgroups", text= "Remove Selected and Adjust Parent").preset = "MENU"

def draw_modifier_options(self, context: Context):
    layout: UILayout = self.layout
    if context.active_object.modifiers:
        layout.separator(type="LINE")
        layout.operator("ya.apply_modifier_sk", text="Apply with Shape Keys", icon="CHECKMARK")
        layout.operator("ya.modifier_flow", text="Add XIV Flow Modifier", icon='ADD')
   