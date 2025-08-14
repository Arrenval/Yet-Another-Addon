import re
import bpy
import bmesh
import numpy as np
import random

from bpy.types        import Object, Mesh, Material
from numpy            import short, ushort, half, single, byte, ubyte, uint8
from numpy.typing     import NDArray
from collections      import defaultdict

from ..com.scene      import get_mesh_ids     
from ....mesh.weights import add_to_vgroup
from ...formats.model import XIVModel, Mesh as XIVMesh, Submesh, VertexDeclaration, VertexElement, VertexUsage, VertexType, get_vert_struct
from ..com.exceptions import XIVMeshError, XIVMeshIDError

from ....testing.time_func import get_time


def remove_loose_verts(obj: Object) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    
    loose_verts = [vert for vert in bm.verts if len(vert.link_faces) == 0]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context='VERTS')
    
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.to_mesh(obj.data)

    bm.free()
    obj.data.update()

@get_time
def split_seams(obj: Object):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.reveal(select=False)
    bpy.ops.mesh.select_all(action='SELECT')
    
    for uv_layer in obj.data.uv_layers:
        uv_layer.active = True
        bpy.ops.uv.seams_from_islands()

    bpy.ops.mesh.select_all(action='DESELECT')

    bm = bmesh.from_edit_mesh(obj.data)

    for edge in bm.edges:
        if edge.seam or not edge.smooth:
            edge.select = True
    
    bmesh.update_edit_mesh(obj.data, destructive=False, loop_triangles=False)
    bpy.ops.mesh.edge_split()
    bpy.ops.object.mode_set(mode='OBJECT')
    
class ModelExport:
    
    @classmethod
    def export_scene(cls, export_obj: list[Object]) -> None:
        exporter = cls()
        exporter.handle_blend_obj(export_obj)

    @get_time
    def handle_blend_obj(self, export_obj: list[Object]) -> None:
        self.model = XIVModel()
        sorted_meshes = self.sort_submeshes(export_obj)

        vert_buffer_size = 0
        for mesh_idx, submeshes in enumerate(sorted_meshes):
            mesh_vert_count = sum(len(submesh.data.vertices) for submesh in submeshes)
            if mesh_vert_count > np.iinfo(ushort).max:
                raise XIVMeshError(f"Mesh #{mesh_idx} exceeds the {np.iinfo(ushort).max} vertices limit.")
            
            mesh = XIVMesh()
            mesh.submesh_index = len(self.model.submeshes)
            mesh.submesh_count = len(submeshes)
            mesh.vertex_count  = mesh_vert_count
            mesh.vertex_stream_count = 2
            
            vert_decl = self.create_vert_declaration(submeshes)
            self.model.vertex_declarations.append(vert_decl)
            for submesh_idx, blend_submesh in enumerate(submeshes):
                if submesh_idx == 0:
                    mesh.material_idx = self.get_material_idx(blend_submesh)

    def sort_submeshes(self, export_obj: list[Object]) -> list[list[Object]]:
        mesh_dict: dict[int, dict[int, Object]] = defaultdict(dict)
        for obj in export_obj:
            if len(obj.data.vertices) == 0:
                continue

            group, part = get_mesh_ids(obj)
            
            if part in mesh_dict[group]:
                raise XIVMeshIDError(f'{obj.name}: Submesh already exists as "{mesh_dict[group][part].name}".')
            
            remove_loose_verts(obj)
            split_seams(obj)
            mesh_dict[group][part] = obj

        sorted_meshes = [submesh_dict for mesh_idx, submesh_dict in sorted(mesh_dict.items(), key=lambda x: x[0])]

        final_sort: list[list[Object]] = []
        for submesh_dict in sorted_meshes:
            sorted_submeshes = [obj for submesh_idx, obj in sorted(submesh_dict.items(), key=lambda x: x[0])]
            final_sort.append(sorted_submeshes)
        
        return final_sort

    def create_vert_declaration(self, submeshes: list[Object]) -> VertexDeclaration:

        def create_element(type: VertexType, usage: VertexUsage, stream: int) -> None:
            nonlocal declaration

            element = VertexElement()
            element.stream = stream
            element.offset = declaration.stream_size(stream)
            element.type   = type
            element.usage  = usage

            declaration.vertex_elements.append(element)

        declaration = VertexDeclaration()

        create_element(VertexType.SINGLE3, VertexUsage.POSITION, 0)
        create_element(VertexType.USHORT4, VertexUsage.BLEND_WEIGHTS, 0)
        create_element(VertexType.USHORT4, VertexUsage.BLEND_INDICES, 0)

        create_element(VertexType.SINGLE3, VertexUsage.NORMAL, 1)
        create_element(VertexType.NBYTE4, VertexUsage.TANGENT, 1)

        col_layers = 0
        uv_layers  = 0
        for obj in submeshes:
            col_layers = max(col_layers, len(obj.data.color_attributes))
            uv_layers  = max(uv_layers, len(obj.data.uv_layers))

        for i in range(col_layers):
            if i > 1:
                break
            create_element(VertexType.NBYTE4, VertexUsage.COLOUR, 1)

        for i in range(uv_layers):
            if i == 0:
                create_element(VertexType.SINGLE4, VertexUsage.UV, 1)
            elif i == 2:
                create_element(VertexType.SINGLE2, VertexUsage.UV, 1)
            elif i > 2:
                break

        return declaration

    def get_material_idx(self, submesh: Object) -> int:

        def clean_material_name(name: str):
            if not name.startswith("/"):
                name = "/" + name
            if not name.endswith(".mtrl"):
                name = name + ".mtrl"
            return name.strip()
        
        material_name = clean_material_name(submesh.material_slots[0].name)

        if material_name in self.model.materials:
            material_idx = self.model.materials.index(material_name)
        else:
            material_idx = len(self.model.materials)
            self.model.materials.append(material_name)
        
        return material_idx

    def submesh_streams(self, obj: Object, vert_decl: VertexDeclaration):...