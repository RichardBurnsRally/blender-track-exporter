"""Steps between versions of this addon, run on load for files that aren't
from the old addon."""

import bpy

from ..properties.fence import recreate_fence_node_group
from ..shaders.refresh import refresh_all_rbr_shaders
from . import texture_bundles


def migrate_versions(current_version: str) -> None:
    scene = bpy.context.scene
    if scene is None:
        return
    texture_bundles.migrate(bpy.context)
    iteration = 0
    while scene.rbr_addon_version != current_version:
        version = scene.rbr_addon_version
        if version == "":
            # unstamped: new, or saved before files were stamped
            refresh_all_rbr_shaders(bpy.context)
            recreate_fence_node_group()
            scene.rbr_addon_version = current_version
        else:
            print(
                f"RBR Addon: unexpected version '{version}' in file, skipping migrations"
            )
            scene.rbr_addon_version = current_version
            break
        iteration += 1
    if iteration > 0:
        print("RBR Addon: reached migration target")
