import bpy

import importlib.util
import os
import platform
import sys
import tomllib
from types import ModuleType
from typing import Optional

# The manifest's full version string: Blender's bl_info drops pre-release
# suffixes, which migrations need to tell apart.
with open(os.path.join(os.path.dirname(__file__), "blender_manifest.toml"), "rb") as f:
    CURRENT_VERSION: str = tomllib.load(f)["version"]


def _load_native_module() -> None:
    """Load this platform's rbr_blender_track_io binary from native/.

    One addon zip ships every platform's binary under a platform-tagged
    name; only the matching one is loaded, registered under the module
    name the rest of the addon expects (the import system derives the
    PyInit symbol from the module name, not the filename, so the files
    can be named per-platform). If there is no binary for this platform
    the addon still loads: the import/export operators report the
    missing binary when invoked.
    """
    name = f"{__package__}.rbr_blender_track_io"
    if name in sys.modules:
        return
    filename = {
        ("Windows", "AMD64"): "windows-x64.pyd",
        ("Linux", "x86_64"): "linux-x64.so",
        ("Darwin", "arm64"): "macos-arm64.so",
        ("Darwin", "x86_64"): "macos-x64.so",
    }.get((platform.system(), platform.machine()))
    if filename is None:
        return
    path = os.path.join(os.path.dirname(__file__), "native", filename)
    if not os.path.isfile(path):
        return
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        del sys.modules[name]
        print(f"RBR Addon: failed to load {filename}: {e}")


_load_native_module()

from . import daemons  # noqa: E402
from . import gpu  # noqa: E402
from . import panels  # noqa: E402
from . import properties  # noqa: E402
from . import physical_material_editor  # noqa: E402
from . import shaders  # noqa: E402
from . import recreate  # noqa: E402

from . import exporter  # noqa: E402
from . import migration  # noqa: E402
from . import preferences  # noqa: E402

importer: Optional[ModuleType]
try:
    from . import importer  # noqa: E402
except ImportError:
    # The importer might not be included in the addon.
    importer = None


# TODO test this


@bpy.app.handlers.persistent  # type: ignore
def load_post_handler(
    scene: bpy.types.Scene,
    depsgraph: bpy.types.Depsgraph,
) -> None:
    if bpy.context.scene is None:
        return
    if migration.is_legacy_file():
        print(
            "RBR Addon: file was made with the old addon, migrate it from the scene panel"
        )
        return
    migration.migrate_versions(CURRENT_VERSION)


# Modules to register, in order
modules = [
    preferences,
    properties,
    panels,
    gpu,
    daemons,
    physical_material_editor,
    shaders,
    recreate,
    migration,
]


def register() -> None:
    for module in modules:
        module.register()

    bpy.types.Scene.rbr_addon_version = bpy.props.StringProperty(
        name="RBR Addon Version",  # noqa: F821
    )

    bpy.app.handlers.load_post.append(load_post_handler)
    exporter.register()
    if importer is not None:
        importer.register()


def unregister() -> None:
    if importer is not None:
        importer.unregister()
    exporter.unregister()
    try:
        bpy.app.handlers.load_post.remove(load_post_handler)
    except ValueError:
        pass

    del bpy.types.Scene.rbr_addon_version

    for module in reversed(modules):
        module.unregister()


if __name__ == "__main__":
    try:
        unregister()
    except:  # noqa: E722
        pass
    register()
