#!/usr/bin/env bash
# Create or update .venv with the dev tooling (black, mypy, headless bpy and
# its type stubs; see requirements-dev.txt). A stamp records what the venv was
# built with, so re-running is free until .python-version or requirements change.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=$(cat .python-version)
PYTHON="python$PY"
STAMP=.venv/stamp
WANT="python==$PY requirements==$(cksum requirements-dev.txt | cut -d' ' -f1)"

if [ -f "$STAMP" ] && [ "$(cat "$STAMP")" = "$WANT" ]; then
    exit 0
fi

if ! command -v "$PYTHON" >/dev/null; then
    echo "error: $PYTHON is required (see .python-version)" >&2
    exit 1
fi

rm -rf .venv
"$PYTHON" -m venv .venv
.venv/bin/python -m pip install --quiet -r requirements-dev.txt
# Fix fake-bpy's broken collection MRO in the installed stubs (in-place).
.venv/bin/python scripts/patch-bpy-stubs.py \
    "$(.venv/bin/python -c 'import site; print(site.getsitepackages()[0])')"

echo "$WANT" > "$STAMP"
