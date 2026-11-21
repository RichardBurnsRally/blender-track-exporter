"""The automatic part of migrating a file made with the pre-Rust addon.

Everything here reads the old addon's data as plain ID properties (its
property groups are no longer registered) and writes the new addon's
properties. Old properties are left in place so the optional steps can be
run later.
"""

import ast
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import bpy

from . import tables
from ..blender_utils import gnodes_input, narrow
from ..gnodes.fence import GNODES_FENCE_SUBDIVIDE, GNODES_FENCE_VCOL
from ..properties.fence import recreate_fence_node_group
from ..shaders import sky, texture
from ..shaders.refresh import pop_links, push_links, refresh_all_rbr_shaders
from ..shaders.shader_node import ShaderNodeRBR
from ..shaders.uv_velocity import setup_uv_velocity_node_tree
from ..types import CloudName, TintSet


class Log:
    """Collects what the migration did and what is left for the user, and
    echoes it to the console."""

    def __init__(self) -> None:
        self.done: List[str] = []
        self.todo: List[str] = []

    def info(self, message: str) -> None:
        self.done.append(message)
        print(f"RBR migration: {message}")

    def manual(self, message: str) -> None:
        self.todo.append(message)
        print(f"RBR migration TODO: {message}")


class LibraryBlocked(Exception):
    def __init__(self, libraries: List[str]):
        super().__init__(", ".join(libraries))
        self.libraries = libraries


# ---------------------------------------------------------------- detection
def legacy_version(scene: bpy.types.Scene) -> Optional[str]:
    """The old addon version string stored in the scene, if the scene was
    last saved by the old addon."""
    version = getattr(scene, "rbr_addon_version", "")
    if isinstance(version, str) and version.startswith("(0,"):
        return version
    if version == "" and (
        "rbr_track_settings" in scene.keys() or "rbr_export_settings" in scene.keys()
    ):
        return "(0, ?)"
    return None


def oldest_legacy_version() -> Optional[Tuple[int, ...]]:
    """The oldest old addon version a scene was saved with, () when a scene's
    version is unknown, or None when no scene was saved by the old addon."""
    oldest: Optional[Tuple[int, ...]] = None
    for scene in bpy.data.scenes:
        version = legacy_version(scene)
        if version is None:
            continue
        try:
            parsed = tuple(ast.literal_eval(version))
        except (ValueError, SyntaxError):
            parsed = ()
        if oldest is None or parsed < oldest:
            oldest = parsed
    return oldest


MIGRATED_FROM_PROP = "rbr_migrated_from"


def is_legacy_file() -> bool:
    """Whether this file holds data written by the old addon: a scene stamped
    with an old version, or, in a file never migrated, local node trees or
    objects in the old layout (a library file may have the data without the
    scene stamp). The old properties are kept after migration, so the marker
    the migration leaves on the scenes decides for those."""
    if any(legacy_version(scene) is not None for scene in bpy.data.scenes):
        return True
    if any(scene.get(MIGRATED_FROM_PROP) for scene in bpy.data.scenes):
        return False
    for node_tree in bpy.data.node_groups:
        if node_tree.library is None and is_old_shader_tree(node_tree):
            return True
    for obj in bpy.data.objects:
        if obj.library is None and old_type(obj) != "NONE":
            return True
    return False


def old_type(obj: bpy.types.Object) -> str:
    settings = obj.get("rbr_object_settings")
    if settings is None:
        return "NONE"
    return tables.OLD_OBJECT_TYPES.get(settings.get("type", 1), "NONE")


def old_settings(obj: bpy.types.Object) -> Any:
    return obj.get("rbr_object_settings")


def _tree_stem(name: str) -> str:
    return re.sub(r"\.\d{3}$", "", name)


def is_old_shader_tree(node_tree: bpy.types.NodeTree) -> bool:
    return _tree_stem(node_tree.name) in tables.OLD_SHADER_TREE_STEMS


def is_old_rbr_node(node: bpy.types.Node) -> bool:
    if node.bl_idname != "ShaderNodeRBR":
        return False
    tree = getattr(node, "node_tree", None)
    if tree is None:
        return "has_diffuse_1" in node.keys() or "mesh_type" not in node.keys()
    return is_old_shader_tree(tree)


def legacy_libraries() -> List[str]:
    """Libraries holding old addon data, which have to be migrated first."""
    found: Set[str] = set()
    for material in bpy.data.materials:
        if material.library is None or material.node_tree is None:
            continue
        if any(is_old_rbr_node(node) for node in material.node_tree.nodes):
            found.add(material.library.filepath)
    for node_tree in bpy.data.node_groups:
        if node_tree.library is not None and is_old_shader_tree(node_tree):
            found.add(node_tree.library.filepath)
    for obj in bpy.data.objects:
        if obj.library is not None and old_type(obj) != "NONE":
            found.add(obj.library.filepath)
    return sorted(found)


# ---------------------------------------------------------------- scenes
def _scene_objects_of_type(
    scene: bpy.types.Scene, type_name: str
) -> List[bpy.types.Object]:
    return [obj for obj in scene.objects if old_type(obj) == type_name]


def migrate_view_transform(scene: bpy.types.Scene, log: Log) -> None:
    """The preview shaders reproduce the game's output, so they only look
    right through the Standard view transform; old files usually carry
    Blender's Filmic default."""
    view: Any = scene.view_settings
    if view is None:
        return
    if (
        view.view_transform == "Standard"
        and view.look == "None"
        and view.exposure == 0.0
        and view.gamma == 1.0
    ):
        return
    was = view.view_transform
    view.view_transform = "Standard"
    view.look = "None"
    view.exposure = 0.0
    view.gamma = 1.0
    log.info(
        f"scene '{scene.name}': view transform changed from {was} to Standard, which the preview is made for"
    )


