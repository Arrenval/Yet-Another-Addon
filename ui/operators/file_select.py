import os
import bpy

from pathlib            import Path
from bpy.types          import Operator, Context
from bpy.props          import StringProperty, IntProperty

from ...properties      import BlendModOption, BlendModGroup, ModFileEntry, get_file_properties, get_window_properties
from ...preferences     import get_prefs


class PMPSelector(Operator):
    bl_idname = "ya.pmp_selector"
    bl_label = "Select Modpack"
    bl_description = """Options:
    *SHIFT click to open modpack.
    *CTRL click to unload modpack selected. 
    *ALT click to open the folder"""
    
    filepath: StringProperty() # type: ignore

    category: StringProperty(options={'HIDDEN'}) # type: ignore
    
    filter_glob: StringProperty(
        default='*.pmp',
        options={'HIDDEN'}) # type: ignore
    
    @classmethod
    def poll(cls, context:Context):
        props = get_window_properties()
        return props.modpack_replace
    
    def invoke(self, context:Context, event):
        self.props  = get_window_properties()
        actual_file = Path(self.props.modpack_dir) 

        if event.alt and event.type == "LEFTMOUSE" and actual_file.is_file():
            actual_dir = actual_file.parent
            os.startfile(str(actual_dir))

        elif event.shift and event.type == "LEFTMOUSE" and actual_file.is_file():
            os.startfile(str(actual_file))

        elif event.ctrl and event.type == "LEFTMOUSE" and actual_file.is_file():
            self.props.loaded_pmp_groups.clear()
            self.props.property_unset("modpack_dir") 

        else :
            context.window_manager.fileselect_add(self)
    
        return {"RUNNING_MODAL"}
    
    def execute(self, context:Context):
        selected_file = Path(self.filepath)

        if selected_file.exists() and selected_file.suffix == ".pmp":
            self.props.modpack_dir = str(selected_file) 
            self.props.modpack_display_dir = selected_file.stem
            self.report({'INFO'}, f"{selected_file.stem} selected!")
        else:
            self.report({'ERROR'}, "Not a valid modpack!")
        
        return {'FINISHED'}

class FileSelector(Operator):
    bl_idname = "ya.file_selector"
    bl_label = "Select File"
    bl_description = "Select file"
    
    filepath: StringProperty(options={'HIDDEN'}) # type: ignore
    category: StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: bpy.props.StringProperty(
        subtype='FILE_PATH',
        options={'HIDDEN'}) # type: ignore
    
    def invoke(self, context: Context, event):
        if self.category.startswith("INSP"):
            self.filter_glob = "*.phyb"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):

        if Path(self.filepath).is_file():
            setattr(get_window_properties(), self.attr_from_category(), self.filepath)
            self.report({"INFO"}, "File selected!")
        else:
            self.report({"ERROR"}, "Not a valid file!")
        
        return {'FINISHED'}
    
    def attr_from_category(self) -> str:
        if self.category == "INSP_ONE":
            return "insp_file_first"
        elif self.category == "INSP_TWO":
            return "insp_file_sec"
    
class DirSelector(Operator):
    bl_idname = "ya.dir_selector"
    bl_label = "Select Folder"
    bl_description = "Select directory. Hold Alt to open the folder"
    
    directory: StringProperty() # type: ignore
    category: StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: bpy.props.StringProperty(
        subtype="DIR_PATH",
        options={'HIDDEN'}) # type: ignore
    
    def invoke(self, context: Context, event):
        self.props = get_prefs()
        actual_dir = getattr(self.props, f"{self.category}_dir", "")     

        if event.alt and event.type == "LEFTMOUSE" and os.path.isdir(actual_dir):
            os.startfile(actual_dir)
        elif event.type == "LEFTMOUSE":
            context.window_manager.fileselect_add(self)
        else:
             self.report({"ERROR"}, "Not a directory!")
    
        return {"RUNNING_MODAL"}

    def execute(self, context):
        actual_dir_prop = f"{self.category}_dir"
        display_dir_prop = f"{self.category}_display_dir"
        selected_file = Path(self.directory)  

        if selected_file.is_dir():
            setattr(self.props, actual_dir_prop, str(selected_file))
            setattr(self.props, display_dir_prop, str(Path(*selected_file.parts[-3:])))
            self.report({"INFO"}, f"Directory selected: {selected_file}")
        
        else:
            self.report({"ERROR"}, "Not a valid path!")
        
        return {'FINISHED'}
    
