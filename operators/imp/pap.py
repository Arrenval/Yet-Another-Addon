from pathlib    import Path
from bpy.types  import Operator
from bpy.props  import StringProperty

from ...props import get_window_props
from ...io.pap.importer import PapImport
from ...xivpy.sklb import XIVSkeleton
from ...xivpy.pap import XIVAnim
   
class AnimImport(Operator):
    bl_idname      = "ya.pap_import"
    bl_label       = "Import PAP"
    bl_description = "Select file"
    bl_options     = {'UNDO'}

    filepath   : StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: StringProperty(
        default="*.pap",
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

        sklb = XIVSkeleton.from_file(get_window_props().anim.sklb)
        pap  = XIVAnim.from_file(self.filepath)
        anim_container = pap.kaos.get_animation_container()
        
        # for node in pap.kaos.nodes:
        #     print(node)
        for idx, anim in enumerate(pap.anim_info):
            bindings  = pap.kaos.nodes[anim_container["bindings"][idx]]
            animation = pap.kaos.nodes[anim_container["animations"][idx]]
            PapImport.from_pap(pap, anim, sklb, animation, bindings)
            
        # for node in pap.kaos.nodes:
            # print(node)
            # if node.name == 'hkaQuantizedAnimation':
            #     anim = QuantisedAnimation.from_bytes(node['data'])
            #     with open(file.parent / 'hkaQuantizedAnimationWrite.hkanim', 'wb') as file:
            #         file.write(node["data"])
        
        return {'FINISHED'}


CLASSES = [
    AnimImport
]
