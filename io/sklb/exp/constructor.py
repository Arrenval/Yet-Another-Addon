import numpy as np

from typing         import Literal, TYPE_CHECKING

from .nodes         import create_node
from .bones         import get_bone_data, BoneNode
from ....props      import Armature, SklbMapper
from ....xivpy.kaos import Tagfile, Definition, get_definitions

if TYPE_CHECKING:
    from ....xivpy.kaos import (hkRootLevelContainerNamedVariantNode as VariantNode,
                                  hkaSkeletonNode as SkelNode, 
                                  hkaSkeletonMapperNode as MapperNode,
                                  hkaSkeletonMapperDataNode as MapperDataNode)

MAPPER_DEFINITIONS = {"hkaSkeletonMapper", "hkaSkeletonMapperData", 
                      "hkaSkeletonMapperDataSimpleMapping", "hkaSkeletonMapperDataChainMapping"}

USED_DEFINITIONS = {
                        "hkRootLevelContainer"              : "0",
                        "hkRootLevelContainerNamedVariant"  : "1",
                        "hkBaseObject"                      : "0",
                        "hkReferencedObject"                : "0",
                        "hkaAnimationContainer"             : "1",
                        "hkaSkeleton"                       : "3",
                        "hkaBone"                           : "0",
                        "hkaSkeletonLocalFrameOnBone"       : "0",
                        "hkLocalFrame"                      : "0",
                        "hkaAnimation"                      : "3",
                        "hkaAnimatedReferenceFrame"         : "0",
                        "hkaAnnotationTrack"                : "0",
                        "hkaAnnotationTrackAnnotation"      : "0",
                        "hkaAnimationBinding"               : "1",
                        "hkaBoneAttachment"                 : "2",
                        "hkaMeshBinding"                    : "3",
                        "hkxMesh"                           : "1",
                        "hkxMeshSection"                    : "2",
                        "hkxVertexBuffer"                   : "1",
                        "hkxVertexBufferVertexData"         : "0",
                        "hkxVertexDescription"              : "1",
                        "hkxVertexDescriptionElementDecl"   : "2",
                        "hkxIndexBuffer"                    : "1",
                        "hkxAttributeHolder"                : "2",
                        "hkxAttributeGroup"                 : "0",
                        "hkxAttribute"                      : "1",
                        "hkxMaterial"                       : "2",
                        "hkxMaterialTextureStage"           : "1",
                        "hkxMaterialProperty"               : "0",
                        "hkxMeshUserChannelInfo"            : "0",
                        "hkaMeshBindingMapping"             : "0",
                        "hkaSkeletonMapper"                 : "0",
                        "hkaSkeletonMapperData"             : "1",
                        "hkaSkeletonMapperDataSimpleMapping": "0",
                        "hkaSkeletonMapperDataChainMapping" : "0"
                    }

def sort_definitions(mappers: list[int]) -> list[Definition]:
    all_definitions = get_definitions()

    definitions = []
    for name, version in USED_DEFINITIONS.items():
        if not mappers and name in MAPPER_DEFINITIONS:
            continue

        definitions.append(Definition.from_dict(all_definitions[name][version]))
    
    return definitions

