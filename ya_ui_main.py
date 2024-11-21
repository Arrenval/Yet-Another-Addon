import bpy
import ya_utils as utils

from bpy.types import Panel

def dynamic_column_buttons(columns, box, section_prop, labels, category, button_type):
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

def dynamic_column_operators(columns, layout, labels):
    box = layout.box()
    row = box.row(align=True)

    columns_list = [row.column(align=True) for _ in range(columns)]

    for index, (name, (operator, depress)) in enumerate(labels.items()):
            
        col_index = index % columns 
        
        columns_list[col_index].operator(operator, text=name, depress=depress)

    return box  

class YAOverview(Panel):
    bl_idname = "VIEW3D_PT_YA_Overview"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "Yet Another Overview"

    def draw(self, context):
        mq = utils.get_object_from_mesh("Mannequin")
        torso = utils.get_object_from_mesh("Torso")
        legs = utils.get_object_from_mesh("Waist")
        hands = utils.get_object_from_mesh("Hands")
        feet = utils.get_object_from_mesh("Feet")

        ob = self.collection_context(context)
        key = ob.data.shape_keys
        layout = self.layout
        label_name = ob.data.name
        scene = context.scene
        section_prop = scene.ya_props

        button_adv = section_prop.button_advanced_expand

        # SHAPE MENUS
        
        if button_adv:
            box = layout.box()
            row = box.row(align=True)
            row.label(text=f"{label_name}:")
            text = "Collection" if section_prop.button_dynamic_view else "Active"
            row.prop(section_prop, "button_dynamic_view", text=text, icon="HIDE_OFF")
        
            depress = True if section_prop.export_body_slot == "Chest" else False
            row.alignment = "RIGHT"
            row.prop(section_prop, "button_advanced_expand", text="", icon="TOOL_SETTINGS")
            

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
            row.label(text="Chest")
            
            button_row = row.row(align=True)
            button_row.prop(section_prop, "shape_mq_chest_bool", text="", icon="ARMATURE_DATA")
            button_row.prop(section_prop, "button_advanced_expand", text="", icon="TOOL_SETTINGS")

            if button:
                box.separator(factor=0.5,type="LINE")
                self.chest_shapes(box, section_prop, mq, torso)

            # LEGS

            button = section_prop.button_leg_shapes

            box = layout.box()
            row = box.row(align=True)
            
            icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
            row.prop(section_prop, "button_leg_shapes", text="", icon=icon, emboss=False)
            row.label(text="Legs")
            
            button_row = row.row(align=True)
            button_row.prop(section_prop, "shape_mq_legs_bool", text="", icon="ARMATURE_DATA")

            if button:
                box.separator(factor=0.5,type="LINE")
                self.leg_shapes(box, section_prop, mq, legs)

            # OTHER

            button = section_prop.button_other_shapes

            box = layout.box()
            row = box.row(align=True)
            icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
            row.prop(section_prop, "button_other_shapes", text="", icon=icon, emboss=False)
            row.label(text="Hands/Feet")
            
            button_row = row.row(align=True)
            button_row.prop(section_prop, "shape_mq_other_bool", text="", icon="ARMATURE_DATA")

            if button:
                box.separator(factor=0.5,type="LINE")
                self.other_shapes(box, section_prop, mq, hands, feet)


        # YAS MENU

        button = section_prop.button_yas_expand                          

        box = layout.box()
        row = box.row(align=True)
        row.alignment = 'LEFT'
        
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row.prop(section_prop, "button_yas_expand", text="", icon=icon, emboss=False)
        row.label(text="Yet Another Skeleton")

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

        if active_ob and utils.has_shape_keys(active_ob):
            if not context.scene.ya_props.button_dynamic_view:
                return active_ob
            else:
                active_collection = active_ob.users_collection
                for body_part, collections in body_part_collections.items():
                    if any(bpy.data.collections[coll_name] in active_collection for coll_name in collections):
                        return utils.get_object_from_mesh(body_part) 
                return active_ob
        else:
            return utils.get_object_from_mesh("Mannequin")

    def chest_shapes(self, box, section_prop, mq, torso):  
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
        
        row = box.row(align=True)
        row.operator("ya.apply_chest_category", text= "Large", depress=large_depress).key = "Large"
        row.operator("ya.apply_chest_category", text= "Medium", depress=medium_depress).key = "Medium"
        row.operator("ya.apply_chest_category", text= "Small", depress=small_depress).key = "Small"

        row = box.row(align=True)
        operator = row.operator("ya.apply_other_option", text= "Buff", depress=buff_depress)
        operator.key = "Buff"
        operator.target = "Torso"
        operator = row.operator("ya.apply_other_option", text= "Rue", depress=rue_depress)
        operator.key = "Rue"
        operator.target = "Torso"

        box.separator(factor=0.5,type="LINE")

        row = box.row()
        
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

        box.separator(factor=0.5,type="LINE")
        
        row = box.row()
        split = row.split(factor=0.25, align=True) 
        col = split.column(align=True)
        col.alignment = "RIGHT"
        col.label(text="Preset:")
        
        col2 = split.column(align=True)
        col2.prop(section_prop, "chest_shape_enum")

        col3 = split.column(align=True)
        col3.operator("ya.apply_shapes", text= "Apply")

    def leg_shapes(self, box, section_prop, mq, legs):
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
        
        row = box.row(align=True)
        
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Genitalia:")
        button_row = split.row(align=True)
        button_row.operator("ya.apply_gen", text= "A", depress=gena_depress).key = "Gen A"
        button_row.operator("ya.apply_gen", text= "B", depress=genb_depress).key = "Gen B"
        button_row.operator("ya.apply_gen", text= "C", depress=genc_depress).key = "Gen C"
        button_row.operator("ya.apply_gen", text= "SFW", depress=gensfw_depress).key = "Gen SFW"
        


        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Leg sizes:")
        button_row = split.row(align=True)
        button_row.operator("ya.apply_legs", text= "Melon", depress=melon_depress).key = "Melon"
        button_row.operator("ya.apply_legs", text= "Skull", depress=skull_depress).key = "Skull"
        button_row.operator("ya.apply_legs", text= "Mini", depress=mini_depress).key = "Mini"

        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Butt options:")
        button_row = split.row(align=True)
        operator = button_row.operator("ya.apply_other_option", text= "Small", depress=small_depress)
        operator.key = "Small Butt"
        operator.target = "Legs"
        operator = button_row.operator("ya.apply_other_option", text= "Soft", depress=soft_depress)
        operator.key = "Soft Butt"
        operator.target = "Legs"

        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        operator = split.operator("ya.apply_other_option", text= "Alt Hips", depress=hip_depress)
        operator.key = "Hip"
        operator.target = "Legs"
        button_row = split.row(align=True)
        operator = button_row.operator("ya.apply_other_option", text= "Rue", depress=rue_depress)
        operator.key = "Rue"
        operator.target = "Legs"

    def other_shapes(self, box, section_prop, mq, hands, feet):
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

        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Hands:")
        button_row = split.row(align=True)
        operator = button_row.operator("ya.apply_other_option", text= "Rue", depress=rue_depress)
        operator.key = "Rue"
        operator.target = "Hands"

        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Nails:")
        button_row = split.row(align=True)
        icon = "HIDE_ON" if nails_col else "HIDE_OFF"
        if not section_prop.shape_mq_other_bool:
            operator = button_row.operator("ya.apply_visibility", text="", icon=icon, depress=not nails_col)
            operator.key = "Nails"
            operator.target = "Hands"
        button_row.operator("ya.apply_nails", text= "Long", depress=long_depress).key = "Long"
        button_row.operator("ya.apply_nails", text= "Short", depress=short_depress).key = "Short"
        button_row.operator("ya.apply_nails", text= "Ballerina", depress=ballerina_depress).key = "Ballerina"
        button_row.operator("ya.apply_nails", text= "Stabbies", depress=stabbies_depress).key = "Stabbies"

        if not section_prop.shape_mq_other_bool:
            row = box.row(align=True)
            split = row.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="Clawsies:")
            button_row = split.row(align=True)
            icon = "HIDE_ON" if clawsies_col else "HIDE_OFF"
            operator = button_row.operator("ya.apply_visibility", text="", icon=icon, depress=not clawsies_col)
            operator.key = "Clawsies"
            operator.target = "Hands"
            operator = button_row.operator("ya.apply_other_option", text= "Straight", depress=clawsies_depress)
            operator.key = "Curved"
            operator.target = "Hands"
            operator = button_row.operator("ya.apply_other_option", text= "Curved", depress=not clawsies_depress)
            operator.key = "Curved"
            operator.target = "Hands"

        box.separator(type="LINE")

        row = box.row(align=True)
        split = row.split(factor=0.25, align=True)
        split.alignment = "RIGHT"
        split.label(text="Feet:")
        button_row = split.row(align=True)
        operator = button_row.operator("ya.apply_other_option", text= "Rue", depress=rue_f_depress)
        operator.key = "Rue"
        operator.target = "Feet"

        if not section_prop.shape_mq_other_bool:
            row = box.row(align=True)
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
        
        row = box.row(align=True)
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

            if active_ob and utils.has_shape_keys(active_ob):
                if not context.scene.ya_props.button_dynamic_view:
                    return active_ob
                else:
                    active_collection = active_ob.users_collection
                    for body_part, collections in body_part_collections.items():
                        if any(bpy.data.collections[coll_name] in active_collection for coll_name in collections):
                            return utils.get_object_from_mesh(body_part) 
                    return active_ob
            else:
                return utils.get_object_from_mesh("Mannequin")


