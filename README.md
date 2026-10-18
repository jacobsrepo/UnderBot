# UnderBot

Robot models, ROS 2 / Foxglove station, perception and memory, navigation simulation, and electrical design sources. Existing development lines are preserved; see [the project map](docs/PROJECT_MAP.md) for their roles and [local setup](docs/LOCAL_SETUP.md) for this PC's working installations.

## Components

| Folder | Purpose |
| --- | --- |
| `compact_lab_rover/` | Original parametric rover URDF, RViz configuration and model generator |
| `robot_station/` | ROS gateway, telemetry demo, Qwen chat, bounded world state, memory integration and navigation executor |
| `robot-station-extension/` | Foxglove controls, chat, simulation navigation and telemetry UI |
| `perception/` | EMEET camera/YOLO pipeline, audio transport, Pi communications and PostgreSQL recognition memory |
| `navigation/` | Sample-map preparation, derived demo map, Foxglove layout and navigation documentation |
| `hardware/electrical/` | Versioned KiCad schematics, carrier/PCB designs, budgets and review reports |
| `tools/windows/` | Preserved Windows launchers, deployment overrides and shared ROS environment manifest |

## Getting started

- [Station setup and topic contract](robot_station/README.md)
- [Qwen chat and memory behavior](robot_station/AI_CHAT.md)
- [Navigation simulation and supported commands](navigation/README.md)
- [Camera, audio and perception](perception/README.md)
- [Recognition memory](perception/memory/README.md)
- [Electrical design and revision history](hardware/electrical/README.md)
- [Team workflow](CONTRIBUTING.md)

## Implementation boundaries

Camera and audio pipelines can use real devices. Navigation demonstrations use simulated robot pose and motion on a sample map; they are not physical navigation, SLAM or validated robot dynamics. General chat uses Ollama when configured. Recognition memory requires private database configuration and enrollment. Hardware forwarding remains disabled by default.

The repository contains alternative robot models and implementation lines, not a single fully integrated autonomous robot. Electrical review reports and CAD checks do not establish hardware ratings or readiness to energize. Existing documentation records historical tests; see [current validation](docs/VALIDATION.md) for checks performed during consolidation.

Dependencies, credentials, personal memory databases, recordings and local tool installations are excluded from Git. Original source revisions and development branches remain available. MATLAB/Simulink modelling is the next task and has not been started here.
