from bpy.types import Context, Panel

from ...ui.draw import aligned_row, ui_category_buttons
from ...properties import get_window_properties

class FileInspector(Panel):
    bl_idname = "VIEW3D_PT_YA_Inspector"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "XIV Kit"
    bl_label = "Inspector"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 4

    def draw(self, context:Context):
        self.window = get_window_properties()
        layout = self.layout

        self.options ={
            "File": "INFO",
            "Phyb": "SHAPEKEY_DATA",
            "Model": "OUTLINER_OB_MESH",
            }

        row = layout.row()
        tab_col = row.column()
        ui_category_buttons(tab_col, self.window, self.options, "ya.inspector_category")

        main_col = row.box().column()

        main_col.separator(factor=3)

        row = aligned_row(main_col, "Primary:", "insp_file_first", self.window)
        row.operator("ya.file_selector", text="", icon="FILE_FOLDER").category = "INSP_ONE"
        row = aligned_row(main_col, "Secondary:", "insp_file_sec", self.window)
        row.operator("ya.file_selector", text="", icon="FILE_FOLDER").category = "INSP_TWO"

        if self.window.file_category:
            split = main_col.split(factor=0.25)
            split.label(text="")
            split.operator("ya.file_inspector", text="Compare")
                
        if self.window.phyb_category:
            split = main_col.split(factor=0.25)
            split.label(text="")
            split.operator("ya.phyb_append", text="Append")

        main_col.separator()
            
        
CLASSES = [
    FileInspector
]