"""The on-demand migration steps. Each reads the old addon's leftover ID
properties, so it can run at any time after the automatic pass."""

from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import bmesh
import bpy
from mathutils import Vector

from . import gnodes, legacy, tables
from .legacy import Log, old_settings, old_type

# ---------------------------------------------------------------- unexported
NOT_EXPORTED_COLLECTION = "not-exported"
MIGRATED_PROP = "rbr_legacy_migrated"


def unexported_objects() -> List[bpy.types.Object]:
    return [
        obj
        for obj in bpy.data.objects
        if obj.library is None
        and old_settings(obj) is not None
        and old_settings(obj).get("exported", 1) == 0
    ]


def move_unexported(log: Log) -> int:
    objects = unexported_objects()
    for obj in objects:
        for scene in bpy.data.scenes:
            if obj.name not in scene.objects:
                continue
            excluded = bpy.data.collections.get(NOT_EXPORTED_COLLECTION)
            if excluded is None:
                excluded = bpy.data.collections.new(NOT_EXPORTED_COLLECTION)
            if excluded.name not in scene.collection.children:
                scene.collection.children.link(excluded)
            for collection in list(obj.users_collection):
                if collection != excluded and obj.name in collection.objects:
                    collection.objects.unlink(obj)
            if obj.name not in excluded.objects:
                excluded.objects.link(obj)
            for view_layer in scene.view_layers:
                layer = view_layer.layer_collection.children.get(excluded.name)
                if layer is not None:
                    layer.exclude = True
        log.info(
            f"'{obj.name}' moved to the excluded '{NOT_EXPORTED_COLLECTION}' collection"
        )
    return len(objects)


# ---------------------------------------------------------------- duplicates
def _copy_suffix(
    kept: legacy.MaterialWant, mesh_type: str, options: Dict[str, Any]
) -> str:
    """Name a split material after what differs from the kept one."""
    if mesh_type != kept[0]:
        return mesh_type.replace("_", "-").lower()
    parts = []
    for name, value in options.items():
        if kept[1].get(name) == value:
            continue
        if isinstance(value, bool):
            parts.append(("" if value else "no-") + name.split("_")[-1])
        else:
            parts.append(str(value).replace("_", "-").lower())
    return "-".join(parts) or mesh_type.replace("_", "-").lower()


def duplicate_shared(log: Log) -> int:
    count = 0
    wants = legacy.material_wants()
    conflicts = legacy.material_conflicts(wants)
    for material, groups in conflicts.items():
        if material.library is not None:
            continue
        kept = legacy.primary_want(material, wants[material])
        kept_key = (kept[0],) + tuple(sorted(kept[1].items()))
        for key, objects in groups.items():
            if key == kept_key:
                continue
            mesh_type = key[0]
            options = dict(key[1:])
            copy = material.copy()
            copy.name = f"{material.name}-{_copy_suffix(kept, mesh_type, options)}"
            legacy.apply_material_settings(copy, mesh_type, options, log)
            for obj in objects:
                for slot in obj.material_slots:
                    if slot.material == material:
                        slot.material = copy
            log.info(
                f"material '{material.name}' split: '{copy.name}' for {len(objects)} object(s)"
            )
            count += 1
    for mesh, mesh_groups in legacy.mesh_wants().items():
        if mesh.library is not None or len(mesh_groups) < 2:
            continue
        first = True
        for material_id, objects in mesh_groups.items():
            if first:
                first = False
                continue
            copy = mesh.copy()
            entry = tables.OLD_SCM_MATERIAL.get(material_id)
            suffix = entry[0].lower() if entry else str(material_id)
            copy.name = f"{mesh.name}-{suffix}"
            copy.rbr_mesh_settings.mesh_type = "STATIC_SHAPE_COLLISION"
            legacy._set_collision_physics(
                copy.rbr_mesh_settings.collision_physics,
                material_id,
                log,
                f"collision mesh '{copy.name}'",
            )
            for obj in objects:
                obj.data = copy
            log.info(
                f"collision mesh '{mesh.name}' split: '{copy.name}' for {len(objects)} object(s)"
            )
            count += 1
    return count


