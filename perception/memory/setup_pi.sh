#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then echo 'ROS 2 Jazzy is required'; exit 1; fi
mkdir -p .private
chmod 700 .private
exec > >(tee .private/pi-setup.log) 2>&1
printf '\nEnter the Pi sudo password when prompted. It will not be saved.\n'
sudo -v
sudo apt-get update
sudo apt-get install -y postgresql python3-venv libgl1 libglib2.0-0 libportaudio2
sudo systemctl enable --now postgresql
python3 -m venv .venv
.venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.14.0+cpu' 'torchvision==0.29.0+cpu'
.venv/bin/pip install -r memory/requirements-pi-tested.txt
.venv/bin/pip check
.venv/bin/python -m memory.bootstrap_pi
.venv/bin/python -m memory.download_models
if [[ -f .private/base-sync.pgpass ]]; then .venv/bin/python -m memory.finish_pi; fi
sudo install -m 644 memory/underbot-memory.service /etc/systemd/system/underbot-memory.service
sudo systemctl daemon-reload
sudo systemctl enable --now underbot-memory.service
.venv/bin/pip freeze > .private/requirements-installed.txt
printf 'ready\n' > .private/pi-setup-ready
printf '\nUNDERBOT_PI_SETUP_READY - local database and sync service installed.\n'
