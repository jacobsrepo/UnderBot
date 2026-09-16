# UnderBot Control Station extension

Movement and camera direction controls, IMU attitude, odometry speed, audio-session requests and robot AI chat for ROS 2 Jazzy through Foxglove Bridge.

Build: `npm ci`, `npm run build`, `npx tsc --noEmit`.
Install locally: `npm run local-install`, then restart Foxglove.
Distribute: `npm run package`; teammates install the resulting `.foxe` file.

Use the layout and ROS gateway in [robot_station](../robot_station/README.md). The extension panel type is `robot-station-extension.UnderBot Controls`.

The controls start disabled and require a fresh gateway heartbeat. The supplied live gateway has hardware forwarding disabled. Camera actuation, audio and AI providers require backend adapters. The local demo is synthetic and does not run SLAM, Nav2, YOLO or physics.
