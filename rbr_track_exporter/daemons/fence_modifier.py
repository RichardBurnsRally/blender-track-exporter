import bpy

from ..properties.fence import get_or_create_fence_modifier
from ..properties.mesh import RBRMeshType


@bpy.app.handlers.persistent  # type: ignore
def fence_modifier_order_daemon(
    scene: bpy.types.Scene, depsgraph: bpy.types.Depsgraph
) -> None:
    """Keeps the .rbr.fence modifier last in the stack so user modifiers (e.g.
    shrinkwrap) shape the fence line and the fence geometry regenerates from the
    result, instead of deforming the generated posts/tiles. Re-adds the modifier
    if the user deletes it from a fence mesh."""
    for update in depsgraph.updates:
        if not isinstance(update.id, bpy.types.Object):
            continue
        obj = bpy.data.objects.get(update.id.name)
        if obj is None:
            continue
        index = obj.modifiers.find(".rbr.fence")
        if index < 0:
            mesh = obj.data
            if not isinstance(mesh, bpy.types.Mesh):
                continue
            if RBRMeshType[mesh.rbr_mesh_settings.mesh_type] is not RBRMeshType.FENCE:
                continue
            # user deleted the modifier from a fence mesh; re-add it
            get_or_create_fence_modifier(obj, mesh.rbr_mesh_settings.fence)
            continue
        last = len(obj.modifiers) - 1
        if index != last:
            # idempotent: once last, this no-ops and the re-trigger stops
            obj.modifiers.move(index, last)


def register() -> None:
    bpy.app.handlers.depsgraph_update_post.append(fence_modifier_order_daemon)


def unregister() -> None:
    try:
        bpy.app.handlers.depsgraph_update_post.remove(fence_modifier_order_daemon)
    except ValueError:
        pass
