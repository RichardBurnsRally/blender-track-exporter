from typing import Optional, Tuple

import bpy
import blf
import gpu
import gpu_extras
from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d

from ..properties.curve import RBRCurveSettings
from ..types import PacenoteId

pacenote_draw_handler = None


def draw_pacenotes_in_3d() -> None:
    context = bpy.context
    obj = context.active_object
    if obj is None:
        return
    if context.scene is None:
        return
    scene_settings = context.scene.rbr_scene_settings
    if obj != scene_settings.driveline:
        return
    if not isinstance(obj.data, bpy.types.Curve):
        return
    curve = obj.data
    curve_settings: RBRCurveSettings = curve.rbr_curve_settings
    if len(curve.splines) == 0:
        return
    spline = curve.splines[0]
    if spline.type != "BEZIER":
        return None

    # Build sorted list of pacenotes and events
    last_location = -1.0
    events = [
        (curve_settings.event_start, PacenoteId.EVENT_START.value),
        (curve_settings.event_split_1, PacenoteId.EVENT_CHECKPOINT.value),
        (curve_settings.event_split_2, PacenoteId.EVENT_CHECKPOINT.value),
        (curve_settings.event_finish, PacenoteId.EVENT_FINISH.value),
        (curve_settings.event_end_of_stage, PacenoteId.EVENT_ENDSTAGE.value),
    ]
    events.sort(key=lambda t: t[0])
    notes = []

    def append_note(location: float, id: int) -> None:
        nonlocal last_location
        while len(events) > 0 and events[0][0] <= location:
            notes.append(events.pop(0))
        notes.append((location, id))
        last_location = location

    for index in curve_settings.get_sorted_pacenote_indices():
        pacenote = curve_settings.pacenotes[index]
        append_note(pacenote.location, pacenote.pacenote_id)
    notes.extend(events)

    # x/y offset of text compared to point (screen space)
    offset = 15

    pacenote_stack = []
    lines = []
    lines_colors = []
    points = []
    points_colors = []
    # Optimisation for position_along_spline
    last_min_point = (0, 0.0)

    for location, note_id in notes:
        m_pos_spline = position_along_spline(
            spline=spline,
            distance_along_spline=location,
            min_point=last_min_point,
        )
        if m_pos_spline is None:
            continue
        last_min_point_prime, pos_spline = m_pos_spline
        pos_spline = obj.matrix_world @ pos_spline
        last_min_point = last_min_point_prime
        if context.region is None or context.region_data is None:
            continue
        pos = location_3d_to_region_2d(
            context.region,
            context.region_data,
            pos_spline,
        )
        # Returns None when the pacenote is off screen, so we just skip it
        if pos is None:
            continue
        # Calculate a nice alpha value so far away notes fade out
        camera_pos = context.region_data.view_matrix.inverted().translation
        view_dist = (pos_spline - camera_pos).length
        near = 200
        far = curve_settings.alpha_far
        depth = min(max(view_dist, near), far)
        alpha = 1 - (depth - near) / (far - near)
        pacenote_stack.append((note_id, pos, alpha))
        lines.append((pos.x, pos.y))
        lines.append((pos.x + offset, pos.y + offset))
        lines_colors.append((1, 1, 1, alpha))
        lines_colors.append((1, 1, 1, alpha))
        points.append((pos.x, pos.y))
        points_colors.append((1, 1, 1, alpha))

    # Draw a small line from the driveline to the position of the text
    gpu.state.line_width_set(2)
    shader = gpu.shader.from_builtin("SMOOTH_COLOR")
    shader.bind()
    batch = gpu_extras.batch.batch_for_shader(
        shader, "LINES", {"pos": lines, "color": lines_colors}
    )
    gpu.state.blend_set("ALPHA")
    batch.draw(shader)
    batch = gpu_extras.batch.batch_for_shader(
        shader, "POINTS", {"pos": points, "color": points_colors}
    )
    batch.draw(shader)

    # Draw text for each note
    for pacenote, pos, alpha in pacenote_stack:
        try:
            pid = PacenoteId(pacenote)
            is_event = pid.is_event()
            label = pid.pretty()
        except ValueError:
            is_event = False
            label = "Unknown"
        FONT_ID = 0
        blf.position(FONT_ID, pos.x + offset + 2, pos.y + offset + 2, 0)
        if is_event:
            blf.color(FONT_ID, 0.91, 0.49, 0.05, alpha)
        else:
            blf.color(FONT_ID, 1, 1, 1, alpha)
        blf.size(FONT_ID, 20)
        blf.draw(FONT_ID, label)