def migrate_scene(scene: bpy.types.Scene, log: Log) -> None:
    migrate_view_transform(scene, log)
    old = scene.get("rbr_track_settings")
    # The old addon kept one export settings block, on the first scene.
    export = scene.get("rbr_export_settings")
    for other in bpy.data.scenes:
        if other.get("rbr_export_settings") and other.get("rbr_export_settings").get(
            "track_id"
        ):
            export = other.get("rbr_export_settings")
            break
    new = scene.rbr_scene_settings

    tint = tables.OLD_TINT_BITS.get(old.get("tint_set", 1) if old else 1, "MORNING")
    new.tint_set_morning = tint == "MORNING"
    new.tint_set_noon = tint == "NOON"
    new.tint_set_evening = tint == "EVENING"
    new.tint_set_overcast = tint == "OVERCAST"
    with bpy.context.temp_override(scene=scene):
        new.active_tint_set = tint

    surface_mask = old.get("surface_types", 1) if old else 1
    new.surface_type_dry = bool(surface_mask & 1)
    new.surface_type_damp = bool(surface_mask & 2)
    new.surface_type_wet = bool(surface_mask & 4)
    if old:
        new.active_surface_type = tables.SURFACE_TYPE_NAMES[
            min(max(old.get("active_surface_type", 0), 0), 2)
        ]
        new.active_surface_age = tables.SURFACE_AGE_NAMES[
            min(max(old.get("active_surface_age", 0), 0), 2)
        ]

    if old:
        weathers = new.get_tint_set_world_weather(TintSet[tint])
        weathers.clear()
        for ptr in old.get("world_weathers", []):
            world = ptr.get("world")
            if not isinstance(world, bpy.types.World):
                continue
            entry = weathers.add()
            entry.world = world
            entry.overcast_time_of_day = tables.TIME_OF_DAY_NAMES[
                min(max(ptr.get("overcast_time_of_day", 0), 0), 2)
            ]
        new.active_world_weather = min(
            old.get("active_world_weather", 0), max(len(weathers) - 1, 0)
        )
        log.info(
            f"scene '{scene.name}': {tint.lower()} tint set with {len(weathers)} weathers"
        )

    if export:
        new.export_to = export.get("export_to", "")
        new.track_id = max(1, export.get("track_id", 1))
        new.track_name = export.get("track_name", "")
        new.author = export.get("author", "")
        particles = export.get("particles", "ps_british")
        if particles and "\\" not in particles and "/" not in particles:
            particles = "Maps\\" + particles
        if particles:
            new.particles = particles
        new.surface = tables.STAGE_SURFACE_NAMES[
            min(max(export.get("surface", 0), 0), 2)
        ]
        new.country_code = tables.COUNTRY_ALPHA2.get(export.get("country", 826), "GB")

    # scene pointers
    drivelines = _scene_objects_of_type(scene, "DRIVELINE")
    if len(drivelines) > 1:
        log.manual(
            f"scene '{scene.name}' has {len(drivelines)} driveline objects, "
            f"using '{drivelines[0].name}'; set the other one by hand if needed"
        )
    with bpy.context.temp_override(scene=scene):
        if drivelines:
            new.driveline = drivelines[0]
            _migrate_driveline(drivelines[0], log)
        cars = _scene_objects_of_type(scene, "CAR_LOCATION")
        if cars:
            new.car_location = cars[0]
        zones = _scene_objects_of_type(scene, "REGISTRATION_ZONE")
        if zones:
            new.registration_zone = zones[0]
        for camera in _scene_objects_of_type(scene, "CAMERA"):
            _migrate_camera(camera, new.driveline is not None, log)
    for brake_wall in _scene_objects_of_type(scene, "BRAKE_WALL"):
        log.manual(
            f"brake wall '{brake_wall.name}' is still a mesh; run the optional brake wall migration"
        )
    for sound in _scene_objects_of_type(scene, "SOUND_EMITTER"):
        log.manual(
            f"sound trigger '{sound.name}' has no equivalent in the new addon and is ignored"
        )


def _migrate_driveline(obj: bpy.types.Object, log: Log) -> None:
    curve = obj.data
    if not isinstance(curve, bpy.types.Curve):
        return
    old = obj.get("rbr_driveline_settings")
    settings = curve.rbr_curve_settings
    if old is None:
        return
    settings.alpha_far = old.get("alpha_far", 3000.0)
    settings.pacenotes.clear()
    checkpoints: List[float] = []
    for note in old.get("pacenotes", []):
        pid = note.get("pacenote_id", tables.PACENOTE_EVENT_START)
        location = note.get("location", 0.0)
        if pid == tables.PACENOTE_EVENT_START:
            settings.event_start = location
        elif pid == tables.PACENOTE_EVENT_FINISH:
            settings.event_finish = location
        elif pid == tables.PACENOTE_EVENT_ENDSTAGE:
            settings.event_end_of_stage = location
        elif pid == tables.PACENOTE_EVENT_CHECKPOINT:
            checkpoints.append(location)
        else:
            entry = settings.pacenotes.add()
            entry.pacenote_id = pid
            entry.location = location
    checkpoints.sort()
    if len(checkpoints) > 0:
        settings.event_split_1 = checkpoints[0]
    if len(checkpoints) > 1:
        settings.event_split_2 = checkpoints[1]
    if len(checkpoints) > 2:
        log.manual(
            f"driveline '{obj.name}' had {len(checkpoints)} checkpoints, only two splits are supported"
        )
    settings.update_sorted_pacenotes()
    for child in obj.children:
        if old_type(child) == "ZFAR":
            scale = sum(child.scale) / 3.0
            if scale > 1.0:
                settings.render_distance_scale = scale
            break
    log.info(
        f"driveline '{obj.name}': {len(settings.pacenotes)} pacenotes and {len(checkpoints)} splits"
    )


