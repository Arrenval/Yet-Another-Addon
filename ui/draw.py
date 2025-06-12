from typing                 import Literal  
from bpy.types              import UILayout

def get_conditional_icon(condition: bool, invert: bool=False, if_true: str="CHECKMARK", if_false: str="X"):
    if invert:
        return if_true if not condition else if_false
    else:
        return if_true if condition else if_false

def aligned_row(layout: UILayout, label: str, attr: str, prop=None, label_icon: str="NONE", attr_icon: str="NONE", factor:float=0.25, emboss: bool=True, alignment: Literal["RIGHT", "LEFT", "EXPAND", "CENTER"]="RIGHT") -> UILayout:
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
        row.prop(prop, attr, text="", emboss=emboss, icon=attr_icon)
    
    return row

def operator_button(layout:UILayout, operator:str, icon:str, text:str="", attributes:dict={}):
        """Operator as a simple button."""

        op = layout.operator(operator, icon=icon, text=text)
        for attribute, value in attributes.items():
            setattr(op, attribute, value)
