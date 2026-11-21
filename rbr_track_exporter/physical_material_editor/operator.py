from typing import TYPE_CHECKING, Any, List, Optional, Set, Tuple

import bpy
from ..types import OperatorReturn
import blf
import gpu
from mathutils import Vector

from .mode import Editor, Mode
from .overview import OverviewMode
from .edit import EditMode
from .resize import ResizeMode
from .new import NewMode
from .drawing_utils import FONT_ID, draw_rect_region
from .properties import (
    RBRFallbackMaterials,
    RBRMaterialMaps,
    RBRMaterialPicker,
    RBRPropertyNodePointer,
)

if TYPE_CHECKING:
    MaterialMapsCollection = bpy.types.bpy_prop_collection[RBRMaterialMaps]
else:
    MaterialMapsCollection = object


def get_region_containing(
    context: bpy.types.Context,
    x: int,
    y: int,
) -> Optional[Tuple[bpy.types.Region, Tuple[int, int]]]:
    if context.screen is None:
        return None
    for area in context.screen.areas:
        if area.type != "IMAGE_EDITOR":
            continue
        for region in area.regions:
            if (
                x > region.x
                and y > region.y
                and x < region.width + region.x
                and y < region.height + region.y
            ):
                if region.type == "WINDOW":
                    return (region, (x - region.x, y - region.y))
                else:
                    return None
    return None