def _migrate_camera(obj: bpy.types.Object, has_driveline: bool, log: Log) -> None:
    camera = obj.data
    if not isinstance(camera, bpy.types.Camera):
        return
    old = old_settings(obj)
    settings = camera.rbr_camera_settings
    mode = tables.OLD_CAMERA_MODE.get(old.get("camera_mode", 0), "DEFAULT")
    settings.helicam = mode == "HELICAM"
    settings.shake = old.get("camera_shake", 0.0)
    for constraint in list(obj.constraints):
        if constraint.type == "TRACK_TO":
            obj.constraints.remove(constraint)
    if old.get("camera_look_at_car", 0):
        if has_driveline:
            settings.look_at_car = True
        else:
            log.manual(
                f"camera '{obj.name}' looked at the car but the scene has no driveline to track"
            )
    for constraint in obj.constraints:
        if constraint.type == "FOLLOW_PATH":
            log.manual(
                f"camera '{obj.name}' follows a path; run the optional camera path migration"
            )
            break
    _migrate_camera_fov(obj, camera, log)


def find_fcurve(id_block: bpy.types.ID, data_path: str) -> Tuple[Any, Any]:
    """An fcurve of the datablock's action by data path, with the channel
    bag holding it, on Blender 5's layered actions."""
    anim: Any = getattr(id_block, "animation_data", None)
    action: Any = anim.action if anim else None
    if action is None:
        return None, None
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                fcurve = channelbag.fcurves.find(data_path)
                if fcurve is not None:
                    return fcurve, channelbag
    return None, None


def _migrate_camera_fov(
    obj: bpy.types.Object, camera: bpy.types.Camera, log: Log
) -> None:
    """The old exporter wrote the camera angle as the game's field of view;
    the new one treats the angle as vertical and widens it by 4/3, so shrink
    the angle (and any lens keyframes) to keep the exported value."""
    old_angle = camera.angle
    sensor_width = camera.sensor_width
    camera.sensor_fit = "VERTICAL"
    camera.angle = old_angle * 0.75
    sensor_height = camera.sensor_height

    def new_lens(old_lens: float) -> float:
        if old_lens <= 0.0:
            return old_lens
        old_fov = 2.0 * math.atan(sensor_width / (2.0 * old_lens))
        return sensor_height / (2.0 * math.tan(0.375 * old_fov))

    fcurve, _ = find_fcurve(camera, "lens")
    converted = 0
    if fcurve is not None:
        for point in fcurve.keyframe_points:
            point.co.y = new_lens(point.co.y)
            point.handle_left.y = new_lens(point.handle_left.y)
            point.handle_right.y = new_lens(point.handle_right.y)
            converted += 1
        fcurve.update()
    log.info(
        f"camera '{obj.name}': field of view kept at {math.degrees(old_angle):.1f} degrees"
        + (f" with {converted} lens keyframe(s) converted" if converted else "")
    )


# ---------------------------------------------------------------- worlds
def migrate_worlds(log: Log) -> None:
    """Copy the world settings and drop the old sky nodes; the world setup
    makes new ones from a freshly rebuilt sky tree."""
    sky.recreate_internals()
    for world in bpy.data.worlds:
        old = world.get("rbr_track_settings")
        if old is None or world.library is not None:
            continue
        new = world.rbr_world_settings
        new.auto_balance = False
        if world.node_tree is not None:
            for node in list(world.node_tree.nodes):
                if isinstance(node, sky.ShaderNodeRBRSky) or node.bl_idname in (
                    "ShaderNodeRBRSky",
                    "NodeUndefined",
                ):
                    world.node_tree.nodes.remove(node)
        if "weather" in old.keys():
            new.weather = tables.WEATHER_NAMES[min(max(old["weather"], 0), 9)]
        if "sky" in old.keys():
            new.sky = tables.SKY_NAMES[min(max(old["sky"], 0), 3)]
        if "cloud_name" in old.keys():
            names = [cloud.name for cloud in CloudName]
            new.cloud_name = names[min(max(old["cloud_name"], 0), len(names) - 1)]
        for field in tables.WORLD_FIELDS:
            if field not in old.keys():
                continue
            value = old[field]
            try:
                if hasattr(value, "__len__") and not isinstance(value, str):
                    setattr(new, field, list(value))
                else:
                    setattr(new, field, value)
            except (TypeError, ValueError) as e:
                log.manual(f"world '{world.name}': could not copy {field} ({e})")
        log.info(f"world '{world.name}': settings copied")


def migrate_suns(log: Log) -> None:
    suns = [obj for obj in bpy.data.objects if old_type(obj) == "SUN"]
    if not suns:
        return
    for scene in bpy.data.scenes:
        old = scene.get("rbr_track_settings")
        if old is None:
            continue
        mask = old.get("tint_set", 1)
        chosen = None
        for sun in suns:
            sun_mask = old_settings(sun).get("tint_sets", 15)
            if sun_mask & mask:
                chosen = sun
                break
        if chosen is None:
            chosen = suns[0]
        for ptr in old.get("world_weathers", []):
            world = ptr.get("world")
            if isinstance(world, bpy.types.World) and world.library is None:
                world.rbr_world_settings.sun = chosen
                world.rbr_world_settings.update_sun_direction()
    log.info(f"{len(suns)} sun object(s) assigned to the weathers' worlds")


# ---------------------------------------------------------------- textures
def migrate_textures(context: bpy.types.Context, log: Log) -> None:
    """Old texture trees keep their settings node; the rest is rebuilt now
    because the scene settings link into it as soon as they change."""
    count = 0
    links = pop_links()
    for node_tree in bpy.data.node_groups:
        if node_tree.library is not None or not node_tree.name.startswith(
            ".RBRTextureV0."
        ):
            continue
        internal = node_tree.nodes.get("internal")
        if internal is None:
            continue
        if not internal.get("override_mip_levels", 0):
            internal["mip_levels"] = 0
        texture.recreate_internals(context, node_tree)
        count += 1
    push_links(links)
    log.info(
        f"{count} RBR textures carried over (format defaults to DXT1; run the optional texture format step to read the .dds headers)"
    )


