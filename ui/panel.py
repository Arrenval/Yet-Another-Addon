import re
import bpy
import platform

from pathlib                import Path
from bpy.types              import Panel, UILayout, Context, Object
from ..preferences          import get_prefs
from ..properties           import BlendModGroup, BlendModOption, CorrectionEntry, ModFileEntry, ModMetaEntry, get_file_properties, get_outfit_properties, get_object_from_mesh, visible_meshobj

class OutfitStudio(Panel):
    bl_idname = "VIEW3D_PT_YA_OutfitStudio"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "XIV Kit"
    bl_label = "Outfit Studio"
    bl_order = 1

    def draw(self, context:Context):
        self.outfit_props = get_outfit_properties()
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
        self.ui_category_buttons(colui, self.outfit_props, self.options)
        col = row.column()
        
        if self.outfit_props.overview_category:
            columns = ["OBJECT", "PART", "ATTR"]

            self.draw_overview(col, self.outfit_props, columns)
            
        if self.outfit_props.shapes_category:
            self.draw_shapes(col, self.outfit_props)
            
        if self.outfit_props.mesh_category:
            self.draw_mesh(col, self.outfit_props)

        if self.outfit_props.weights_category:
            self.draw_weights(col, self.outfit_props)

        if self.outfit_props.armature_category:
            self.draw_armature(col, self.outfit_props)

    def draw_overview(self, layout:UILayout, section_prop, columns):

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
                            text = section_prop.attr_dict[attr] if attr in section_prop.attr_dict else attr
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

    def draw_shapes(self, layout:UILayout, section_prop):
        if hasattr(bpy.context.scene, "devkit_props"):
            devkit_prop = bpy.context.scene.devkit_props
        box = layout.box()
        button_type = "shpk"
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Shapes", icon=self.options["Shapes"])

        col = box.column(align=True)
        split = col.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Method:")
        split.prop(section_prop, "shapes_method", text="", icon="OBJECT_DATA")
        col.separator(type="LINE", factor=2)

        if not hasattr(bpy.context.scene, "devkit_props") and section_prop.shapes_method != "Selected":
            row = col.row(align=True)
            row.alignment = "CENTER"
            row.label(text="Yet Another Devkit required.", icon="INFO")

        else:
            row = col.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="Smoothing:")
            split.prop(section_prop, "shapes_corrections", text="")
            if section_prop.shapes_method == "Legs" or section_prop.shapes_method == "Seams":
                split.prop(section_prop, "add_shrinkwrap", text="Shrinkwrap")
            
            if section_prop.shapes_method == "Selected":
                col.separator(type="SPACE", factor=1)
                
                row = col.row(align=True)
                split = row.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                split.label(text="Options:")
                split.prop(section_prop, "all_keys", text="All Keys")
                split.prop(section_prop, "add_shrinkwrap", text="Shrinkwrap")
                
                row = col.row(align=True)
                split = row.split(factor=0.25, align=True)
                split.label(text="")
                split.prop(section_prop, "existing_only", text="Existing")
                split.prop(section_prop, "include_deforms", text="Deforms")

                col.separator(type="LINE", factor=2)
            
                if section_prop.shapes_corrections != "None":
                    split = col.split(factor=0.25, align=True)
                    split.alignment = "RIGHT"
                    split.label(text="Pin:")
                    split.prop(section_prop, "obj_vertex_groups", text="", icon="GROUP_VERTEX")
                if section_prop.add_shrinkwrap:
                    split = col.split(factor=0.25, align=True)
                    split.alignment = "RIGHT"
                    split.label(text="Exclude:")
                    split.prop(section_prop, "exclude_vertex_groups", text="", icon="GROUP_VERTEX")

                if section_prop.add_shrinkwrap or section_prop.shapes_corrections != "None":
                    col.separator(type="LINE", factor=2)

                row = col.row(align=True)
                split = row.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                split.label(text="Source:")
                split.prop(section_prop, "shapes_source", text="")
                if not section_prop.all_keys and section_prop.include_deforms:
                    split.prop(section_prop, "shapes_source_enum", text="")

            elif section_prop.shapes_method == "Chest":
                col.separator(type="SPACE", factor=1)

                row = col.row(align=True)
                split = row.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                split.label(text="Options:")
                split.prop(section_prop, "sub_shape_keys", text="Sub Keys")
                split.prop(section_prop, "add_shrinkwrap", text="Shrinkwrap")

                row = col.row(align=True)
                split = row.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                split.label(text="")
                split.prop(section_prop, "adjust_overhang", text="Overhang")
                ctrl = bpy.data.objects["Chest"].visible_get(view_layer=bpy.context.view_layer)
                icon = "HIDE_ON" if not ctrl else "HIDE_OFF"
                adj_op = split.operator("yakit.apply_visibility", text="Source", icon=icon, depress=ctrl)
                adj_op.target = "Shape"
                adj_op.key = ""
                col.separator(type="LINE", factor=2)
            
                split = col.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                split.label(text="Base:")
                split.prop(section_prop, "shape_chest_base", text="", icon="SHAPEKEY_DATA")
                if section_prop.shapes_corrections != "None":
                    split = col.split(factor=0.25, align=True)
                    split.alignment = "RIGHT"
                    split.label(text="Pin:")
                    split.prop(section_prop, "obj_vertex_groups", text="", icon="GROUP_VERTEX")
                if section_prop.add_shrinkwrap:
                    split = col.split(factor=0.25, align=True)
                    split.alignment = "RIGHT"
                    split.label(text="Exclude:")
                    split.prop(section_prop, "exclude_vertex_groups", text="", icon="GROUP_VERTEX")

                col.separator(type="LINE", factor=2)

                slot = "Chest"
                labels = {
                        "Large":      "LARGE",    
                        "Medium":     "MEDIUM",    
                        "Small":      "SMALL", 
                        "Masc":       "MASC", 
                        "Buff":       "Buff",    
                        "Rue":        "Rue",        
                    }
                
                # del labels[section_prop.shape_chest_base]
                row = col.row(align=True)
                col.prop(devkit_prop, "key_pushup_large_ctrl", text="Push-Up Adjustment:")
                col.prop(devkit_prop, "key_squeeze_large_ctrl", text="Squeeze Adjustment:")

                self.dynamic_column_buttons(2, col, devkit_prop, labels, slot, button_type)
                
                col.separator(type="LINE", factor=2)

            if section_prop.shapes_method == "Legs":

                col.separator(type="LINE", factor=2)
            
                split = col.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                split.label(text="Base:")
                split.prop(section_prop, "shape_leg_base", text="", icon="SHAPEKEY_DATA")
                if section_prop.shapes_corrections != "None":
                    split = col.split(factor=0.25, align=True)
                    split.alignment = "RIGHT"
                    split.label(text="Pin:")
                    split.prop(section_prop, "obj_vertex_groups", text="", icon="GROUP_VERTEX")
                if section_prop.add_shrinkwrap:
                    split = col.split(factor=0.25, align=True)
                    split.alignment = "RIGHT"
                    split.label(text="Exclude:")
                    split.prop(section_prop, "exclude_vertex_groups", text="", icon="GROUP_VERTEX")

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
                
                # del labels[section_prop.shape_leg_base]
                self.dynamic_column_buttons(2, col, devkit_prop, labels, slot, button_type)

                col.separator(type="LINE", factor=2)

            if section_prop.shapes_method == "Seams":

                col.separator(type="LINE", factor=2)
                
                split = col.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                split.label(text="Base:")
                split.prop(section_prop, "shape_seam_base", text="", icon="SHAPEKEY_DATA")

                if section_prop.shapes_corrections != "None":
                    split = col.split(factor=0.25, align=True)
                    split.alignment = "RIGHT"
                    split.label(text="Pin:")
                    split.prop(section_prop, "obj_vertex_groups", text="", icon="GROUP_VERTEX")
                if section_prop.add_shrinkwrap:
                    split = col.split(factor=0.25, align=True)
                    split.alignment = "RIGHT"
                    split.label(text="Exclude:")
                    split.prop(section_prop, "exclude_vertex_groups", text="", icon="GROUP_VERTEX")

                if section_prop.add_shrinkwrap or section_prop.shapes_corrections != "None":
                    col.separator(type="LINE", factor=2)

                row = col.row(align=True)
                icon = 'CHECKMARK' if getattr(section_prop, "seam_waist") else 'PANEL_CLOSE'
                row.prop(section_prop, "seam_waist", text="Waist", icon=icon)
                icon = 'CHECKMARK' if getattr(section_prop, "seam_wrist") else 'PANEL_CLOSE'
                row.prop(section_prop, "seam_wrist", text="Wrist", icon=icon)
                icon = 'CHECKMARK' if getattr(section_prop, "seam_ankle") else 'PANEL_CLOSE'
                row.prop(section_prop, "seam_ankle", text="Ankle", icon=icon)

                col.separator(type="LINE", factor=2)

            row = col.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="Target:")
            split.prop(section_prop, "shapes_target", text="")
            if section_prop.shapes_method == "Selected" and not section_prop.all_keys and section_prop.include_deforms:
                split.prop(section_prop, "shapes_target_enum", text="")
            
            col.separator(type="LINE", factor=2)

            row = col.row()
            row.alignment = "CENTER"
            col = row.column(align=True)
            row = col.row(align=True)
            col.operator("ya.transfer_shape_keys", text="Transfer")
          
    def draw_mesh(self, layout:UILayout, section_prop):
        box = layout.box()
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Mesh", icon=self.options["Mesh"])
        
        row = box.row(align=True)
        button = section_prop.button_backfaces_expand
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row.prop(section_prop, "button_backfaces_expand", text="", icon=icon, emboss=False)
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
        button = section_prop.button_modifiers_expand
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row.prop(section_prop, "button_modifiers_expand", text="", icon=icon, emboss=False)
        row.label(text="Modifiers")
        
        obj = bpy.context.active_object
        if button and obj is not None:
            row = box.row(align=True)
            if obj.modifiers and obj.data.shape_keys:
                row = box.row(align=True)
                split = row.split(factor=0.75, align=True)
                split.prop(section_prop, "shape_modifiers")
                split.operator("ya.apply_modifier", text="Apply")
                icon = "PINNED" if section_prop.keep_modifier else "UNPINNED"
                row.prop(section_prop, "keep_modifier", text="", icon=icon)
                if section_prop.shape_modifiers == "None" or section_prop.shape_modifiers == "":
                    pass
                elif  obj.modifiers[section_prop.shape_modifiers].type == "DATA_TRANSFER":
                    row = box.row(align=True)
                    row.alignment = "CENTER"
                    row.label(text="Will be applied to mix of current shape keys.", icon="INFO")
                else:
                    row = box.row(align=True)
                    key = obj.data.shape_keys
                    row.template_list(
                        "MESH_UL_shape", 
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
            if obj.type == 'MESH' and section_prop.shape_modifiers == 'None':
                row = box.row(align=True)
                row.operator("wm.call_menu", text="Add Modifier", icon="ADD").name = "OBJECT_MT_modifier_add"
        elif button:
            row = box.row(align=True)
            row.alignment = "CENTER"
            row.label(text="No Object Selected.", icon="INFO")
        
        row = box.row(align=True)
        button = section_prop.button_transp_expand
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row.prop(section_prop, "button_transp_expand", text="", icon=icon, emboss=False)
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
            
    def draw_weights(self, layout:UILayout, section_prop):
        box = layout.box()
        row = box.row()
        row.alignment = "CENTER"
        row.label(text="Weights", icon=self.options["Weights"])

        obj = bpy.context.active_object
        row = box.row()
        col = row.column(align=True)
        if section_prop.filter_vgroups:
            col.template_list(
                "MESH_UL_yas", "", 
                get_outfit_properties(), "yas_vgroups", 
                get_outfit_properties(), "yas_vindex", 
                rows=5
                )
        else:
            if not obj:
                obj = get_object_from_mesh("Mannequin")
            col.template_list(
                "MESH_UL_yas", "", 
                obj, "vertex_groups", 
                obj.vertex_groups, "active_index", 
                rows=5
                )
        row = col.row(align=True)
        row.operator("ya.remove_select_vgroups", text= "Remove Selected").preset = "PANEL"
        row.operator("ya.remove_empty_vgroups", text= "Remove Empty")
        row.prop(section_prop, "filter_vgroups", text="", icon="FILTER")
                    
    def draw_armature(self, layout:UILayout, section_prop):
        box = layout.box()
        row = box.row()
        row.alignment = "CENTER"
        row.label(text="Armature", icon=self.options["Armature"])
        row = box.row()
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Armature:")
        split.prop(section_prop, "armatures", text="", icon="ARMATURE_DATA")
        box.separator(factor=0.5, type="LINE")
        if section_prop.armatures == "None":
            row = box.row()
            row.alignment = "CENTER"
            row.label(text="Please select an Armature.", icon="INFO")
        else:
            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="Scaling:" if section_prop.scaling_armature else "Pose:")
            split.label(text=self.outfit_props.pose_display_directory)
            buttonrow = split.row(align=True)
            op = buttonrow.operator("ya.pose_apply", text="Apply")
      
            buttonrow.prop(section_prop, "scaling_armature", text="", icon="FIXED_SIZE")
            op = buttonrow.operator("ya.pose_apply", text="", icon="FILE_REFRESH")
            op.reset = True

            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="" if section_prop.scaling_armature else "Scaling:")
            op = split.operator("ya.pose_apply", text="Import from Clipboard")
            op.use_clipboard = True

            box.separator(factor=0.5, type="LINE")
            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="Animation:")
            split.prop(section_prop, "actions", text="", icon="ACTION")

            
            if section_prop.armatures != "None" and section_prop.actions != "None":
                # box.separator(factor=0.5, type="LINE")
                row = box.row(align=True)
                col = row.column(align=True)
                row = col.row(align=True)
                row.alignment = "CENTER"
                row.label(text="Animation Frame:")
                col.prop(section_prop, "animation_frame", text="")
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
                     
    def dynamic_column_buttons(self, columns:int, layout:UILayout, section_prop, labels, slot, button_type):
        row = layout.row(align=True)
        columns_list = [row.column(align=True) for _ in range(columns)]

        for index, (name, key) in enumerate(labels.items()):
            key_lower = key.lower().replace(' ', "_")
            slot_lower = slot.lower()

            prop_name = f"{button_type}_{slot_lower}_{key_lower}"

            if hasattr(section_prop, prop_name):
                icon = 'CHECKMARK' if getattr(section_prop, prop_name) else 'PANEL_CLOSE'
                
                col_index = index % columns 
                emboss = False if (slot == "Legs" and name == self.outfit_props.shape_leg_base) or (slot == "Chest" and name == self.outfit_props.shape_chest_base) else True
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

