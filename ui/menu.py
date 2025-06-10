def menu_emptyvgroup_append(self, context):
    self.layout.separator(type="LINE")
    self.layout.operator("ya.add_yas_vgroups", text= "Add YAS Groups")
    self.layout.separator(type="LINE")
    self.layout.operator("ya.remove_empty_vgroups", text="Remove Empty Vertex Groups")
    self.layout.operator("ya.remove_select_vgroups", text= "Remove Selected and Adjust Parent").preset = "MENU"