def transparent_texture_trees() -> Set[str]:
    """Texture trees used by a material the old exporter treated as
    transparent (any blend mode but opaque), which it wrote with an opacity
    map."""
    names: Set[str] = set()
    for material in bpy.data.materials:
        if material.library is not None or material.node_tree is None:
            continue
        if material.blend_method == "OPAQUE":
            continue
        for node in material.node_tree.nodes:
            tree = getattr(node, "node_tree", None)
            if node.bl_idname == "ShaderNodeRBRTexture" and tree is not None:
                names.add(tree.name)
    return names


def migrate_texture_transparency(log: Log) -> None:
    """DXT1 here means opaque; a DXT1 texture on a transparent material
    needs the 1-bit alpha variant to keep the alpha test the old addon gave
    it."""
    count = 0
    for name in sorted(transparent_texture_trees()):
        node_tree = bpy.data.node_groups.get(name)
        internal = node_tree.nodes.get("internal") if node_tree else None
        if internal is None or node_tree is None or node_tree.library is not None:
            continue
        if internal.texture_format == "DXT1":
            internal.texture_format = "DXT1_1BIT"
            count += 1
    if count:
        log.info(
            f"{count} texture(s) on transparent materials export as DXT1 with 1-bit alpha so their alpha test is kept"
        )


def migrate_uv_velocity(log: Log) -> None:
    """The old UV velocity tree used a Time node the new addon doesn't have;
    point every velocity node at a freshly built tree."""
    old_trees = [
        nt
        for nt in bpy.data.node_groups
        if nt.library is None and _tree_stem(nt.name) == tables.UV_VELOCITY_TREE_STEM
    ]
    if not old_trees:
        return
    for nt in old_trees:
        nt.name = nt.name + ".legacy"
    new_tree = setup_uv_velocity_node_tree()
    count = 0
    for material in bpy.data.materials:
        if material.library is not None or material.node_tree is None:
            continue
        for node in material.node_tree.nodes:
            if node.bl_idname != "ShaderNodeUVVelocity":
                continue
            velocity_socket = node.inputs.get("UV Velocity")
            velocity = (
                list(velocity_socket.default_value)
                if velocity_socket
                else [0.0, 0.0, 0.0]
            )
            node.node_tree = new_tree
            velocity_socket = node.inputs.get("UV Velocity")
            if velocity_socket is not None:
                velocity_socket.default_value = velocity
            count += 1
    for nt in old_trees:
        if nt.users == 0:
            bpy.data.node_groups.remove(nt)
    log.info(f"{count} UV velocity node(s) rebuilt")


# ---------------------------------------------------------------- materials
MaterialWant = Tuple[str, Dict[str, Any]]


def material_wants() -> (
    Dict[bpy.types.Material, List[Tuple[bpy.types.Object, MaterialWant]]]
):
    """For every material used by an old typed object, what the new material
    should be, per object."""
    wants: Dict[bpy.types.Material, List[Tuple[bpy.types.Object, MaterialWant]]] = {}
    for obj in bpy.data.objects:
        kind = old_type(obj)
        mesh_type = tables.MATERIAL_MESH_TYPES.get(kind)
        if mesh_type is None or not isinstance(obj.data, bpy.types.Mesh):
            continue
        settings = old_settings(obj)
        options: Dict[str, Any] = {}
        if kind == "GEOM_BLOCKS":
            distance = tables.OLD_GEOM_DISTANCE.get(
                settings.get("geom_blocks_distance", 1), "NEAR"
            )
            collision = (
                bool(settings.get("is_geom_blocks_collision", 0)) and distance != "FAR"
            )
            options = {
                "geom_block_type": distance,
                "is_geom_block_collision": collision,
                "is_geom_block_invisible": collision
                and bool(settings.get("is_geom_blocks_invisible", 0)),
            }
        elif kind == "OBJECT_BLOCKS":
            options = {
                "object_block_type": tables.OLD_OBJECT_BLOCK_DETAIL.get(
                    settings.get("object_blocks_detail", 3), "BOTH"
                )
            }
        for material in obj.data.materials:
            if material is None:
                continue
            wants.setdefault(material, []).append((obj, (mesh_type, options)))
    return wants


def material_conflicts(
    wants: Dict[bpy.types.Material, List[Tuple[bpy.types.Object, MaterialWant]]],
) -> Dict[bpy.types.Material, Dict[Tuple[Any, ...], List[bpy.types.Object]]]:
    """Materials whose objects disagree, grouped by the wanted settings."""
    conflicts = {}
    for material, users in wants.items():
        groups: Dict[Tuple[Any, ...], List[bpy.types.Object]] = {}
        for obj, (mesh_type, options) in users:
            key = (mesh_type,) + tuple(sorted(options.items()))
            groups.setdefault(key, []).append(obj)
        if len(groups) > 1:
            conflicts[material] = groups
    return conflicts


def canonical_socket_names(mesh_type: str) -> Dict[str, str]:
    """New socket name -> old (mesh type independent) socket name."""
    return {new: old for old, new in tables.SOCKET_MAPS[mesh_type].items()}


