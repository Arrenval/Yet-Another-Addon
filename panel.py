from bpy.types import Panel

def dynamic_column_operators(columns, layout, labels):
    box = layout.box()
    row = box.row(align=True)

    columns_list = [row.column(align=True) for _ in range(columns)]

    for index, (name, (operator, depress)) in enumerate(labels.items()):
            
        col_index = index % columns 
        
        columns_list[col_index].operator(operator, text=name, depress=depress)

    return box  

def dropdown_header(self, button, section_prop, prop_str=str, label=str, extra_icon=""):
    layout = self.layout
    row = layout.row(align=True)
    split = row.split(factor=1)
    box = split.box()
    sub = box.row(align=True)
    sub.alignment = 'LEFT'

    icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
    sub.prop(section_prop, prop_str, text="", icon=icon, emboss=False)
    sub.label(text=label)
    if extra_icon != "":
        sub.label(icon=extra_icon)
    
    return box

class Tools(Panel):
    bl_idname = "VIEW3D_PT_YA_Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "Weights"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 1
    
    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator("ya.remove_empty_vgroups", text= "Remove Empty Groups")



          
classes = [
    Tools,
]