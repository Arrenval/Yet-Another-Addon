import bpy

from bpy.props            import StringProperty, EnumProperty, BoolProperty
from bpy.types            import Operator, Context
from ..properties         import get_window_properties, get_outfit_properties
from ..utils.mesh_handler import remove_vertex_groups


class RemoveEmptyVGroups(Operator):                         
    bl_idname = "ya.remove_empty_vgroups"
    bl_label = ""
    bl_description = "Removes Vertex Groups with no weights. Ignores locked groups"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return obj is not None and obj.type == 'MESH' and obj.vertex_groups

    def execute(self, context:Context):
        props    = get_outfit_properties()
        old_mode = context.mode
        match old_mode:
            case "PAINT_WEIGHT":
                old_mode = "WEIGHT_PAINT"
            case "EDIT_MESH":
                old_mode = "EDIT"
   
        bpy.ops.object.mode_set(mode='OBJECT')
        obj = context.active_object
        
        vgroups = {vg.index: False for vg in obj.vertex_groups if not vg.lock_weight}
    
        for v in obj.data.vertices:
            for g in v.groups:
                if g.group in vgroups and g.weight > 0:
                    vgroups[g.group] = True
        
        removed = []
        for i, used in sorted(vgroups.items(), reverse=True):
            if not used:
                removed.append(obj.vertex_groups[i].name)
                obj.vertex_groups.remove(obj.vertex_groups[i])
                

        self.report({'INFO'}, f"Removed {', '.join(removed)}.")
        bpy.ops.object.mode_set(mode=old_mode)
        props.set_yas_vgroups(context)
        return {"FINISHED"}
    
