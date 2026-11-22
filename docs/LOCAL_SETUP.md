# Local setup

The Git checkout should live at `D:\gitdemo\Underbot`. Large applications and
environments stay on D: under `D:\Robotics`.

| Local path | Purpose |
| --- | --- |
| `D:\Robotics\gazebo-harmonic` | Native Windows Gazebo Harmonic Pixi environment |
| `D:\Robotics\rviz2-jazzy` | Shared ROS 2 Jazzy / RViz Pixi environment |
| `D:\Robotics\robot-station` | Deployed station copy used by existing shortcuts |
| `D:\Robotics\*.cmd` | Local launch shortcuts; update when source paths move |
| `perception\.private` | Ignored credentials and local recognition-memory configuration |
| `simulation\pybullet\.venv` | Shared Python environment for PyBullet and Gazebo control tools |

The workstation remains Windows. Gazebo is installed natively; no Linux
distribution or WSL environment is required by this project. The robot's
Raspberry Pi runs Linux independently.

The pre-cleanup backup is
`D:\gitdemo\archive\UnderBot-before-consolidation-2026-10-18`. It includes a Git
bundle and unpublished-source archive. Installed dependencies, private data,
model weights, and generated recordings are not source-controlled.
