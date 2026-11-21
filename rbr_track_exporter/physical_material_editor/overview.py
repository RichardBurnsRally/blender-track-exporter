from dataclasses import dataclass
from typing import List, Set

import bpy
from ..types import OperatorReturn
from mathutils import Vector

from .mode import Editor, Mode
from .drawing_utils import draw_rect_view


@dataclass
class OverviewMode(Mode):
    """View all mapped regions"""

    def draw(
        self,
        editor: Editor,
        region: bpy.types.Region,
    ) -> None:
        hovered = editor.hovered_map_indices()
        all_maps = editor.material_maps
        alpha = editor.material_picker.alpha
        for i, mat in enumerate(all_maps):
            opacity = alpha / 2
            # Only highlight the last map: it'll be the last to be drawn, so
            # it's always on top.
            if hovered != [] and i == hovered[-1]:
                opacity = alpha
            draw_rect_view(
                region,
                Vector(mat.position_1),
                Vector(mat.position_2),
                bg_color=(1, 1, 1, opacity),
            )

    def handle_event(self, editor: Editor, event: bpy.types.Event) -> OperatorReturn:
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            hovered = editor.hovered_map_indices()
            if hovered != []:
                editor.to_resize_mode(resizing_index=hovered[-1])
                return {"RUNNING_MODAL"}
            else:
                return {"PASS_THROUGH"}
        elif event.type == "RIGHTMOUSE" and event.value == "PRESS":
            editor.to_new_mode()
            return {"RUNNING_MODAL"}
        elif event.type == "F" and event.value == "PRESS":
            editor.fallback_materials.set_from_active(editor.material_picker)
        elif event.type == "ESC" and event.value == "PRESS":
            return {"FINISHED"}
        return {"PASS_THROUGH"}

    def cursor(self) -> str:
        return "DEFAULT"

    def messages(self, editor: Editor) -> List[str]:
        fallback_material = editor.fallback_materials.active_material()
        return [
            "Overview",
            f"Fallback material: {fallback_material.pretty()}",
        ]

    def draw_status(self, ui: bpy.types.UILayout) -> None:
        ui.label(text="Exit", icon="EVENT_ESC")
        ui.label(text="Edit", icon="MOUSE_LMB")
        ui.label(text="New", icon="MOUSE_RMB")
        ui.label(text="Set Fallback", icon="EVENT_F")
