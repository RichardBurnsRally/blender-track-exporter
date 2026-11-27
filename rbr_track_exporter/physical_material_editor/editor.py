"""State shared by the material map tools: which texture is being edited, the
selected region, and the overlay drawn over the Image Editor."""

import array
from typing import Any, Callable, List, Optional, Set, Tuple

import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector

from ..types import MaterialId, SurfaceAge, SurfaceType, material_id_to_color
from .drawing_utils import FONT_ID, draw_rect_region
from .types import GrabHandle

PAINT_TOOL = "rbr.material_map_paint"
FILL_TOOL = "rbr.material_map_fill"
SAMPLE_TOOL = "rbr.material_map_sample"
REGIONS_TOOL = "rbr.material_map_regions"
TOOLS = (PAINT_TOOL, FILL_TOOL, SAMPLE_TOOL, REGIONS_TOOL)
CELL_TOOLS = (PAINT_TOOL, FILL_TOOL, SAMPLE_TOOL)


def grab_handle_size() -> float:
    """Half the drawn size of a resize handle, in region pixels."""
    prefs = bpy.context.preferences
    scale = prefs.system.ui_scale if prefs is not None else 0.0
    return 3.5 * (scale or 1.0)


Report = Callable[[Set[str], str], Any]


def editing_tree(context: bpy.types.Context) -> Optional[bpy.types.NodeTree]:
    wm = context.window_manager
    if wm is None:
        return None
    # A name rather than a pointer, which undo would clear.
    tree = bpy.data.node_groups.get((wm.rbr_material_map_texture, None))
    if tree is None or "internal" not in tree.nodes:
        return None
    return tree


def editing_internal(context: bpy.types.Context) -> Any:
    """The edited texture's ShaderNodeRBRTextureInternal, if any."""
    tree = editing_tree(context)
    return None if tree is None else tree.nodes["internal"]


def active_tool(context: bpy.types.Context) -> Optional[str]:
    space = context.space_data
    if not isinstance(space, bpy.types.SpaceImageEditor) or context.workspace is None:
        return None
    tool = context.workspace.tools.from_space_image_mode(space.mode, create=False)
    return None if tool is None else str(tool.idname)


def is_editing(context: bpy.types.Context) -> bool:
    return editing_tree(context) is not None and active_tool(context) in TOOLS


def selected_region(context: bpy.types.Context, internal: Any) -> Optional[int]:
    wm = context.window_manager
    if wm is None:
        return None
    index = int(wm.rbr_material_map_region)
    return index if 0 <= index < len(internal.material_maps) else None


def select_region(context: bpy.types.Context, index: Optional[int]) -> None:
    if context.window_manager is not None:
        context.window_manager.rbr_material_map_region = -1 if index is None else index


def mouse_uv(context: bpy.types.Context, event: bpy.types.Event) -> Vector:
    region = context.region
    if region is None:
        return Vector((0.0, 0.0))
    return Vector(
        region.view2d.region_to_view(event.mouse_region_x, event.mouse_region_y)
    )


def regions_at(internal: Any, uv: Vector) -> List[int]:
    return [
        i for i, maps in enumerate(internal.material_maps) if maps.point_in_map(*uv)
    ]


def target_region(
    context: bpy.types.Context, internal: Any, uv: Vector
) -> Optional[int]:
    """The region painted at uv: the selected one if it's under the cursor,
    otherwise the topmost one."""
    hits = regions_at(internal, uv)
    if not hits:
        return None
    selected = selected_region(context, internal)
    return selected if selected in hits else hits[-1]


def active_condition(
    context: bpy.types.Context, internal: Any
) -> Tuple[SurfaceType, SurfaceAge]:
    if context.scene is None:
        raise RuntimeError("No active scene")
    settings = context.scene.rbr_scene_settings
    surface_type: SurfaceType = settings.get_active_surface_type()
    surface_age: SurfaceAge = settings.get_active_surface_age()
    if not internal.is_road_surface:
        surface_age = SurfaceAge.NEW
    return surface_type, surface_age


