import bpy
import numpy as np

from numpy                    import single
from bpy.props                import IntProperty
from bpy.types                import Object, Operator, NodesModifier, NodeTree, Nodes, Node, NodeLinks, ShaderNodeMath, ShaderNodeCombineColor

from ..xiv.io.model.com.space import lin_to_srgb


def default_xiv_flow(obj: Object) -> None:
    count = len(obj.data.loops)
    
    if "vc2" in obj.data.color_attributes:
        layer = obj.data.color_attributes["vc2"]
    
        if layer.data_type =='BYTE_COLOR':
            # This is a correction to restore linear colour data.
            rgba = np.ones(count * 4, dtype=single)
            layer.data.foreach_get("color", rgba)
            obj.data.color_attributes.remove(layer)
            
            layer = obj.data.color_attributes.new("xiv_flow", domain='CORNER', type='FLOAT_COLOR')
            layer.data.foreach_set("color", lin_to_srgb(rgba.reshape(-1, 4)).flatten())
        else:
            layer.name = "xiv_flow" 

    else:
        rg    = np.full((count, 2), 0.5, dtype=single)
        ba    = np.ones((count, 2), dtype=single)
        rgba  = np.c_[rg, ba]
        layer = obj.data.color_attributes.new("xiv_flow", domain='CORNER', type='FLOAT_COLOR')
        layer.data.foreach_set("color", rgba.flatten())

def get_colour(angle: int):
    precision = np.pi / 64  
    quantised = round(np.radians(angle) / precision) * precision
    direction = np.array([np.cos(quantised), np.sin(quantised)])

    rg = ((direction + 1.0) / 2.0) 
    return (rg[0], rg[1], 1.0, 1.0)