def interpolate_cubic_bezier(
    bsp0: bpy.types.BezierSplinePoint,
    bsp1: bpy.types.BezierSplinePoint,
    t: float,
) -> Vector:
    """Get the position at a certain point along the cubic bezier spline
    segment

    bsp0
        First bezier point
    bsp1
        Second bezier point
    t
        Relative position on curve (range: [0, 1])
    """
    p0 = bsp0.co
    p1 = bsp0.handle_right
    p2 = bsp1.handle_left
    p3 = bsp1.co
    r = 1 - t
    a = r * r * r * p0
    b = 3 * r * r * t * p1
    c = 3 * r * t * t * p2
    d = t * t * t * p3
    return a + b + c + d


def walk_cubic_bezier_segment(
    bsp0: bpy.types.BezierSplinePoint,
    bsp1: bpy.types.BezierSplinePoint,
    distance_along_segment: float,
    resolution: int = 16,
) -> Tuple[float, Optional[Vector]]:
    """Walk along a segment and return the segment length and the point which
    is at distance_along_segment. Returns None if the point is not on the
    segment.
    """
    walked = 0.0
    last_pos = bsp0.co
    pos_to_return = None
    for i in range(resolution + 2):
        t = i / (resolution + 1)
        pos = interpolate_cubic_bezier(bsp0, bsp1, t)
        # A vector pointing from the last position to this position
        segment = pos - last_pos
        # If the point we seek lies on this segment
        if walked <= distance_along_segment <= walked + segment.length:
            # Linear interpolation between last position and this position
            pos_to_return = last_pos + segment.normalized() * (
                distance_along_segment - walked
            )
        walked += segment.length
        last_pos = pos
    return (walked, pos_to_return)


def position_along_spline(
    spline: bpy.types.Spline,
    distance_along_spline: float,
    min_point: Tuple[int, float] = (0, 0.0),
) -> Optional[Tuple[Tuple[int, float], Vector]]:
    """Compute the position from a distance along a spline.

    spline
        The spline we are walking along
    distance_along_spline
        The distance along the spline to walk
    min_point
        Optimisation - the minimum point to consider and the distance
        (previously) walked to the minimum point

    Returns None if the point does not lie on the spline.
    Otherwise returns a tuple of:
        - The index of the segment the point lies on
        - The total distance walked along the spline up to that segment
        - The world position
    The first two of these can be plugged back into future invocations,
    provided we are walking a sorted list of points. This turns a quadratic
    algorithm into a linear one.
    """
    distance_travelled_from_min_point = 0.0
    for i in range(min_point[0], len(spline.bezier_points) - 1):
        bsp0 = spline.bezier_points[i]
        bsp1 = spline.bezier_points[i + 1]
        distance_along_segment = (
            distance_along_spline - min_point[1] - distance_travelled_from_min_point
        )
        segment_length, pos = walk_cubic_bezier_segment(
            bsp0, bsp1, distance_along_segment
        )
        if pos is not None:
            # The point lies on this segment
            return ((i, min_point[1] + distance_travelled_from_min_point), pos)
        else:
            distance_travelled_from_min_point += segment_length
    return None


def register() -> None:
    global pacenote_draw_handler
    pacenote_draw_handler = bpy.types.SpaceView3D.draw_handler_add(
        draw_pacenotes_in_3d,
        (),
        "WINDOW",
        "POST_PIXEL",
    )


def unregister() -> None:
    bpy.types.SpaceView3D.draw_handler_remove(pacenote_draw_handler, "WINDOW")
