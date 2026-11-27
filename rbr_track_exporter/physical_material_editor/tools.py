from typing import Any, Tuple

import bpy

from ..types import MaterialId
from . import editor

SHARED_KEYMAP: Tuple[Any, ...] = (
    (
        "wm.tool_set_by_id",
        {"type": "ESC", "value": "PRESS"},
        {"properties": [("name", "builtin.sample"), ("space_type", "IMAGE_EDITOR")]},
    ),
)


def _in_header(context: bpy.types.Context) -> bool:
    return context.region is not None and context.region.type in {
        "HEADER",
        "TOOL_HEADER",
    }


def draw_picker(context: bpy.types.Context, layout: bpy.types.UILayout) -> None:
    internal = editor.editing_internal(context)
    if internal is None:
        layout.label(text="Use Edit Material Maps on an RBR Texture node")
        return
    picker = internal.material_picker
    if _in_header(context):
        layout.label(text=MaterialId(picker.material_id).pretty())
        layout.prop(picker, "alpha", text="Opacity", slider=True)
        return
    layout.use_property_split = False
    layout.prop(picker, "alpha", text="Overlay Opacity", slider=True)
    layout.label(text="Material")
    picker.draw(context, layout)


class RBRMaterialMapPaintTool(bpy.types.WorkSpaceTool):
    bl_space_type = "IMAGE_EDITOR"
    bl_context_mode = "VIEW"
    bl_idname = editor.PAINT_TOOL
    bl_label = "Paint Materials"
    bl_description = "Paint physical materials into the material map cells"
    bl_icon = "brush.draw"
    bl_cursor = "PAINT_BRUSH"
    # The click comes last: Blender stores tool keymaps in reverse, and the
    # Shift+Space popup borrows a letter from a tool's first item.
    bl_keymap = (
        *SHARED_KEYMAP,
        ("rbr.material_map_paint", {"type": "LEFTMOUSE", "value": "PRESS"}, None),
    )

    @staticmethod
    def draw_settings(
        context: bpy.types.Context, layout: bpy.types.UILayout, tool: Any
    ) -> None:
        draw_picker(context, layout)

    @staticmethod
    def draw_cursor(context: bpy.types.Context, tool: Any, xy: Any) -> None:
        editor.draw_cursor(context, xy)


class RBRMaterialMapFillTool(bpy.types.WorkSpaceTool):
    bl_space_type = "IMAGE_EDITOR"
    bl_context_mode = "VIEW"
    bl_idname = editor.FILL_TOOL
    bl_label = "Fill Materials"
    bl_description = "Fill connected material map cells of the same material"
    bl_icon = "brush.paint_texture.fill"
    bl_cursor = "PAINT_BRUSH"
    bl_keymap = (
        *SHARED_KEYMAP,
        ("rbr.material_map_fill", {"type": "LEFTMOUSE", "value": "PRESS"}, None),
    )

    @staticmethod
    def draw_settings(
        context: bpy.types.Context, layout: bpy.types.UILayout, tool: Any
    ) -> None:
        draw_picker(context, layout)

    @staticmethod
    def draw_cursor(context: bpy.types.Context, tool: Any, xy: Any) -> None:
        editor.draw_cursor(context, xy)


class RBRMaterialMapSampleTool(bpy.types.WorkSpaceTool):
    bl_space_type = "IMAGE_EDITOR"
    bl_context_mode = "VIEW"
    bl_idname = editor.SAMPLE_TOOL
    bl_label = "Sample Material"
    bl_description = "Pick the material of a material map cell to paint with"
    bl_icon = "ops.paint.eyedropper_add"
    bl_cursor = "EYEDROPPER"
    bl_keymap = (
        *SHARED_KEYMAP,
        ("rbr.material_map_sample", {"type": "LEFTMOUSE", "value": "PRESS"}, None),
    )

    @staticmethod
    def draw_settings(
        context: bpy.types.Context, layout: bpy.types.UILayout, tool: Any
    ) -> None:
        draw_picker(context, layout)

    @staticmethod
    def draw_cursor(context: bpy.types.Context, tool: Any, xy: Any) -> None:
        editor.draw_cursor(context, xy)


