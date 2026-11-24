import os
from typing import Any, Callable, List, Set, Optional, Tuple

import bpy
from .blender_utils import NODE_PATH_SEPARATOR, narrow
from .types import OperatorReturn

from .properties.scene import RBRSceneSettings, RBRExportMessage
from .preferences import RBRAddonPreferences
from . import __package__ as base_package

try:
    from . import rbr_blender_track_io
except ImportError:
    # The binary might not be built yet (e.g. during a bindings regen on a
    # fresh checkout). The export operator reports an error when invoked.
    rbr_blender_track_io = None


def jump_to_object(
    context: bpy.types.Context,
    bad_obj: bpy.types.Object,
    instancer: Optional[bpy.types.Object],
    bad_material: Optional[bpy.types.Material],
    select_kind: str,
    select_indices: List[int],
    report: Callable[[Set[str], str], None],
) -> None:
    """Select and frame the object, falling back to its instancer if the object
    itself isn't in the view layer."""
    view_layer = context.view_layer
    if view_layer is None:
        report({"WARNING"}, "No active view layer to jump to")
        return
    target = bad_obj
    fallback_message: Optional[str] = None
    if bad_obj.name not in view_layer.objects:
        if instancer is not None and instancer.name in view_layer.objects:
            target = instancer
            fallback_message = (
                f"'{bad_obj.name}' is instanced and not in the view layer; "
                f"jumped to its instancer '{instancer.name}'"
            )
        else:
            report({"WARNING"}, f"'{bad_obj.name}' is not in the active view layer")
            return
    target.hide_set(False)
    for obj in view_layer.objects:
        obj.select_set(obj == target)
    view_layer.objects.active = target
    run_view3d_operator(lambda: bpy.ops.view3d.view_selected(use_all_regions=True))
    if (
        fallback_message is None
        and bad_material is not None
        and isinstance(target.data, bpy.types.Mesh)
    ):
        for i, material in enumerate(target.data.materials):
            if material == bad_material:
                target.active_material_index = i
                break
    if fallback_message is None and select_indices:
        if select_kind == "FACE":
            select_mesh_elements(context, target, select_indices, (False, False, True))
        elif select_kind == "VERTEX":
            select_mesh_elements(context, target, select_indices, (True, False, False))
        elif select_kind == "CURVE_POINT":
            select_curve_points(target, select_indices)
    if fallback_message is not None:
        report({"INFO"}, fallback_message)


def select_mesh_elements(
    context: bpy.types.Context,
    obj: bpy.types.Object,
    indices: List[int],
    select_mode: Tuple[bool, bool, bool],
) -> None:
    mesh = obj.data
    if not isinstance(mesh, bpy.types.Mesh):
        return
    elements = mesh.polygons if select_mode[2] else mesh.vertices

    def go() -> None:
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for vertex in mesh.vertices:
            vertex.select = False
        for edge in mesh.edges:
            edge.select = False
        for polygon in mesh.polygons:
            polygon.select = False
        for index in indices:
            if 0 <= index < len(elements):
                elements[index].select = True
        if context.tool_settings is not None:
            context.tool_settings.mesh_select_mode[:] = select_mode
        bpy.ops.object.mode_set(mode="EDIT")

    run_view3d_operator_once(go)


def select_curve_points(obj: bpy.types.Object, indices: List[int]) -> None:
    curve = obj.data
    if not isinstance(curve, bpy.types.Curve) or len(curve.splines) == 0:
        return
    spline = curve.splines[0]

    def go() -> None:
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for other in curve.splines:
            for bezier_point in other.bezier_points:
                bezier_point.select_control_point = False
                bezier_point.select_left_handle = False
                bezier_point.select_right_handle = False
            for point in other.points:
                point.select = False
        for index in indices:
            if len(spline.bezier_points) > 0:
                if 0 <= index < len(spline.bezier_points):
                    bezier_point = spline.bezier_points[index]
                    bezier_point.select_control_point = True
                    bezier_point.select_left_handle = True
                    bezier_point.select_right_handle = True
            elif 0 <= index < len(spline.points):
                spline.points[index].select = True
        bpy.ops.object.mode_set(mode="EDIT")

    run_view3d_operator_once(go)


def jump_to_material(
    bad_material: bpy.types.Material,
    node_name: str,
) -> None:
    # select the relevant node in the tree
    if node_name == "":
        return
    if not bad_material.use_nodes:
        return
    if bad_material.node_tree is None:
        return
    *group_names, name = node_name.split(NODE_PATH_SEPARATOR)
    tree = bad_material.node_tree
    groups: List[bpy.types.ShaderNodeGroup] = []
    for group_name in group_names:
        group = tree.nodes.get(group_name)
        if not isinstance(group, bpy.types.ShaderNodeGroup) or group.node_tree is None:
            return
        groups.append(group)
        tree = group.node_tree
    bad_node = tree.nodes.get(name)
    if bad_node is None:
        return
    for node in tree.nodes:
        node.select = node == bad_node
    frame_node_tree_selection(bad_material.node_tree, groups)


