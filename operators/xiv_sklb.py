from bpy.types          import Operator, Object, Context
from bpy.props          import EnumProperty, StringProperty, BoolProperty, IntProperty

from ..props            import Armature, get_skeleton_props, get_window_props
from ..io.sklb          import synchronise_bone_list, synchronise_bone_indices, calculate_mapping, combine_sklb, sort_bone_list
from ..utils.typings    import BlendEnum
from ..ui.popup.sklb    import draw_sklb
from ..utils.serialiser import RNAPropertyIO


class SklbCombine(Operator):
    bl_idname      = "ya.sklb_combine"
    bl_label       = "Skeleton Combiner"
    bl_options     = {"UNDO"}
    bl_description = "Add bones from a source skeleton to your target base"

    def invoke(self, context, event):
        armatures = self._get_armatures(context)
        if not armatures:
            self.report({'ERROR'}, "Missing a base or source.")
            return {'CANCELLED'}

        obj_vis: dict[Object, bool] = {}
        for arm_tuple in armatures:
            for obj in arm_tuple:
                obj_vis[obj] = obj.hide_get()
                obj.hide_set(False)

        for target, source in armatures:
            combine_sklb(source, target, get_window_props().skeleton.scale_bones)

        for obj, visibility in obj_vis.items():
            obj.hide_set(visibility)

        return {'FINISHED'}
    
    def _get_armatures(self, context: Context) -> list[tuple[Object, Object]] | None:
        window = get_window_props().skeleton
        if window.combine_tab == 'SELECT':
            return [(context.active_object, get_skeleton_props().source)]
        
        else:
            prefixes = (window.base_prefix, window.source_prefix)
            targets  = {}
            sources  = {}
            for obj in context.view_layer.objects:
                if obj.type != 'ARMATURE':
                    continue
                for prefix in prefixes:
                    if not obj.name.startswith(prefix):
                        continue

                    name      = obj.name[len(prefix):].strip()
                    container = targets if prefix == window.base_prefix else sources
                    container[name] = obj
            
            return [(base, sources[name]) for name, base in targets.items() if name in sources]

