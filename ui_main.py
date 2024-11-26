import bpy
import utils as Utils

from bpy.types import Panel

def dynamic_column_operators(columns, layout, labels):
    box = layout.box()
    row = box.row(align=True)

    columns_list = [row.column(align=True) for _ in range(columns)]

    for index, (name, (operator, depress)) in enumerate(labels.items()):
            
        col_index = index % columns 
        
        columns_list[col_index].operator(operator, text=name, depress=depress)

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

class Overview(Panel):
    bl_idname = "VIEW3D_PT_YA_Overview"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "Yet Another Overview"

    def draw(self, context):
        mq = Utils.get_object_from_mesh("Mannequin")
        torso = Utils.get_object_from_mesh("Torso")
        legs = Utils.get_object_from_mesh("Waist")
        hands = Utils.get_object_from_mesh("Hands")
        feet = Utils.get_object_from_mesh("Feet")

        ob = self.collection_context(context)
        key = ob.data.shape_keys
        layout = self.layout
        label_name = ob.data.name
        scene = context.scene
        section_prop = scene.main_props
        ui_props = scene.main_props

        button_adv = ui_props.button_advanced_expand

        # SHAPE MENUS
        
        if button_adv:
            box = layout.box()
            row = box.row(align=True)
            row.label(text=f"{label_name}:")
            text = "Collection" if section_prop.button_dynamic_view else "Active"
            row.prop(section_prop, "button_dynamic_view", text=text, icon="HIDE_OFF")
        
            row.alignment = "RIGHT"
            row.prop(ui_props, "button_advanced_expand", text="", icon="TOOL_SETTINGS")
            

            row = layout.row()
            row.template_list(
                "MESH_UL_shape_keys", 
                "", 
                key, 
                "key_blocks", 
                ob, 
                "active_shape_key_index", 
                rows=10)
        
        if not button_adv:
            
            # CHEST

            button = section_prop.button_chest_shapes

            box = layout.box()
            row = box.row(align=True)
            
            icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
            row.prop(section_prop, "button_chest_shapes", text="", icon=icon, emboss=False)
            row.label(text="CHEST")
            
            button_row = row.row(align=True)
            button_row.prop(section_prop, "shape_mq_chest_bool", text="", icon="ARMATURE_DATA")
            button_row.prop(section_prop, "button_advanced_expand", text="", icon="TOOL_SETTINGS")

            if button:
                box.separator(factor=0.5,type="LINE")
                self.chest_shapes(box, section_prop, mq, torso)

            layout.separator(factor=0.1)

            # LEGS

            button = section_prop.button_leg_shapes

            box = layout.box()
            row = box.row(align=True)
            
            icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
            row.prop(section_prop, "button_leg_shapes", text="", icon=icon, emboss=False)
            row.label(text="LEGS")
            
            button_row = row.row(align=True)
            button_row.prop(section_prop, "shape_mq_legs_bool", text="", icon="ARMATURE_DATA")

            if button:
                box.separator(factor=0.5,type="LINE")
                self.leg_shapes(box, section_prop, mq, legs)

            layout.separator(factor=0.1)
            
            # OTHER

            button = section_prop.button_other_shapes

            box = layout.box()
            row = box.row(align=True)
            icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
            row.prop(section_prop, "button_other_shapes", text="", icon=icon, emboss=False)
            row.label(text="HANDS/FEET")
            
            button_row = row.row(align=True)
            button_row.prop(section_prop, "shape_mq_other_bool", text="", icon="ARMATURE_DATA")

            if button:
                box.separator(factor=0.5,type="LINE")
                self.other_shapes(box, section_prop, mq, hands, feet)

        layout.separator(factor=0.1)

        # YAS MENU

        button = ui_props.button_yas_expand                          

        box = layout.box()
        row = box.row(align=True)
        row.alignment = 'LEFT'
        
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row.prop(section_prop, "button_yas_expand", text="", icon=icon, emboss=False)
        row.label(text="YET ANOTHER SKELETON")

        if button:
            box.separator(factor=0.5,type="LINE")
            row = box.row(align=True)
            icon = 'CHECKMARK' if torso.toggle_yas else 'PANEL_CLOSE'
            row.prop(torso, "toggle_yas", text="Chest", icon=icon)
            icon = 'CHECKMARK' if hands.toggle_yas else 'PANEL_CLOSE'
            row.prop(hands, "toggle_yas", text="Hands", icon=icon)
            icon = 'CHECKMARK' if feet.toggle_yas else 'PANEL_CLOSE'
            row.prop(feet, "toggle_yas", text="Feet", icon=icon)

            box.separator(factor=0.5,type="LINE")

            row = box.row(align=True)
            col2 = row.column(align=True)
            col2.label(text="Legs:")
            icon = 'CHECKMARK' if legs.toggle_yas else 'PANEL_CLOSE'
            col2.prop(legs, "toggle_yas", text="YAS", icon=icon)
            icon = 'CHECKMARK' if legs.toggle_yas_gen else 'PANEL_CLOSE'
            col2.prop(legs, "toggle_yas_gen", text="Genitalia", icon=icon)

            col = row.column(align=True)
            col.label(text="Mannequin:")
            icon = 'CHECKMARK' if mq.toggle_yas else 'PANEL_CLOSE'
            col.prop(mq, "toggle_yas", text="YAS", icon=icon)
            icon = 'CHECKMARK' if mq.toggle_yas_gen else 'PANEL_CLOSE'
            col.prop(mq, "toggle_yas_gen", text="Genitalia", icon=icon) 

            box.separator(factor=0.1)
            
    def collection_context(self, context):
        # Links mesh name to the standard collections)
        body_part_collections = {
            "Torso": ['Chest', 'Nipple Piercings'],
            "Waist": ['Legs', 'Pubes'],
            "Hands": ['Hands', 'Nails', 'Practical Uses', 'Clawsies'],
            "Feet": ['Feet', 'Toenails', 'Toe Clawsies'] 
            }

        # Get the active object
        active_ob = bpy.context.active_object

        if active_ob and Utils.has_shape_keys(active_ob):
            if not context.scene.main_props.button_dynamic_view:
                return active_ob
            else:
                active_collection = active_ob.users_collection
                for body_part, collections in body_part_collections.items():
                    if any(bpy.data.collections[coll_name] in active_collection for coll_name in collections):
                        return Utils.get_object_from_mesh(body_part) 
                return active_ob
        else:
            return Utils.get_object_from_mesh("Mannequin")

    def chest_shapes(self, layout, section_prop, mq, torso):  
        if section_prop.shape_mq_chest_bool:
            target = mq
            key_target = "mq"
        else:
            target = torso
            key_target = "torso"

        medium_mute = target.data.shape_keys.key_blocks["MEDIUM ----------------------------"].mute
        small_mute = target.data.shape_keys.key_blocks["SMALL ------------------------------"].mute
        buff_mute = target.data.shape_keys.key_blocks["Buff"].mute
        rue_mute = target.data.shape_keys.key_blocks["Rue"].mute
        
        large_depress = True if small_mute and medium_mute else False
        medium_depress = True if not medium_mute and small_mute else False
        small_depress = True if not small_mute and medium_mute else False
        buff_depress = True if not buff_mute else False
        rue_depress = True if not rue_mute else False
        
        row = layout.row(align=True)
        operator = row.operator("ya.apply_shapes", text= "Large", depress=large_depress)
        operator.key = "Large"
        operator.target = "Torso"
        operator.preset = "chest_category"
        operator = row.operator("ya.apply_shapes", text= "Medium", depress=medium_depress)
        operator.key = "Medium"
        operator.target = "Torso"
        operator.preset = "chest_category"
        operator = row.operator("ya.apply_shapes", text= "Small", depress=small_depress)
        operator.key = "Small"
        operator.target = "Torso"
        operator.preset = "chest_category"

        row = layout.row(align=True)
        operator = row.operator("ya.apply_shapes", text= "Buff", depress=buff_depress)
        operator.key = "Buff"
        operator.target = "Torso"
        operator.preset = "other"

        operator = row.operator("ya.apply_shapes", text= "Rue", depress=rue_depress)
        operator.key = "Rue"
        operator.target = "Torso"
        operator.preset = "other"

        layout.separator(factor=0.5,type="LINE")

        row = layout.row()
        
        if not small_mute and not medium_mute:
            row.alignment = "CENTER"
            row.label(text="Select a chest size.")
        else:
            split = row.split(factor=0.25)
            col = split.column(align=True)
            col.alignment = "RIGHT"
            col.label(text="Squeeze:")
            if large_depress or medium_depress:
                col.label(text="Squish:")
                col.label(text="Push-Up:")
            if medium_depress:
                col.label(text="Sayonara:")
                col.label(text="Mini:")
            if large_depress:
                col.label(text="Omoi:")
            if large_depress or medium_depress:
                col.label(text="Sag:")
            col.label(text="Nip Nops:")

            if large_depress:
                col2 = split.column(align=True)
                col2.prop(section_prop, f"key_squeeze_large_{key_target}")
                col2.prop(section_prop, f"key_squish_large_{key_target}")
                col2.prop(section_prop, f"key_pushup_large_{key_target}")
                col2.prop(section_prop, f"key_omoi_large_{key_target}")
                col2.prop(section_prop, f"key_sag_omoi_{key_target}")
                col2.prop(section_prop, f"key_nipnops_large_{key_target}")
            
            elif medium_depress:
                col2 = split.column(align=True)
                col2.prop(section_prop, f"key_squeeze_medium_{key_target}")
                col2.prop(section_prop, f"key_squish_medium_{key_target}")
                col2.prop(section_prop, f"key_pushup_medium_{key_target}")
                col2.prop(section_prop, f"key_sayonara_medium_{key_target}")
                col2.prop(section_prop, f"key_mini_medium_{key_target}")
                col2.prop(section_prop, f"key_sag_medium_{key_target}")
                col2.prop(section_prop, f"key_nipnops_medium_{key_target}")

            elif small_depress:
                col2 = split.column(align=True)
                col2.prop(section_prop, f"key_squeeze_small_{key_target}")
                col2.prop(section_prop, f"key_nipnops_small_{key_target}")

        layout.separator(factor=0.5,type="LINE")
        
        row = layout.row()
        split = row.split(factor=0.25, align=True) 
        col = split.column(align=True)
        col.alignment = "RIGHT"
        col.label(text="Preset:")
        
        col2 = split.column(align=True)
        col2.prop(section_prop, "chest_shape_enum")

        col3 = split.column(align=True)
        col3.operator("ya.apply_shapes", text= "Apply").preset = "shapes"

        layout.separator(factor=0.1)

    def leg_shapes(self, layout, section_prop, mq, legs):
        if section_prop.shape_mq_legs_bool:
            target = mq
        else:
            target = legs

        skull_mute = target.data.shape_keys.key_blocks["Skull Crushers"].mute
        mini_mute = target.data.shape_keys.key_blocks["Mini"].mute
        rue_mute = target.data.shape_keys.key_blocks["Rue"].mute

        genb_mute = target.data.shape_keys.key_blocks["Gen B"].mute
        genc_mute = target.data.shape_keys.key_blocks["Gen C"].mute
        gensfw_mute = target.data.shape_keys.key_blocks["Gen SFW"].mute

        small_mute = target.data.shape_keys.key_blocks["Small Butt"].mute
        soft_mute = target.data.shape_keys.key_blocks["Soft Butt"].mute

        hip_yab_mute = target.data.shape_keys.key_blocks["Hip Dips (for YAB)"].mute
        hip_rue_mute = target.data.shape_keys.key_blocks["Less Hip Dips (for Rue)"].mute

        melon_depress = True if skull_mute and mini_mute else False
        skull_depress = True if not skull_mute else False
        mini_depress = True if not mini_mute else False
        rue_depress = True if not rue_mute else False

        gena_depress = True if genb_mute and gensfw_mute and genc_mute else False
        genb_depress = True if not genb_mute else False
        genc_depress = True if not genc_mute else False
        gensfw_depress = True if not gensfw_mute else False

        small_depress = True if not small_mute else False
        soft_depress = True if not soft_mute else False
        hip_depress = True if not hip_yab_mute or not hip_rue_mute else False
        
        row = layout.row(align=True) 
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Genitalia:")
        button_row = split.row(align=True)

        operator = button_row.operator("ya.apply_shapes", text= "A", depress=gena_depress)
        operator.key = "Gen A"
        operator.target = "Legs"
        operator.preset = "gen"

        operator = button_row.operator("ya.apply_shapes", text= "B", depress=genb_depress)
        operator.key = "Gen B"
        operator.target = "Legs"
        operator.preset = "gen"

        operator = button_row.operator("ya.apply_shapes", text= "C", depress=genc_depress)
        operator.key = "Gen C"
        operator.target = "Legs"
        operator.preset = "gen"

        operator = button_row.operator("ya.apply_shapes", text= "SFW", depress=gensfw_depress)
        operator.key = "Gen SFW"
        operator.target = "Legs"
        operator.preset = "gen"
        
        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Leg sizes:")
        button_row = split.row(align=True)
        operator = button_row.operator("ya.apply_shapes", text= "Melon", depress=melon_depress)
        operator.key = "Melon"
        operator.target = "Legs"
        operator.preset = "leg_size"

        operator = button_row.operator("ya.apply_shapes", text= "Skull", depress=skull_depress)
        operator.key = "Skull"
        operator.target = "Legs"
        operator.preset = "leg_size"

        operator = button_row.operator("ya.apply_shapes", text= "Mini", depress=mini_depress)
        operator.key = "Mini"
        operator.target = "Legs"
        operator.preset = "leg_size"

        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Butt options:")
        button_row = split.row(align=True)
        operator = button_row.operator("ya.apply_shapes", text= "Small", depress=small_depress)
        operator.key = "Small Butt"
        operator.target = "Legs"
        operator.preset = "other"
        operator = button_row.operator("ya.apply_shapes", text= "Soft", depress=soft_depress)
        operator.key = "Soft Butt"
        operator.target = "Legs"
        operator.preset = "other"

        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        operator = split.operator("ya.apply_shapes", text= "Alt Hips", depress=hip_depress)
        operator.key = "Alt Hips"
        operator.target = "Legs"
        operator.preset = "other"
        button_row = split.row(align=True)
        operator = button_row.operator("ya.apply_shapes", text= "Rue", depress=rue_depress)
        operator.key = "Rue"
        operator.target = "Legs"
        operator.preset = "other"
        
        layout.separator(factor=0.1)

    def other_shapes(self, layout, section_prop, mq, hands, feet):
        if section_prop.shape_mq_other_bool:
                        target = mq
                        target_f = mq
                        key_target = "mq"
        else:
            target = hands
            target_f = feet
            key_target = "feet"
            clawsies_mute = target.data.shape_keys.key_blocks["Curved"].mute
            clawsies_depress = True if clawsies_mute else False
            clawsies_col = bpy.context.view_layer.layer_collection.children["Hands"].children["Clawsies"].exclude
            toeclawsies_col = bpy.context.view_layer.layer_collection.children["Feet"].children["Toe Clawsies"].exclude

        short_mute = target.data.shape_keys.key_blocks["Short Nails"].mute
        ballerina_mute = target.data.shape_keys.key_blocks["Ballerina"].mute
        stabbies_mute = target.data.shape_keys.key_blocks["Stabbies"].mute
        rue_mute = target.data.shape_keys.key_blocks["Rue"].mute
        rue_f_mute = target_f.data.shape_keys.key_blocks["Rue"].mute

        long_depress = True if short_mute and ballerina_mute and stabbies_mute else False
        short_depress = True if not short_mute else False
        ballerina_depress = True if not ballerina_mute else False
        stabbies_depress = True if not stabbies_mute else False
        rue_depress = True if not rue_mute else False
        rue_f_depress = True if not rue_f_mute else False
        nails_col = bpy.context.view_layer.layer_collection.children["Hands"].children["Nails"].exclude
        toenails_col = bpy.context.view_layer.layer_collection.children["Feet"].children["Toenails"].exclude

        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Hands:")
        button_row = split.row(align=True)
        operator = button_row.operator("ya.apply_shapes", text= "Rue", depress=rue_depress)
        operator.key = "Rue"
        operator.target = "Hands"
        operator.preset = "other"

        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Nails:")
        button_row = split.row(align=True)
        icon = "HIDE_ON" if nails_col else "HIDE_OFF"
        if not section_prop.shape_mq_other_bool:
            operator = button_row.operator("ya.apply_visibility", text="", icon=icon, depress=not nails_col)
            operator.key = "Nails"
            operator.target = "Hands"

        operator = button_row.operator("ya.apply_shapes", text= "Long", depress=long_depress)
        operator.key = "Long"
        operator.target = "Hands"
        operator.preset = "nails"
        
        operator = button_row.operator("ya.apply_shapes", text= "Short", depress=short_depress)
        operator.key = "Short"
        operator.target = "Hands"
        operator.preset = "nails"

        operator = button_row.operator("ya.apply_shapes", text= "Ballerina", depress=ballerina_depress)
        operator.key = "Ballerina"
        operator.target = "Hands"
        operator.preset = "nails"

        operator = button_row.operator("ya.apply_shapes", text= "Stabbies", depress=stabbies_depress)
        operator.key = "Stabbies"
        operator.target = "Hands"
        operator.preset = "nails"

        if not section_prop.shape_mq_other_bool:
            row = layout.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="Clawsies:")
            button_row = split.row(align=True)
            icon = "HIDE_ON" if clawsies_col else "HIDE_OFF"
            operator = button_row.operator("ya.apply_visibility", text="", icon=icon, depress=not clawsies_col)
            operator.key = "Clawsies"
            operator.target = "Hands"
            operator = button_row.operator("ya.apply_shapes", text= "Straight", depress=clawsies_depress)
            operator.key = "Curved"
            operator.target = "Hands"
            operator.preset = "other"
            operator = button_row.operator("ya.apply_shapes", text= "Curved", depress=not clawsies_depress)
            operator.key = "Curved"
            operator.target = "Hands"
            operator.preset = "other"

        layout.separator(type="LINE")

        row = layout.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Feet:")
        button_row = split.row(align=True)
        operator = button_row.operator("ya.apply_shapes", text= "Rue", depress=rue_f_depress)
        operator.key = "Rue"
        operator.target = "Feet"

        if not section_prop.shape_mq_other_bool:
            row = layout.row(align=True)
            col = row.column(align=True)
            row = col.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = 'RIGHT'  # Align label to the right
            split.label(text="Nails/Claws:")
            icon = "HIDE_ON" if nails_col else "HIDE_OFF"
            operator = split.operator("ya.apply_visibility", text="", icon=icon, depress=not toenails_col)
            operator.key = "Nails"
            operator.target = "Feet"
            split.operator("ya.apply_visibility", text="", icon=icon, depress=not toeclawsies_col).target = "Feet"
        
        row = layout.row(align=True)
        split = row.split(factor=0.25)
        col = split.column(align=True)
        col.alignment = "RIGHT"
        col.label(text="Heels:")
        col.label(text="Cinderella:")
        col.label(text="Mini Heels:")

        col2 = split.column(align=True)
        col2.prop(section_prop, f"key_heels_{key_target}")
        col2.prop(section_prop, f"key_cinderella_{key_target}")
        col2.prop(section_prop, f"key_miniheels_{key_target}")

        layout.separator(factor=0.1)


