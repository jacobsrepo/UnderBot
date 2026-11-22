# Repository cleanup record

Status: completed on 2026-11-22.

The repository now focuses on the active R09 robot description, PyBullet and
Gazebo simulation, the ROS/Foxglove station, perception, and navigation. The
confirmed controller boundaries and remaining hardware unknowns were retained
in `HARDWARE_INTERFACES.md`.

The cleanup removed:

- KiCad schematics, PCB concepts, fabrication exports, and provisional BOMs;
- the R08 delivery tree, historical CAD, compact demo rover, and duplicate R09
  export/download bundles;
- independent desktop-assistant, alternate ROS, and bundled website snapshots;
- obsolete R08 Foxglove tooling and consolidation metadata;
- parent-workspace logs, disk inventories, generated files, and one-use scripts.

The PyBullet implementation moved from `simulation/python` to
`simulation/pybullet`. Fleet, test, perception-layout, and navigation consumers
were moved to the active R09 portable URDF before the compact rover was removed.

Deleted tracked files remain available in Git history. A verified offline backup
also exists at `D:\gitdemo\archive\UnderBot-before-consolidation-2026-10-18`.
For a future public GitHub repository, publish a clean snapshot branch if old
large assets or historical material should never enter the remote history.
