# Working on UnderBot

Use a feature branch for each change and keep commits focused. The active robot
description is R09 under `models/r09/underbot_description`; do not add another
robot model without documenting why it is needed.

## Editing and checks

- Robot geometry and joints: edit the R09 URDF/Xacro and meshes under
  `models/r09/underbot_description`, then load the result in PyBullet and Gazebo.
- PyBullet dynamics: work in `simulation/pybullet` and run its unit tests.
- Gazebo worlds, demonstrations, and controls: work in `simulation/gazebo`.
- Foxglove layout: edit `robot_station/build_layout.py`, regenerate the layout,
  and verify it against the station demo.
- Foxglove extension: run `npm ci`, `npm run build`, and `npx tsc --noEmit` in
  `robot-station-extension`.
- ROS gateway: run `python -m unittest test_gateway -v` in ROS 2 Jazzy, or use
  the Pixi task in `robot_station` on Windows.
- Before committing: run `git diff --check`, then inspect `git diff` and
  `git status`.

Preserve documented topic names, units, frames, and JSON formats, or update all
producers and consumers together. Report measured state separately from command
requests. Never label synthetic messages as live robot data. Keep physical
hardware forwarding disabled until controller interfaces, limits, watchdogs,
and stop behavior have been verified.

Use environment variables or ignored local configuration for credentials. Do
not commit keys, passwords, recordings, dependencies, generated output, or
machine caches.

## Current integration priorities

1. Measure the R09 robot and replace estimated masses, inertias, limits, and
   actuator performance.
2. Add a coordinated end-effector trajectory interface and demonstration
   recorder for pick-and-place data.
3. Validate contact, grasping, and collision behavior in Gazebo.
4. Define and test the Pi-to-controller command and telemetry contract before
   enabling the physical robot.
5. Reuse the same task-level commands in simulation and on hardware, with a
   hardware-specific low-level controller underneath.

The simulation and station demonstrations establish software behavior only;
physical capability requires measurement and hardware tests.
