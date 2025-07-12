from pathlib             import Path
from bpy.types           import Operator, Context
from bpy.props           import StringProperty, IntProperty
from ...properties       import BlendModOption, BlendModGroup, CorrectionEntry, get_file_properties, get_window_properties
from ...preferences      import get_prefs
 

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
        props = get_window_properties()
        export_dir = Path(prefs.export_dir)
        mod_groups: list[BlendModGroup] = props.pmp_mod_groups

        if len(mod_groups) > 0:
            mod_group = mod_groups[self.group]
            group_options:list[BlendModOption] = mod_group.mod_options
        
        match self.category:
            case "OUTPUT_PMP":
                prefs.modpack_output_dir = str(export_dir)
                prefs.modpack_output_display_dir = str(Path(*export_dir.parts[-3:]))
            case "GROUP" | "SIM":
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
        self.props = get_window_properties()

        mod_groups: list[BlendModGroup] = self.props.pmp_mod_groups
        mod_group: BlendModGroup = self.props.pmp_mod_groups[self.group]
        
        if self.category.endswith("COMBI"):
            group_options:list[CorrectionEntry] = mod_group.corrections
        else:
            group_options:list[BlendModOption] = mod_group.mod_options
        
        if self.category == "GROUP":
            game_path: str = mod_groups[self.group].game_path
        elif self.category.endswith("COMBI"):
            game_path: str = group_options[self.option].file_entries[self.entry].game_path
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
    CopyToModpacker,
    GamepathCategory
]
