import os
import bpy

from bpy.types import AddonPreferences, PropertyGroup, Context
from bpy.props import StringProperty, IntProperty, BoolProperty, CollectionProperty, EnumProperty


class ModpackOptionPreset(PropertyGroup):
    name: StringProperty(name="", description="Name of preset") # type: ignore
    preset: StringProperty(name="", description="JSON serialised preset") # type: ignore

class YetAnotherPreference(AddonPreferences):
    # This must match the add-on name, use `__package__`
    # when defining this for add-on extensions or a sub-module of a python package.
    
    bl_idname = __package__

    modpack_presets: CollectionProperty(
        type=ModpackOptionPreset
        ) # type: ignore
    
    # modpack_presets_select: EnumProperty(
    #     type=ModpackOptionPreset
    #     ) # type: ignore
    
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
        prop = context.scene.file_props
        actual_prop = f"{category}_dir"
        display_prop = f"{category}_display_dir"

        display_dir = getattr(prop, display_prop, "")

        if os.path.exists(display_dir):  
            setattr(prop, actual_prop, display_dir)

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

    def draw(self, context):
        pass
        layout = self.layout
        layout_split = layout.split(factor=0.5, align=True)

        left_col = layout_split.column(align=True)
        box = left_col.box()
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Export:")

        box.separator(type="LINE")

        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="")

        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="File Export:")
        split.prop(self, "export_dir", text="")
        row.operator("ya.dir_selector", text="", icon="FILE_FOLDER")

        box.separator(type="LINE")

        split = box.split(factor=0.25)
        split.prop(self, "ya_sort", text="Yet Another Sort", icon="CHECKMARK" if self.ya_sort else "X")

        right_col = layout_split.column(align=True)
        box = right_col.box()
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Modpack:")
        
        box.separator(type="LINE")

        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="ConsoleTools:")
        split.prop(self, "textools_directory", text="")
        row.operator("ya.consoletools_dir", text="", icon="FILE_FOLDER")

        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Mod Output:")
        split.prop(self, "modpack_output_dir", text="")
        row.operator("ya.modpack_dir_selector", text="", icon="FILE_FOLDER")

        box.separator(type="LINE")

        split = box.split(factor=0.25)
        split.prop(self, "ya_sort", text="Yet Another Sort", icon="CHECKMARK" if self.ya_sort else "X")
        split.label(text="Sorts model sizes according to Yet Another Standard.")

        # layout.label(text="This is a preferences view for our add-on")
        # layout.prop(self, "filepath")
        # layout.prop(self, "number")

def get_preferences() -> YetAnotherPreference:
    """Get Yet Another Preference"""
    return bpy.context.preferences.addons[__package__].preferences

        
CLASSES = [
    ModpackOptionPreset,
    YetAnotherPreference
]