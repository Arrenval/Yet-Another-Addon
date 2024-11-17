import bpy
import ya_utils as utils
import ya_operators as operators

from bpy.props import StringProperty, BoolProperty, EnumProperty

def dynamic_column_buttons(columns, layout, section_prop, labels, category, button_type):
    box = layout.box()
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


class VIEW3D_PT_YA_Overview(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "Yet Another Overview"
    bl_order = 0

    # Draws static shape key list in viewport.
    def draw(self, context):
        mq = utils.get_object_from_mesh("Mannequin")
        torso = utils.get_object_from_mesh("Torso")
        legs = utils.get_object_from_mesh("Waist")
        hands = utils.get_object_from_mesh("Hands")
        feet = utils.get_object_from_mesh("Feet")

        ob = self.collection_context(context)
        key = ob.data.shape_keys
        layout = self.layout
        LabelName = ob.data.name
        scene = context.scene
        section_prop = scene.ya_props

        button_adv = section_prop.button_advanced_expand

        # SHAPE MENUS
        
        if button_adv:
            box = layout.box()
            row = box.row(align=True)
            row.label(text=f"{LabelName}:")
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
            

            button = section_prop.button_chest_shapes

            box = layout.box()
            row = box.row(align=True)
            col = row.column(align=True)
            
            icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
            col.prop(section_prop, "button_chest_shapes", text="", icon=icon, emboss=False)
            
            col2 = row.column(align=True)
            col2.label(text="Chest")
            
            col3 = row.column(align=True)
            col3.prop(section_prop, "shape_mq_chest_bool", text="", icon="ARMATURE_DATA")

            col4 = row.column(align=True)
            col4.prop(section_prop, "button_advanced_expand", text="", icon="TOOL_SETTINGS")

            if button:
                if section_prop.shape_mq_chest_bool:
                    target = mq
                    key_target = "mq"
                else:
                    target = torso
                    key_target = "torso"

                medium_mute = target.data.shape_keys.key_blocks["MEDIUM ----------------------------"].mute
                small_mute = target.data.shape_keys.key_blocks["SMALL ------------------------------"].mute
                large_depress = True if small_mute and medium_mute else False
                medium_depress = True if not medium_mute and small_mute else False
                small_depress = True if not small_mute and medium_mute else False

                box = layout.box()
                row = box.row(align=True)
                row.operator("MESH_OT_apply_size_category_large", text= "Large", depress=large_depress)
                row.operator("MESH_OT_apply_size_category_medium", text= "Medium", depress=medium_depress)
                row.operator("MESH_OT_apply_size_category_small", text= "Small", depress=small_depress)

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
                col3.operator("MESH_OT_apply_shapes", text= "Apply Shape")
               

        # YAS MENU

        button = section_prop.button_yas_expand                          

        box = layout.box()
        row = box.row(align=True)
        row.alignment = 'LEFT'
        
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        row.prop(section_prop, "button_yas_expand", text="", icon=icon, emboss=False)
        row.label(text="Yet Another Skeleton")

        if button:
            yas_torso = torso.modifiers["YAS Toggle"].show_viewport
            yas_mq = mq.modifiers["YAS Toggle"].show_viewport
            yas_legs = legs.modifiers["YAS Toggle"].show_viewport
            yas_hands = hands.modifiers["YAS Toggle"].show_viewport
            yas_feet = feet.modifiers["YAS Toggle"].show_viewport

            depress = True if yas_torso else False

            row = layout.row(align=True)
            box = row.box()
            col2 = box.column(align=True)
            col2.label(text="Legs:")
            icon = 'CHECKMARK' if legs.toggle_yas else 'PANEL_CLOSE'
            col2.prop(legs, "toggle_yas", text="YAS", icon=icon)
            icon = 'CHECKMARK' if legs.toggle_yas_gen else 'PANEL_CLOSE'
            col2.prop(legs, "toggle_yas_gen", text="Genitalia", icon=icon)

            box = row.box()
            col = box.column(align=True)
            col.label(text="Mannequin:")
            icon = 'CHECKMARK' if mq.toggle_yas else 'PANEL_CLOSE'
            col.prop(mq, "toggle_yas", text="YAS", icon=icon)
            icon = 'CHECKMARK' if mq.toggle_yas_gen else 'PANEL_CLOSE'
            col.prop(mq, "toggle_yas_gen", text="Genitalia", icon=icon)

            box = layout.box()
            row = box.row(align=True)
            depress = True if yas_torso else False
            icon = 'CHECKMARK' if torso.toggle_yas else 'PANEL_CLOSE'
            row.prop(torso, "toggle_yas", text="Chest", icon=icon)
            icon = 'CHECKMARK' if hands.toggle_yas else 'PANEL_CLOSE'
            row.prop(hands, "toggle_yas", text="Hands", icon=icon)
            icon = 'CHECKMARK' if feet.toggle_yas else 'PANEL_CLOSE'
            row.prop(feet, "toggle_yas", text="Feet", icon=icon)
            

            

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


class VIEW3D_PT_YA_Tools(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "Weights"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 1
    
    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator("mesh.remove_empty_vgroups", text= "Remove Empty Groups")


class VIEW3D_PT_YA_FileManager(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "Import/Export"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 2

    # EXPORT

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
        
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        sub.prop(section_prop, "button_export_expand", text="", icon=icon, emboss=False)
        sub.label(text="Export")
        sub.label(icon="EXPORT")

        if button:
            row = layout.row(align=True)
            row.prop(context.scene.ya_props, "export_display_directory", text="")
            row = layout.row(align=True)
            col = row.column(align=True)
            col.operator("FILE_OT_simple_export", text="Simple Export")
            col2 = row.column(align=True)
            col2.operator("FILE_OT_batch_export", text="Batch Export")
            
            
            export_text = "GLTF" if section_prop.export_gltf else "FBX"
            icon = "BLENDER" if section_prop.export_gltf else "VIEW3D"
            col3 = row.column(align=True)
            col3.alignment = "RIGHT"
            col3.prop(section_prop, "export_gltf", text=export_text, icon=icon, invert_checkbox=True)

            layout.separator(factor=2, type='LINE')

            row = layout.row(align=True)
            if section_prop.export_body_slot == "Chest/Legs":
                row.label(text=f"Body Part: Chest")
            else:
                row.label(text=f"Body Part: {section_prop.export_body_slot}")

            
            depress = True if section_prop.export_body_slot == "Chest" else False
            button = row.operator("object.set_body_part", text="", icon="MOD_CLOTH", depress=depress)
            button.body_part = "Chest" 

            depress = True if section_prop.export_body_slot == "Legs" else False
            button = row.operator("object.set_body_part", text="", icon="BONE_DATA", depress=depress)
            button.body_part = "Legs"

            depress = True if section_prop.export_body_slot == "Hands" else False
            button = row.operator("object.set_body_part", text="", icon="VIEW_PAN", depress=depress)
            button.body_part = "Hands"

            depress = True if section_prop.export_body_slot == "Feet" else False
            button = row.operator("object.set_body_part", text="", icon="VIEW_PERSPECTIVE", depress=depress)
            button.body_part = "Feet"

            depress = True if section_prop.export_body_slot == "Chest/Legs" else False
            button = row.operator("object.set_body_part", text="", icon="ARMATURE_DATA", depress=depress)
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
        
                dynamic_column_buttons(3, layout, section_prop, labels, category, button_type)

                layout.separator(factor=2, type="LINE")

                labels = {"Buff": "Buff", "Rue": "Rue", "Piercings": "Piercings"}
        
                dynamic_column_buttons(3, layout, section_prop, labels, category, button_type)

                if section_prop.export_body_slot == "Chest/Legs":
                    row = layout.row(align=True)
                    row.label(text=f"Body Part: Legs")
                else:
                    layout.separator(factor=1,)
              
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
        
                dynamic_column_buttons(3, layout, section_prop, labels, category, button_type)

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
        
                dynamic_column_buttons(3, layout, section_prop, labels, category, button_type)  

                layout.separator(factor=1,)
  
            # HAND EXPORT  
            
            if section_prop.export_body_slot == "Hands":
                
                category = "Hands"
                labels = {
                    "YAB": "YAB", 
                    "Rue": "Rue"
                    }
        
                dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)
                
                layout.separator(factor=2, type="LINE")

                labels = {
                    "Long": "Long", 
                    "Short": "Short", 
                    "Ballerina": "Ballerina", 
                    "Stabbies": "Stabbies" 
                    }

                dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)

                row = layout.row(align=True)
                row.label(text="Clawsies:")

                labels = { 
                    "Straight": "Straight", 
                    "Curved": "Curved"
                    }

                dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)

                row = layout.row(align=True)

            # FEET EXPORT  
            
            if section_prop.export_body_slot == "Feet":
                
                category = "Feet"
                labels = {
                    "YAB": "YAB", 
                    "Rue": "Rue", 
                    }
        
                dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)

                labels = { 
                    "Clawsies": "Clawsies"
                    }

                dynamic_column_buttons(2, layout, section_prop, labels, category, button_type)

                layout.separator(factor=1)   

        
        #IMPORT

        button = section_prop.button_import_expand

        row = layout.row(align=True)
        split = row.split(factor=1)
        box = split.box()
        sub = box.row(align=True)
        sub.alignment = 'LEFT'
        
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        sub.prop(section_prop, "button_import_expand", text="", icon=icon, emboss=False)
        sub.label(text="Import")
        sub.label(icon="IMPORT")

        if button:
            row = layout.row(align=True)
            row.prop(context.scene.ya_props, "export_directory", text="")
            row = layout.row(align=True)
            row.operator("FILE_OT_batch_export", text="Export FBX")
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

        row = layout.row(align=True)
        split = row.split(factor=1)
        box = split.box()
        sub = box.row(align=True)
        sub.alignment = 'LEFT'
        
        icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
        sub.prop(section_prop, "button_file_expand", text="", icon=icon, emboss=False)
        sub.label(text="Modpacker")
        sub.label(icon="NEWFOLDER")

        if button:
            row = layout.row(align=True)
            row.prop(context.scene.ya_props, "export_directory", text="")
            row = layout.row(align=True)
            row.operator("FILE_OT_batch_export", text="Export FBX")
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


            
    



        
