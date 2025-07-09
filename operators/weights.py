import bpy

from bpy.props       import StringProperty, EnumProperty, BoolProperty
from bpy.types       import Operator, Context, Object
from ..properties    import get_window_properties, get_outfit_properties, get_devkit_properties
from ..mesh.weights  import remove_vertex_groups, restore_yas_groups
from ..utils.typings import DevkitProps
from ..utils.objects import get_collection_obj, get_object_from_mesh


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
    
        for vert in obj.data.vertices:
            for v_group in vert.groups:
                if v_group.group in vgroups and v_group.weight > 0:
                    vgroups[v_group.group] = True
        
        removed = []
        for idx, used in sorted(vgroups.items(), reverse=True):
            if not used:
                removed.append(obj.vertex_groups[idx].name)
                obj.vertex_groups.remove(obj.vertex_groups[idx])
                

        self.report({'INFO'}, f"Removed {', '.join(removed)}.")
        bpy.ops.object.mode_set(mode=old_mode)
        props.set_yas_ui_vgroups(context)
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
            yas_vgroups  = props.yas_ui_vgroups
            index        = props.yas_vindex
            vertex_group = obj.vertex_groups.get(yas_vgroups[index].name)
        else: 
            vertex_group = obj.vertex_groups.active

        if not obj.parent.data.bones.get(vertex_group.name):
            self.report({'ERROR'}, "Selected group has no parent.")
            return {'CANCELLED'}

        if not obj.parent or obj.parent.type != 'ARMATURE':
            self.report({'ERROR'}, "Mesh is missing a parent skeleton")
            return {'CANCELLED'}
        
        remove_vertex_groups(obj, obj.parent, (vertex_group.name))

        parent_vgroup = obj.parent.data.bones.get(vertex_group.name).parent.name
        self.report({'INFO'}, f"Removed {vertex_group.name}, weights added to {parent_vgroup}.")
        bpy.ops.object.mode_set(mode=old_mode)
        props.set_yas_ui_vgroups(context)
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

        props.set_yas_ui_vgroups(context)
        return {"FINISHED"}  

