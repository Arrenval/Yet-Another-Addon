
from bpy.types import Context, Panel

class FileInspector(Panel):
    bl_idname = "VIEW3D_PT_YA_Inspector"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "XIV Kit"
    bl_label = "Inspector"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 4

    def draw(self, context:Context):
        layout = self.layout
        layout.operator("ya.file_inspector", text="Load")

CLASSES = [
    FileInspector
]