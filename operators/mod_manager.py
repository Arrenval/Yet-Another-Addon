from bpy.types          import Operator, Context, OperatorProperties
from bpy.props          import StringProperty, EnumProperty, BoolProperty, IntProperty
from ..ui.draw          import aligned_row, get_conditional_icon
from ..properties       import BlendModOption, BlendModGroup, get_file_properties
from ..preferences      import get_prefs
from ..utils.typings    import Preset
from ..utils.serialiser import RNAPropertySerialiser, dict_to_json, json_to_dict


class ModpackManager(Operator):
    bl_idname = "ya.modpack_manager"
    bl_label = ""
    bl_description = ""
    bl_options = {'UNDO'}

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
        self.props = get_file_properties()
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
        layout = self.layout
        layout.prop(self, "user_input")

    def execute(self, context:Context):
        self.prefs = get_prefs()
        self.props = get_file_properties()
        self.mod_groups: list[BlendModGroup] = self.props.pmp_mod_groups
        
        if self.category == "ENTRY":
            self.category = self.user_input
        self.group: int
        self.option: int
        
        if len(self.mod_groups) > 0:
            mod_group = self.mod_groups[self.group]
            group_options:list[BlendModOption] = mod_group.mod_options
        
        if self.delete:
            manager = RNAPropertySerialiser()

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

        return {'FINISHED'}
    
class ModpackPresets(Operator):
    bl_idname = "ya.modpack_presets"
    bl_label = ""
    bl_description = ""

    bl_options = {'UNDO'}

    preset_name: StringProperty(default="Enter preset name...", options={"SKIP_SAVE"}) # type: ignore
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
        self.props  = get_file_properties()
        self.format = "modpack"
        self.mod_group: BlendModGroup = self.props.pmp_mod_groups[self.group]

        if len(self.prefs.modpack_presets) == 0:
            self.new_preset = True

        if self.settings:
            return self.execute(context)
        
        if event.shift or event.alt:
            manager = RNAPropertySerialiser()
            if event.alt:
                option_data     = manager.extract(self.mod_group.mod_options)
                correction_data = manager.extract(self.mod_group.corrections)
                preset: Preset  = manager.to_clipboard([option_data, correction_data], self.format)

                context.window_manager.clipboard = preset

            elif event.shift:
                try:
                    preset = json_to_dict(context.window_manager.clipboard)
                except:
                    self.report({"ERROR"}, "Not a valid modpack preset!")
                    return {"CANCELLED"}

                if preset.get("_version") == 1 and preset.get("_format") == "modpack":
                    manager.add(preset["preset"], self.mod_group.mod_options)
                    manager.add(preset["corrections"], self.mod_group.corrections)

                else:
                    self.report({"ERROR"}, "Not a valid modpack preset!")
                    return {"CANCELLED"}

        else:
            context.window_manager.invoke_props_dialog(self, confirm_text="Confirm", title="Preset Manager", width=200)
            return {"RUNNING_MODAL"}

        return {"FINISHED"}
    
    def execute(self, context):
        manager = RNAPropertySerialiser()
        presets = self.prefs.modpack_presets

        if self.delete:
            manager.remove(presets, self.preset_idx)
            
        elif self.new_preset:
            if self.preset_name.strip() == "" or self.preset_name == "Enter preset name...":
                self.report({"ERROR"}, "Preset needs a name!")
                return {"CANCELLED"}
            
            option_data     = manager.extract(self.mod_group.mod_options)
            correction_data = manager.extract(self.mod_group.corrections)
            preset: Preset  = manager.to_clipboard([option_data, correction_data], self.format)

            new_preset        = presets.add()
            new_preset.name   = self.preset_name
            new_preset.preset = preset
            new_preset.format = self.format

            self.sort_presets(presets, manager)
        
        else:
            idx           = int(self.prefs.modpack_preset_select)
            preset:Preset = json_to_dict(presets[idx].preset)

            manager.add(preset["preset"], self.mod_group.mod_options)
            manager.add(preset["corrections"], self.mod_group.corrections)

            context.window_manager.clipboard = preset

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

    def sort_presets(self, presets, manager: RNAPropertySerialiser):
        data = manager.extract(presets)
        sorted_presets = sorted(data, key=lambda preset: (preset["format"], preset["name"]))
        manager.restore(sorted_presets, presets)


CLASSES = [
    ModpackManager,
    ModpackPresets
]
