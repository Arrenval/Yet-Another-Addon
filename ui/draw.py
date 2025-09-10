from typing    import Literal  
from bpy.types import UILayout


def show_ui_button(layout: UILayout, prop, attr: str, label: str) -> tuple[bool, UILayout]:
    button = getattr(prop, attr)
    icon = 'TRIA_DOWN' if button else 'TRIA_RIGHT'
    row = layout.row(align=True)
    row.prop(prop, attr, text="", icon=icon, emboss=False)
    row.label(text=label)
    button_row = row.row(align=True)

    return button, button_row
    
def get_conditional_icon(condition: bool, invert: bool=False, if_true: str="CHECKMARK", if_false: str="X") -> str:
    if invert:
        return if_true if not condition else if_false
    else:
        return if_true if condition else if_false

def aligned_row(layout: UILayout, label: str, attr: str, prop=None, prop_str: str="", label_icon: str="NONE", attr_icon: str="NONE", factor:float=0.25, emboss: bool=True, alignment: Literal["RIGHT", "LEFT", "EXPAND", "CENTER"]="RIGHT") -> UILayout:
    """
    Create a row with a label in the main split and a prop or text label in the second split. Returns the row if you want to append extra items.
    Args:
        label: Row name.
        prop: Prop referenced, if an object is not passed, the prop is just treated as a label with text
        container: Object that contains the necessary props.
        factor: Split row ratio.
        alignment: Right aligned by default.
    """
    row = layout.row(align=True)
    split = row.split(factor=factor, align=True)
    split.alignment = alignment
    split.label(text=label, icon=label_icon)

    if prop is None:
        row = split.row(align=True)
        row.label(text=attr)
    else:
        row = split.row(align=True)
        row.prop(prop, attr, text=prop_str, emboss=emboss, icon=attr_icon)
    
    return row

def operator_button(layout:UILayout, operator:str, icon:str, text:str="", attributes:dict={}) -> None:
        """Operator as a simple button."""

        op = layout.operator(operator, icon=icon, text=text)
        for attribute, value in attributes.items():
            setattr(op, attribute, value)

def ui_category_buttons(layout:UILayout, section_prop, options, operator_str: str) -> None:
    row = layout
    for index, (slot, icon) in enumerate(options.items()):
        button = getattr(section_prop, f"{slot.lower()}_category")
        if index == 0:
            row.separator(factor=0.5)
        depress = True if button else False
        operator = row.operator(operator_str, text="", icon=icon, depress=depress, emboss=True if depress else False)
        operator.menu = slot.upper()
        row.separator(factor=2)