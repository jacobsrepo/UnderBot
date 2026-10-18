#!/usr/bin/env bash
set -euo pipefail
station_address="${1:-100.123.136.69}"
if [[ ! "$station_address" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]*$ ]]; then
  echo 'Use an IPv4 address or hostname.' >&2
  exit 1
fi
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo 'ROS 2 Jazzy is required at /opt/ros/jazzy.' >&2
  exit 1
fi
sudo apt-get update
sudo apt-get install -y ros-jazzy-foxglove-bridge python3-pil
mkdir -p "$HOME/.config/systemd/user"
station_python="$(command -v python3)"
station_path="$PWD"
cat > "$HOME/.config/systemd/user/underbot-station.service" <<EOF
[Unit]
Description=UnderBot Foxglove station (hardware disabled)
After=network-online.target

[Service]
Type=simple
WorkingDirectory="$station_path"
ExecStart=/bin/bash -c 'source /opt/ros/jazzy/setup.bash && exec "$station_python" "$station_path/start.py" --address "$station_address"'
Restart=on-failure
RestartSec=5
KillMode=control-group

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now underbot-station.service
sleep 3
systemctl --user --no-pager status underbot-station.service
echo "Station installed: ws://$station_address:8765. Hardware forwarding is disabled."
echo 'The user service runs while the user session is active. For unattended boot, an administrator can enable loginctl linger for this user.'
