from typing import Optional

import bpy

from ..properties.scene import RBRSceneSettings
from ..properties.curve import fixup_brake_wall_object


def fixup_brake_wall_spline(spline: bpy.types.Spline, full_fixup: bool) -> None:
    """Ensure the brake wall meets RBR expectations.
    - Keeps Z=0

    curve
        Brake wall curve
    full_fixup
        Modify all handles
    """
    for point in spline.points:
        selected = point.select
        if full_fixup or selected:
            point.co.z = 0
    for bezier_point in spline.bezier_points:
        any_selected = any(
            [
                bezier_point.select_control_point,
                bezier_point.select_left_handle,
                bezier_point.select_right_handle,
            ]
        )
        if full_fixup or any_selected:
            bezier_point.handle_right.z = 0
            bezier_point.handle_left.z = 0
            bezier_point.co.z = 0


@bpy.app.handlers.persistent  # type: ignore
def fixup_brake_wall_daemon(
    scene: bpy.types.Scene, depsgraph: bpy.types.Depsgraph
) -> None:
    """Watches for brake wall updates to uphold RBR invariants"""
    for update in depsgraph.updates:
        if not isinstance(update.id, bpy.types.Object):
            continue
        readonly_obj = update.id
        obj = bpy.data.objects[readonly_obj.name]
        scene_settings: RBRSceneSettings = scene.rbr_scene_settings
        if obj != scene_settings.brake_wall:
            continue
        spline = fixup_brake_wall_object(obj)
        if spline is None:
            continue
        try:
            was_edit_mode = fixup_brake_wall_daemon.last_mode == "EDIT"
        except AttributeError:
            was_edit_mode = False
        finally:
            fixup_brake_wall_daemon.last_mode = obj.mode
        changing_to_object_mode = obj.mode == "OBJECT" and was_edit_mode
        # Only do full fixup if changing edit->object mode - too slow otherwise
        fixup_brake_wall_spline(spline, full_fixup=changing_to_object_mode)
        break


def register() -> None:
    bpy.app.handlers.depsgraph_update_post.append(fixup_brake_wall_daemon)


def unregister() -> None:
    try:
        bpy.app.handlers.depsgraph_update_post.remove(fixup_brake_wall_daemon)
    except ValueError:
        pass
