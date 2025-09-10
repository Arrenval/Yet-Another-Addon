import bpy

from ..props   import get_window_props
from bpy.types import Operator
from bpy.props import BoolProperty


class FrameJump(Operator):
    bl_idname = "ya.frame_jump"
    bl_label = "Jump to Endpoint"
    bl_description = "Jump to first/last frame in frame range"
    bl_options = {"UNDO", "REGISTER"}

    end: BoolProperty(options={'HIDDEN'}) # type: ignore
 
    def execute(self, context):
        bpy.ops.screen.frame_jump(end=self.end)
        get_window_props().animation_frame = context.scene.frame_current

        return {'FINISHED'}

class KeyframeJump(Operator):
    bl_idname = "ya.keyframe_jump"
    bl_label = "Jump to Keyframe"
    bl_description = "Jump to previous/next keyframe"
    bl_options = {"UNDO", "REGISTER"}

    next: BoolProperty(options={'HIDDEN'}) # type: ignore

    def execute(self, context):
        bpy.ops.screen.keyframe_jump(next=self.next)
        get_window_props().animation_frame = context.scene.frame_current

        return {'FINISHED'}


CLASSES = [
    FrameJump,
    KeyframeJump
]   