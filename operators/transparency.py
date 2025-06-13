import bpy

from bpy.types    import Operator, Context
from bpy.props    import StringProperty


class TransparencyOverview(Operator):
    bl_idname = "ya.transparency"
    bl_label = "Transparency"
    bl_options = {"UNDO", "REGISTER"}
    bl_description ="Tag mesh as being transparent ingame for extra handling on export. Adjust rendering in Blender when using 'BLENDED'"

    render: StringProperty(default="") # type: ignore

    @classmethod
    def description(cls, context, properties):
        if properties.render == 'BLENDED':
            return "Simpler Blender render method, less accurate transparency"
        elif properties.render == "DITHERED":
            return "More accurate Blender rendering of transparency. More performance heavy"
        
    def execute(self, context:Context):
        obj = context.active_object
        if obj.active_material:
            material = obj.active_material

        if self.render == 'BLENDED':
            material.surface_render_method = 'BLENDED'
        elif self.render == 'DITHERED':
            material.surface_render_method = 'DITHERED'
        else:
            if "xiv_transparency" not in obj:
                obj["xiv_transparency"] = True
                if obj.active_material:
                    obj.active_material.use_transparency_overlap = True
            elif obj["xiv_transparency"]:
                obj["xiv_transparency"] = False
                if obj.active_material:
                    obj.active_material.use_transparency_overlap = False
            elif not obj["xiv_transparency"]:
                obj["xiv_transparency"] = True
                if obj.active_material:
                    obj.active_material.use_transparency_overlap = True
        return {"FINISHED"}


CLASSES = [
    TransparencyOverview,
]