class RBRMaterialMapRegionsTool(bpy.types.WorkSpaceTool):
    bl_space_type = "IMAGE_EDITOR"
    bl_context_mode = "VIEW"
    bl_idname = editor.REGIONS_TOOL
    bl_label = "Material Map Regions"
    bl_description = (
        "Select, move and resize material map regions, or drag on empty space "
        "to add one"
    )
    bl_icon = "ops.gpencil.transform_fill"
    bl_cursor = "DEFAULT"
    bl_keymap = (
        ("rbr.material_map_region_delete", {"type": "DEL", "value": "PRESS"}, None),
        (
            "rbr.material_map_region_delete",
            {"type": "BACK_SPACE", "value": "PRESS"},
            None,
        ),
        *SHARED_KEYMAP,
        (
            "rbr.material_map_region_tweak",
            {"type": "LEFTMOUSE", "value": "PRESS"},
            None,
        ),
    )

    @staticmethod
    def draw_settings(
        context: bpy.types.Context, layout: bpy.types.UILayout, tool: Any
    ) -> None:
        internal = editor.editing_internal(context)
        if internal is None:
            layout.label(text="Use Edit Material Maps on an RBR Texture node")
            return
        if not _in_header(context):
            layout.prop(
                internal.material_picker, "alpha", text="Overlay Opacity", slider=True
            )
        index = editor.selected_region(context, internal)
        if index is None:
            layout.label(text="No region selected")
            return
        maps = internal.material_maps[index]
        row = layout.row(align=True)
        row.label(text="Repeat")
        for axis, on in (("X", maps.repeat_x), ("Y", maps.repeat_y)):
            op = row.operator("rbr.material_map_region_repeat", text=axis, depress=on)
            op.axis = axis
        layout.operator("rbr.material_map_region_delete", icon="TRASH")

    @staticmethod
    def draw_cursor(context: bpy.types.Context, tool: Any, xy: Any) -> None:
        editor.draw_cursor(context, xy)


TOOLS = (
    RBRMaterialMapPaintTool,
    RBRMaterialMapFillTool,
    RBRMaterialMapSampleTool,
    RBRMaterialMapRegionsTool,
)


# Letters for the tools in the Shift+Space toolbar popup.
POPUP_KEYS = (
    (editor.PAINT_TOOL, "P"),
    (editor.FILL_TOOL, "F"),
    (editor.SAMPLE_TOOL, "S"),
    (editor.REGIONS_TOOL, "R"),
)

_popup_keymap_items: list[Tuple[Any, Any]] = []


def register_popup_keys() -> None:
    wm = bpy.context.window_manager
    keyconfig = wm.keyconfigs.addon if wm is not None else None
    if keyconfig is None:
        return
    keymap = keyconfig.keymaps.new(
        "Toolbar Popup", space_type="EMPTY", region_type="TEMPORARY"
    )
    for name, key in POPUP_KEYS:
        items: Any = keymap.keymap_items
        item = items.new("wm.tool_set_by_id", key, "PRESS")
        properties: Any = item.properties
        properties.name = name
        _popup_keymap_items.append((keymap, item))


def register() -> None:
    register_popup_keys()
    bpy.utils.register_tool(TOOLS[0], separator=True)
    for previous, tool in zip(editor.TOOLS, TOOLS[1:]):
        bpy.utils.register_tool(tool, after={previous})


def unregister() -> None:
    for tool in reversed(TOOLS):
        bpy.utils.unregister_tool(tool)
    for keymap, item in _popup_keymap_items:
        keymap.keymap_items.remove(item)
    _popup_keymap_items.clear()
