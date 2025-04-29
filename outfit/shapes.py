import bpy   

from bpy.types     import Operator, ShapeKey, Object, SurfaceDeformModifier, ShrinkwrapModifier, CorrectiveSmoothModifier
    
    
class ShapeKeyTransfer(Operator):
    bl_idname = "ya.transfer_shape_keys"
    bl_label = "Shape Keys"
    bl_description = "Transfers and links shape keys to your active mesh"
    bl_options = {'UNDO'}

    sub_keys_bool:bool = False
    shrinkwrap   :bool = False
    chest_base   :str  = ""
    vertex_pin   :str  = "None"
    exclude_wrap :str  = "None"

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return obj is not None and obj.type == 'MESH' and context.mode == "OBJECT"

    def execute(self, context):
        props                           = bpy.context.scene.outfit_props
        self.key_filter                 = [".ignore"]
        self.deform_target              = {}
        self.chest_deforms              = ["LARGE", "MEDIUM", "SMALL"]
        self.source_input       :str    = props.shape_key_source
        
        if hasattr(bpy.context.scene, "devkit"):
            self.devkit                 = bpy.context.scene.devkit

        if self.source_input == "Chest":
            self.shrinkwrap     :bool   = props.add_shrinkwrap
            self.sub_keys_bool  :bool   = props.sub_shape_keys
            self.overhang       :bool   = props.adjust_overhang
            self.chest_base     :str    = props.shape_key_base
            self.vertex_pin     :str    = props.obj_vertex_groups
            self.exclude_wrap   :str    = props.exclude_vertex_groups

        match self.source_input:
            case "Chest":
                source = self.devkit.get_object_from_mesh("Torso")
                ignore = ["bibo arms", "no shoulder blades", "buff/rue", "corrections:", "other:"]
                sub_keys =  ["squeeze", "squish", "push-up", "omoi", "sag", "nip nops", "sayonara", "mini"]
                for sub in ignore:
                    self.key_filter.append(sub)
                
                if not self.sub_keys_bool:
                    for sub in sub_keys:
                        self.key_filter.append(sub)
                self.deform_target = self.get_shape_keys()
            case "Legs":
                source = self.devkit.get_object_from_mesh("Waist")
                ignore = ["gen ", "rue/mini", "rue/lava", "less hip dips (", "hip dips (", "bodies:", "corrections:", "other:"]
                for sub in ignore:
                    self.key_filter.append(sub)
                self.deform_target = self.get_shape_keys()
            case _:
                try:
                    source = [obj for obj in context.selected_objects if obj != context.active_object][0]
                except:
                    self.report({'ERROR'}, "Missing source and/or target object.")
                    return {'CANCELLED'}
                    
        target = context.active_object
        self.transfer(source, target)
        return {'FINISHED'}
    
    def get_shape_keys(self) -> dict:
        options = {}
        prop = bpy.context.scene.devkit_props

        for shape, (name, slot, shape_category, description, body, key) in prop.ALL_SHAPES.items():
            if key == "":
                continue
            if slot != self.source_input:
                continue
            slot_lower = slot.lower().replace("/", " ")
            key_lower = key.lower().replace(" ", "_")
            
            prop_name = f"shpk_{slot_lower}_{key_lower}"

            if hasattr(prop, prop_name):
                options[shape] = (getattr(prop, prop_name), key)
        
        if self.source_input == "Chest":
            options[self.chest_base] = (False , self.chest_base.upper())

        return options
    
    def add_driver(self, new_key:ShapeKey, source:Object, target:Object) -> None:
            new_key.driver_remove("value")
            new_key.driver_remove("mute")
            value = new_key.driver_add("value").driver
            mute = new_key.driver_add("mute").driver

            if new_key.name == "LARGE" and self.chest_base != "LARGE":
                value.type = "SCRIPTED"
                value.expression = "1 if mute == 0 else 0"
                value_var = value.variables.new()
                value_var.name = "mute"
                value_var.type = "SINGLE_PROP"

                value_var.targets[0].id_type = "KEY"
                value_var.targets[0].id = target.data.shape_keys
                value_var.targets[0].data_path = f'key_blocks["LARGE"].mute'
            else:
                value.type = "AVERAGE"
                value_var = value.variables.new()
                value_var.name = "key_value"
                value_var.type = "SINGLE_PROP"

                value_var.targets[0].id_type = "KEY"
                value_var.targets[0].id = source.data.shape_keys
                value_var.targets[0].data_path = f'key_blocks["{new_key.name}"].value'

            mute.type = "AVERAGE"
            mute_var = mute.variables.new()
            mute_var.name = "key_mute"
            mute_var.type = "SINGLE_PROP"
            
            mute_var.targets[0].id_type = "KEY"
            mute_var.targets[0].id = source.data.shape_keys
            mute_var.targets[0].data_path = f'key_blocks["{new_key.name}"].mute'

    def transfer(self, source:Object, target:Object) -> None:

        def create_keys(shape_key:ShapeKey, target:Object, relative:str) -> None:
            if target.data.shape_keys.key_blocks.get(shape_key.name):
                    new_key = target.data.shape_keys.key_blocks[shape_key.name]
            else:
                new_key = target.shape_key_add(name=shape_key.name, from_mix=False)
            try:
                new_key.relative_key = target.data.shape_keys.key_blocks[relative]
            except:
                self.retry_relative.append((new_key, relative))

            self.deform(new_key, target)
            self.driver.append(new_key)

        sub_keys = ["squeeze", "squish", "push-up", "omoi", "sag", "nip nops", "sayonara", "mini"]
        transfer = [
            key for key in source.data.shape_keys.key_blocks 
            if not any(sub in key.name.lower() for sub in self.key_filter)
            ]
        new_base           : list[tuple[ShapeKey, str]] = []
        self.driver        : list[ShapeKey]             = []
        self.retry_relative: list[tuple[ShapeKey, str]] = []

        if self.source_input == "Chest" and self.chest_base != "Large":
            try:
                target.data.shape_keys.key_blocks[0].name = self.chest_base.upper()
            except AttributeError:
                target.shape_key_add(name=self.chest_base.upper())
        else:
            try:
                target.data.shape_keys.key_blocks[0].name = source.data.shape_keys.key_blocks[0].name
            except AttributeError:
                target.shape_key_add(name=source.data.shape_keys.key_blocks[0].name)

        for shape_key in transfer:
            if self.source_input == "Chest" and self.chest_base != "Large" and shape_key.relative_key.name != self.chest_base.upper():
                # filters out and reorders shape keys to match the new base shape if selected
                if any(key in shape_key.name.lower() for key in sub_keys): 
                    new_base.append((shape_key, shape_key.relative_key.name))
                else:
                    new_base.append((shape_key, self.chest_base.upper()))
                continue

            create_keys(shape_key, target, shape_key.relative_key.name)

        for (shape_key, relative) in new_base:
            # adds back the filtered shape keys for the new base
            create_keys(shape_key, target, relative)

        for new_key in self.driver:
            self.add_driver(new_key, source, target)
            
        for (key, relative) in self.retry_relative:
            key.relative_key = target.data.shape_keys.key_blocks[relative]
        
        if self.sub_keys_bool:
            for shape_key in transfer:
                if any(key in shape_key.name.lower() for key in sub_keys):
                    relative = shape_key.relative_key.name
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    key_index = target.data.shape_keys.key_blocks.find(shape_key.name)
                    target.active_shape_key_index = key_index
                    bpy.ops.mesh.blend_from_shape(shape=relative, add=False)    
                    bpy.ops.mesh.select_all(action='DESELECT')
                    bpy.ops.object.mode_set(mode='OBJECT')
                    
    def deform(self, new_key:ShapeKey, target:Object) -> None:
        if any(key == new_key.name for shape, (bool, key) in self.deform_target.items() if bool == True):
            if any(new_key.name == deform for deform in self.chest_deforms):
                source = self.devkit.get_object_from_mesh("Chest Controller")
            else:
                source = self.devkit.get_object_from_mesh("Body Controller")

            if new_key.name == "Alt Hips":
                driver_source = self.devkit.get_object_from_mesh("Waist")
                new_key = target.shape_key_add(name="Hip Dips (for YAB)", from_mix=False)
                self.add_modifier(new_key.name, source, target)
                self.add_driver(new_key, driver_source, target)

                if self.deform_target["Rue Legs"][0]:
                    new_key = target.shape_key_add(name="Less Hip Dips (for Rue)", from_mix=False)
                    self.add_modifier("Less Hip Dips (for Rue)", source, target)
                    self.add_driver(new_key, driver_source, target)
                    new_key.relative_key = target.data.shape_keys.key_blocks["Rue"]
            else:
                self.add_modifier(new_key.name, source, target)

    def add_modifier(self, key_name:str, source:Object, target:Object) -> None:
        source_keys = source.data.shape_keys.key_blocks
        self.controller_state(source)
        bpy.ops.object.modifier_add(type='SURFACE_DEFORM')
        modifier: SurfaceDeformModifier = target.modifiers[-1]
        modifier.target = source
        bpy.ops.object.surfacedeform_bind(modifier=modifier.name)

        if self.vertex_pin != "None":
            modifier.vertex_group = self.vertex_pin
            modifier.invert_vertex_group = True
        if key_name == "Less Hip Dips (for Rue)":
            source_keys["Rue"].mute = False
        if "Hip Dips" in key_name:
            source_keys["Alt Hips"].mute = False
        else:
            if source.data.name == "Chest Controller" and self.chest_base != "Large" and key_name != self.chest_base.upper():
                source_keys[self.chest_base.upper()].mute = True
                source_keys[key_name].mute = False
            else:
                source_keys[key_name].mute = False

        self.apply_modifier(key_name, target, modifier.name)
        if self.source_input == "Chest":
            if any(key_name == deform for deform in self.chest_deforms) and key_name != self.chest_base.upper():
                target.data.shape_keys.key_blocks[key_name].value = 1

                self.deform_corrections(key_name, source, target, high=True)

                # Second pass of shrinkwrap with less aggressive smooth corrective
                if self.shrinkwrap:
                    self.deform_corrections(key_name, source, target, high=False)

                target.data.shape_keys.key_blocks[key_name].value = 0
        else:
            target.data.shape_keys.key_blocks[key_name].value = 1
            self.deform_corrections(key_name, source, target, high=False)
            target.data.shape_keys.key_blocks[key_name].value = 0
        
        self.controller_state(source, reset=True)

    def deform_corrections(self, key_name:str, source:Object, target:Object, high:bool) -> None:
        if high:
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
            self.apply_modifier(key_name, target, shr_modifier.name)

            if self.exclude_wrap != "None" and self.vertex_pin != "None":
                bpy.ops.object.vertex_group_remove(all=False)

        bpy.ops.object.modifier_add(type='CORRECTIVE_SMOOTH')
        cor_modifier: CorrectiveSmoothModifier = target.modifiers[-1]
        cor_modifier.factor = factor
        cor_modifier.iterations = iterations
        cor_modifier.use_pin_boundary = True
        if self.vertex_pin != "None":
            cor_modifier.vertex_group = self.vertex_pin
            cor_modifier.invert_vertex_group = True

        self.apply_modifier(key_name, target, cor_modifier.name)

    def shrinkwrap_exclude(self, target:Object, modifier) -> None:
        if self.exclude_wrap != "None":
            if self.vertex_pin != "None":
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
        modifier.invert_vertex_group = True

    def apply_modifier(self, key_name:str, target:Object, modifier:str) -> None:
        bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=False, modifier=modifier)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        key_index = target.data.shape_keys.key_blocks.find(key_name)
        target.active_shape_key_index = key_index
        bpy.ops.mesh.blend_from_shape(shape=modifier, add=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        key_index = target.data.shape_keys.key_blocks.find(modifier)
        target.active_shape_key_index = key_index
        bpy.ops.object.shape_key_remove(all=False)

    def controller_state(self, source:Object, reset=False) -> None:
        key_blocks = source.data.shape_keys.key_blocks
        for key in key_blocks:
            key.mute = True

        if source.data.name == "Chest Controller":
            if self.overhang and not reset:
                key_blocks["Overhang"].mute = False
            key_blocks[self.chest_base.upper()].mute = False

CLASSES = [
    ShapeKeyTransfer
]