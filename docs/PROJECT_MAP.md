# Project map

`models/r09/underbot_description` is the single robot-description source of
truth. Both simulators and the fleet demo load that model. Earlier R08, compact
rover, FreeCAD, PCB, desktop-assistant, alternate ROS, and website snapshots were
removed from the active tree during repository cleanup; they remain recoverable
from Git history and the pre-cleanup backup.

## Runtime components

```text
R09 robot description
  |-- PyBullet model checks and dynamics
  |-- Gazebo physics, controls, and demonstrations
  |-- ROS/Foxglove station model and fleet visualization
  `-- Perception layout model

Camera/audio --> perception --> ROS topics --> station/Foxglove
Navigation demo ---------------------------> station/Foxglove
Gazebo controls --> Gazebo Transport (simulation only)
Physical controllers --> not integrated yet
```

The station publishes real ROS 2 topics even when their values come from demo
publishers. Gazebo currently runs as an isolated native Windows simulation and
does not publish those station ROS topics. The physical T12, arms, grippers, and
MCU do not yet share a validated command/feedback adapter with either simulator.

## Source-of-truth rules

- Change robot geometry, limits, collisions, and inertias in the active R09
  package, then rerun both simulator checks.
- Keep local credentials and recognition data under ignored `.private` paths.
- Put reproducible source in Git; keep generated worlds, recordings, caches,
  virtual environments, and installed software outside Git.
- Add a new top-level component only when it has a distinct maintained runtime
  responsibility. Historical snapshots belong in Git history, not the live tree.
