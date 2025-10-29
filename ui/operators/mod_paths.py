from pathlib          import Path
from bpy.types        import Operator, Context
from bpy.props        import StringProperty, IntProperty

from ...props         import get_window_props
from ...preferences   import get_prefs
 

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
        props = get_window_props()
        export_dir = Path(prefs.export.output_dir)
        mod_groups = props.file.modpack.pmp_mod_groups

        if len(mod_groups) > 0:
            mod_group     = mod_groups[self.group]
            group_options = mod_group.mod_options
        
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
        self.props = get_window_props()

        if self.category == "EXPORT":
            game_path: str = self.props.file.io.export_xiv_path
            game_path      = self.change_category(game_path)
            setattr(self.props.file.io, "export_xiv_path", game_path)
        else:
            self.modpack_path()

        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}
    
    def modpack_path(self):
        mod_groups = self.props.file.modpack.pmp_mod_groups
        mod_group  = self.props.file.modpack.pmp_mod_groups[self.group]
        
        if self.category.endswith("COMBI"):
            group_options = mod_group.corrections
        else:
            group_options = mod_group.mod_options
        
        if self.category == "GROUP":
            game_path: str = mod_groups[self.group].game_path
        elif self.category.endswith("COMBI"):
            game_path: str = group_options[self.option].file_entries[self.entry].game_path
        else:
            game_path: str = group_options[self.option].file_entries[self.entry].game_path
        
        game_path = self.change_category(game_path)

        if self.category == "GROUP":
            setattr(mod_groups[self.group], "game_path", game_path)
        else:
            setattr(group_options[self.option].file_entries[self.entry], "game_path", game_path)
        
    def change_category(self, game_path: str) -> str:
        game_path_split     = game_path.split("_")
        category_split      = game_path_split[-1].split(".")
        category_split[0]   = self.body_slot
        game_path_split[-1] = ".".join(category_split)

        game_path = "_".join(game_path_split)
        
        return game_path


CLASSES = [
    CopyToModpacker,
    GamepathCategory
]
