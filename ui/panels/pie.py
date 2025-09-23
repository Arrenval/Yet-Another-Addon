import bpy

from bpy.types import Operator, UILayout, Menu


class FlowPie(Menu):
    bl_idname = "YA_MT_flow_direction_pie"
    bl_label = "Flow Direction"

    @classmethod
    def poll(cls, context):
        if context.space_data.type != 'IMAGE_EDITOR':
            return False
        
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
            
        if context.active_object.mode != 'EDIT':
            return False
            
        if not context.active_object.data.uv_layers:
            return False
            
        return True
    
    def draw(self, context):
        pie = self.layout.menu_pie()
        angles = [180, 0, 270, 90, 135, 45, 225, 315]

        for angle in angles:
            pie.operator("ya.set_flow", text=f"{str(angle):>16}°").angle = angle


CLASSES = [
    FlowPie
]