from pathlib            import Path
from bpy.types          import Operator, Context
from bpy.props          import StringProperty, EnumProperty, BoolProperty, IntProperty
from ...properties      import BlendModOption, BlendModGroup, get_file_properties
from ...preferences     import get_prefs
from ...util.serialiser import RNAPropertyManager


MODPACK_DEFAULT_ENUMS = {
    'slot': 'Body',
    'race_condition': '0', 
    'connector_condition': 'None',
    'idx': 'New',
    'page': '0',
    'group_type': 'Single',
    'subfolder': 'None',
    'names': '0'
}   
 
class ModpackerContainers(Operator):
    bl_idname = "ya.modpacker_ui_containers"
    bl_label = ""
    bl_description = ""

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
            if properties.category == "ENTRY":
                return f"""Add {properties.category.capitalize()}:
        *SHIFT click for file.
        *CTRL click for shape key.
        *ALT click for attribute"""
            elif properties.category == "OPTION":
                return f"""Add {properties.category.capitalize()}. 
        *SHIFT click to add a correction entry to a Combining group"""
            else:
                return f"Add {properties.category.capitalize()}"
        elif properties.category.endswith("_ENTRY"):
            return f"Hold CTRL to remove {properties.category[:3]}"
        else:
            return f"Hold CTRL to remove {properties.category.capitalize()}"
        
    def invoke(self, context:Context, event):
        self.prefs = get_prefs()
        self.props = get_file_properties()
        self.mod_groups: list[BlendModGroup] = self.props.pmp_mod_groups

        if self.category in ("ENTRY", "COMBI_ENTRY"):
            if event.shift:
                self.category = "FILE_ENTRY"

            elif event.ctrl:
                self.category = f"SHP_{self.category.split('_')[0]}"

            elif event.alt:
                self.category = f"ATR_{self.category.split('_')[0]}"
                
            else:
                context.window_manager.invoke_props_dialog(self, confirm_text="Confirm", title="", width=2)
                return {'RUNNING_MODAL'}
                
        if self.category == "OPTION":
            mod_group = self.mod_groups[self.group]
            if event.shift and mod_group.group_type == "Combining":
                self.category = "COMBI"

        if self.delete and not event.ctrl:
            return {'FINISHED'}
        return self.execute(context)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "user_input")

    def execute(self, context:Context):
        if self.category == "ENTRY":
            self.category = self.user_input
        self.group: int
        self.option: int

        if len(self.mod_groups) > 0:
            mod_group = self.mod_groups[self.group]
            group_options:list[BlendModOption] = mod_group.mod_options
        
        if self.delete:
            manager = RNAPropertyManager()
            manager.enum_defaults = MODPACK_DEFAULT_ENUMS

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

            case "FILE_ENTRY":

                option_entries = group_options[self.option].file_entries

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
    
    def set_preset(self, context) -> None:
        model_id = self.get_model_id_from_path(context)
        prefix = "shpx_"
        
        slot, options, corrections = self.get_preset(context, self.preset)

        idx = len(self.combining_options)
        for option, key_data in options.items():
            new_option = self.combining_options.add()
            new_option.name = option

            for entries in key_data:
                new_shape = self.combining_options[idx].meta_entries.add()
                new_shape.slot = slot
                new_shape.modelid = model_id
                new_shape.condition = entries["Conditional"]
                new_shape.manip_ref = prefix + entries["Shape"]
            idx +=1
        for correction in corrections:
            add_corrections = self.corrections.add()
            add_corrections.name = "Alt Hips/Soft Butt"
            add_corrections.entry.slot = slot
            add_corrections.entry.modelid = model_id
            add_corrections.entry.condition = correction["Conditional"]
            add_corrections.entry.manip_ref = prefix + correction["Shape"]

            total_options = [option.name for option in self.combining_options]

            idx_list = []
            split = "Alt Hips/Soft Butt".split("/")
            for option in split:
                idx = total_options.index(option)
                idx_list.append(idx)
            for idx in idx_list:
                item = add_corrections.option_idx.add()
                item.value = idx

    def get_preset(self, context, preset):
        slot = "Legs"

        options = {"Alt Hips":  [{"Shape": "yab_hip", "Conditional": "None"},
                                 {"Shape": "rue_hip", "Conditional": "None"}],

                   "Soft Butt": [{"Shape": "softbutt", "Conditional": "None"},
                                 {"Shape": "yabc_waist", "Conditional": "Waist"}]}
        
        corrections = [{"Shape": "yabc_hipsoft", "Conditional": "None"},
                       {"Shape": "ruec_hipsoft", "Conditional": "None"}]
        
        return slot, options, corrections

class CopyToModpacker(Operator):
    bl_idname = "ya.directory_copy"
    bl_label = "Copy Path"
    bl_description = "Copies the export directory to your modpack directory. This should be where your FBX files are located"

    category: StringProperty() # type: ignore

    group : IntProperty(default=0, options={"SKIP_SAVE"}) # type: ignore

    def execute(self, context):
        self.group:int
        self.option:int
        prefs = get_prefs()
        props = get_file_properties()
        export_dir = Path(prefs.export_dir)
        mod_groups: list[BlendModGroup] = props.pmp_mod_groups

        if len(mod_groups) > 0:
            mod_group = mod_groups[self.group]
            group_options:list[BlendModOption] = mod_group.mod_options
        
        match self.category:
            case "OUTPUT_PMP":
                prefs.modpack_output_dir = str(export_dir)
                prefs.modpack_output_display_dir = str(Path(*export_dir.parts[-3:]))
            case "GROUP":
                mod_group.folder_path = str(export_dir)
            case "OPTION":
                group_options[self.option].folder_path = str(export_dir)

        return {'FINISHED'}

class GamepathCategory(Operator):
    bl_idname = "ya.gamepath_category"
    bl_label = "Modpacker"
    bl_description = "Changes gamepath category"

    body_slot: StringProperty() # type: ignore
    category : StringProperty() # type: ignore

    group : IntProperty(default=0, options={"SKIP_SAVE"}) # type: ignore
    option: IntProperty(default=0, options={"SKIP_SAVE"}) # type: ignore
    entry : IntProperty(default=0, options={"SKIP_SAVE"}) # type: ignore


    def execute(self, context: Context):
        self.group: int
        self.option: int
        self.entry: int
        self.props = get_file_properties()

        mod_groups: list[BlendModGroup] = self.props.pmp_mod_groups
        mod_group = mod_groups[self.group]
        group_options:list[BlendModOption] = mod_group.mod_options
        
        if self.category == "GROUP":
            game_path: str = mod_groups[self.group].game_path
        else:
            game_path: str = group_options[self.option].file_entries[self.entry].game_path
        
        game_path_split     = game_path.split("_")
        category_split      = game_path_split[-1].split(".")
        category_split[0]   = self.body_slot
        game_path_split[-1]  = ".".join(category_split)

        game_path = "_".join(game_path_split)

        if self.category == "GROUP":
            setattr(mod_groups[self.group], "game_path", "_".join(game_path_split))
        else:
            setattr(group_options[self.option].file_entries[self.entry], "game_path", "_".join(game_path_split))
        context.view_layer.update()
        return {'FINISHED'}
  

CLASSES = [
    ModpackerContainers,
    CopyToModpacker,
    GamepathCategory
]