def can_edit(context: bpy.types.Context, internal: Any, report: Report) -> bool:
    """Whether the active condition's maps and fallback can be changed by
    hand. Automatic ones can't; this reports why."""
    surface_type, surface_age = active_condition(context, internal)
    if not internal.auto_wetness.is_auto(surface_type, surface_age):
        return True
    label = surface_type.pretty()
    if internal.is_road_surface:
        label += "/" + surface_age.pretty()
    report({"WARNING"}, f"{label} is automatic")
    return False


def after_edit(
    context: bpy.types.Context, internal: Any, region: Optional[int] = None
) -> None:
    """Call after changing the active condition's maps or fallback."""
    surface_type, surface_age = active_condition(context, internal)
    if surface_type is SurfaceType.DRY:
        internal.auto_wetness.sync(surface_age, region)


def image_editors(
    context: bpy.types.Context,
) -> List[Tuple[bpy.types.Area, bpy.types.SpaceImageEditor]]:
    if context.screen is None:
        return []
    result = []
    for area in context.screen.areas:
        space = area.spaces.active
        if area.ui_type == "IMAGE_EDITOR" and isinstance(
            space, bpy.types.SpaceImageEditor
        ):
            result.append((area, space))
    return result


def redraw_image_editors(context: bpy.types.Context) -> None:
    for area, _ in image_editors(context):
        area.tag_redraw()


def set_image_keeping_view(
    context: bpy.types.Context,
    area: bpy.types.Area,
    space: bpy.types.SpaceImageEditor,
    image: bpy.types.Image,
) -> None:
    """Show another image without the view jumping: Blender restores the zoom
    and pan stored on each image, so carry the current ones across."""
    old = space.image
    if old == image:
        # Setting it again would restore the view Blender last stored on it.
        return
    region = next((r for r in area.regions if r.type == "WINDOW"), None)
    if (
        old is None
        or region is None
        or context.window is None
        or 0 in old.size
        or 0 in image.size
    ):
        space.image = image
        return
    cx, cy = region.view2d.region_to_view(region.width / 2, region.height / 2)
    zoom = space.zoom_percentage / 100 * old.size[0] / image.size[0]
    space.image = image
    width, height = image.size
    # These operators also store the view on the image, so it survives the
    # image being set again. The image is drawn half a pixel off its offset.
    with context.temp_override(window=context.window, area=area, region=region):
        bpy.ops.image.view_all()
        bpy.ops.image.view_zoom_ratio(ratio=zoom)
        bpy.ops.image.view_pan(
            offset=((cx - 0.5) * width - 0.5, (cy - 0.5) * height - 0.5)
        )


def refresh_images(context: bpy.types.Context) -> None:
    """Show the edited texture's image for the active condition."""
    from ..shaders.texture import context_active_image_name

    tree = editing_tree(context)
    if tree is None:
        return
    internal: Any = tree.nodes["internal"]
    node = tree.nodes.get(context_active_image_name(context, internal.is_road_surface))
    if not isinstance(node, bpy.types.ShaderNodeTexImage) or node.image is None:
        return
    for area, space in image_editors(context):
        set_image_keeping_view(context, area, space, node.image)


def region_rect(
    region: bpy.types.Region, maps: Any
) -> Tuple[float, float, float, float]:
    x0, y0 = region.view2d.view_to_region(*maps.position_1, clip=False)
    x1, y1 = region.view2d.view_to_region(*maps.position_2, clip=False)
    return x0, y0, x1, y1


def grab_handle_at(
    region: bpy.types.Region, maps: Any, x: float, y: float
) -> Optional[GrabHandle]:
    x0, y0, x1, y1 = region_rect(region, maps)
    for handle in GrabHandle:
        if not handle.is_grabbable(repeat_x=maps.repeat_x, repeat_y=maps.repeat_y):
            continue
        mx, my = handle.position_relative()
        hx, hy = x0 + (x1 - x0) * mx, y0 + (y1 - y0) * my
        reach = grab_handle_size() * 1.3
        if abs(x - hx) <= reach and abs(y - hy) <= reach:
            return handle
    return None


