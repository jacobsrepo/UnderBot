# Local setup and preservation

## Where to work

Primary consolidated Git checkout: `D:\gitdemo\Underbot\.publish-underbot`.
This existing path is intentionally retained because live launchers and memory configuration reference it.

| Local path | Purpose |
| --- | --- |
| `D:\Robotics\robot-station` | Existing deployed station; core sources are preserved; the source navigation loader additionally supports the bundled repository map; launch/deploy overrides are preserved in tools/windows/deployed-snapshot |
| `D:\Robotics\rviz2-jazzy` | Shared installed Pixi ROS/RViz environment |
| `D:\Robotics\underbot-r08` | Existing R08 Foxglove deployment |
| `D:\Robotics\compact-lab-rover` | Existing original rover deployment; local RViz/view settings retained |
| `D:\Robotics\*.cmd` | Existing launch shortcuts, unchanged |
| `.publish-underbot\perception\.private` | Local credentials/configuration; deliberately excluded from Git |
| `D:\gitdemo\Underbot` | Historical setup/diagnostic/migration scripts and original concept sources, retained locally |
| `D:\gitdemo\temp\Underbot_URDF\foxglove-r08` | Original Foxglove layout metadata, backups and review images |
| `D:\gitdemo\temp\Underbot_URDF\UnderBot-Personal` | Original R08 checkout; newer R09 imported from its remote into the consolidated repository |
| `D:\gitdemo\Underbot-Website` and `D:\gitdemo\temp\Underbot_URDF\Underbot-Website` | Existing website checkouts, unchanged |
| `D:\gitdemo\RoboticsProject` | Original FreeCAD files, retained and copied into models/historical-cad |
| `D:\MATLAB\R2026b` | Existing MATLAB installation; activation/toolboxes are a separate next task |

## Backup

`D:\gitdemo\archive\UnderBot-before-consolidation-2026-10-18` contains a full Git bundle of the original UnderBot branch histories and a ZIP of the initial unpublished files. Original active installations were not moved or deleted.

## What stays local

Dependency environments, downloaded model weights, PDF tools, KiCad session settings, personal identity databases, credentials, camera recordings and machine caches do not belong in source control. No personal database contents are published. Historical one-off setup/authentication/migration scripts remain in the original local folder; current runtime source is in the component directories.

The original `navigation/sample-map-planning.zip` and extracted upstream map stay local. Derived `demo_map.npz`, metadata and preparation code are published. Use the documented source URL and SHA-256 in navigation/README.md to retrieve the upstream map for regeneration. The third-party `hardware/electrical/adeept-v4.zip` remains local and in the backup; generated project designs are published.

## Starting existing work

Continue using the existing D:/Robotics shortcuts. No robot services were restarted or hardware commands issued by consolidation. For portable setup, use the component README and configure local paths, licensed applications and private settings separately.
