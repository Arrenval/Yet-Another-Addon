import bpy   

from bpy.types       import Operator, ShapeKey, Object, SurfaceDeformModifier, ShrinkwrapModifier, CorrectiveSmoothModifier
from ..properties    import get_outfit_properties, get_devkit_properties
from ..utils.objects import get_object_from_mesh
    
    
class ShapeKeyTransfer(Operator):
    bl_idname = "ya.transfer_shape_keys"
    bl_label = "Shape Keys"
    bl_description = "Transfers and links shape keys to your target mesh"
    bl_options = {"UNDO"}

    sub_keys     :bool = False
    shrinkwrap   :bool = False
    all_keys     :bool = False
    existing     :bool = False
    deforms      :bool = True
    vertex_pin   :str  = "None"
    exclude_wrap :str  = "None"
    smooth_level :str  = "None"
    shape_source :str  = None
    shape_target :str  = None

    @classmethod
    def poll(cls, context):
        props         = get_outfit_properties()
        obj:Object    = props.shapes_target
        source:Object = props.shapes_source
        if props.shapes_method != "Selected":
            return obj is not None and obj.visible_get() and obj.type == 'MESH' and context.mode == "OBJECT"
        else:
            return (obj is not None and source is not None) and obj.visible_get() and (obj.type == 'MESH' and source.type == 'MESH') and context.mode == "OBJECT"

    def execute(self, context):
  
        self.devkit                = get_devkit_properties()
        props                      = get_outfit_properties()
        self.deform_target         = {}
        self.input_method  :str    = props.shapes_method
        self.vertex_pin    :str    = props.obj_vertex_groups
        self.exclude_wrap  :str    = props.exclude_vertex_groups
        self.smooth_level  :str    = props.shapes_corrections
        self.shrinkwrap    :bool   = props.add_shrinkwrap
        self.object_target :Object = props.shapes_target
        self.seam_values   :dict   = {"wa_": props.seam_waist, "wr_": props.seam_wrist, "an_": props.seam_ankle}

        match self.input_method:
            case "Chest":
                self.sub_keys       :bool   = props.sub_shape_keys
                self.overhang       :bool   = props.adjust_overhang
                self.chest_base     :str    = props.shape_chest_base  
        
                source = self.devkit.yam_torso
                self.deform_target = self.get_shape_keys()

            case "Legs":
                self.leg_base       :str    = props.shape_leg_base

                if self.leg_base == "Skull":
                    self.leg_base = "Skull Crushers"

                if self.leg_base == "Melon":
                    self.leg_base = "Gen A/Watermelon Crushers"

                source = self.devkit.yam_legs
                self.deform_target = self.get_shape_keys()

            case "Seams":
                self.seams          :set     = {key for key, value in self.seam_values.items() if value}
                self.seam_base      :str     = props.shape_seam_base

                if self.seam_base == "YAB":
                    self.seam_base = "BASE"
                
                source = get_object_from_mesh("Body Controller")

            case "Selected":
                self.all_keys       :bool   = props.all_keys
                self.deforms        :bool   = props.include_deforms
                self.existing       :bool   = props.existing_only
                self.shape_source   :str    = props.shapes_source_enum
                self.shape_target   :str    = props.shapes_target_enum
                source              :Object = props.shapes_source
                
        self.transfer(source, self.object_target)
        return {'FINISHED'}
    
    def get_shape_keys(self) -> dict:
        options = {}
        prop = get_devkit_properties()
        leg_corrections = ["Rue/Lava", "Rue/Mini"]
        target = self.object_target

        for shape, (name, slot, shape_category, description, body, key) in prop.ALL_SHAPES.items():
            if key == "":
                continue
            if slot != self.input_method:
                continue
            slot_lower = slot.lower().replace("/", " ")
            key_lower = key.lower().replace(" ", "_")
            
            prop_name = f"shpk_{slot_lower}_{key_lower}"

            if hasattr(prop, prop_name):
                options[key] = (getattr(prop, prop_name))
        
        if self.input_method == "Chest":
            options[self.chest_base.upper()] = False

        if self.input_method == "Legs":
            options[self.leg_base] = False

            for key_name in leg_corrections:
                rue_shape = target.data.shape_keys and target.data.shape_keys.key_blocks.get("Rue")
                options[key_name] = True if options["Rue"] or rue_shape else False

        return options
    
    def add_driver(self, target_key:ShapeKey, driver_source:ShapeKey, source:Object, target:Object) -> None:
            target_key.driver_remove("value")
            target_key.driver_remove("mute")
            value = target_key.driver_add("value").driver
            mute = target_key.driver_add("mute").driver

            if self.input_method == "Chest" and target_key.name == "LARGE" and self.chest_base != "LARGE":
                value.type = "SCRIPTED"
                value.expression = "1 if mute == 0 else 0"
                value_var = value.variables.new()
                value_var.name = "mute"
                value_var.type = "SINGLE_PROP"

                value_var.targets[0].id_type = "KEY"
                value_var.targets[0].id = target.data.shape_keys
                value_var.targets[0].data_path = f'key_blocks["LARGE"].mute'
            elif self.input_method == "Legs" and target_key.name == "Gen A/Watermelon Crushers" and self.leg_base != "Melon":
                value.type = "SCRIPTED"
                value.expression = "1 if mute == 0 else 0"
                value_var = value.variables.new()
                value_var.name = "mute"
                value_var.type = "SINGLE_PROP"

                value_var.targets[0].id_type = "KEY"
                value_var.targets[0].id = target.data.shape_keys
                value_var.targets[0].data_path = f'key_blocks["Gen A/Watermelon Crushers"].mute'
            else:
                value.type = "AVERAGE"
                value_var = value.variables.new()
                value_var.name = "key_value"
                value_var.type = "SINGLE_PROP"

                value_var.targets[0].id_type = "KEY"
                value_var.targets[0].id = source.data.shape_keys
                value_var.targets[0].data_path = f'key_blocks["{driver_source.name}"].value'

            mute.type = "AVERAGE"
            mute_var = mute.variables.new()
            mute_var.name = "key_mute"
            mute_var.type = "SINGLE_PROP"
            
            mute_var.targets[0].id_type = "KEY"
            mute_var.targets[0].id = source.data.shape_keys
            mute_var.targets[0].data_path = f'key_blocks["{driver_source.name}"].mute'

    def transfer(self, main_source:Object, target:Object) -> None:

        def resolve_base_name() -> None:
            '''Resolves the name of the basis shape key. Important for relative key assignment later.'''

            if self.input_method == "Seams":
                pass
            elif self.input_method == "Chest" and self.chest_base != "Large":
                target.data.shape_keys.key_blocks[0].name = self.chest_base.upper()
            elif self.input_method == "Legs" and self.leg_base != "Gen A/Watermelon Crushers":
                target.data.shape_keys.key_blocks[0].name = self.leg_base
            else:
                target.data.shape_keys.key_blocks[0].name = main_source.data.shape_keys.key_blocks[0].name

        def finalise_key_relationship() -> None:
            '''Sets appropriate relative keys and assigns a driver.'''

            if self.input_method == "Chest" and self.chest_base != "Large" and driver_source.relative_key.name == "Large":
                target_key.relative_key = target.data.shape_keys.key_blocks[self.chest_base.upper()]
            elif self.input_method == "Legs" and self.leg_base != "Gen A/Watermelon Crushers" and driver_source.relative_key.name == "Gen A/Watermelon Crushers":
                target_key.relative_key = target.data.shape_keys.key_blocks[self.leg_base]
            elif target_key.name == "shpx_wa_yabs":
                try:
                    target_key.relative_key = target.data.shape_keys.key_blocks["Buff"]
                except:
                    target_key.relative_key = target.data.shape_keys.key_blocks[0]
            else:
                try:
                    target_key.relative_key = target.data.shape_keys.key_blocks[driver_source.relative_key.name]
                except:
                    target_key.relative_key = target.data.shape_keys.key_blocks[0]
            
            if target_key.name[8:11] == "_c_" or self.input_method == "Seams":
                return

            self.add_driver(target_key, driver_source, main_source, target)
        
        sk_transfer:list[ShapeKey] = []

        if not target.data.shape_keys:
            target.shape_key_add(name="Basis", from_mix=False)

        resolve_base_name()
        
        if self.all_keys or self.input_method != "Selected":
            for key in main_source.data.shape_keys.key_blocks:
                sk_transfer.append(key)
        else:
            source_key = main_source.data.shape_keys.key_blocks.get(self.shape_source)
            sk_transfer.append(source_key)
        
        shape_key_queue = self.shape_key_queue(sk_transfer, main_source, target)

        for target_key, temp_source, source_key, driver_source, model_state, deform in shape_key_queue:
            if deform:
                self.add_modifier(target_key, temp_source, source_key, target, model_state)
        
        for target_key, source, source_key, driver_source, model_state, deform in shape_key_queue:
            finalise_key_relationship()

    def shape_key_queue(self, shape_key_list:list[ShapeKey], source:Object, target:Object) -> list[tuple[ShapeKey, Object, ShapeKey, ShapeKey, list[ShapeKey], bool]]:
        # A quirk of how the devkit is setup is that when using the specialised transfer methods the source and source_key will refer to different Objects.
        # driver_source is added to account for this later when adding drivers.

        def get_target_key(key_name:str):
            target_key = target.data.shape_keys.key_blocks.get(key_name)
            if not target_key:
                target_key = target.shape_key_add(name=key_name, from_mix=False)
    
            return target_key

        shape_key_queue = []

        if self.devkit:
            chest_controller: Object = get_object_from_mesh("Chest Controller")
            body_controller : Object = get_object_from_mesh("Body Controller")

        for source_key in shape_key_list:
            # Model state is a list of keys that should be turned on before enabling the surface deform
            model_state   = []
            new_name      = source_key.name
            driver_source = source_key
            deform        = True

            if self.input_method == "Selected":
                if self.all_keys:
                    target_key = target.data.shape_keys.key_blocks.get(new_name)
                    if not target_key and not self.existing:
                        target_key = target.shape_key_add(name=new_name, from_mix=False)

                else:
                    if self.shape_target == "None":
                        target_key = target.shape_key_add(name=new_name, from_mix=False)
                    else:
                        target_key = target.data.shape_keys.key_blocks.get(self.shape_target)

                if not target_key:
                    continue

                if not self.deforms:
                    deform = False
                     
            if self.input_method == "Chest":
                if source_key.name not in self.deform_target and not source_key.name.startswith("-"):
                    continue
                if source_key.name.startswith("-") or not self.deform_target[source_key.name]:
                    if self.all_keys and source_key.name.startswith("-"):
                        deform = False
                    else:
                        continue
                if source_key.name == "CORRECTIONS:":
                    break

                chest_key = chest_controller.data.shape_keys.key_blocks.get(source_key.name)
                body_key  = body_controller.data.shape_keys.key_blocks.get(source_key.name)

                if chest_key:
                    source_key = chest_key
                    source     = chest_controller
                elif body_key:
                    source_key = body_key
                    source     = body_controller
                elif not self.sub_keys:
                    continue
                
                target_key = get_target_key(new_name)

            if self.input_method == "Legs":
                if source_key.name not in self.deform_target:
                    continue
                if not self.deform_target[source_key.name]:
                    continue
                
                body_key = body_controller.data.shape_keys.key_blocks.get(source_key.name)
                rue_key  = body_controller.data.shape_keys.key_blocks.get("Rue")
                lava_key = body_controller.data.shape_keys.key_blocks.get("Lavabod")
                
                if body_key:
                    source_key = body_key
                    source     = body_controller
                else:
                    continue

                if source_key.name == "Soft Butt":
                    new_name = "shpx_yam_softbutt"

                if source_key.name == "Alt Hips":
                    driver_source = source.data.shape_keys.key_blocks.get("Hip Dips (for YAB)")
                    new_name = "shpx_yab_hip"
                    
                    if self.deform_target["Rue"] or target.data.shape_keys.key_blocks.get("Rue"):
                        rue_hip_driver = source.data.shape_keys.key_blocks.get("Less Hip Dips (for Rue)")

                        target_key = get_target_key("shpx_rue_hip")

                        shape_key_queue.append((target_key, source, source_key, rue_hip_driver, [rue_key], deform))

                    if self.deform_target["Soft Butt"] or target.data.shape_keys.key_blocks.get("shpx_softbutt"):
                        target_key = get_target_key("shpx_yab_c_hipsoft")
                        correction_source_key = source.data.shape_keys.key_blocks.get("shpx_yab_c_hipsoft")
                        correction_driver_source = source.data.shape_keys.key_blocks.get("shpx_yab_c_hipsoft")

                        shape_key_queue.append((target_key, source, correction_source_key, correction_driver_source, [rue_key], deform))

                        if self.deform_target["Rue"] or target.data.shape_keys.key_blocks.get("Rue"):
                            target_key = get_target_key("shpx_rue_c_hipsoft")
                            correction_source_key = source.data.shape_keys.key_blocks.get("shpx_rue_c_hipsoft")
                            correction_driver_source = source.data.shape_keys.key_blocks.get("shpx_rue_c_hipsoft")

                            shape_key_queue.append((target_key, source, correction_source_key, correction_driver_source, [rue_key], deform))
                    

                if source_key.name == "Rue/Lava":
                    if not target.data.shape_keys.key_blocks.get("Lavabod"):
                        continue
                    model_state.append(lava_key)

                if source_key.name == "Rue/Mini":
                    if not target.data.shape_keys.key_blocks.get("Mini"):
                        continue
                    model_state.append(rue_key)
            
                target_key = get_target_key(new_name)

            if self.input_method == "Seams":
                if source_key.name[5:8] not in self.seams:
                    if self.seam_values["wa_"] and source_key.name == "shpx_yam_c_softwaist":
                        pass
                    else:
                        continue
                
                if not source.data.shape_keys.key_blocks.get(source_key.name):
                    continue

                buff = target.data.shape_keys.key_blocks.get("Buff")
                if buff and source_key.name == "shpx_wa_yabs":
                    model_state.append(buff)

                target_key = get_target_key(new_name)

            shape_key_queue.append((target_key, source, source_key, driver_source, model_state, deform))
        
        return shape_key_queue
                    
    def add_modifier(self, target_key:ShapeKey, source:Object, source_key:ShapeKey, target:Object, model_state:list[ShapeKey]) -> None:

        def base_model_state() -> float:
            chest_filter = {"LARGE", "MEDIUM", "SMALL", "MASC"} 
            leg_filter   = {"Gen A/Watermelon Crushers", "Skull Crushers", "Yanilla", "Mini", "Lavabod", "Masc"} 

            old_value = source_key.value
            source_key.mute = False
            source_key.value = 1

            if self.input_method == "Chest" and target_key.name in chest_filter:
                source.data.shape_keys.key_blocks[self.chest_base.upper()].mute = True

            elif self.input_method == "Legs" and target_key.name in leg_filter:
                source.data.shape_keys.key_blocks[self.leg_base].mute = True

            for key in model_state:
                key.mute = False

            return old_value

        def controller_state(reset=False) -> None:
            key_blocks = source.data.shape_keys.key_blocks
            for key in key_blocks:
                key.mute = True

            if source.data.name == "Chest Controller" and self.input_method == "Chest":
                key_blocks[self.chest_base.upper()].mute = False

            if source.data.name == "Body Controller":
                if self.input_method == "Legs":
                    key_blocks[self.leg_base].mute = False
                if self.input_method == "Seams":
                    key_blocks[self.seam_base].mute = False
            
            if not reset:
                if source.data.name == "Chest Controller" and self.overhang:
                    key_blocks["Overhang"].mute = False

        controller_state()

        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = target
        target.select_set(state=True)
        bpy.ops.object.modifier_add(type='SURFACE_DEFORM')
        modifier: SurfaceDeformModifier = target.modifiers[-1]
        modifier.target = source
        bpy.ops.object.surfacedeform_bind(modifier=modifier.name)
        
        if self.vertex_pin != "None":
            modifier.vertex_group = self.vertex_pin
            modifier.invert_vertex_group = True
        
        old_value = base_model_state()

        self.apply_modifier(target_key, target, modifier.name)
        
        source_key.value = old_value
        target_key.value = 1

        if self.smooth_level != "None":
            self.deform_corrections(target_key, source, target, self.smooth_level)

        # Second pass of shrinkwrap with less aggressive smooth corrective
        if self.shrinkwrap:
            self.deform_corrections(target_key, source, target, "Smooth")
        
        target_key.value = 0
        
        controller_state(reset=True)

    def deform_corrections(self, target_key:ShapeKey, source:Object, target:Object, smooth:str) -> None:
        if smooth == "Aggressive":
            factor = 1.0
            iterations = 10
        else:
            factor = 0.5
            iterations = 5

        if self.shrinkwrap:
            bpy.ops.object.modifier_add(type='SHRINKWRAP')
            shr_modifier: ShrinkwrapModifier = target.modifiers[-1]
            shr_modifier.target = source
            shr_modifier.wrap_mode = 'OUTSIDE'
            shr_modifier.offset = 0.001

            self.shrinkwrap_exclude(target, shr_modifier)
            self.apply_modifier(target_key, target, shr_modifier.name)

            if self.exclude_wrap != "None" and self.vertex_pin != "None":
                bpy.ops.object.vertex_group_remove(all=False)

        if smooth != "None":
            bpy.ops.object.modifier_add(type='CORRECTIVE_SMOOTH')
            cor_modifier: CorrectiveSmoothModifier = target.modifiers[-1]
            cor_modifier.factor = factor
            cor_modifier.iterations = iterations
            cor_modifier.use_pin_boundary = True
            if self.vertex_pin != "None":
                cor_modifier.vertex_group = self.vertex_pin
                cor_modifier.invert_vertex_group = True

            self.apply_modifier(target_key, target, cor_modifier.name)

    def shrinkwrap_exclude(self, target:Object, modifier:ShrinkwrapModifier) -> None:
        if self.exclude_wrap != "None":
            if self.vertex_pin != "None" and self.smooth_level != "None":
                target.vertex_groups.active = target.vertex_groups[self.vertex_pin]
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.object.vertex_group_select()
                target.vertex_groups.active = target.vertex_groups[self.exclude_wrap]
                bpy.ops.object.vertex_group_select()
                bpy.ops.object.vertex_group_assign_new()
                bpy.ops.object.mode_set(mode='OBJECT')
                modifier.vertex_group = target.vertex_groups[-1].name

            else:
                modifier.vertex_group = self.exclude_wrap

        elif self.vertex_pin != "None":
            modifier.vertex_group = self.vertex_pin
        
        if modifier.vertex_group != "":
            modifier.invert_vertex_group = True

    def apply_modifier(self, target_key:ShapeKey, target:Object, modifier:str) -> None:
        # Blends shape from modifier into the intended transfer shape key
        bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=False, modifier=modifier)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        key_index = target.data.shape_keys.key_blocks.find(target_key.name)
        target.active_shape_key_index = key_index
        bpy.ops.mesh.blend_from_shape(shape=modifier, add=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')

        # Removes shape key created by modifier
        key_index = target.data.shape_keys.key_blocks.find(modifier)
        target.active_shape_key_index = key_index
        bpy.ops.object.shape_key_remove(all=False)

        
CLASSES = [
    ShapeKeyTransfer
]