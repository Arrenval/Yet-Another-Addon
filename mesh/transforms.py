import bpy
import numpy as np

from numpy     import single
from bpy.types import Object, MeshVertices
from mathutils import Matrix


def apply_transforms(obj: Object, clear_parent: bool=False):
        
        def transform_verts(data: MeshVertices, vert_count: int) -> None:
            pos = np.zeros(vert_count * 3, dtype=single)
            data.foreach_get("co", pos)
            pos = np.c_[pos.reshape(-1, 3), np.ones(vert_count)]
            pos = (transform_matrix @ pos.T).T[:, :3]
            data.foreach_set("co", pos.flatten())

        world_transform = obj.matrix_world.copy()
        if obj.data is None:
            return
        if world_transform == Matrix.Identity(4):
            return

        if clear_parent:
            obj.parent = None
            
        if obj.type != 'MESH' or not obj.data.shape_keys:
            obj.data.transform(world_transform)
        else:
            vert_count       = len(obj.data.vertices)
            transform_matrix = np.array(world_transform).astype(single)

            transform_verts(obj.data.vertices, vert_count)
            for key in obj.data.shape_keys.key_blocks:
                transform_verts(key.data, vert_count)

        if obj.type == 'MESH':
            obj.data.update()
        else:
            obj.update_tag(refresh={"DATA"})
            bpy.context.view_layer.update()
        obj.matrix_basis.identity()
