from typing         import Literal, overload, TYPE_CHECKING

from ....xivpy.kaos import Tagfile, Node

if TYPE_CHECKING:
    from ....xivpy.kaos import (hkRootLevelContainerNode,
                                hkRootLevelContainerNamedVariantNode, hkaAnimationContainerNode,
                                hkaSkeletonNode, hkaBoneNode,
                                hkaSkeletonMapperNode, hkaSkeletonMapperDataNode, 
                                hkaSkeletonMapperDataSimpleMappingNode)
                              

FIELDS = {
            "hkRootLevelContainer"            : {"namedVariants"},
            "hkaAnimationContainer"           : {"skeletons"},
            "hkaSkeleton"                     : {"name", "parentIndices", "bones", "referencePose"},
            "hkRootLevelContainerNamedVariant": {"name", "className", "variant"},
            "hkaBone"                         : {"name"},

            "hkaSkeletonMapper"                 : {"mapping"},
            "hkaSkeletonMapperData"             : {"skeletonA", "skeletonB", "simpleMappings", "extractedMotionMapping", "keepUnmappedLocal", "mappingType"},
            "hkaSkeletonMapperDataSimpleMapping": {"boneA", "boneB", "aFromBTransform"},
          }

REF_NODES = {"hkRootLevelContainer", "hkaAnimationContainer", "hkaSkeleton", "hkaSkeletonMapper"}


@overload
def create_node(name: Literal['hkRootLevelContainer'], kaos: Tagfile, fields: set[str] | None=None, store_ref=True) -> tuple[int, 'hkRootLevelContainerNode']: ...

@overload
def create_node(name: Literal['hkRootLevelContainerNamedVariant'], kaos: Tagfile, fields: set[str] | None=None, store_ref=True) -> tuple[int, 'hkRootLevelContainerNamedVariantNode']: ...

@overload
def create_node(name: Literal['hkaAnimationContainer'], kaos: Tagfile, fields: set[str] | None=None, store_ref=True) -> tuple[int, 'hkaAnimationContainerNode']: ...

@overload
def create_node(name: Literal['hkaSkeleton'], kaos: Tagfile, fields: set[str] | None=None, store_ref=True) -> tuple[int, 'hkaSkeletonNode']: ...

@overload
def create_node(name: Literal['hkaBone'], kaos: Tagfile, fields: set[str] | None=None, store_ref=True) -> tuple[int, 'hkaBoneNode']: ...

@overload
def create_node(name: Literal['hkaSkeletonMapper'], kaos: Tagfile, fields: set[str] | None=None, store_ref=True) -> tuple[int, 'hkaSkeletonMapperNode']: ...

@overload
def create_node(name: Literal['hkaSkeletonMapperData'], kaos: Tagfile, fields: set[str] | None=None, store_ref=True) -> tuple[int, 'hkaSkeletonMapperDataNode']: ...

@overload
def create_node(name: Literal['hkaSkeletonMapperDataSimpleMapping'], kaos: Tagfile, fields: set[str] | None=None, store_ref=True) -> tuple[int, 'hkaSkeletonMapperDataSimpleMappingNode']: ...

def create_node(name: str, kaos: Tagfile, fields: set[str] | None=None, store_ref=True) -> tuple[int, Node]:
    fields = fields if fields is not None else FIELDS[name]
    node   = Node.from_definition(kaos.context.get_definition(name), fields)
    idx    = len(kaos.nodes)
    kaos.nodes.append(node)

    if name in REF_NODES and store_ref:
        kaos.references.append(idx)

    return idx, node