def apply_material_settings(
    material: bpy.types.Material,
    mesh_type: str,
    options: Dict[str, Any],
    log: Optional[Log] = None,
) -> None:
    """Set a rebuilt material's mesh type and options. Changing the mesh type
    renames sockets, so the links are carried across by their old names."""
    if material.node_tree is None:
        return
    node_tree = material.node_tree
    for node in node_tree.nodes:
        if not isinstance(node, ShaderNodeRBR) or is_old_rbr_node(node):
            continue
        if node.mesh_type != mesh_type:
            canonical = canonical_socket_names(node.mesh_type)
            saved = []
            for socket in node.inputs:
                for link in socket.links:
                    saved.append(
                        (canonical.get(socket.name, socket.name), link.from_socket)
                    )
            outputs = [
                (socket.name, link.to_socket)
                for socket in node.outputs
                for link in socket.links
            ]
            node.mesh_type = mesh_type
            for link in list(node_tree.links):
                if link.to_node == node or link.from_node == node:
                    node_tree.links.remove(link)
            target = tables.SOCKET_MAPS[mesh_type]
            for old_name, from_socket in saved:
                new_socket = node.inputs.get(target.get(old_name, old_name))
                if new_socket is None:
                    if log is not None:
                        log.manual(
                            f"material '{material.name}': {mesh_type.replace('_', ' ').lower()} "
                            f"materials have no '{old_name}' input, its link was dropped"
                        )
                    continue
                node_tree.links.new(from_socket, new_socket)
            for name, to_socket in outputs:
                new_socket = node.outputs.get(name)
                if new_socket is not None:
                    node_tree.links.new(new_socket, to_socket)
        for name, value in options.items():
            setattr(node, name, value)
            if mesh_type == "CLIPPING_PLANE":
                cull = node.inputs.get("Backface Cull (don't connect)")
                if cull is not None:
                    cull.default_value = material.use_backface_culling


ALLOWED_VALUE_SOURCES = {
    "ShaderNodeAttribute",
    "ShaderNodeRGB",
    "ShaderNodeValue",
    "ShaderNodeRBRTintSet",
}


def _upstream(link: bpy.types.NodeLink) -> bpy.types.Node:
    node = link.from_node
    while isinstance(node, bpy.types.NodeReroute) and node.inputs[0].links:
        node = node.inputs[0].links[0].from_node
    return node


def rebuild_material(
    material: bpy.types.Material, mesh_type: str, options: Dict[str, Any], log: Log
) -> None:
    """Replace the old RBR shader node with a new one of the given mesh type,
    carrying the links across. Vertex Color nodes become Attribute nodes."""
    node_tree = material.node_tree
    if node_tree is None:
        material.use_nodes = True
        node_tree = material.node_tree
        if node_tree is None:
            return
    old_nodes = [node for node in node_tree.nodes if is_old_rbr_node(node)]
    socket_map = tables.SOCKET_MAPS[mesh_type]

    # Vertex colour nodes become attribute nodes once, shared by every link.
    converted: Dict[str, bpy.types.Node] = {}

    def attribute_for(vc_node: bpy.types.Node) -> bpy.types.Node:
        if vc_node.name in converted:
            return converted[vc_node.name]
        attr = narrow(
            node_tree.nodes.new("ShaderNodeAttribute"), bpy.types.ShaderNodeAttribute
        )
        attr.attribute_type = "GEOMETRY"
        attr.attribute_name = narrow(
            vc_node, bpy.types.ShaderNodeVertexColor
        ).layer_name
        attr.location = vc_node.location
        attr.label = vc_node.label
        converted[vc_node.name] = attr
        return attr

    if not old_nodes:
        if mesh_type != "CLIPPING_PLANE":
            log.manual(
                f"material '{material.name}' has no RBR shader node; it will not export"
            )
            return
        output = node_tree.get_output_node("EEVEE") or node_tree.nodes.new(
            "ShaderNodeOutputMaterial"
        )
        new = narrow(node_tree.nodes.new("ShaderNodeRBR"), ShaderNodeRBR)
        new.mesh_type = mesh_type
        node_tree.links.new(new.outputs["Surface"], output.inputs["Surface"])
        apply_material_settings(material, mesh_type, options)
        log.info(f"material '{material.name}': clipping plane shader added")
        return

    for old in old_nodes:
        new = narrow(node_tree.nodes.new("ShaderNodeRBR"), ShaderNodeRBR)
        new.mesh_type = mesh_type
        new.location = old.location
        new.width = old.width
        for name, value in options.items():
            setattr(new, name, value)
        if mesh_type == "CLIPPING_PLANE":
            cull = new.inputs.get("Backface Cull (don't connect)")
            if cull is not None:
                cull.default_value = material.use_backface_culling

        # inputs
        for old_socket in old.inputs:
            new_name = socket_map.get(old_socket.name)
            new_socket = new.inputs.get(new_name) if new_name else None
            if new_socket is None:
                if old_socket.links:
                    log.manual(
                        f"material '{material.name}': {mesh_type.replace('_', ' ').lower()} "
                        f"materials have no '{old_socket.name}' input, its link was dropped"
                    )
                continue
            if not old_socket.links:
                if new_name not in tables.TEXTURE_SOCKETS and hasattr(
                    old_socket, "default_value"
                ):
                    try:
                        new_socket.default_value = old_socket.default_value
                    except (TypeError, ValueError):
                        pass
                continue
            link = old_socket.links[0]
            from_node = link.from_node
            from_socket = link.from_socket
            if from_node.bl_idname == "ShaderNodeVertexColor":
                from_node = attribute_for(from_node)
                from_socket = from_node.outputs[
                    "Alpha" if link.from_socket.name == "Alpha" else "Color"
                ]
            node_tree.links.new(from_socket, new_socket)
            source = _upstream(link)
            if source.bl_idname == "ShaderNodeVertexColor":
                continue
            if new_name in tables.TEXTURE_SOCKETS:
                ok = source.bl_idname == "ShaderNodeRBRTexture"
            else:
                ok = source.bl_idname in ALLOWED_VALUE_SOURCES
            if not ok:
                log.manual(
                    f"material '{material.name}': input '{new_name}' is fed by a {source.bl_idname} "
                    f"node; the exporter only reads Attribute, RGB and Value nodes there, bake it to an attribute"
                )

        # outputs
        for old_socket in old.outputs:
            for link in list(old_socket.links):
                target = {
                    "Surface": "Surface",
                    "Shader": "Surface",
                    "Displacement": "Displacement",
                }.get(old_socket.name)
                new_socket = new.outputs.get(target) if target else None
                if new_socket is None:
                    continue
                node_tree.links.new(new_socket, link.to_socket)
        node_tree.nodes.remove(old)

    # Vertex colour nodes feeding anything else keep working, so only drop the
    # ones that are now unused.
    for name in converted:
        vc = node_tree.nodes.get(name)
        if vc is not None and not any(socket.links for socket in vc.outputs):
            node_tree.nodes.remove(vc)
    log.info(
        f"material '{material.name}': {mesh_type.replace('_', ' ').lower()} shader rebuilt"
    )


