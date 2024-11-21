import bpy
import os
import ya_utils as utils
from bpy.types import Operator
from bpy.props import StringProperty

class UI_OT_YA_SetBodyPart(Operator):
    bl_idname = "object.set_body_part"
    bl_label = "Select body slot to export."
    bl_description = "The icons almost make sense"

    body_part: StringProperty() # type: ignore

    def execute(self, context):
        # Update the export_body_part with the selected body part
        context.scene.ya_props.export_body_slot = self.body_part
        return {'FINISHED'}

class UI_OT_YA_ConsoleToolsDirectory(Operator):
    bl_idname = "wm.consoletools_dir"
    bl_label = "Select File"
    bl_description = "Use this to manually find the TexTools directory and select ConsoleTools.exe"
    
    filepath: StringProperty() # type: ignore

    def invoke(self, context, event):
        consolet_path = context.scene.ya_props.consoletools_directory

        if event.shift and os.path.exists(consolet_path):
            self.filepath = context.scene.ya_props.consoletools_directory
            context.window_manager.fileselect_add(self)
        else:
             self.report({'ERROR'}, "Not a directory!")

    
        return {'RUNNING_MODAL'}

    def execute(self, context):
        # This is called after the user selects a file in the file dialog
        selected_file = self.filepath  # Get the file path from the operator
        if os.path.exists(selected_file) and selected_file.endswith("ConsoleTools.exe"):

            context.scene.ya_props.consoletools_directory = selected_file
            context.scene.ya_props.consoletools_status = "ConsoleTools Ready!"
            self.report({'INFO'}, f"Directory selected: {selected_file}")
        else:
            self.report({'ERROR'}, "Not a valid ConsoleTools.exe!")
        
        return {'FINISHED'}