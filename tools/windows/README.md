# Windows tools

This directory records the Windows launchers and ROS 2 environment used for the
active UnderBot stack. The launchers assume the checkout is
`D:\gitdemo\Underbot` and shared tools are under `D:\Robotics`.

- `launchers/`: shortcuts for the station, perception, ROS 2, and RViz.
- `deployed-snapshot/`: station deployment helpers retained for reference.
- `ros-environment/`: Pixi manifest and lockfile for ROS 2 Jazzy and RViz.

Private configuration, credentials, downloaded models, and environments remain
outside Git. See `../../docs/LOCAL_SETUP.md` for the workstation path map.
