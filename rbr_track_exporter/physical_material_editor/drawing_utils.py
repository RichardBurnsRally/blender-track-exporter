from typing import Tuple

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

FONT_ID = 0


def draw_rect_view(
    region: bpy.types.Region,
    p0: Vector,
    p1: Vector,
    bg_color: Tuple[float, float, float, float] = (1, 1, 1, 0.2),
    border_color: Tuple[float, float, float, float] = (0, 0, 0, 1),
) -> None:
    """Draw a rectangle in the view space of the given region"""
    p0x, p0y = region.view2d.view_to_region(p0.x, p0.y, clip=False)
    p1x, p1y = region.view2d.view_to_region(p1.x, p1.y, clip=False)
    draw_rect_region(Vector((p0x, p0y)), Vector((p1x, p1y)), bg_color, border_color)


def draw_rect_region(
    p0: Vector,
    p1: Vector,
    bg_color: Tuple[float, float, float, float] = (1, 1, 1, 0.2),
    border_color: Tuple[float, float, float, float] = (0, 0, 0, 1),
) -> None:
    """Draw a rectangle in region space"""
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    shader.bind()
    gpu.state.blend_set("ALPHA")
    gpu.state.line_width_set(2)
    x0, y0 = p0.to_tuple()
    x1, y1 = p1.to_tuple()
    fan = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    shader.uniform_float("color", bg_color)
    batch = batch_for_shader(shader, "TRI_FAN", {"pos": fan})
    batch.draw(shader)
    lines = fan + [fan[0]]
    shader.uniform_float("color", border_color)
    batch = batch_for_shader(shader, "LINE_STRIP", {"pos": lines})
    batch.draw(shader)
