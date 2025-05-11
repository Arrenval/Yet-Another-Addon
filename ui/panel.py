import os
import re
import bpy
import platform

from pathlib       import Path
from bpy.props     import StringProperty, BoolProperty
from ..util.props  import get_object_from_mesh, visible_meshobj
from bpy.types     import Panel, Operator, UIList, UILayout, Context, VertexGroup, Object

class MESH_UL_yas(UIList):
    bl_idname = "MESH_UL_yas"

    def draw_item(self, context:Context, layout:UILayout, data, item:VertexGroup, icon, active_data, active_propname):
        ob = data
        vgroup = item
        icon = self.get_icon_value("GROUP_VERTEX")
        try:
            category = bpy.context.scene.outfit_props.YAS_BONES[vgroup.name]
        except:
            category = "Unknown"
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if len(context.scene.yas_vgroups) == 1 and "has no " in vgroup.name:
                error = self.get_icon_value("INFO")
                layout.prop(vgroup, "name", text="", emboss=False, icon_value=error)
                layout.alignment = "CENTER"
            else:
                layout.prop(vgroup, "name", text=category, emboss=False, icon_value=icon)
                icon = 'LOCKED' if vgroup.lock_weight else 'UNLOCKED'
                layout.prop(vgroup, "lock_weight", text="", icon=icon, emboss=False)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)
    
    def get_icon_value(self, icon_name: str) -> int:
        icon_items = UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.items()
        icon_dict = {tup[1].identifier : tup[1].value for tup in icon_items}

        return icon_dict[icon_name]

class MESH_UL_shape(UIList):
    bl_idname = "MESH_UL_shape"

    def draw_item(self, context, layout:UILayout, data, item:VertexGroup, icon, active_data, active_propname):
        ob = data
        shape = item
        sizes = ["LARGE", "MEDIUM", "SMALL"]
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if shape.name.isupper() and not any(shape.name == size for size in sizes):
                layout.prop(shape, "name", text="", emboss=False, icon_value=self.get_icon_value("REMOVE"))
            else:
                layout.prop(shape, "name", text="", emboss=False, icon_value=icon)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)
    
    def get_icon_value(self, icon_name: str) -> int:
        icon_items = UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.items()
        icon_dict = {tup[1].identifier : tup[1].value for tup in icon_items}

        return icon_dict[icon_name]

class FrameJump(Operator):
    bl_idname = "ya.frame_jump"
    bl_label = "Jump to Endpoint"
    bl_description = "Jump to first/last frame in frame range"
    bl_options = {'REGISTER'}

    end: BoolProperty() # type: ignore
 
    def execute(self, context):
        bpy.ops.screen.frame_jump(end=self.end)
        context.scene.outfit_props.animation_frame = context.scene.frame_current

        return {'FINISHED'}

class KeyframeJump(Operator):
    bl_idname = "ya.keyframe_jump"
    bl_label = "Jump to Keyframe"
    bl_description = "Jump to previous/next keyframe"
    bl_options = {'REGISTER'}

    next: BoolProperty() # type: ignore

    def execute(self, context):
        bpy.ops.screen.keyframe_jump(next=self.next)
        context.scene.outfit_props.animation_frame = context.scene.frame_current

        return {'FINISHED'}
    
class DirSelector(Operator):
    bl_idname = "ya.dir_selector"
    bl_label = "Select Folder"
    bl_description = "Select file or directory. Hold Alt to open the folder"
    
    directory: StringProperty() # type: ignore
    category: StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: bpy.props.StringProperty(
        subtype="DIR_PATH",
        options={'HIDDEN'}) # type: ignore
    
    

    def invoke(self, context, event):
        actual_dir = getattr(context.scene.file_props, f"{self.category}_directory", "")     

        if event.alt and event.type == "LEFTMOUSE" and os.path.isdir(actual_dir):
            os.startfile(actual_dir)
        elif event.type == "LEFTMOUSE":
            context.window_manager.fileselect_add(self)
        else:
             self.report({"ERROR"}, "Not a directory!")
    
        return {"RUNNING_MODAL"}

    def execute(self, context):
        actual_dir_prop = f"{self.category}_directory"
        display_dir_prop = f"{self.category}_display_directory"
        selected_file = Path(self.directory)  

        if selected_file.is_dir():
            setattr(context.scene.file_props, actual_dir_prop, str(selected_file))
            setattr(context.scene.file_props, display_dir_prop, str(Path(*selected_file.parts[-3:])))
            self.report({"INFO"}, f"Directory selected: {selected_file}")
        
        else:
            self.report({"ERROR"}, "Not a valid path!")
        
        return {'FINISHED'}
    
