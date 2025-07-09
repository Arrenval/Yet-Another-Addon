import bmesh
import numpy as np

from numpy           import float32, uint32
from bpy.types       import Object, VertexGroup
from numpy.typing    import NDArray
from collections.abc import Iterable

from ..properties    import YASGroup


def remove_vertex_groups(obj: Object, skeleton: Object, prefix: tuple[str, ...], store_yas=False) -> None:
        """Can remove any vertex group and add weights to parent group."""
        group_to_parent = _get_group_parent(obj, skeleton, prefix)
        source_groups   = [value for value in group_to_parent.keys()]

        if not source_groups:
            return

        weight_matrix = _create_weight_matrix(obj, skeleton, group_to_parent, source_groups)

        # Adds weights to parent
        updated_groups = {value for value in group_to_parent.values()}
        for v_group in obj.vertex_groups:
            if v_group.index not in updated_groups:
                continue

            indices = np.flatnonzero(weight_matrix[:, v_group.index])
            weights = weight_matrix[:, v_group.index][indices]
            if len(indices) == 0:
                continue

            grouped_indices, unique_weights = group_weights(indices, weights)
            
            for array_idx, vert_indices in enumerate(grouped_indices):
                vert_indices = vert_indices.tolist()
                v_group.add(vert_indices, unique_weights[array_idx], type='ADD')
        
        if store_yas:
            _store_yas_groups(obj, skeleton, group_to_parent, weight_matrix)

        for v_group in obj.vertex_groups:
            if v_group.name.startswith(prefix):
                obj.vertex_groups.remove(v_group)

def _store_yas_groups(obj: Object, skeleton: Object, group_to_parent: dict[int, int], weight_matrix: NDArray[float32]) -> None:
    yas_groups: Iterable[YASGroup] = obj.yas.v_groups
    
    existing_groups = [group.name for group in yas_groups]
    for group in group_to_parent:
        group_name = obj.vertex_groups[group].name
        if group_name in existing_groups:
            continue

        indices = np.flatnonzero(weight_matrix[:, group])
        weights = weight_matrix[:, group][indices]
        if len(indices) == 0:
            continue

        new_group: YASGroup  = yas_groups.add()
        new_group.name       = group_name
        new_group.parent     = skeleton.data.bones.get(group_name).parent.name

        for _ in range(len(indices)):
            new_group.vertices.add()

        new_group.vertices.foreach_set("idx", indices)
        new_group.vertices.foreach_set("value", weights)

def restore_yas_groups(obj: Object) -> None:
    yas_groups: Iterable[YASGroup] = obj.yas.v_groups
    yas_to_parent: dict[str, str] = {}
    stored_weights: dict[str, tuple[list[NDArray], NDArray]] = {}

    for v_group in yas_groups:
        verts =  len(v_group.vertices)
        yas_to_parent[v_group.name] = v_group.parent

        indices = np.zeros(verts, dtype=uint32)
        weights = np.zeros(verts, dtype=float32)

        v_group.vertices.foreach_get("idx", indices)
        v_group.vertices.foreach_get("value", weights)

        grouped_indices, unique_weights = group_weights(indices, weights)
        
        stored_weights[v_group.name] = (grouped_indices, unique_weights)

    for yas_name, parent_name in yas_to_parent.items():
        parent = obj.vertex_groups.get(parent_name)
        if not parent: 
            continue

        if obj.vertex_groups.get(yas_name):
            yas_group = obj.vertex_groups.get(yas_name)
        else: 
            yas_group = obj.vertex_groups.new(name=yas_name)

        weights = stored_weights[yas_name]
        for array_idx, vert_indices in enumerate(weights[0]):
            vert_indices = vert_indices.tolist()
            parent.add(vert_indices, weights[1][array_idx], type='SUBTRACT')
            yas_group.add(vert_indices, weights[1][array_idx], type='REPLACE')
    
    yas_groups.clear()

def group_weights(indices: NDArray[uint32], weights: NDArray[float32]) -> tuple[list[NDArray[uint32]], NDArray[float32]]:
    '''Groups vert indices based on unique weight values. 
    This limits the calls to the Blender API vertex_group.add() function.'''
    unique_weights, inverse_indices = np.unique(weights, return_inverse=True)

    sort_order     = np.argsort(inverse_indices)
    sorted_groups  = inverse_indices[sort_order]
    sorted_indices = indices[sort_order]

    split_points    = np.where(np.diff(sorted_groups))[0] + 1
    grouped_indices = np.split(sorted_indices, split_points)

    return grouped_indices, unique_weights

def _get_group_parent(obj: Object, skeleton: Object, prefix: set[str]) -> dict[int, int | str]:
    group_to_parent = {}

    for v_group in obj.vertex_groups:
        if not v_group.name.startswith(prefix):
            continue
        
        parent = skeleton.data.bones.get(v_group.name).parent.name
        parent_group = obj.vertex_groups.get(parent)

        if parent_group:
            group_to_parent[v_group.index] = parent_group.index
        else:
            group_to_parent[v_group.index] = parent
    
    return group_to_parent

def _create_weight_matrix(obj: Object, skeleton: Object, group_to_parent: dict[int, int | str], source_groups: set[int]) -> NDArray[float32]:
    verts          = len(obj.data.vertices)
    missing_groups = {value for value in group_to_parent.values() if isinstance(value, str)}
    max_groups     = len(obj.vertex_groups) + len(missing_groups)
    weight_matrix  = np.zeros((verts, max_groups), dtype=float32)
    
    if len(source_groups) == 1:
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        group_idx = source_groups[0]
        deform_layer = bm.verts.layers.deform.active
        for vert_idx, vert in enumerate(bm.verts):
            weight_matrix[vert_idx, group_idx] = vert[deform_layer].get(group_idx, 0)

        bm.free()
    else:
        for vertex_idx, vertex in enumerate(obj.data.vertices):
            for group in vertex.groups:
                if group.group in source_groups:
                    weight_matrix[vertex_idx, group.group] = group.weight

    _create_missing_parents(obj, skeleton, group_to_parent)

    for group_idx, parent in group_to_parent.items():
        weight_matrix[:, parent] += weight_matrix[:, group_idx]
    
    return weight_matrix

def _create_missing_parents(obj: Object, skeleton: Object, group_to_parent: dict[int, int | str]) -> None:
    parent_to_group = {}
    for group, parent in group_to_parent.items():
        parent_to_group[parent] = parent_to_group.get(parent, []) + [group]

    added_parents = set()
    for group_idx, parent in group_to_parent.items():
        if not isinstance(parent, str):
            continue
        if parent in added_parents:
            continue

        v_group     = obj.vertex_groups[group_idx].name
        parent_name = skeleton.data.bones.get(v_group).parent.name
        new_group   = obj.vertex_groups.new(name=parent)

        added_parents.add(parent_name)

        parent = new_group.index

        for group in parent_to_group[parent_name]:
            group_to_parent[group] = parent


def combine_v_groups(obj: Object, v_groups: list[int]) -> VertexGroup:
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    deform_layer = bm.verts.layers.deform.active

    vertex_weights = np.zeros((len(bm.verts), len(v_groups)), dtype=np.float32)
    for idx, vert in enumerate(bm.verts):
        for col_idx, group_idx in enumerate(v_groups):
            vertex_weights[idx, col_idx] = vert[deform_layer].get(group_idx, 0)
    
    bm.free()

    indices = np.where(np.any(vertex_weights > 0, axis=1))[0]
    indices = indices.tolist()

    combined_group = obj.vertex_groups.new()
    combined_group.add(indices, 1.0, type='REPLACE')

    return combined_group