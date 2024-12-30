import os
import bpy
import json

from math          import pi
from pathlib       import Path
from mathutils     import Quaternion
from bpy.types     import Operator, Object, PoseBone, Context
from bpy.props     import StringProperty, BoolProperty

    
class PoseApply(Operator):
    bl_idname = "ya.pose_apply"
    bl_label = ""
    bl_options = {'UNDO'}

    filepath: StringProperty() # type: ignore
    filter_glob: bpy.props.StringProperty(
        default='*.pose',
        options={'HIDDEN'}) # type: ignore
    reset: BoolProperty(default=False) # type: ignore

    @classmethod
    def description(cls, context, properties):
        if properties.reset:
            return """Reset armature"""
        else:
            return """Select and apply .pose to armature:
            * Hold Shift to reapply.
            * Hold Alt to open folder"""
        
    @classmethod
    def poll(self, context):
        return bpy.data.objects[context.scene.outfit_props.armatures].type == "ARMATURE"
    
    def invoke(self, context, event):
        self.actual_file = Path(self.filepath) 

        if self.reset:
            self.execute(context)
        elif event.alt and event.type == "LEFTMOUSE" and self.actual_file.is_file():
            actual_dir = self.actual_file.parent
            os.startfile(str(actual_dir))
        elif event.shift and event.type == "LEFTMOUSE" and self.actual_file.is_file():
            self.execute(context)
        elif event.type == "LEFTMOUSE":
            context.window_manager.fileselect_add(self)
        else:
             self.report({"ERROR"}, "Not a valid pose file!")
    
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        pose_file        = Path(self.filepath)
        skeleton: Object = bpy.data.objects[context.scene.outfit_props.armatures]
        if self.reset:
            self.reset_armature(context, skeleton)
            return {'FINISHED'}
        elif pose_file.exists() and pose_file.suffix == ".pose": 
            context.scene.outfit_props.pose_display_directory = pose_file.stem
            self.apply(context, skeleton, pose_file)
            self.report({'INFO'}, f"{pose_file.stem} selected!")  
        else:
            self.report({'ERROR'}, "Not a valid pose file!")

        return {'FINISHED'}
    
    def reset_armature(self, context:Context, skeleton:Object):
        skeleton: Object = bpy.data.objects[context.scene.outfit_props.armatures]
        context.view_layer.objects.active = skeleton
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.transforms_clear()
        bpy.ops.pose.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')

    def apply(self, context:Context, skeleton:Object, pose_file:Path):
        # Get world space matrix of armature
        self.armature_world = skeleton.matrix_world
        # XIV armatures are rotated -90 on the X axis, this will align rotation with Blender's default world space
        self.rotation_x90   = Quaternion((1, 0, 0), pi / 2)
        # Checks if the armature has an unapplied World Space rotation, typical for TT n_roots
        self.is_rotated     = skeleton.rotation_euler[0] != 0.0
        
        with open(pose_file, "r") as file:
            pose = json.load(file)
        
        # We need to update Blender's depsgraph per bone level or else child bones will not be given the proper local space rotation
        bone_levels = self.get_bone_hierarchy_levels(skeleton)

        for level in range(max(bone_levels.keys())):
            level_bones = bone_levels[level]
            for bone in level_bones:
                self.convert_rotation_space(skeleton, pose["Bones"], bone)
            skeleton.update_tag(refresh={'DATA'})
            context.evaluated_depsgraph_get().update()
    
    def convert_rotation_space(self, skeleton:Object, source_bone_rotations:dict[str, str], bone:PoseBone):
        try:
            if bone.name not in source_bone_rotations:
                return
                
            # Get rotation data for current bone
            rotation_str = source_bone_rotations[bone.name]["Rotation"]
            rotation = rotation_str.split(", ")
            # XYZW to WXYZ
            rotation = [float(rotation[3]), float(rotation[0]), float(rotation[1]), float(rotation[2])]
            rotation = Quaternion(rotation)
            
            rotation_matrix = rotation.to_matrix().to_4x4()
            
            if self.is_rotated:
                final_rotation      = rotation_matrix
            else:
                # Include skeleton transformation matrix
                world_rotation      = (rotation_matrix @ self.armature_world).to_quaternion()
                
                # Corrects world rotation to match devkit skeleton's
                corrected_rotation  = self.rotation_x90 @ world_rotation
                final_rotation      = corrected_rotation.to_matrix().to_4x4()
            
            # Gives us local space rotation for the bone
            bone_rotation = skeleton.convert_space(
                pose_bone=bone,
                matrix=final_rotation,
                from_space='POSE',
                to_space='LOCAL'
            )
            
            bone.rotation_mode = 'QUATERNION'
            bone.rotation_quaternion = bone_rotation.to_quaternion()

        except (KeyError, ValueError):
            return
    
    def get_bone_hierarchy_levels(self, skeleton: Object) -> dict[int, list]:
        bone_levels: dict[int, list] = {}
        
        def calculate_bone_level(bone: PoseBone, level: int):
            bone_levels.setdefault(level, [])
            bone_levels[level].append(bone)
            for child in bone.children:
                calculate_bone_level(child, level + 1)
        
        for bone in skeleton.pose.bones:
            if not bone.parent:
                calculate_bone_level(bone, 0)
        
        return bone_levels
        

CLASSES = [
    PoseApply
]