from dataclasses import dataclass
import enum
from typing import List, Optional, Set, Tuple

import bpy
from ..types import OperatorReturn
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from ..types import MaterialId, material_id_to_color

from .clipboard import GLOBAL_PHYSICAL_MATERIAL_CLIPBOARD
from .mode import Editor, Mode
from .drawing_utils import FONT_ID


class Tool(enum.Enum):
    PAINT = 1
    FILL = 2
    UV = 3

    def cursor(self) -> str:
        if self == Tool.PAINT:
            return "PAINT_BRUSH"
        elif self == Tool.FILL:
            return "PAINT_BRUSH"
        elif self == Tool.UV:
            return "DEFAULT"
        else:
            raise NotImplementedError()

    def pretty(self) -> str:
        if self == Tool.PAINT:
            return "Paint"
        elif self == Tool.FILL:
            return "Bucket fill"
        elif self == Tool.UV:
            return "Edit UV"
        else:
            raise NotImplementedError()


@dataclass
class EditMode(Mode):
    editing_index: int

    left_mouse_down: bool = False
    highlight_mat_pixel: Tuple[int, int] = (0, 0)
    highlight_snap: Tuple[int, int] = (0, 0)

    _tool: Tool = Tool.PAINT

    @property
    def tool(self) -> Tool:
        return self._tool

    @tool.setter
    def tool(self, m: Tool) -> None:
        if bpy.context.window is None:
            return
        bpy.context.window.cursor_modal_set(m.cursor())
        self._tool = m

    def update_active_maps(self, editor: Editor) -> Optional[OperatorReturn]:
        if self.editing_index >= len(editor.material_maps):
            editor.to_overview_mode()
            return {"PASS_THROUGH"}
        self.active_maps = editor.material_maps[self.editing_index]
        return None

    def draw(
        self,
        editor: Editor,
        region: bpy.types.Region,
    ) -> None:
        self.update_active_maps(editor)
        p1x, p1y = self.active_maps.position_1
        p2x, p2y = self.active_maps.position_2
        box_bl = Vector(region.view2d.view_to_region(p1x, p1y, clip=False))
        box_tr = Vector(region.view2d.view_to_region(p2x, p2y, clip=False))

        x0 = box_bl.x
        y0 = box_bl.y
        x1 = box_tr.x
        y1 = box_tr.y

        dx = x1 - x0
        dy = y1 - y0
        # Draw grid
        lines = []
        for i in range(17):
            multiplier = i / 16.0
            lines.append(
                [
                    (x0 + dx * multiplier, y0),
                    (x0 + dx * multiplier, y1),
                ]
            )
            lines.append(
                [
                    (x0, y0 + dy * multiplier),
                    (x1, y0 + dy * multiplier),
                ]
            )
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        shader.bind()
        batch = batch_for_shader(
            shader,
            "LINES",
            {
                "pos": [x for xs in lines for x in xs],
            },
        )
        shader.uniform_float("color", (1, 1, 1, 0.5))
        batch.draw(shader)

        mat_alpha = editor.material_picker.alpha

        def draw_box(i: int, j: int, px: int = 0, di: int = 1, dj: int = 1) -> None:
            mult_i_0 = i / 16.0
            mult_i_1 = (i + di) / 16.0
            mult_j_0 = j / 16.0
            mult_j_1 = (j + dj) / 16.0
            batch = batch_for_shader(
                shader,
                "TRI_FAN",
                {
                    "pos": [
                        (x0 + dx * mult_j_0 + px, y0 + dy * mult_i_0 + px),
                        (x0 + dx * mult_j_1 - px, y0 + dy * mult_i_0 + px),
                        (x0 + dx * mult_j_1 - px, y0 + dy * mult_i_1 - px),
                        (x0 + dx * mult_j_0 + px, y0 + dy * mult_i_1 - px),
                    ]
                },
            )
            batch.draw(shader)

        # Draw material map
        highlight_j, highlight_i = self.highlight_mat_pixel
        for i, row in enumerate(self.active_maps.get_active_map().rows):
            for j, col in enumerate(row.cols):
                mat_id = MaterialId(col.material_id)
                rgb = material_id_to_color(mat_id)
                r = rgb.r / 255.0
                g = rgb.g / 255.0
                b = rgb.b / 255.0
                shader.uniform_float("color", (r, g, b, mat_alpha))
                draw_box(i, j)

        shader.uniform_float("color", (1, 1, 1, 0.4))
        draw_box(highlight_i, highlight_j, px=2)

        debug = False
        if debug:
            # Debug indices
            wrap_width = round(dx / 16)
            blf.enable(FONT_ID, blf.WORD_WRAP)
            for i, row in enumerate(self.active_maps.get_active_map().rows):
                for j, col in enumerate(row.cols):
                    mat_id = MaterialId(col.material_id)
                    fx = x0 + dx * (j / 16) + 2
                    fy = y0 + dy * (i / 16)
                    fy1 = y0 + dy * ((i + 1) / 16) + 2
                    blf.position(FONT_ID, fx, fy1, 0)
                    blf.color(FONT_ID, 0, 0, 0, 1)
                    blf.size(FONT_ID, 10)
                    blf.draw(FONT_ID, str(i) + "," + str(j))
                    blf.word_wrap(FONT_ID, wrap_width)
                    blf.position(FONT_ID, fx, fy - 10, 0)
                    blf.size(FONT_ID, 8)
                    blf.draw(FONT_ID, mat_id.pretty())

    def paint(self, editor: Editor) -> None:
        self.update_active_maps(editor)
        highlight_j, highlight_i = self.highlight_mat_pixel
        paint_material = editor.material_picker.material_id
        self.active_maps.get_active_map().rows[highlight_i].cols[
            highlight_j
        ].material_id = paint_material

    def fill(self, editor: Editor) -> None:
        self.update_active_maps(editor)
        j, i = self.highlight_mat_pixel
        from_mat = self.active_maps.get_active_map().rows[i].cols[j].material_id
        self.recursive_fill(editor, from_mat, (i, j))

    def recursive_fill(
        self, editor: Editor, from_mat: int, pixel: Tuple[int, int]
    ) -> None:
        i, j = pixel
        this_mat = self.active_maps.get_active_map().rows[i].cols[j].material_id
        paint_material = editor.material_picker.material_id
        if this_mat == paint_material:
            return
        if this_mat == from_mat:
            new_mat = paint_material
            self.active_maps.get_active_map().rows[i].cols[j].material_id = new_mat
            if i < 15:
                self.recursive_fill(editor, from_mat, (i + 1, j))
            if i > 0:
                self.recursive_fill(editor, from_mat, (i - 1, j))
            if j < 15:
                self.recursive_fill(editor, from_mat, (i, j + 1))
            if j > 0:
                self.recursive_fill(editor, from_mat, (i, j - 1))

    def handle_event(self, editor: Editor, event: bpy.types.Event) -> OperatorReturn:
        region, mx, my = editor.last_mouse_region()
        vx, vy = region.view2d.region_to_view(mx, my)

        result = self.update_active_maps(editor)
        if result is not None:
            return result
        self.highlight_mat_pixel = self.active_maps.pixel(vx, vy)
        self.highlight_snap = self.active_maps.quantized_uv(vx, vy)

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            self.left_mouse_down = True
            if self.tool is Tool.PAINT:
                self.paint(editor)
            elif self.tool is Tool.FILL:
                self.fill(editor)
            elif self.tool is Tool.UV:
                return {"PASS_THROUGH"}
            return {"RUNNING_MODAL"}
        elif event.type == "LEFTMOUSE" and event.value == "RELEASE":
            self.left_mouse_down = False
            return {"RUNNING_MODAL"}

        elif event.type == "RIGHTMOUSE":
            if self.tool is Tool.UV:
                return {"PASS_THROUGH"}
            if event.value == "RELEASE":
                j, i = self.highlight_mat_pixel
                ok = editor.material_picker.set_material_id(
                    MaterialId(
                        self.active_maps.get_active_map().rows[i].cols[j].material_id
                    )
                )
                if not ok:
                    editor.report_message({"WARNING"}, "Can't sample invalid material")
            return {"RUNNING_MODAL"}

        elif event.type == "T" and event.value == "PRESS":
            if self.tool is Tool.PAINT:
                self.tool = Tool.FILL
            elif self.tool is Tool.FILL:
                self.tool = Tool.UV
            elif self.tool is Tool.UV:
                self.tool = Tool.PAINT
            return {"RUNNING_MODAL"}

        elif event.type == "MOUSEMOVE":
            if self.left_mouse_down and self.tool is Tool.PAINT:
                self.paint(editor)
            elif self.left_mouse_down and self.tool is Tool.FILL:
                self.fill(editor)
            elif self.tool is Tool.UV:
                return {"PASS_THROUGH"}
            return {"RUNNING_MODAL"}

        elif event.type == "C" and event.value == "PRESS":
            GLOBAL_PHYSICAL_MATERIAL_CLIPBOARD.copy(
                editor.material_maps,
                material_index=self.editing_index,
            )
            editor.report_message({"WARNING"}, "Copied material map")
            return {"RUNNING_MODAL"}

        elif event.type == "V" and event.value == "PRESS":
            success = GLOBAL_PHYSICAL_MATERIAL_CLIPBOARD.paste(
                editor.material_maps,
                material_index=self.editing_index,
            )
            if not success:
                editor.report_message({"WARNING"}, "No material map in clipboard")
            else:
                editor.report_message({"WARNING"}, "Pasted material map")
            return {"RUNNING_MODAL"}

        elif event.type == "TAB":
            if event.value == "RELEASE":
                editor.to_resize_mode(resizing_index=self.editing_index)
            return {"RUNNING_MODAL"}

        elif event.type == "ESC" and event.value == "PRESS":
            editor.to_overview_mode()
            return {"RUNNING_MODAL"}

        return {"PASS_THROUGH"}

    def cursor(self) -> str:
        return "PAINT_BRUSH"

    def messages(self, editor: Editor) -> List[str]:
        if self.active_maps is None:
            return []
        highlight_j, highlight_i = self.highlight_mat_pixel
        mat_id_int = (
            self.active_maps.get_active_map()
            .rows[highlight_i]
            .cols[highlight_j]
            .material_id
        )
        mat_id = MaterialId(mat_id_int)
        paint_material = MaterialId(editor.material_picker.material_id)
        return [
            "Edit Materials",
            "Tool: " + self.tool.pretty(),
            "Active material: " + paint_material.pretty(),
            "Hovered material: " + mat_id.pretty(),
        ]

    def draw_status(self, ui: bpy.types.UILayout) -> None:
        ui.label(text="Overview", icon="EVENT_ESC")
        ui.label(text="Resize", icon="EVENT_TAB")
        if self.tool is Tool.PAINT:
            ui.label(text="Draw", icon="MOUSE_LMB")
        elif self.tool is Tool.FILL:
            ui.label(text="Fill", icon="MOUSE_LMB")
        if self.tool is not Tool.UV:
            ui.label(text="Sample", icon="MOUSE_RMB")
        ui.label(text="Change Tool", icon="EVENT_T")
        ui.label(text="Copy", icon="EVENT_C")
        ui.label(text="Paste", icon="EVENT_V")