def frame_node_tree_selection(
    node_tree: bpy.types.NodeTree,
    groups: List[bpy.types.ShaderNodeGroup],
) -> None:
    """Frame the selected nodes in every shader editor showing node_tree,
    after entering groups (outermost first).

    Shader editors only pick up a change of active object/material when they
    next refresh, so framing straight after jump_to_object would run against
    the old (or no) tree and view_selected's poll fails. Retry from a timer
    until an editor shows the tree, giving up after a short while."""
    attempts = [0]

    def try_frame() -> Optional[float]:
        try:
            node_tree.name
        except ReferenceError:  # tree deleted before the editor caught up
            return None
        wm = bpy.context.window_manager
        if wm is None:
            return None
        framed = False
        for window in wm.windows:
            screen = window.screen
            if screen is None:
                continue
            for area in screen.areas:
                if area.type != "NODE_EDITOR" or area.ui_type != "ShaderNodeTree":
                    continue
                space = area.spaces.active
                if not isinstance(space, bpy.types.SpaceNodeEditor):
                    continue
                if space.node_tree != node_tree:
                    continue
                while len(space.path) > 1:
                    space.path.pop()
                for group in groups:
                    space.path.append(group.node_tree, node=group)
                for region in area.regions:
                    if region.type != "WINDOW":
                        continue
                    with bpy.context.temp_override(
                        window=window, screen=screen, area=area, region=region
                    ):
                        if bpy.ops.node.view_selected.poll():  # type: ignore[call-arg]
                            bpy.ops.node.view_selected()
                            framed = True
        attempts[0] += 1
        if framed or attempts[0] >= 20:
            return None
        return 0.05

    if try_frame() is not None:
        bpy.app.timers.register(try_frame, first_interval=0.05)


def run_view3d_operator(f: Callable[[], object]) -> None:
    if bpy.context.screen is None:
        return
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            for region in area.regions:
                if region.type == "WINDOW":
                    with bpy.context.temp_override(area=area, region=region):
                        f()


def run_view3d_operator_once(f: Callable[[], object]) -> None:
    if bpy.context.screen is None:
        f()
        return
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            for region in area.regions:
                if region.type == "WINDOW":
                    with bpy.context.temp_override(area=area, region=region):
                        f()
                    return
    f()


class RBR_OT_jump_to_message_source(bpy.types.Operator):
    """Jump to message source"""

    bl_idname = "rbr.jump_to_message_source"
    bl_label = "Jump to message source"
    bl_description = "Jump to the source of an RBR export message"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if hasattr(context, "rbr_export_message"):
            m: RBRExportMessage = context.rbr_export_message
            return m.object is not None or m.material is not None
        return False

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        message: RBRExportMessage = context.rbr_export_message
        if message.object is not None:
            jump_to_object(
                context,
                message.object,
                message.instancer,
                message.material,
                message.select_kind,
                [element.index for element in message.select_indices],
                self.report,
            )
        if message.material is not None:
            jump_to_material(message.material, message.node_name)
        return {"FINISHED"}


class RBR_OT_export_track(bpy.types.Operator):
    """Export an RBR track"""

    bl_idname = "rbr.export_track"
    bl_label = "Export RBR Track"
    bl_description = "Export to native RBR track format (.dls, .lbs, ...)"
    bl_options = {"UNDO"}
    handle: Optional[Any] = None

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        if rbr_blender_track_io is None:
            self.report(
                {"ERROR"},
                "rbr_blender_track_io binary is missing or failed to load",
            )
            return {"CANCELLED"}
        if bpy.context.scene is None or bpy.context.preferences is None:
            return {"CANCELLED"}
        scene_settings: RBRSceneSettings = bpy.context.scene.rbr_scene_settings
        prefs = narrow(
            bpy.context.preferences.addons[base_package].preferences,
            RBRAddonPreferences,
        )
        export_dir = prefs.get_export_directory(scene_settings.export_to)
        if export_dir is None:
            self.report({"ERROR"}, "No export directory")
            return {"CANCELLED"}
        if export_dir.strip() == "":
            self.report(
                {"ERROR"},
                f"Export directory '{scene_settings.export_to}' has no path set",
            )
            return {"CANCELLED"}
        export_dir = os.path.normpath(bpy.path.abspath(export_dir))
        if not os.path.isdir(export_dir):
            self.report({"ERROR"}, f"Export directory doesn't exist: {export_dir}")
            return {"CANCELLED"}
        scene_settings.export_errors.clear()
        scene_settings.export_warnings.clear()
        view_settings = bpy.context.scene.view_settings
        if view_settings is not None:
            view_settings.view_transform = "Standard"  # type: ignore[assignment]
        num_errors, num_warnings = rbr_blender_track_io.run_export(
            export_dir,
            scene_settings.simplify_shadows,
            scene_settings.shadow_dedup_threshold,
            scene_settings.shadow_gradient_threshold,
            scene_settings.compress_textures,
            scene_settings.keep_existing_pacenotes,
        )
        errors = "1 error" if num_errors == 1 else f"{num_errors} errors"
        warnings = "1 warning" if num_warnings == 1 else f"{num_warnings} warnings"
        if num_errors > 0:
            self.report({"ERROR"}, f"Export failed ({errors}, {warnings})")
        elif num_warnings > 0:
            self.report({"WARNING"}, f"Export complete ({warnings})")
        else:
            self.report({"INFO"}, f"Export complete ({warnings})")
        return {"FINISHED"}


def export_menu_func(self: Any, context: bpy.types.Context) -> None:
    self.layout.operator(
        RBR_OT_export_track.bl_idname,
        text="RBR Track (.trk, .lbs, ...)",
    )


def register() -> None:
    bpy.utils.register_class(RBR_OT_jump_to_message_source)
    bpy.utils.register_class(RBR_OT_export_track)
    bpy.types.TOPBAR_MT_file_export.append(export_menu_func)


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_export.remove(export_menu_func)
    bpy.utils.unregister_class(RBR_OT_export_track)
    bpy.utils.unregister_class(RBR_OT_jump_to_message_source)
