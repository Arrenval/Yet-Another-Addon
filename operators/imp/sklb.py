from pathlib    import Path
from bpy.types  import Operator
from bpy.props  import StringProperty

from ...io.sklb import SklbImport

   
class SkeletonImport(Operator):
    bl_idname      = "ya.sklb_import"
    bl_label       = "Import SKLB"
    bl_description = "Select file"
    bl_options     = {'UNDO'}

    filepath   : StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: StringProperty(
        default="*.sklb",
        subtype='FILE_PATH',
        options={'HIDDEN'}) # type: ignore
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        file = Path(self.filepath)

        if not file.is_file():
            self.report({"ERROR"}, "Not a valid file!")
            return {'FINISHED'}
 
        SklbImport.from_file(self.filepath, file.stem)
        return {'FINISHED'}


CLASSES = [
    SkeletonImport
]
