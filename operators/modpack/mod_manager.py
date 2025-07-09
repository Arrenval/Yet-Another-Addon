import json
import gzip
import base64

from typing              import Any
from bpy.types           import Operator, Context
from bpy.props           import StringProperty, EnumProperty, BoolProperty, IntProperty
from ...ui.draw          import aligned_row, get_conditional_icon
from ...properties       import BlendModOption, BlendModGroup, get_file_properties, get_window_properties
from ...preferences      import get_prefs
from ...utils.typings    import Preset
from ...utils.serialiser import RNAPropertyIO


class ModpackManager(Operator):
    bl_idname = "ya.modpack_manager"
    bl_label = ""
    bl_description = ""
    bl_options = {"UNDO"}

    category: StringProperty() # type: ignore

    delete  : BoolProperty(default=False, options={"SKIP_SAVE"}) # type: ignore

    group : IntProperty(default=0, options={"SKIP_SAVE"}) # type: ignore
    option: IntProperty(default=0, options={"SKIP_SAVE"}) # type: ignore
    entry : IntProperty(default=0, options={"SKIP_SAVE"}) # type: ignore

    def get_user_input_items(self, context):
        base_items = [
            ("FILE_ENTRY", "File", ""),
            ("SHP_ENTRY", "Shape Key", ""),
            ("ATR_ENTRY", "Attribute", "")
        ]
        
        return base_items
    
    user_input: EnumProperty(
        name="",
        items=get_user_input_items
    ) # type: ignore

    @classmethod
    def description(cls, context, properties):
        if properties.delete == False:
            if properties.category in ("ENTRY", "COMBI_ENTRY"):
                return f"""Add Entry:
        *SHIFT click for file.
        *ALT click for shape key.
        *SHIFT + ALT click for attribute"""
            
            elif properties.category == "OPTION":
                return f"""Add {properties.category.capitalize()}. 
        *SHIFT click to add a correction option to a Combining group"""
            
            else:
                return f"Add {properties.category.capitalize()}"
            
        elif properties.category.endswith("_ENTRY"):
            return f"Hold CTRL to remove {properties.category[:3]}"
        
        else:
            return f"Hold CTRL to remove {properties.category.capitalize()}"
        
    def invoke(self, context:Context, event):
        if not event.ctrl and self.delete:
            return {'FINISHED'}
                
        self.prefs = get_prefs()
        self.props = get_window_properties()
        self.mod_groups: list[BlendModGroup] = self.props.pmp_mod_groups

        if self.category in ("ENTRY", "COMBI_ENTRY"):
            if event.shift and event.alt:
                self.category = f"ATR_{self.category.split('_')[0]}"

            elif event.shift:
                self.category = f"FILE_{self.category.split('_')[0]}"

            elif event.alt:
                self.category = f"SHP_{self.category.split('_')[0]}"
                
            else:
                context.window_manager.invoke_props_dialog(self, confirm_text="Confirm", title="", width=2)
                return {'RUNNING_MODAL'}
                
        elif self.category == "OPTION":
            mod_group = self.mod_groups[self.group]
            if event.shift and mod_group.group_type == "Combining":
                self.category = "COMBI"

        return self.execute(context)
    
    def draw(self, context):
        col = self.layout.column(align=True)
        col.prop(self, "user_input", expand=True, text="type")

    def execute(self, context:Context):
        self.prefs = get_prefs()
        self.props = get_window_properties()
        self.mod_groups: list[BlendModGroup] = self.props.pmp_mod_groups

        if self.category == "ENTRY":
            self.category = self.user_input
        elif self.category == "COMBI_ENTRY":
            if self.user_input.startswith("ATR"):
                self.category = f"ATR_{self.category.split('_')[0]}"

            elif self.user_input.startswith("FILE"):
                self.category = f"FILE_{self.category.split('_')[0]}"

            elif self.user_input.startswith("SHP"):
                self.category = f"SHP_{self.category.split('_')[0]}"

        self.group: int
        self.option: int
        
        if len(self.mod_groups) > 0:
            mod_group = self.mod_groups[self.group]
            group_options:list[BlendModOption] = mod_group.mod_options
        
        if self.delete:
            manager = RNAPropertyIO()

        match self.category:
            case "GROUP":
                if not self.delete:
                    new_group     = self.mod_groups.add()
                    new_group.idx = "New"
                else:
                    manager.remove(self.mod_groups, self.group)

            case "OPTION":
                if not self.delete:
                    new_option = group_options.add()
                    new_option.name = f"Option #{len(group_options)}"
                else:
                    manager.remove(group_options, self.option)

            case "COMBI":
                if not self.delete:
                    new_correction = mod_group.corrections.add()
                    new_correction.group_idx = self.group
                else:
                    manager.remove(mod_group.corrections, self.option)

            case "FILE_ENTRY" | "FILE_COMBI":
                
                if self.category.endswith("ENTRY"):
                    option_entries = group_options[self.option].file_entries
                else:
                    option_entries = mod_group.corrections[self.option].file_entries
                    print(len(option_entries))

                if not self.delete:
                    option_entries.add()
                else:
                    manager.remove(option_entries, self.entry)

            case "SHP_ENTRY" | "ATR_ENTRY" | "SHP_COMBI" | "ATR_COMBI":

                if self.category.endswith("ENTRY"):
                    option_entries = group_options[self.option].meta_entries

                else:
                    option_entries = mod_group.corrections[self.option].meta_entries

                if not self.delete:
                    new_entry = option_entries.add()
                    new_entry.type = self.category[:3]
                    new_entry.manip_ref = "shpx_" if self.category[:3] == "SHP" else "atrx_"
                else:
                    manager.remove(option_entries, self.entry)

        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}
    
