# UnderBot

UnderBot is an R09 mobile-manipulator project with a ROS 2 / Foxglove station,
camera and audio perception, navigation experiments, and Python-based simulation.
The repository describes work in progress; simulated behavior is not evidence of
physical robot performance.

## Repository map

| Folder | Purpose |
| --- | --- |
| `models/r09/underbot_description/` | Active robot URDF, meshes, limits, inertial data, and simulator configuration |
| `simulation/pybullet/` | Fast fixed-base dynamics and model-import checks |
| `simulation/gazebo/` | Native Windows Gazebo world, coordinated arm controls, and demonstration recording |
| `robot_station/` | ROS gateway, telemetry, AI chat, world state, and navigation execution |
| `robot-station-extension/` | Foxglove station controls and panels |
| `perception/` | Camera, audio, Pi communication, and recognition memory |
| `navigation/` | Sample-map planning and fleet demonstrations using R09 |
| `tools/windows/` | Current Windows launchers and the reproducible ROS environment |
| `docs/` | Architecture, hardware boundaries, setup, validation, and cleanup record |

## Start here

- [Architecture and component boundaries](docs/ARCHITECTURE.md)
- [Local Windows and Pi setup](docs/LOCAL_SETUP.md)
- [Hardware interfaces and unresolved decisions](docs/HARDWARE_INTERFACES.md)
- [Validation status](docs/VALIDATION.md)
- [PyBullet simulation](simulation/pybullet/README.md)
- [Gazebo simulation](simulation/gazebo/README.md)
- [ROS/Foxglove station](robot_station/README.md)
- [Perception](perception/README.md)

Dependencies, credentials, recordings, local databases, generated simulation
data, and installed applications are excluded from Git. Hardware forwarding is
disabled by default. The current Gazebo controls use Gazebo Transport rather than
ROS 2; integration with the physical motor controllers remains future work.
