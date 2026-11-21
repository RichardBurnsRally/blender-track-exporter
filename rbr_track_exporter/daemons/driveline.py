from typing import Optional

import bpy

from ..properties.scene import RBRSceneSettings
from ..properties.curve import fixup_driveline_obj


def fixup_driveline_spline(spline: bpy.types.Spline, full_fixup: bool) -> None:
    """Ensure the driveline meets RBR expectations.
    - Mirrors the spline handles, RBR only supports mirrored handles
    - Sets radius == 1, this value is used to scale child objects like render
      distance.

    curve
        Driveline curve
    full_fixup
        Modify all handles
    """
    for bezier_point in spline.bezier_points:
        any_selected = any(
            [
                bezier_point.select_control_point,
                bezier_point.select_left_handle,
                bezier_point.select_right_handle,
            ]
        )
        # Skip the point if nothing is selected. Must do this to avoid a
        # performance penalty in edit mode.
        if not full_fixup and not any_selected:
            continue
        # Force use of aligned handles
        bezier_point.handle_left_type = "ALIGNED"
        bezier_point.handle_right_type = "ALIGNED"
        # So that parenting works correctly without scaling the objects
        bezier_point.radius = 1.0
        # Force the handles to be equal length
        pos = bezier_point.co
        if full_fixup:
            # Set handles to the average of both
            left = bezier_point.handle_left
            right = bezier_point.handle_right
            # Vector from left to right, halved
            between = (right - left) * 0.5
            bezier_point.handle_left = pos - between
            bezier_point.handle_right = pos + between
        else:
            # Move opposite handle
            if not bezier_point.select_right_handle:
                left = bezier_point.handle_left
                bezier_point.handle_right = 2 * pos - left
            if not bezier_point.select_left_handle:
                right = bezier_point.handle_right
                bezier_point.handle_left = 2 * pos - right


@bpy.app.handlers.persistent  # type: ignore
def fixup_driveline_daemon(
    scene: bpy.types.Scene, depsgraph: bpy.types.Depsgraph
) -> None:
    """Watches for driveline updates to uphold RBR invariants"""
    for update in depsgraph.updates:
        if not isinstance(update.id, bpy.types.Object):
            continue
        readonly_obj = update.id
        obj = bpy.data.objects[readonly_obj.name]
        scene_settings: RBRSceneSettings = scene.rbr_scene_settings
        if obj != scene_settings.driveline:
            continue
        driveline_objects = fixup_driveline_obj(obj)
        if driveline_objects is None:
            continue
        try:
            was_edit_mode = fixup_driveline_daemon.last_mode == "EDIT"
        except AttributeError:
            was_edit_mode = False
        finally:
            fixup_driveline_daemon.last_mode = obj.mode
        changing_to_object_mode = obj.mode == "OBJECT" and was_edit_mode
        # Only do full fixup if changing edit->object mode - too slow otherwise
        if driveline_objects.spline is not None:
            fixup_driveline_spline(
                driveline_objects.spline, full_fixup=changing_to_object_mode
            )
        break


def register() -> None:
    bpy.app.handlers.depsgraph_update_post.append(fixup_driveline_daemon)


def unregister() -> None:
    try:
        bpy.app.handlers.depsgraph_update_post.remove(fixup_driveline_daemon)
    except ValueError:
        pass
