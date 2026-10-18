# Project map

Consolidated on 2026-10-18. This is a source and history consolidation, not a claim that the independent stacks are runtime-integrated.

| Component | Location | Provenance / role |
| --- | --- | --- |
| Working Foxglove station | `robot_station/`, `robot-station-extension/` | EM-URDF-Body plus previously unpublished station, Qwen, navigation and memory work |
| Camera/audio/memory | `perception/` | Existing local Windows/Pi pipelines; private configuration stays local |
| Navigation demo | `navigation/` | Derived Autoware sample map and planning/command demonstration |
| Electrical design | `hardware/electrical/` | All local design revisions retained; Carrier-r10 is the routed carrier review, not proof of complete robot readiness |
| Original rover | `compact_lab_rover/` | Original model retained at its existing path |
| Historical FreeCAD | `models/historical-cad/` | Original Compact Lab Rover CAD and pictures |
| R08 robot model | `models/r08/` | Full model-source snapshot at 3f28a65; matches the prior published R08 revision |
| R09 robot model | `models/r09/` | Full model-source snapshot at d508b07, including final exports and textured models |
| Cortex desktop assistant | `desktop/` | Complete Local-VLA-Setup snapshot at bfcace6; run from this folder using its README |
| Alternate ROS subsystem | `ros2_subsystem/` | Complete Ros2-subsystem snapshot at 9f3b462; colcon workspace and Linux services remain independent |
| Project website | `website/` | Underbot-Website main snapshot; existing website repository/deployments remain independent |
| Windows integration | `tools/windows/` | Preserved working launchers, environment manifests and deployed overrides |

## Integration boundaries

- The Foxglove stack uses `/station/...`; the alternate ROS stack uses `/underbot/...` and publishes proposed plans. They are not interchangeable without topic/behavior adapters.
- Cortex, station Qwen chat and the ROS VLA node are distinct applications. No one has been replaced by another.
- Original rover, R08 and R09 models are alternatives. Model selection and mass/inertia/hardware assumptions must be reviewed before MATLAB/Simulink work.
- Existing branches remain available. Imported branch histories are retained as merge parents; full source trees are placed in their own directories so root-level files do not overwrite one another.
- Historical READMEs and validation reports retain their original scope and dates. Current checks are recorded in VALIDATION.md.

## Repository workflow

Use `main` as the consolidated source baseline. Develop new work on feature branches and review changes before integration. The original EM-URDF-Body, Local-VLA-Setup and Ros2-subsystem branches remain preserved. Do not force-push or delete them as part of this consolidation.

The website still deploys from https://github.com/jacobsrepo/Underbot-Website and the original model repository remains https://github.com/gautamsajeen/UnderBot-Personal. Imported folders are snapshots; future changes require an explicit sync or a decision to make this repository their source of truth.