OLD_SHADOW_LAYER = "RBR_SHADOW"


def wire_collision_shading(
    material: bpy.types.Material, users: List[bpy.types.Object], log: Log
) -> None:
    """The old collision shading came from a fixed vertex colour layer; the
    new one is a shader input, so feed it that layer when every user has it
    and fall back to the old default of fully lit otherwise."""
    node_tree = material.node_tree
    if node_tree is None:
        return
    meshes = {obj.data for obj in users if isinstance(obj.data, bpy.types.Mesh)}
    with_layer = [mesh for mesh in meshes if OLD_SHADOW_LAYER in mesh.attributes]
    for node in node_tree.nodes:
        if not isinstance(node, ShaderNodeRBR) or not node.is_geom_block_collision:
            continue
        shading = node.inputs.get("Collision Shading")
        if shading is None:
            continue
        if meshes and len(with_layer) == len(meshes):
            attr = narrow(
                node_tree.nodes.new("ShaderNodeAttribute"),
                bpy.types.ShaderNodeAttribute,
            )
            attr.attribute_type = "GEOMETRY"
            attr.attribute_name = OLD_SHADOW_LAYER
            attr.location = (node.location.x - 300, node.location.y - 400)
            node_tree.links.new(attr.outputs["Color"], shading)
        else:
            shading.default_value = 1.0
            if with_layer:
                log.manual(
                    f"material '{material.name}': only some of its meshes have an "
                    f"'{OLD_SHADOW_LAYER}' layer, collision shading set to 1.0 for all"
                )


def _dropped_links(material: bpy.types.Material, mesh_type: str) -> int:
    """How many linked old shader inputs the given mesh type has no socket for."""
    if material.node_tree is None:
        return 0
    socket_map = tables.SOCKET_MAPS[mesh_type]
    dropped = 0
    for node in material.node_tree.nodes:
        if not is_old_rbr_node(node):
            continue
        for socket in node.inputs:
            if socket.links and socket.name not in socket_map:
                dropped += 1
    return dropped


def primary_want(
    material: bpy.types.Material,
    users: List[Tuple[bpy.types.Object, MaterialWant]],
) -> MaterialWant:
    """The settings the shared material itself gets: the group that loses the
    fewest links, then the one with the most objects."""
    groups: Dict[Tuple[Any, ...], Tuple[MaterialWant, int]] = {}
    for _, want in users:
        key = (want[0],) + tuple(sorted(want[1].items()))
        want_, count = groups.get(key, (want, 0))
        groups[key] = (want_, count + 1)
    ranked = sorted(
        groups.values(),
        key=lambda item: (_dropped_links(material, item[0][0]), -item[1]),
    )
    return ranked[0][0]


def migrate_materials(log: Log) -> None:
    wants = material_wants()
    conflicts = material_conflicts(wants)
    for material, users in wants.items():
        if material.library is not None:
            continue
        mesh_type, options = primary_want(material, users)
        rebuild_material(material, mesh_type, options, log)
        if options.get("is_geom_block_collision"):
            same = [obj for obj, want in users if want == (mesh_type, options)]
            wire_collision_shading(material, same, log)
    for material, groups in conflicts.items():
        log.manual(
            f"material '{material.name}' is shared by {len(groups)} groups of objects with "
            f"different settings; run the optional duplicate step to split it"
        )
    # Old RBR shader nodes in materials no typed object uses
    for material in bpy.data.materials:
        if (
            material.library is not None
            or material.node_tree is None
            or material in wants
        ):
            continue
        if any(is_old_rbr_node(node) for node in material.node_tree.nodes):
            rebuild_material(material, "GEOM_BLOCK", {"geom_block_type": "NEAR"}, log)
            log.manual(
                f"material '{material.name}' is not used by any typed object; rebuilt as a geom block"
            )


# ---------------------------------------------------------------- old addon steps
def migrate_interactive_collision_meshes(log: Log) -> None:
    """The old addon's 0.2.2 step: shape collision meshes parented to an
    interactive object became its collision mesh."""
    colmesh_type = next(
        k
        for k, v in tables.OLD_OBJECT_TYPES.items()
        if v == "INTERACTIVE_OBJECTS_COLMESH"
    )
    count = 0
    for obj in bpy.data.objects:
        if obj.library is not None or old_type(obj) != "INTERACTIVE_OBJECTS":
            continue
        kind = old_settings(obj).get("interactive_object_kind", 1)
        for child in obj.children:
            if old_type(child) == "SHAPE_COLLISION_MESH":
                settings = old_settings(child)
                settings["type"] = colmesh_type
                settings["interactive_object_kind"] = kind
                count += 1
    if count:
        log.info(f"{count} interactive object collision mesh(es) from before 0.2.2")


