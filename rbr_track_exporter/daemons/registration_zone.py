import bpy

from ..properties.scene import RBRSceneSettings


def fixup_registration_zone_object(obj: bpy.types.Object) -> None:
    obj.empty_display_type = "SPHERE"
    obj.scale.y = obj.scale.x
    obj.scale.z = obj.scale.x


@bpy.app.handlers.persistent  # type: ignore
def fixup_registration_zone_daemon(
    scene: bpy.types.Scene, depsgraph: bpy.types.Depsgraph
) -> None:
    """Watches for registration zone updates"""
    for update in depsgraph.updates:
        if not isinstance(update.id, bpy.types.Object):
            continue
        readonly_obj = update.id
        obj = bpy.data.objects[readonly_obj.name]
        scene_settings: RBRSceneSettings = scene.rbr_scene_settings
        if obj != scene_settings.registration_zone:
            continue
        fixup_registration_zone_object(obj)
        break


def register() -> None:
    bpy.app.handlers.depsgraph_update_post.append(fixup_registration_zone_daemon)


def unregister() -> None:
    try:
        bpy.app.handlers.depsgraph_update_post.remove(fixup_registration_zone_daemon)
    except ValueError:
        pass
