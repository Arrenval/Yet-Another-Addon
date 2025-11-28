import bpy
import math
import numpy as np

from typing        import TYPE_CHECKING
from mathutils     import Vector, Quaternion, Matrix
from numpy.typing  import NDArray
from bpy.types     import PoseBone

from ...xivpy.kaos import QuantisedAnimation
from ...xivpy.sklb import XIVSkeleton
from ...xivpy.pap  import XIVAnim, AnimInfo
from ...xivpy.kaos.animation.tracks import create_matrix_tracks, create_raw_tracks

if TYPE_CHECKING:
    from ...xivpy.kaos import hkaAnimationBindingNode, hkaAnimationNode


COMPRESSION = {"hkaInterleavedUncompressedAnimation", "hkaSplineCompressedAnimation", "hkaQuantizedAnimation",}

USED_DEFINITIONS = {
                        "hkRootLevelContainer"               : "0",
                        "hkRootLevelContainerNamedVariant"   : "1",
                        "hkBaseObject"                       : "0",
                        "hkReferencedObject"                 : "0",
                        "hkaAnimationContainer"              : "1",
                        "hkaSkeleton"                        : "5",
                        "hkaBone"                            : "0",
                        "hkaSkeletonLocalFrameOnBone"        : "0",
                        "hkLocalFrame"                       : "0",
                        "hkaSkeletonPartition"               : "1",
                        "hkaAnimation"                       : "3",
                        "hkaAnimatedReferenceFrame"          : "0",
                        "hkaAnnotationTrack"                 : "0",
                        "hkaAnnotationTrackAnnotation"       : "0",
                        "hkaAnimationBinding"                : "3",
                        "hkaBoneAttachment"                  : "2",
                        "hkaMeshBinding"                     : "3",
                        "hkxMesh"                            : "1",
                        "hkxMeshSection"                     : "5",
                        "hkxVertexBuffer"                    : "1",
                        "hkxVertexBufferVertexData"          : "2",
                        "hkxVertexDescription"               : "1",
                        "hkxVertexDescriptionElementDecl"    : "4",
                        "hkxIndexBuffer"                     : "1",
                        "hkxAttributeHolder"                 : "2",
                        "hkxAttributeGroup"                  : "0",
                        "hkxAttribute"                       : "1",
                        "hkxMaterial"                        : "5",
                        "hkxMaterialTextureStage"            : "1",
                        "hkxMaterialProperty"                : "0",
                        "hkxVertexAnimation"                 : "0",
                        "hkxVertexAnimationUsageMap"         : "0",
                        "hkMeshBoneIndexMapping"             : "0",
                        "hkxMeshUserChannelInfo"             : "0",
                        "hkaMeshBindingMapping"              : "0",
                        "hkaInterleavedUncompressedAnimation": "0",
                        "hkaSplineCompressedAnimation"       : "0",
                        "hkaQuantizedAnimation"              : "0"
                    }

class PapImport:

    def __init__(self, pap: XIVAnim, info: AnimInfo) -> None:
        self.pap  = pap
        self.info = info

    @classmethod
    def from_pap(cls, pap: XIVAnim, info: AnimInfo, skeleton: XIVSkeleton, animation: 'hkaAnimationNode', binding: 'hkaAnimationBindingNode') -> None:
        importer = cls(pap, info)
        return importer._create_action(skeleton, animation, binding)
    
    def _create_action(self, skeleton: XIVSkeleton, animation: 'hkaAnimationNode', binding: 'hkaAnimationBindingNode') -> None:
        hkaskeleton = skeleton.kaos.get_skeleton_node()
        bone_list   = skeleton.kaos.get_bone_list(hkaskeleton)

        if animation.name == "hkaQuantizedAnimation":
            final_animation = QuantisedAnimation.from_bytes(animation, binding["transformTrackToBoneIndices"])
            frame_tracks    = create_raw_tracks(final_animation, hkaskeleton, binding, bone_list)

        action_name = self.info.name
        if action_name in bpy.data.actions:
            action = bpy.data.actions[action_name]
            action.fcurves.clear()
        else:
            action = bpy.data.actions.new(name=action_name)
        frame_count  = final_animation.header.frame_count
        self.armature = bpy.context.active_object

        if self.armature.animation_data is None:
            self.armature.animation_data_create()

        self.armature.animation_data.action = action
        for bone_name, track in frame_tracks.items():
            pose_bone = self.armature.pose.bones.get(bone_name)
            if not pose_bone:
                continue
            
            pose_bone.rotation_mode = 'QUATERNION'
            self._local_to_world_matrix(track, pose_bone, bone_name, frame_count)
            
    def _armature_to_world_matrix(self, track: NDArray, pose_bone: PoseBone, bone_name: str, frame_count: int):
        # This function does not apply the transformation properly, WIP
        bone = self.armature.data.bones[bone_name]
        if bone.parent:
            rest_arma = bone.parent.matrix_local
        else:
            rest_arma = Matrix.Identity()

        rest_arma_inv = rest_arma.inverted()
        
        for frame_idx in range(min(100, frame_count)):
            blender_frame = 1 + frame_idx

            arma_mat = Matrix(track[: , : , frame_idx].tolist())

            pose_basis = rest_arma_inv @ arma_mat
            loc, rot, scale = pose_basis.decompose()
            pose_bone.location = loc
            pose_bone.rotation_quaternion = rot
            
            pose_bone.keyframe_insert(data_path="location", frame=blender_frame, group=bone_name)
            pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=blender_frame, group=bone_name)

    def _local_to_world_matrix(self, track: dict[str, NDArray], pose_bone: PoseBone, bone_name: str, frame_count: int):
        trs = track
        rot = track
        for frame_idx in range(min(100, frame_count)):
            blender_frame = 1 + frame_idx

            t = Vector(trs[:3, frame_idx])
            r = Quaternion([
                rot[7, frame_idx], 
                rot[4, frame_idx], 
                rot[5, frame_idx], 
                rot[6, frame_idx], 
            ])
            
            anim_local = Matrix.Translation(t) @ r.to_matrix().to_4x4()
            
            if pose_bone.parent:
                parent_world = pose_bone.parent.matrix
            else:
                parent_world = Matrix.Identity(4)
            
            pose_bone.matrix = parent_world @ anim_local
            pose_bone.keyframe_insert(data_path="location", frame=blender_frame, group=bone_name)
            pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=blender_frame, group=bone_name)
