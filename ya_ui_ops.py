import bpy
import os
import ya_utils as utils

from bpy.types import Operator
from bpy.props import StringProperty

class UI_OT_YA_SetBodyPart(Operator):
    bl_idname = "ya.set_body_part"
    bl_label = "Select body slot to export."
    bl_description = "The icons almost make sense"

    body_part: StringProperty() # type: ignore

    def execute(self, context):
        # Update the export_body_part with the selected body part
        context.scene.ya_props.export_body_slot = self.body_part
        return {'FINISHED'}


class UI_OT_YA_DirSelector(Operator):
    bl_idname = "ya.dir_selector"
    bl_label = "Select Folder"
    bl_description = "Select file or directory. Cli"
    
    directory: StringProperty() # type: ignore
    category: StringProperty() # type: ignore

    def invoke(self, context, event):
        actual_dir = getattr(context.scene.ya_props, f"{self.category}_directory", "")

        if event.type == 'LEFTMOUSE' and os.path.exists(actual_dir):
            self.directory = context.scene.ya_props.export_directory
            context.window_manager.fileselect_add(self)

        elif event.type == 'LEFTMOUSE':
            context.window_manager.fileselect_add(self)

        else:
             self.report({'ERROR'}, "Not a directory!")
    
        return {'RUNNING_MODAL'}
    

    def execute(self, context):
        actual_dir_prop = f"{self.category}_directory"
        display_dir_prop = f"{self.category}_display_directory"
        selected_file = self.directory  

        if os.path.isdir(selected_file):
            setattr(context.scene.ya_props, actual_dir_prop, selected_file)
            display_dir = utils.directory_short(selected_file) 

            setattr(context.scene.ya_props, display_dir_prop, display_dir)
            self.report({'INFO'}, f"Directory selected: {selected_file}")
        
        else:
            self.report({'ERROR'}, "Not a valid path!")
        
        return {'FINISHED'}
    

class UI_OT_YA_ConsoleToolsDirectory(Operator):
    bl_idname = "ya.consoletools_dir"
    bl_label = "Select File"
    bl_description = "Use this to manually find the TexTools directory and select ConsoleTools.exe. Hold Alt to open the directory if found"
    
    filepath: StringProperty() # type: ignore

    def invoke(self, context, event):
        consoletools_path = context.scene.ya_props.consoletools_directory

        if event.alt and os.path.exists(consoletools_path):
            self.filepath = context.scene.ya_props.consoletools_directory
            context.window_manager.fileselect_add(self)

        elif event.type == 'LEFTMOUSE':
            context.window_manager.fileselect_add(self)

        else:
             self.report({'ERROR'}, "Not a directory!")
    
        return {'RUNNING_MODAL'}

    def execute(self, context):
        selected_file = self.filepath

        if os.path.exists(selected_file) and selected_file.endswith("ConsoleTools.exe"):
            context.scene.ya_props.consoletools_directory = selected_file
            context.scene.ya_props.consoletools_status = "ConsoleTools Ready!"
            self.report({'INFO'}, f"Directory selected: {selected_file}")
        
        else:
            self.report({'ERROR'}, "Not a valid ConsoleTools.exe!")
        
        return {'FINISHED'}
    
