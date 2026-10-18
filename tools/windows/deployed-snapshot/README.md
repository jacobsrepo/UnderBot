# UnderBot Foxglove station

Prepared for ROS 2 Jazzy and the Pi at `100.123.136.69` (`underbot`).
The Pi currently has no hardware attached. Live mode publishes station status
only; missing cameras, IMU, odometry, map and perception remain missing.

## Windows viewer

1. Install the `UnderBot Control Station` extension from `../robot-station-extension`:
   `npm ci`, then `npm run local-install`. Restart Foxglove.
   Local extensions require a Foxglove developer seat.
2. Import `underbot-station.json` using Foxglove's layout menu.
3. Open a Foxglove WebSocket connection to `ws://100.123.136.69:8765`.

The layout has a camera view, an annotated perception view, a top-down room map
with the `/plan` path overlay, and a custom controls/telemetry/chat panel.
L/R/U/D is assumed to mean pan/tilt controls for one camera. Add more Image panels
if the hardware design instead has four cameras.

## Topic contract

| Topic | ROS 2 type | Producer / purpose |
|---|---|---|
| `/camera/image/compressed` | `sensor_msgs/msg/CompressedImage` | Camera driver, JPEG/PNG |
| `/perception/annotated/compressed` | `sensor_msgs/msg/CompressedImage` | YOLO adapter renders boxes, labels and pose skeletons onto the matching frame |
| `/imu/data` | `sensor_msgs/msg/Imu` | Fused valid quaternion; covariance[0] = -1 means no orientation |
| `/odom` | `nav_msgs/msg/Odometry` | Actual measured speed; UI displays hypot(vx, vy) |
| `/map` | `nav_msgs/msg/OccupancyGrid` | SLAM/map server, transient-local durability |
| `/plan` | `nav_msgs/msg/Path` | Nav2 global path, not a claim of mathematical optimality |
| `/scan` | `sensor_msgs/msg/LaserScan` | Optional LiDAR |
| `/tf`, `/tf_static` | `tf2_msgs/msg/TFMessage` | Correct map/odom/base/sensor transforms |
| `/station/status` | `std_msgs/msg/String` | JSON heartbeat, gateway publishes twice per second |
| `/station/cmd_vel` | `geometry_msgs/msg/Twist` | Requested F/B or L/R turning; optional strafe in settings |
| `/station/camera_cmd` | `geometry_msgs/msg/Twist` | Pan angular.z, tilt angular.y velocity requests |
| `/station/comms/request` | `std_msgs/msg/String` | JSON `{"enabled":true}` or false |
| `/station/ai/request` | `std_msgs/msg/String` | JSON `{"id":"unique-id","text":"question"}` |
| `/station/ai/response` | `std_msgs/msg/String` | JSON `{"id":"same-id","ok":true,"text":"answer"}` |

AI chat is a transport interface, not an installed language model. The included
gateway returns an explicit “not configured” reply. Implement one AI request
subscriber and remove the placeholder subscription when integrating your backend.
No API keys belong in the layout, extension, or Git. Chat has no motor-command path.

The comms button requests an audio session; it does not transmit microphone audio.
Your eventual audio/WebRTC adapter must implement the request and report actual
session state. The gateway currently reports it as not configured.

## Raspberry Pi setup

Copy this directory to the Pi, then run `bash setup_pi.sh`. This installs the bridge
from the existing ROS apt repository and creates a systemd **user** service.
It binds to the specified Tailscale address, with only station request topics
allowed for client publishing. Stop with `systemctl --user stop underbot-station`.
Inspect with `journalctl --user -u underbot-station -f`.

For manual launch in a sourced Jazzy shell:

```sh
python3 start.py --address 100.123.136.69
```

## Separate synthetic demo

```sh
python3 start.py --demo --port 8766
```

Connect the same layout to `ws://127.0.0.1:8766`. Domain 74 and localhost discovery
isolate the test publishers. The panel says SYNTHETIC DEMO, and both images are
watermarked. You can enable controls to move the test pose and watch odometry,
orientation and map position change. This is a kinematic UI test: there is no
collision physics, path following, SLAM or YOLO inference. The path and map are
fixed example data. Audio/AI still report not configured.

## Before attaching motors

The installed gateway has `hardware_enabled=false` and creates **no motor-output
publisher**. To integrate later, implement a reviewed controller adapter for
`/station/guarded_cmd_vel` and explicitly enable hardware on the gateway. Do not
connect the raw UI request topic directly to motor drivers. The gateway limits
planar speed to 0.2 m/s and yaw rate to 0.5 rad/s, rejects nonfinite values, and
outputs zero after 350 ms without a command. The motor controller itself must
also stop on stale commands or gateway failure, and retain its physical emergency
stop. UI stop is only a software zero command. Multi-operator arbitration and
Nav2/manual command arbitration must be added before sharing motor control.

The UI disables controls when its heartbeat is stale, starts disarmed, publishes
held commands at 10 Hz, and stops on release, lost pointer capture, window blur,
panel removal or visibility change. Review camera-axis conventions before adding
actuator hardware. Camera forwarding is not implemented in this gateway.

## Build / validation

Generate the desktop import layout with `python build_layout.py` (standard library only).
Run `python -m unittest test_gateway -v` in a sourced ROS
environment. Extension: `npm run build` and `npx tsc --noEmit`.

References: [Foxglove extensions](https://docs.foxglove.dev/docs/extensions),
[ROS bridge](https://docs.foxglove.dev/docs/fleet/bridge),
[layout import](https://docs.foxglove.dev/docs/visualization/layouts).
