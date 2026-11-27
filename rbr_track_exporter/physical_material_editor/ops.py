from typing import Any, Optional

import bpy
from mathutils import Vector

from ..types import MaterialId, OperatorReturn
from . import editor
from .clipboard import GLOBAL_PHYSICAL_MATERIAL_CLIPBOARD
from .properties import RBRAutoWetness, RBRPropertyNodePointer
from .types import GrabHandle


class RBR_OT_edit_material_maps(bpy.types.Operator):
    bl_idname = "rbr.edit_material_maps"
    bl_label = "Edit Material Maps"
    bl_description = "Edit this texture's material maps in the Image Editor"
    bl_options = {"INTERNAL"}

    node: bpy.props.PointerProperty(type=RBRPropertyNodePointer)  # type: ignore

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        node: Any = self.node.get_shader_node()
        if node is None or node.node_tree is None:
            self.report({"ERROR"}, "Calling node not found")
            return {"CANCELLED"}
        if node.node_tree.library is not None:
            self.report({"ERROR"}, "Node is from a library, edit the material there")
            return {"CANCELLED"}
        editors = editor.image_editors(context)
        if not editors or context.window_manager is None:
            self.report({"ERROR"}, "Open an Image Editor first")
            return {"CANCELLED"}
        wm = context.window_manager
        if wm.rbr_material_map_texture != node.node_tree.name:
            wm.rbr_material_map_texture = node.node_tree.name
            editor.select_region(context, None)
        node.get_internal().material_picker.init(context)
        for area, space in editors:
            space.ui_mode = "VIEW"
            space.show_region_ui = True
            space.show_region_toolbar = True
            area.tag_redraw()
        editor.refresh_images(context)
        area, _ = editors[0]
        region = next(r for r in area.regions if r.type == "WINDOW")
        with context.temp_override(window=context.window, area=area, region=region):
            bpy.ops.wm.tool_set_by_id(name=editor.PAINT_TOOL, space_type="IMAGE_EDITOR")
        return {"FINISHED"}


class MaterialMapOperator(bpy.types.Operator):
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return editor.editing_internal(context) is not None

    def finish(self, context: bpy.types.Context) -> OperatorReturn:
        editor.invalidate()
        editor.redraw_image_editors(context)
        return {"FINISHED"}


class RBR_OT_material_map_paint(MaterialMapOperator):
    bl_idname = "rbr.material_map_paint"
    bl_label = "Paint Materials"
    bl_description = "Paint the active material into the cells under the cursor"
    bl_options = {"UNDO", "INTERNAL"}

    region_index: int = 0

    def paint(self, context: bpy.types.Context, event: bpy.types.Event) -> None:
        internal = editor.editing_internal(context)
        maps = internal.material_maps[self.region_index]
        uv = editor.mouse_uv(context, event)
        if not maps.point_in_map(*uv):
            return
        px, py = maps.pixel(*uv)
        st, sa = editor.active_condition(context, internal)
        cell = maps.get_map(st, sa).rows[py].cols[px]
        material = internal.material_picker.material_id
        if cell.material_id != material:
            cell.material_id = material
            editor.invalidate()
            editor.redraw_image_editors(context)

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        internal = editor.editing_internal(context)
        index = editor.target_region(context, internal, editor.mouse_uv(context, event))
        if index is None:
            return {"PASS_THROUGH"}
        if not editor.can_edit(context, internal, self.report):
            return {"CANCELLED"}
        self.region_index = index
        editor.select_region(context, index)
        self.paint(context, event)
        if context.window_manager is None:
            return {"CANCELLED"}
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        if event.type == "MOUSEMOVE":
            self.paint(context, event)
        elif event.type in {"LEFTMOUSE", "ESC", "RIGHTMOUSE"}:
            if event.value == "RELEASE" or event.type == "ESC":
                internal = editor.editing_internal(context)
                editor.after_edit(context, internal, self.region_index)
                return self.finish(context)
        return {"RUNNING_MODAL"}


class RBR_OT_material_map_fill(MaterialMapOperator):
    bl_idname = "rbr.material_map_fill"
    bl_label = "Fill Materials"
    bl_description = "Fill the connected cells of the same material"
    bl_options = {"UNDO", "INTERNAL"}

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        internal = editor.editing_internal(context)
        uv = editor.mouse_uv(context, event)
        index = editor.target_region(context, internal, uv)
        if index is None:
            return {"PASS_THROUGH"}
        if not editor.can_edit(context, internal, self.report):
            return {"CANCELLED"}
        editor.select_region(context, index)
        maps = internal.material_maps[index]
        st, sa = editor.active_condition(context, internal)
        rows = maps.get_map(st, sa).rows
        px, py = maps.pixel(*uv)
        material = internal.material_picker.material_id
        source = rows[py].cols[px].material_id
        if source == material:
            return {"CANCELLED"}
        stack = [(py, px)]
        while stack:
            i, j = stack.pop()
            if not (0 <= i < 16 and 0 <= j < 16):
                continue
            cell = rows[i].cols[j]
            if cell.material_id != source:
                continue
            cell.material_id = material
            stack += [(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)]
        editor.after_edit(context, internal, index)
        return self.finish(context)


