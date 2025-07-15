import numpy as np

from numpy           import float32
from numpy.typing    import NDArray
from bpy.types       import Object, Depsgraph

from ..utils.objects import evaluate_obj


def get_shape_mix(source_obj: Object, extra_key: str="") -> NDArray[float32]:
    """
    Get current mix of shape keys from a mesh. 
    The extra key is optional and will blend that key in at its full value.
    """
    key_blocks = source_obj.data.shape_keys.key_blocks
    vert_count = len(source_obj.data.vertices)
    co_bases   = {}

    basis_co = np.zeros(vert_count * 3, dtype=np.float32)
    key_blocks[0].data.foreach_get("co", basis_co)
    co_bases[key_blocks[0].name] = basis_co

    # We need a copy of the main basis to mix our keys with
    mix_coords = basis_co.copy()

    # Account for keys with a different relative shape
    for key in key_blocks[1:]:
        if key.relative_key.name in co_bases:
            continue
        relative_co = np.zeros(vert_count * 3, dtype=np.float32)
        key.relative_key.data.foreach_get("co", relative_co)
        co_bases[key.relative_key.name] = relative_co

    for key in key_blocks[1:]:
        if key.name == extra_key:
            keep  = True
            blend = 1
        else:
            keep  = False
            blend = key.value
            
        if keep or (key.value != 0 and not key.mute):
            relative_key = key.relative_key.name
            key_coords   = np.zeros(vert_count * 3, dtype=np.float32)
            key.data.foreach_get("co", key_coords)

            # Use relative key coordinates to get offset
            offset = key_coords - co_bases[relative_key]
            mix_coords += offset * blend
    
    return mix_coords

def create_co_cache(co_cache: dict[str, None], shapes: dict[str, Object], target: Object, base_key: str, vert_count: int, depsgraph: Depsgraph) -> None:
    '''Takes a dict of shape key names of relative keys on a mesh and creates a cache of their coordinates per key.'''
    for key_name in co_cache:
        shape = shapes[key_name]
        evaluate_obj(shape, depsgraph)

        shape_co = np.zeros(vert_count * 3, dtype=np.float32)
        shape.data.vertices.foreach_get("co", shape_co)

        co_cache[key_name] = shape_co

        if key_name == base_key:
            target.data.shape_keys.key_blocks[0].data.foreach_set("co", shape_co)
        else:
            new_shape = target.data.shape_keys.key_blocks.get(key_name)
            new_shape.data.foreach_set("co", shape_co)

        del shapes[key_name]

def create_shape_keys(co_cache: dict[str, NDArray[float32]], shapes: dict[str, Object], target: Object, base_key:str, vert_count: int, depsgraph: Depsgraph) -> None:
    '''Uses a co_cache to recreate shape keys on target mesh.'''
    for key_name, shape in shapes.items():
        evaluate_obj(shape, depsgraph)
        shape_co = np.zeros(vert_count * 3, dtype=np.float32)
        shape.data.vertices.foreach_get("co", shape_co)

        rel_key = target.data.shape_keys.key_blocks.get(key_name).relative_key
        new_shape = target.data.shape_keys.key_blocks.get(key_name)
        if rel_key.name not in co_cache:
            continue
 
        offset = shape_co - co_cache[base_key]
        mix_coords = co_cache[rel_key.name] + offset
        new_shape.data.foreach_set("co", mix_coords)
    target.data.update()