class RemoveSelectedVGroups(Operator):
    bl_idname = "ya.remove_select_vgroups"
    bl_label = ""
    bl_description = "Removes selected group and adds the weights to the parent group"
    bl_options = {"UNDO"}

    preset: StringProperty() # type: ignore

    @classmethod
    def poll(cls, context:Context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.vertex_groups

    def execute(self, context:Context):
        props    = get_outfit_properties()
        window   = get_window_properties()
        old_mode = context.mode

        if self.preset == "PANEL" and props.yas_empty and window.filter_vgroups:
            self.report({"ERROR"}, "No YAS group selected.")
            return {"CANCELLED"}

        if old_mode == 'PAINT_WEIGHT':
            old_mode = 'WEIGHT_PAINT'

        bpy.ops.object.mode_set(mode='OBJECT')
        obj = context.active_object

        if self.preset != "MENU" and window.filter_vgroups:
            yas_vgroups  = props.yas_vgroups
            index        = props.yas_vindex
            vertex_group = obj.vertex_groups.get(yas_vgroups[index].name)
        else: 
            vertex_group = obj.vertex_groups.active

        if not obj.parent.data.bones.get(vertex_group.name):
            self.report({'ERROR'}, "Selected group has no parent.")
            return {'CANCELLED'}

        if not obj.parent and obj.parent.type == "ARMATURE":
            self.report({'ERROR'}, "Mesh is missing a parent skeleton")
            return {'CANCELLED'}
        
        remove_vertex_groups(obj, (vertex_group.name))

        parent_vgroup = obj.parent.data.bones.get(vertex_group.name).parent.name
        self.report({'INFO'}, f"Removed {vertex_group.name}, weights added to {parent_vgroup}.")
        bpy.ops.object.mode_set(mode=old_mode)
        props.set_yas_vgroups(context)
        return {"FINISHED"}

class AddYASGroups(Operator):
    bl_idname = "ya.add_yas_vgroups"
    bl_label = ""
    bl_description = "Add YAS related Vertex Groups"
    bl_options = {"UNDO"}


    user_input: EnumProperty(
        name="",
        items=[("TORSO", "Torso", ""),
               ("FINGERS", "Hands", ""),
               ("LEGS", "Legs", ""),
               ("TOES", "Feet", "")]) # type: ignore
    
    torso: BoolProperty(default=False) # type: ignore
    fingers: BoolProperty(default=False) # type: ignore
    legs: BoolProperty(default=False) # type: ignore
    toes: BoolProperty(default=False) # type: ignore

    anus: BoolProperty(default=False) # type: ignore
    penis: BoolProperty(default=False) # type: ignore
    vagina: BoolProperty(default=False) # type: ignore

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"
    
    def invoke(self, context, event):
        context.window_manager.invoke_props_dialog(self, confirm_text="Confirm", title="", width=2)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Select categories:")

        row = layout.row(align=True)
        row.prop(self, "torso", icon="CHECKMARK" if self.torso else "X", text="Torso")
        row.prop(self, "fingers", icon="CHECKMARK" if self.fingers else "X", text="Fingers")

        row = layout.row(align=True)
        row.prop(self, "legs", icon="CHECKMARK" if self.legs else "X", text="Legs")
        row.prop(self, "toes", icon="CHECKMARK" if self.toes else "X", text="Toes")

        layout.separator(type="LINE")

        row = layout.row(align=True)
        row.prop(self, "anus", icon="CHECKMARK" if self.anus else "X", text="Anus")
        row.prop(self, "penis", icon="CHECKMARK" if self.penis else "X", text="Penis")

        row = layout.row(align=True)
        row.prop(self, "vagina", icon="CHECKMARK" if self.vagina else "X", text="Vagina")
        
    def execute(self, context):
        props = get_outfit_properties()

        torso_groups = [
            'iv_nitoukin_l',
            'iv_nitoukin_r',

            'ya_fukubu_phys',             
            'iv_fukubu_phys',            
            'iv_fukubu_phys_l',       
            'iv_fukubu_phys_r',
        ]
        
        fingers_groups = [
            'iv_hito_c_l',
            'iv_ko_c_l',  
            'iv_kusu_c_l',
            'iv_naka_c_l',

            'iv_hito_c_r',
            'iv_ko_c_r',  
            'iv_kusu_c_r',
            'iv_naka_c_r'
            ]
        
        leg_groups = [
            'iv_shiri_l',
            'iv_shiri_r',
            'ya_shiri_phys_l',        
            'ya_shiri_phys_r',

            'ya_fukubu_phys',            
            'iv_fukubu_phys',            
            'iv_fukubu_phys_l',       
            'iv_fukubu_phys_r',

            'iv_daitai_phys_l',    
            'ya_daitai_phys_l',   
            'iv_daitai_phys_r',    
            'ya_daitai_phys_r'   
        ]

        toe_groups = [
            'iv_asi_oya_a_l',      
            'iv_asi_hito_a_l',     
            'iv_asi_naka_a_l',     
            'iv_asi_kusu_a_l',     
            'iv_asi_ko_a_l',       
            'iv_asi_oya_b_l', 
            'iv_asi_hito_b_l',
            'iv_asi_naka_b_l',
            'iv_asi_kusu_b_l',
            'iv_asi_ko_b_l',

            'iv_asi_oya_a_r',      
            'iv_asi_hito_a_r',     
            'iv_asi_naka_a_r',     
            'iv_asi_kusu_a_r',     
            'iv_asi_ko_a_r',       
            'iv_asi_oya_b_r', 
            'iv_asi_hito_b_r',
            'iv_asi_naka_b_r',
            'iv_asi_kusu_b_r',
            'iv_asi_ko_b_r',  
        ]

        penis_groups = [
            'iv_kintama_phys_l',              
            'iv_kintama_phys_r',    
            'iv_kougan_l',
            'iv_kougan_r',

            'iv_funyachin_phy_a',           
            'iv_funyachin_phy_b',        
            'iv_funyachin_phy_c',        
            'iv_funyachin_phy_d',     
            'iv_ochinko_a',                 
            'iv_ochinko_b',              
            'iv_ochinko_c',              
            'iv_ochinko_d',                 
            'iv_ochinko_e',         
            'iv_ochinko_f',  
        ]

        vagina_groups = [
            'iv_kuritto',                   
            'iv_inshin_l',               
            'iv_inshin_r',               
            'iv_omanko',           
        ]

        anus_groups = [
            'iv_koumon',                      
            'iv_koumon_l',                 
            'iv_koumon_r',         
        ]
        
        obj                   = context.active_object
        to_transfer: set[str] = set()
        if self.torso:
            to_transfer.update(torso_groups)
        if self.fingers:
            to_transfer.update(fingers_groups)
        if self.legs:
            to_transfer.update(leg_groups)
        if self.anus:
            to_transfer.update(anus_groups)
        if self.penis:
            to_transfer.update(penis_groups)
        if self.vagina:
            to_transfer.update(vagina_groups)
        if self.toes:
            to_transfer.update(toe_groups)

        for group in to_transfer:
            if obj.vertex_groups.get(group):
                continue
            bpy.ops.object.vertex_group_add()
            obj.vertex_groups.active.name = group

        props.set_yas_vgroups(context)
        return {"FINISHED"}  

class RemoveGenGroups(Operator):
    bl_idname = "ya.remove_gen"
    bl_label = ""
    bl_description = "Removes most genitalia related groups and adds the weights to the parent group"
    bl_options = {"UNDO"}

    preset: StringProperty() # type: ignore

    @classmethod
    def poll(cls, context:Context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.vertex_groups

    def execute(self, context: Context):
        props = get_outfit_properties()
        obj   = context.active_object
        genitalia = [
            'iv_kuritto',                   
            'iv_inshin_l',               
            'iv_inshin_r',               
            'iv_omanko', 
            'iv_koumon',                      
            'iv_koumon_l',                 
            'iv_koumon_r',

            'iv_kintama_phys_l',              
            'iv_kintama_phys_r',    
            'iv_kougan_l',
            'iv_kougan_r',
           
            'iv_funyachin_phy_b',        
            'iv_funyachin_phy_c',        
            'iv_funyachin_phy_d',     
            'iv_ochinko_a',                 
            'iv_ochinko_b',              
            'iv_ochinko_c',              
            'iv_ochinko_d',                 
            'iv_ochinko_e',         
            'iv_ochinko_f',
            ]
        
        remove_vertex_groups(obj, tuple(genitalia))
        props.set_yas_vgroups(context)
        return {"FINISHED"}


CLASSES = [
    RemoveEmptyVGroups,
    RemoveSelectedVGroups,
    AddYASGroups,
    RemoveGenGroups
]