class RBR_OT_edit_material_maps(Editor, bpy.types.Operator):
    """The main editor. This does all of the plumbing between each of the edit
    modes, and handles view controls, scaling, and drawing the image to the
    screen.
    """

    bl_idname = "rbr.edit_material_maps"
    bl_label = "Edit Material Maps"
    bl_description = "Edit the physical properties of this texture" ""
    bl_options = {"REGISTER", "INTERNAL", "UNDO"}

    # Static variable which acts as a lock so only one editor is ever active.
    # When this is not none, it holds the draw handler. It must be static in
    # order to be removed if the user creates a new file while the operator is
    # active: the operator object will be removed and the handle will be lost,
    # so we can never recover.
    handle: Optional[Any] = None
    # Also keep track of this for updating surface type/age.
    active_operator: Optional[Any] = None

    @property
    def mode(self) -> Mode:
        return self._mode

    @mode.setter
    def mode(self, m: Mode) -> None:
        if bpy.context.window is None or bpy.context.workspace is None:
            return
        bpy.context.window.cursor_modal_set(m.cursor())

        def status_text_handler(
            header: bpy.types.Header, _ctx: bpy.types.Context
        ) -> None:
            try:
                ui = header.layout
                self.mode.draw_status(ui)
                ui.label(text="Pan/Zoom", icon="MOUSE_MMB_DRAG")
            except ReferenceError:
                # Can hit this when the user has the editor open and creates a
                # new document.
                if bpy.context.workspace is not None:
                    bpy.context.workspace.status_text_set(None)

        bpy.context.workspace.status_text_set(text=status_text_handler)
        self._mode = m

    def to_overview_mode(self) -> None:
        self.mode = OverviewMode()

    def to_resize_mode(self, resizing_index: int) -> None:
        self.mode = ResizeMode(resizing_index=resizing_index)

    def to_edit_mode(self, editing_index: int) -> None:
        self.mode = EditMode(editing_index=editing_index)

    def to_new_mode(self) -> None:
        self.mode = NewMode()

    node: bpy.props.PointerProperty(type=RBRPropertyNodePointer)  # type: ignore

    # Holds the currently active material maps (from the texture node)
    _material_maps: Optional[MaterialMapsCollection] = None
    _fallback_materials: Optional[RBRFallbackMaterials] = None
    _material_picker: Optional[RBRMaterialPicker] = None

    @property
    def material_maps(self) -> MaterialMapsCollection:
        if self._material_maps is None:
            raise RuntimeError("Missing material maps in editor")
        return self._material_maps

    @material_maps.setter
    def material_maps(self, t: MaterialMapsCollection) -> None:
        self._material_maps = t

    @property
    def fallback_materials(self) -> RBRFallbackMaterials:
        if self._fallback_materials is None:
            raise RuntimeError("Missing fallback materials in editor")
        return self._fallback_materials

    @fallback_materials.setter
    def fallback_materials(self, t: RBRFallbackMaterials) -> None:
        self._fallback_materials = t

    @property
    def material_picker(self) -> RBRMaterialPicker:
        if self._material_picker is None:
            raise RuntimeError("Missing material picker in editor")
        return self._material_picker

    @material_picker.setter
    def material_picker(self, t: RBRMaterialPicker) -> None:
        self._material_picker = t

    def report_message(self, level: Set[str], message: str) -> None:
        self.report(level, message)

    def update_active_texture(
        self, context: bpy.types.Context
    ) -> Optional[OperatorReturn]:
        """Make sure we have a material map available and update the image editors to
        use the appropriate image"""
        node = self.node.get_shader_node()
        if node is None:
            return {"CANCELLED"}
        image = node.get_active_image(context)
        if context.screen is None:
            return {"CANCELLED"}
        for area in context.screen.areas:
            if area.type == "IMAGE_EDITOR":
                space = area.spaces.active
                if isinstance(space, bpy.types.SpaceImageEditor):
                    space.image = image
        self.material_maps = node.get_internal().material_maps
        self.fallback_materials = node.get_internal().fallback_materials
        self.material_picker = node.get_internal().material_picker
        self.material_picker.init(context)
        return None

    # Keep track of the last image editor region the user hovered over,
    # and the mouse coordinates within that region.
    _last_mouse_region: Tuple[bpy.types.Region, float, float]

    def last_mouse_region(self) -> Tuple[bpy.types.Region, float, float]:
        return self._last_mouse_region

    # Maintain a list of maps the mouse is hovered over.
    _hovered_map_indices: List[int] = []

    def hovered_map_indices(self) -> List[int]:
        return self._hovered_map_indices

    def set_hovered_map_indices(
        self, region: bpy.types.Region, rx: int, ry: int
    ) -> None:
        vx, vy = region.view2d.region_to_view(rx, ry)
        all_maps = self.material_maps
        found_indices = []
        for i, mat in enumerate(all_maps):
            if mat.point_in_map(vx, vy):
                found_indices.append(i)
        self._hovered_map_indices = found_indices

    def draw_editor_wrapped(self, context: bpy.types.Context) -> None:
        try:
            self.draw_editor(context)
        except ReferenceError:
            RBR_OT_edit_material_maps.cleanup_handle(context)

    def draw_editor(self, context: bpy.types.Context) -> None:
        area = context.area
        if area is None or bpy.context.preferences is None:
            return
        region: bpy.types.Region | None = None
        for r in area.regions:
            if r.type == "WINDOW":
                region = r
                break
        if region is None:
            return

        gpu.state.blend_set("ALPHA")
        gpu.state.line_width_set(2)

        self.mode.draw(self, region)

        scale = bpy.context.preferences.system.ui_scale
        font_size = round(scale * 10)
        blf.color(FONT_ID, 0, 0, 0, 1)
        blf.size(FONT_ID, font_size)

        padding = scale * 5
        position_bl = scale * Vector((20, 20))

        messages = self.mode.messages(self)
        width = 0.0
        for message in messages:
            x, y = blf.dimensions(FONT_ID, message)
            width = max(x, width)
        width += 2 * padding

        height = len(messages) * (font_size + 2 * padding)
        height += 2 * padding

        draw_rect_region(
            position_bl,
            position_bl + Vector((width, height)),
            bg_color=(1, 1, 1, 0.8),
            border_color=(1, 1, 1, 0.8),
        )

        messages.reverse()
        font_pos_y = position_bl.y + 2 * padding
        for message in messages:
            blf.position(FONT_ID, position_bl.x + padding, font_pos_y, 0)
            blf.draw(FONT_ID, message)
            font_pos_y += font_size + 2 * padding

        # If we don't disable this at the end, the entire blender UI breaks.
        blf.disable(FONT_ID, blf.WORD_WRAP)
        return

    @staticmethod
    def cleanup_handle(context: bpy.types.Context) -> None:
        if RBR_OT_edit_material_maps.handle is not None:
            bpy.types.SpaceImageEditor.draw_handler_remove(
                RBR_OT_edit_material_maps.handle, "WINDOW"
            )
            if context.window is not None:
                context.window.cursor_modal_restore()
            RBR_OT_edit_material_maps.handle = None
            RBR_OT_edit_material_maps.active_operator = None

    def cleanup(self, context: bpy.types.Context) -> None:
        if bpy.context.workspace is not None:
            bpy.context.workspace.status_text_set(None)
        RBR_OT_edit_material_maps.cleanup_handle(context)

    def modal(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        # Force all image editors to redraw
        # This makes sure the user defined boxes get drawn.
        if context.screen is None:
            return {"CANCELLED"}
        for area in context.screen.areas:
            if area.type == "IMAGE_EDITOR":
                area.tag_redraw()

        # Find the region the user is currently hovering over
        region_and_mouse = get_region_containing(context, event.mouse_x, event.mouse_y)
        if region_and_mouse is None:
            return {"PASS_THROUGH"}
        region, (rmx, rmy) = region_and_mouse

        self._last_mouse_region = (region, rmx, rmy)

        self.set_hovered_map_indices(region, rmx, rmy)

        # Defer to the mode handler
        result = self.mode.handle_event(self, event)
        if result == {"FINISHED"} or result == {"CANCELLED"}:
            self.cleanup(context)
        return result

    @classmethod
    def poll(_cls, context: bpy.types.Context) -> bool:
        return True

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> OperatorReturn:
        if RBR_OT_edit_material_maps.handle is not None:
            self.cleanup(context)
        node = self.node.get_shader_node()
        if node is None or node.node_tree is None:
            self.report({"ERROR"}, "Calling node not found")
            return {"CANCELLED"}
        if node.node_tree.library is not None:
            self.report({"ERROR"}, "Node is from a library, edit the material there")
            return {"CANCELLED"}
        if context.screen is None or context.window_manager is None:
            return {"CANCELLED"}
        if "IMAGE_EDITOR" not in [a.type for a in context.screen.areas]:
            self.report({"ERROR"}, "Must have an image editor on screen")
            return {"CANCELLED"}

        for area in context.screen.areas:
            if area.type == "IMAGE_EDITOR":
                area.tag_redraw()

        self.to_overview_mode()

        # Cleanup the existing handle
        RBR_OT_edit_material_maps.cleanup_handle(context)
        RBR_OT_edit_material_maps.handle = bpy.types.SpaceImageEditor.draw_handler_add(
            self.draw_editor_wrapped, (context,), "WINDOW", "POST_PIXEL"
        )
        self.update_active_texture(context)
        context.window_manager.modal_handler_add(self)

        RBR_OT_edit_material_maps.active_operator = self

        return {"RUNNING_MODAL"}


def register() -> None:
    bpy.utils.register_class(RBR_OT_edit_material_maps)


def unregister() -> None:
    bpy.utils.unregister_class(RBR_OT_edit_material_maps)
