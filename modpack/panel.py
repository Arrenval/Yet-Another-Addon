from bpy.types import Panel

def draw_modpack(self, layout, section_prop, devkit=False):
    row = layout.row(align=True)
    split = row.split(factor=0.65, align=True)
    icon = "CHECKMARK" if section_prop.consoletools_status == "ConsoleTools Ready!" else "X"
    split.label(text=section_prop.consoletools_status, icon=icon)
    split.operator("ya.file_console_tools", text="Check")
    row.operator("ya.consoletools_dir", icon="FILE_FOLDER", text="")

    layout.separator(factor=0.5,type="LINE")

    row = layout.row(align=True)
    split = row.split(factor=0.25, align=True)
    split.alignment = "RIGHT"
    split.label(text="Model:")
    split.prop(section_prop, "game_model_path", text="")
    model_path = section_prop.game_model_path
    icon = "CHECKMARK" if model_path.startswith("chara") or model_path.endswith("mdl") else "X"
    row.label(icon=icon)
    
    row = layout.row(align=True)
    split = row.split(factor=0.25, align=True)
    split.alignment = "RIGHT"
    split.label(text="FBX:")
    split.prop(section_prop, "savemodpack_display_directory", text="")
    
    row.operator("ya.modpack_dir_selector", icon="FILE_FOLDER", text="").category = "savemodpack"

    if devkit:
        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.label(text="")
        split.operator("ya.directory_copy", text="Copy from Export") 

    box = layout.box()
    row = box.row(align=True)
    row.prop(section_prop, "button_modpack_replace", text="New", icon="FILE_NEW", invert_checkbox=True)
    row.prop(section_prop, "button_modpack_replace", text="Update", icon="CURRENT_FILE",)

    if section_prop.button_modpack_replace:
        
        row = box.row()
        split = row.split(factor=0.33)
        col2 = split.column(align=True)
        col2.label(text="Ver.")
        col2.prop(section_prop, "loadmodpack_version", text="")
        col = split.column(align=True)
        col.label(text="Modpack:")
        col.prop(section_prop, "loadmodpack_display_directory", text="", emboss=False)
        split2 = row.split(factor=0.8)
        col3 = split2.column(align=True)
        col3.alignment = "CENTER"
        col3.label(text="")
        col3.prop(section_prop, "loadmodpack_author", text="by", emboss=False)

    
        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.label(text="")
        split.operator("ya.pmp_selector", icon="FILE_FOLDER", text="Choose Modpack")
        
        
        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Replace:")
        split.prop(section_prop, "modpack_groups", text="")

        row = box.row()
        split = row.split(factor=0.25)
        col2 = split.column(align=True)
        if section_prop.modpack_groups == "0":
            col2.prop(section_prop, "mod_group_type", text="")
        else:
            text = "" if section_prop.modpack_groups == "0" else "Rename:"
            col2.alignment = "RIGHT"
            col2.label(text=text)
        col = split.column(align=True)
        col.prop(section_prop, "modpack_rename_group", text="")
    
    else:
        

        row = box.row()
        split = row.split(factor=0.25)
        col2 = split.column(align=True)
        col2.label(text="Ver.")
        col2.prop(section_prop, "new_mod_version", text="")
        col = split.column(align=True)
        col.label(text="Mod Name:")
        col.prop(section_prop, "new_mod_name", text="")

        row = box.row()
        split = row.split(factor=0.25)
        col2 = split.column(align=True)
        col2.label(text="Type:")
        col2.prop(section_prop, "mod_group_type", text="")
        col = split.column(align=True)
        col.label(text="Group Name:")
        col.prop(section_prop, "modpack_rename_group", text="")

        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Author:")
        split.prop(section_prop, "author_name", text="")



    row = box.row(align=True)
    row.operator("ya.file_modpacker", text="Convert & Pack").preset = "convert_pack"
    row.operator("ya.file_modpacker", text="Convert").preset = "convert"
    row.operator("ya.file_modpacker", text="Pack").preset = "pack"

    box.separator(factor=0.5, type="LINE")

    row = box.row(align=True)
    split = row.split(factor=0.25, align=True)
    split.alignment = "RIGHT"
    split.label(text="Status:")
    split.prop(section_prop, "modpack_progress", text="", emboss=False)

    box.separator(factor=0.1)

class ModpackManager(Panel):
    bl_idname = "VIEW3D_PT_YA_Modpack"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "File Manager"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        section_prop = context.scene.pmp_props

        draw_modpack(self, layout,section_prop)


classes = [
    ModpackManager
]