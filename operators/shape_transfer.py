import bpy   
from bpy.types       import Operator, ShapeKey, Object, SurfaceDeformModifier, ShrinkwrapModifier, CorrectiveSmoothModifier

from ..properties         import get_outfit_properties, get_devkit_properties, get_window_properties, get_devkit_win_props
from ..mesh.shapes        import create_co_cache, create_shape_keys
from ..mesh.weights       import combine_v_groups
from ..utils.objects      import quick_copy, safe_object_delete
from ..utils.ya_exception import SurfaceDeformBindError, VertexCountError


ShapeKeyQueue = list[tuple[Object, Object, ShapeKey, ShapeKey, ShapeKey, bool]]

def get_target_key(target: Object, key_name:str):
    target_key = target.data.shape_keys.key_blocks.get(key_name)
    if not target_key:
        target_key = target.shape_key_add(name=key_name, from_mix=False)

    return target_key

class ControllerVisibility(Operator):
    bl_idname = "ya.chest_controller"
    bl_label = ""
    bl_description = "Show the controller mesh"
    bl_options = {"UNDO"}

    def execute(self, context):
        controller = get_devkit_properties().yam_shapes
        collection = context.view_layer.layer_collection.children["Resources"].children["Controller"]
        
        if controller.visible_get():
             collection.exclude = True
        else:
            collection.exclude = False
            for obj in bpy.data.collections.get("Controller").objects:
                obj.hide_set(state=True)

            controller.hide_set(state=False)

        return {'FINISHED'}
    
