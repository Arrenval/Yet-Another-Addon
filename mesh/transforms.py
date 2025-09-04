import numpy as np

from numpy     import single
from bpy.types import Object
from mathutils import Matrix


def apply_transforms(obj: Object):
        world_transform = obj.matrix_world.copy()
        if world_transform == Matrix.Identity(4):
            return
        
        if not obj.data.shape_keys:
            obj.data.transform(world_transform)
        else:
            vert_count       = len(obj.data.vertices)
            transform_matrix = np.array(world_transform).astype(single)
            for key in obj.data.shape_keys.key_blocks:
                pos = np.zeros(vert_count * 3, dtype=single)
                key.data.foreach_get("co", pos)
                pos = np.c_[pos.reshape(-1, 3), np.ones(vert_count)]
                pos = (transform_matrix @ pos.T).T[:, :3]
                key.data.foreach_set("co", pos.flatten())

        obj.matrix_world.identity()
