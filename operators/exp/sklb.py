from bpy.types  import Operator
from bpy.props  import StringProperty

from ...io.sklb import SklbExport
   
class SkeletonExport(Operator):
    bl_idname      = "ya.sklb_export"
    bl_label       = "Export SKLB"
    bl_description = "Export skeleton"
    bl_options     = {'UNDO'}

    filepath   : StringProperty(options={'HIDDEN'}) # type: ignore
    filename   : StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: StringProperty(
        default="*.sklb",
        subtype='FILE_PATH',
        options={'HIDDEN'}) # type: ignore
    
    @classmethod
    def poll(cls, context) -> bool:
        return context.active_object and context.active_object.type == 'ARMATURE'
    
    def invoke(self, context, event):
        if not self.filename:
            self.filename = context.active_object.name

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        SklbExport.export_armature(context.active_object.data, self.filepath)
        return {'FINISHED'}


CLASSES = [
    SkeletonExport
]