class SklbConstructor:

    def __init__(self, kaos: Tagfile, armature: Armature, bone_indices: dict[str, int]):
        self.kaos          = kaos
        self.armature      = armature
        self.sklb_indices  = bone_indices
        self.map_ids       = armature.kaos.get_mappers()
        self.map_count     = len(self.map_ids) * 2
        self.sklb_idx: int = None

        self.mappers : list[int]           = []
        self.variants: list['VariantNode'] = []
        
    @classmethod
    def from_armature(cls, kaos: Tagfile, armature: Armature, bone_indices: dict[str, int]) -> 'SklbConstructor':
        constructor = cls(kaos, armature, bone_indices)
        constructor._create_reference_nodes()
        return constructor
    
    def _get_ref_node(self, container: Literal['MAPPER']) -> 'MapperNode':
        if container == 'MAPPER':
            idx = self.mappers.pop()
            self.kaos.references.append(idx)
            return self.kaos.nodes[idx]

    def _create_reference_nodes(self) -> None:
        self.kaos.definitions += sort_definitions(self.map_ids)
        self.kaos.create_context(read=False)

        root_idx, root = create_node("hkRootLevelContainer", self.kaos)
        self.kaos.root_idx = root_idx

        # The order isn't super intuitive but it mimics how the nodes in the game's sklb are ordered.
        for _ in range(self.map_count):
            mapper_idx = create_node("hkaSkeletonMapper", self.kaos, store_ref=False)[0]
            self.mappers.append(mapper_idx)
        
        anim = create_node("hkaAnimationContainer", self.kaos)[1]

        variant_count = 1 + self.map_count
        for idx in range(variant_count):
            variant_idx, variant = create_node("hkRootLevelContainerNamedVariant", self.kaos)
            variant["variant"]   = idx + 1

            self.variants.append(variant)
            root["namedVariants"].append(variant_idx)
        
        self.sklb_idx, skl_node = create_node("hkaSkeleton", self.kaos)
        self._create_hkbones(skl_node, self.sklb_indices, get_bone_data(self.armature, self.sklb_indices))
        anim["skeletons"].append(self.sklb_idx)

        anim_variant              = self.variants.pop()
        anim_variant["name"]      = anim.definition.name
        anim_variant["className"] = anim.definition.name

        for mapper in reversed(self.armature.kaos.mappers):
            if not mapper.bone_maps:
                continue
            self.skla_indices = mapper.get_bone_indices()
            self._create_skeleton_mapper(mapper)

    def _create_hkbones(self, skl_node: 'SkelNode', bone_indices: dict[str, int], bone_data: dict[str, BoneNode]) -> None:
        skl_node["name"] = "skeleton"

        ref_pose = []
        for bone_name in bone_indices.keys():
            node_idx, bnode = create_node("hkaBone", self.kaos)
            bnode["name"]   = bone_name

            skl_node["bones"].append(node_idx)
            skl_node["parentIndices"].append(bone_data[bone_name].parent)
            ref_pose.append(bone_data[bone_name].to_list())

        skl_node["referencePose"] = np.array(ref_pose, dtype=np.float32)

    def _create_skeleton_mapper(self, mapper: SklbMapper) -> int:
        header_idx = str(self.map_ids.index(int(mapper.race_id)))
        mapper_data: list['MapperDataNode'] = []

        mdata_node = self._create_mapper_data(mapper, self._get_ref_node('MAPPER'), self.variants.pop(), header_idx)
        skla_idx, skl_node = create_node("hkaSkeleton", self.kaos)
        mapper_data.append(mdata_node)

        self._create_simple_mappings(mapper, mdata_node, True)
        self._create_hkbones(skl_node, self.skla_indices, get_bone_data(mapper, self.skla_indices))
        
        mdata_node = self._create_mapper_data(mapper, self._get_ref_node('MAPPER'), self.variants.pop(), header_idx)
        self._create_simple_mappings(mapper, mdata_node, False)
        mapper_data.append(mdata_node)

        for data in mapper_data:
            data["skeletonA"] = skla_idx

    def _create_mapper_data(self, mapper: SklbMapper, mapper_node: 'MapperNode', variant: 'VariantNode', header_idx: int) -> 'MapperDataNode':
        mapper_idx, mapper_data = create_node("hkaSkeletonMapperData", self.kaos)

        mapper_data["skeletonB"] = self.sklb_idx
        mapper_data["extractedMotionMapping"] = mapper.get_values()

        mapper_data["mappingType"]       = 1
        mapper_data["keepUnmappedLocal"] = 1

        variant["name"]      = header_idx
        variant["className"] = "hkaSkeletonMapper"

        mapper_node["mapping"] = mapper_idx
        
        return mapper_data
    
    def _create_simple_mappings(self, mapper: SklbMapper, mapper_data: 'MapperDataNode', rotation: bool) -> None:
        for bmap in mapper.bone_maps:
            bmap_idx, bmap_node = create_node("hkaSkeletonMapperDataSimpleMapping", self.kaos)
            bmap_node["boneA"] = self.skla_indices[bmap.bone_a]
            bmap_node["boneB"] = self.sklb_indices[bmap.bone_b]
            bmap_node["aFromBTransform"] = bmap.get_values(rotation)
            mapper_data["simpleMappings"].append(bmap_idx)