class FlowNode(Operator):
    bl_idname = "ya.modifier_flow"
    bl_label = "XIV Flow"
    bl_description = "Creates a geo-node modifier to assign hair flow values to a mesh"
    bl_options = {"UNDO", "REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.mode != "EDIT_MESH"
    
    def execute(self, context):
        obj = bpy.context.active_object

        modifier: NodesModifier = obj.modifiers.new(name="XIV Hair Flow", type='NODES')
        node_group              = bpy.data.node_groups.new(name="Flow Values", type='GeometryNodeTree')

        modifier.node_group = node_group
        node_group.nodes.clear()
        
        nodes = node_group.nodes
        links = node_group.links
        
        group_input, group_output = self._create_io_groups(node_group, nodes)
        radians, colour           = self._create_math_nodes(nodes, links)
        
        store_attr = nodes.new(type='GeometryNodeStoreNamedAttribute')
        store_attr.data_type = 'FLOAT_COLOR'
        store_attr.domain    = 'CORNER'
        store_attr.inputs[2].default_value = "xiv_flow"
        store_attr.location = (400, 76)
        
        links.new(group_input.outputs['Geometry'], store_attr.inputs['Geometry'])
        links.new(group_input.outputs['Vertex Group'], store_attr.inputs['Selection'])
        links.new(store_attr.outputs['Geometry'], group_output.inputs['Geometry'])
        links.new(group_input.outputs['Degrees'], radians.inputs[0])
        links.new(colour.outputs['Color'], store_attr.inputs['Value'])

        node_group.update_tag()

        if "xiv_flow" not in obj.data.color_attributes:
            default_xiv_flow(obj)
            
        obj.data.color_attributes.active_color_name = "xiv_flow"
        bpy.ops.object.geometry_nodes_input_attribute_toggle(input_name="Socket_2", modifier_name=modifier.name)

        return {'FINISHED'}
    
    def _create_io_groups(self, node_group: NodeTree, nodes: Nodes) -> tuple[Node, Node]:
        group_input  = nodes.new(type='NodeGroupInput')
        group_output = nodes.new(type='NodeGroupOutput')
        node_group.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
        node_group.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')

        group_input.location  = (-800, 0)
        group_output.location = (600, 0)

        vgroup  = node_group.interface.new_socket(
                                    "Vertex Group", 
                                    in_out='INPUT',
                                    description="Enter a vertex group to control where to apply colour.", 
                                    socket_type='NodeSocketInt')

        degrees = node_group.interface.new_socket(
                                    'Degrees', 
                                    in_out='INPUT', 
                                    description="Orientation of the UVs",
                                    socket_type='NodeSocketInt')
    
        degrees.min_value       = 0
        degrees.max_value       = 360
        degrees.force_non_field = True

        return group_input, group_output
    
    def _create_math_nodes(self, nodes: Nodes, links: NodeLinks) -> tuple[ShaderNodeMath, ShaderNodeCombineColor]:
        to_radians   : ShaderNodeMath         = nodes.new(type='ShaderNodeMath')
        combine_color: ShaderNodeCombineColor = nodes.new(type='FunctionNodeCombineColor')

        red          : ShaderNodeMath = nodes.new(type='ShaderNodeMath')
        add_red      : ShaderNodeMath = nodes.new(type='ShaderNodeMath')
        divide_red   : ShaderNodeMath = nodes.new(type='ShaderNodeMath')

        green        : ShaderNodeMath = nodes.new(type='ShaderNodeMath')
        add_green    : ShaderNodeMath = nodes.new(type='ShaderNodeMath')
        divide_green : ShaderNodeMath = nodes.new(type='ShaderNodeMath')
        
        to_radians.operation = 'RADIANS'
        
        red.operation        = 'COSINE'
        add_red.operation    = 'ADD'
        divide_red.operation = 'DIVIDE'
        
        add_red.inputs[1].default_value    = 1.0
        divide_red.inputs[1].default_value = 2.0

        green.operation        = 'SINE'
        add_green.operation    = 'ADD'
        divide_green.operation = 'DIVIDE'
        
        add_green.inputs[1].default_value    = 1.0
        divide_green.inputs[1].default_value = 2.0

        combine_color.mode = 'RGB'
        combine_color.inputs['Blue'].default_value = 1.0  
        combine_color.inputs['Alpha'].default_value = 1.0

        to_radians.location    = (-600, -100)  
        combine_color.location = (200, -100)

        red.location        = (-400, -100)
        add_red.location    = (-200, -100)
        divide_red.location = (0, -100)

        green.location        = (-400, -275)
        add_green.location    = (-200, -275)
        divide_green.location = (0, -275)

        links.new(to_radians.outputs[0], red.inputs[0])
        links.new(to_radians.outputs[0], green.inputs[0])
        
        links.new(red.outputs[0], add_red.inputs[0])
        links.new(add_red.outputs[0], divide_red.inputs[0])
        links.new(divide_red.outputs[0], combine_color.inputs['Red'])
        
        links.new(green.outputs[0], add_green.inputs[0])
        links.new(add_green.outputs[0], divide_green.inputs[0])
        links.new(divide_green.outputs[0], combine_color.inputs['Green'])

        return to_radians, combine_color

class SetFlow(Operator):
    bl_idname = "ya.set_flow"
    bl_label = "XIV Flow"
    bl_description = "Sets flow based on selected angle"
    bl_options = {"UNDO", "REGISTER"}

    angle: IntProperty(default=0, options={"HIDDEN", "SKIP_SAVE"}) # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"
    
    def execute(self, context):
        obj = bpy.context.active_object
        bpy.ops.object.mode_set(mode='OBJECT')
        if "xiv_flow" not in obj.data.color_attributes:
            default_xiv_flow(obj)
        
        col_layer   = obj.data.color_attributes["xiv_flow"].data
        flow_colour = get_colour(self.angle)

        verts = {vert.index for vert in obj.data.vertices if vert.select}
        for idx, loop in enumerate(obj.data.loops):
            if loop.vertex_index in verts:
                col_layer[idx].color = flow_colour

        obj.data.color_attributes.active_color_name = "xiv_flow"
        obj.data.update()

        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


CLASSES = [
    FlowNode,
    SetFlow
]