class ModpackPresets(Operator):
    bl_idname = "ya.preset_manager"
    bl_label = ""
    bl_description = ""

    bl_options = {"UNDO"}

    preset_name: StringProperty(default="Enter preset name...", options={"SKIP_SAVE"}) # type: ignore
    format     : StringProperty(options={"SKIP_SAVE", "OUTPUT_PATH"}) # type: ignore
    new_preset : BoolProperty(default=True, options={"SKIP_SAVE"}) # type: ignore
    
    settings  : BoolProperty(default=False, options={"SKIP_SAVE"}) # type: ignore
    delete    : BoolProperty(default=False, options={"SKIP_SAVE"}) # type: ignore

    group     : IntProperty(default=0, options={"SKIP_SAVE"}) # type: ignore
    preset_idx: IntProperty(default=0, options={"SKIP_SAVE"}) # type: ignore    
    
    @classmethod
    def description(cls, context, properties):
        if properties.settings:
            return "CTRL click to delete this preset"
        
        else: 
            return """Open preset manager:
    SHIFT click to apply from clipboard.
    ALT click to copy to clipboard"""

    def invoke(self, context: Context, event):
        if self.delete and not event.ctrl:
            return {"FINISHED"}
        
        self.prefs  = get_prefs()
        self.props  = get_window_properties()
        self.format = "modpack"
        self.mod_group: BlendModGroup = self.props.pmp_mod_groups[self.group]

        if len(self.prefs.modpack_presets) == 0:
            self.new_preset = True

        if self.settings:
            return self.execute(context)
        
        if event.shift or event.alt:
            manager = RNAPropertyIO()
            if event.alt:
                return self.to_clipboard(context, manager)

            elif event.shift:
                preset = self.load_preset(context, context.window_manager.clipboard.strip())
                return self.add_preset(preset, manager)
            
        else:
            context.window_manager.invoke_props_dialog(self, confirm_text="Confirm", title="Preset Manager", width=200)
            return {"RUNNING_MODAL"}

        return {"FINISHED"}
    
    def execute(self, context):
        manager = RNAPropertyIO()
        presets = self.prefs.modpack_presets

        if self.delete:
            manager.remove(presets, self.preset_idx)
            
        elif self.new_preset:
            if self.preset_name.strip() == "" or self.preset_name == "Enter preset name...":
                self.report({"ERROR"}, "Preset needs a name!")
                return {"CANCELLED"}
            
            self.to_clipboard(context, manager)

            new_preset        = presets.add()
            new_preset.name   = self.preset_name
            new_preset.preset = context.window_manager.clipboard
            new_preset.format = self.format

            self.sort_presets(presets, manager)
        
        else:
            idx            = int(self.prefs.modpack_preset_select)
            preset :Preset = self.load_preset(context, presets[idx].preset)

            context.window_manager.clipboard = presets[idx].preset

            return self.add_preset(preset, manager)

        return {"FINISHED"}
    
    def draw(self, context: Context):
        layout = self.layout
        row = layout.row(align=True)
        if not len(self.prefs.modpack_presets) == 0:
            row.prop(self, "new_preset", text="Save", icon=get_conditional_icon(self.new_preset))
            row.prop(self, "new_preset", text="Load", icon=get_conditional_icon(self.new_preset, invert=True), invert_checkbox=True)
        if self.new_preset:
            aligned_row(layout, "Name:", "preset_name", self)
        else:
            aligned_row(layout, "Preset:", "modpack_preset_select", self.prefs)

    def to_clipboard(self, context: Context, manager: RNAPropertyIO) -> set:
        option_data     = manager.extract(self.mod_group.mod_options)
        correction_data = manager.extract(self.mod_group.corrections)

        preset_json: str = self.get_wrapper([option_data, correction_data], self.format)
        preset_bytes     = gzip.compress(preset_json.encode("utf-8"))                  
        b64_string       = base64.b64encode(preset_bytes).decode("utf-8")
        
        context.window_manager.clipboard = b64_string
        return {"FINISHED"}

    def add_preset(self, preset: Preset, manager: RNAPropertyIO) -> set:
        if preset.get("_version") == 1 and preset.get("_format") == "modpack":
            manager.add(preset["preset"][0], self.mod_group.mod_options)
            manager.add(preset["preset"][1], self.mod_group.corrections)
        else:
            self.report({"ERROR"}, "Not a valid modpack preset!")
            return {"CANCELLED"}
        return {"FINISHED"}
    
    def load_preset(self, context: Context, source: str) -> Preset:
        print(source)
        preset_bytes   = base64.b64decode(source)
        preset_data    = gzip.decompress(preset_bytes) 
        preset: Preset = json.loads(preset_data.decode("utf-8"))

        # print(preset)

        return preset
    
    def get_wrapper(self, preset: Any):

        wrapper: Preset = {
            "_version":    1,
            "_format":     self.format.lower(),
            "preset":      preset,

        }
        return json.dumps(wrapper)
    
    def sort_presets(self, presets, manager: RNAPropertyIO):
        data = manager.extract(presets)
        sorted_presets = sorted(data, key=lambda preset: (preset["format"], preset["name"]))
        manager.restore(sorted_presets, presets)


CLASSES = [
    ModpackManager,
    ModpackPresets
]
