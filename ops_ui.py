import bpy
import os
import ya_utils as utils

from bpy.types  import Operator
from bpy.props  import StringProperty

class BodyPartSlot(Operator):
    bl_idname = "ya.set_body_part"
    bl_label = "Select body slot to export."
    bl_description = "The icons almost make sense"

    body_part: StringProperty() # type: ignore

    def execute(self, context):
        # Update the export_body_part with the selected body part
        context.scene.file_props.export_body_slot = self.body_part
        return {'FINISHED'}


class DirSelector(Operator):
    bl_idname = "ya.dir_selector"
    bl_label = "Select Folder"
    bl_description = "Select file or directory. Hold Alt to open the folder"
    
    directory: StringProperty() # type: ignore
    category: StringProperty() # type: ignore

    def invoke(self, context, event):
        actual_dir = getattr(context.scene.file_props, f"{self.category}_directory", "")     

        if event.alt and event.type == "LEFTMOUSE" and os.path.isdir(actual_dir):
            os.startfile(actual_dir)
        elif event.type == "LEFTMOUSE":
            context.window_manager.fileselect_add(self)

        else:
             self.report({"ERROR"}, "Not a directory!")
    
        return {"RUNNING_MODAL"}
    

    def execute(self, context):
        actual_dir_prop = f"{self.category}_directory"
        display_dir_prop = f"{self.category}_display_directory"
        selected_file = self.directory  

        if os.path.isdir(selected_file):
            setattr(context.scene.file_props, actual_dir_prop, selected_file)
            display_dir = utils.directory_short(selected_file, 3) 

            setattr(context.scene.file_props, display_dir_prop, display_dir)
            self.report({"INFO"}, f"Directory selected: {selected_file}")
        
        else:
            self.report({"ERROR"}, "Not a valid path!")
        
        return {'FINISHED'}
    

class ConsoleToolsDirectory(Operator):
    bl_idname = "ya.consoletools_dir"
    bl_label = "Select File"
    bl_description = "Use this to manually find the TexTools directory and select ConsoleTools.exe. Hold Alt to open the TexTools folder if already found"
    
    filepath: StringProperty() # type: ignore

    def invoke(self, context, event):
        textools = context.scene.file_props.textools_directory

        if event.alt and os.path.exists(textools):
            os.startfile(textools)

        elif event.type == 'LEFTMOUSE':
            context.window_manager.fileselect_add(self)

        else:
             self.report({'ERROR'}, "Not a directory!")
    
        return {'RUNNING_MODAL'}

    def execute(self, context):
        selected_file = self.filepath

        if os.path.exists(selected_file) and selected_file.endswith("ConsoleTools.exe"):
            path_parts = selected_file.split(os.sep)
            textools_folder = os.sep.join(path_parts[:-1])
            context.scene.file_props.textools_directory = textools_folder
            context.scene.file_props.consoletools_status = "ConsoleTools Ready!"
            self.report({'INFO'}, f"Directory selected: {textools_folder}")
        
        else:
            self.report({'ERROR'}, "Not a valid ConsoleTools.exe!")
        
        return {'FINISHED'}
    

class PMPSelector(Operator):
    bl_idname = "ya.pmp_selector"
    bl_label = "Select Modpack"
    bl_description = "Select a modpack. If selected, hold Alt to open the folder, hold Shift to open modpack"
    
    filepath: StringProperty() # type: ignore
    category: StringProperty() # type: ignore

    def invoke(self, context, event):
        actual_file = context.scene.file_props.loadmodpack_directory 

        if event.alt and event.type == "LEFTMOUSE" and os.path.isfile(actual_file):
            path_parts = actual_file.split(os.sep)
            actual_dir = os.sep.join(path_parts[:-1])
            print(actual_dir)
            os.startfile(actual_dir)

        elif event.shift and event.type == "LEFTMOUSE" and os.path.isfile(actual_file):
            os.startfile(actual_file)

        elif event.type == "LEFTMOUSE":
            context.window_manager.fileselect_add(self)

        else:
             self.report({"ERROR"}, "Not a valid modpack!")
    
        return {"RUNNING_MODAL"}
    
    
    def execute(self, context):
        selected_file = self.filepath

        if os.path.exists(selected_file) and selected_file.endswith(".pmp"):
            
            context.scene.file_props.loadmodpack_directory = selected_file
            display_dir = utils.directory_short(selected_file, 1) 
            context.scene.file_props.loadmodpack_display_directory = display_dir[:-4]

            self.report({'INFO'}, f"{display_dir} selected!")
        
        else:
            self.report({'ERROR'}, "Not a valid modpack!")
        
        return {'FINISHED'}
    

class CopyToFBX(Operator):
    bl_idname = "ya.directory_copy"
    bl_label = "Copy Path"
    bl_description = "Copies the export directory to your modpack directry. This should be where your FBX files are located"

    def execute(self, context):
        export_dir = context.scene.file_props.export_directory
        context.scene.file_props.savemodpack_directory = export_dir
        context.scene.file_props.savemodpack_display_directory = utils.directory_short(export_dir, 3)
    
        return {'FINISHED'}

classes = [
    BodyPartSlot,
    DirSelector,
    ConsoleToolsDirectory,
    PMPSelector,
    CopyToFBX
]