class YASManager(Operator):
    bl_idname = "ya.yas_manager"
    bl_label = ""

    bl_options = {'UNDO', 'REGISTER'}

    mode: StringProperty(default="ACTIVE", options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    target: StringProperty(options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    store: BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore

    @classmethod
    def description(cls, context, properties):
        if properties.mode == "RESTORE":
            return '''Restore weights to target object.
    *CTRL click to delete the stored weights'''
        
        elif properties.target == "DEVKIT":
            return "Store weights for devkit meshes"
        
        else: 
            return '''Store target weights.
    *CTRL click to delete without storing''' 

    def invoke(self, context, event):
        self.store = not event.ctrl
        dependent  = self._dependent_target([context.active_object], get_devkit_properties())
        delete_dep = self.target != "DEVKIT" and dependent and not self.store

        if (self.target == "ACTIVE" or delete_dep) and dependent:
            cond_text = "restored" if self.mode == "RESTORE" else "stored"
            if delete_dep:
                cond_text = "deleted"

            context.window_manager.invoke_confirm(
                self,
                event=None, 
                title="YAS Manager", 
                message=f"The selected mesh is dependent on other devkit source meshes, the dependencies will also be {cond_text}.",
                icon='INFO'
                )
            return {'RUNNING_MODAL'}
        else:
            return self.execute(context)
    
    def execute(self, context: Context):
        props   = get_outfit_properties()
        devkit  = get_devkit_properties()
        targets = self.get_targets(context, devkit)

        if self.mode == "RESTORE":
            for obj in targets:
                if not obj.yas.v_groups:
                    continue
                if len(obj.data.vertices) != obj.yas.old_count:
                    self.report({'ERROR'}, f"{obj.name}'s vertex count has changed, not possible to restore.")
                    return {'CANCELLED'}

                if self.store:
                    restore_yas_groups(obj)
                else:
                    obj.yas.v_groups.clear()
                
                obj.yas.all_groups = False
                obj.yas.genitalia  = False
                obj.yas.physics    = False
                    
        else:
            prefix = self.get_prefix()
            for obj in targets:
                if devkit:
                    skeleton  = bpy.data.objects.get("Skeleton")
                elif obj.parent.type == 'ARMATURE':
                    skeleton = obj.parent
                else:
                    self.report({'ERROR'}, f"{obj.name} is not parented to a skeleton.")
                    return {'CANCELLED'}
                
                remove_vertex_groups(obj, skeleton, prefix, self.store)
                obj.yas.old_count = len(obj.data.vertices)
                if self.mode == "ALL":
                    obj.yas.all_groups = True
                elif self.mode == "GEN":
                    obj.yas.genitalia  = True
                elif self.mode == "PHYS":
                    obj.yas.physics    = True


        props.set_yas_ui_vgroups(context)
        return {'FINISHED'}
    
    def get_targets(self, context: Context, devkit: DevkitProps) -> list[Object]:
        base_targets = self._get_base_targets(context, devkit)
        
        if self._dependent_target(base_targets, devkit):
            base_targets.extend(self._get_devkit_targets(devkit))
        
        if devkit:
            base_targets.extend(self._add_secondary_meshes(base_targets, devkit))
        
        return base_targets

    def get_prefix(self) -> tuple[str, ...]:
        if self.mode == "ALL":
            prefix = ("iv_", "ya_")
        elif self.mode == "PHYS":
            prefix = (""
                "ya_shiri_phys_l",  "ya_shiri_phys_r",
                "iv_daitai_phys_l", "iv_daitai_phys_r",
                "ya_daitai_phys_l", "ya_daitai_phys_r"
                )
        else:
            prefix = (
                "iv_kuritto",                   
                "iv_inshin_l",               
                "iv_inshin_r",               
                "iv_omanko", 
                "iv_koumon",                      
                "iv_koumon_l",                 
                "iv_koumon_r",

                "iv_kintama_phys_l",              
                "iv_kintama_phys_r",    
                "iv_kougan_l",
                "iv_kougan_r",
            
                "iv_funyachin_phy_a",
                "iv_funyachin_phy_b",        
                "iv_funyachin_phy_c",        
                "iv_funyachin_phy_d",     
                "iv_ochinko_a",                 
                "iv_ochinko_b",              
                "iv_ochinko_c",              
                "iv_ochinko_d",                 
                "iv_ochinko_e",         
                "iv_ochinko_f",
                )
        
        return prefix

    def _get_base_targets(self, context: Context, devkit: DevkitProps) -> list[Object]:
        if devkit:
            devkit_targets = {
                "TORSO": devkit.yam_torso,
                "LEGS": devkit.yam_legs,
                "HANDS": devkit.yam_hands,
                "FEET": devkit.yam_feet,
                "MANNEQUIN": devkit.yam_mannequin,
            }

            if self.target == "DEVKIT" and self.mode == "GEN":
                return [devkit.yam_legs, devkit.yam_mannequin] 
            
            if self.target in devkit_targets:
                return [devkit_targets[self.target]]
        
        return [context.active_object] if context.active_object else []

    def _dependent_target(self, base_targets: list[Object], devkit: DevkitProps) -> bool:
        if not devkit or not base_targets:
            return False
        
        if self.target == "DEVKIT":
            return self.mode != "GEN"
        
        if self.mode == "RESTORE":
            all_groups = any(group.all_groups for group in base_targets[0].yas_groups)
            if not all_groups:
                return False
        
        if self.mode in ("ALL", "RESTORE"):
            dependent_targets = {"TORSO", "LEGS", "MANNEQUIN"}
            
            if self.target in dependent_targets:
                return True
            
            if self.target == "ACTIVE":
                devkit_objects = [devkit.yam_torso, devkit.yam_legs, devkit.yam_mannequin]
                return base_targets[0] in devkit_objects
        
        return False

    def _get_devkit_targets(self, devkit: DevkitProps) -> list[Object]:
        if self.target == "DEVKIT" and self.mode == "ALL":
            devkit_objects = [devkit.yam_torso, devkit.yam_legs,devkit.yam_hands, devkit.yam_feet, devkit.yam_mannequin]
        else:
            devkit_objects = [devkit.yam_torso, devkit.yam_legs, devkit.yam_mannequin]

        data_source_objects = get_collection_obj("Data Sources", type='MESH', sub_collections=True)
        
        devkit_targets = devkit_objects + data_source_objects
        return devkit_targets
    
    def _add_secondary_meshes(self, targets: list[Object], devkit: DevkitProps):
        if devkit.yam_torso in targets:
            targets.append(get_object_from_mesh("Neck"))
            targets.append(get_object_from_mesh("Elbow"))
            targets.append(get_object_from_mesh("Wrist"))
            targets.append(get_object_from_mesh("PiercBelly"))
            targets.extend(get_collection_obj("Nipple Piercings", type='MESH'))

        if devkit.yam_hands in targets:
            targets.extend(get_collection_obj("Nails", type='MESH', sub_collections=True))
            targets.extend(get_collection_obj("Clawsies", type='MESH'))
        
        if devkit.yam_legs in targets:
            targets.extend(get_collection_obj("Pubes", type='MESH'))

        if devkit.yam_feet in targets:
            targets.extend(get_collection_obj("Toenails", type='MESH'))
            targets.extend(get_collection_obj("Toe Clawsies", type='MESH'))

    
CLASSES = [
    RemoveEmptyVGroups,
    RemoveSelectedVGroups,
    AddYASGroups,
    YASManager
]
