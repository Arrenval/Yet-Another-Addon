import os
import bpy

from pathlib            import Path
from bpy.types          import Operator, Context
from bpy.props          import StringProperty, IntProperty
from ...properties      import BlendModOption, BlendModGroup, ModFileEntry, get_file_properties
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
    filter_glob: bpy.props.StringProperty(
        default='*.pmp',
        options={'HIDDEN'}) # type: ignore
    
    @classmethod
    def poll(cls, context:Context):
        props = get_file_properties()
        return props.modpack_replace
    
    def invoke(self, context:Context, event):
        self.props  = get_file_properties()
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
  
class DirSelector(Operator):
    bl_idname = "ya.dir_selector"
    bl_label = "Select Folder"
    bl_description = "Select file or directory. Hold Alt to open the folder"
    
    directory: StringProperty() # type: ignore
    category: StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: bpy.props.StringProperty(
        subtype="DIR_PATH",
        options={'HIDDEN'}) # type: ignore
    
    def invoke(self, context: Context, event):
        self.props = get_file_properties()
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
        props = get_file_properties()

        mod_group = props.pmp_mod_groups[self.group]
        group_options:list[BlendModOption] = mod_group.mod_options
   
        self.container = group_options[self.option].file_entries[self.entry]

        self.filter_glob = "*.mdl;*.phyb;*.tex"

        if event.ctrl and event.type == "LEFTMOUSE":
            bpy.ops.ya.modpacker_ui_containers(
            'EXEC_DEFAULT',
            delete=True,
            category=self.category,
            group=self.group,
            option=self.option,
            entry=self.entry)

        else:
            context.window_manager.fileselect_add(self,)

        return {"RUNNING_MODAL"}
    
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
    bl_description = """Options:
    *SHIFT click to copy directory from file export.
    *CTRL click to remove folder. 
    *ALT click to open the folder"""
    
    directory: StringProperty(subtype="DIR_PATH") # type: ignore

    category: StringProperty(options={'HIDDEN'}) # type: ignore
    group : IntProperty(default=0, options={'HIDDEN', "SKIP_SAVE"}) # type: ignore

    filter_glob: bpy.props.StringProperty(
        options={'HIDDEN'}) # type: ignore

    def invoke(self, context: Context, event):
        self.group:int
        self.option:int
        self.container:BlendModGroup | BlendModOption | ModFileEntry

        self.prefs = get_prefs()
        self.props = get_file_properties()
        
        mod_group = self.props.pmp_mod_groups[self.group]
   
        match self.category:
            case "GROUP":
                self.container = mod_group
                self.folder    = self.container.folder_path
                attribute      = "file_path"

            case "OUTPUT_PMP":
                self.folder    = self.container.modpack_output_dir
                attribute      = "modpack_output_dir"

        self.filter_glob = "DIR_PATH"

        if self.folder == "":
            context.window_manager.fileselect_add(self)
            return {"RUNNING_MODAL"}
        else:
            self.folder = Path(self.folder)
            
        if event.ctrl and event.type == "LEFTMOUSE" and self.folder.is_dir():
            if self.category == "OUTPUT_PMP":
                self.prefs.property_unset("modpack_output_display_dir")
            else:
                self.container.property_unset(attribute)
            return {'FINISHED'}
        
        elif event.alt and event.type == "LEFTMOUSE" and self.folder.is_dir():
            os.startfile(self.folder)
        elif event.shift and event.type == "LEFTMOUSE":
            bpy.ops.ya.directory_copy(
                "EXEC_DEFAULT", 
                category=self.category,
                group=self.group,
                option=self.option)
        else:
            context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        selected_file = Path(self.directory)  

        if selected_file.is_dir():
            if self.category == "OUTPUT_PMP":
                self.prefs.modpack_output_display_dir = str(Path(*selected_file.parts[-3:]))
                self.prefs.modpack_output_dir = str(selected_file)
            else:
                self.container.folder_path = str(selected_file)
            self.report({"INFO"}, f"Directory selected: {selected_file}")
        else:
            self.report({"ERROR"}, "Not a valid path!")
        
        return {'FINISHED'}


CLASSES = [
    PMPSelector,
    DirSelector,
    ModpackFileSelector,
    ModpackDirSelector,
]