class BodyPartSlot(Operator):
    bl_idname = "ya.set_body_part"
    bl_label = "Select body slot to export."
    bl_description = "The icons almost make sense"

    body_part: StringProperty() # type: ignore

    def execute(self, context):
        context.scene.file_props.export_body_slot = self.body_part
        return {'FINISHED'}
    
class PanelCategory(Operator):
    bl_idname = "ya.set_ui"
    bl_label = "Select the menu."
    bl_description = "Changes the panel menu"

    menu: StringProperty() # type: ignore

    def execute(self, context):
        context.scene.file_props.file_man_ui = self.menu
        return {'FINISHED'}

class OutfitCategory(Operator):
    bl_idname = "ya.outfit_category"
    bl_label = "Select menus."
    bl_description = """Changes the panel menu.
    *Click to select single category.
    *Shift+Click to pin/unpin categories"""

    menu: StringProperty() # type: ignore
    panel: StringProperty() # type: ignore

    def invoke(self, context, event):
        props = context.scene.outfit_props
        categories = ["overview", "shapes", "mesh", "weights", "armature"]
        if event.shift:
            state = getattr(props, f"{self.menu.lower()}_category")
            if state:
                setattr(props, f"{self.menu.lower()}_category", False)
            else:
                setattr(props, f"{self.menu.lower()}_category", True)
        else:
            for category in categories:
                if self.menu.lower() == category:
                    setattr(props, f"{category.lower()}_category", True)
                else:
                    setattr(props, f"{category.lower()}_category", False)

        return {'FINISHED'}

