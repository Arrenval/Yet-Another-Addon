import os
import bpy

from pathlib       import Path
from bpy.types     import Panel, Operator, UILayout
from bpy.props     import StringProperty

class DirSelector(Operator):
    bl_idname = "ya.dir_selector"
    bl_label = "Select Folder"
    bl_description = "Select file or directory. Hold Alt to open the folder"
    
    directory: StringProperty() # type: ignore
    category: StringProperty() # type: ignore

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
        # Update the export_body_part with the selected body part
        context.scene.file_props.export_body_slot = self.body_part
        return {'FINISHED'}
    
class PanelCategory(Operator):
    bl_idname = "ya.set_ui"
    bl_label = "Select the menu."
    bl_description = "Changes the panel menu"

    overview: StringProperty() # type: ignore
    panel: StringProperty() # type: ignore

    def execute(self, context):
        match self.panel:
            case "file":
                context.scene.file_props.file_man_ui = self.overview
            case "outfit":
                context.scene.outfit_props.outfit_ui = self.overview
        return {'FINISHED'}

class OutfitStudio(Panel):
    bl_idname = "VIEW3D_PT_YA_OutfitStudio"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "Outfit Studio"
    bl_order = 1

    def draw(self, context):
        if hasattr(context.scene, "devkit_props"):
            devkit_prop = context.scene.devkit_props

        section_prop = context.scene.outfit_props
        layout = self.layout
        button_type = "shpk"

        options ={
            "Overview": "INFO",
            "Shapes": "SHAPEKEY_DATA",
            "Mesh": "OUTLINER_OB_MESH",
            "Weights": "WPAINT_HLT",
            }

        row = layout.row()
        colui = row.column()
        self.ui_category_buttons(colui, section_prop, "outfit_ui", options, "outfit")
        box = row.box()
        
        if section_prop.outfit_ui == "Overview":
            box.label(icon="INFO", text="Work in progress...")
        
            
        if section_prop.outfit_ui == "Shapes":
            row = box.row(align=True)
            row.alignment = "CENTER"
            row.label(text="Shapes")

            col = box.column(align=True)
            split = col.split(factor=0.25, align=True)
            split.alignment = "RIGHT"
            split.label(text="Source:")
            split.prop(section_prop, "shape_key_source", text="", icon="SHAPEKEY_DATA")
            col.separator(type="LINE", factor=2)

            if not hasattr(context.scene, "devkit_props") and section_prop.shape_key_source != "Selected":
                row = col.row(align=True)
                row.alignment = "CENTER"
                row.label(text="Yet Another Devkit required.", icon="INFO")

            else:
                if section_prop.shape_key_source == "Chest":
                    row = col.row(align=True)
                    row.alignment = "CENTER"
                    row.prop(section_prop, "sub_shape_keys", text="Include Sub Keys")
                    row.prop(section_prop, "add_shrinkwrap", text="Shrinkwrap")
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
                    row.prop(devkit_prop, "key_pushup_large_ctrl", text="Push-Up Adjustment:")
                    ctrl = bpy.data.objects["Chest"].visible_get(view_layer=context.view_layer)
                    icon = "HIDE_ON" if not ctrl else "HIDE_OFF"
                    adj_op = row.operator("yakit.apply_visibility", text="", icon=icon, depress=ctrl)
                    adj_op.target = "Shape"
                    adj_op.key = ""

                    self.dynamic_column_buttons(2, col, devkit_prop, labels, slot, button_type)
                    
                    col.separator(type="LINE", factor=2)

                if section_prop.shape_key_source == "Legs":

                    slot = "Legs"
                    labels = {    
                            "Skull":      "Skull Crushers",                   
                            "Mini":       "Mini",                 
                            "Rue":        "Rue",           
                            "Alt Hips":   "Alt Hips",
                            "Small Butt": "Small Butt",         
                            "Soft Butt":  "Soft Butt",
                        }
                    
                    self.dynamic_column_buttons(2, col, devkit_prop, labels, slot, button_type)
                    col.separator(type="LINE", factor=2)

                # box.separator(type="LINE", factor=0.5)

                row = col.row()
                row.alignment = "CENTER"
                col = row.column(align=True)
                row = col.row(align=True)
                col.operator("ya.transfer_shape_keys", text="Transfer")

        if section_prop.outfit_ui == "Mesh":
            row = box.column(align=True)
            row.label(text="Backfaces", icon="REMOVE")
            col = box.column(align=True)
            sub = col.row(align=True)
            sub.operator("ya.tag_backfaces", text=f"   ADD ").preset = 'ADD'
            sub.operator("ya.create_backfaces", text=f"CREATE")
            sub.operator("ya.tag_backfaces", text="REMOVE").preset = 'REMOVE'

        if section_prop.outfit_ui == "Weights":
            row = box.row()
            row.alignment = "CENTER"
            col = row.column(align=True)
            col.operator("ya.remove_empty_vgroups", text= "Remove Empty Groups")

    def dynamic_column_buttons(self, columns, layout, section_prop, labels, slot, button_type):
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
                print(f"{name} has no assigned property!")
        return layout  

    def ui_category_buttons(self, layout, section_prop, prop, options, panel:str):
        row = layout
        ui_selector = getattr(section_prop, prop)

        for index, (slot, icon) in enumerate(options.items()):
            if index == 0:
                row.separator(factor=0.5)
            depress = True if ui_selector == slot else False
            operator = row.operator("ya.set_ui", text="", icon=icon, depress=depress, emboss=True if depress else False)
            operator.overview = slot
            operator.panel = panel
            row.separator(factor=2)