class Tools(Panel):
    bl_idname = "VIEW3D_PT_YA_Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "Weights"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 1
    
    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator("ya.remove_empty_vgroups", text= "Remove Empty Groups")


class FileManager(Panel):
    bl_idname = "VIEW3D_PT_YA_FileManager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "File Manager"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        section_prop = scene.file_props
        ui_prop = scene.main_props

        # EXPORT
        button = ui_prop.button_export_expand
        box = dropdown_header(self, button, ui_prop, "button_export_expand", "EXPORT", "EXPORT")
        if button:
            box.separator(factor=0.5,type="LINE")
            self.draw_export(box, section_prop, ui_prop)

        layout.separator(factor=0.1)

        # IMPORT
        button = ui_prop.button_import_expand
        box = dropdown_header(self, button, ui_prop, "button_import_expand", "IMPORT", "IMPORT")

        layout.separator(factor=0.1)

        # MODPACKER
        button = ui_prop.button_file_expand
        box = dropdown_header(self, button, ui_prop, "button_file_expand", "MODPACK", "NEWFOLDER")

        if button:
            box.separator(factor=0.5,type="LINE")
            row = box.row(align=True)
            split = row.split(factor=0.65, align=True)
            icon = "CHECKMARK" if section_prop.consoletools_status == "ConsoleTools Ready!" else "X"
            split.label(text=section_prop.consoletools_status, icon=icon)
            split.operator("ya.file_console_tools", text="Check")
            row.operator("ya.consoletools_dir", icon="FILE_FOLDER", text="")

            box.separator(factor=0.5,type="LINE")

            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="Model:")
            split.prop(section_prop, "game_model_path", text="")
            model_path = section_prop.game_model_path
            icon = "CHECKMARK" if model_path.startswith("chara") or model_path.endswith("mdl") else "X"
            row.label(icon=icon)
            
            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="FBX:")
            split.prop(section_prop, "savemodpack_display_directory", text="")
            
            row.operator("ya.dir_selector", icon="FILE_FOLDER", text="").category = "savemodpack"

            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.label(text="")
            split.operator("ya.directory_copy", text="Copy from Export") 

            row = box.row(align=True)
            row.prop(ui_prop, "button_modpack_replace", text="New", icon="FILE_NEW", invert_checkbox=True)
            row.prop(ui_prop, "button_modpack_replace", text="Update", icon="CURRENT_FILE",)

            if ui_prop.button_modpack_replace:

                row = box.row()
                split = row.split(factor=0.33)
                col2 = split.column(align=True)
                col2.label(text="Ver.")
                col2.prop(section_prop, "loadmodpack_version", text="")
                col = split.column(align=True)
                col.label(text="Modpack:")
                col.prop(section_prop, "loadmodpack_display_directory", text="", emboss=False)
                split2 = row.split(factor=0.8)
                col3 = split2.column(align=True)
                col3.alignment = "CENTER"
                col3.label(text="")
                col3.prop(section_prop, "loadmodpack_author", text="by", emboss=False)

         
                row = box.row(align=True)
                split = row.split(factor=0.25, align=True)
                split.label(text="")
                split.operator("ya.pmp_selector", icon="FILE_FOLDER", text="Choose Modpack")
                
                
                row = box.row(align=True)
                split = row.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                split.label(text="Replace:")
                split.prop(section_prop, "modpack_groups", text="")

                row = box.row()
                split = row.split(factor=0.25)
                col2 = split.column(align=True)
                if section_prop.modpack_groups == "0":
                    col2.prop(section_prop, "mod_group_type", text="")
                else:
                    text = "" if section_prop.modpack_groups == "0" else "Rename:"
                    col2.alignment = "RIGHT"
                    col2.label(text=text)
                col = split.column(align=True)
                col.prop(section_prop, "modpack_rename_group", text="")
            
            else:
                

                row = box.row()
                split = row.split(factor=0.25)
                col2 = split.column(align=True)
                col2.label(text="Ver.")
                col2.prop(section_prop, "new_mod_version", text="")
                col = split.column(align=True)
                col.label(text="Mod Name:")
                col.prop(section_prop, "new_mod_name", text="")

                row = box.row()
                split = row.split(factor=0.25)
                col2 = split.column(align=True)
                col2.label(text="Type:")
                col2.prop(section_prop, "mod_group_type", text="")
                col = split.column(align=True)
                col.label(text="Group Name:")
                col.prop(section_prop, "modpack_rename_group", text="")

                row = box.row(align=True)
                split = row.split(factor=0.25, align=True)
                split.alignment = "RIGHT"
                split.label(text="Author:")
                split.prop(section_prop, "author_name", text="")



            row = box.row(align=True)
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
    
    def draw_export(self, layout, section_prop, ui_prop):
        row = layout.row(align=True)
        row.prop(section_prop, "export_display_directory", text="")
        row.operator("ya.dir_selector", icon="FILE_FOLDER", text="").category = "export"

        row = layout.row(align=True)
        col = row.column(align=True)
        col.operator("ya.simple_export", text="Simple Export")
        col2 = row.column(align=True)
        col2.operator("ya.batch_queue", text="Batch Export")
        
        export_text = "GLTF" if section_prop.export_gltf else "FBX"
        icon = "BLENDER" if section_prop.export_gltf else "VIEW3D"
        col3 = row.column(align=True)
        col3.alignment = "RIGHT"
        col3.prop(section_prop, "export_gltf", text=export_text, icon=icon, invert_checkbox=True)


        layout.separator(factor=1, type='LINE')


        row = layout.row(align=True)
        if section_prop.export_body_slot == "Chest/Legs":
            row.label(text=f"Body Part: Chest")
        else:
            row.label(text=f"Body Part: {section_prop.export_body_slot}")

        options =[
            ("Chest", "MOD_CLOTH"),
            ("Legs", "BONE_DATA"),
            ("Hands", "VIEW_PAN"),
            ("Feet", "VIEW_PERSPECTIVE"),
            ("Chest/Legs", "ARMATURE_DATA")
            ]
        
        self.body_category_buttons(row, section_prop, options)
    
            
        # CHEST EXPORT  
        
        button_type = "export"
        if section_prop.export_body_slot == "Chest" or section_prop.export_body_slot == "Chest/Legs":

            category = "Chest"
            labels = {
                "Large":      "Large",    
                "Medium":     "Medium",   
                "Small":      "Small",    
                "Omoi":       "Omoi",     
                "Sayonara":   "Sayonara", 
                "Mini":       "Mini",     
                "Sugoi Omoi": "Sugoi Omoi", 
                "Tsukareta":  "Tsukareta", 
                "Tsukareta+": "Tsukareta+"
            }
    
            self.dynamic_column_buttons(3, layout, section_prop, labels, category, button_type)

            layout.separator(factor=1)

            labels = {"Buff": "Buff", "Rue": "Rue", "Piercings": "Piercings"}
    
            self.dynamic_column_buttons(3, layout, section_prop, labels, category, button_type)

            if section_prop.export_body_slot == "Chest/Legs":
                layout.separator(factor=1, type="LINE")
                row = layout.row(align=True)
                row.label(text=f"Body Part: Legs")
            
        # LEG EXPORT  
        
        if section_prop.export_body_slot == "Legs" or section_prop.export_body_slot == "Chest/Legs":
            
            category = "Legs"
            labels = {
                "Melon": "Melon",
                "Skull": "Skull",  
                "Mini": "Mini",
                "Small Butt": "Small Butt",
                "Rue": "Rue",
                "Soft Butt": "Soft Butt", 
                    
                }
    
            self.dynamic_column_buttons(3, layout, section_prop, labels, category, button_type)

            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(text="One leg and gen shape is required.")

            labels = {
                "Gen A":  "Gen A",
                "Gen B":  "Gen B", 
                "Gen C":  "Gen C",
                "Hip Dips":  "Hip Dips", 
                "Gen SFW":  "Gen SFW",
                "Pubes":  "Pubes"
            }
    
            self.dynamic_column_buttons(3, layout, section_prop, labels, category, button_type)  

        # HAND EXPORT  
        
        if section_prop.export_body_slot == "Hands":
            
            category = "Hands"
            labels = {
                "YAB": "YAB", 
                "Rue": "Rue"
                }
    
            self.dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)
            
            layout.separator(factor=0.5, type="LINE")

            labels = {
                "Long": "Long", 
                "Short": "Short", 
                "Ballerina": "Ballerina", 
                "Stabbies": "Stabbies" 
                }

            self.dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)

            row = layout.row(align=True)
            row.label(text="Clawsies:")

            labels = { 
                "Straight": "Straight", 
                "Curved": "Curved"
                }

            self.dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)

            row = layout.row(align=True)

        # FEET EXPORT  
        
        if section_prop.export_body_slot == "Feet":
            
            category = "Feet"
            labels = {
                "YAB": "YAB", 
                "Rue": "Rue", 
                }
    
            self.dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)

            labels = { 
                "Clawsies": "Clawsies"
                }

            self.dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)
       
        layout.separator(factor=0.5, type="LINE")

        button = ui_prop.button_export_options
        
        row = layout.row(align=True)
        split = row.split(factor=1)
        sub = split.row(align=True)
        sub.alignment = 'LEFT'

        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        sub.prop(ui_prop, "button_export_options", text="", icon=icon, emboss=False)
        sub.label(text="Advanced Options")
        if button:
            row = layout.row(align=True)
            col = row.column(align=True)
            icon = 'CHECKMARK' if section_prop.force_yas else 'PANEL_CLOSE'
            col.prop(section_prop, "force_yas", text="Force YAS", icon=icon)
            col2 = row.column(align=True)
            icon = 'CHECKMARK' if section_prop.check_tris else 'PANEL_CLOSE'
            col2.prop(section_prop, "check_tris", text="Check Triangulation", icon=icon)

            

        layout.separator(factor=0.5)

    def dynamic_column_buttons(self, columns, box, section_prop, labels, category, button_type):
        row = box.row(align=True)

        columns_list = [row.column(align=True) for _ in range(columns)]

        for index, (size, name) in enumerate(labels.items()):
            size_lower = size.lower().replace(' ', "_")
            category_lower = category.lower()

            prop_name = f"{button_type}_{size_lower}_{category_lower}_bool"

            if hasattr(section_prop, prop_name):
                icon = 'CHECKMARK' if getattr(section_prop, prop_name) else 'PANEL_CLOSE'
                
                col_index = index % columns 
                
                columns_list[col_index].prop(section_prop, prop_name, text=name, icon=icon)
            else:
                print(f"{name} has no assigned property!")
        return box  

    def body_category_buttons(self, layout, section_prop, options):
        row = layout

        for slot, icon in options:
            depress = True if section_prop.export_body_slot == slot else False
            row.operator("ya.set_body_part", text="", icon=icon, depress=depress).body_part = slot
        
          
classes = [
    Overview,
    Tools,
    FileManager
]