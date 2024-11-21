import bpy
import os
import subprocess
from bpy.types import Operator

class UI_OT_YA_SetBodyPart(Operator):
    bl_idname = "object.set_body_part"
    bl_label = "Select body slot to export."
    bl_description = "The icons almost make sense"

    body_part: bpy.props.StringProperty() # type: ignore

    def execute(self, context):
        # Update the export_body_part with the selected body part
        context.scene.ya_props.export_body_slot = self.body_part
        return {'FINISHED'}

class UI_OT_YA_ConsoleToolsDirectory(Operator):
    bl_idname = "wm.console_tools_dir"
    bl_label = "Click to open file selector. Hold Alt to open current folder"
    
    folder_path: bpy.context.scene.ya_props.consoletools_directory # type: ignore
      

    def invoke(self, context, event):
        # Check if the Alt key is held while clicking
        if event.alt:
            context.window_manager.fileselect_add(self)
        else:
            self.report({'ERROR'}, "No directory selected for export!")

        return {'FINISHED'}

    def execute(self, context):
        # This is called after the user selects a file in the file dialog
        selected_file = context.scene.filepath
        bpy.context.scene.ya_props.consoletools_directory = selected_file
        self.report({'INFO'}, f"File selected: {selected_file}")
        
        return {'FINISHED'}