class SklbManager(Operator):
    bl_idname      = "ya.sklb_manager"
    bl_label       = "Skeleton Manager"
    bl_options     = {"UNDO"}
    bl_description = "Manage skeleton properties"

    def _bone_search(self, context, edit_text: str) -> list[str]:
        armature: Armature = context.active_object.data
        anim_bones = {bone.name for layer in armature.kaos.anim_layers for bone in layer.bone_list}
        bone_set   = {bone.name for bone in armature.kaos.bone_list}
        if self.bfilter:
            bone_set -= anim_bones

        return sorted(bone_set)
  
    up      : BoolProperty(default=True, name="", description="", options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    add     : BoolProperty(default=True, name="", description="", options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    category: StringProperty(default="", name="", description="", options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    bfilter : BoolProperty(default=False, name="", description="Only show bones not in any other layer", options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    new_name: StringProperty(
                    default="Search for a bone...", 
                    name="", 
                    description="Search for a bone in the armature", 
                    search=_bone_search,
                    options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    
    @classmethod
    def description(cls, context, properties):
        if properties.category == "BONE_LIST":
            return "Move bone"

        elif properties.category == "BONE_SORT":
            return "Sort entire bone list according to vanilla/IVCS order"

        elif properties.category == "LAYER":
            return "Add/Remove layer"
            
        elif properties.category == "LAYER_BONE":
            return "Add/Remove bone"

    def invoke(self, context, event) -> None:
        self.props = get_skeleton_props()
        self.armature: Armature = context.active_object.data

        if self.category == "LAYER_BONE" and self.add:
            context.window_manager.invoke_props_dialog(self)
            return {'RUNNING_MODAL'}
        else:
            return self.execute(context)
    
    def draw(self, context) -> None:
        row = self.layout.row(align=True)
        row.prop(self, "new_name")
        row.prop(self, "bfilter", text="", icon='FILTER')

    def execute(self, context) -> None:
        manager  = RNAPropertyIO()
        bone_set = {bone.name for bone in self.armature.kaos.bone_list}
        if self.category == "BONE_LIST":
            bone_list = self.armature.kaos.bone_list
            manager.indexing = True
            manager.sort(bone_list, self.props.bone_idx, self.up)
            synchronise_bone_indices(self.armature)
            if self.up and self.props.bone_idx != 0:
                self.props.bone_idx -= 1
            elif not self.up and self.props.bone_idx < len(bone_list) - 1:
                self.props.bone_idx += 1

        elif self.category == "BONE_SORT":
            bone_list = list(self.armature.kaos.get_bone_indices().keys())
            bone_indices = sort_bone_list(bone_list)
            self.armature.kaos.bone_list.clear()
            for idx, bone in enumerate(bone_indices.keys()):
                new_bone = self.armature.kaos.bone_list.add()
                new_bone.name  = bone
                new_bone.index = idx
            synchronise_bone_indices(self.armature)

        elif self.category == "LAYER":
            layers = self.armature.kaos.anim_layers
            if self.add:
                new_layer = layers.add()
                new_layer.name = f"Layer #{len(layers)}"
                self.props.layer_idx += 1
            else:
                manager.remove(layers, idx_to_remove=self.props.layer_idx)
                self.props.layer_idx -= 1
            
            for idx, layer in enumerate(layers):
                layer.name = f"Layer #{idx + 1}"
            
        elif self.category == "LAYER_BONE":
            bone_list = self.armature.kaos.anim_layers[self.props.layer_idx].bone_list
            if self.add:
                if self.new_name in bone_set:
                    new_bone = bone_list.add()
                    new_bone.name = self.new_name
                    synchronise_bone_indices(self.armature)
            else:
                manager.remove(bone_list, idx_to_remove=self.props.layer_b_idx)

        return {'FINISHED'}

_map_enums: BlendEnum = []

def map_enums(self, context) -> BlendEnum:
    return _map_enums

class SklbMapping(Operator):
    bl_idname      = "ya.sklb_mapping"
    bl_label       = "Skeleton Mappings"
    bl_options     = {"UNDO"}
    bl_description = "Calculate skeleton bone mapping"

    idx     : IntProperty(default=True, name="", description="", options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    add     : BoolProperty(default=True, name="", description="", options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    category: StringProperty(default="", name="", description="", options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    
    def invoke(self, context, event):
        global _map_enums
        armature: Armature = context.active_object.data
        if self.category == 'GEN':
            calculate_mapping(armature, self.idx, armature.kaos.mappers[self.idx].existing)
        elif self.category == 'PARENT':
            if self.add and len(armature.kaos.mappers) < 4:
                armature.kaos.mappers.add()
            elif not self.add and event.ctrl:
                manager = RNAPropertyIO()
                manager.remove(armature.kaos.mappers, self.idx)
            _map_enums = [(str(idx), f"Parent #{idx + 1}", "") for idx, mapper in enumerate(armature.kaos.mappers)]

        return {'FINISHED'}

class SklbConfig(Operator):
    bl_idname      = "ya.sklb_config"
    bl_label       = "Skeleton Properties"
    bl_options     = {"UNDO"}
    bl_description = "View and configure skeleton properties"

    tab: EnumProperty(
            name= "",
            description= "Select a manager",
            items= [
                ("DATA", "Overview", "Overview and bone list", "INFO", 0),
                ("LAYER", "Animation Layers", "Animation Layers", "RENDER_ANIMATION", 1),
                ("MAP", "Mapping", "Racial animation mapping", "EMPTY_ARROWS", 2),
            ]
            )  # type: ignore
    
    map: EnumProperty(
            name= "",
            description= "Select a mapper",
            default=0,
            items=map_enums,
            options={'SKIP_SAVE'}
            )  # type: ignore

    def invoke(self, context, event):
        global _map_enums
        self.props              = get_skeleton_props()
        self.armature: Armature = context.active_object.data

        _map_enums = [(str(idx), f"Parent #{idx + 1}", "") for idx, mapper in enumerate(self.armature.kaos.mappers)]
        if _map_enums:
            self.map = "0"

        synchronise_bone_list(self.armature)

        self.blend_bones = {bone.name: bone for bone in self.armature.bones}
        if not self.armature:
            return {'FINISHED'}
        if self.props.bone_idx >= len(self.armature.kaos.bone_list): 
            self.props.bone_idx = 0
            
        context.window_manager.invoke_props_dialog(self, width=500)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        draw_sklb(self, self.layout, self.armature, self.props)

    def execute(self, context):
        global _map_enums

        _map_enums = []
        synchronise_bone_list(self.armature)
        return {'FINISHED'}


CLASSES = [
    SklbCombine,
    SklbMapping,
    SklbManager,
    SklbConfig
]