import os
import bpy
import platform

from .ui.draw  import aligned_row, get_conditional_icon, operator_button
from bpy.types import AddonPreferences, PropertyGroup, Context, UILayout
from bpy.props import StringProperty, IntProperty, BoolProperty, CollectionProperty, EnumProperty


class ModpackOptionPreset(PropertyGroup):
    name   : StringProperty(name="", description="Name of preset") # type: ignore
    format : StringProperty(name="", description="Type of preset") # type: ignore
    options: StringProperty(name="", description="JSON serialised preset") # type: ignore

class YetAnotherPreference(AddonPreferences):
    # This must match the add-on name, use `__package__`
    # when defining this for add-on extensions or a sub-module of a python package.
    
    bl_idname = __package__

    modpack_presets: CollectionProperty(
        type=ModpackOptionPreset,
        ) # type: ignore
    
    def get_preset_enums(self):
        if len(self.modpack_presets) > 0:
            return [(str(idx), entry.name, "") for idx, entry in enumerate(self.modpack_presets)]
        else:
            return [("None", "No Presets", "")]
    
    modpack_preset_select: EnumProperty(
        name="Option Presets",
        description="Select a preset to apply to your mod group",
        items=lambda self, context: self.get_preset_enums()
        ) # type: ignore
    
    textools_directory: StringProperty(
        name="ConsoleTools Directory",
        default="Select ConsoleTools.exe...", 
        maxlen=255,
        options={'HIDDEN'},
        
        )  # type: ignore
    
    consoletools_status: BoolProperty(
        default=False,
        )  # type: ignore
    
    def update_directory(self, context:Context, category:str) -> None:
        actual_prop = f"{category}_dir"
        display_prop = f"{category}_display_dir"

        display_dir = getattr(self, display_prop, "")

        if os.path.exists(display_dir):  
            setattr(self, actual_prop, display_dir)

    modpack_output_display_dir: StringProperty(
        name="",
        default="Select an output folder...",
        description="Mod export location", 
        maxlen=255,
        update=lambda self, context: self.update_directory(context, 'modpack_output')
        )  # type: ignore
    
    modpack_output_dir: StringProperty(
        default="Select an output folder...",
        description="Mod export location", 
        maxlen=255,
        )  # type: ignore
    
    export_display_dir: StringProperty(
        name="Export Folder",
        default="Select an export directory...",  
        maxlen=255,
        update=lambda self, context: self.update_directory(context, 'export'),
        ) # type: ignore
    
    export_dir: StringProperty(
        name="",
        default="Select an export directory...",
        maxlen=255,
        )  # type: ignore
    
    ya_sort: BoolProperty(
        name="Yet Another Sort",
        description="When enabled the modpacker sorts model YAB sizes according to my regular packing format",
        default=True,
        ) # type: ignore

    def draw(self, context: Context):
        layout = self.layout
        layout_split = layout.split(factor=0.5, align=True)

        left_col = layout_split.column(align=True)
        export_box = left_col.box()

        self.draw_export(export_box, context)

        preset_box = left_col.box()
    
        self.draw_presets(preset_box, context)
        
        right_col = layout_split.column(align=True)
        modpack_box = right_col.box()

        self.draw_modpack(modpack_box, context)

    def draw_modpack(self, layout: UILayout, context: Context):
        options = [
            (self, "ya_sort", get_conditional_icon(self.ya_sort), 
            "Yet Another Sort", "Sorts model sizes according to Yet Another Standard."),
        ]

        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Modpack:")
        
        layout.separator(type="LINE")

        if platform.system() == "Windows":
            text = "✓  ConsoleTools Ready!" if self.consoletools_status else "✕  ConsoleTools missing."
            row = aligned_row(layout, "", text)
            row.operator("ya.file_console_tools", text="Check")

            row = aligned_row(layout, "ConsoleTools:", "textools_directory", self)
            row.operator("ya.consoletools_dir", text="", icon="FILE_FOLDER")

        row = aligned_row(layout, "Mod Output:", "modpack_output_dir", self)
        row.operator("ya.modpack_dir_selector", text="", icon="FILE_FOLDER")

        layout.separator(type="LINE")

        self.option_rows(layout, options)
        
        layout.separator(type="SPACE")
  
    def draw_export(self, layout: UILayout, context: Context):
        options = [
            (None, "", "", "", ""),
        ]

        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Export:")

        layout.separator(type="LINE")

        if platform.system() == "Windows":
            layout.label(text="") 

        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="File Export:")
        split.prop(self, "export_dir", text="")
        row.operator("ya.dir_selector", text="", icon="FILE_FOLDER")

        if platform.system() == "Windows":
            layout.label(text="")

        layout.separator(type="LINE")

        self.option_rows(layout, options)

        layout.separator(type="SPACE")

    def draw_presets(self, layout: UILayout, contex: Context):
        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Presets:")

        layout.separator(type="LINE")

        if len(self.modpack_presets) == 0:
            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(text="You currently have no presets.", icon="INFO")

        for idx, preset in enumerate(self.modpack_presets):
            if preset.type != self.modpack_presets[idx -1].type:
                layout.separator(type="LINE")

            row = aligned_row(layout, preset.format.capitalize(), "name", preset)

            op_atr = {
            "delete":       True,
            "settings":     True,
            "preset_idx":   idx,
            }
            
            operator_button(row, "ya.modpack_presets", icon="TRASH", attributes=op_atr)
            
            subrow = row.row(align=True)
            subrow.scale_x = 2.2
            subrow.label(text="", icon="BLANK1")
        
        layout.separator(type="SPACE")
            
    def option_rows(self, layout:UILayout, options:list):
        for (prop, attr, button_icon, button_text, label) in options:
            if prop is None:
                layout.label(text="")
                continue
            split = layout.split(factor=0.25)
            split.prop(prop, attr, text=button_text, icon=button_icon)
            split.label(text=label)

def get_prefs() -> YetAnotherPreference:
    """Get Yet Another Preference"""
    return bpy.context.preferences.addons[__package__].preferences

        
CLASSES = [
    ModpackOptionPreset,
    YetAnotherPreference
]