# A region being dragged out with the regions tool, in UV space.
new_region_drag: Optional[Tuple[Vector, Vector]] = None


def _cells_batch(maps: Any, material_map: Any, alpha: float) -> Any:
    """The region's cells as triangles in UV space."""
    (u0, v0), (u1, v1) = maps.position_1, maps.position_2
    du, dv = (u1 - u0) / 16, (v1 - v0) / 16
    positions = []
    colors = []
    for i, row in enumerate(material_map.rows):
        for j, col in enumerate(row.cols):
            rgb = material_id_to_color(MaterialId(col.material_id))
            color = (rgb.r / 255, rgb.g / 255, rgb.b / 255, alpha)
            cu0, cv0 = u0 + du * j, v0 + dv * i
            cu1, cv1 = cu0 + du, cv0 + dv
            positions += [
                (cu0, cv0),
                (cu1, cv0),
                (cu1, cv1),
                (cu0, cv0),
                (cu1, cv1),
                (cu0, cv1),
            ]
            colors += [color] * 6
    shader = gpu.shader.from_builtin("FLAT_COLOR")
    return batch_for_shader(shader, "TRIS", {"pos": positions, "color": colors})


# Cell batches per (texture, condition, region, opacity). Building them reads
# every cell, so they're only rebuilt after invalidate().
_cell_batches: dict[Tuple[str, SurfaceType, SurfaceAge, int, float], Any] = {}


def _draw_cells(
    region: bpy.types.Region,
    internal: Any,
    index: int,
    condition: Tuple[SurfaceType, SurfaceAge],
    alpha: float,
) -> None:
    key = (internal.id_data.name, *condition, index, alpha)
    batch = _cell_batches.get(key)
    if batch is None:
        maps = internal.material_maps[index]
        batch = _cells_batch(maps, maps.get_map(*condition), alpha)
        _cell_batches[key] = batch
    x0, y0 = region.view2d.view_to_region(0.0, 0.0, clip=False)
    x1, y1 = region.view2d.view_to_region(1.0, 1.0, clip=False)
    uv_to_region = Matrix(
        ((x1 - x0, 0, 0, x0), (0, y1 - y0, 0, y0), (0, 0, 1, 0), (0, 0, 0, 1))
    )
    shader = gpu.shader.from_builtin("FLAT_COLOR")
    gpu.matrix.push()
    try:
        gpu.matrix.multiply_matrix(uv_to_region)
        batch.draw(shader)
    finally:
        gpu.matrix.pop()


def _draw_lines(
    lines: List[Tuple[float, float]], color: Tuple[float, float, float, float]
) -> None:
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    shader.bind()
    shader.uniform_float("color", color)
    batch_for_shader(shader, "LINES", {"pos": lines}).draw(shader)


def _outline(x0: float, y0: float, x1: float, y1: float) -> List[Tuple[float, float]]:
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return [p for k in range(4) for p in (corners[k], corners[(k + 1) % 4])]


