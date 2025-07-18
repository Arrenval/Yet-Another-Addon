from bpy.types import Context, Panel, UILayout

from ..draw import aligned_row, ui_category_buttons
from ...properties import get_window_properties


class FileUtilities(Panel):
    bl_idname = "VIEW3D_PT_YA_Utilities"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "XIV Kit"
    bl_label = "Utilities"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 4

    def draw(self, context:Context):
        self.window = get_window_properties()
        layout = self.layout

        self.options ={
            "File": "FILE",
            "Phyb": "PHYSICS",
            "Model": "OUTLINER_OB_MESH",
            }

        row = layout.row()
        tab_col = row.column()
        ui_category_buttons(tab_col, self.window, self.options, "ya.inspector_category")

        main_col = row.box().column()

        if self.window.phyb_category:
            self.draw_phyb(main_col)
        else:
            row = main_col.split(factor=1.0, align=True).row(align=True)
            row.alignment = "CENTER"
            row.label(text="Check back later.", icon='INFO')
            pass
    
    def draw_overview(self, layout: UILayout) -> None:
        pass

    def draw_phyb(self, layout: UILayout) -> None:
        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Phybs", icon='PHYSICS')

        layout.separator(type="LINE", factor=2)

        row = aligned_row(layout, "Base Phyb:", "insp_file_first", self.window)
        row.operator("ya.file_selector", text="", icon="FILE_FOLDER").category = "INSP_ONE"
        row = aligned_row(layout, "Simulators:", "insp_file_sec", self.window)
        row.operator("ya.file_selector", text="", icon="FILE_FOLDER").category = "INSP_TWO"

        split = layout.split(factor=0.25, align=True)
        split.label(text="")
        split.operator("ya.phyb_append", text="Append")
        split.operator("ya.phyb_append", text="Collision").collision_check = True

        layout.separator()

               
CLASSES = [
    FileUtilities
]