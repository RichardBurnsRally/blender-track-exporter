from typing import Any, List

import bpy

from ..types import SurfaceAge, SurfaceType
from . import editor
from .clipboard import GLOBAL_PHYSICAL_MATERIAL_CLIPBOARD
from .properties import RBRAutoWetness


class RBR_PT_material_maps_panel(bpy.types.Panel):
    bl_idname = "RBR_PT_material_maps_panel"
    bl_label = "RBR Material Maps"
    bl_category = "Tool"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return editor.is_editing(context)

    def draw(self, context: bpy.types.Context) -> None:
        from ..shaders.texture import tree_name_to_texture_name

        tree = editor.editing_tree(context)
        if tree is None or context.scene is None:
            return
        internal: Any = tree.nodes["internal"]
        ui = self.layout
        ui.label(text=tree_name_to_texture_name(tree) or "", icon="TEXTURE")

        shown = editor.active_condition(context, internal)
        st, sa = shown
        undefined = editor.undefined_conditions(internal)
        ages = list(SurfaceAge) if internal.is_road_surface else [SurfaceAge.NEW]

        row = ui.box().row()
        row.alignment = "LEFT"
        row.operator("rbr.material_map_set_fallback", text="Set Fallback")
        row.label(text=internal.fallback_materials.get_condition(st, sa).pretty())
        ui.separator(factor=0.5)

        # One box per age: automatic conditions only follow dry of their age.
        grid = ui.column(align=True)
        header = inset_split(grid)
        header.label(text="")
        for surface_type, name_row in zip(SurfaceType, surface_columns(header)):
            name_row.alignment = "CENTER"
            name_row.label(text=surface_type.pretty())
        for i, age in enumerate(ages):
            if i > 0:
                grid.separator(factor=0.5)
            row = grid.box().split(factor=LABEL_FACTOR)
            row.label(text=age.pretty())
            for surface_type, cell in zip(SurfaceType, surface_columns(row)):
                cell.alignment = "CENTER"
                complete = (surface_type, age) not in undefined
                op = cell.operator(
                    "rbr.material_map_view_condition",
                    text="",
                    icon="HIDE_OFF" if complete else "ERROR",
                    depress=(surface_type, age) == shown,
                )
                op.surface_type = surface_type.name
                op.surface_age = age.name
                if surface_type is not SurfaceType.DRY:
                    auto = internal.auto_wetness.is_auto(surface_type, age)
                    cell.prop(
                        internal.auto_wetness,
                        RBRAutoWetness.prop_name(surface_type, age),
                        text="",
                        icon="LINKED" if auto else "UNLINKED",
                        toggle=True,
                    )
        if internal.auto_wetness.is_auto(st, sa):
            ui.label(text="Shown maps are automatic from dry", icon="INFO")

        ui.separator(factor=0.5)
        region = inset_split(ui.column())
        region.enabled = editor.selected_region(context, internal) is not None
        region.label(text="Region")
        row = region.row(align=True)
        row.operator("rbr.material_map_copy", text="Copy", icon="COPYDOWN")
        paste = row.row(align=True)
        paste.enabled = (
            GLOBAL_PHYSICAL_MATERIAL_CLIPBOARD.clipboard_material is not None
        )
        paste.operator("rbr.material_map_paste", text="Paste", icon="PASTEDOWN")


LABEL_FACTOR = 0.22
# A box pads its contents by 5px; separators are 0.3 units (6px) per factor.
BOX_INSET = 5 / 6


# Dry only has its view button, so its column is narrower than damp and wet.
DRY_SHARE = 0.26


def surface_columns(layout: bpy.types.UILayout) -> List[bpy.types.UILayout]:
    """Rows for the dry, damp and wet columns."""
    split = layout.split(factor=DRY_SHARE)
    dry = split.row(align=True)
    rest = split.split(factor=0.5)
    return [dry, rest.row(align=True), rest.row(align=True)]


def inset_split(layout: bpy.types.UILayout) -> bpy.types.UILayout:
    """A label/content split inset like the grid boxes' contents, so labels
    and columns line up with theirs."""
    padded = layout.row(align=True)
    padded.separator(factor=BOX_INSET)
    split = padded.split(factor=LABEL_FACTOR)
    padded.separator(factor=BOX_INSET)
    return split


def register() -> None:
    bpy.utils.register_class(RBR_PT_material_maps_panel)


def unregister() -> None:
    bpy.utils.unregister_class(RBR_PT_material_maps_panel)