class ShapeKeyTransfer(Operator):
    bl_idname = "ya.transfer_shape_keys"
    bl_label = "Shape Keys"
    bl_description = "Transfers and links shape keys to your target mesh"
    bl_options = {"UNDO"}

    sub_keys    : bool = False
    deforms     : bool = True
    vertex_pin  : str  = "None"
    exclude_wrap: str  = "None"
    smooth_level: str  = "None"
    shape_source: str  = None
    shape_target: str  = None
    shapes_type : str  = "None"

    @classmethod
    def poll(cls, context):
        props         = get_outfit_properties()
        obj:Object    = props.shapes_target
        source:Object = props.shapes_source
        if get_window_properties().shapes_method != "Selected":
            return obj is not None and obj.visible_get() and obj.type == 'MESH' and context.mode == "OBJECT"
        else:
            return (obj is not None and source is not None) and obj.visible_get() and (obj.type == 'MESH' and source.type == 'MESH') and context.mode == "OBJECT"

    def execute(self, context):
        self.devkit               = get_devkit_properties()
        props                     = get_outfit_properties()
        window                    = get_window_properties()
        self.deform_target        = {}
        self.input_method: str    = window.shapes_method
        self.vertex_pin  : str    = window.obj_vertex_groups
        self.exclude_wrap: str    = window.exclude_vertex_groups
        self.smooth_level: str    = window.shapes_corrections
        self.shrinkwrap  : bool   = window.add_shrinkwrap
        self.target      : Object = props.shapes_target
        self.shr_group   : str    = ""
        self.seam_values : dict   = {"wa_": window.seam_waist, "wr_": window.seam_wrist, "an_": window.seam_ankle}
    
        self.cleanup     : list[Object] = []    

        if self.input_method == "Chest":
            self.sub_keys  : bool = window.sub_shape_keys
            self.overhang  : bool = window.adjust_overhang
            self.chest_base: str  = props.shape_chest_base  
    
            self.source = self.devkit.yam_torso
            self.deform_target = self.get_shape_keys()

        elif self.input_method == "Legs":
            self.leg_base: str = window.shape_leg_base

            if self.leg_base == "Skull":
                self.leg_base = "Skull Crushers"

            if self.leg_base == "Melon":
                self.leg_base = "Gen A/Watermelon Crushers"

            self.source = self.devkit.yam_legs
            self.deform_target = self.get_shape_keys()

        elif self.input_method == "Seams":
            self.seams    : set = {key for key, value in self.seam_values.items() if value}
            self.seam_base: str = window.shape_seam_base
            self.source         = self.devkit.yam_shapes

        else:
            self.shapes_type : str    = window.shapes_type
            self.deforms     : bool   = window.include_deforms
            self.shape_source: str    = window.shapes_source_enum
            self.shape_target: str    = window.shapes_target_enum
            self.source      : Object = props.shapes_source

        try:
            shr_combined = self._shrinkwrap_exclude()
            self.transfer()
        
        except SurfaceDeformBindError:
            self.report({'ERROR'}, "Unable to bind Surface Deform. Adding a triangulate modifier can fix this.")
            return {'FINISHED'}
        
        except VertexCountError:
            self.report({'ERROR'}, "Vertex count mismatch, please temporarily disable any topology altering modifiers.")
            return {'FINISHED'}
        
        except Exception as e:
            raise e
        
        finally:
            if shr_combined:
                combined_group = self.target.vertex_groups.get(self.shr_group)
                self.target.vertex_groups.remove(combined_group)
    
            for obj in self.cleanup:
                if isinstance(obj, Object):
                    safe_object_delete(obj)
                else:
                    try:
                        bpy.data.meshes.remove(obj, do_id_user=True, do_ui_user=True, do_unlink=True)
                    except:
                        pass
        
        self.report({'INFO'}, "Shapes transferred!")
        return {'FINISHED'}
    
    def _shrinkwrap_exclude(self) -> bool:
        combined = False

        if self.exclude_wrap != "None" and self.vertex_pin != "None" and self.smooth_level != "None":
            v_groups = [self.target.vertex_groups.get(self.exclude_wrap).index,
                       self.target.vertex_groups.get(self.vertex_pin).index]
            combined_group = combine_v_groups(self.target, v_groups)

            combined = True
            self.shr_group = combined_group.name

        elif self.exclude_wrap != "None":
            self.shr_group = self.exclude_wrap

        elif self.vertex_pin != "None":
            self.shr_group = self.vertex_pin
        
        return combined
      
    def get_shape_keys(self) -> dict:
        options = {}
        prop    = get_devkit_properties()
        dev_win = get_devkit_win_props()
        target  = self.target

        for shape, (name, slot, shape_category, description, body, key) in prop.ALL_SHAPES.items():
            if key == "":
                continue
            if slot != self.input_method:
                continue
            slot_lower = slot.lower().replace("/", " ")
            key_lower = key.lower().replace("- ", "").replace("-", "").replace(" ", "_")
            
            prop_name = f"shpk_{slot_lower}_{key_lower}"
            if hasattr(dev_win, prop_name):
                options[key] = (getattr(dev_win, prop_name))

        lava_shape = target.data.shape_keys and target.data.shape_keys.key_blocks.get("Lavabod")
        buff_shape = target.data.shape_keys and target.data.shape_keys.key_blocks.get("Buff")
        rue_shape  = target.data.shape_keys and target.data.shape_keys.key_blocks.get("Rue")
        mini_shape = target.data.shape_keys and target.data.shape_keys.key_blocks.get("Mini")

        lava_options = any(value for option, value in options.items() 
                            if option in ("Lavabod", "-- Teardrop", "--- Cupcake"))
        
        if self.input_method == "Chest":
            if self.chest_base == "Teardrop":
                options["-- Teardrop"] = False
            elif self.chest_base == "Cupcake":
                options["--- Cupcake"] = False
            else:
                options[self.chest_base] = False

            options["Rue/Buff"] = True if (options["Buff"] or buff_shape) and (options["Rue"] or rue_shape) else False
            options["Rue/Lava"] = True if (lava_options or lava_shape) and (options["Rue"] or rue_shape) else False

        if self.input_method == "Legs":
            options[self.leg_base] = False
            
            options["Rue/Mini"] = True if (options["Mini"] or mini_shape) and (options["Rue"] or rue_shape) else False
            options["Rue/Lava"] = True if (lava_options or lava_shape) and (options["Rue"] or rue_shape) else False

        return options
    
    def transfer(self) -> None:

        def resolve_base_name() -> None:
            '''Resolves the name of the basis shape key. Important for relative key assignment later.'''

            if self.input_method == "Seams":
                pass

            elif self.input_method == "Chest" and self.chest_base != "Large":
                self.target.data.shape_keys.key_blocks[0].name = self.chest_base.upper()

            elif self.input_method == "Legs" and self.leg_base != "Gen A/Watermelon Crushers":
                self.target.data.shape_keys.key_blocks[0].name = self.leg_base

            else:
                self.target.data.shape_keys.key_blocks[0].name = self.source.data.shape_keys.key_blocks[0].name

        def finalise_key_relationship() -> None:
            '''Sets appropriate relative keys and assigns a driver.'''

            if self.input_method == "Chest" and self.chest_base != "Large" and driver_source.relative_key.name == "LARGE":
                target_key.relative_key = self.target.data.shape_keys.key_blocks[self.chest_base.upper()]
                
            elif self.input_method == "Legs" and self.leg_base != "Gen A/Watermelon Crushers" and driver_source.relative_key.name == "Gen A/Watermelon Crushers":
                target_key.relative_key = self.target.data.shape_keys.key_blocks[self.leg_base]

            elif target_key.name == "shpx_wa_yabs":
                try:
                    target_key.relative_key = self.target.data.shape_keys.key_blocks["Buff"]
                except:
                    target_key.relative_key = self.target.data.shape_keys.key_blocks[0]
            else:
                try:
                    target_key.relative_key = self.target.data.shape_keys.key_blocks[driver_source.relative_key.name]
                except:
                    target_key.relative_key = self.target.data.shape_keys.key_blocks[0]
            
            if target_key.name[8:11] == "_c_" or self.input_method == "Seams":
                return

            self._add_driver(target_key, driver_source, self.source)
        
        sk_transfer: list[ShapeKey] = []

        if self.shapes_type != 'EXISTING':
            if not self.target.data.shape_keys:
                self.target.shape_key_add(name="Basis", from_mix=False)
            resolve_base_name()

        if not self.target.data.shape_keys:
            return
        
        base_key = self.target.data.shape_keys.key_blocks[0].name
        
        if self.shapes_type in ('ALL', 'EXISTING') or self.input_method != "Selected":
            for key in self.source.data.shape_keys.key_blocks:
                sk_transfer.append(key)
        else:
            source_key = self.source.data.shape_keys.key_blocks.get(self.shape_source)
            sk_transfer.append(source_key)
        
        shape_key_queue = self.shape_key_queue(sk_transfer)

        if not shape_key_queue:
            return
        
        base_copy = quick_copy(self.target)
        self.cleanup.append(base_copy)
        self.cleanup.append(base_copy.data)
        
        shapes: dict[str, Object] = {base_key: base_copy}
        for temp_target, controller, target_key, controller_key, driver_source, deform in shape_key_queue:
            if deform:
                self.add_modifier(temp_target, controller, target_key, controller_key)
                shapes[target_key.name] = temp_target
        
        for temp_target, controller, target_key, controller_key, driver_source, deform in shape_key_queue:
            finalise_key_relationship()

        co_cache = {}
        for key in self.target.data.shape_keys.key_blocks:
            relative_key = key.relative_key.name
            if relative_key not in co_cache and relative_key in shapes:
                co_cache[key.relative_key.name] = None

        vert_count = len(self.target.data.vertices)
        depsgraph  = bpy.context.evaluated_depsgraph_get()

        if vert_count != len(base_copy.data.vertices):
            raise VertexCountError
        
        create_co_cache(co_cache, shapes, self.target, base_key, vert_count, depsgraph)

        create_shape_keys(co_cache, shapes, self.target, base_key, vert_count, depsgraph)
        
    def shape_key_queue(self, shape_key_list: list[ShapeKey]) -> ShapeKeyQueue:
        if self.input_method == "Chest":
            return self._chest_queue(shape_key_list)
        
        elif self.input_method == "Legs":
            return self._leg_queue(shape_key_list)
        
        elif self.input_method == "Seams":
            return self._seam_queue(shape_key_list)
        
        else:
            return self._general_queue(shape_key_list)

    def _general_queue(self, shape_key_list: list[ShapeKey]) -> ShapeKeyQueue:
        shape_key_queue = []

        for source_key in shape_key_list:
            new_name      = source_key.name
            driver_source = source_key
            deform        = True

            
            if self.shapes_type == 'ALL':
                target_key = self.target.data.shape_keys.key_blocks.get(new_name)
                if not target_key:
                    target_key = self.target.shape_key_add(name=new_name, from_mix=False)

            elif self.shapes_type == 'EXISTING':
                target_key = self.target.data.shape_keys.key_blocks.get(new_name)

            else:
                if self.shape_target == "None":
                    target_key = self.target.shape_key_add(name=new_name, from_mix=False)
                else:
                    target_key = self.target.data.shape_keys.key_blocks.get(self.shape_target)

            if not target_key:
                continue

            if not self.deforms:
                deform = False
            
            temp_target = quick_copy(self.target)
            self.cleanup.append(temp_target)
            self.cleanup.append(temp_target.data)

            controller = quick_copy(self.source)
            self.cleanup.append(controller)
            self.cleanup.append(controller.data)

            controller_key = controller.data.shape_keys.key_blocks.get(source_key.name)
            
            shape_key_queue.append((temp_target, controller, target_key, controller_key, driver_source, deform))

        return shape_key_queue
    
    def _chest_queue(self, shape_key_list: list[ShapeKey]) -> ShapeKeyQueue:
        shape_key_queue = []
        shape_controller = self.devkit.yam_shapes

        for source_key in shape_key_list:
            driver_source = source_key
            lava_size     = source_key.name.endswith(("Teardrop", "Cupcake"))
            sub_key       = source_key.name.startswith("-") and not lava_size and self.sub_keys
            deform        = not sub_key

            key_name = "Lavatop" if source_key.name == "Lavabod" else source_key.name
            
            if not self.deform_target.get(source_key.name, False) and not sub_key:
                continue

            body_key  = shape_controller.data.shape_keys.key_blocks.get(key_name)

            if body_key:
                controller = quick_copy(shape_controller)
                self.cleanup.append(controller)
                self.cleanup.append(controller.data)

            elif not self.sub_keys:
                continue

            controller_key = controller.data.shape_keys.key_blocks.get(key_name)
            target_key = get_target_key(self.target, source_key.name)

            temp_target = quick_copy(self.target)
            self.cleanup.append(temp_target)
            self.cleanup.append(temp_target.data)

            shape_key_queue.append((temp_target, controller, target_key, controller_key, driver_source, deform))
            
        return shape_key_queue
    
    def _leg_queue(self, shape_key_list: list[ShapeKey]) -> ShapeKeyQueue:
        shape_key_queue = []
        shape_controller = self.devkit.yam_shapes

        for source_key in shape_key_list:
            new_name      = source_key.name
            driver_source = source_key
            deform        = True

            if source_key.name not in self.deform_target:
                continue
            if not self.deform_target[source_key.name]:
                continue
            
            if source_key.name == "Gen A/Watermelon Crushers":
                key_name = "LARGE"
            elif source_key.name == "Rue/Lava":
                key_name = "Rue/Lava Legs"
            else:
                key_name = source_key.name
            body_key = shape_controller.data.shape_keys.key_blocks.get(key_name)
            
            if body_key:
                controller = quick_copy(shape_controller)
                self.cleanup.append(controller)
                self.cleanup.append(controller.data)

                controller_key = controller.data.shape_keys.key_blocks.get(key_name)
            else:
                continue

            if source_key.name == "Soft Butt":
                new_name = "shpx_yam_softbutt"

            elif source_key.name == "Alt Hips":
                driver_source  = self.source.data.shape_keys.key_blocks.get("Hip Dips (for YAB)")
                controller_key = controller.data.shape_keys.key_blocks.get("Hip Dips (for YAB)")
                new_name = "shpx_yab_hip"

                shape_key_queue.extend(self._hip_keys(shape_controller, deform))
        
            target_key = get_target_key(self.target, new_name)

            temp_target = quick_copy(self.target)
            self.cleanup.append(temp_target)
            self.cleanup.append(temp_target.data)

            shape_key_queue.append((temp_target, controller, target_key, controller_key, driver_source, deform))
            
        return shape_key_queue

    def _hip_keys(self, shape_controller: Object, deform) -> ShapeKeyQueue:
        hip_keys = []
    
        if self.deform_target["Rue"] or self.target.data.shape_keys.key_blocks.get("Rue"):
            rue_hip_driver = self.source.data.shape_keys.key_blocks.get("Less Hip Dips (for Rue)")
            controller = quick_copy(shape_controller)
            self.cleanup.append(controller)
            self.cleanup.append(controller.data)

            controller_key = controller.data.shape_keys.key_blocks.get("Less Hip Dips (for Rue)")

            target_key  = get_target_key(self.target, "shpx_rue_hip")
            temp_target = quick_copy(self.target)
            self.cleanup.append(temp_target)
            self.cleanup.append(temp_target.data)

            hip_keys.append((temp_target, controller, target_key, controller_key, rue_hip_driver, deform))

        if self.deform_target["Soft Butt"] or self.target.data.shape_keys.key_blocks.get("shpx_softbutt"):
            target_key = get_target_key(self.target, "shpx_yab_c_hipsoft")
            controller = quick_copy(shape_controller)
            self.cleanup.append(controller)
            self.cleanup.append(controller.data)

            correction_key = controller.data.shape_keys.key_blocks.get("shpx_yab_c_hipsoft")
            correction_driver_source = self.source.data.shape_keys.key_blocks.get("shpx_yab_c_hipsoft")
            
            temp_target = quick_copy(self.target)
            self.cleanup.append(temp_target)
            self.cleanup.append(temp_target.data)

            hip_keys.append((temp_target, controller, target_key, correction_key, correction_driver_source, deform))

            if self.deform_target["Rue"] or self.target.data.shape_keys.key_blocks.get("Rue"):
                target_key = get_target_key(self.target, "shpx_rue_c_hipsoft")
                controller = quick_copy(shape_controller)
                self.cleanup.append(controller)
                self.cleanup.append(controller.data)
                correction_key = controller.data.shape_keys.key_blocks.get("shpx_rue_c_hipsoft")
                correction_driver_source = self.source.data.shape_keys.key_blocks.get("shpx_rue_c_hipsoft")

                temp_target = quick_copy(self.target)
                self.cleanup.append(temp_target)
                self.cleanup.append(temp_target.data)
                hip_keys.append((temp_target, controller, target_key, correction_key, correction_driver_source, deform))
    
        return hip_keys

    def _seam_queue(self, shape_key_list: list[ShapeKey]) -> ShapeKeyQueue:
        shape_key_queue = []

        for source_key in shape_key_list:
            # Model state is a list of keys that should be turned on before enabling the surface deform
            new_name      = source_key.name
            driver_source = source_key
            deform        = True

            if source_key.name[5:8] not in self.seams:
                if self.seam_values["wa_"] and source_key.name == "shpx_yam_c_softwaist":
                    pass
                else:
                    continue
            
            if not self.source.data.shape_keys.key_blocks.get(source_key.name):
                continue

            buff = self.target.data.shape_keys.key_blocks.get("Buff")

            target_key = get_target_key(self.target, new_name)

            temp_target = quick_copy(self.target)
            self.cleanup.append(temp_target)
            self.cleanup.append(temp_target.data)

            controller = quick_copy(self.source)
            self.cleanup.append(controller)
            self.cleanup.append(controller.data)

            controller_key = controller.data.shape_keys.key_blocks.get(source_key.name)

            shape_key_queue.append((temp_target, controller, target_key, controller_key, driver_source, deform))
            
        return shape_key_queue
    
    def add_modifier(self, temp_target: Object, controller: Object, target_key: ShapeKey, source_key: ShapeKey) -> None:

        def base_model_state() -> None:
            key_blocks   = controller.data.shape_keys.key_blocks
            chest_filter = {"LARGE", "MEDIUM", "SMALL", "MASC", "Lavabod"} 
            lava_keys    = {"Lavabod" , "-- Teardrop", "--- Cupcake"}
            leg_filter   = {"Gen A/Watermelon Crushers", "Skull Crushers", "Yanilla", "Mini", "Lavabod", "Masc"} 

            source_key.mute = False
            source_key.value = 1
            
            if self.input_method == "Chest" and target_key.name in chest_filter:
                key_name = "Lavatop" if self.chest_base == "Lavabod" else self.chest_base 
                key_blocks[key_name].mute = True

                if self.chest_base in ("Lavabod", "Teardrop", "Cupcake") and target_key.name not in lava_keys:
                    key_blocks["Lavatop"].mute = True

            elif self.input_method == "Legs" and target_key.name in leg_filter:
                key_name = "LARGE" if self.leg_base == "Gen A/Watermelon Crushers" else self.leg_base
                key_blocks[key_name].mute = True

        def controller_state(reset=False) -> None:
            key_blocks = controller.data.shape_keys.key_blocks
            for key in key_blocks:
                key.mute = True

            if "ShapeController" in controller.data.name and self.input_method == "Chest":
                key_name = "Lavatop" if self.chest_base == "Lavabod" else self.chest_base
                key_blocks[key_name].mute = False

                if self.chest_base in ("Lavabod", "Teardrop", "Cupcake"):
                    key_blocks["Lavatop"].mute = False

                if self.chest_base not in ("MEDIUM", "Teardrop"):
                    key_blocks["Medium/Push-Up"].mute = True

                if self.chest_base in ("SMALL", "Cupcake", "MASC"):
                    key_blocks["Push-Up"].value = 0
                    key_blocks["Squeeze"].value = 0

            if "ShapeController" in controller.data.name:
                if self.input_method == "Legs":
                    key_name = "LARGE" if self.leg_base == "Gen A/Watermelon Crushers" else self.leg_base
                    key_blocks[key_name].mute = False
                if self.input_method == "Seams":
                    key_blocks[self.seam_base].mute = False
            
            if not reset and self.input_method == "Chest":
                if "ShapeController" in controller.data.name and self.overhang:
                    key_blocks["Overhang"].mute = False

        controller_state()

        modifier: SurfaceDeformModifier = temp_target.modifiers.new(name="Deform", type='SURFACE_DEFORM')
        modifier.target = controller
        with bpy.context.temp_override(object=temp_target):
            bpy.ops.object.surfacedeform_bind(modifier=modifier.name)
        
        if not modifier.is_bound:
            raise SurfaceDeformBindError()
        
        if self.vertex_pin != "None":
            modifier.vertex_group = self.vertex_pin
            modifier.invert_vertex_group = True
        
        base_model_state()
        
        if self.smooth_level != "None":
            self._deform_corrections(temp_target, controller, self.smooth_level)

        # Second pass of shrinkwrap with less aggressive smooth corrective
        if self.shrinkwrap:
            self._deform_corrections(temp_target, controller, "Smooth")
        
    def _deform_corrections(self, target: Object, controller: Object, smooth:str) -> None:
        if smooth == "Aggressive":
            factor = 1.0
            iterations = 10
        else:
            factor = 0.5
            iterations = 5

        if self.shrinkwrap:
            shr_modifier: ShrinkwrapModifier     = target.modifiers.new(name="Shrinkwrap", type='SHRINKWRAP')
            shr_modifier.target                  = controller
            shr_modifier.wrap_mode               = 'OUTSIDE'
            shr_modifier.offset                  = 0.001
            shr_modifier.vertex_group            = self.shr_group

            if shr_modifier.vertex_group != "":
                shr_modifier.invert_vertex_group = True

        if smooth != "None":
            cor_modifier: CorrectiveSmoothModifier = target.modifiers.new(name="Corrective", type='CORRECTIVE_SMOOTH')
            cor_modifier.factor                    = factor
            cor_modifier.iterations                = iterations
            cor_modifier.use_pin_boundary          = True

            if self.vertex_pin != "None":
                cor_modifier.vertex_group          = self.vertex_pin
                cor_modifier.invert_vertex_group   = True
    
    def _add_driver(self, target_key: ShapeKey, driver_source: ShapeKey, source: Object) -> None:
        target_key.driver_remove("value")
        target_key.driver_remove("mute")
        value = target_key.driver_add("value").driver
        mute = target_key.driver_add("mute").driver

        if self.input_method == "Chest" and target_key.name == "LARGE" and self.chest_base != "LARGE":
            value.type = 'SCRIPTED'
            value.expression = "size == 0"
            value_var = value.variables.new()
            value_var.name = "size"
            value_var.type = 'SINGLE_PROP'
            
            value_var.targets[0].id_type = 'SCENE'
            value_var.targets[0].id = bpy.context.scene
            value_var.targets[0].data_path = "ya_devkit_props.torso_state.chest_size"

        elif self.input_method == "Legs" and target_key.name == "Gen A/Watermelon Crushers" and self.leg_base != "Melon":
            value.type = 'SCRIPTED'
            value.expression = "size == 0"
            value_var = value.variables.new()
            value_var.name = "size"
            value_var.type = 'SINGLE_PROP'

            value_var.targets[0].id_type = 'SCENE'
            value_var.targets[0].id = bpy.context.scene
            value_var.targets[0].data_path = "ya_devkit_props.leg_state.leg_size"

        else:
            value.type = 'AVERAGE'
            value_var = value.variables.new()
            value_var.name = "key_value"
            value_var.type = 'SINGLE_PROP'

            value_var.targets[0].id_type = 'KEY'
            value_var.targets[0].id = source.data.shape_keys
            value_var.targets[0].data_path = f'key_blocks["{driver_source.name}"].value'

        mute.type = 'AVERAGE'
        mute_var = mute.variables.new()
        mute_var.name = "key_mute"
        mute_var.type = 'SINGLE_PROP'
        
        mute_var.targets[0].id_type = 'KEY'
        mute_var.targets[0].id = source.data.shape_keys
        mute_var.targets[0].data_path = f'key_blocks["{driver_source.name}"].mute'

        
CLASSES = [
    ControllerVisibility,
    ShapeKeyTransfer
]