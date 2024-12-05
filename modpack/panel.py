import bpy

from pathlib       import Path
from bpy.types     import Panel

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
    
    if len(bpy.context.scene.fbx_subfolder) > 1:
        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Subfolder:")
        split.prop(section_prop, "fbx_subfolder", text="") 
        row.label(icon="FOLDER_REDIRECT") 

    if devkit:
        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.label(text="")
        split.operator("ya.directory_copy", text="Copy from Export") 

    box = layout.box()
    row = box.row(align=True)
    row.prop(section_prop, "button_modpack_replace", text="New", icon="FILE_NEW", invert_checkbox=True)
    row.prop(section_prop, "button_modpack_replace", text="Update", icon="CURRENT_FILE",)

    box.separator(factor=0.5,type="LINE")

    if section_prop.button_modpack_replace:

        row = box.row(align=True)
        split = row.split(factor=0.25)
        col2 = split.column(align=True)
        col2.label(text="Ver.")
        col2.prop(section_prop, "loadmodpack_version", text="")

        col = split.column(align=True)
        col.label(text="Modpack:")
        col.prop(section_prop, "loadmodpack_display_directory", text="", emboss=False)

        split2 = row.split(factor=0.8)
        col3 = split2.column()
        col3.alignment = "CENTER"
        col3.operator("ya.pmp_selector", icon="FILE_FOLDER", text="")
        col3.prop(section_prop, "loadmodpack_author", text="by", emboss=False)

        if Path(section_prop.loadmodpack_directory).is_file():
            selection = section_prop.modpack_groups

            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            text = "Create:" if selection == "0" else "Replace:"
            split.label(text=text)
            split.prop(section_prop, "modpack_groups", text="")
            sub = row.row(align=True)
            sub.alignment = "RIGHT"
            if selection != "0":
                sub.prop(section_prop, "modpack_ui_page", emboss=False)
            else:
                sub.prop(section_prop, "modpack_page", emboss=True)

            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="Name:")
            split.prop(section_prop, "modpack_rename_group", text="")
            sub = row.row(align=True)
            sub.alignment = "RIGHT"
            sub.prop(section_prop, "mod_group_type", text="")
        else:
            row = box.row(align=True)

    else:

        row = box.row(align=True)
        split = row.split(factor=0.25)
        col2 = split.column(align=True)
        col2.label(text="Ver.")
        col2.prop(section_prop, "new_mod_version", text="")

        col = split.column(align=True)
        col.label(text="Mod Name:")
        col.prop(section_prop, "new_mod_name", text="")
        
        split2 = row.split(factor=0.8)
        col3 = split2.column(align=True)
        col3.alignment = "CENTER"
        col3.label(text="Author:")
        col3.prop(section_prop, "author_name", text="")

        row = box.row(align=True)
        split = row.split(factor=0.25)
        col3 = split.column(align=True)
        col3.alignment = "RIGHT"
        col3.label(text="Group:")

        
        col2 = split.column(align=True)
        col2.prop(section_prop, "modpack_rename_group", text="")

        split2 = row.split(factor=0.8)
        col = split2.column(align=True)
        col.alignment = "CENTER"
        col.prop(section_prop, "mod_group_type", text="")



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
    bl_label = "Modpack"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        section_prop = context.scene.pmp_props

        draw_modpack(self, layout, section_prop)


classes = [
    ModpackManager
]