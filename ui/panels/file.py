import platform

from pathlib        import Path   
from bpy.types      import Panel, UILayout, Context

from ..draw         import aligned_row, get_conditional_icon, operator_button
from ...properties  import BlendModGroup, BlendModOption, CorrectionEntry, ModFileEntry, get_file_properties, get_devkit_properties, get_window_properties, get_devkit_win_props
from ...preferences import get_prefs


class FileManager(Panel):
    bl_idname = "VIEW3D_PT_YA_FileManager"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "XIV Kit"
    bl_label = "File Manager"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 3

    def draw(self, context:Context):
        self.prefs        = get_prefs()
        self.window_props = get_window_properties()
        self.file_props   = get_file_properties()
        self.devkit_props = get_devkit_properties()
        self.devkit_win   = get_devkit_win_props()

        layout = self.layout

        options ={
            "IMPORT": "IMPORT",
            "EXPORT": "EXPORT",
            "MODPACK": "NEWFOLDER",
            }

        box = layout.box()
        row = box.row(align=True)
        row.label(icon=options[self.window_props.file_man_ui])
        row.label(text=f"  {self.window_props.file_man_ui.capitalize()}")
        button_row = row.row(align=True)
        
        button_row.prop(self.window_props, "file_man_ui", expand=True, text="")

        # IMPORT
        button = self.window_props.file_man_ui
        if button == "IMPORT":
            self.draw_import(layout)

        # EXPORT
        if button == "EXPORT":
            self.draw_export(context, layout)

        if button == "MODPACK":
            self.draw_modpack(layout)

    def draw_export(self, context:Context, layout:UILayout):
        row = layout.row(align=True)
        row.prop(self.prefs, "export_display_dir", text="")
        row.operator("ya.dir_selector", icon="FILE_FOLDER", text="").category = "export"

        row = layout.row(align=True)
        row.operator("ya.export", text="Simple Export").mode = "SIMPLE"

        if self.devkit_props:
            row.operator("ya.export", text="Batch Export").mode = "BATCH"
        
        row.separator()

        subrow = row.row()
        subrow.alignment = "RIGHT"
        subrow.scale_x = 0.20
        subrow.prop(self.window_props, "file_format", text=self.window_props.file_format, expand=True)

        if context.space_data.shading.type in ("MATERIAL", "RENDERED"):
            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(
                text=f"{context.space_data.shading.type.capitalize()} shading will drastically increase export times.", 
                icon="ERROR"
                )

        layout.separator(type="LINE")
        
        row = layout.row(align=True)
        icon = get_conditional_icon(self.window_props.keep_shapekeys)
        row.prop(self.window_props, "keep_shapekeys", text="Shape Keys", icon=icon)
        icon = get_conditional_icon(self.window_props.check_tris)
        row.prop(self.window_props, "check_tris", text="Check Tris", icon=icon)
        icon = get_conditional_icon((self.window_props.create_backfaces and self.window_props.check_tris))
        row.prop(self.window_props, "create_backfaces", text="Backfaces", icon=icon, emboss=self.window_props.check_tris)

        layout.separator(type="LINE")

        if self.window_props.file_format == 'MDL':
            row = aligned_row(layout, "XIV Path:", "export_xiv_path", self.window_props)
            row.label(text="", icon=get_conditional_icon(self.window_props.valid_xiv_path))

        aligned_row(layout, "IVCS/YAS:", "remove_yas", self.window_props)
        

        layout.separator(factor=0.1)

        if self.devkit_props:
            box = layout.box()
            row = box.row(align=True)
            if self.window_props.export_body_slot == "Chest & Legs":
                row.label(text=f"Body Part: Chest")
            else:
                row.label(text=f"Body Part: {self.window_props.export_body_slot}")

            row.prop(self.window_props, "export_body_slot", text="" , expand=True)

            # CHEST EXPORT  
        
            button_type = "export"
        
            if self.window_props.export_body_slot == "Chest" or self.window_props.export_body_slot == "Chest & Legs":

                category = "Chest"

                labels = {"YAB": ("YAB", []), "Rue": ("Rue", []), "Lava": ("Lava", []), "Flat": ("Masc", [])}
        
                self.dynamic_column_buttons(len(labels), layout, labels, category, button_type)

                yab = self.devkit_win.export_yab_chest_bool
                rue = self.devkit_win.export_rue_chest_bool and self.window_props.rue_export
                lava = self.devkit_win.export_lava_chest_bool
                masc = self.devkit_win.export_flat_chest_bool

                layout.separator(factor=0.5, type="LINE")

                labels = {"Buff": ("Buff", [yab, rue, lava, masc]), "Piercings": ("Piercings", [yab, rue, lava, masc])}
        
                self.dynamic_column_buttons(len(labels), layout, labels, category, button_type)

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
        
                self.dynamic_column_buttons(3, layout, labels, category, button_type)
                
            # LEG EXPORT  
            
            if self.window_props.export_body_slot == "Legs" or self.window_props.export_body_slot == "Chest & Legs":
                
                category = "Legs"

                if self.window_props.export_body_slot == "Chest & Legs":
                    layout.separator(factor=1, type="LINE")
                    row = layout.row(align=True)
                    row.label(text=f"Body Part: Legs")

                labels = {"YAB": ("YAB", []), "Rue": ("Rue", []), "Lava": ("Lava", []), "Masc": ("Masc", [])}
        
                self.dynamic_column_buttons(len(labels), layout, labels, category, button_type)

                yab = self.devkit_win.export_yab_legs_bool
                rue = self.devkit_win.export_rue_legs_bool
                lava = self.devkit_win.export_lava_legs_bool
                masc = self.devkit_win.export_masc_legs_bool

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
                
                self.dynamic_column_buttons(4, layout, labels, category, button_type)

                layout.separator(factor=0.5, type="LINE")

                labels = {
                    "Small Butt":  ("Small", [yab, rue, lava, masc]),
                    "Pubes":  ("Pubes", [yab, rue, lava, masc])
                }
        
                self.dynamic_column_buttons(3, layout, labels, category, button_type) 

            # HAND EXPORT  
            
            if self.window_props.export_body_slot == "Hands":
                
                category = "Hands"
                labels = {
                    "YAB": ("YAB", []), 
                    "Rue": ("Rue", []),
                    "Lava": ("Lava", []),
                    }
        
                self.dynamic_column_buttons(3, layout, labels, category, button_type)
                
                yab = self.devkit_win.export_yab_hands_bool
                rue = self.devkit_win.export_rue_hands_bool
                lava = self.devkit_win.export_lava_hands_bool

                layout.separator(factor=0.5, type="LINE")

                labels = {
                    "Long": ("Long", [yab, rue, lava]), 
                    "Short": ("Short", [yab, rue, lava]),  
                    "Ballerina": ("Ballerina", [yab, rue, lava]), 
                    "Stabbies": ("Stabbies", [yab, rue, lava]), 
                    }

                self.dynamic_column_buttons(2, layout, labels, category, button_type)
                
                row = layout.row(align=True)
                row.label(text="Clawsies:")

                labels = { 
                    "Straight": ("Straight", [yab, rue, lava]),
                    "Curved": ("Curved", [yab, rue, lava]),
                    }

                self.dynamic_column_buttons(2, layout, labels, category, button_type)

                row = layout.row(align=True)

            # FEET EXPORT  
            
            if self.window_props.export_body_slot == "Feet":
                
                category = "Feet"
                labels = {
                    "YAB": ("YAB", []), 
                    "Rue": ("Rue", []), 
                    }
        
                self.dynamic_column_buttons(2, layout, labels, category, button_type)

                yab = self.devkit_win.export_yab_feet_bool
                rue = self.devkit_win.export_rue_feet_bool

                layout.separator(factor=0.5, type="LINE")

                labels = { 
                    "Clawsies": ("Clawsies", [yab, rue])
                    }

                self.dynamic_column_buttons(2, layout, labels, category, button_type)
        
            layout.separator(factor=0.5, type="LINE")

        if get_devkit_properties():
            box = layout.box()
            row = box.row(align=True)
            row.alignment = "CENTER"
            row.label(text="Batch Options")

            layout.separator(factor=0.1) 

            row = layout.row(align=True)
            col = row.column(align=True)
            
            aligned_row(col, "Export Prefix:", "export_prefix", self.window_props)

            icon = get_conditional_icon(self.window_props.body_names)
            text = "Always" if self.window_props.body_names else "Conditional"
            aligned_row(col, "Body Names:", "body_names", self.window_props, prop_str=text, attr_icon=icon)

            icon = get_conditional_icon(self.window_props.create_subfolder)
            text = "Standalone" if self.window_props.create_subfolder else "Variant"
            aligned_row(col, "Rue Export:", "rue_export", self.window_props, prop_str=text, attr_icon=icon)

            icon = get_conditional_icon(self.window_props.create_subfolder)
            text = "Remove" if self.window_props.create_subfolder else "Keep"
            aligned_row(col, "Subfolder:", "create_subfolder", self.window_props, prop_str=text, attr_icon=icon)

    def draw_import(self, layout:UILayout):
        layout = self.layout
        row = layout.row(align=True)

        if self.window_props.waiting_import:
            row.alignment = "CENTER"
            row.label(text="Waiting for import to complete...", icon='IMPORT')
            
            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(text="Press ESC to cancel", icon='CANCEL')
            return
       
        subrow = row.row(align=True)
        subrow.alignment = "LEFT"
        subrow.scale_x   = 0.9
        subrow.prop(self.prefs, "auto_cleanup", icon=get_conditional_icon(self.prefs.auto_cleanup), text="Auto")

        row.operator("ya.simple_import", text="Import")
        row.operator("ya.simple_cleanup", text="Cleanup")
        
        row.separator()
        
        subrow = row.row()
        subrow.alignment = "RIGHT"
        subrow.scale_x = 0.25
        subrow.prop(self.window_props, "file_format", text=self.window_props.file_format, expand=True)

        box = layout.box()
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Cleanup Options") 

        layout.separator(factor=0.1)  

        row = layout.row(align=True)
        col = row.column(align=True)
        
        aligned_row(col, "Rename:", "rename_import", self.window_props)

        icon = get_conditional_icon(self.prefs.update_material)
        text = 'Update' if self.prefs.update_material else 'Keep'
        aligned_row(col, "Materials:", "update_material", self.prefs, prop_str=text, attr_icon=icon)

        icon = get_conditional_icon(self.prefs.reorder_meshid)
        text = 'Update' if self.prefs.reorder_meshid else 'Keep'
        aligned_row(col, "Mesh ID:", "reorder_meshid", self.prefs, prop_str=text, attr_icon=icon)

        icon = get_conditional_icon(self.prefs.remove_nonmesh)
        text = 'Remove' if self.prefs.remove_nonmesh else 'Keep'
        aligned_row(col, "Non-Mesh:", "remove_nonmesh", self.prefs, prop_str=text, attr_icon=icon)

        aligned_row(col, "Armature:", "import_armature", self.file_props)

    def draw_modpack(self, layout:UILayout):
        self.checked_folders: dict[Path, list[Path] | False] = {}
        option_indent: float  = 0.08

        self.get_file_stats()

        row = aligned_row(layout, "Output:", "modpack_output_display_dir", self.prefs)
        row.operator("ya.modpack_dir_selector", icon="FILE_FOLDER", text="").category = "OUTPUT_PMP" 

        box = layout.box()
        row = box.row(align=True)
        
        op_atr = {
            "category": "ALL",
            "group":    0,
            }
            
        operator_button(row, "ya.mod_packager", icon="FILE_PARENT", attributes=op_atr)
        row.prop(self.window_props, "modpack_replace", text="New", icon="FILE_NEW", invert_checkbox=True)
        row.prop(self.window_props, "modpack_replace", text="Update", icon="CURRENT_FILE",)

        op_atr = {
            "category": "GROUP",
            "group":    0,
            "option":   0
            }
            
        operator_button(row, "ya.modpack_manager", icon="ADD", attributes=op_atr)
        operator_button(row, "ya.pmp_selector", icon="FILE")

        box.separator(factor=0.5,type="LINE")

        row = box.row(align=True)
        split = row.split(factor=0.25)
        col2 = split.column(align=True)
        col2.label(text="Ver.")
        col2.prop(self.window_props, "modpack_version", text="")

        col = split.column(align=True)
        col.label(text="Modpack:")
        col.prop(self.window_props, "modpack_display_dir", text="", emboss=True)

        split2 = row.split()
        col3 = split2.column(align=True)
        col3.alignment = "CENTER"
        col3.label(text="")
        col3.prop(self.window_props, "modpack_author", text="by", emboss=True)

        self.status_info(box)

        for group_idx, group in enumerate(self.window_props.pmp_mod_groups):
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
                    row = aligned_row(columns[1], "Description:", "description", option)

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
                    aligned_row(columns[1], "Options:", "names", correction)

                    columns[1].separator(factor=2,type="LINE")

                    self.entry_container(columns[1], correction, group_idx, correction_idx)

    def status_info(self, layout:UILayout):
        if self.window_props.modpack_replace and Path(self.window_props.modpack_dir).is_file():
            layout.separator(factor=0.5,type="LINE")
            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(text=f"{Path(self.window_props.modpack_dir).name} is loaded.", icon="INFO")

        elif self.window_props.modpack_replace:
            layout.separator(factor=0.5,type="LINE")
            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(text="No modpack is loaded.", icon="INFO")

        elif not self.window_props.modpack_replace and (Path(self.prefs.modpack_output_dir) / Path(self.window_props.modpack_display_dir + ".pmp")).is_file():
            layout.separator(factor=0.5,type="LINE")
            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(text=f"{self.window_props.modpack_display_dir + '.pmp'} already exists!", icon="ERROR")

        layout.separator(factor=0.1,type="SPACE")

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
            
        operator_button(row, "ya.mod_packager", icon="FILE_PARENT", attributes=op_atr)

        op_atr = {
        "group":    group_idx,
        "format":   "MODPACK",
        }
        
        operator_button(row, "ya.preset_manager", icon="FILE_TICK", attributes=op_atr)

        row.prop(group, "name", text="")
        subrow = row.row(align=True)
        subrow.scale_x = 0.4
        subrow.prop(group, "priority", text="")
       
        row = columns[2].row(align=True)
        row.alignment = "RIGHT"
        row.label(icon="BLANK1")

        row.prop(group, "use_folder", text="", icon="NEWFOLDER", emboss=True)
        
        if group.use_folder and group.group_type != "Combining":
            row.label(icon="ADD", text="")
        else:
            op_atr = {
            "category": "OPTION",
            "group":    group_idx,
            "option":   0
            }
            
            operator_button(row, "ya.modpack_manager", icon="ADD", attributes=op_atr)

        op_atr = {
        "delete":   True,
        "category": "GROUP",
        "group":    group_idx,
        }
        
        operator_button(row, "ya.modpack_manager", icon="TRASH", attributes=op_atr)

    def group_container(self, layout:UILayout, group:BlendModGroup, idx:int):
            enum_width = 0.6
            text = "Create:" if group.idx == "New" else "Replace:"
            row = aligned_row(layout, text, "idx", group)

            subrow = row.row(align=True)
            subrow.scale_x = enum_width
            subrow.prop(group, "page", text="")

            row = aligned_row(layout, "Description:", "description", group)
        
            subrow = row.row(align=True)
            subrow.scale_x = enum_width
            subrow.prop(group, "group_type", text="")

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
        row.label(icon="BLANK1")

        op_atr = {
            "category": "ENTRY",
            "group":    group_idx,
            "option":   option_idx
            }
            
        operator_button(row, "ya.modpack_manager", icon="ADD", attributes=op_atr)
        
        op_atr = {
            "delete":   True,
            "category": "OPTION",
            "group":    group_idx,
            "option":   option_idx
            }
            
        operator_button(row, "ya.modpack_manager", icon="TRASH", attributes=op_atr)
    
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
            
        operator_button(row, "ya.modpack_manager", icon="ADD", attributes=op_atr)
        
        op_atr = {
            "delete":   True,
            "category": "COMBI",
            "group":    group_idx,
            "option":   option_idx
            }
            
        operator_button(row, "ya.modpack_manager", icon="TRASH", attributes=op_atr)

    def folder_container(self, layout:UILayout, container:BlendModGroup, group_idx:int, option_idx:int):
        layout.separator(factor=0.1,type="SPACE")

        path = str(Path(*Path(container.folder_path).parts[-3:])) if Path(container.folder_path).is_dir else container.folder_path
        row = aligned_row(layout, "Folder:", path)

        op_atr = {
            "category": "GROUP",
            "group": group_idx,
            }

        operator_button(row, "ya.modpack_dir_selector", icon="FILE_FOLDER", attributes=op_atr)

        if len(container.get_subfolder()) > 1:
            row = aligned_row(layout, "Subfolder:", "subfolder", prop=container, factor=0.5)
            row.label(icon="FOLDER_REDIRECT")

        if container.use_folder:
            row = aligned_row(layout, "XIV Path:", "game_path", container)
            icon = "CHECKMARK" if container.valid_path else "X"
            row.label(icon=icon)
            self.xiv_path_category(layout, container, "GROUP", group_idx, option_idx)
            folder = container.final_folder()
        
            if self.checked_folders[folder]:
                layout.separator(factor=2,type="LINE")

                button = container.show_folder
                icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
                row = layout.row(align=True)
                row.alignment = "LEFT"
                row.prop(container, "show_folder", text="Option Preview", icon=icon, emboss=False)

                if button:
                    split_factor = 0.8
                    layout.separator(factor=2,type="LINE")
                    
                    row = layout.row(align=True)
                    row.label(icon="BLANK1")
                    split = row.split(factor=split_factor)
                    split.label(text="Name:")
                    split.label(text="Type:")

                    for file in self.checked_folders[folder]:
                        if file.suffix not in self.file_props.GAME_SUFFIX:
                            continue
                        row = layout.row(align=True)
                        row.label(icon="BLANK1")
                        split = row.split(factor=split_factor)
                        split.label(text=file.stem)
                        split.label(text=file.suffix)
            else:
                layout.separator(factor=2,type="LINE")

                row = layout.row(align=True)
                row.alignment = "CENTER"
                row.label(text="No supported game files in folder.", icon="INFO")
        
        layout.separator(factor=0.1,type="SPACE")

    def entry_container(self, layout:UILayout, container:BlendModOption | CorrectionEntry, group_idx:int, option_idx:int):
         
        for file_idx, file in enumerate(container.file_entries):
            category = "FILE_ENTRY" if isinstance(container, BlendModOption) else "FILE_COMBI"
            row = aligned_row(layout, "File:", Path(file.file_path).name)

            op_atr = {
                "category": category,
                "group": group_idx,
                "option": option_idx,
                "entry": file_idx,
            }
    
            operator_button(row, "ya.modpack_file_selector", icon="FILE_FOLDER", attributes=op_atr)
            
            row = aligned_row(layout, "XIV Path:", "game_path", file)
            icon = "CHECKMARK" if file.valid_path else "X"
            row.label(icon=icon)
            self.xiv_path_category(layout, file, category, group_idx, option_idx, file_idx)

            layout.separator(factor=1.5,type="LINE")

        for entry_idx, entry in enumerate(container.meta_entries):

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

            slot_scale = 0.6
            name_scale = 0.8
            model_scale = 0.6
            
            if entry.type == "SHP":
                race_scale =  0.6
            else:
                race_scale =  0.85

            subrow = row.row(align=True)
            subrow.scale_x = slot_scale
            subrow.prop(entry, "slot", text="")

            subrow = row.row(align=True)
            subrow.scale_x = name_scale
            subrow.prop(entry, "manip_ref", text="")

            subrow = row.row(align=True)
            subrow.scale_x = model_scale
            subrow.prop(entry, "model_id", text="")

            if entry.type == "SHP":
                subrow = row.row(align=True)
                subrow.scale_x = 0.6
                subrow.prop(entry, "connector_condition", text="")

            subrow = row.row(align=True)
            subrow.scale_x = race_scale
            subrow.prop(entry, "race_condition", text="")

            row.prop(entry, "enable", text="", icon= "CHECKMARK" if entry.enable else "X")
            
            op_atr = {
                "delete":   True,
                "category": category,
                "group":    group_idx,
                "option":   option_idx,
                "entry":    entry_idx,
            }
    
            operator_button(row, "ya.modpack_manager", icon="TRASH", attributes=op_atr)

            layout.separator(factor=1.5,type="LINE")
    
    def get_file_stats(self):
        folders = [(group.final_folder(), group) for group in self.window_props.pmp_mod_groups if group.use_folder]
        for folder, group in folders:
            if folder not in self.checked_folders:
                self.checked_folders[folder] = group.get_folder_content()

    def dynamic_column_buttons(self, columns, box:UILayout, labels, category, button_type):
        if category == "Chest":
            yab = self.devkit_win.export_yab_chest_bool
            rue = self.devkit_win.export_rue_chest_bool and self.window_props.rue_export
            lava = self.devkit_win.export_lava_chest_bool

        row = box.row(align=True)

        columns_list = [row.column(align=True) for _ in range(columns)]

        for index, (size, (name, bodies)) in enumerate(labels.items()):
            size_lower = size.lower().replace(' ', "_")
            category_lower = category.lower()
            emboss = True if not bodies or any(body is True for body in bodies) else False

            prop_name = f"{button_type}_{size_lower}_{category_lower}_bool"

            if hasattr(self.devkit_win, prop_name):
                icon = 'CHECKMARK' if getattr(self.devkit_win, prop_name) and emboss else 'PANEL_CLOSE'
                
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

                columns_list[col_index].prop(self.devkit_win, prop_name, text=name, icon=icon, emboss=emboss)
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

    def operator_button(layout:UILayout, operator:str, icon:str, text:str="", attributes:dict={}):
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
        

CLASSES = [
    FileManager
]   