#!/usr/bin/env bash
# Load the addon in headless blender and check it registers cleanly, then
# build every node tree it generates.
# Needs the bpy module (see requirements-dev.txt).
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/smoke.py
python3 scripts/node_trees.py