def draw_overlay() -> None:
    context = bpy.context
    region = context.region
    if region is None or not is_editing(context):
        return
    internal = editing_internal(context)
    tool = active_tool(context)
    surface_type, surface_age = active_condition(context, internal)
    all_maps = internal.material_maps
    selected = selected_region(context, internal)
    alpha = internal.material_picker.alpha

    gpu.state.blend_set("ALPHA")
    gpu.state.line_width_set(2)
    order = [i for i in range(len(all_maps)) if i != selected]
    if selected is not None:
        order.append(selected)
    for i in order:
        _draw_cells(region, internal, i, (surface_type, surface_age), alpha)
        _draw_lines(_outline(*region_rect(region, all_maps[i])), (0, 0, 0, 1))
    if selected is not None:
        maps = all_maps[selected]
        x0, y0, x1, y1 = region_rect(region, maps)
        grid = []
        for k in range(1, 16):
            x = x0 + (x1 - x0) * k / 16
            y = y0 + (y1 - y0) * k / 16
            grid += [(x, y0), (x, y1), (x0, y), (x1, y)]
        gpu.state.line_width_set(1)
        _draw_lines(grid, (1, 1, 1, 0.4))
        gpu.state.line_width_set(2)
        _draw_lines(_outline(x0, y0, x1, y1), (1, 1, 1, 1))
        if tool == REGIONS_TOOL:
            for handle in GrabHandle:
                grabbable = handle.is_grabbable(
                    repeat_x=maps.repeat_x, repeat_y=maps.repeat_y
                )
                mx, my = handle.position_relative()
                p = Vector((x0 + (x1 - x0) * mx, y0 + (y1 - y0) * my))
                size = Vector((grab_handle_size(), grab_handle_size()))
                draw_rect_region(
                    p - size,
                    p + size,
                    bg_color=(1, 1, 1, 1) if grabbable else (0.4, 0.4, 0.4, 1),
                    border_color=(0, 0, 0, 1),
                )
    if new_region_drag is not None:
        start, end = new_region_drag
        sx, sy = region.view2d.view_to_region(*start, clip=False)
        ex, ey = region.view2d.view_to_region(*end, clip=False)
        _draw_lines(_outline(sx, sy, ex, ey), (1, 1, 1, 1))

    if tool in CELL_TOOLS:
        _draw_hovered_cell(context, region, internal)


# The hovered cell per Image Editor region, as (region index, x, y).
hovered_cells: dict[int, Tuple[int, int, int]] = {}


def handle_cursor(handle: GrabHandle) -> str:
    if handle in (GrabHandle.MID_LEFT, GrabHandle.MID_RIGHT):
        return "MOVE_X"
    if handle in (GrabHandle.TOP_MID, GrabHandle.BOTTOM_MID):
        return "MOVE_Y"
    return "SCROLL_XY"


def regions_cursor(
    context: bpy.types.Context, region: bpy.types.Region, x: float, y: float
) -> str:
    """The cursor for what a click of the regions tool at x, y would do."""
    internal = editing_internal(context)
    selected = selected_region(context, internal)
    if selected is not None:
        handle = grab_handle_at(region, internal.material_maps[selected], x, y)
        if handle is not None:
            return handle_cursor(handle)
    if regions_at(internal, Vector(region.view2d.region_to_view(x, y))):
        return "HAND"
    return "CROSSHAIR"


def draw_cursor(context: bpy.types.Context, xy: Tuple[int, int]) -> None:
    """Track the cell under the cursor. The overlay draws it, so ask for a
    redraw when it changes. The regions tool shows what a click would do."""
    context = bpy.context
    region = context.region
    if region is None or not is_editing(context):
        return
    rx, ry = xy[0] - region.x, xy[1] - region.y
    if active_tool(context) == REGIONS_TOOL:
        if context.window is not None:
            context.window.cursor_set(regions_cursor(context, region, rx, ry))
        return
    internal = editing_internal(context)
    uv = Vector(region.view2d.region_to_view(rx, ry))
    index = target_region(context, internal, uv)
    key = region.as_pointer()
    hovered = None
    if index is not None:
        hovered = (index, *internal.material_maps[index].pixel(*uv))
    if hovered_cells.get(key) != hovered:
        if hovered is None:
            hovered_cells.pop(key, None)
        else:
            hovered_cells[key] = hovered
        region.tag_redraw()