class FileManager(Panel):
    bl_idname = "VIEW3D_PT_YA_FileManager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Devkit"
    bl_label = "File Manager"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 3

    def draw(self, context):
        section_prop = context.scene.file_props
        self.outfit_prop  = context.scene.outfit_props
        if hasattr(context.scene, "devkit_props"):
            self.devkit_props = context.scene.devkit_props
        layout = self.layout

        options ={
            "Import": "IMPORT",
            "Export": "EXPORT",
            "Modpack": "NEWFOLDER",
            }

        box = layout.box()
        row = box.row(align=True)
        row.label(icon=options[section_prop.file_man_ui])
        row.label(text=f"  {section_prop.file_man_ui}")
        button_row = row.row(align=True)
        
        self.ui_category_buttons(button_row, section_prop, "file_man_ui", options, "file")

        # IMPORT
        button = section_prop.file_man_ui
        # box = self.dropdown_header(button, section_prop, "button_import_expand", "Import", "IMPORT")
        if button == "Import":
            self.draw_import(layout, section_prop)

        # EXPORT
        # box = self.dropdown_header(button, section_prop, "button_export_expand", "Export", "EXPORT")
        if button == "Export":
            self.draw_export(context, layout, section_prop)

        if button == "Modpack":
                section_prop = context.scene.file_props
                self.draw_modpack(layout, section_prop, devkit=True)

    def draw_export(self, context, layout:UILayout, section_prop):
        global is_exporting

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

                labels = {"Buff": "Buff", "Rue": "Rue", "Piercings": "Piercings"}
        
                self.dynamic_column_buttons(3, layout, self.devkit_props, labels, category, button_type)


                layout.separator(factor=0.5, type="LINE")
                
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
        
                self.dynamic_column_buttons(3, layout, self.devkit_props, labels, category, button_type)
                
            # LEG EXPORT  
            
            if section_prop.export_body_slot == "Legs" or section_prop.export_body_slot == "Chest & Legs":
                category = "Legs"

                if section_prop.export_body_slot == "Chest & Legs":
                    layout.separator(factor=1, type="LINE")
                    row = layout.row(align=True)
                    row.label(text=f"Body Part: Legs")

                labels = {
                    "Gen A":  "Gen A",
                    "Gen B":  "Gen B", 
                    "Gen C":  "Gen C",
                    "Gen SFW":  "Gen SFW",
                    "Melon": "Melon",
                    "Skull": "Skull",  
                    "Mini": "Mini",
                    "Pubes":  "Pubes"
                }
                
                self.dynamic_column_buttons(4, layout, self.devkit_props, labels, category, button_type)

                layout.separator(factor=0.5, type="LINE")

                labels = {
                    "Small Butt": "Small Butt",
                    "Rue": "Rue",
                    "Soft Butt": "Soft Butt", 
                    "Hip Dips":  "Hip Dips",
                }
        
                self.dynamic_column_buttons(2, layout, self.devkit_props, labels, category, button_type) 

            # HAND EXPORT  
            
            if section_prop.export_body_slot == "Hands":
                
                category = "Hands"
                labels = {
                    "YAB": "YAB", 
                    "Rue": "Rue"
                    }
        
                self.dynamic_column_buttons(2, layout, self.devkit_props, labels, category, button_type)
                
                layout.separator(factor=0.5, type="LINE")

                labels = {
                    "Long": "Long", 
                    "Short": "Short", 
                    "Ballerina": "Ballerina", 
                    "Stabbies": "Stabbies" 
                    }

                self.dynamic_column_buttons(2, layout, self.devkit_props, labels, category, button_type)

                row = layout.row(align=True)
                row.label(text="Clawsies:")

                labels = { 
                    "Straight": "Straight", 
                    "Curved": "Curved"
                    }

                self.dynamic_column_buttons(2, layout, self.devkit_props, labels, category, button_type)

                row = layout.row(align=True)

            # FEET EXPORT  
            
            if section_prop.export_body_slot == "Feet":
                
                category = "Feet"
                labels = {
                    "YAB": "YAB", 
                    "Rue": "Rue", 
                    }
        
                self.dynamic_column_buttons(2, layout, self.devkit_props, labels, category, button_type)

                layout.separator(factor=0.5, type="LINE")

                labels = { 
                    "Clawsies": "Clawsies"
                    }

                self.dynamic_column_buttons(2, layout, self.devkit_props, labels, category, button_type)
        
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
        if hasattr(bpy.context.scene, "devkit_props"):
            col.label(text="Fix Parenting:")
        col.label(text="Update Material:")
        col.label(text="Rename:")
        
        col2 = split.column(align=True)
        col2.alignment = "RIGHT"
        if hasattr(bpy.context.scene, "devkit_props"):
            icon = 'CHECKMARK' if section_prop.fix_parent else 'PANEL_CLOSE'
            text = 'Enabled' if section_prop.fix_parent else 'Disabled'
            col2.prop(section_prop, "fix_parent", text=text, icon=icon)
        icon = 'CHECKMARK' if section_prop.update_material else 'PANEL_CLOSE'
        text = 'Enabled' if section_prop.update_material else 'Disabled'
        col2.prop(section_prop, "update_material", text=text, icon=icon)
        col2.prop(section_prop, "rename_import", text="")

        layout.separator(factor=0.5)

    def draw_modpack(self, layout:UILayout, section_prop, devkit=False):
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

        if devkit:
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

            split2 = row.split(factor=0.8)
            col3 = split2.column()
            col3.alignment = "CENTER"
            col3.operator("ya.pmp_selector", icon="FILE_FOLDER", text="")
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
            
            split2 = row.split(factor=0.8)
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

            split2 = row.split(factor=0.8)
            col = split2.column(align=True)
            col.alignment = "CENTER"
            col.prop(section_prop, "mod_group_type", text="")



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

    def dynamic_column_buttons(self, columns, box:UILayout, section_prop, labels, category, button_type):
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

    def ui_category_buttons(self, layout:UILayout, section_prop, prop, options, panel:str):
            row = layout
            ui_selector = getattr(section_prop, prop)

            for slot, icon in options.items():
                depress = True if ui_selector == slot else False
                operator = row.operator("ya.set_ui", text="", icon=icon, depress=depress)
                operator.overview = slot
                operator.panel = panel


CLASSES = [
    DirSelector,
    BodyPartSlot,
    PanelCategory,
    OutfitStudio,
    FileManager
]