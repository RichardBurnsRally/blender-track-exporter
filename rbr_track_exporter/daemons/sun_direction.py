import bpy

from ..properties.world import RBRWorldSettings


@bpy.app.handlers.persistent  # type: ignore
def sun_direction_daemon(
    scene: bpy.types.Scene, depsgraph: bpy.types.Depsgraph
) -> None:
    """Watches for sun object updates and updates the shaders."""
    for update in depsgraph.updates:
        if not update.is_updated_transform:
            continue
        if not isinstance(update.id, bpy.types.Object):
            continue
        obj = update.id.original
        if not isinstance(obj, bpy.types.Object):
            continue
        if not isinstance(obj.data, bpy.types.SunLight):
            continue
        should_tag = False
        for world in bpy.data.worlds:
            rbr_world: RBRWorldSettings = world.rbr_world_settings
            if rbr_world.sun == obj:
                rbr_world.update_sun_direction()
                should_tag = True
        if should_tag:
            # required or the ShaderNodeAttributes won't get updated
            scene.update_tag()
        break


def register() -> None:
    bpy.app.handlers.depsgraph_update_post.append(sun_direction_daemon)


def unregister() -> None:
    try:
        bpy.app.handlers.depsgraph_update_post.remove(sun_direction_daemon)
    except ValueError:
        pass
