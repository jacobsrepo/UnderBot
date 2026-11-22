# Architecture

The Raspberry Pi is the intended high-level computer. It owns perception,
planning, task sequencing, ROS publication, and the future hardware adapter. A
microcontroller or retained vendor controller must own time-critical actuation,
watchdogs, local limits, and stop behavior.

The Windows workstation provides development, Foxglove visualization, PyBullet
checks, and Gazebo simulation. Simulation commands never reach hardware.

## Interfaces

- ROS 2 and `foxglove_bridge` carry station telemetry and bounded station
  commands.
- Gazebo Transport carries native Windows simulation commands and feedback.
- The physical-controller protocol is unresolved. It must eventually expose the
  same conceptual contract: bounded targets, measured state, acknowledgements,
  faults, cancellation, and a controller-owned timeout.

Imitation-learning demonstrations store observations separately from actions.
The current Gazebo recorder captures joint state, full arm targets, and available
object poses. It is infrastructure for collecting data, not a trained policy.
