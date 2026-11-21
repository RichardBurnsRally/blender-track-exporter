"""Migration of .blend files made with the pre-Rust RBR addon (0.2 to 0.3.3),
and between versions of this addon.

Self-contained: the old data is read as plain ID properties and nothing else
in the addon depends on this package beyond the scene panel box and the
load handler."""

from .legacy import is_legacy_file as is_legacy_file
from .ui import draw_scene_box as draw_scene_box
from .versions import migrate_versions as migrate_versions
from . import ui


def register() -> None:
    ui.register()


def unregister() -> None:
    ui.unregister()
