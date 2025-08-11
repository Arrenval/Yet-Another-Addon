from bpy.types import Panel

from ..draw    import aligned_row
from ...props  import get_window_properties


class AddSymmetryGroups(Panel):
    bl_label = "Symmetry Groups"
    bl_idname = "DATA_PT_YA_add_symmetry"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_parent_id = "DATA_PT_vertex_groups"
    
    def draw(self, context):
        layout = self.layout
        props = get_window_properties()
        aligned_row(layout, "Right Suffx:", "sym_group_r", props)
        aligned_row(layout, "Left Suffx:", "sym_group_l", props)
        split = layout.split(factor=0.25, align=True)
        split.label(text="")
        split.operator("ya.add_symmetry_vgroup", text="Add Missing Groups")


CLASSES = [
    AddSymmetryGroups
]   