def _draw_hovered_cell(
    context: bpy.types.Context, region: bpy.types.Region, internal: Any
) -> None:
    hovered = hovered_cells.get(region.as_pointer())
    if hovered is None or hovered[0] >= len(internal.material_maps):
        return
    index, px, py = hovered
    maps = internal.material_maps[index]
    x0, y0, x1, y1 = region_rect(region, maps)
    dx, dy = (x1 - x0) / 16, (y1 - y0) / 16
    cx, cy = x0 + dx * px, y0 + dy * py
    draw_rect_region(
        Vector((cx, cy)),
        Vector((cx + dx, cy + dy)),
        bg_color=(1, 1, 1, 0.3),
        border_color=(1, 1, 1, 1),
    )
    surface_type, surface_age = active_condition(context, internal)
    cell = maps.get_map(surface_type, surface_age).rows[py].cols[px]
    if bpy.context.preferences is None:
        return
    scale = bpy.context.preferences.system.ui_scale
    blf.size(FONT_ID, round(scale * 11))
    blf.color(FONT_ID, 1, 1, 1, 1)
    blf.enable(FONT_ID, blf.SHADOW)
    blf.shadow(FONT_ID, 3, 0, 0, 0, 1)
    blf.position(FONT_ID, cx + dx + 6 * scale, cy + dy / 2 - 4 * scale, 0)
    blf.draw(FONT_ID, MaterialId(cell.material_id).pretty())
    blf.disable(FONT_ID, blf.SHADOW)


# Per texture name, the conditions with an undefined cell or fallback. Cleared
# whenever maps may have changed.
_undefined_cache: dict[str, Set[Tuple[SurfaceType, SurfaceAge]]] = {}


def invalidate() -> None:
    """Call after material maps may have changed."""
    _undefined_cache.clear()
    _cell_batches.clear()


def undefined_conditions(internal: Any) -> Set[Tuple[SurfaceType, SurfaceAge]]:
    name = internal.id_data.name
    cached = _undefined_cache.get(name)
    if cached is not None:
        return cached
    undefined = MaterialId.UNDEFINED.value
    ages = list(SurfaceAge) if internal.is_road_surface else [SurfaceAge.NEW]
    row_ids = array.array("i", [0] * 16)
    found = set()
    for surface_type in SurfaceType:
        for age in ages:
            if internal.fallback_materials.get_condition(surface_type, age) is (
                MaterialId.UNDEFINED
            ):
                found.add((surface_type, age))
                continue
            for maps in internal.material_maps:
                rows = maps.get_map(surface_type, age).rows
                if any(_row_has(row, row_ids, undefined) for row in rows):
                    found.add((surface_type, age))
                    break
    _undefined_cache[name] = found
    return found


def _row_has(row: Any, buffer: "array.array[int]", value: int) -> bool:
    row.cols.foreach_get("material_id", buffer)
    return value in buffer


@bpy.app.handlers.persistent  # type: ignore
def _invalidate_handler(*_args: Any) -> None:
    invalidate()


@bpy.app.handlers.persistent  # type: ignore
def _depsgraph_handler(_scene: Any, depsgraph: bpy.types.Depsgraph) -> None:
    if any(isinstance(u.id, bpy.types.NodeTree) for u in depsgraph.updates):
        invalidate()


_HANDLERS = (
    bpy.app.handlers.undo_post,
    bpy.app.handlers.redo_post,
    bpy.app.handlers.load_post,
)

_draw_handle: Any = None


def register() -> None:
    global _draw_handle
    for handlers in _HANDLERS:
        handlers.append(_invalidate_handler)
    bpy.app.handlers.depsgraph_update_post.append(_depsgraph_handler)
    bpy.types.WindowManager.rbr_material_map_texture = bpy.props.StringProperty()
    bpy.types.WindowManager.rbr_material_map_region = bpy.props.IntProperty(default=-1)
    _draw_handle = bpy.types.SpaceImageEditor.draw_handler_add(
        draw_overlay, (), "WINDOW", "POST_PIXEL"
    )


def unregister() -> None:
    global _draw_handle
    for handlers in _HANDLERS:
        if _invalidate_handler in handlers:
            handlers.remove(_invalidate_handler)
    if _depsgraph_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_depsgraph_handler)
    if _draw_handle is not None:
        bpy.types.SpaceImageEditor.draw_handler_remove(_draw_handle, "WINDOW")
        _draw_handle = None
    del bpy.types.WindowManager.rbr_material_map_region
    del bpy.types.WindowManager.rbr_material_map_texture
