from bpy.types      import UILayout
from functools      import partial

from ..draw         import aligned_row, operator_button, centre_header, padding_icons, get_conditional_icon
from ...props       import Armature, SkeletonProps
from ...props.enums import get_racial_name


def draw_sklb(op, layout: UILayout, armature: Armature, props: SkeletonProps) -> None:
    row = layout.row(align=True)
    row.prop(op, "tab", expand=True, text="Test")

    layout.separator(factor=0.5, type='LINE')
    top_row      = layout.row(align=True)
    layout_split = layout.split(factor=0.60, align=True)
    left_col     = layout_split.column(align=False)
    right_col    = layout_split.box().column(align=True)

    if op.tab == 'DATA':
        _draw_data(left_col, right_col, armature, props)
        
    if op.tab == 'LAYER':
        _draw_layer(left_col, right_col, armature, props)
    
    if op.tab == 'MAP':
        top_row.prop(op, "map", expand=True, text="Test")
        if not armature.kaos.mappers:
            top_row.alignment = 'CENTER'
            top_row.label(text="Skeleton has no parents.", icon='INFO')
            operator_button(top_row, "ya.sklb_mapping", 'ADD', "", {"category": "PARENT", "add": True})
            return
        
        if len(armature.kaos.mappers) < 4: 
            operator_button(top_row, "ya.sklb_mapping", 'ADD', "", {"category": "PARENT", "add": True})
        else:
            top_row.label(text="", icon='ADD')

        operator_button(top_row, "ya.sklb_mapping", 'TRASH', "", {"idx": int(op.map), "category": "PARENT", "add": False})
        _draw_mappings(op, left_col, right_col, armature, props)
        
def _draw_data(left_col: UILayout, right_col: UILayout, armature: Armature, props: SkeletonProps) -> None:
    left_col.alignment = 'CENTER'
    data_split = 0.45

    centre_header(left_col.box(), "Skeleton Data", "ARMATURE_DATA")

    row = aligned_row(left_col, "Race:", attr="race_id", prop=armature.kaos, factor=data_split)
    padding_icons(row, 4)
    
    if armature.kaos.mappers:
        left_col.separator(factor=0.5, type='LINE')

    for mapper in armature.kaos.mappers:
        aligned_row(left_col, "Parent:", attr=f"  {get_racial_name(mapper.race_id)}", factor=data_split)

    left_col.separator(factor=0.5, type='LINE')

    aligned_row(left_col, "Bones:", attr=f"  {len(armature.kaos.bone_list)}", factor=data_split)
    aligned_row(left_col, "Layers:", attr=f"  {len(armature.kaos.anim_layers)}", factor=data_split)

    left_col.separator(factor=0.5, type='SPACE')

    centre_header(left_col.box(), "Bone Info", "BONE_DATA")

    if armature.kaos.bone_list:
        selected_bone   = armature.kaos.bone_list[props.bone_idx].name
        selected_parent = armature.bones[selected_bone].parent
        aligned_row(left_col, "Parent:", attr=f"  {selected_parent.name if selected_parent else None}", factor=data_split)

    row = centre_header(right_col, "Bone List", "BONE_DATA")
    padding_icons(row, 1)

    row = right_col.row()
    row.template_list(
            "MESH_UL_YA_BONES", "", 
            armature.kaos, "bone_list", 
            props, "bone_idx", 
            rows=15
            )
    
    col  = row.column(align=True)
    attr = {"up": True, "category": "BONE_LIST"}
    operator_button(col, "ya.sklb_manager", "TRIA_UP", attributes=attr)
    attr = {"up": False, "category": "BONE_LIST"}
    operator_button(col, "ya.sklb_manager", "TRIA_DOWN", attributes=attr)
    
    col.separator(type='SPACE')

    attr = {"category": "BONE_SORT"}
    operator_button(col, "ya.sklb_manager", "SORTSIZE", attributes=attr)

