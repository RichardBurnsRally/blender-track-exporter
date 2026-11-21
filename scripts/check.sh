#!/usr/bin/env bash
# Format check + type check (see requirements-dev.txt for the tools).
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m black --check .
python3 -m mypy -p rbr_track_exporter
