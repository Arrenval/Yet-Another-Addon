import bpy

from mathutils     import Vector
from bpy.types     import Object

from ...props      import Armature, KaosArmature
from .imp.bones    import BoneData, calc_bone_data, blend_bones
from ...xivpy.kaos import Node
from ...xivpy.sklb import XIVSkeleton


def get_floats(target, values: list[float]) -> None:
    target.pos     = values[:3]
    target.rot     = [values[7], values[4], values[5], values[6]]
    target.scale   = values[8:]
    target.unknown = values[3]

class SklbImport:

    def __init__(self, sklb: XIVSkeleton) -> None:
        self.sklb  = sklb
        self.kaos  = sklb.kaos
        self.nodes = sklb.kaos.nodes
        
    @classmethod
    def from_file(cls, file_path: str, import_name: str) -> Object:
        importer = cls(XIVSkeleton.from_file(file_path))
        return importer._create_armature(import_name)

    @classmethod
    def from_bytes(cls, data: bytes, import_name: str) -> Object:
        importer = cls(XIVSkeleton.from_bytes(data))
        return importer._create_armature(import_name)
    
    def _create_armature(self, name: str) -> None:
        sklt_node = self.kaos.get_skeleton_node()
        bone_parents: list[int]   = sklt_node["parentIndices"]
        bone_values : list[float] = sklt_node["referencePose"]
        bone_list   : list[str]   = self.kaos.get_bone_list(sklt_node)
        bone_data = calc_bone_data(bone_list, bone_parents, bone_values)
        blend_bones(bone_list, bone_data)

        armature = bpy.data.armatures.new(name)
        new_obj  = bpy.data.objects.new(name, armature)
        bpy.context.collection.objects.link(new_obj)
        bpy.context.view_layer.objects.active = new_obj
        
        try:
            bpy.ops.object.mode_set(mode='EDIT')
            self._create_bones(armature, bone_data)
        finally:
            bpy.ops.object.mode_set(mode='OBJECT')

        self._store_cache(armature, bone_list, bone_data)
        self._headers(armature.kaos, bone_list)
        self._extract_mappers(armature.kaos)

        armature.update_tag()
        return new_obj
        
    def _create_bones(self, armature: Armature, bone_data: dict[str, BoneData]) -> None:
        for bone, data in bone_data.items():
            new_bone = armature.edit_bones.new(bone)
            arma_mat = data.arma_mat

            new_bone.head     = arma_mat @ Vector((0, 0, 0))
            new_bone.tail     = arma_mat @ Vector((1, 0, 0))
            new_bone.length   = data.length
            new_bone.kaos_unk = data.unknown

            new_bone.inherit_scale = 'NONE'
            new_bone.align_roll(arma_mat @ Vector((0, 0, 1)) - new_bone.head)
            
        for bone, data in bone_data.items():
            if data.parent is not None:
                armature.edit_bones[bone].parent = armature.edit_bones[data.parent]
        
        for bone in ("iv_c_mune_l", "iv_c_mune_r"):
            if bone in bone_data:
                armature.edit_bones[bone].inherit_scale = 'FULL'

    def _store_cache(self, armature: Armature, bone_list: list[str], bone_data: dict[str, BoneData]) -> None:
        for idx, bone in enumerate(bone_list):
            new_bone       = armature.kaos.bone_list.add()
            new_bone.name  = bone
            new_bone.index = idx
            
            trs, rot, scl = armature.bones[bone].matrix_local.decompose()
            parent = armature.bones[bone].parent
            cache  = armature.kaos.bone_cache.add()
            cache.name  = bone
            cache.ctrs   = trs
            cache.crot   = rot
            cache.cscl   = scl
            cache.parent = parent.name if parent else "" 

            get_floats(cache, bone_data[bone].raw)

    def _extract_mappers(self, arma_kaos: KaosArmature) -> None:
        mapper_nodes = self.kaos.get_mapper_nodes()
        for idx, (name, node) in enumerate(mapper_nodes):
            # Mappers come in near identical pairs referencing the same base skeleton.
            # The first one has no rotation data so we discard it.
            # We keep the second one as it has complete mapping data we can use to recreate the mapper we skipped. 
            if not idx % 2:
                continue
            if not name.isdigit():
                raise Exception(f"Invalid Mapper Name: {name}")

            mapper         = arma_kaos.mappers.add()
            mapper.race_id = self.sklb.header.get_race_id_str(int(name))
            get_floats(mapper, node["extractedMotionMapping"])

            parent  = self.nodes[node["skeletonA"]] # This is the base/parent
            target  = self.nodes[node["skeletonB"]] # This is the target, also the main sklb
            blist_a = self.kaos.get_bone_list(parent) 
            blist_b = self.kaos.get_bone_list(target) 
            for node_idx in node["simpleMappings"]:
                bmap       = mapper.bone_maps.add()
                nmap: Node = self.nodes[node_idx]

                bmap.bone_a = blist_a[nmap["boneA"]]
                bmap.bone_b = blist_b[nmap["boneB"]]
                get_floats(bmap, nmap["aFromBTransform"])
            
            for idx, bone_name in enumerate(blist_a):
                mbone      = mapper.bone_list.add()
                parent_idx = parent["parentIndices"][idx]

                mbone.name   = bone_name
                mbone.parent = blist_a[parent_idx] if parent_idx > -1 else ""
                get_floats(mbone, parent["referencePose"][idx])

    def _headers(self, arma_kaos: KaosArmature, bone_list: list[str]) -> None:
        bone_indices = arma_kaos.get_bone_indices()
        arma_kaos.race_id = self.sklb.header.get_race_id_str()
        for idx, layer in enumerate(self.sklb.anim_data.layers):
            new_layer = arma_kaos.anim_layers.add()
            new_layer.id = layer.id
            new_layer.name = f"Layer #{idx + 1}"

            for bone_idx in layer.bone_indices:
                new_bone  = new_layer.bone_list.add()
                bone_name = bone_list[bone_idx]

                new_bone.name  = bone_name
                new_bone.index = bone_indices[bone_name]
