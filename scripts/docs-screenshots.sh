#!/usr/bin/env bash
# Regenerate the docs' node tree screenshots (docs/src/images) in the blender
# UI. Opens a blender window for a few seconds. BLENDER overrides the binary.
set -euo pipefail
cd "$(dirname "$0")/.."

BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
TMP=$(mktemp -d)
# Keep the screen awake and the screensaver away: the shots are taken from
# what's on screen, and a covered window can stall drawing.
caffeinate -dimsu -t 900 &
AWAKE=$!
trap 'kill $AWAKE 2>/dev/null; rm -rf "$TMP"' EXIT

# Opening a file skips the splash screen, which would otherwise cover the shots.
"$BLENDER" --background --factory-startup \
  --python-expr "import bpy; bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.wm.save_as_mainfile(filepath='$TMP/empty.blend')" \
  > /dev/null
"$BLENDER" --factory-startup "$TMP/empty.blend" --python scripts/docs-screenshots.py
