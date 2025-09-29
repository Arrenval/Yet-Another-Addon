import os
import bpy
import rna_keymap_ui

from typing         import TYPE_CHECKING
from bpy.types      import AddonPreferences, PropertyGroup, Context, UILayout, KeyMap, KeyMapItem
from bpy.props      import StringProperty, BoolProperty, CollectionProperty, EnumProperty, PointerProperty
     
from .ui.draw       import aligned_row, get_conditional_icon, operator_button


_keymaps: dict[str, tuple[KeyMap, KeyMapItem]] = {}

class ModpackOptionPreset(PropertyGroup):
    name  : StringProperty(name="", description="Name of preset") # type: ignore
    format: StringProperty(name="", description="Type of preset") # type: ignore
    preset: StringProperty(name="", description="JSON serialised preset") # type: ignore

    if TYPE_CHECKING:
        name  : str
        format: str
        preset: str

class MenuSelect(PropertyGroup):
    def register_outfit_panel(self, context) -> None:
        from .ui.panels.studio import MeshStudio

        if self.outfit_panel:
            bpy.utils.register_class(MeshStudio)
        else:
            bpy.utils.unregister_class(MeshStudio)

    def register_file_panel(self, context) -> None:
        from .ui.panels.file import FileManager

        if self.file_panel:
            bpy.utils.register_class(FileManager)
        else:
            bpy.utils.unregister_class(FileManager)
    
    def register_util_panel(self, context) -> None:
        from .ui.panels.utilities import FileUtilities

        if self.util_panel:
            bpy.utils.register_class(FileUtilities)
        else:
            bpy.utils.unregister_class(FileUtilities)

    def register_sym_panel(self, context) -> None:
        from .ui.panels.v_groups import AddSymmetryGroups

        if self.sym_panel:
            bpy.utils.register_class(AddSymmetryGroups)
        else:
            bpy.utils.unregister_class(AddSymmetryGroups)

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

    util_panel: BoolProperty(
        name="",
        description="Show Utilities",
        default=False,
        update=register_util_panel
        ) # type: ignore
    
    sym_panel: BoolProperty(
        name="",
        description="Located under the Vertex Group list",
        default=True,
        update=register_sym_panel
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
        util_panel  : bool
        weight_menu : bool
        mod_button  : bool

class ExportPrefs(PropertyGroup):
    def update_directory(self, context: Context) -> None:
        actual_prop =  "output_dir"
        display_prop = "display_dir"

        display_dir = getattr(self, display_prop, "")

        if os.path.exists(display_dir):  
            setattr(self, actual_prop, display_dir)

    display_dir: StringProperty(
        name="Export Folder",
        default="Select an export directory...",  
        maxlen=255,
        update=update_directory,
        ) # type: ignore
    
    output_dir: StringProperty(
        name="",
        default="Select an export directory...",
        maxlen=255,
        )  # type: ignore

    if TYPE_CHECKING:
        display_dir        : str
        output_dir         : str

class YetAnotherPreference(AddonPreferences):
    bl_idname = __package__

    modpack_presets: CollectionProperty(
        type=ModpackOptionPreset,
        ) # type: ignore
    
    menus : PointerProperty(
        type=MenuSelect,
        ) # type: ignore
    
    export: PointerProperty(
        type=ExportPrefs,
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
    
    pref_menu: EnumProperty(
        name="Preferences Menu",
        description="Select a category",
        items=[
            ('GENERAL', "General", ""),
            ('KEY', "Keymap/Presets", "")
        ]
        ) # type: ignore
    
    def update_directory(self, context: Context, category: str) -> None:
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
    
    auto_cleanup: BoolProperty(
        name="Auto Cleanup",
        description="Cleans up imported files automatically with your current settings",
        default=True,
        ) # type: ignore
    
    remove_nonmesh: BoolProperty(
        name="Cleanup",
        description="Removes non-mesh objects. Typically leftover objects from FBX imports or skeletons",
        default=True,
        ) # type: ignore
    
    update_material: BoolProperty(
        name="Cleanup",
        description="Changes material rendering and enables backface culling. Tries to adjust metallic and roughness values of TT materials",
        default=True,
        ) # type: ignore
    
    reorder_meshid: BoolProperty(
        name="Cleanup",
        description="Moves mesh identifier to the front of the object name",
        default=True,
        ) # type: ignore
    
    armature_vis_anim: BoolProperty(
        name="Hide Armature",
        description="Controls whether armatures are hidden during animation playback",
        default=True,
        ) # type: ignore

    if TYPE_CHECKING:
        modpack_presets: list[ModpackOptionPreset]
        menus          : MenuSelect
        export         : ExportPrefs

        modpack_output_display_dir: str
        modpack_output_dir        : str

        auto_cleanup   : bool
        remove_nonmesh : bool
        update_material: bool
        reorder_meshid : bool

    def draw(self, context: Context):
        layout       = self.layout
        row          = layout.row(align=True)
        row.prop(self, "pref_menu", text="Menu", expand=True)

        layout_split = layout.split(factor=0.5, align=True)
        left_col     = layout_split.column(align=True)
        right_col    = layout_split.column(align=True)

        if self.pref_menu == 'GENERAL':
            options_box = left_col.box()
            self.draw_options(options_box)

            panel_box = right_col.box()
            self.draw_menus(panel_box)

            modpack_box = right_col.box()
            self.draw_directories(modpack_box)

        elif self.pref_menu == 'KEY':
            keymap_box = left_col.box()
            self.draw_keymaps(keymap_box)

            preset_box = right_col.box()
            self.draw_presets(preset_box)

    def draw_directories(self, layout: UILayout) -> None:
        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Directories:")
        
        row = aligned_row(layout, "Model:", "output_dir", self.export)
        row.operator("ya.dir_selector", text="", icon="FILE_FOLDER").category = "export"
        row = aligned_row(layout, "Modpack:", "modpack_output_dir", self)
        row.operator("ya.modpack_dir_selector", text="", icon="FILE_FOLDER").category = "OUTPUT_PMP"

        layout.separator(type="SPACE")
    
    def draw_keymaps(self, layout: UILayout) -> None:
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.user

        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Keymaps:")

        layout.separator(type="LINE")
        for km, kmi in _keymaps.values():
            row = layout.row(align=True)
            rna_keymap_ui.draw_kmi(['ADDON', 'USER', 'DEFAULT'], kc, km, kmi, row, 0)

    def draw_presets(self, layout: UILayout) -> None:
        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Presets:")

        layout.separator(type="LINE")

        if len(self.modpack_presets) == 0:
            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(text="You currently have no presets.", icon="INFO")

        for idx, preset in enumerate(self.modpack_presets):
            if preset.format != self.modpack_presets[idx - 1].format:
                layout.separator(type="LINE")

            row = aligned_row(layout, preset.format.capitalize(), "name", preset)

            op_atr = {
            "delete":       True,
            "settings":     True,
            "preset_idx":   idx,
            }
            
            operator_button(row, "ya.preset_manager", icon="TRASH", attributes=op_atr)

    def draw_options(self, layout: UILayout) -> None:
        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Options:")
        options = [
            (self, "armature_vis_anim", self.armature_vis_anim, "Hide Armature", "Controls whether armatures are hidden during animation playback."),
        ]

        self.option_rows(layout.column(align=True), options)

        options = [
            (self, "auto_cleanup", self.auto_cleanup, "Auto Cleanup", "Cleans up imported files automatically with your current settings"),
            (self, "remove_nonmesh", self.remove_nonmesh, "Remove Non-Mesh", "Removes non-mesh objects. Typically leftover objects from FBX imports or skeletons."),
            (self, "update_material", self.update_material, "Update Materials", "Changes material rendering and enables backface culling. Tries to adjust metallic and roughness values of TT materials."),
            (self, "reorder_meshid", self.reorder_meshid, "Mesh ID", "Moves mesh identifier to the front of the object name."),
        ]

        self.option_rows(layout.column(align=True), options)

    def draw_menus (self, layout: UILayout) -> None:
        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Menus:")

        options = [
            (self.menus, "outfit_panel", self.menus.outfit_panel, "Outfit Studio", "Panel containing various mod tools."),
            (self.menus, "file_panel", self.menus.file_panel, "File Manager", "Panel for import/export and modpacking tools."),
            (self.menus, "util_panel", self.menus.util_panel, "Utilities", "Panel with various file utilities."),
            (self.menus, "sym_panel", self.menus.sym_panel, "Sym Groups", "Panel under vertex group menu that can add missing symmetry groups."),
            ]

        self.option_rows(layout.column(align=True), options)

        options = [
            (self.menus, "weight_menu", self.menus.weight_menu, "Vertex Weights", "Vertex Group addition to quickly remove selected or empty vertex groups."),
            (self.menus, "mod_button", self.menus.mod_button, "Shape Key Modifiers", "Operator that helps apply modifiers to meshes with shape keys."),
        ]

        self.option_rows(layout.column(align=True), options)

    def option_rows(self, layout:UILayout, options:list):
        for (prop, attr, button_icon, button_text, label) in options:
            if prop is None:
                layout.label(text="")
                continue
            split = layout.split(factor=0.25)
            split.prop(prop, attr, text=button_text, icon=get_conditional_icon(button_icon))
            split.label(text=label)

def register_keymaps() -> None:
    global _keymaps
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    km  = kc.keymaps.new(name='UV Editor', space_type='EMPTY')
    kmi = km.keymap_items.new(
            'wm.call_menu_pie',           
            'F',                          
            'PRESS',                      
            ctrl=True,                 
        )
    kmi.properties.name = "YA_MT_flow_direction_pie"

    _keymaps["YA_MT_flow_direction_pie"] = (km, kmi)

def unregister_keymaps() -> None:
    global _keymaps

    for km, kmi in _keymaps.values():
        km.keymap_items.remove(kmi)
    _keymaps.clear()

def register_menus() -> None:
    from .ui.panels.pie       import CLASSES
    from .ui.panels.studio    import MeshStudio
    from .ui.panels.file      import FileManager
    from .ui.panels.utilities import FileUtilities
    from .ui.panels.v_groups  import AddSymmetryGroups
    from .ui.menu             import menu_vertex_group_append, draw_modifier_options

    menus = get_prefs().menus

    if menus.outfit_panel:
        bpy.utils.register_class(MeshStudio)
    if menus.file_panel:
        bpy.utils.register_class(FileManager)
    if menus.util_panel:
        bpy.utils.register_class(FileUtilities)
    if menus.sym_panel:
        bpy.utils.register_class(AddSymmetryGroups)
    if menus.weight_menu:
        bpy.types.MESH_MT_vertex_group_context_menu.append(menu_vertex_group_append)
    if menus.mod_button:
        bpy.types.DATA_PT_modifiers.append(draw_modifier_options)
    
    for cls in CLASSES:
        bpy.utils.register_class(cls)

def unregister_menus() -> None:
    from .ui.panels.pie       import CLASSES
    from .ui.panels.studio    import MeshStudio
    from .ui.panels.file      import FileManager
    from .ui.panels.utilities import FileUtilities
    from .ui.panels.v_groups  import AddSymmetryGroups
    from .ui.menu             import menu_vertex_group_append, draw_modifier_options

    menus = get_prefs().menus

    if menus.outfit_panel:
        bpy.utils.unregister_class(MeshStudio)
    if menus.file_panel:
        bpy.utils.unregister_class(FileManager)
    if menus.util_panel:
        bpy.utils.unregister_class(FileUtilities)
    if menus.sym_panel:
        bpy.utils.unregister_class(AddSymmetryGroups)
    if menus.weight_menu:
        bpy.types.MESH_MT_vertex_group_context_menu.remove(menu_vertex_group_append)
    if menus.mod_button:
        bpy.types.DATA_PT_modifiers.remove(draw_modifier_options)
    
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)

def get_prefs() -> YetAnotherPreference:
    """Get Yet Another Preference"""
    return bpy.context.preferences.addons[__package__].preferences

        
CLASSES = [
    ModpackOptionPreset,
    MenuSelect,
    ExportPrefs,
    YetAnotherPreference
]
