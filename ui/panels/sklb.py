from bpy.types      import Context, Panel

from ..draw         import aligned_row, header_category
from ...props       import Armature, get_window_props, get_skeleton_props
from ...props.enums import get_racial_name


class SkelUtilities(Panel):
    bl_idname      = "VIEW3D_PT_YA_Skeleton"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "XIV Kit"
    bl_label       = "Skeleton"
    bl_options     = {'DEFAULT_CLOSED'}
    bl_order       = 5

    def draw(self, context: Context):
        self.props  = get_skeleton_props()
        self.window = get_window_props()
        layout = self.layout
        ui_tab = self.window.skeleton.ui_tab

        options ={
            "IO":  "IMPORT",
            "CONFIG":  "ARMATURE_DATA",
            "COMBINE": "GROUP_BONE",
            }

        button_row = header_category(layout, ui_tab, options[ui_tab])
        button_row.prop(self.window.skeleton, "ui_tab", expand=True, text="")

        obj = context.active_object
        if ui_tab == 'CONFIG':
            if not obj and obj != 'ARMATURE':
                aligned_row(layout, "Active:", attr="No Armature Selected.")
                return
            
            aligned_row(layout, "Active:", attr=obj.name)
            
            layout.separator(factor=0.5, type='LINE')

            armature: Armature = obj.data
            aligned_row(layout, "Race:", attr="race_id", prop=armature.kaos)
            
            if armature.kaos.mappers:
                layout.separator(factor=0.5, type='LINE')

            for mapper in armature.kaos.mappers:
                aligned_row(layout, "Parent:", attr=f"  {get_racial_name(mapper.race_id)}")

            layout.separator(factor=0.5, type='LINE')

            aligned_row(layout, "Bones:", attr=f"  {len(armature.kaos.bone_list)}")
            aligned_row(layout, "Layers:", attr=f"  {len(armature.kaos.anim_layers)}")

            layout.separator(factor=0.5, type='LINE')

            layout.operator("ya.sklb_config", text="Configure")
        
        elif ui_tab == 'COMBINE':
            layout.prop(self.window.skeleton, "combine_tab", expand=True, text=" ")

            layout.separator(factor=0.5, type='LINE')

            if self.window.skeleton.combine_tab == 'SELECT':
                if not obj and obj != 'ARMATURE':
                    aligned_row(layout, "Base:", attr="No Armature Selected.")
                    return
                
                aligned_row(layout, "Base:", attr=obj.name)
                aligned_row(layout, "Source:", attr="source", prop=self.props)
            else:
                aligned_row(layout, "Base:", attr="base_prefix", prop=self.window.skeleton)
                aligned_row(layout, "Source:", attr="source_prefix", prop=self.window.skeleton)

            row = layout.row(align=True)
            row.prop(self.window.skeleton, "scale_bones", text="", icon='FIXED_SIZE')
            row.operator("ya.sklb_combine", text="Combine")

        else:
            row = layout.row(align=True)
            row.operator("ya.sklb_import", text="Import")
            row.operator("ya.sklb_export", text="Export")

               
CLASSES = [
    SkelUtilities
]