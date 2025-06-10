import bpy

from bpy.types          import Operator
from bpy.props          import BoolProperty
from ..properties       import get_outfit_properties


class FrameJump(Operator):
    bl_idname = "ya.frame_jump"
    bl_label = "Jump to Endpoint"
    bl_description = "Jump to first/last frame in frame range"
    bl_options = {'REGISTER'}

    end: BoolProperty() # type: ignore
 
    def execute(self, context):
        bpy.ops.screen.frame_jump(end=self.end)
        get_outfit_properties().animation_frame = context.scene.frame_current

        return {'FINISHED'}

class KeyframeJump(Operator):
    bl_idname = "ya.keyframe_jump"
    bl_label = "Jump to Keyframe"
    bl_description = "Jump to previous/next keyframe"
    bl_options = {'REGISTER'}

    next: BoolProperty() # type: ignore

    def execute(self, context):
        bpy.ops.screen.keyframe_jump(next=self.next)
        get_outfit_properties().animation_frame = context.scene.frame_current

        return {'FINISHED'}


CLASSES = [
    FrameJump,
    KeyframeJump
]   