def trim_excess_material_maps(log: Log) -> None:
    """The old addon's 0.3.2 step: a bug grew material map regions past 9
    surface maps of 16x16 cells."""
    count = 0
    for node_tree in bpy.data.node_groups:
        if node_tree.library is not None or not node_tree.name.startswith(
            ".RBRTextureV0."
        ):
            continue
        internal = node_tree.nodes.get("internal")
        if not isinstance(internal, texture.ShaderNodeRBRTextureInternal):
            continue
        for region in internal.material_maps:
            trimmed = len(region.maps) > 9
            while len(region.maps) > 9:
                region.maps.remove(9)
            for material_map in region.maps:
                trimmed |= len(material_map.rows) > 16
                while len(material_map.rows) > 16:
                    material_map.rows.remove(16)
                for row in material_map.rows:
                    trimmed |= len(row.cols) > 16
                    while len(row.cols) > 16:
                        row.cols.remove(16)
            count += trimmed
    if count:
        log.info(f"{count} material map region(s) trimmed of excess maps")


# ---------------------------------------------------------------- objects
def _set_tint_flags(obj: bpy.types.Object) -> None:
    settings = old_settings(obj)
    mask = settings.get("tint_sets", 15) if settings is not None else 15
    new = obj.rbr_object_settings
    new.tint_set_morning = bool(mask & 1)
    new.tint_set_noon = bool(mask & 2)
    new.tint_set_evening = bool(mask & 4)
    new.tint_set_overcast = bool(mask & 8)


def _set_collision_physics(target: Any, material_id: int, log: Log, what: str) -> None:
    entry = tables.OLD_SCM_MATERIAL.get(material_id)
    if entry is None:
        log.manual(
            f"{what}: unknown collision material id {material_id}, left undefined"
        )
        return
    physics, density, size = entry
    target.physics = physics
    if density is not None:
        target.bush_density = density
    if size is not None:
        target.size = size


def mesh_wants() -> Dict[bpy.types.Mesh, Dict[int, List[bpy.types.Object]]]:
    """Shape collision meshes and the material ids their objects want."""
    wants: Dict[bpy.types.Mesh, Dict[int, List[bpy.types.Object]]] = {}
    for obj in bpy.data.objects:
        if old_type(obj) != "SHAPE_COLLISION_MESH" or not isinstance(
            obj.data, bpy.types.Mesh
        ):
            continue
        material_id = old_settings(obj).get("shape_collision_mesh_material", 0)
        wants.setdefault(obj.data, {}).setdefault(material_id, []).append(obj)
    return wants


def migrate_objects(log: Log) -> None:
    counts: Dict[str, int] = {}
    scm_meshes = mesh_wants()
    for mesh, groups in scm_meshes.items():
        if mesh.library is not None:
            continue
        settings = mesh.rbr_mesh_settings
        settings.mesh_type = "STATIC_SHAPE_COLLISION"
        first_id = next(iter(groups))
        _set_collision_physics(
            settings.collision_physics, first_id, log, f"collision mesh '{mesh.name}'"
        )
        if len(groups) > 1:
            log.manual(
                f"collision mesh '{mesh.name}' is shared by objects with different materials; "
                f"kept '{groups[first_id][0].name}', run the optional duplicate step to split it"
            )

    for obj in bpy.data.objects:
        if obj.library is not None:
            continue
        kind = old_type(obj)
        if kind == "NONE":
            continue
        counts[kind] = counts.get(kind, 0) + 1
        _set_tint_flags(obj)
        settings = old_settings(obj)
        if settings.get("exported", 1) == 0:
            log.manual(
                f"'{obj.name}' had export unticked; run the optional step to move it out of the export"
            )
        if kind == "INSTANCER":
            obj.rbr_object_settings.make_instances_real = True
        elif kind == "SHAPE_COLLISION_MESH":
            if isinstance(obj.data, bpy.types.Mesh):
                material_id = settings.get("shape_collision_mesh_material", 0)
                for child in obj.children:
                    if child.data is None and child.empty_display_type in (
                        "SPHERE",
                        "CUBE",
                    ):
                        child_settings = child.rbr_object_settings
                        child_settings.soft_collision = True
                        _set_collision_physics(
                            child_settings.collision_physics,
                            material_id,
                            log,
                            f"soft volume '{child.name}'",
                        )
                        size = child.empty_display_size
                        child.scale = [s * size for s in child.scale]
                        child.empty_display_size = 1.0
        elif kind == "INTERACTIVE_OBJECTS":
            if isinstance(obj.data, bpy.types.Mesh):
                mesh_settings = obj.data.rbr_mesh_settings
                mesh_settings.mesh_type = "INTERACTIVE_OBJECT"
                colmesh = None
                for child in obj.children:
                    if old_type(child) == "INTERACTIVE_OBJECTS_COLMESH":
                        colmesh = child
                        break
                if colmesh is None:
                    log.manual(
                        f"interactive object '{obj.name}' has no child collision mesh"
                    )
                else:
                    mesh_settings.interactive_object_colmesh = colmesh
                    kind_id = old_settings(colmesh).get("interactive_object_kind", 1)
                    mesh_settings.interactive_object_physics = (
                        tables.OLD_INTERACTIVE_KIND.get(kind_id, "TRAFFIC_CONE")
                    )
        elif kind == "WET_SURFACE":
            if isinstance(obj.data, bpy.types.Mesh):
                obj.data.rbr_mesh_settings.mesh_type = "WATER_SPLASH"
                obj.data.rbr_mesh_settings.water_splash_weather = (
                    tables.OLD_WET_KIND.get(
                        settings.get("wet_surface_kind", 1), "ALL_WEATHERS"
                    )
                )
        elif kind == "FENCE":
            _migrate_fence(obj, settings, log)
        elif kind == "OBJECT_BLOCKS":
            if (
                settings.get("object_blocks_lod_mode", 0)
                == tables.OLD_OBJECT_BLOCK_LOD_FACE_MAP
            ):
                log.manual(
                    f"object block '{obj.name}' used a face map for its level of detail; that is gone, it uses the object setting now"
                )
    for kind, count in sorted(counts.items()):
        log.info(f"{count} {kind.replace('_', ' ').lower()} object(s)")
    dummy = bpy.data.objects.get("Dummy Car")
    if dummy is not None and dummy.data is None and old_type(dummy) == "NONE":
        bpy.data.objects.remove(dummy)
        log.info("removed the old 'Dummy Car' empty")