# ---------------------------------------------------------------- textures
def texture_formats(log: Log) -> int:
    count = 0
    transparent = legacy.transparent_texture_trees()
    for node_tree in bpy.data.node_groups:
        if node_tree.library is not None or not node_tree.name.startswith(
            ".RBRTextureV0."
        ):
            continue
        internal = node_tree.nodes.get("internal")
        if internal is None or internal.passthrough_dds:
            continue
        image = None
        for name in ("dry/new", "damp/new", "wet/new"):
            node = node_tree.nodes.get(name)
            if (
                isinstance(node, bpy.types.ShaderNodeTexImage)
                and node.image is not None
            ):
                image = node.image
                break
        if image is None:
            continue
        path = bpy.path.abspath(image.filepath, library=image.library)
        fmt = legacy.dds_format(path)
        if fmt == "DXT1" and node_tree.name in transparent:
            fmt = "DXT1_1BIT"
        if fmt is None:
            log.manual(
                f"texture '{node_tree.name[len('.RBRTextureV0.'):]}': could not read a DDS header from '{image.filepath}', left as DXT1"
            )
            continue
        internal.texture_format = fmt
        count += 1
    log.info(f"{count} texture format(s) read from .dds headers")
    return count


# ---------------------------------------------------------------- cameras
def _find_fcurve(obj: bpy.types.Object, data_path: str) -> Tuple[Any, Any]:
    return legacy.find_fcurve(obj, data_path)


def follow_path_cameras() -> (
    List[Tuple[bpy.types.Object, bpy.types.FollowPathConstraint]]
):
    found: List[Tuple[bpy.types.Object, bpy.types.FollowPathConstraint]] = []
    for obj in bpy.data.objects:
        if obj.library is not None or old_type(obj) != "CAMERA":
            continue
        camera = obj.data
        if (
            isinstance(camera, bpy.types.Camera)
            and camera.rbr_camera_settings.follow_path is not None
        ):
            continue
        for constraint in obj.constraints:
            if (
                isinstance(constraint, bpy.types.FollowPathConstraint)
                and constraint.target is not None
            ):
                found.append((obj, constraint))
                break
    return found


def convert_follow_paths(log: Log) -> int:
    count = 0
    for obj, constraint in follow_path_cameras():
        camera = obj.data
        if not isinstance(camera, bpy.types.Camera):
            continue
        target = constraint.target
        if target is None or not isinstance(target.data, bpy.types.Curve):
            continue
        duration = float(target.data.path_duration) or 1.0
        keyframes = []
        fcurve, channelbag = _find_fcurve(
            obj, f'constraints["{constraint.name}"].offset'
        )
        if fcurve is not None:
            for point in fcurve.keyframe_points:
                keyframes.append((point.co.x, point.co.y, point.interpolation))
            channelbag.fcurves.remove(fcurve)
        obj.constraints.remove(constraint)
        camera.rbr_camera_settings.follow_path = target
        new_constraint = obj.constraints.get("Follow Path")
        if not isinstance(new_constraint, bpy.types.FollowPathConstraint):
            log.manual(
                f"camera '{obj.name}': the follow path constraint could not be recreated"
            )
            continue
        for frame, offset, interpolation in keyframes:
            new_constraint.offset_factor = min(max(-offset / duration, 0.0), 1.0)
            new_constraint.keyframe_insert("offset_factor", frame=frame)
        new_fcurve, _ = _find_fcurve(obj, 'constraints["Follow Path"].offset_factor')
        if new_fcurve is not None:
            for point, (_, _, interpolation) in zip(
                new_fcurve.keyframe_points, keyframes
            ):
                point.interpolation = interpolation
        log.info(
            f"camera '{obj.name}': follows '{target.name}' with {len(keyframes)} keyframe(s)"
        )
        count += 1
    return count


# ---------------------------------------------------------------- brake wall
def brake_walls() -> List[Tuple[List[bpy.types.Scene], bpy.types.Object]]:
    """Old brake wall meshes not yet converted, with the scenes using them."""
    found: Dict[str, Tuple[List[bpy.types.Scene], bpy.types.Object]] = {}
    for scene in bpy.data.scenes:
        for obj in scene.objects:
            if (
                obj.library is None
                and old_type(obj) == "BRAKE_WALL"
                and isinstance(obj.data, bpy.types.Mesh)
                and not obj.get(MIGRATED_PROP)
            ):
                found.setdefault(obj.name, ([], obj))[0].append(scene)
                break
    return list(found.values())


def _vertex_members(
    obj: bpy.types.Object, mesh: bpy.types.Mesh, name: str
) -> Optional[Set[int]]:
    """Vertices in a vertex group, or with a truthy point attribute of that
    name (the way geometry nodes brake walls mark them)."""
    group = obj.vertex_groups.get(name)
    if group is not None:
        return {
            vert.index
            for vert in mesh.vertices
            for element in vert.groups
            if element.group == group.index
        }
    attribute = mesh.attributes.get(name)
    if attribute is None or attribute.domain != "POINT":
        return None
    if attribute.data_type not in ("BOOLEAN", "FLOAT", "INT"):
        return None
    return {i for i, element in enumerate(attribute.data) if element.value > 0}