class OutfitStudio(Panel):
    bl_idname = "VIEW3D_PT_YA_OutfitStudio"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "Outfit Studio"
    bl_order = 1

    def draw(self, context:Context):
        section_prop = context.scene.outfit_props
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
        self.ui_category_buttons(colui, section_prop, self.options)
        col = row.column()
        
        if section_prop.overview_category:
            columns = ["OBJECT", "PART", "ATTR"]

            self.draw_overview(col, section_prop, columns)
            
        if section_prop.shapes_category:
            self.draw_shapes(col, section_prop)
            
        if section_prop.mesh_category:
            self.draw_mesh(col, section_prop)

        if section_prop.weights_category:
            self.draw_weights(col, section_prop)

        if section_prop.armature_category:
            self.draw_armature(col, section_prop)

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
                        conflict = False
                        for con_obj, con_values in obj_data:
                            if con_obj == obj:
                                continue
                            if con_values["part"] == values["part"]:
                                conflict = True
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
        split.label(text="Source:")
        split.prop(section_prop, "shape_key_source", text="", icon="OBJECT_DATA")
        col.separator(type="LINE", factor=2)

        if not hasattr(bpy.context.scene, "devkit_props") and section_prop.shape_key_source != "Selected":
            row = col.row(align=True)
            row.alignment = "CENTER"
            row.label(text="Yet Another Devkit required.", icon="INFO")

        else:
            if section_prop.shape_key_source == "Chest":
                row = col.row(align=True)
                row.alignment = "CENTER"
                row.prop(section_prop, "sub_shape_keys", text="Sub Keys")
                row.prop(section_prop, "add_shrinkwrap", text="Shrinkwrap")
                row.prop(section_prop, "adjust_overhang", text="Overhang")
                col2 = row.column(align=True)
                ctrl = bpy.data.objects["Chest"].visible_get(view_layer=bpy.context.view_layer)
                icon = "HIDE_ON" if not ctrl else "HIDE_OFF"
                adj_op = col2.operator("yakit.apply_visibility", text="", icon=icon, depress=ctrl)
                adj_op.target = "Shape"
                adj_op.key = ""
                col.separator(type="LINE", factor=2)
            
                split = col.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                split.label(text="Base:")
                split.prop(section_prop, "shape_key_base", text="", icon="SHAPEKEY_DATA")
                split = col.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                split.label(text="Pin:")
                split.prop(section_prop, "obj_vertex_groups", text="", icon="GROUP_VERTEX")
                split = col.split(factor=0.25, align=True)
                if section_prop.add_shrinkwrap:
                    split.alignment = "RIGHT"
                    split.label(text="Exclude:")
                    split.prop(section_prop, "exclude_vertex_groups", text="", icon="GROUP_VERTEX")
                col.separator(type="LINE", factor=2)

                slot = "Chest"
                labels = {
                        "Large":      "LARGE",    
                        "Medium":     "MEDIUM",    
                        "Small":      "SMALL", 
                        "Buff":       "Buff",    
                        "Rue":        "Rue",        
                    }
                
                del labels[section_prop.shape_key_base]
                row = col.row(align=True)
                col.prop(devkit_prop, "key_pushup_large_ctrl", text="Push-Up Adjustment:")
                col.prop(devkit_prop, "key_squeeze_large_ctrl", text="Squeeze Adjustment:")

                self.dynamic_column_buttons(2, col, devkit_prop, labels, slot, button_type)
                
                col.separator(type="LINE", factor=2)

            if section_prop.shape_key_source == "Legs":

                slot = "Legs"
                labels = {    
                        "Skull":      "Skull Crushers",                   
                        "Mini":       "Mini",                 
                        "Lava":       "Lavabod",                 
                        "Masc":       "Masc",                 
                        "Rue":        "Rue",           
                        "Alt Hips":   "Alt Hips",
                        "Small Butt": "Small Butt",         
                        "Soft Butt":  "Soft Butt",
                    }
                
                self.dynamic_column_buttons(2, col, devkit_prop, labels, slot, button_type)
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
            if obj != None:
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
                bpy.context.scene, "yas_vgroups", 
                bpy.context.scene, "yas_vindex", 
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
        row.operator("ya.remove_select_vgroups", text= "Remove Selected").preset = ""
        row.operator("ya.remove_empty_vgroups", text= "Remove Empty").preset = ""
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
            split.label(text=bpy.context.scene.outfit_props.pose_display_directory)
            buttonrow = split.row(align=True)
            buttonrow.operator("ya.pose_apply", text="Apply")
            buttonrow.prop(section_prop, "scaling_armature", text="", icon="FIXED_SIZE")
            buttonrow.operator("ya.pose_apply", text="", icon="FILE_REFRESH").reset = True

            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="" if section_prop.scaling_armature else "Scaling:")
            split.operator("ya.pose_apply", text="Import from Clipboard").use_clipboard = True

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
                     
    def dynamic_column_buttons(self, columns, layout:UILayout, section_prop, labels, slot, button_type):
        row = layout.row(align=True)

        columns_list = [row.column(align=True) for _ in range(columns)]

        for index, (name, key) in enumerate(labels.items()):
            key_lower = key.lower().replace(' ', "_")
            slot_lower = slot.lower()

            prop_name = f"{button_type}_{slot_lower}_{key_lower}"

            if hasattr(section_prop, prop_name):
                icon = 'CHECKMARK' if getattr(section_prop, prop_name) else 'PANEL_CLOSE'
                
                col_index = index % columns 
                
                columns_list[col_index].prop(section_prop, prop_name, text=name, icon=icon)
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
    bl_category = "Devkit"
    bl_label = "File Manager"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 3

    def draw(self, context:Context):
        section_prop = context.scene.file_props
        self.outfit_prop  = context.scene.outfit_props
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
        row.label(icon=options[section_prop.file_man_ui])
        row.label(text=f"  {section_prop.file_man_ui.capitalize()}")
        button_row = row.row(align=True)
        
        self.ui_category_buttons(button_row, section_prop, options)

        # IMPORT
        button = section_prop.file_man_ui
        # box = self.dropdown_header(button, section_prop, "button_import_expand", "Import", "IMPORT")
        if button == "IMPORT":
            self.draw_import(layout, section_prop)

        # EXPORT
        # box = self.dropdown_header(button, section_prop, "button_export_expand", "Export", "EXPORT")
        if button == "EXPORT":
            self.draw_export(context, layout, section_prop)

        if button == "MODPACK":
                section_prop = context.scene.file_props
                self.draw_modpack(layout, section_prop)

    def draw_export(self, context:Context, layout:UILayout, section_prop):
        if section_prop.export_total > 0:
            layout.separator(factor=0.5)

            total = section_prop.export_total
            step = section_prop.export_step
            total_time = section_prop.export_time
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
                factor=section_prop.export_progress, 
                text=f"Exporting: {step + 1}/{total}",
                type="RING")
            row.label(text=f"{time_left}")
            layout.separator(factor=0.5, type="LINE")
            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(text=f"{section_prop.export_file_name}")

            layout.separator(factor=0.5)
        else:
            row = layout.row(align=True)
            row.prop(section_prop, "export_display_directory", text="")
            row.operator("ya.dir_selector", icon="FILE_FOLDER", text="").category = "export"

            row = layout.row(align=True)
            col = row.column(align=True)
            col.operator("ya.simple_export", text="Simple Export")

            if hasattr(bpy.context.scene, "devkit_props"):
                col2 = row.column(align=True)
                col2.operator("ya.batch_queue", text="Batch Export")
            
            export_text = "GLTF" if section_prop.file_gltf else " FBX "
            icon = "BLENDER" if section_prop.file_gltf else "VIEW3D"
            col3 = row.column(align=True)
            col3.alignment = "RIGHT"
            col3.prop(section_prop, "file_gltf", text=export_text, icon=icon, invert_checkbox=True)

        if hasattr(bpy.context.scene, "devkit_props"):
            box = layout.box()
            row = box.row(align=True)
            if section_prop.export_body_slot == "Chest & Legs":
                row.label(text=f"Body Part: Chest")
            else:
                row.label(text=f"Body Part: {section_prop.export_body_slot}")

            options =[
                ("Chest", "MOD_CLOTH"),
                ("Legs", "BONE_DATA"),
                ("Hands", "VIEW_PAN"),
                ("Feet", "VIEW_PERSPECTIVE"),
                ("Chest & Legs", "ARMATURE_DATA")
                ]
            
            self.body_category_buttons(row, section_prop, options)
    
            
            # CHEST EXPORT  
        
            button_type = "export"
        
            if section_prop.export_body_slot == "Chest" or section_prop.export_body_slot == "Chest & Legs":

                category = "Chest"

                labels = {"YAB": ("YAB", []), "Rue": ("Rue", []), "Lava": ("Lava", []), "Flat": ("Masc", [])}
        
                self.dynamic_column_buttons(len(labels), layout, section_prop, labels, category, button_type)

                yab = self.devkit_props.export_yab_chest_bool
                rue = self.devkit_props.export_rue_chest_bool and section_prop.rue_export
                lava = self.devkit_props.export_lava_chest_bool
                masc = self.devkit_props.export_flat_chest_bool

                layout.separator(factor=0.5, type="LINE")

                labels = {"Buff": ("Buff", [yab, rue, lava, masc]), "Piercings": ("Piercings", [yab, rue, lava, masc])}
        
                self.dynamic_column_buttons(len(labels), layout, section_prop, labels, category, button_type)

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
        
                self.dynamic_column_buttons(3, layout, section_prop, labels, category, button_type)
                
            # LEG EXPORT  
            
            if section_prop.export_body_slot == "Legs" or section_prop.export_body_slot == "Chest & Legs":
                
                category = "Legs"

                if section_prop.export_body_slot == "Chest & Legs":
                    layout.separator(factor=1, type="LINE")
                    row = layout.row(align=True)
                    row.label(text=f"Body Part: Legs")

                labels = {"YAB": ("YAB", []), "Rue": ("Rue", []), "Lava": ("Lava", []), "Masc": ("Masc", [])}
        
                self.dynamic_column_buttons(len(labels), layout, section_prop, labels, category, button_type)

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
                    "Mini": ("Mini", [yab, rue]),
                    "Pubes":  ("Pubes", [yab, rue, lava, masc])
                }
                
                self.dynamic_column_buttons(4, layout, section_prop, labels, category, button_type)

                layout.separator(factor=0.5, type="LINE")

                labels = {
                    "Small Butt": ("Small Butt", [yab, rue, lava, masc]),
                    "Soft Butt": ("Soft Butt", [yab, rue, lava, masc]), 
                    "Hip Dips":  ("Hip Dips", [yab, rue]),
                }
        
                self.dynamic_column_buttons(3, layout, section_prop, labels, category, button_type) 

            # HAND EXPORT  
            
            if section_prop.export_body_slot == "Hands":
                
                category = "Hands"
                labels = {
                    "YAB": ("YAB", []), 
                    "Rue": ("Rue", []),
                    "Lava": ("Lava", []),
                    }
        
                self.dynamic_column_buttons(3, layout, section_prop, labels, category, button_type)
                
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

                self.dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)
                
                row = layout.row(align=True)
                row.label(text="Clawsies:")

                labels = { 
                    "Straight": ("Straight", [yab, rue, lava]),
                    "Curved": ("Curved", [yab, rue, lava]),
                    }

                self.dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)

                row = layout.row(align=True)

            # FEET EXPORT  
            
            if section_prop.export_body_slot == "Feet":
                
                category = "Feet"
                labels = {
                    "YAB": ("YAB", []), 
                    "Rue": ("Rue", []), 
                    }
        
                self.dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)

                yab = self.devkit_props.export_yab_feet_bool
                rue = self.devkit_props.export_rue_feet_bool

                layout.separator(factor=0.5, type="LINE")

                labels = { 
                    "Clawsies": ("Clawsies", [yab, rue])
                    }

                self.dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)
        
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
            icon = 'CHECKMARK' if section_prop.force_yas else 'PANEL_CLOSE'
            text = 'Enabled' if section_prop.force_yas else 'Disabled'
            col2.prop(section_prop, "force_yas", text=text, icon=icon)
            icon = 'CHECKMARK' if section_prop.body_names else 'PANEL_CLOSE'
            text = 'Always' if section_prop.body_names else 'Conditional'
            col2.prop(section_prop, "body_names", text=text, icon=icon)
            icon = 'CHECKMARK' if section_prop.rue_export else 'PANEL_CLOSE'
            text = 'Standalone' if section_prop.rue_export else 'Variant'
            col2.prop(section_prop, "rue_export", text=text, icon=icon)
        icon = 'CHECKMARK' if section_prop.check_tris else 'PANEL_CLOSE'
        text = 'Enabled' if section_prop.check_tris else 'Disabled'
        col2.prop(section_prop, "check_tris", text=text, icon=icon)
        icon = 'CHECKMARK' if section_prop.keep_shapekeys else 'PANEL_CLOSE'
        text = 'Keep' if section_prop.keep_shapekeys else 'Remove'
        col2.prop(section_prop, "keep_shapekeys", text=text, icon=icon)
        icon = 'CHECKMARK' if section_prop.create_backfaces else 'PANEL_CLOSE'
        text = 'Create' if section_prop.create_backfaces else 'Ignore'
        col2.prop(section_prop, "create_backfaces", text=text, icon=icon)
        if hasattr(context.scene, "devkit_props"):
            icon = 'CHECKMARK' if section_prop.create_subfolder else 'PANEL_CLOSE'
            text = 'Create' if section_prop.create_subfolder else 'Ignore'
            col2.prop(section_prop, "create_subfolder", text=text, icon=icon)

        layout.separator(factor=0.5)
    
    def draw_import(self, layout:UILayout, section_prop):
        layout = self.layout
        row = layout.row(align=True)
        col = row.column(align=True)
        col.operator("ya.simple_import", text="Import")

        col2 = row.column(align=True)
        col2.operator("ya.simple_cleanup", text="Cleanup")
        
        export_text = "GLTF" if section_prop.file_gltf else "FBX"
        icon = "BLENDER" if section_prop.file_gltf else "VIEW3D"
        col3 = row.column(align=True)
        col3.alignment = "RIGHT"
        col3.prop(section_prop, "file_gltf", text=export_text, icon=icon, invert_checkbox=True)

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
        icon = 'CHECKMARK' if section_prop.remove_nonmesh else 'PANEL_CLOSE'
        col2.prop(section_prop, "armatures", text="", icon="ARMATURE_DATA")
        text = 'Remove' if section_prop.remove_nonmesh else 'Keep'
        col2.prop(section_prop, "remove_nonmesh", text=text, icon=icon)
        icon = 'CHECKMARK' if section_prop.update_material else 'PANEL_CLOSE'
        text = 'Enabled' if section_prop.update_material else 'Disabled'
        col2.prop(section_prop, "update_material", text=text, icon=icon)
        icon = 'CHECKMARK' if section_prop.reorder_mesh_id else 'PANEL_CLOSE'
        text = 'Enabled' if section_prop.reorder_mesh_id else 'Disabled'
        col2.prop(section_prop, "reorder_mesh_id", text=text, icon=icon)
        col2.prop(section_prop, "rename_import", text="")

        layout.separator(factor=0.5)

    def draw_modpack(self, layout:UILayout, section_prop):
        if platform.system() == "Windows":
            row = layout.row(align=True)
            split = row.split(factor=0.65, align=True)
            icon = "CHECKMARK" if section_prop.consoletools_status == "ConsoleTools Ready!" else "X"
            split.label(text=section_prop.consoletools_status, icon=icon)
            split.operator("ya.file_console_tools", text="Check")
            row.operator("ya.consoletools_dir", icon="FILE_FOLDER", text="")

            layout.separator(factor=0.5,type="LINE")

        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Model:")
        split.prop(section_prop, "game_model_path", text="")
        model_path = section_prop.game_model_path
        icon = "CHECKMARK" if model_path.startswith("chara") or model_path.endswith("mdl") else "X"
        row.label(icon=icon)

        if section_prop.game_model_path.startswith("chara") and section_prop.game_model_path.endswith("mdl"):
            row = layout.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="")
            split.operator("ya.gamepath_category", text="Chest", depress=section_prop.chest_g_category).category = "top"
            split.operator("ya.gamepath_category", text="Hands", depress=section_prop.hands_g_category).category = "glv"
            split.operator("ya.gamepath_category", text="Legs", depress=section_prop.legs_g_category).category = "dwn"
            split.operator("ya.gamepath_category", text="Feet", depress=section_prop.feet_g_category).category = "sho"
        
        
        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="FBX:")
        split.prop(section_prop, "savemodpack_display_directory", text="")
        row.operator("ya.modpack_dir_selector", icon="FILE_FOLDER", text="").category = "savemodpack"
        
        if len(bpy.context.scene.fbx_subfolder) > 1:
            row = layout.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="Subfolder:")
            split.prop(section_prop, "fbx_subfolder", text="") 
            row.label(icon="FOLDER_REDIRECT") 

        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.label(text="")
        split.operator("ya.directory_copy", text="Copy from Export") 

        box = layout.box()
        row = box.row(align=True)
        row.prop(section_prop, "button_modpack_replace", text="New", icon="FILE_NEW", invert_checkbox=True)
        row.prop(section_prop, "button_modpack_replace", text="Update", icon="CURRENT_FILE",)

        box.separator(factor=0.5,type="LINE")

        if section_prop.button_modpack_replace:

            row = box.row(align=True)
            split = row.split(factor=0.25)
            col2 = split.column(align=True)
            col2.label(text="Ver.")
            col2.prop(section_prop, "loadmodpack_version", text="")

            col = split.column(align=True)
            col.label(text="Modpack:")
            col.prop(section_prop, "loadmodpack_display_directory", text="", emboss=False)

            split2 = row.split(factor=1)
            col3 = split2.column(align=True)
            col3.alignment = "CENTER"
            col3.operator("ya.pmp_selector", icon="FILE", text="")
            col3.prop(section_prop, "loadmodpack_author", text="by", emboss=False)

            if Path(section_prop.loadmodpack_directory).is_file():
                selection = section_prop.modpack_groups

                row = box.row(align=True)
                split = row.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                text = "Create:" if selection == "0" else "Replace:"
                split.label(text=text)
                split.prop(section_prop, "modpack_groups", text="")
                sub = row.row(align=True)
                sub.alignment = "RIGHT"
                if selection != "0":
                    sub.prop(section_prop, "modpack_ui_page", emboss=False)
                else:
                    sub.prop(section_prop, "modpack_page", emboss=True)

                row = box.row(align=True)
                split = row.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                split.label(text="Name:")
                split.prop(section_prop, "modpack_rename_group", text="")
                sub = row.row(align=True)
                sub.alignment = "RIGHT"
                sub.prop(section_prop, "mod_group_type", text="")
            else:
                row = box.row(align=True)

        else:

            row = box.row(align=True)
            split = row.split(factor=0.25)
            col2 = split.column(align=True)
            col2.label(text="Ver.")
            col2.prop(section_prop, "new_mod_version", text="")

            col = split.column(align=True)
            col.label(text="Mod Name:")
            col.prop(section_prop, "new_mod_name", text="")
            
            split2 = row.split(factor=1)
            col3 = split2.column(align=True)
            col3.alignment = "CENTER"
            col3.label(text="Author:")
            col3.prop(section_prop, "author_name", text="")

            row = box.row(align=True)
            split = row.split(factor=0.25)
            col3 = split.column(align=True)
            col3.alignment = "RIGHT"
            col3.label(text="Group:")

            col2 = split.column(align=True)
            col2.prop(section_prop, "modpack_rename_group", text="")

            split2 = row.split(factor=1)
            col = split2.column(align=True)
            col.alignment = "CENTER"
            col.prop(section_prop, "mod_group_type", text="")



        row = box.row(align=True)
        if platform.system() == "Windows":
            row.operator("ya.file_modpacker", text="Convert & Pack").preset = "convert_pack"
            row.operator("ya.file_modpacker", text="Convert").preset = "convert"
        row.operator("ya.file_modpacker", text="Pack").preset = "pack"

        box.separator(factor=0.5, type="LINE")

        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Status:")
        split.prop(section_prop, "modpack_progress", text="", emboss=False)

        box.separator(factor=0.1)

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

    def dropdown_header(self, button, section_prop, prop_str=str, label=str, extra_icon=""):
        layout = self.layout
        row = layout.row(align=True)
        split = row.split(factor=1)
        box = split.box()
        sub = box.row(align=True)
        sub.alignment = 'LEFT'

        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        sub.prop(section_prop, prop_str, text="", icon=icon, emboss=False)
        sub.label(text=label)
        if extra_icon != "":
            sub.label(icon=extra_icon)
        
        return box

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
    MESH_UL_yas,
    MESH_UL_shape,
    FrameJump,
    KeyframeJump,
    DirSelector,
    BodyPartSlot,
    PanelCategory,
    OutfitCategory,
    OutfitStudio,
    FileManager
]   