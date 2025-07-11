import os
import bpy
import platform

from typing    import TYPE_CHECKING
from bpy.types import AddonPreferences, PropertyGroup, Context, UILayout
from bpy.props import StringProperty, BoolProperty, CollectionProperty, EnumProperty, PointerProperty

from .ui.draw  import aligned_row, get_conditional_icon, operator_button


class ModpackOptionPreset(PropertyGroup):
    name   : StringProperty(name="", description="Name of preset") # type: ignore
    format : StringProperty(name="", description="Type of preset") # type: ignore
    preset: StringProperty(name="", description="JSON serialised preset") # type: ignore

class MenuSelect(PropertyGroup):
    def register_outfit_panel(self, context) -> None:
        from .ui.panels.outfit import OutfitStudio

        if self.outfit_panel:
            bpy.utils.register_class(OutfitStudio)
        else:
            bpy.utils.unregister_class(OutfitStudio)

    def register_file_panel(self, context) -> None:
        from .ui.panels.file import FileManager

        if self.file_panel:
            bpy.utils.register_class(FileManager)
        else:
            bpy.utils.unregister_class(FileManager)
    
    def register_inspector_panel(self, context) -> None:
        from .ui.panels.inspector import FileInspector

        if self.inspect_panel:
            bpy.utils.register_class(FileInspector)
        else:
            bpy.utils.unregister_class(FileInspector)

    outfit_panel: BoolProperty(
        name="",
        description="Show Outfit Studio",
        default=True,
        update=register_outfit_panel
        ) # type: ignore
    
    file_panel: BoolProperty(
        name="",
        description="Show File Manager",
        default=True,
        update=register_file_panel
        ) # type: ignore

    inspect_panel: BoolProperty(
        name="",
        description="Show Inspector",
        default=False,
        update=register_inspector_panel
        ) # type: ignore

    def register_weights(self, context) -> None:
        from .ui.menu import menu_vertex_group_append
        if self.weight_menu:
            bpy.types.MESH_MT_vertex_group_context_menu.append(menu_vertex_group_append)
        else:
            bpy.types.MESH_MT_vertex_group_context_menu.remove(menu_vertex_group_append)

    def register_mod_sk(self, context) -> None:
        from .ui.menu import draw_modifier_options
        if self.mod_button:
            bpy.types.DATA_PT_modifiers.append(draw_modifier_options)
        else:
            bpy.types.DATA_PT_modifiers.remove(draw_modifier_options)

    weight_menu: BoolProperty(
        name="",
        description="Located under the extended Vertex Group dropdown menu",
        default=True,
        update=register_weights
        ) # type: ignore
    
    mod_button: BoolProperty(
        name="",
        description="Located in the active object's Modifier tab",
        default=True,
        update=register_mod_sk
        ) # type: ignore
    
    if TYPE_CHECKING:
        outfit_panel: bool
        file_panel  : bool
        weight_menu : bool
        mod_button  : bool

