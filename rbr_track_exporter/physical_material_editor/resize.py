from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

import bpy
from ..types import OperatorReturn
from mathutils import Vector

from .types import GrabHandle
from .mode import Editor, Mode
from .properties import point_in_area
from .drawing_utils import draw_rect_region, draw_rect_view


@dataclass
class ResizeMode(Mode):
    resizing_index: int
    grab_handle: Optional[GrabHandle] = None
    grab_handle_size: Vector = Vector((5, 5))
    # Start position and last position of drag, in view space
    drag_start_pos: Optional[Vector] = None
    drag_last_pos: Optional[Vector] = None

    def draw(
        self,
        editor: Editor,
        region: bpy.types.Region,
    ) -> None:
        all_maps = editor.material_maps
        resizing_mat = None
        alpha = editor.material_picker.alpha
        for i, mat in enumerate(all_maps):
            # Draw the resizing one on top of others
            if i == self.resizing_index:
                resizing_mat = mat
                continue
            draw_rect_view(
                region,
                Vector(mat.position_1),
                Vector(mat.position_2),
                bg_color=(1, 1, 1, alpha / 2),
            )
        if resizing_mat is not None:
            draw_rect_view(
                region,
                Vector(resizing_mat.position_1),
                Vector(resizing_mat.position_2),
                bg_color=(1, 1, 1, alpha),
            )
            for handle in GrabHandle:
                grabbable = handle.is_grabbable(
                    repeat_x=resizing_mat.repeat_x,
                    repeat_y=resizing_mat.repeat_y,
                )
                if grabbable:
                    bg_color = (1.0, 1.0, 1.0, 1.0)
                else:
                    bg_color = (0.4, 0.4, 0.4, 1.0)
                x, y = self.grab_handle_pos(editor, handle)
                p = Vector(region.view2d.view_to_region(x, y, clip=False))
                draw_rect_region(
                    p - self.grab_handle_size,
                    p + self.grab_handle_size,
                    bg_color=bg_color,
                    border_color=(0, 0, 0, 1),
                )

    def grab_handle_pos(
        self, editor: Editor, handle: GrabHandle
    ) -> Tuple[float, float]:
        if self.resizing_index >= len(editor.material_maps):
            return (0, 0)
        mat = editor.material_maps[self.resizing_index]
        x0, y0 = mat.position_1
        x1, y1 = mat.position_2
        dx = x1 - x0
        dy = y1 - y0
        mx, my = handle.position_relative().to_tuple()
        return (x0 + dx * mx, y0 + dy * my)

    def handle_event(self, editor: Editor, event: bpy.types.Event) -> OperatorReturn:
        region, mx, my = editor.last_mouse_region()
        cursor_pos_view = Vector(region.view2d.region_to_view(mx, my))
        if self.resizing_index >= len(editor.material_maps):
            editor.to_overview_mode()
            return {"PASS_THROUGH"}
        mat = editor.material_maps[self.resizing_index]
        if event.type == "MOUSEMOVE":
            if self.grab_handle is not None:
                new_handle = mat.update_mat_pos(self.grab_handle, cursor_pos_view)
                if new_handle is not None:
                    self.grab_handle = new_handle
            elif self.drag_last_pos is not None:
                mat.drag(cursor_pos_view - self.drag_last_pos)
                self.drag_last_pos = cursor_pos_view
            return {"RUNNING_MODAL"}
        elif event.type == "LEFTMOUSE" and event.value == "PRESS":
            self.drag_start_pos = None
            self.drag_last_pos = None
            self.grab_handle = None
            # Deal with grab handles first, exiting the handler early if we are
            # grabbing one.
            for handle in GrabHandle:
                x, y = self.grab_handle_pos(editor, handle)
                p = Vector(region.view2d.view_to_region(x, y, clip=False))
                grabbing = point_in_area(
                    Vector((mx, my)),
                    p - self.grab_handle_size,
                    p + self.grab_handle_size,
                )
                if grabbing:
                    self.grab_handle = handle
                    return {"RUNNING_MODAL"}
            hovered = editor.hovered_map_indices()
            # Mark this map as being dragged if the cursor is hovering it
            if self.resizing_index in hovered:
                self.drag_start_pos = cursor_pos_view
                self.drag_last_pos = cursor_pos_view
            # If the cursor is hovering nothing, go back to overview
            elif hovered == []:
                editor.to_overview_mode()
            # Or switch directly to the topmost hovered map
            else:
                editor.to_resize_mode(hovered[-1])
            return {"RUNNING_MODAL"}
        elif event.type == "LEFTMOUSE" and event.value == "RELEASE":
            if self.grab_handle is not None:
                mat.update_mat_pos(self.grab_handle, cursor_pos_view)
                self.grab_handle = None
            if self.drag_last_pos is not None:
                mat.drag(cursor_pos_view - self.drag_last_pos)
                self.drag_last_pos = None
            # If we've only been dragged a tiny amount (according to the drag
            # start position and current cursor position), treat the interaction
            # as a simple mouse press and cycle through the available maps.
            if self.drag_start_pos is not None:
                dx, dy = self.drag_start_pos
                drag_pixel_start = Vector(
                    region.view2d.view_to_region(dx, dy, clip=False)
                )
                drag_vector_pixels = Vector((mx, my)) - drag_pixel_start
                if drag_vector_pixels.length < 2:
                    hovered = editor.hovered_map_indices()
                    index_to_use = 0
                    try:
                        i = hovered.index(self.resizing_index)
                        if i + 1 < len(hovered):
                            index_to_use = i + 1
                    except ValueError:
                        # New hovered set doesn't contain the currently resized map.
                        # We can just use the zeroeth map.
                        pass
                    editor.to_resize_mode(hovered[index_to_use])
                self.drag_start_pos = None
            return {"RUNNING_MODAL"}
        elif (
            event.type == "BACK_SPACE" or event.type == "DEL"
        ) and event.value == "PRESS":
            all_maps = editor.material_maps
            all_maps.remove(self.resizing_index)
            editor.to_overview_mode()
            return {"RUNNING_MODAL"}
        elif event.type == "X":
            if event.value == "RELEASE":
                all_maps = editor.material_maps
                this_map = all_maps[self.resizing_index]
                this_map.repeat_x = not this_map.repeat_x
                this_map.maintain_position_invariant()
            return {"RUNNING_MODAL"}
        elif event.type == "Y":
            if event.value == "RELEASE":
                all_maps = editor.material_maps
                this_map = all_maps[self.resizing_index]
                this_map.repeat_y = not this_map.repeat_y
                this_map.maintain_position_invariant()
            return {"RUNNING_MODAL"}
        elif event.type == "TAB":
            if event.value == "RELEASE":
                editor.to_edit_mode(editing_index=self.resizing_index)
            return {"RUNNING_MODAL"}
        elif event.type == "ESC" and event.value == "PRESS":
            editor.to_overview_mode()
            return {"RUNNING_MODAL"}
        return {"PASS_THROUGH"}

    def messages(self, editor: Editor) -> List[str]:
        return [
            "Move/Resize Map",
        ]

    def draw_status(self, ui: bpy.types.UILayout) -> None:
        ui.label(text="Overview", icon="EVENT_ESC")
        ui.label(text="Edit Materials", icon="EVENT_TAB")
        ui.label(text="Move/Resize", icon="MOUSE_LMB_DRAG")
        ui.label(text="Delete", icon="CANCEL")
        ui.label(text="Repeat X", icon="EVENT_X")
        ui.label(text="Repeat Y", icon="EVENT_Y")
