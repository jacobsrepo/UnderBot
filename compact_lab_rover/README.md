# Compact Lab Rover: RViz2 concept preview

## Run from this repository

On Windows, install [Pixi](https://pixi.sh), open a terminal in this directory,
and run:

```text
pixi run view
```

The included manifest installs the ROS 2 Jazzy visualization dependencies via
RoboStack. The first run downloads the environment. To regenerate the URDF after
editing its source, run `pixi run build-model`.

On a computer with an existing ROS 2 Jazzy environment, install `rviz2`,
`robot_state_publisher`, and `joint_state_publisher_gui`, source that environment,
and run `python view_rover.py` (or `python3 view_rover.py` on Linux).

## Existing installation on the original Windows computer

Double-click `D:\Robotics\View Compact Lab Rover.cmd`.
RViz opens with the model and a separate joint-slider window. Drag in RViz to
orbit, use the scroll wheel to zoom, and move the joint sliders to pose the
arms, fingers, wheels and camera. Close RViz to stop the preview publishers.

This is a simplified interpretation of the supplied concept picture, not a CAD
reconstruction. The chassis has a nominal 200 x 200 mm footprint and the camera
top is about 395 mm high. Arms extend outside that footprint. +X is forward,
+Y is left, and +Z is up. The image's stated dimensions are design assumptions,
not verified measurements. Wheel placement, arm lengths, axes, travel limits,
and gripper construction are provisional. The mecanum rollers are decorative.

This model is visual only. It has no calibrated inertias, collision model,
hardware interfaces, sensor drivers, navigation or physics. Its joint limits
and effort values are placeholders and must not be used for real control.
The picture specifies ToF sensors; no LiDAR hardware is confirmed or invented.

Files:
- `rover.urdf`: generated ROS robot description, usable in later ROS projects.
- `build_model.py`: source for dimensions, geometry, colors and joints.
- `rover.rviz`: prepared camera, grid and RobotModel display.
- `view_rover.py`: local preview supervisor using ROS 2 Jazzy.

The preview sets discovery to LOCALHOST and domain 73 for its child processes.
Your normal RViz launcher and ROS settings are unchanged. These are illustrative
joint states; they do not command real motors. Use a separate live-robot launch
with real joint feedback when connecting hardware.

Next stages: replace approximate geometry with measured CAD/URDF, confirm drive
type and joint axes, add real sensor/encoder publishers, then configure mapping
and navigation (e.g. SLAM Toolbox and Nav2). Arm planning can use MoveIt 2 after
the model has accurate joints and collision geometry.
