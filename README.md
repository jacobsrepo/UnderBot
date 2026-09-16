# UnderBot

ROS 2 Jazzy robot concept model and Foxglove control-station scaffold.
The robot is currently a Raspberry Pi with no attached sensors or actuators.

## Repository contents

| Folder | Contents | Current status |
| --- | --- | --- |
| `compact_lab_rover/` | Approximate URDF body, articulated arms/grippers/wheels/camera, model generator, RViz settings and joint-slider launcher | Visual concept preview; dimensions and joints are provisional |
| `robot_station/` | Foxglove layout, ROS bridge configuration, gateway, synthetic telemetry/demo, Pi deployment scripts and gateway tests | Local demo verified; Pi deployment not yet confirmed |
| `robot-station-extension/` | TypeScript source and npm lockfile for movement/camera controls, IMU horizon, speed, communications requests and chat | Built and exercised with the local ROS demo |

The model and station are separate runnable components. The station demo uses a
simple moving pose, example map/path and synthetic images; it does not yet load
or animate the articulated URDF. Model preview uses ROS domain 73, station demo
uses domain 74, and both restrict discovery to localhost.

## Start here

Clone this branch (or switch to it in an existing clone):

```sh
git clone --branch EM-URDF-Body https://github.com/jacobsrepo/UnderBot.git
cd UnderBot
```

- **View the robot body:** follow [model setup](compact_lab_rover/README.md).
- **Use the dashboard:** follow [station setup and topic contract](robot_station/README.md).
- **Modify the controls:** follow [extension build instructions](robot-station-extension/README.md).
- **Work as a team:** read [CONTRIBUTING.md](CONTRIBUTING.md).

Windows demos use native ROS packages through Pixi; Linux on the Windows PC is
not required. Foxglove and Pixi are installed separately. A Pi with an existing
Ubuntu/apt-based Jazzy installation can run the supplied deployment script.

## What is and is not implemented

The station displays image streams, IMU orientation, speed, an occupancy map and
a planned-path overlay. It publishes movement, camera, audio-session and chat
requests. The gateway starts with hardware forwarding disabled. The demo labels
all synthetic sensor/perception data, and the chat placeholder explicitly reports
that no AI model is configured.

This repository does **not** include accurate CAD, calibrated mass/inertia,
collision geometry, Gazebo physics, sensor/motor drivers, SLAM, Nav2 planning,
YOLO inference, microphone/audio transport, or an AI provider. It provides the
visualization and topic interfaces for those future integrations. The displayed
example path is not computed by a planner or guaranteed optimal.

Use `build_model.py` as the model geometry source and regenerate `rover.urdf`.
Use `build_layout.py` as the dashboard layout source and regenerate
`underbot-station.json`. Commit each generator together with its output.

## Sharing and dependencies

Source, configuration, tests, documentation, and the npm lockfile belong in Git.
Dependencies (`node_modules`, `.pixi`), compiled extensions, logs, recordings and
credentials do not. Build an extension package with `npm run package` when needed;
share the `.foxe` separately as a release artifact. Installed programs and local
D-drive shortcuts are not part of this repository.

No project-wide open-source license has been selected. The extension remains
`UNLICENSED`; choose a license deliberately before distributing it as an
open-source package.