class RBR_OT_material_map_sample(MaterialMapOperator):
    bl_idname = "rbr.material_map_sample"
    bl_label = "Sample Material"
    bl_description = "Pick the material under the cursor"
    bl_options = {"INTERNAL"}

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        internal = editor.editing_internal(context)
        uv = editor.mouse_uv(context, event)
        index = editor.target_region(context, internal, uv)
        st, sa = editor.active_condition(context, internal)
        if index is None:
            material = internal.fallback_materials.get_condition(st, sa)
        else:
            maps = internal.material_maps[index]
            px, py = maps.pixel(*uv)
            material = MaterialId(maps.get_map(st, sa).rows[py].cols[px].material_id)
        if not internal.material_picker.set_material_id(material):
            self.report({"WARNING"}, "Can't sample this material")
            return {"CANCELLED"}
        return self.finish(context)


class RBR_OT_material_map_region_tweak(MaterialMapOperator):
    bl_idname = "rbr.material_map_region_tweak"
    bl_label = "Select, Move or Resize Region"
    bl_description = (
        "Click a region to select it, drag it or its handles to move or resize "
        "it, or drag on empty space to add a region"
    )
    bl_options = {"UNDO", "INTERNAL"}

    handle: Optional[GrabHandle] = None
    index: Optional[int] = None
    creating: bool = False
    start_uv: Vector = Vector((0.0, 0.0))
    last_uv: Vector = Vector((0.0, 0.0))
    start_px: Vector = Vector((0.0, 0.0))
    moved: bool = False

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        internal = editor.editing_internal(context)
        region = context.region
        if region is None or context.window_manager is None:
            return {"CANCELLED"}
        uv = editor.mouse_uv(context, event)
        self.start_uv = self.last_uv = uv
        self.start_px = Vector((event.mouse_region_x, event.mouse_region_y))
        self.moved = False
        self.handle = None
        self.creating = False
        selected = editor.selected_region(context, internal)
        if selected is not None:
            self.handle = editor.grab_handle_at(
                region,
                internal.material_maps[selected],
                event.mouse_region_x,
                event.mouse_region_y,
            )
        hits = editor.regions_at(internal, uv)
        if self.handle is not None:
            self.index = selected
        elif selected in hits:
            self.index = selected
        elif hits:
            self.index = hits[-1]
            editor.select_region(context, self.index)
        else:
            self.index = None
            self.creating = True
            editor.new_region_drag = (uv, uv)
        if context.window is not None:
            if self.handle is not None:
                cursor = editor.handle_cursor(self.handle)
            else:
                cursor = "CROSSHAIR" if self.creating else "HAND_CLOSED"
            context.window.cursor_modal_set(cursor)
        context.window_manager.modal_handler_add(self)
        editor.redraw_image_editors(context)
        return {"RUNNING_MODAL"}

    def modal(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        internal = editor.editing_internal(context)
        uv = editor.mouse_uv(context, event)
        if event.type == "MOUSEMOVE":
            px = Vector((event.mouse_region_x, event.mouse_region_y))
            if (px - self.start_px).length >= 3:
                self.moved = True
            if self.moved:
                self.update(internal, uv)
            editor.redraw_image_editors(context)
        elif event.type == "LEFTMOUSE" and event.value == "RELEASE":
            if self.moved:
                self.update(internal, uv)
            return self.release(context, internal, uv)
        elif event.type in {"ESC", "RIGHTMOUSE"}:
            editor.new_region_drag = None
            return self.finish(context)
        return {"RUNNING_MODAL"}

    def finish(self, context: bpy.types.Context) -> OperatorReturn:
        if context.window is not None:
            context.window.cursor_modal_restore()
        return super().finish(context)

    def update(self, internal: Any, uv: Vector) -> None:
        if self.creating:
            editor.new_region_drag = (self.start_uv, uv)
            return
        if self.index is None:
            return
        maps = internal.material_maps[self.index]
        if self.handle is not None:
            flipped = maps.update_mat_pos(self.handle, uv)
            if flipped is not None:
                self.handle = flipped
        else:
            maps.drag(uv - self.last_uv)
        self.last_uv = uv
        editor.invalidate()

    def release(
        self, context: bpy.types.Context, internal: Any, uv: Vector
    ) -> OperatorReturn:
        if self.creating:
            editor.new_region_drag = None
            if not self.moved:
                editor.select_region(context, None)
                return self.finish(context)
            maps = internal.material_maps.add()
            maps.position_1 = self.start_uv
            maps.position_2 = uv
            maps._init()
            editor.select_region(context, len(internal.material_maps) - 1)
            return self.finish(context)
        if not self.moved and self.handle is None:
            # A click on overlapping regions cycles through them.
            hits = editor.regions_at(internal, uv)
            if self.index in hits and len(hits) > 1:
                position = hits.index(self.index)
                editor.select_region(context, hits[(position + 1) % len(hits)])
        return self.finish(context)


class RBR_OT_material_map_view_condition(MaterialMapOperator):
    bl_idname = "rbr.material_map_view_condition"
    bl_label = "Show Condition"
    bl_description = "Show and paint this condition's maps"
    bl_options = {"INTERNAL"}

    surface_type: bpy.props.StringProperty()  # type: ignore
    surface_age: bpy.props.StringProperty()  # type: ignore

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        if context.scene is None:
            return {"CANCELLED"}
        settings = context.scene.rbr_scene_settings
        settings.active_surface_type = self.surface_type
        if editor.editing_internal(context).is_road_surface:
            settings.active_surface_age = self.surface_age
        return self.finish(context)


class RBR_OT_material_map_region_repeat(MaterialMapOperator):
    bl_idname = "rbr.material_map_region_repeat"
    bl_label = "Repeat Region"
    bl_description = "Make the selected region span and repeat across the texture"
    bl_options = {"UNDO", "INTERNAL"}

    axis: bpy.props.EnumProperty(  # type: ignore
        items=[("X", "X", "Across the width"), ("Y", "Y", "Across the height")]
    )

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        internal = editor.editing_internal(context)
        index = editor.selected_region(context, internal)
        if index is None:
            return {"CANCELLED"}
        maps = internal.material_maps[index]
        if self.axis == "X":
            maps.repeat_x = not maps.repeat_x
        else:
            maps.repeat_y = not maps.repeat_y
        maps.maintain_position_invariant()
        return self.finish(context)


class RBR_OT_material_map_region_delete(MaterialMapOperator):
    bl_idname = "rbr.material_map_region_delete"
    bl_label = "Delete Region"
    bl_description = "Delete the selected region"
    bl_options = {"UNDO", "INTERNAL"}

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        internal = editor.editing_internal(context)
        index = editor.selected_region(context, internal)
        if index is None:
            return {"CANCELLED"}
        internal.material_maps.remove(index)
        editor.select_region(context, None)
        return self.finish(context)


class RegionGridOperator(MaterialMapOperator):
    """Acts on the selected region's grid for the shown condition."""

    def run(
        self, context: bpy.types.Context, internal: Any, index: int
    ) -> OperatorReturn:
        raise NotImplementedError

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        internal = editor.editing_internal(context)
        index = editor.selected_region(context, internal)
        if index is None:
            self.report({"WARNING"}, "No region selected")
            return {"CANCELLED"}
        return self.run(context, internal, index)


class RBR_OT_material_map_copy(RegionGridOperator):
    bl_idname = "rbr.material_map_copy"
    bl_label = "Copy Material Map"
    bl_description = "Copy the selected region's materials for the shown condition"
    bl_options = {"INTERNAL"}

    def run(
        self, context: bpy.types.Context, internal: Any, index: int
    ) -> OperatorReturn:
        st, sa = editor.active_condition(context, internal)
        GLOBAL_PHYSICAL_MATERIAL_CLIPBOARD.copy(
            internal.material_maps[index].get_map(st, sa)
        )
        self.report({"INFO"}, "Copied material map")
        return self.finish(context)


class RBR_OT_material_map_paste(RegionGridOperator):
    bl_idname = "rbr.material_map_paste"
    bl_label = "Paste Material Map"
    bl_description = "Paste materials into the selected region for the shown condition"
    bl_options = {"UNDO", "INTERNAL"}

    def run(
        self, context: bpy.types.Context, internal: Any, index: int
    ) -> OperatorReturn:
        if GLOBAL_PHYSICAL_MATERIAL_CLIPBOARD.clipboard_material is None:
            self.report({"WARNING"}, "No material map in clipboard")
            return {"CANCELLED"}
        if not editor.can_edit(context, internal, self.report):
            return {"CANCELLED"}
        st, sa = editor.active_condition(context, internal)
        GLOBAL_PHYSICAL_MATERIAL_CLIPBOARD.paste(
            internal.material_maps[index].get_map(st, sa)
        )
        editor.after_edit(context, internal, index)
        return self.finish(context)


class RBR_OT_material_map_set_fallback(MaterialMapOperator):
    bl_idname = "rbr.material_map_set_fallback"
    bl_label = "Set Fallback Material"
    bl_description = (
        "Use the active material where no region covers a face, for the "
        "active condition"
    )
    bl_options = {"UNDO", "INTERNAL"}

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        internal = editor.editing_internal(context)
        if not editor.can_edit(context, internal, self.report):
            return {"CANCELLED"}
        st, sa = editor.active_condition(context, internal)
        fallback = getattr(
            internal.fallback_materials, RBRAutoWetness.prop_name(st, sa)
        )
        fallback.material_id = internal.material_picker.material_id
        editor.after_edit(context, internal)
        return self.finish(context)


CLASSES = (
    RBR_OT_edit_material_maps,
    RBR_OT_material_map_paint,
    RBR_OT_material_map_fill,
    RBR_OT_material_map_sample,
    RBR_OT_material_map_region_tweak,
    RBR_OT_material_map_view_condition,
    RBR_OT_material_map_region_repeat,
    RBR_OT_material_map_region_delete,
    RBR_OT_material_map_copy,
    RBR_OT_material_map_paste,
    RBR_OT_material_map_set_fallback,
)


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