def _walk_brake_wall(
    obj: bpy.types.Object, log: Log
) -> Optional[List[Tuple[Vector, Vector, bool]]]:
    """Port of the old exporter's walk: pairs of (inner, outer, respawn) in
    world space, in the mesh's own order."""
    settings = old_settings(obj)
    inner_name = settings.get("brake_wall_inner_group", "inner")
    outer_name = settings.get("brake_wall_outer_group", "outer")
    respawn_name = settings.get("brake_wall_respawn_group", "respawn")
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.data
    assert isinstance(mesh, bpy.types.Mesh)
    inner_members = _vertex_members(obj, mesh, inner_name)
    outer_members = _vertex_members(obj, mesh, outer_name)
    respawn_members = _vertex_members(obj, mesh, respawn_name) or set()
    if inner_members is None or outer_members is None:
        log.manual(
            f"brake wall '{obj.name}': vertex groups or attributes '{inner_name}' and '{outer_name}' are needed"
        )
        return None
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        flags = bm.verts.layers.int.new("rbr_legacy_flags")
        bm.verts.ensure_lookup_table()
        for vert in bm.verts:
            vert[flags] = (
                (1 if vert.index in inner_members else 0)
                | (2 if vert.index in outer_members else 0)
                | (4 if vert.index in respawn_members else 0)
            )
        inner: Set[int] = set()
        outer: Set[int] = set()
        respawn: Set[int] = set()
        for vert in bm.verts:
            is_inner = bool(vert[flags] & 1)
            is_outer = bool(vert[flags] & 2)
            if is_inner and not is_outer:
                inner.add(vert.index)
            elif is_outer and not is_inner:
                outer.add(vert.index)
            else:
                log.manual(
                    f"brake wall '{obj.name}': vertex at {tuple(round(c, 2) for c in vert.co)} is in neither or both groups"
                )
                return None
            if vert[flags] & 4:
                respawn.add(vert.index)
        if not inner or len(inner) != len(outer):
            log.manual(
                f"brake wall '{obj.name}': {len(inner)} inner and {len(outer)} outer vertices, they must match"
            )
            return None
        matrix = obj.matrix_world
        visited: Set[int] = set()
        pairs: List[Tuple[Vector, Vector, bool]] = []
        current = next(iter(inner))
        while True:
            vert = bm.verts[current]
            next_inner = None
            outer_index = None
            for edge in vert.link_edges:
                other = edge.other_vert(vert).index
                if other in inner:
                    if other not in visited and next_inner is None:
                        next_inner = other
                elif other in outer:
                    outer_index = other
            if outer_index is None:
                log.manual(
                    f"brake wall '{obj.name}': inner vertex at {tuple(round(c, 2) for c in vert.co)} has no outer partner"
                )
                return None
            visited.add(current)
            pairs.append(
                (
                    (matrix @ vert.co).copy(),
                    (matrix @ bm.verts[outer_index].co).copy(),
                    current in respawn or outer_index in respawn,
                )
            )
            if next_inner is None or len(visited) == len(inner):
                return pairs
            current = next_inner
    finally:
        bm.free()


def _winding(points: List[Vector]) -> float:
    result = 0.0
    for i, p1 in enumerate(points):
        p2 = points[(i + 1) % len(points)]
        result += (p2.x - p1.x) * (p2.y + p1.y)
    return result