class ModpackFileSelector(Operator):
    bl_idname = "ya.modpack_file_selector"
    bl_label = "Select File"
    bl_description = "CTRL click to remove file entry"
    
    filepath : StringProperty(subtype="FILE_PATH") # type: ignore

    category: StringProperty(options={'HIDDEN'}) # type: ignore

    group : IntProperty(default=0, options={'HIDDEN', "SKIP_SAVE"}) # type: ignore
    option: IntProperty(default=0, options={'HIDDEN', "SKIP_SAVE"}) # type: ignore
    entry : IntProperty(default=0, options={'HIDDEN', "SKIP_SAVE"}) # type: ignore
    
    filter_glob: bpy.props.StringProperty(
        options={'HIDDEN'}) # type: ignore

    def invoke(self, context: Context, event):
        self.group:int
        self.option:int
        self.container:BlendModGroup | BlendModOption | ModFileEntry
        props = get_window_properties()

        mod_group: BlendModGroup = props.pmp_mod_groups[self.group]

        if self.category == "PHYB":
            return self.manage_phybs(context, event, mod_group, self.option)
        
        if self.category.endswith("COMBI"):
            group_options: list[BlendModOption] = mod_group.corrections
        else:
            group_options: list[BlendModOption] = mod_group.mod_options

        
        self.container = group_options[self.option].file_entries[self.entry]

        self.filter_glob = "*.mdl;*.phyb;*.tex"

        if event.ctrl and event.type == "LEFTMOUSE":
            self._remove_entry()
            return {"FINISHED"}

        else:
            context.window_manager.fileselect_add(self,)

        return {"RUNNING_MODAL"}
    
    def manage_phybs(self, context: Context, event, mod_group: BlendModGroup, option: int) -> set[str]:
        self.container   = mod_group.base_phybs[option]
        self.filter_glob = "*.phyb"

        if event.ctrl and event.type == "LEFTMOUSE":
            self._remove_entry()
            return {"FINISHED"}
        else:
            context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}
    
    def _remove_entry(self):
        bpy.ops.ya.modpack_manager(
                'EXEC_DEFAULT',
                delete=True,
                category=self.category,
                group=self.group,
                option=self.option,
                entry=self.entry
            )

    def execute(self, context):
        selected_file = Path(self.filepath) 

        if selected_file.is_file():
            self.container.file_path = str(selected_file)
            self.report({"INFO"}, f"File selected: {selected_file.name}")
        else:
            self.report({"ERROR"}, "Not a valid path!")
        
        return {'FINISHED'}
    
class ModpackDirSelector(Operator):
    bl_idname = "ya.modpack_dir_selector"
    bl_label = "Select folder"
    bl_description = ""

    @classmethod
    def description(cls, context, properties):
        if properties.category == "PHYB":
            return "Get base phybs from folder"
        else:
            return """Options:
    *SHIFT click to copy directory from file export.
    *CTRL click to remove folder. 
    *ALT click to open the folder"""
        
    directory: StringProperty(subtype="DIR_PATH") # type: ignore

    category: StringProperty(options={'HIDDEN', "SKIP_SAVE"}) # type: ignore
    group   : IntProperty(default=0, options={'HIDDEN', "SKIP_SAVE"}) # type: ignore

    filter_glob: bpy.props.StringProperty(
        options={'HIDDEN'}) # type: ignore

    def invoke(self, context: Context, event):
        self.group:int
        self.option:int
        self.container: BlendModGroup | BlendModOption | ModFileEntry

        self.prefs = get_prefs()
        self.props = get_window_properties()
        
        match self.category:
            case "GROUP" | "SIM":
                self.container = self.props.pmp_mod_groups[self.group]
                self.folder    = self.container.folder_path
                attribute      = "folder_path"

            case "OUTPUT_PMP":
                self.folder    = self.prefs.modpack_output_dir
                attribute      = "modpack_output_dir"
            case "PHYB":
                context.window_manager.fileselect_add(self)
                return {"RUNNING_MODAL"}
                
        if self.folder.strip() == "":
            context.window_manager.fileselect_add(self)
            return {"RUNNING_MODAL"}
        else:
            self.folder = Path(self.folder)
            
        if event.ctrl and event.type == "LEFTMOUSE" and self.folder.is_dir():
            if self.category == "OUTPUT_PMP":
                self.prefs.property_unset("modpack_output_display_dir")
            else:
                self.container.property_unset(attribute)
                self.container.subfolder = "None"
            return {'FINISHED'}
        
        elif event.alt and event.type == "LEFTMOUSE" and self.folder.is_dir():
            os.startfile(self.folder)
        elif event.shift and event.type == "LEFTMOUSE":
            bpy.ops.ya.directory_copy(
                "EXEC_DEFAULT", 
                category=self.category,
                group=self.group,)
        else:
            context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        selected_dir = Path(self.directory)  

        if selected_dir.is_dir():
            if self.category == "OUTPUT_PMP":
                self.prefs.modpack_output_display_dir = str(Path(*selected_dir.parts[-3:]))
                self.prefs.modpack_output_dir = str(selected_dir)
            elif self.category == "PHYB":
                self.phybs_from_folder(selected_dir)
            else:
                self.container.folder_path = str(selected_dir)
            self.report({"INFO"}, f"Directory selected: {selected_dir}")
        else:
            self.report({"ERROR"}, "Not a valid directory!")
        
        return {'FINISHED'}
    
    def phybs_from_folder(self, folder: Path) -> None:
        group: BlendModGroup = get_window_properties().pmp_mod_groups[self.group]
        files = [file for file in folder.glob("*") if file.is_file() and file.suffix in ".phyb"]
        
        group.base_phybs.clear()
        for file in files:
            new_phyb = group.base_phybs.add()
            new_phyb.file_path = str(file)




CLASSES = [
    PMPSelector,
    FileSelector,
    DirSelector,
    ModpackFileSelector,
    ModpackDirSelector,
]
