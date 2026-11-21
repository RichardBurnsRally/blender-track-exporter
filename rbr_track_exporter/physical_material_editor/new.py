from dataclasses import dataclass
from typing import List, Optional, Set

import bpy
from ..types import OperatorReturn
from mathutils import Vector

from .mode import Editor, Mode
from .drawing_utils import draw_rect_view


@dataclass
class NewMode(Mode):
    """Map a new region by clicking and dragging"""

    # Start position of drag, UV space
    start_position: Optional[Vector] = None
    end_position: Optional[Vector] = None

    def draw(
        self,
        editor: Editor,
        region: bpy.types.Region,
    ) -> None:
        for mat in editor.material_maps:
            draw_rect_view(region, Vector(mat.position_1), Vector(mat.position_2))
        if self.start_position is not None:
            mouse_region, mouse_x, mouse_y = editor.last_mouse_region()
            if mouse_region == region:
                mouse_pos = Vector(region.view2d.region_to_view(mouse_x, mouse_y))
                draw_rect_view(region, self.start_position, mouse_pos)

    def handle_event(self, editor: Editor, event: bpy.types.Event) -> OperatorReturn:
        region, mx, my = editor.last_mouse_region()
        cursor_pos_view = Vector(region.view2d.region_to_view(mx, my))
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            self.start_position = cursor_pos_view
            return {"RUNNING_MODAL"}
        elif event.type == "LEFTMOUSE" and event.value == "RELEASE":
            # Ignore tiny drags
            if self.start_position is not None:
                if (self.start_position - cursor_pos_view).length < 0.02:
                    self.start_position = None
                else:
                    material_maps = editor.material_maps.add()
                    material_maps.position_1 = self.start_position
                    material_maps.position_2 = cursor_pos_view
                    material_maps._init()
                    editor.to_overview_mode()
            return {"RUNNING_MODAL"}
        elif event.type == "ESC" and event.value == "PRESS":
            editor.to_overview_mode()
            return {"RUNNING_MODAL"}
        return {"PASS_THROUGH"}

    def cursor(self) -> str:
        return "PAINT_CROSS"

    def messages(self, editor: Editor) -> List[str]:
        return [
            "Create New Map",
        ]

    def draw_status(self, ui: bpy.types.UILayout) -> None:
        ui.label(text="Overview", icon="EVENT_ESC")
        ui.label(text="Draw Map Bounds", icon="MOUSE_LMB_DRAG")