def convert_brake_walls(log: Log) -> int:
    count = 0
    for scenes, obj in brake_walls():
        scene = scenes[0]
        pairs = _walk_brake_wall(obj, log)
        if pairs is None:
            continue
        if _winding([p[1] for p in pairs]) < 0:
            pairs.reverse()
        n = len(pairs)
        curve = bpy.data.curves.new(f"{obj.name}-curve", "CURVE")
        curve.dimensions = "3D"
        curve.twist_mode = "Z_UP"
        spline = curve.splines.new("POLY")
        spline.points.add(n - 1)
        spline.use_cyclic_u = True
        outer_points = [Vector((p[1].x, p[1].y)) for p in pairs]
        inner_points = [Vector((p[0].x, p[0].y)) for p in pairs]
        for i, point in enumerate(spline.points):
            point.co = (outer_points[i].x, outer_points[i].y, 0.0, 1.0)
            point.radius = (outer_points[i] - inner_points[i]).length
            prev = outer_points[(i - 1) % n]
            this = outer_points[i]
            nxt = outer_points[(i + 1) % n]
            tangent = (
                (this - prev).normalized() + (nxt - this).normalized()
            ).normalized()
            normal = Vector((tangent.y, -tangent.x))
            to_inner = inner_points[i] - this
            point.tilt = normal.angle_signed(to_inner) if to_inner.length > 0 else 0.0
        wall = bpy.data.objects.new(f"{obj.name}-curve", curve)
        scene.collection.objects.link(wall)
        wall.show_wire = True
        respawn_collection = bpy.data.collections.new(f"{obj.name}-respawn-areas")
        scene.collection.children.link(respawn_collection)
        for other in scenes:
            if wall.name not in other.objects:
                other.collection.objects.link(wall)
            if respawn_collection.name not in other.collection.children:
                other.collection.children.link(respawn_collection)
            if old_settings(obj).get("exported", 1):
                with bpy.context.temp_override(scene=other):
                    other.rbr_scene_settings.brake_wall = wall
        modifier = wall.modifiers.get(".rbr.brake_wall")
        if isinstance(modifier, bpy.types.NodesModifier):
            from ..blender_utils import gnodes_input

            gnodes_input(modifier, "Socket_2").value = respawn_collection
        areas = 0
        for i in range(n):
            if not pairs[i][2]:
                continue
            this_outer = outer_points[i]
            next_outer = outer_points[(i + 1) % n]
            this_inner = inner_points[i]
            next_inner = inner_points[(i + 1) % n]
            tangent_axis = (next_outer - this_outer).normalized()
            cross_axis = Vector((tangent_axis.y, -tangent_axis.x))
            angle = tangent_axis.angle_signed(Vector((1.0, 0.0)))
            tangents = [
                0.0,
                (next_outer - this_outer).dot(tangent_axis),
                (next_inner - this_outer).dot(tangent_axis),
                (this_inner - this_outer).dot(tangent_axis),
            ]
            crosses = [
                (next_inner - this_outer).dot(cross_axis),
                (this_inner - this_outer).dot(cross_axis),
            ]
            tangent_min, tangent_max = min(tangents), max(tangents)
            cross_length = max(crosses)
            tangent_length = tangent_max - tangent_min
            midpoint = (
                this_outer
                + tangent_axis * tangent_min
                + 0.5 * (tangent_axis * tangent_length + cross_axis * cross_length)
            )
            area = bpy.data.objects.new("respawn-area", None)
            respawn_collection.objects.link(area)
            area.empty_display_type = "CUBE"
            area.empty_display_size = 0.5
            area.rotation_mode = "XYZ"
            area.rotation_euler = (0.0, 0.0, -angle)
            area.location = (midpoint.x, midpoint.y, 0.0)
            area.scale = (tangent_length, cross_length, 1.0)
            areas += 1
        obj.hide_viewport = True
        obj.hide_render = True
        obj[MIGRATED_PROP] = True
        log.info(
            f"brake wall '{obj.name}': curve with {n} points and {areas} respawn area(s); the old mesh is hidden"
        )
        if not old_settings(obj).get("exported", 1):
            log.manual(
                f"brake wall '{obj.name}' had export unticked, so '{wall.name}' is not set as the scene brake wall"
            )
        count += 1
    return count


# ---------------------------------------------------------------- registry
STEPS: List[Tuple[str, str, Callable[[], int]]] = [
    ("brake_wall", "Brake wall mesh to curve", lambda: len(brake_walls())),
    ("follow_path", "Camera follow path keyframes", lambda: len(follow_path_cameras())),
    ("texture_format", "Texture formats from .dds headers", lambda: 1),
    (
        "duplicate_shared",
        "Split materials and meshes with conflicting settings",
        lambda: len(legacy.material_conflicts(legacy.material_wants()))
        + sum(1 for g in legacy.mesh_wants().values() if len(g) > 1),
    ),
    (
        "unexported",
        "Move objects with export unticked out of the export",
        lambda: len(unexported_objects()),
    ),
    (
        "node_maths",
        "Move node maths into geometry nodes",
        lambda: len(gnodes.candidates()),
    ),
]

RUNNERS = {
    "brake_wall": convert_brake_walls,
    "follow_path": convert_follow_paths,
    "texture_format": texture_formats,
    "duplicate_shared": duplicate_shared,
    "unexported": move_unexported,
    "node_maths": gnodes.move_node_maths,
}


def applicable() -> Dict[str, int]:
    return {key: count() for key, _, count in STEPS}
