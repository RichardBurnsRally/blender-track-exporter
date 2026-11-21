import bpy

from ..properties.scene import RBRSceneSettings


def fixup_car_location_object(obj: bpy.types.Object) -> None:
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 1
    obj.scale = [1.5, 3, 1.5]
    obj.lock_scale[:] = [True, True, True]


@bpy.app.handlers.persistent  # type: ignore
def fixup_car_location_daemon(
    scene: bpy.types.Scene, depsgraph: bpy.types.Depsgraph
) -> None:
    """Watches for car location updates"""
    for update in depsgraph.updates:
        if not isinstance(update.id, bpy.types.Object):
            continue
        readonly_obj = update.id
        obj = bpy.data.objects[readonly_obj.name]
        scene_settings: RBRSceneSettings = scene.rbr_scene_settings
        if obj != scene_settings.car_location:
            continue
        fixup_car_location_object(obj)
        break


def register() -> None:
    bpy.app.handlers.depsgraph_update_post.append(fixup_car_location_daemon)


def unregister() -> None:
    try:
        bpy.app.handlers.depsgraph_update_post.remove(fixup_car_location_daemon)
    except ValueError:
        pass
