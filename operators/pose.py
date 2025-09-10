import os
import bpy
import json
import gzip
import base64

from math           import pi
from pathlib        import Path
from ..props        import get_studio_props, get_window_props
from mathutils      import Quaternion
from bpy.types      import Operator, PoseBone, Context, Modifier
from bpy.props      import StringProperty, BoolProperty
from ..mesh.objects import visible_meshobj


class PoseApply(Operator):
    bl_idname = "ya.pose_apply"
    bl_label = ""
    bl_options = {"UNDO", "REGISTER"}

    filepath:       StringProperty(options={"HIDDEN"}) # type: ignore
    filter_glob:    StringProperty(
        default="*.pose",
        options={"HIDDEN"}) # type: ignore
    
    reset:          BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"}) # type: ignore
    use_clipboard:  BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"}) # type: ignore
   
    @classmethod
    def description(cls, context, properties):
        if properties.reset:
            return "Click to reset pose. SHIFT click to reset scale"
   
        if properties.use_clipboard:
            return "Apply C+ scaling from clipboard"
        else:
            if get_window_props().scaling_armature:
                return """Select and apply scaling to armature:
            *Hold Shift to reapply.
            *Hold Alt to open folder"""
            else:
                return """Select and apply pose to armature:
                *Hold Shift to reapply.
                *Hold Alt to open folder"""
        
    @classmethod
    def poll(cls, context):
        return get_studio_props().outfit_armature
    
    def invoke(self, context, event):
        self.actual_file = Path(self.filepath)

        if self.reset:
            scaling = False
            if event.shift:
                scaling = True
            return self.reset_armature(context, scaling)
        
        elif self.use_clipboard:
            return self.execute(context)
        
        elif event.alt and event.type == "LEFTMOUSE" and self.actual_file.is_file():
            actual_dir = self.actual_file.parent
            os.startfile(str(actual_dir))

        elif event.shift and event.type == "LEFTMOUSE" and self.actual_file.is_file():
            return self.execute(context)

        elif event.type == "LEFTMOUSE":
            context.window_manager.fileselect_add(self)

        else:
             self.report({"ERROR"}, "Not a valid pose file!")
    
        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        self.props        = get_studio_props()
        self.window       = get_window_props()
        self.scaling      = self.window.scaling_armature
        self.old_bone_map = {
            "j_asi_e_l": "ToesLeft",
            "j_asi_d_l": "FootLeft",
            "j_asi_c_l": "CalfLeft",
            "j_asi_b_l": "KneeLeft",
            "j_asi_a_l": "LegLeft",
            "j_asi_e_r": "ToesRight",
            "j_asi_d_r": "FootRight",
            "j_asi_c_r": "CalfRight",
            "j_asi_b_r": "KneeRight",
            "j_asi_a_r": "LegRight",
            "j_ko_b_r": "PinkyBRight",
            "j_ko_a_r": "PinkyARight",
            "j_kusu_b_r": "RingBRight",
            "j_kusu_a_r": "RingARight",
            "j_naka_b_r": "MiddleBRight",
            "j_naka_a_r": "MiddleARight",
            "j_hito_b_r": "IndexBRight",
            "j_hito_a_r": "IndexARight",
            "j_oya_b_r": "ThumbBRight",
            "j_oya_a_r": "ThumbARight",
            "j_te_r": "HandRight",
            "n_hte_r": "WristRight",
            "j_ude_b_r": "ForearmRight",
            "j_ude_a_r": "ArmRight",
            "n_hhiji_r": "ElbowRight",
            "n_hkata_r": "ShoulderRight",
            "j_ko_b_l": "PinkyBLeft",
            "j_ko_a_l": "PinkyALeft",
            "j_kusu_b_l": "RingBLeft",
            "j_kusu_a_l": "RingALeft",
            "j_naka_b_l": "MiddleBLeft",
            "j_naka_a_l": "MiddleALeft",
            "j_hito_b_l": "IndexBLeft",
            "j_hito_a_l": "IndexALeft",
            "j_oya_b_l": "ThumbBLeft",
            "j_oya_a_l": "ThumbALeft",
            "j_te_l": "HandLeft",
            "n_hte_l": "WristLeft",
            "j_ude_b_l": "ForearmLeft",
            "j_ude_a_l": "ArmLeft",
            "n_hhiji_l": "ElbowLeft",
            "n_hkata_l": "ShoulderLeft",
            "j_kao": "Head",
            "j_kubi": "Neck",
            "j_kosi": "Waist",
            "j_sebo_a": "SpineA",
            "j_sebo_b": "SpineB",
            "j_sebo_c": "SpineC",
            "j_mune_r": "BreastRight",
            "j_mune_l": "BreastLeft",
            "j_sako_r": "ClavicleRight",
            "j_sako_l": "ClavicleLeft",
            "n_throw": "Throw",
            "n_hara": "Root",
            "j_ago": "Jaw",
            "j_f_dlip_a": "LipLowerA",
            "j_f_dlip_b": "LipLowerB",
            "j_f_ulip_a": "LipUpperA",
            "j_f_ulip_b": "LipUpperB",
            "j_f_lip_l": "LipsLeft",
            "j_f_lip_r": "LipsRight",
            "j_f_hoho_r": "CheekRight",
            "j_f_hoho_l": "CheekLeft",
            "j_f_hana": "Nose",
            "n_sippo_a": "TailA",
            "n_sippo_b": "TailB",
            "n_sippo_c": "TailC",
            "n_sippo_d": "TailD",
            "n_sippo_e": "TailE",
            "j_f_memoto": "Bridge",
            "j_f_umab_l": "EyelidUpperLeft",
            "j_f_dmab_l": "EyelidLowerLeft",
            "j_f_eye_l": "EyeLeft",
            "j_f_umab_r": "EyelidUpperRight",
            "j_f_dmab_r": "EyelidLowerRight",
            "j_f_eye_r": "EyeRight",
            "j_f_miken_l": "BrowLeft",
            "j_f_mayu_l": "EyebrowLeft",
            "j_f_miken_r": "BrowRight",
            "j_f_mayu_r": "EyebrowRight",
            "j_mimi_r": "EarRight",
            "j_mimi_l": "EarLeft",
            "n_ear_a_l": "EarringALeft",
            "n_ear_b_l": "EarringBLeft",
            "n_ear_a_r": "EarringARight",
            "n_ear_b_r": "EarringBRight"
            }
    
        pose_file         = Path(self.filepath)
        self.armature_obj = self.props.outfit_armature

        visibility = self.armature_obj.hide_get()
        self.armature_obj.hide_set(state=False)

        if self.use_clipboard or (pose_file.exists() and pose_file.suffix == ".pose"):
            if not self.use_clipboard:
                self.props.pose_display_directory = pose_file.stem
            apply_status = self.apply(context, pose_file)

            if apply_status == "JSON":
                self.report({"ERROR"}, "Not a valid C+ preset.")
            else:
                self.report({"INFO"}, f"{pose_file.stem} selected!")  

        else:
            self.report({"ERROR"}, "Not a valid pose file!")

        self.armature_obj.hide_set(state=visibility)
        return {"FINISHED"}
    
    def reset_armature(self, context: Context, scaling:bool):
        armature_obj = get_studio_props().outfit_armature
        for bone in armature_obj.pose.bones:
            if scaling:
                bone.scale = (1.0, 1.0, 1.0)
            else:
                bone.location = (0.0, 0.0, 0.0)
                
                if bone.rotation_mode == "QUATERNION":
                    bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
                else:
                    bone.rotation_euler = (0.0, 0.0, 0.0)

        context.view_layer.update()
        return {"FINISHED"}

    def apply(self, context: Context, pose_file: Path) -> None:
        if self.use_clipboard:
            try:
                clipboard = bpy.context.window_manager.clipboard
                clip_result= gzip.decompress(base64.b64decode(clipboard))
                pose = json.loads(clip_result[1:].decode("utf-8"))
            except Exception as e:
                raise f"Error reading clipboard: {e}"
        else:
            with open(pose_file, "r") as file:
                pose = json.load(file)
 
        if self.scaling or self.use_clipboard:
            for bone in self.armature_obj.data.bones:
                bone.inherit_scale = "NONE"
            for bone in self.armature_obj.pose.bones:
                self.scale_bones(pose["Bones"], bone)

        else:
            # Checks if the armature has an unapplied World Space x axis rotation, typical for TT n_roots
            self.is_rotated = self.armature_obj.rotation_euler[0] != 0.0

            # Get world space matrix of armature
            if self.is_rotated:
                self.armature_world = self.armature_obj.matrix_world.copy()
            else:
                # Apply 90° X rotation for coordinate system correction
                self.x_rotation = Quaternion((1, 0, 0), pi / 2).to_matrix().to_4x4()
                self.armature_world = self.armature_obj.matrix_world @ self.x_rotation

            visible_mesh = visible_meshobj()
            # Dictionary of objects linked to the skeleton and their armature modifier state.
            # We toggle off any armature modifiers to reduce render time for the depsgraph update later.
            obj_skeleton: dict[str, tuple[str, bool]] = {}
            for obj in visible_mesh:
                arm_modifiers: list[Modifier] = [modifier for modifier in obj.modifiers if modifier.type == "ARMATURE"]
                for modifier in arm_modifiers:
                    if modifier.object == self.armature_obj: 
                        obj_skeleton[obj.name] = modifier.name, modifier.show_viewport
                        modifier.show_viewport = False


            # We need to update Blender"s depsgraph per bone level or else child bones will not be given the proper local space rotation
            bone_levels = self.get_bone_hierarchy_levels()
            for level in range(max(bone_levels.keys())):
                level_bones = bone_levels[level]
                for bone in level_bones:
                    self.convert_rotation_space(pose["Bones"], bone)

                self.armature_obj.update_tag(refresh={"DATA"})
                context.evaluated_depsgraph_get().update()
            
            for obj_name, (modifer, modifier_state) in obj_skeleton.items():
                bpy.data.objects[obj_name].modifiers[modifer].show_viewport = modifier_state
    
    def convert_rotation_space(self, source_bone_rotations: dict[str, str], bone: PoseBone) -> None:
        bone_name = bone.name
        if bone_name not in source_bone_rotations:
            if bone_name not in self.old_bone_map:
                return
            if self.old_bone_map[bone_name] not in source_bone_rotations:
                return
            bone_name = self.old_bone_map[bone.name]
            
        # Get rotation data for current bone
        rotation_str = source_bone_rotations[bone_name]["Rotation"]
        rotation = rotation_str.split(", ")
        # XYZW to WXYZ
        rotation = Quaternion((float(rotation[3]), float(rotation[0]), float(rotation[1]), float(rotation[2])))
        
        if self.is_rotated:
            final_matrix        = rotation.to_matrix().to_4x4()
        else:
            # Adjust global space of quaternion
            corrected_rotation  = Quaternion((1, 0, 0), pi / 2) @ rotation
            final_matrix        = corrected_rotation.to_matrix().to_4x4()
        
        # Gives us local space rotation for the bone
        bone_rotation = self.armature_obj.convert_space(
            pose_bone=bone,
            matrix=final_matrix,
            from_space="POSE",
            to_space="LOCAL"
        )
        
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = bone_rotation.to_quaternion()

    def get_bone_hierarchy_levels(self) -> dict[int, list]:
        bone_levels: dict[int, list] = {}
        
        def calculate_bone_level(bone: PoseBone, level: int):
            bone_levels.setdefault(level, [])
            bone_levels[level].append(bone)
            for child in bone.children:
                calculate_bone_level(child, level + 1)
        
        for bone in self.armature_obj.pose.bones:
            if not bone.parent:
                calculate_bone_level(bone, 0)
        
        return bone_levels

    def scale_bones(self, source_bone_scaling: dict[str, str], bone: PoseBone):
        bone_name = bone.name
        if bone_name not in source_bone_scaling:
            if bone_name not in self.old_bone_map:
                return
            if self.old_bone_map[bone_name] not in source_bone_scaling:
                return
            bone_name = self.old_bone_map[bone.name]
            
        # Get scaling data for current bone
        try:
            scaling_str = source_bone_scaling[bone_name]["Scale"]
            scaling = scaling_str.split(", ")
            bone.scale[0] = float(scaling[0])
            bone.scale[1] = float(scaling[1])
            bone.scale[2] = float(scaling[2])
        except:
            scaling_dict = source_bone_scaling[bone_name]["Scaling"]
            bone.scale[0] = float(scaling_dict["X"])
            bone.scale[1] = float(scaling_dict["Y"])
            bone.scale[2] = float(scaling_dict["Z"])     
    

CLASSES = [
    PoseApply
]