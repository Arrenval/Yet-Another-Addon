import re
import bpy
   
from bpy.types        import Panel, UILayout, Context, Object

from ..draw           import aligned_row, get_conditional_icon, operator_button
from ...properties    import get_outfit_properties, get_devkit_properties, get_window_properties, get_devkit_win_props
from ...preferences   import get_prefs
from ...utils.objects import visible_meshobj, get_object_from_mesh


class OutfitStudio(Panel):
    bl_idname = "VIEW3D_PT_YA_OutfitStudio"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "XIV Kit"
    bl_label = "Outfit Studio"
    bl_order = 1

    def draw(self, context:Context):
        self.outfit_props = get_outfit_properties()
        self.window_props = get_window_properties()
        self.devkit_props = get_devkit_properties()
        self.devkit_win   = get_devkit_win_props()
        layout = self.layout

        self.options ={
            "Overview": "INFO",
            "Shapes": "SHAPEKEY_DATA",
            "Mesh": "OUTLINER_OB_MESH",
            "Weights": "WPAINT_HLT",
            "Armature": "ARMATURE_DATA"
            }

        row = layout.row()
        colui = row.column()
        self.ui_category_buttons(colui, self.window_props, self.options)
        col = row.column()
        
        if self.window_props.overview_category:
            columns = ["OBJECT", "PART", "ATTR"]

            self.draw_overview(col, columns)
            
        if self.window_props.shapes_category:
            self.draw_shapes(col)
            
        if self.window_props.mesh_category:
            self.draw_mesh(col)

        if self.window_props.weights_category:
            self.draw_weights(col)

        if self.window_props.armature_category:
            self.draw_armature(col)

    def draw_overview(self, layout:UILayout, columns):

        def get_entries(visible:list[Object]) -> dict[int, dict[Object, dict[str, tuple[str | int, int | None]]]]:
            data_entries = {}
            for obj in visible:
                obj_props = []
                name_parts = obj.name.split(" ")
                if re.search(r"^\d+.\d+\s", obj.name):
                    id_index = 0
                    name = name_parts[1:]
                elif re.search(r"\s\d+.\d+$", obj.name):
                    id_index = -1
                    name = name_parts[:-1]
                else:
                    continue
                try:
                    group = int(name_parts[id_index].split(".")[0])
                    part  = int(name_parts[id_index].split(".")[1])
                    if name_parts[-2] == "Part":
                        name_parts.pop()
                except:
                    continue

                material  = obj.data.materials[0].name[1:-5] if obj.data.materials[0].name.endswith(".mtrl") else obj.data.materials[0].name
                triangles = len(obj.data.loop_triangle_polygons)

                for key, value in obj.items():
                    if key.startswith("atr") and value:
                        obj_props.append(key)
                data_entries.setdefault(group, {})
                data_entries[group][obj] = ({"name": ((" ".join(name)), None), 
                                            "part": (part, 1), 
                                            "props": (obj_props, 2), 
                                            "material": (material, None), 
                                            "triangles": (triangles, None)})
    
            return data_entries
        
        visible            = visible_meshobj()
        data_entries       = get_entries(visible)
        triangles:     int = 0
        selected_tris: int = 0
        if len(bpy.context.selected_objects) > 0:
            selected_tris = sum([len(obj.data.loop_triangle_polygons) for obj in bpy.context.selected_objects if obj.type == "MESH"])
        row = layout.box().row(align=False).split(factor=0.3)
        row_list = [row for _ in range(len(columns))]
        
        for index, text in enumerate(columns):
            header = row_list[index].row(align=True)
            header.alignment = "CENTER"
            header.label(text=text if text == "OBJECT" else text)

        layout.separator(type="SPACE", factor=0.2)

        for group, obj_data in sorted(data_entries.items(), key=lambda item: item[0]):
            obj_data = sorted(obj_data.items(), key=lambda item: item[1]["part"][0])
            
            box = layout.box().row().split(factor=0.3)
            col = box.column().row()
            col.alignment = "CENTER"
            col.label(text=f"Mesh #{group}:")
            col2 = box.column()
            matr_text = obj_data[0][1]["material"][0]
            matr_obj  = obj_data[0][0]
            op = col2.operator("ya.overview_material", text=str(matr_text), emboss=True)
            op.obj = matr_obj.name
            
            col_box = layout.box().split(factor=0.3)
            columns_list = [col_box.column(align=True) for _ in range(len(columns))]
            for obj, values in obj_data:
                col = columns_list[0]
                col.alignment = "CENTER"
                op = col.operator("ya.overview_group", text=values["name"][0], emboss=False)
                op.type = "GROUP"
                op.obj = obj.name
            
                for key, (value, column) in values.items():
                    if column is None:
                        continue
                    col = columns_list[column].row(align=True)
                    col.alignment = "CENTER"
                    if key == "props":
                        if len(values["props"][0]) > 0:
                            col.alignment = "EXPAND"
                        else:
                            col.alignment = "RIGHT"
                        for attr in value:
                            text = self.outfit_props.attr_dict[attr] if attr in self.outfit_props.attr_dict else attr
                            op = col.operator("ya.attributes", text=f"{text}")
                            op.attr = attr
                            op.obj = obj.name
                        op = col.operator("ya.attributes", icon="ADD", text="")
                        op.attr = "NEW"
                        op.obj = obj.name

                    elif key == "part":
                        col.alignment = "EXPAND"
                        col.scale_x = 1.5
                        conflict = False
                        for con_obj, con_values in obj_data:
                            if con_obj == obj:
                                continue
                            if con_values["part"] == values["part"]:
                                conflict = True
                                break
                        op = col.operator("ya.overview_group", 
                                            text="", 
                                            emboss=False, 
                                            icon= "TRIA_LEFT")
                        op.type = "DEC_PART"
                        op.obj = obj.name

                        op = col.operator("ya.overview_group", 
                                            text=str(value), 
                                            emboss=False, 
                                            icon= "ERROR" if conflict else "NONE")
                        op.type = "PART"
                        op.obj = obj.name

                        op = col.operator("ya.overview_group", 
                                            text="", 
                                            emboss=False, 
                                            icon= "TRIA_RIGHT")
                        op.type = "INC_PART"
                        op.obj = obj.name
            
                triangles += values["triangles"][0]

        count = f"{triangles:,}" if len(bpy.context.selected_objects) == 0 else f"{selected_tris:,} / {triangles:,}"
        row = layout.box()
        row.alignment = "RIGHT"
        row.label(text=f"Triangles: {count}    ")

    def draw_shapes(self, layout:UILayout):
        box = layout.box()
        button_type = "shpk"
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Shapes", icon=self.options["Shapes"])

        col = box.column(align=True)
        aligned_row(col, "Method:", "shapes_method", self.window_props, "", attr_icon='OBJECT_DATA')
        col.separator(type="LINE", factor=2)

        if not self.devkit_props and self.window_props.shapes_method != "Selected":
            row = col.row(align=True)
            row.alignment = "CENTER"
            row.label(text="Yet Another Devkit required.", icon="INFO")

        else:

            row = aligned_row(col, "Smoothing:", "shapes_corrections", self.window_props, "")
            row.separator()
            row.prop(self.window_props, "add_shrinkwrap", text="Shrinkwrap")

            if self.window_props.shapes_corrections != "None" or self.window_props.add_shrinkwrap:
                col.separator()

            if self.window_props.shapes_corrections != "None":
                aligned_row(col, "Pin:", "obj_vertex_groups", self.window_props, "", attr_icon='GROUP_VERTEX')

            if self.window_props.add_shrinkwrap:
                aligned_row(col, "Exclude:", "exclude_vertex_groups", self.window_props, "", attr_icon='GROUP_VERTEX')

            if self.window_props.shapes_method == "Selected":
                col.separator(type="LINE", factor=2)

                row = aligned_row(col, "Options:", "shapes_type", self.window_props, "")
                row.separator()
                row.prop(self.window_props, "include_deforms", text="Deforms")

            if self.window_props.shapes_method == "Chest":
                col.separator(type="LINE", factor=2)
                
                row = aligned_row(col, "Options:", "sub_shape_keys", self.window_props, "Sub Keys")
                row.separator()
                row.prop(self.window_props, "adjust_overhang", text="Overhang")

                col.separator(type="LINE", factor=2)

                chest_obj = self.devkit_props.yam_chest_controller
                if chest_obj is None:
                    row = col.row(align=True)
                    row.alignment = "CENTER"
                    row.label(text="Couldn't find controller mesh.", icon="ERROR")
                    row = col.row(align=True)
                    row.alignment = "CENTER"
                    row.label(text="Please see your devkit settings menu.", icon='BLANK1')
                    return

                visible = chest_obj.visible_get()
                row = aligned_row(col, "Base:", "shape_chest_base", self.outfit_props, "", attr_icon='SHAPEKEY_DATA')
                row.operator("ya.chest_controller",
                              text="", 
                              icon="HIDE_OFF" if visible  else "HIDE_ON", 
                              depress=visible)
            
            if self.window_props.shapes_method == "Legs":
                col.separator(type="LINE", factor=2)

                aligned_row(col, "Base:", "shape_leg_base", self.window_props, "", attr_icon='SHAPEKEY_DATA')
            
            if self.window_props.shapes_method == "Chest":
                col.separator(type="LINE", factor=2)

                
                

                keys = chest_obj.data.shape_keys.key_blocks
                slot = "Chest"
                labels = {
                        "Large":      "LARGE",    
                        "Medium":     "MEDIUM",    
                        "Small":      "SMALL", 
                        "Omoi":       "Lavabod", 
                        "Teardrop":   "Teardrop", 
                        "Cupcake":    "Cupcake",
                        "Masc":       "MASC",  
                        "Buff":       "Buff",    
                        "Rue":        "Rue",        
                    }
                
                row = col.row(align=True)
                col.prop(keys["Push-Up"], "value", text="Push-Up Adjustment:")
                col.prop(keys["Squeeze"], "value", text="Squeeze Adjustment:")

                self.dynamic_column_buttons(3, col, self.devkit_win, labels, slot, button_type)

            if self.window_props.shapes_method == "Legs":

                col.separator(type="LINE", factor=2)

                slot = "Legs"
                labels = {    
                        "Melon":      "Gen A/Watermelon Crushers",                   
                        "Skull":      "Skull Crushers",                   
                        "Yanilla":    "Yanilla",                 
                        "Mini":       "Mini",                 
                        "Lavabod":    "Lavabod",                 
                        "Masc":       "Masc",                 
                        "Rue":        "Rue",           
                        "Alt Hips":   "Alt Hips",
                        "Small Butt": "Small Butt",         
                        "Soft Butt":  "Soft Butt",
                    }
                
                self.dynamic_column_buttons(2, col, self.devkit_win, labels, slot, button_type)

            if self.window_props.shapes_method == "Seams":

                col.separator(type="LINE", factor=2)

                row = col.row(align=True)
                icon = get_conditional_icon(self.window_props.seam_waist)
                row.prop(self.window_props, "seam_waist", text="Waist", icon=icon)
                icon = get_conditional_icon(self.window_props.seam_waist)
                row.prop(self.window_props, "seam_wrist", text="Wrist", icon=icon)
                icon = get_conditional_icon(self.window_props.seam_ankle)
                row.prop(self.window_props, "seam_ankle", text="Ankle", icon=icon)

            col.separator(type="LINE", factor=2)

            if self.window_props.shapes_method == "Selected":
                row = aligned_row(col, "Source:", "shapes_source", self.outfit_props, "")
                if self.window_props.shapes_method == "Selected" and self.window_props.shapes_type == 'SINGLE' and self.window_props.include_deforms:
                    row.prop(self.window_props, "shapes_source_enum", text="")

            row = col.row(align=True)
            row = aligned_row(col, "Target:", "shapes_target", self.outfit_props, "")
            if self.window_props.shapes_method == "Selected" and self.window_props.shapes_type == 'SINGLE' and self.window_props.include_deforms:
                row.prop(self.window_props, "shapes_target_enum", text="")
            
            col.separator(type="LINE", factor=2)

            row = col.row()
            row.alignment = "CENTER"
            col = row.column(align=True)
            row = col.row(align=True)
            col.operator("ya.transfer_shape_keys", text="Transfer")
          
    def draw_mesh(self, layout:UILayout):
        box = layout.box()
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Mesh", icon=self.options["Mesh"])
        
        row = box.row(align=True)
        button = self.window_props.button_backfaces_expand
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row.prop(self.window_props, "button_backfaces_expand", text="", icon=icon, emboss=False)
        row.label(text="Backfaces")
        
        if button:
            col = box.column(align=True)
            sub = col.row(align=True)
            sub.scale_x = 4
            sub.operator("ya.tag_backfaces", text="", icon="ADD").preset = 'ADD'
            sub.scale_x = 1
            sub.operator("ya.create_backfaces", text=f"CREATE")
            sub.scale_x = 4
            sub.operator("ya.tag_backfaces", text="", icon="REMOVE").preset = 'REMOVE'
            sub.scale_x = 1
            
        row = box.row(align=True)
        button = self.window_props.button_modifiers_expand
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row.prop(self.window_props, "button_modifiers_expand", text="", icon=icon, emboss=False)
        row.label(text="Modifiers")
        
        obj = bpy.context.active_object
        if button and obj is not None:
            row = box.row(align=True)
            if obj.modifiers and obj.data.shape_keys:
                row = box.row(align=True)
                split = row.split(factor=0.75, align=True)
                split.prop(self.window_props, "shape_modifiers")
                split.operator("ya.apply_modifier", text="Apply")
                icon = "PINNED" if self.window_props.keep_modifier else "UNPINNED"
                row.prop(self.window_props, "keep_modifier", text="", icon=icon)
                if self.window_props.shape_modifiers == "None" or self.window_props.shape_modifiers == "":
                    pass
                elif  obj.modifiers[self.window_props.shape_modifiers].type == "DATA_TRANSFER":
                    row = box.row(align=True)
                    row.alignment = "CENTER"
                    row.label(text="Will be applied to mix of current shape keys.", icon="INFO")
                else:
                    row = box.row(align=True)
                    key = obj.data.shape_keys
                    row.template_list(
                        "MESH_UL_YA_SHAPE", 
                        "", 
                        key, 
                        "key_blocks", 
                        obj, 
                        "active_shape_key_index", 
                        rows=5)

            elif not obj.modifiers:
                row.alignment = "CENTER"
                row.label(text="Object has no modifiers.", icon="INFO")
            elif not obj.data.shape_keys:
                row.alignment = "CENTER"
                row.label(text="Object has no shape keys.", icon="INFO")
            if obj.type == 'MESH' and self.window_props.shape_modifiers == 'None':
                row = box.row(align=True)
                row.operator("wm.call_menu", text="Add Modifier", icon="ADD").name = "OBJECT_MT_modifier_add"
        elif button:
            row = box.row(align=True)
            row.alignment = "CENTER"
            row.label(text="No object selected.", icon="INFO")
        
        row = box.row(align=True)
        button = self.window_props.button_transp_expand
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row.prop(self.window_props, "button_transp_expand", text="", icon=icon, emboss=False)
        row.label(text="Transparency")
        if button:
            obj = bpy.context.active_object
            if obj is not None:
                icon = 'CHECKBOX_HLT' if "xiv_transparency" in obj and obj["xiv_transparency"] == True else 'CHECKBOX_DEHLT'
                row = box.row(align=True)
                row.label(text="Transparent Mesh", icon=icon)
                text = "Tag" if "xiv_transparency" not in obj else 'Toggle'
                row.operator("ya.transparency", text=text).render = "TAG"
                row = box.row(align=True)
                if obj.active_material:
                    material = obj.active_material
                    row.operator("ya.transparency", text="BLENDED", depress=material.surface_render_method == 'BLENDED').render = 'BLENDED'
                    row.operator("ya.transparency", text="DITHERED", depress=material.surface_render_method == 'DITHERED').render = 'DITHERED'
                # row.operator("ya.tris", text="Apply")
            else:
                row = box.row(align=True)
                row.alignment = "CENTER"
                row.label(text="No Object Selected.", icon="INFO")
            
    def draw_weights(self, layout:UILayout):
        box = layout.box()
        row = box.row()
        row.alignment = "CENTER"
        row.label(text="Weights", icon=self.options["Weights"])

        obj = bpy.context.active_object
        row = box.row()
        col = row.column(align=True)
        if not obj:
            row = box.row(align=True)
            row.alignment = "CENTER"
            row.label(text="No active object.", icon="INFO")
            return
        
        if self.window_props.filter_vgroups:
            col.template_list(
                "MESH_UL_YAS", "", 
                self.outfit_props, "yas_ui_vgroups", 
                self.outfit_props, "yas_vindex", 
                rows=5
                )
        else:
            col.template_list(
                "MESH_UL_YAS", "", 
                obj, "vertex_groups", 
                obj.vertex_groups, "active_index", 
                rows=5
                )
            
        row = col.row(align=True)
        row.operator("ya.remove_select_vgroups", text= "Remove Selected").preset = "PANEL"
        row.operator("ya.remove_empty_vgroups", text= "Remove Empty")
        row.prop(self.window_props, "filter_vgroups", text="", icon="FILTER")

        row = box.row(align=True)
        button = self.window_props.button_yas_man_expand
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row.prop(self.window_props, "button_yas_man_expand", text="", icon=icon, emboss=False)
        row.label(text="YAS Manager")

        if button:
            group_bool = {
                "ALL": obj.yas.all_groups,
                "GEN": obj.yas.genitalia or obj.yas.all_groups,
                "PHYS": obj.yas.physics or obj.yas.all_groups
            }
            row = box.row(align=True)
            split = row.split(factor=0.33, align=True)
            split.prop(self.window_props, 'yas_storage', text="")

            icon, text = self.yas_status()
            split.label(text=text, icon=icon)
            if not group_bool[self.window_props.yas_storage]:
                op = row.operator("ya.yas_manager", text="", icon='FILE_TICK')
                op.mode = self.window_props.yas_storage
                op.target = 'ACTIVE'
            if obj.yas.v_groups:
                op = row.operator("ya.yas_manager", text="", icon='FILE_PARENT')
                op.mode = 'RESTORE'
                op.target = 'ACTIVE'         

    def yas_status(self) -> tuple[str, str]:
        no_weights  = "No stored weights."
        gen_weights = "Genitalia weights stored."
        all_weights = "All weights stored."
        phy_weights = "Physics weights stored."
        com_weights = "Physics, gentialia, weights stored."
        vertices    = "Vertex count changed."
        missing_obj = "Check your devkit settings."

        obj = bpy.context.active_object

        if not obj:
            icon = 'ERROR'
            text = missing_obj
        
        elif not obj.yas.v_groups:
            icon = 'X'
            text = no_weights
        
        elif obj.yas.old_count != len(obj.data.vertices):
            icon = 'ERROR'
            text = vertices

        else:
            icon = 'CHECKMARK'
            if obj.yas.all_groups:
                text = all_weights
            elif obj.yas.genitalia and obj.yas.physics:
                text = com_weights
            elif obj.yas.genitalia:
                text = gen_weights
            elif obj.yas.physics:
                text = phy_weights
            else:
                text = "Undefined weights stored."
    
        return icon, text
           
    def draw_armature(self, layout:UILayout):
        box = layout.box()
        row = box.row()
        row.alignment = "CENTER"
        row.label(text="Armature", icon=self.options["Armature"])
        row = box.row()
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Armature:")
        split.prop(self.outfit_props, "outfit_armature", text="", icon="ARMATURE_DATA")
        box.separator(factor=0.5, type="LINE")
        if not self.outfit_props.outfit_armature:
            row = box.row()
            row.alignment = "CENTER"
            row.label(text="Please select an Armature.", icon="INFO")
        else:
            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="Scaling:" if self.window_props.scaling_armature else "Pose:")
            split.label(text=self.outfit_props.pose_display_directory)
            buttonrow = split.row(align=True)
            op = buttonrow.operator("ya.pose_apply", text="Apply")
      
            buttonrow.prop(self.window_props, "scaling_armature", text="", icon="FIXED_SIZE")
            op = buttonrow.operator("ya.pose_apply", text="", icon="FILE_REFRESH")
            op.reset = True

            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="" if self.window_props.scaling_armature else "Scaling:")
            op = split.operator("ya.pose_apply", text="Import from Clipboard")
            op.use_clipboard = True

            box.separator(factor=0.5, type="LINE")
            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="Animation:")
            split.prop(self.outfit_props, "actions", text="", icon="ACTION")

            if self.outfit_props.outfit_armature and self.outfit_props.actions != "None":
                # box.separator(factor=0.5, type="LINE")
                row = box.row(align=True)
                col = row.column(align=True)
                row = col.row(align=True)
                row.alignment = "CENTER"
                row.label(text="Animation Frame:")
                col.prop(self.window_props, "animation_frame", text="")
                row = box.row(align=True)
                row.alignment = "CENTER"
                row.operator("ya.frame_jump", text="", icon="FRAME_PREV").end = False
                row.operator("ya.keyframe_jump", text="", icon="PREV_KEYFRAME").next = False
                if bpy.context.screen.is_animation_playing:
                    row.scale_x = 2
                    row.operator("screen.animation_play", text="", icon="PAUSE")
                    row.scale_x = 1
                else:
                    row.operator("screen.animation_play", text="", icon="PLAY_REVERSE").reverse = True
                    row.operator("screen.animation_play", text="", icon="PLAY")
                row.operator("ya.keyframe_jump", text="", icon="NEXT_KEYFRAME").next = True
                row.operator("ya.frame_jump", text="", icon="FRAME_NEXT").end = True
                     
    def dynamic_column_buttons(self, columns:int, layout:UILayout, section_prop, labels: dict[str, str], slot, button_type):
        row = layout.row(align=True)
        columns_list = [row.column(align=True) for _ in range(columns)]

        for index, (name, key) in enumerate(labels.items()):
            key_lower = key.lower().replace(' ', "_")
            slot_lower = slot.lower()

            prop_name = f"{button_type}_{slot_lower}_{key_lower}"

            if hasattr(section_prop, prop_name):
                icon = get_conditional_icon(getattr(section_prop, prop_name))
                
                col_index = index % columns 
                emboss = False if (slot == "Legs" and name == self.window_props.shape_leg_base) or (slot == "Chest" and key == self.outfit_props.shape_chest_base) else True
                columns_list[col_index].prop(section_prop, prop_name, text=name, icon=icon if emboss else "SHAPEKEY_DATA", emboss=emboss)
            else:
                # print(f"{name} has no assigned property!")
                pass
        return layout  

    def ui_category_buttons(self, layout:UILayout, section_prop, options):
        row = layout

        for index, (slot, icon) in enumerate(options.items()):
            button = getattr(section_prop, f"{slot.lower()}_category")
            if index == 0:
                row.separator(factor=0.5)
            depress = True if button else False
            operator = row.operator("ya.outfit_category", text="", icon=icon, depress=depress, emboss=True if depress else False)
            operator.menu = slot.upper()
            row.separator(factor=2)


CLASSES = [
    OutfitStudio,
]   