class YetAnotherPreference(AddonPreferences):
    # This must match the add-on name, use `__package__`
    # when defining this for add-on extensions or a sub-module of a python package.
    
    bl_idname = __package__

    modpack_presets: CollectionProperty(
        type=ModpackOptionPreset,
        ) # type: ignore
    
    menus: PointerProperty(
        type=MenuSelect,
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
    
    auto_cleanup: BoolProperty(
        name="Auto Cleanup",
        description="Cleans up imported files automatically with your current settings",
        default=True,
        ) # type: ignore
    
    remove_nonmesh: BoolProperty(
        name="Cleanup",
        description="Removes objects without any meshes. Cleans up unnecessary files from TT imports",
        default=True,
        ) # type: ignore
    
    update_material: BoolProperty(
        name="Cleanup",
        description="Changes material rendering and enables backface culling. Tries to normalise metallic and roughness values of TT materials",
        default=True,
        ) # type: ignore
    
    reorder_meshid: BoolProperty(
        name="Cleanup",
        description="Moves mesh identifier to the front of the object name",
        default=True,
        ) # type: ignore

    if TYPE_CHECKING:
        modpack_presets: ModpackOptionPreset
        menus          : MenuSelect

        textools_directory : str
        consoletools_status: bool

        modpack_output_display_dir: str
        modpack_output_dir        : str
        export_display_dir        : str
        export_dir                : str

        auto_cleanup   : bool
        remove_nonmesh : bool
        update_material: bool
        reorder_meshid : bool

    def draw(self, context: Context):
        layout = self.layout
        layout_split = layout.split(factor=0.5, align=True)

        left_col = layout_split.column(align=True)
        right_col = layout_split.column(align=True)

        export_box = left_col.box()
        self.draw_export(export_box, context)

        modpack_box = left_col.box()

        self.draw_modpack(modpack_box, context)

        panel_box = right_col.box()

        row = panel_box.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Menus:")

        split = panel_box.split(factor=0.25)
        button_col = split.column(align=True)
        label_col = split.column(align=True)

        button_col.prop(self.menus, "outfit_panel", text="Outfit Studio", icon=get_conditional_icon(self.menus.outfit_panel))
        label_col.label(text="Panel containing various mod tools")

        button_col.prop(self.menus, "file_panel", text="File Manager", icon=get_conditional_icon(self.menus.outfit_panel))
        label_col.label(text="Panel for import/export and modpacking tools")

        button_col.prop(self.menus, "inspect_panel", text="Inspector", icon=get_conditional_icon(self.menus.inspect_panel))
        label_col.label(text="Panel with various file utilities, WIP")

        button_col.separator(type='SPACE')
        label_col.separator(type='SPACE')

        button_col.prop(self.menus, "weight_menu", text="Vertex Weights", icon=get_conditional_icon(self.menus.weight_menu))
        label_col.label(text="Vertex Group menu addition to quickly remove selected or empty vertex groups")

        button_col.prop(self.menus, "mod_button", text="Shape Key Modifiers", icon=get_conditional_icon(self.menus.mod_button))
        label_col.label(text="Operator that helps apply modifiers to meshes with shape keys")

        right_col.separator(type='SPACE')

        preset_box = right_col.box()
        self.draw_presets(preset_box, context)

    def draw_modpack(self, layout: UILayout, context: Context):
        # options = [
        #     (None, "", "", "", ""),
        # ]

        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Modpack:")
        
        layout.separator(type="LINE")

        if platform.system() == "Windows":
            text = "✓  ConsoleTools Ready!" if self.consoletools_status else "X  ConsoleTools missing."
            row = aligned_row(layout, "", text)
            row.operator("ya.consoletools", text="Check")

            row = aligned_row(layout, "ConsoleTools:", "textools_directory", self)
            row.operator("ya.consoletools_dir", text="", icon="FILE_FOLDER")

        row = aligned_row(layout, "Mod Output:", "modpack_output_dir", self)
        row.operator("ya.modpack_dir_selector", text="", icon="FILE_FOLDER").category = "OUTPUT_PMP"

        # layout.separator(type="LINE")

        # self.option_rows(layout, options)
        
        layout.separator(type="SPACE")
  
    def draw_export(self, layout: UILayout, context: Context):
        # options = [
        #     (None, "", "", "", ""),
        # ]

        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Export:")

        layout.separator(type="LINE")

        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="File Export:")
        split.prop(self, "export_dir", text="")
        row.operator("ya.dir_selector", text="", icon="FILE_FOLDER")

        # layout.separator(type="LINE")

        # self.option_rows(layout, options)

        layout.separator(type='SPACE')

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


def register_menus() -> None:
    from .ui.panels.outfit    import OutfitStudio
    from .ui.panels.file      import FileManager
    from .ui.panels.inspector import FileInspector
    from .ui.menu             import menu_vertex_group_append, draw_modifier_options

    if get_prefs().menus.outfit_panel:
        bpy.utils.register_class(OutfitStudio)
    if get_prefs().menus.file_panel:
        bpy.utils.register_class(FileManager)
    if get_prefs().menus.inspect_panel:
        bpy.utils.register_class(FileInspector)
    if get_prefs().menus.weight_menu:
        bpy.types.MESH_MT_vertex_group_context_menu.append(menu_vertex_group_append)
    if get_prefs().menus.mod_button:
        bpy.types.DATA_PT_modifiers.append(draw_modifier_options)

def unregister_menus() -> None:
    from .ui.panels.outfit    import OutfitStudio
    from .ui.panels.file      import FileManager
    from .ui.panels.inspector import FileInspector
    from .ui.menu             import menu_vertex_group_append, draw_modifier_options

    if get_prefs().menus.outfit_panel:
        bpy.utils.unregister_class(OutfitStudio)
    if get_prefs().menus.file_panel:
        bpy.utils.unregister_class(FileManager)
    if get_prefs().menus.inspect_panel:
        bpy.utils.unregister_class(FileInspector)
    if get_prefs().menus.weight_menu:
        bpy.types.MESH_MT_vertex_group_context_menu.remove(menu_vertex_group_append)
    if get_prefs().menus.mod_button:
        bpy.types.DATA_PT_modifiers.remove(draw_modifier_options)

def get_prefs() -> YetAnotherPreference:
    """Get Yet Another Preference"""
    return bpy.context.preferences.addons[__package__].preferences

        
CLASSES = [
    ModpackOptionPreset,
    MenuSelect,
    YetAnotherPreference
]
