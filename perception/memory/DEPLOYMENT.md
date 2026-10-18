# Pi deployment verified 2026-09-17

Target: Raspberry Pi 5 Model B, 8 GB RAM, Ubuntu 24.04 ARM64, ROS 2 Jazzy.
Source deployed to /home/underbot/UnderBot/perception.

- Local PostgreSQL database initialized; credentials restricted under .private/.
- underbot-memory.service active and enabled for boot. Reboot itself was not tested.
- Base station tunnel uses loopback 55433 on Pi -> loopback55432 on Windows over SSH.
- Sam Jacob initially had one local reference. On 2026-09-19, nine additional
  user-provided photos were enrolled into the same person record (ten total).
  Both PC recognition and Pi galleries were verified at one person/ten samples.
  A live EMEET observation subsequently confirmed Sam Jacob; intermittent frame
  freshness gaps remain a separate pipeline issue. This is not an accuracy benchmark.
- Genuine tunnel interruption test passed: local gallery remained available and a
  marked synthetic observation queued. After reconnection it uploaded successfully
  (Pi pending count returned to zero). No live person observation was fabricated.
- Photo streamed through SSH into RAM, without saving a photo file on the Pi.
  YuNet/SFace matched the enrolled identity; YOLO detected person and tie; an empty
  gallery returned no identity. The test used the enrollment photo itself, so this
  is a deployment check, not independent face-recognition accuracy validation.
- Face extraction/matching took about 0.20 seconds in that test; the first YOLO
  detection including model initialization took about 3.9 seconds. These are not
  live-camera FPS measurements. Continuous RGB+pose+identity timing remains untested.
- ROS node/message construction and face model loading passed. CPU-only torch2.14.0
  and torchvision0.29.0 installed; unnecessary CUDA runtime packages removed.
- pip check passed. The tested ARM64 Python3.12 packages are listed in
  requirements-pi-tested.txt. Install CPU PyTorch first using the official CPU index.

The original photo stays on the user's external drive. Database data, passwords,
SSH keys and face references are ignored by Git. No new image/audio recording runs.

## Start after shutdown

Pi PostgreSQL and the memory synchronization service start at boot. On Windows run
D:\Robotics\Start UnderBot Base.cmd to start the local database and reconnecting
SSH tunnel. Windows automatic startup has not been configured. Sync retries while
Windows is off. Offline gallery expiry is seven days since last successful sync;
see README.md for event retention and loss bounds.

## When a USB camera is attached to the Pi

From /home/underbot/UnderBot/perception, list devices with:

    source /opt/ros/jazzy/setup.bash
    .venv/bin/python camera_node.py --list

Then run `bash memory/start_robot.sh 0`, replacing 0 with its actual device index.
This starts camera, YOLO and local identity matching. Ctrl+C releases the camera.
The Pi needs its own Foxglove bridge to display those topics on the Windows station;
the currently displayed Windows camera pipeline is a separate source.
A physical Pi camera stream and its Foxglove display are not yet validated.
