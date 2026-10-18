#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/.."
source /opt/ros/jazzy/setup.bash
# The systemd memory service handles sync; avoid launching a second sync worker.
exec .venv/bin/python start.py --camera-index "${1:-0}" --memory-config .private/robot.json --no-memory-sync
