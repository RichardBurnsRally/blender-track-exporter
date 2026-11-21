import bpy

from .properties.fence import recreate_fence_node_group
from .shaders.refresh import refresh_all_rbr_shaders
from .types import OperatorReturn


class RBR_OT_recreate(bpy.types.Operator):
    """Rebuild the addon's node trees in this file (RBR shaders, textures and
    the fence node group) from the installed addon version"""

    bl_idname = "rbr.recreate"
    bl_label = "Recreate RBR node trees"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> OperatorReturn:
        refresh_all_rbr_shaders(context)
        recreate_fence_node_group()
        return {"FINISHED"}


def register() -> None:
    bpy.utils.register_class(RBR_OT_recreate)


def unregister() -> None:
    bpy.utils.unregister_class(RBR_OT_recreate)