def _draw_layer(left_col: UILayout, right_col: UILayout, armature: Armature, props: SkeletonProps) -> None:
    layer_rows = max(12, len(armature.kaos.anim_layers))

    if armature.kaos.anim_layers:
        layer = armature.kaos.anim_layers[props.layer_idx]

        row = aligned_row(left_col, "  Layer ID:", "id", prop=layer, alignment='LEFT')
        padding_icons(row, 2)
        
        bone_box = left_col.box().row()
        bone_box.template_list(
                "MESH_UL_YA_BONES", "", 
                layer, "bone_list", 
                props, "layer_b_idx", 
                rows=layer_rows,
                )
        
        col = bone_box.column(align=True)
        attr = {"add": True, "category": "LAYER_BONE"}
        operator_button(col, "ya.sklb_manager", "ADD", attributes=attr)
        attr = {"add": False, "category": "LAYER_BONE"}
        operator_button(col, "ya.sklb_manager", "REMOVE", attributes=attr)

    right_col.separator(type='SPACE', factor=0.4)

    row = centre_header(right_col, "Layers", "NODE_COMPOSITING")
    padding_icons(row, 1)

    row = right_col.row()
    row.template_list(
            "MESH_UL_YA_LAYER", "", 
            armature.kaos, "anim_layers", 
            props, "layer_idx", 
            rows=layer_rows
            )
    
    col = row.column(align=True)
    attr = {"add": True, "category": "LAYER"}
    operator_button(col, "ya.sklb_manager", "ADD", attributes=attr)
    attr = {"add": False, "category": "LAYER"}
    operator_button(col, "ya.sklb_manager", "REMOVE", attributes=attr)

def _draw_mappings(op, left_col: UILayout, right_col: UILayout, armature: Armature, props: SkeletonProps) -> None:
    if not armature.kaos.mappers:
        row.label(text="Skeleton has no parents.", icon='ICON')
        return
    
    mapper = armature.kaos.mappers[int(op.map)]
    
    left_col.alignment = 'CENTER'

    centre_header(left_col.box(), "Parent Data", "ARMATURE_DATA")

    row = aligned_row(left_col, "Race:", attr="race_id", prop=mapper)
    padding_icons(row, 7)

    left_col.separator(factor=1, type='LINE')

    aligned_row(left_col, "Transform:", attr="pos", prop=mapper)
    aligned_row(left_col, "Rotation:", attr="rot", prop=mapper)
    aligned_row(left_col, "Scale:", attr="scale", prop=mapper)
    aligned_row(left_col, "Unknown:", attr="unknown", prop=mapper)

    left_col.separator(factor=1, type='LINE')

    map_op = partial(
                operator_button, 
                operator="ya.sklb_mapping",
                icon="NONE",
                text="Generate",
                attributes={"idx": int(op.map), "category": "GEN"}
            )

    row = aligned_row(left_col, "", function=map_op)
    row.prop(mapper, "existing", text="", icon=get_conditional_icon(mapper.existing, if_true='CHECKBOX_HLT', if_false='CHECKBOX_DEHLT'))
    aligned_row(left_col, "New Source:", attr="new_source", prop=mapper)

    left_col.separator(factor=0.5, type='SPACE')

    centre_header(left_col.box(), "Bone Info", "BONE_DATA")

    if mapper.bone_maps:
        bone = mapper.bone_maps[props.map_idx]

        aligned_row(left_col, "Transform:", attr="pos", prop=bone)
        aligned_row(left_col, "Rotation:", attr="rot", prop=bone)
        aligned_row(left_col, "Scale:", attr="scale", prop=bone)
        aligned_row(left_col, "Unknown:", attr="unknown", prop=bone)

    row = centre_header(right_col, "Bone Maps", "BONE_DATA")
    padding_icons(row, 1)

    row = right_col.row()
    row.template_list(
        "MESH_UL_YA_MAPPER", "", 
        mapper, "bone_maps", 
        props, "map_idx", 
        rows=15
        )
    