class FileManager(Panel):
    bl_idname = "VIEW3D_PT_YA_FileManager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "XIV Kit"
    bl_label = "File Manager"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 3

    def draw(self, context:Context):
        self.prefs       = get_prefs()
        self.file_props  = get_file_properties()
        self.outfit_prop = get_outfit_properties()

        if hasattr(context.scene, "devkit_props"):
            self.devkit_props = context.scene.devkit_props
        layout = self.layout

        options ={
            "IMPORT": "IMPORT",
            "EXPORT": "EXPORT",
            "MODPACK": "NEWFOLDER",
            }

        box = layout.box()
        row = box.row(align=True)
        row.label(icon=options[self.file_props.file_man_ui])
        row.label(text=f"  {self.file_props.file_man_ui.capitalize()}")
        button_row = row.row(align=True)
        
        self.ui_category_buttons(button_row, self.file_props, options)

        # IMPORT
        button = self.file_props.file_man_ui
        if button == "IMPORT":
            self.draw_import(layout)

        # EXPORT
        if button == "EXPORT":
            self.draw_export(context, layout)

        if button == "MODPACK":
            self.draw_modpack(layout)

    def draw_export(self, context:Context, layout:UILayout):
        if self.file_props.export_total > 0:
            layout.separator(factor=0.5)

            total = self.file_props.export_total
            step = self.file_props.export_step
            total_time = self.file_props.export_time
            if step < 1:
                time_left = "Estimating duration..."
            else:
                average_time = total_time / step
                estimate = int((total - step) * average_time)

                if estimate < 60:
                    time_left = f"~{estimate} seconds"
                else:
                    minutes = estimate / 60
                    seconds = estimate % 60
                    time_left = f"~{int(minutes)} min {int(seconds)} seconds"

            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.progress(
                factor=self.file_props.export_progress, 
                text=f"Exporting: {step + 1}/{total}",
                type="RING")
            row.label(text=f"{time_left}")
            layout.separator(factor=0.5, type="LINE")
            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(text=f"{self.file_props.export_file_name}")

            layout.separator(factor=0.5)
        else:
            row = layout.row(align=True)
            row.prop(self.prefs, "export_display_dir", text="")
            row.operator("ya.dir_selector", icon="FILE_FOLDER", text="").category = "export"

            row = layout.row(align=True)
            col = row.column(align=True)
            col.operator("ya.simple_export", text="Simple Export")

            if hasattr(bpy.context.scene, "devkit_props"):
                col2 = row.column(align=True)
                col2.operator("ya.batch_queue", text="Batch Export")
            
            export_text = "GLTF" if self.file_props.file_gltf else " FBX "
            icon = "BLENDER" if self.file_props.file_gltf else "VIEW3D"
            col3 = row.column(align=True)
            col3.alignment = "RIGHT"
            col3.prop(self.file_props, "file_gltf", text=export_text, icon=icon, invert_checkbox=True)

        if hasattr(bpy.context.scene, "devkit_props"):
            box = layout.box()
            row = box.row(align=True)
            if self.file_props.export_body_slot == "Chest & Legs":
                row.label(text=f"Body Part: Chest")
            else:
                row.label(text=f"Body Part: {self.file_props.export_body_slot}")

            options =[
                ("Chest", "MOD_CLOTH"),
                ("Legs", "BONE_DATA"),
                ("Hands", "VIEW_PAN"),
                ("Feet", "VIEW_PERSPECTIVE"),
                ("Chest & Legs", "ARMATURE_DATA")
                ]
            
            self.body_category_buttons(row, self.file_props, options)
    
            
            # CHEST EXPORT  
        
            button_type = "export"
        
            if self.file_props.export_body_slot == "Chest" or self.file_props.export_body_slot == "Chest & Legs":

                category = "Chest"

                labels = {"YAB": ("YAB", []), "Rue": ("Rue", []), "Lava": ("Lava", []), "Flat": ("Masc", [])}
        
                self.dynamic_column_buttons(len(labels), layout, self.file_props, labels, category, button_type)

                yab = self.devkit_props.export_yab_chest_bool
                rue = self.devkit_props.export_rue_chest_bool and self.file_props.rue_export
                lava = self.devkit_props.export_lava_chest_bool
                masc = self.devkit_props.export_flat_chest_bool

                layout.separator(factor=0.5, type="LINE")

                labels = {"Buff": ("Buff", [yab, rue, lava, masc]), "Piercings": ("Piercings", [yab, rue, lava, masc])}
        
                self.dynamic_column_buttons(len(labels), layout, self.file_props, labels, category, button_type)

                layout.separator(factor=0.5, type="LINE")
                
                labels = {
                    "Large":      ("Large", [yab, rue, lava]),    
                    "Medium":     ("Medium", [yab, rue, lava]),   
                    "Small":      ("Small", [yab, rue, lava]),    
                    "Omoi":       ("Omoi", [yab, rue]),     
                    "Sayonara":   ("Sayonara", [yab, rue]), 
                    "Mini":       ("Mini", [yab, rue]),     
                    "Sugoi Omoi": ("Sugoi Omoi", [yab, rue]),
                    "Tsukareta":  ("Tsukareta", [yab, rue]),
                    "Tsukareta+": ("Tsukareta+", [yab, rue]),
                    "Uranus":     ("Uranus", [yab, rue]),
                    "Sugar":      ("Sugar", [lava]),
                    "Pecs":       ("Pecs", [masc]),
                }
        
                self.dynamic_column_buttons(3, layout, self.file_props, labels, category, button_type)
                
            # LEG EXPORT  
            
            if self.file_props.export_body_slot == "Legs" or self.file_props.export_body_slot == "Chest & Legs":
                
                category = "Legs"

                if self.file_props.export_body_slot == "Chest & Legs":
                    layout.separator(factor=1, type="LINE")
                    row = layout.row(align=True)
                    row.label(text=f"Body Part: Legs")

                labels = {"YAB": ("YAB", []), "Rue": ("Rue", []), "Lava": ("Lava", []), "Masc": ("Masc", [])}
        
                self.dynamic_column_buttons(len(labels), layout, self.file_props, labels, category, button_type)

                yab = self.devkit_props.export_yab_legs_bool
                rue = self.devkit_props.export_rue_legs_bool
                lava = self.devkit_props.export_lava_legs_bool
                masc = self.devkit_props.export_masc_legs_bool

                layout.separator(factor=0.5, type="LINE")

                labels = {
                    "Gen A":  ("Gen A", [yab, rue, lava, masc]),
                    "Gen B":  ("Gen B", [yab, rue, lava, masc]), 
                    "Gen C":  ("Gen C", [yab, rue, lava, masc]),
                    "Gen SFW":  ("Gen SFW", [yab, rue, lava, masc]),
                    "Melon": ("Melon", [yab, rue, lava, masc]),
                    "Skull": ("Skull", [yab, rue]),
                    "Yanilla":  ("Yanilla", [yab, rue]),  
                    "Mini": ("Mini", [yab, rue]),
                    
                }
                
                self.dynamic_column_buttons(4, layout, self.file_props, labels, category, button_type)

                layout.separator(factor=0.5, type="LINE")

                labels = {
                    "Small Butt":  ("Small", [yab, rue, lava, masc]),
                    "Pubes":  ("Pubes", [yab, rue, lava, masc])
                }
        
                self.dynamic_column_buttons(3, layout, self.file_props, labels, category, button_type) 

            # HAND EXPORT  
            
            if self.file_props.export_body_slot == "Hands":
                
                category = "Hands"
                labels = {
                    "YAB": ("YAB", []), 
                    "Rue": ("Rue", []),
                    "Lava": ("Lava", []),
                    }
        
                self.dynamic_column_buttons(3, layout, self.file_props, labels, category, button_type)
                
                yab = self.devkit_props.export_yab_hands_bool
                rue = self.devkit_props.export_rue_hands_bool
                lava = self.devkit_props.export_lava_hands_bool

                layout.separator(factor=0.5, type="LINE")

                labels = {
                    "Long": ("Long", [yab, rue, lava]), 
                    "Short": ("Short", [yab, rue, lava]),  
                    "Ballerina": ("Ballerina", [yab, rue, lava]), 
                    "Stabbies": ("Stabbies", [yab, rue, lava]), 
                    }

                self.dynamic_column_buttons(2, layout, self.file_props, labels, category, button_type)
                
                row = layout.row(align=True)
                row.label(text="Clawsies:")

                labels = { 
                    "Straight": ("Straight", [yab, rue, lava]),
                    "Curved": ("Curved", [yab, rue, lava]),
                    }

                self.dynamic_column_buttons(2, layout, self.file_props, labels, category, button_type)

                row = layout.row(align=True)

            # FEET EXPORT  
            
            if self.file_props.export_body_slot == "Feet":
                
                category = "Feet"
                labels = {
                    "YAB": ("YAB", []), 
                    "Rue": ("Rue", []), 
                    }
        
                self.dynamic_column_buttons(2, layout, self.file_props, labels, category, button_type)

                yab = self.devkit_props.export_yab_feet_bool
                rue = self.devkit_props.export_rue_feet_bool

                layout.separator(factor=0.5, type="LINE")

                labels = { 
                    "Clawsies": ("Clawsies", [yab, rue])
                    }

                self.dynamic_column_buttons(2, layout, self.file_props, labels, category, button_type)
        
            layout.separator(factor=0.5, type="LINE")

        box = layout.box()
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Advanced Options")

        layout.separator(factor=0.1) 

        row = layout.row(align=True)
        split = row.split(factor=0.33)
        col = split.column(align=True)
        col.alignment = "RIGHT"
        if hasattr(context.scene, "devkit_props"):
            col.label(text="Force YAS:")
            col.label(text="Body Names:")
            col.label(text="Rue Export:")
        col.label(text="Check Tris:")
        col.label(text="Shape Keys:")
        col.label(text="Backfaces:")
        if hasattr(context.scene, "devkit_props"):
            col.label(text="Subfolder:")
        
        col2 = split.column(align=True)
        col2.alignment = "RIGHT"
        if hasattr(context.scene, "devkit_props"):
            icon = 'CHECKMARK' if self.file_props.force_yas else 'PANEL_CLOSE'
            text = 'Enabled' if self.file_props.force_yas else 'Disabled'
            col2.prop(self.file_props, "force_yas", text=text, icon=icon)
            icon = 'CHECKMARK' if self.file_props.body_names else 'PANEL_CLOSE'
            text = 'Always' if self.file_props.body_names else 'Conditional'
            col2.prop(self.file_props, "body_names", text=text, icon=icon)
            icon = 'CHECKMARK' if self.file_props.rue_export else 'PANEL_CLOSE'
            text = 'Standalone' if self.file_props.rue_export else 'Variant'
            col2.prop(self.file_props, "rue_export", text=text, icon=icon)
        icon = 'CHECKMARK' if self.file_props.check_tris else 'PANEL_CLOSE'
        text = 'Enabled' if self.file_props.check_tris else 'Disabled'
        col2.prop(self.file_props, "check_tris", text=text, icon=icon)
        icon = 'CHECKMARK' if self.file_props.keep_shapekeys else 'PANEL_CLOSE'
        text = 'Keep' if self.file_props.keep_shapekeys else 'Remove'
        col2.prop(self.file_props, "keep_shapekeys", text=text, icon=icon)
        icon = 'CHECKMARK' if self.file_props.create_backfaces else 'PANEL_CLOSE'
        text = 'Create' if self.file_props.create_backfaces else 'Ignore'
        col2.prop(self.file_props, "create_backfaces", text=text, icon=icon)
        if hasattr(context.scene, "devkit_props"):
            icon = 'CHECKMARK' if self.file_props.create_subfolder else 'PANEL_CLOSE'
            text = 'Create' if self.file_props.create_subfolder else 'Ignore'
            col2.prop(self.file_props, "create_subfolder", text=text, icon=icon)

        layout.separator(factor=0.5)
    
    def draw_import(self, layout:UILayout):
        layout = self.layout
        row = layout.row(align=True)
        col = row.column(align=True)
        col.operator("ya.simple_import", text="Import")

        col2 = row.column(align=True)
        col2.operator("ya.simple_cleanup", text="Cleanup")
        
        export_text = "GLTF" if self.file_props.file_gltf else "FBX"
        icon = "BLENDER" if self.file_props.file_gltf else "VIEW3D"
        col3 = row.column(align=True)
        col3.alignment = "RIGHT"
        col3.prop(self.file_props, "file_gltf", text=export_text, icon=icon, invert_checkbox=True)

        box = layout.box()
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Cleanup Options") 

        layout.separator(factor=0.1)  

        row = layout.row(align=True)
        split = row.split(factor=0.33)
        col = split.column(align=True)
        col.alignment = "RIGHT"
        col.label(text="Armature:")
        col.label(text="Non-Mesh:")
        col.label(text="Update Material:")
        col.label(text="Reorder Mesh ID:")
        col.label(text="Rename:")
        
        col2 = split.column(align=True)
        col2.alignment = "RIGHT"
        icon = 'CHECKMARK' if self.file_props.remove_nonmesh else 'PANEL_CLOSE'
        col2.prop(self.file_props, "armatures", text="", icon="ARMATURE_DATA")
        text = 'Remove' if self.file_props.remove_nonmesh else 'Keep'
        col2.prop(self.file_props, "remove_nonmesh", text=text, icon=icon)
        icon = 'CHECKMARK' if self.file_props.update_material else 'PANEL_CLOSE'
        text = 'Enabled' if self.file_props.update_material else 'Disabled'
        col2.prop(self.file_props, "update_material", text=text, icon=icon)
        icon = 'CHECKMARK' if self.file_props.reorder_mesh_id else 'PANEL_CLOSE'
        text = 'Enabled' if self.file_props.reorder_mesh_id else 'Disabled'
        col2.prop(self.file_props, "reorder_mesh_id", text=text, icon=icon)
        col2.prop(self.file_props, "rename_import", text="")

        layout.separator(factor=0.5)

    def draw_modpack(self, layout:UILayout):
        if platform.system() == "Windows":
            row = layout.row(align=True)
            split = row.split(factor=0.25, align=True)
            icon = "CHECKMARK" if self.prefs.consoletools_status else "X"
            text = "ConsoleTools Ready!" if self.prefs.consoletools_status else "ConsoleTools missing."
            split.alignment = "RIGHT"
            split.label(text="")
            split.label(text=text, icon=icon)
            split.operator("ya.file_console_tools", text="Check")
            row.operator("ya.consoletools_dir", icon="FILE_FOLDER", text="")

            layout.separator(factor=0.5,type="LINE")
        
        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Output:")
        split.prop(self.prefs, "modpack_output_display_dir", text="")
        row.operator("ya.modpack_dir_selector", icon="FILE_FOLDER", text="").category = "OUTPUT_PMP" 

        box = layout.box()
        row = box.row(align=True)
        
        op_atr = {
            "category": "ALL",
            "group":    0,
            }
            
        self.operator_button(row, "ya.file_modpacker", icon="FILE_PARENT", attributes=op_atr)
        row.prop(self.file_props, "modpack_replace", text="New", icon="FILE_NEW", invert_checkbox=True)
        row.prop(self.file_props, "modpack_replace", text="Update", icon="CURRENT_FILE",)

        op_atr = {
            "category": "GROUP",
            "group":    0,
            "option":   0
            }
            
        self.operator_button(row, "ya.modpacker_ui_containers", icon="ADD", attributes=op_atr)
        self.operator_button(row, "ya.pmp_selector", icon="FILE")

        box.separator(factor=0.5,type="LINE")

        row = box.row(align=True)
        split = row.split(factor=0.25)
        col2 = split.column(align=True)
        col2.label(text="Ver.")
        col2.prop(self.file_props, "modpack_version", text="")

        col = split.column(align=True)
        col.label(text="Modpack:")
        col.prop(self.file_props, "modpack_display_dir", text="", emboss=True)

        split2 = row.split()
        col3 = split2.column(align=True)
        col3.alignment = "CENTER"
        col3.label(text="")
        col3.prop(self.file_props, "modpack_author", text="by", emboss=True)

        if self.file_props.modpack_replace and Path(self.file_props.modpack_dir).is_file():
            box.separator(factor=0.5,type="LINE")
            row = box.row(align=True)
            row.alignment = "CENTER"
            row.label(text=f"{Path(self.file_props.modpack_dir).name} is loaded.", icon="INFO")

        elif self.file_props.modpack_replace:
            box.separator(factor=0.5,type="LINE")
            row = box.row(align=True)
            row.alignment = "CENTER"
            row.label(text="No modpack is loaded.", icon="INFO")

        elif not self.file_props.modpack_replace and (Path(self.prefs.modpack_output_dir) / Path(self.file_props.modpack_display_dir + ".pmp")).is_file():
            box.separator(factor=0.5,type="LINE")
            row = box.row(align=True)
            row.alignment = "CENTER"
            row.label(text=f"{self.file_props.modpack_display_dir + '.pmp'} already exists!", icon="ERROR")
        else:
            box.separator(factor=0.1,type="SPACE")

        self.checked_folders = {}
        option_indent:float = 0.21
        for group_idx, group in enumerate(self.file_props.pmp_mod_groups):
            group: BlendModGroup
            box = layout.box()
            button = group.show_group

            self.group_header(box, group, group_idx)

            if not button:
                continue

            box.separator(factor=0.5,type="LINE")

            self.group_container(box, group, group_idx)

            if group.use_folder and group.group_type != "Combining":
                box.separator(factor=0.1,type="SPACE")
    
                row = layout.row(align=True)
                split = row.split(factor=option_indent)

                columns = [split.column() for _ in range(1, 3)]
                box = columns[1].box()
                self.folder_container(box, group, group_idx, 0)

                layout.separator(factor=0.1,type="SPACE")
                continue

            for option_idx, option in enumerate(group.mod_options):
                option: BlendModOption

                row = layout.row(align=True)
                split = row.split(factor=option_indent)

                columns = [split.column() for _ in range(1, 3)]
                                                         
                if group.group_type == "Combining" and option_idx == 8:
                    row = columns[1].row(align=True)
                    row.alignment = "CENTER"
                    row.label(icon="ERROR", text="Combining groups have a limit of 8 options.")
                    row = columns[1].row(align=True)
                    row.alignment = "CENTER"
                    row.label(icon="BLANK1", text="Options below will be discarded.")
                    columns[1].separator(factor=2,type="LINE")

                self.option_header(columns[1], group, option, group_idx, option_idx)

                if option.show_option:
                    row = self.right_align_prop(columns[1], "Description", "description", option)

                    columns[1].separator(factor=2,type="LINE")

                    row.label(icon="FILE_TEXT")
                    self.entry_container(columns[1], option, group_idx, option_idx)
            
            for correction_idx, correction in enumerate(group.corrections):
                correction: CorrectionEntry

                row = layout.row(align=True)
                split = row.split(factor=option_indent)

                columns = [split.column() for _ in range(1, 3)]

                self.correction_header(columns[1], group, correction, group_idx, correction_idx)

                if correction.show_option:
                    self.right_align_prop(columns[1], "Options", "names", correction)

                    columns[1].separator(factor=2,type="LINE")

                    self.entry_container(columns[1], correction, group_idx, correction_idx)

        # row = layout.row(align=True)
        # if platform.system() == "Windows":
            # row.operator("ya.file_converter", text="Convert")
           
    def group_header(self, layout:UILayout, group:BlendModGroup, group_idx:int):
        button = group.show_group

        row = layout.row(align=True)
        columns = [row.column() for _ in range(1, 4)]
        
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row = columns[0].row(align=True)
        row.alignment = "LEFT"
        row.prop(group, "show_group", text="", icon=icon, emboss=False)
        row.label(icon="BLANK1")
        row.label(icon="BLANK1")
    
        row = columns[1].row(align=True)
        row.alignment = "EXPAND"
        op_atr = {
            "category": "SINGLE",
            "group":    group_idx,
            }
            
        self.operator_button(row, "ya.file_modpacker", icon="FILE_PARENT", attributes=op_atr)
        row.prop(group, "name", text="", icon="GROUP")
        subrow = row.row(align=True)
        subrow.scale_x = 0.4
        subrow.prop(group, "priority", text="")
       
        row = columns[2].row(align=True)
        row.alignment = "RIGHT"
        row.label(icon="BLANK1")

        # if group.group_type == "Combining":
            # row.label(text="", icon="NEWFOLDER")
        # else:
        row.prop(group, "use_folder", text="", icon="NEWFOLDER", emboss=True)
        
        if group.use_folder and group.group_type != "Combining":
            row.label(icon="ADD", text="")
        else:
            op_atr = {
            "category": "OPTION",
            "group":    group_idx,
            "option":   0
            }
            
            self.operator_button(row, "ya.modpacker_ui_containers", icon="ADD", attributes=op_atr)

        op_atr = {
        "delete":   True,
        "category": "GROUP",
        "group":    group_idx,
        }
        
        self.operator_button(row, "ya.modpacker_ui_containers", icon="TRASH", attributes=op_atr)

    def group_container(self, layout:UILayout, group:BlendModGroup, idx:int):
            row = layout.row(align=True)
            split = row.split(factor=0.25)
            col = split.column()
            subrow = col.row(align=True)
            subrow.alignment = "RIGHT"
            subrow.label(text="Replace:")

            col2 = split.column()
            col2.prop(group, "idx")

            split2 = row.split(factor=1)
            col3 = split2.column()
            col3.alignment = "CENTER"
            col3.prop(group, "page", text="", emboss=True)

            row = layout.row(align=True)
            split = row.split(factor=0.25)
            col = split.column()
            subrow = col.row(align=True)
            subrow.alignment = "RIGHT"
            subrow.label(text="Description:")

            col2 = split.column()
            col2.prop(group, "description", text="")

            split2 = row.split(factor=1)
            col3 = split2.column(align=True)
            col3.alignment = "CENTER"
            col3.prop(group, "group_type", text="", emboss=True)

            if not group.use_folder:
                layout.separator(factor=0.1, type="SPACE")

    def option_header(self, layout:UILayout, group:BlendModGroup, option:BlendModOption, group_idx:int, option_idx:int):
        row = layout.box().row(align=True)
        columns = [row.column() for _ in range(1, 4)]

        button = option.show_option
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row = columns[0].row(align=True)
        row.alignment = "LEFT"
        row.prop(option, "show_option", text="", icon=icon, emboss=False)
        row.label(icon="BLANK1")
    
        row = columns[1].row(align=True)
        row.alignment = "EXPAND"
        row.row(align=True).prop(option, "name", text="", icon="OPTIONS")
        if group.group_type != "Combining":
            subrow = row.row(align=True)
            subrow.scale_x = 0.4
            subrow.prop(option, "priority", text="")

        row = columns[2].row(align=True)
        row.alignment = "RIGHT"
        row.label(icon="BLANK1")

        op_atr = {
            "category": "ENTRY",
            "group":    group_idx,
            "option":   option_idx
            }
            
        self.operator_button(row, "ya.modpacker_ui_containers", icon="ADD", attributes=op_atr)
        
        op_atr = {
            "delete":   True,
            "category": "OPTION",
            "group":    group_idx,
            "option":   option_idx
            }
            
        self.operator_button(row, "ya.modpacker_ui_containers", icon="TRASH", attributes=op_atr)
    
    def correction_header(self, layout:UILayout, group:BlendModGroup, option:CorrectionEntry, group_idx:int, option_idx:int):
        row = layout.box().row(align=True)
        columns = [row.column() for _ in range(1, 4)]

        button = option.show_option
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row = columns[0].row(align=True)
        row.alignment = "LEFT"
        row.prop(option, "show_option", text="", icon=icon, emboss=False)
        row.label(icon="BLANK1")
    
        row = columns[1].row(align=True)
        row.alignment = "EXPAND"
        row.row(align=True).label(text=f"Correction #{option_idx + 1}", icon="LINK_BLEND")

        row = columns[2].row(align=True)
        row.alignment = "RIGHT"
        row.label(icon="BLANK1")

        op_atr = {
            "category": "COMBI_ENTRY",
            "group":    group_idx,
            "option":   option_idx
            }
            
        self.operator_button(row, "ya.modpacker_ui_containers", icon="ADD", attributes=op_atr)
        
        op_atr = {
            "delete":   True,
            "category": "COMBI",
            "group":    group_idx,
            "option":   option_idx
            }
            
        self.operator_button(row, "ya.modpacker_ui_containers", icon="TRASH", attributes=op_atr)

    def folder_container(self, layout:UILayout, container:BlendModGroup, group_idx:int, option_idx:int):
        layout.separator(factor=0.1,type="SPACE")

        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Folder:")

        # This is stupid
        path = str(Path(*Path(container.folder_path).parts[-3:])) if Path(container.folder_path).is_dir else container.folder_path
        split.alignment = "LEFT"
        split.label(text=f"{path}")

        op_atr = {
            "category": "GROUP",
            "group": group_idx,
            }

        self.operator_button(row, "ya.modpack_dir_selector", icon="FILE_FOLDER", attributes=op_atr)

        if len(container.get_subfolder()) > 1:
            row = layout.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="")
            split.prop(container, "subfolder", text="Subfolder")
            row.label(icon="FOLDER_REDIRECT")

        if container.use_folder:
            row = self.right_align_prop(layout, "XIV Path", "game_path", container)
            icon = "CHECKMARK" if container.valid_path else "X"
            row.label(icon=icon)
            self.xiv_path_category(layout, container, "GROUP", group_idx, option_idx)
        
            if container.get_folder_stats(model_check=True):
                self.get_file_stats(layout, container)
        
        layout.separator(factor=0.1,type="SPACE")

    def entry_container(self, layout:UILayout, container:BlendModOption | CorrectionEntry, group_idx:int, option_idx:int):
         
        for file_idx, file in enumerate(container.file_entries):
            file: ModFileEntry

            row = layout.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="File:")
            split.alignment = "LEFT"
            split.label(text=f"{Path(file.file_path).name}")

            op_atr = {
                "category": "FILE_ENTRY",
                "group": group_idx,
                "option": option_idx,
                "entry": file_idx,
            }
    
            self.operator_button(row, "ya.modpack_file_selector", icon="FILE_FOLDER", attributes=op_atr)
            
            row = self.right_align_prop(layout, "XIV Path", "game_path", file)
            icon = "CHECKMARK" if file.valid_path else "X"
            row.label(icon=icon)
            self.xiv_path_category(layout, file, "FILE_ENTRY", group_idx, option_idx, file_idx)

            layout.separator(factor=1.5,type="LINE")

        for entry_idx, entry in enumerate(container.meta_entries):
            entry: ModMetaEntry

            match entry.type:
                case "ATR":
                    category = "ATR_ENTRY" if isinstance(container, BlendModOption) else "ATR_COMBI"
                    icon = "MESH_CONE"

                case "SHP":
                    category = "SHP_ENTRY" if isinstance(container, BlendModOption) else "SHP_COMBI"
                    icon = "SHAPEKEY_DATA"

            row = layout.row(align=True)
            row.alignment = "EXPAND"
            row.label(text="", icon=icon)

            subrow = row.row(align=True)
            subrow.scale_x = 0.6
            subrow.prop(entry, "slot", text="")

            subrow = row.row(align=True)
            subrow.scale_x = 0.8
            subrow.prop(entry, "manip_ref", text="")

            subrow = row.row(align=True)
            subrow.scale_x = 0.6
            subrow.prop(entry, "model_id", text="")

            if entry.type == "SHP":
                subrow = row.row(align=True)
                subrow.scale_x = 0.6
                subrow.prop(entry, "connector_condition", text="")

            subrow = row.row(align=True)
            subrow.scale_x = 0.6
            subrow.prop(entry, "race_condition", text="")

            row.prop(entry, "enable", text="", icon= "CHECKMARK" if entry.enable else "X")
            
            op_atr = {
                "delete":   True,
                "category": category,
                "group":    group_idx,
                "option":   option_idx,
                "entry":    entry_idx,
            }
    
            self.operator_button(row, "ya.modpacker_ui_containers", icon="TRASH", attributes=op_atr)

            layout.separator(factor=1.5,type="LINE")
    
    def get_file_stats(self, layout:UILayout, container:BlendModGroup | BlendModOption):

        layout.separator(factor=2,type="LINE")

        button = container.show_folder
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row = layout.row(align=True)
        row.alignment = "LEFT"
        row.prop(container, "show_folder", text="Model Stats", icon=icon, emboss=False)

        if button:
            layout.separator(factor=0.5,type="LINE")
            
            row = layout.row(align=True)
            row.label(icon="BLANK1")
            split = row.split(factor=0.4)
            split.label(text="Name:")
            split.label(text="MDL:")
            split.label(text="FBX:")

            folder = container.final_folder()
            if folder not in self.checked_folders:
                folder_stats = container.get_folder_stats()
            else: 
                folder_stats = self.checked_folders[folder]

            for file_name, file_type in folder_stats.items():
                file_name:str
                file_type:dict[str, bool]

                row = layout.row(align=True)
                row.label(icon="BLANK1")
                split = row.split(factor=0.4)
                split.label(text=file_name)
                split.label(text="  X" if not file_type["mdl"] or file_type["mdl"] < file_type["fbx"] else "  ✓")
                split.label(text="  X" if not file_type["fbx"] or file_type["mdl"] > file_type["fbx"] else "  ✓")
            
            layout.separator(factor=2,type="LINE")
            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(text="Checkmarks indicate the most recent file.", icon="INFO")

    def dynamic_column_buttons(self, columns, box:UILayout, section_prop, labels, category, button_type):
        if category == "Chest":
            yab = self.devkit_props.export_yab_chest_bool
            rue = self.devkit_props.export_rue_chest_bool and section_prop.rue_export
            lava = self.devkit_props.export_lava_chest_bool

        row = box.row(align=True)

        columns_list = [row.column(align=True) for _ in range(columns)]

        for index, (size, (name, bodies)) in enumerate(labels.items()):
            size_lower = size.lower().replace(' ', "_")
            category_lower = category.lower()
            emboss = True if not bodies or any(body is True for body in bodies) else False

            prop_name = f"{button_type}_{size_lower}_{category_lower}_bool"

            if hasattr(self.devkit_props, prop_name):
                icon = 'CHECKMARK' if getattr(self.devkit_props, prop_name) and emboss else 'PANEL_CLOSE'
                
                col_index = index % columns

                if category == "Chest" and lava and (not yab and not rue):
                    match name:
                        case "Large":
                            name = "Omoi"
                        case "Medium":
                            name = "Teardrop"
                        case "Small":
                            name = "Cupcake"
                        case "Omoi":
                            name = "---"

                columns_list[col_index].prop(self.devkit_props, prop_name, text=name, icon=icon, emboss=emboss)
            else:
                col_index = index % columns 
        
                columns_list[col_index].label(text=name, icon="PANEL_CLOSE")
        return box  

    def dropdown_header(self, layout:UILayout, button, section_prop, prop_str=str, label=str, alignment="LEFT", extra_icon=""):
        row = layout.row(align=True)
        split = row.split(factor=1)
        box = split.box()
        sub = box.row(align=True)
        sub.alignment = alignment

        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        sub.prop(section_prop, prop_str, text="", icon=icon, emboss=False)
        if isinstance(section_prop, BlendModOption):
            sub.prop(section_prop, "name", text="")
        else:
            sub.label(text=label)
        if extra_icon != "":
            sub.label(icon=extra_icon)
        
        return box

    def right_align_prop(self, layout:UILayout, label:str, prop:str, obj, factor:float=0.25) -> UILayout:
        """Get simple, customisable, right aligned prop with label on a new row. Returns the row if you want to append extra items.
        Args:
            label: Row name.
            prop: Prop referenced.
            container: Object that contains the necessary props.
            factor: Split row ratio.
           """
        
        row = layout.row(align=True)
        split = row.split(factor=factor, align=True)
        split.alignment = "RIGHT"
        split.label(text=f"{label}:")
        split.prop(obj, prop, text="")
        
        return row

    def operator_button(self, layout:UILayout, operator:str, icon:str, text:str="", attributes:dict={}):
        """Operator as a simple button."""

        op = layout.operator(operator, icon=icon, text=text)
        for attribute, value in attributes.items():
            setattr(op, attribute, value)
    
    def xiv_path_category(self, layout:UILayout, container:BlendModOption | ModFileEntry, category:str, group_idx:int, option_idx:int=0, entry_idx:int=0, factor:float=0.25):
        if container.valid_path and container.game_path.endswith(".mdl"):
            body_slots = {
                "Chest": "top",
                "Hands": "glv",
                "Legs":  "dwn",
                "Feet":  "sho"
            }
        
            row = layout.row(align=True)
            split = row.split(factor=factor, align=True)
            split.alignment = "RIGHT"
            split.label(text="")
            for key, value in body_slots.items():
                op = split.operator("ya.gamepath_category", text=key, depress=True if value == container.check_gamepath_category() else False)
                setattr(op, "body_slot", value)
                setattr(op, "group", group_idx)
                setattr(op, "option", option_idx)
                setattr(op, "entry", entry_idx)
                setattr(op, "category", category)
        
    def body_category_buttons(self, layout:UILayout, section_prop, options):
        row = layout

        for slot, icon in options:
            depress = True if section_prop.export_body_slot == slot else False
            row.operator("ya.set_body_part", text="", icon=icon, depress=depress).body_part = slot

    def ui_category_buttons(self, layout:UILayout, section_prop, options):
            row = layout
            ui_selector = getattr(section_prop, "file_man_ui")

            for slot, icon in options.items():
                depress = True if ui_selector == slot else False
                operator = row.operator("ya.set_ui", text="", icon=icon, depress=depress)
                operator.menu = slot


CLASSES = [
    OutfitStudio,
    FileManager
]   