def _migrate_fence(obj: bpy.types.Object, settings: Any, log: Log) -> None:
    mesh = obj.data
    if not isinstance(mesh, bpy.types.Mesh):
        return
    kind = tables.OLD_FENCE_KIND.get(settings.get("fence_kind", 4), "TAPE")
    fence = mesh.rbr_mesh_settings.fence
    fence.fence_kind = kind
    if kind == "TAPE":
        fence.fence_tile_builtin = tables.OLD_TILE_TAPE.get(
            settings.get("fence_tile_tape_texture", 2), "br_fence_tile"
        )
        pole = tables.OLD_POLE_TAPE.get(
            settings.get("fence_pole_tape_texture", 2), "br_fencestolpe"
        )
        if pole == "signs_road":
            pole = "signs_road_" + tables.OLD_POLE_NET_COLOUR.get(
                settings.get("fence_pole_net_texture", 2), "grey"
            )
        fence.fence_pole_builtin = pole
    elif kind == "NET":
        fence.fence_tile_builtin = tables.OLD_TILE_NET.get(
            settings.get("fence_tile_net_texture", 0), "fence_tile01"
        )
        fence.fence_pole_builtin = "fence_pole_" + tables.OLD_POLE_NET_COLOUR.get(
            settings.get("fence_pole_net_texture", 2), "grey"
        )
    else:
        fence.fence_tile_builtin = "barbed_wire_tile"
        fence.fence_pole_builtin = "barbed_wire_stolpe"
    mesh.rbr_mesh_settings.mesh_type = "FENCE"
    shading = settings.get("fence_shading", "")
    for user in bpy.data.objects:
        if user.data != mesh:
            continue
        gnodes = user.modifiers.get(".rbr.fence")
        if not isinstance(gnodes, bpy.types.NodesModifier):
            continue
        gnodes_input(gnodes, GNODES_FENCE_SUBDIVIDE).value = bool(
            settings.get("fence_is_long", 0)
        )
        if shading and shading in mesh.attributes:
            vcol = gnodes_input(gnodes, GNODES_FENCE_VCOL)
            vcol.type = "ATTRIBUTE"
            vcol.attribute_name = shading


# ---------------------------------------------------------------- cleanup
def remove_old_trees(log: Log) -> None:
    removed = 0
    for node_tree in list(bpy.data.node_groups):
        if node_tree.library is not None:
            continue
        stem = _tree_stem(node_tree.name)
        if stem in tables.OLD_SHADER_TREE_STEMS or stem == tables.OLD_TIME_TREE_STEM:
            if node_tree.users == 0 or stem == tables.OLD_TIME_TREE_STEM:
                bpy.data.node_groups.remove(node_tree)
                removed += 1
            else:
                log.manual(
                    f"old shader tree '{node_tree.name}' is still used and was kept"
                )
    log.info(f"{removed} old node tree(s) removed")


# ---------------------------------------------------------------- entry
def _socket_defaults() -> Dict[Tuple[str, str, str], Any]:
    """Unlinked input values of every RBR shader node; the shader refresh
    rebuilds the node sockets and would reset them."""
    saved: Dict[Tuple[str, str, str], Any] = {}
    for material in bpy.data.materials:
        if material.library is not None or material.node_tree is None:
            continue
        for node in material.node_tree.nodes:
            if not isinstance(node, ShaderNodeRBR):
                continue
            for sock in node.inputs:
                if sock.links or not hasattr(sock, "default_value"):
                    continue
                value = sock.default_value
                if hasattr(value, "__len__"):
                    value = list(value)
                saved[(material.name, node.name, sock.name)] = value
    return saved


def _restore_socket_defaults(saved: Dict[Tuple[str, str, str], Any]) -> None:
    for (material_name, node_name, socket_name), value in saved.items():
        material = bpy.data.materials.get(material_name)
        node = (
            material.node_tree.nodes.get(node_name)
            if material and material.node_tree
            else None
        )
        sock = node.inputs.get(socket_name) if node else None
        if sock is None or sock.links or not hasattr(sock, "default_value"):
            continue
        try:
            sock.default_value = value
        except (TypeError, ValueError):
            pass


def migrate(context: bpy.types.Context, log: Log) -> None:
    blocked = legacy_libraries()
    if blocked:
        raise LibraryBlocked(blocked)
    from .. import CURRENT_VERSION

    scenes = [scene for scene in bpy.data.scenes if legacy_version(scene) is not None]
    oldest = oldest_legacy_version()
    if oldest is not None and oldest <= (0, 2, 2):
        migrate_interactive_collision_meshes(log)
    if oldest is not None and oldest <= (0, 3, 2):
        trim_excess_material_maps(log)
    migrate_worlds(log)
    migrate_textures(context, log)
    migrate_uv_velocity(log)
    migrate_materials(log)
    migrate_texture_transparency(log)
    migrate_objects(log)
    for scene in scenes:
        migrate_scene(scene, log)
    migrate_suns(log)
    remove_old_trees(log)
    defaults = _socket_defaults()
    refresh_all_rbr_shaders(context)
    _restore_socket_defaults(defaults)
    recreate_fence_node_group()
    for scene in bpy.data.scenes:
        old_version = (
            legacy_version(scene) or scene.get("rbr_addon_version") or "(0, ?)"
        )
        scene.rbr_addon_version = CURRENT_VERSION
        stale = scene.get("rbr_addon_version")
        if isinstance(stale, str) and stale.startswith("(0,"):
            del scene["rbr_addon_version"]
        scene[MIGRATED_FROM_PROP] = str(old_version)
        with context.temp_override(scene=scene):
            scene.rbr_scene_settings.update_world_context(context)
    log.info(f"migrated {len(scenes)} scene(s) to addon version {CURRENT_VERSION}")