class YATools(Panel):
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


class YAFileManager(Panel):
    bl_idname = "VIEW3D_PT_YA_FileManager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "Import/Export"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        section_prop = scene.ya_props
        button = section_prop.button_export_expand
        
        row = layout.row(align=True)
        split = row.split(factor=1)
        box = split.box()
        sub = box.row(align=True)
        sub.alignment = 'LEFT'

        # EXPORT
        
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        sub.prop(section_prop, "button_export_expand", text="", icon=icon, emboss=False)
        sub.label(text="Export")
        sub.label(icon="EXPORT")

        if button:
            box.separator(factor=0.5, type="LINE")
            self.export_category(box, section_prop)

        button = section_prop.button_import_expand

        row = layout.row(align=True)
        split = row.split(factor=1)
        box = split.box()
        sub = box.row(align=True)
        sub.alignment = 'LEFT'
        
        # IMPORT
        
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        sub.prop(section_prop, "button_import_expand", text="", icon=icon, emboss=False)
        sub.label(text="Import")
        sub.label(icon="IMPORT")

        if button:
            row = layout.row(align=True)
            row.prop(context.scene.ya_props, "export_directory", text="")
            row = layout.row(align=True)
            row.operator("FILE_OT_batch_queue", text="Export FBX")
            row = layout.row()
            row.prop(context.scene.ya_props, "export_body_slot", text="")
            row = layout.row(align=True)
            row.prop(context.scene.ya_props, "export_large_bool", text="Large")
            row.prop(context.scene.ya_props, "export_medium_bool", text="Medium")
            row.prop(context.scene.ya_props, "export_small_bool", text="Small")
            row = layout.row(align=True)
            row.prop(context.scene.ya_props, "export_buff_bool", text="Buff")
            row.prop(context.scene.ya_props, "export_rue_bool", text="Rue")
            row.prop(context.scene.ya_props, "export_piercings_bool", text="Piercings")

        button = section_prop.button_file_expand

        box = layout.box()
        row = box.row(align=True)
        row.alignment = "LEFT"
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row.prop(section_prop, "button_file_expand", text="", icon=icon, emboss=False)
        row.label(text="Modpacker")
        row.label(icon="NEWFOLDER")

        if button:
            box.separator(factor=0.5,type="LINE")
            row = box.row(align=True)
            split = row.split(factor=0.65, align=True)
            icon = "CHECKMARK" if section_prop.consoletools_status == "ConsoleTools Ready!" else "X"
            split.label(text=section_prop.consoletools_status, icon=icon)
            split.operator("ya.file_console_tools", text="Check")
            row.operator("ya.consoletools_dir", icon="FILE_FOLDER", text="")
          
    def export_category(self, box, section_prop):
        row = box.row(align=True)
        row.prop(section_prop, "export_display_directory", text="")
        row.operator("ya.dir_selector", icon="FILE_FOLDER", text="").category = "export"
        row = box.row(align=True)
        col = row.column(align=True)
        col.operator("FILE_OT_simple_export", text="Simple Export")
        col2 = row.column(align=True)
        col2.operator("FILE_OT_batch_queue", text="Batch Export")
        
        
        export_text = "GLTF" if section_prop.export_gltf else "FBX"
        icon = "BLENDER" if section_prop.export_gltf else "VIEW3D"
        col3 = row.column(align=True)
        col3.alignment = "RIGHT"
        col3.prop(section_prop, "export_gltf", text=export_text, icon=icon, invert_checkbox=True)

        box.separator(factor=0.5, type='LINE')

        row = box.row(align=True)
        if section_prop.export_body_slot == "Chest/Legs":
            row.label(text=f"Body Part: Chest")
        else:
            row.label(text=f"Body Part: {section_prop.export_body_slot}")

        
        depress = True if section_prop.export_body_slot == "Chest" else False
        button = row.operator("ya.set_body_part", text="", icon="MOD_CLOTH", depress=depress)
        button.body_part = "Chest" 

        depress = True if section_prop.export_body_slot == "Legs" else False
        button = row.operator("ya.set_body_part", text="", icon="BONE_DATA", depress=depress)
        button.body_part = "Legs"

        depress = True if section_prop.export_body_slot == "Hands" else False
        button = row.operator("ya.set_body_part", text="", icon="VIEW_PAN", depress=depress)
        button.body_part = "Hands"

        depress = True if section_prop.export_body_slot == "Feet" else False
        button = row.operator("ya.set_body_part", text="", icon="VIEW_PERSPECTIVE", depress=depress)
        button.body_part = "Feet"

        depress = True if section_prop.export_body_slot == "Chest/Legs" else False
        button = row.operator("ya.set_body_part", text="", icon="ARMATURE_DATA", depress=depress)
        button.body_part = "Chest/Legs"
            
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
    
            dynamic_column_buttons(3, box, section_prop, labels, category, button_type)

            box.separator(factor=0.5, type="LINE")

            labels = {"Buff": "Buff", "Rue": "Rue", "Piercings": "Piercings"}
    
            dynamic_column_buttons(3, box, section_prop, labels, category, button_type)

            if section_prop.export_body_slot == "Chest/Legs":
                row = box.row(align=True)
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
    
            dynamic_column_buttons(3, box, section_prop, labels, category, button_type)

            row = box.row(align=True)
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
    
            dynamic_column_buttons(3, box, section_prop, labels, category, button_type)  

        # HAND EXPORT  
        
        if section_prop.export_body_slot == "Hands":
            
            category = "Hands"
            labels = {
                "YAB": "YAB", 
                "Rue": "Rue"
                }
    
            dynamic_column_buttons(2, box, section_prop, labels, category, button_type)
            
            box.separator(factor=0.5, type="LINE")

            labels = {
                "Long": "Long", 
                "Short": "Short", 
                "Ballerina": "Ballerina", 
                "Stabbies": "Stabbies" 
                }

            dynamic_column_buttons(2, box, section_prop, labels, category, button_type)

            row = box.row(align=True)
            row.label(text="Clawsies:")

            labels = { 
                "Straight": "Straight", 
                "Curved": "Curved"
                }

            dynamic_column_buttons(2, box, section_prop, labels, category, button_type)

            row = box.row(align=True)

        # FEET EXPORT  
        
        if section_prop.export_body_slot == "Feet":
            
            category = "Feet"
            labels = {
                "YAB": "YAB", 
                "Rue": "Rue", 
                }
    
            dynamic_column_buttons(2, box, section_prop, labels, category, button_type)

            labels = { 
                "Clawsies": "Clawsies"
                }

            dynamic_column_buttons(2, box, section_prop, labels, category, button_type)

  