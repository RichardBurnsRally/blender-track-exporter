"""Smoke test: enable + disable the addon in headless blender (the bpy pip
module) and fail on any registration error. Run via scripts/smoke.sh.

Forces the no-core path: every platform's native binary is hidden for the
duration so the addon must register without it (the contract this guards).
The addon is designed to load fully and report the missing core only when
the import/export operators are invoked.
"""

import os
import sys

import bpy  # type: ignore

# importable only once bpy has set up blender's script paths
import addon_utils  # type: ignore

ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON_DIR)

native_dir = os.path.join(ADDON_DIR, "rbr_track_exporter", "native")
hidden_dir = native_dir + ".smoke-hidden"

# Recover the binaries if a previous run was interrupted between hide/restore.
if os.path.isdir(hidden_dir) and not os.path.isdir(native_dir):
    os.rename(hidden_dir, native_dir)

hidden = False
if os.path.isdir(native_dir):
    os.rename(native_dir, hidden_dir)
    hidden = True

try:
    # enable() catches registration exceptions, prints the traceback, and
    # returns None — so a None here means the addon blew up somewhere.
    module = addon_utils.enable(
        "rbr_track_exporter", default_set=False, persistent=False
    )
    if module is None:
        sys.exit("smoke test FAILED: could not enable rbr_track_exporter")

    if "export_track" not in dir(bpy.ops.rbr):
        sys.exit("smoke test FAILED: export operator not registered")

    # The native core is hidden, so nothing on the registration path may pull
    # it in (ffi.py, which imports it, is only ever imported by the rust side).
    if "rbr_track_exporter.rbr_blender_track_io" in sys.modules:
        sys.exit("smoke test FAILED: native core loaded despite being hidden")

    try:
        addon_utils.disable("rbr_track_exporter", default_set=False)
    except Exception as e:
        sys.exit(f"smoke test FAILED: disable raised {e!r}")
finally:
    if hidden:
        os.rename(hidden_dir, native_dir)

print("smoke test passed")
