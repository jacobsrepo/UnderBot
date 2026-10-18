# Existing Windows deployment

These files preserve the working PC launchers and installed station overrides as of 2026-10-18. They intentionally reference this PC's D: paths and are not a portable installer.

- `launchers/`: copies of the existing D:/Robotics shortcuts. Original shortcuts remain in place.
- `deployed-snapshot/`: installed station launch/deployment overrides and its original README. The portable source remains in `robot_station/`.
- `ros-environment/`: manifest and lockfile for the installed shared ROS/RViz environment.

Runtime configuration, database credentials, enrolled identities, downloaded models and environments remain local. Do not run deployment scripts merely to inspect this archive. See ../../docs/LOCAL_SETUP.md for the path map.
