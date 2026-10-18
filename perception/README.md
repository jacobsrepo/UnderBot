# EMEET RGB perception (ROS 2 Jazzy)

Live PC webcam capture, general object detection and human pose estimation.
The selected camera is `HD Webcam eMeet C960`. Inference runs locally using
Ultralytics YOLO26n (objects) and YOLO26n-pose (17 human keypoints).
The pose model is not a general object-pose model. No camera video is recorded.

## Windows quick start

Install Pixi and Foxglove separately. From this folder:

```powershell
pixi run cameras
pixi run start
```

`start` opens the uniquely matching EMEET camera and runs both models on CPU.
Close competing webcam apps first. First launch downloads dependencies and model
weights to the ignored `models/` directory. Press Ctrl+C in the terminal to stop
both programs and release the camera. Keep only one capture process running.
For a background run, use `pixi run stop` from another terminal in this folder.

For another camera or inference device:

```powershell
pixi run python start.py --camera-index 0
pixi run python start.py --camera-only
pixi run python yolo_node.py --device cpu --imgsz 416 --max-fps 5
```

The separate `yolo_node.py` command is for use alongside a camera-only publisher;
do not start it a second time alongside the full `start` pipeline. CUDA inference
is optional and requires a separately compatible PyTorch/driver/GPU combination.
The checked-in lockfile covers the tested native Windows CPU environment.

## Foxglove connection and your layout

Start the existing station demo in a second terminal if it is not already running:

```powershell
cd ../robot_station
pixi run demo
```

Connect Foxglove to `ws://127.0.0.1:8766`. Both the station demo and perception use
ROS domain 74 with localhost discovery. The bridge's existing camera/perception
allowlists already admit the new topics; no bridge config change is required.

To keep your current dashboard, select these topics in its two Image panels:

- Raw: `/camera/emeet/image/compressed`
- Annotated: `/perception/emeet/annotated/compressed`

Alternatively, run `pixi run layout` in this folder and import the generated
`UnderBot EMEET Live.json`. The template preserves the panel arrangement and URDF,
selects the real camera and microphone topics, follows the manual location marker,
and uses the second gauge for camera-to-result latency in milliseconds.
The unused extra Teleop panel has been removed. Generated absolute URDF paths
are ignored by Git; each teammate generates their own layout.

Camera and microphone streams are real. Room map, path, odometry, IMU and robot
motion remain synthetic. The geographic Pi marker is manually configured, not GPS.
Large frame labels and manual URDF transforms are display settings, not calibration.

## Headset microphone

Start separately (camera startup does not enable the microphone):

```powershell
pixi run microphones
pixi run audio
# In another terminal to release the microphone:
pixi run audio-stop
```

Default input is the uniquely matching Plantronics microphone via Windows WASAPI.
Use `pixi run python audio_node.py --device-index N` for another listed input.
Run only one microphone publisher at a time. Capture is mono PCM signed 16-bit
at the input device's default sample rate (tested: 48000 Hz, 20 ms packets).
No audio files are recorded, no transcription is performed, and no AI receives it.
The Audio panel selects `/station/audio` (`foxglove_msgs/msg/RawAudio`) and starts
muted. Unmute to listen through headphones. **Panel mute only stops playback**;
`audio-stop` or Ctrl+C stops capture. `/station/audio_status` reports source,
packet count, RMS level and dropped/overflow counts. Comms buttons remain placeholders.

The bridge environment also needs `ros-jazzy-foxglove-msgs` (included in the station
manifest). Later, install rclpy, foxglove_msgs, sounddevice/PortAudio and NumPy on
the Pi, choose its microphone, and run this node with `--network --domain N` using
your configured ROS network. Stop the PC publisher first; keep the same topic and
connect Foxglove to the Pi bridge. Pi audio capture/networking has not been tested.
This is microphone monitoring, not two-way voice communication.

## Manual geographic marker and latency gauge

Create ignored `location.local.json` with your own decimal-degree `latitude` and
`longitude`. Camera startup launches the manual publisher if this file exists;
`pixi run location` can launch it separately. Do not run both copies.
The Map panel follows `/station/manual_location` and explicitly labels it MANUAL.
The NavSatFix representation is for display only: it is not a measured GPS fix
and must not be fed into navigation sensor fusion. `/station/location_status`
reports `live_tracking: false`. The local address/coordinates are not in Git.

The second gauge uses `/perception/emeet/latency_ms.data` (Float32), showing age
from camera capture to inference result publication. It excludes network/render
latency, and updates only when a fresh result is published.

See [recognition roadmap](RECOGNITION_ROADMAP.md) for people, equipment and packaging.

## Topic contract

| Topic | Type | Contents |
| --- | --- | --- |
| `/camera/emeet/image/compressed` | `sensor_msgs/msg/CompressedImage` | Unannotated JPEG, actual captured resolution, host capture timestamp |
| `/camera/emeet/status` | `std_msgs/msg/String` | JSON camera name, capture health, frame count, average rate |
| `/perception/emeet/annotated/compressed` | `sensor_msgs/msg/CompressedImage` | Same frame with object boxes, human skeletons and inference timing |
| `/perception/emeet/objects` | `std_msgs/msg/String` | JSON class IDs, labels, confidence and pixel `xyxy` boxes |
| `/perception/emeet/poses` | `std_msgs/msg/String` | JSON person boxes and named keypoints with pixel x/y and confidence |
| `/perception/emeet/status` | `std_msgs/msg/String` | JSON inference state, timing, processed frames and detection counts |

Result messages have `schema_version: 1`, original `header`, `image_width`,
`image_height`, `coordinates: pixels_top_left_origin`, model name and inference
latency. Annotated images and both result messages retain the camera timestamp
and `emeet_optical_frame`. IDs are class IDs, not persistent tracked identities.
Low-confidence keypoints can be zero/missing; consumers must check confidence.
No depth, distances, 3D positions or physical object dimensions are inferred.

Capture and inference are separate ROS nodes. Camera publication is independent
of model speed; the inference subscriber keeps only recent input, drops frames
over two seconds old, and publishes empty result arrays when nothing is detected.
Both models process the same unmodified image, then annotations are composed.

## Verification

With the pipeline running, `pixi run check` checks real ROS JPEG decoding, result
messages and shared timestamps for 20 seconds without saving frames. The first
local check received 299 raw images and 51 matched image/object/pose sets in
20 seconds (about 15 fps raw and 2.5 fps inference). Rates vary with CPU load and
scene. A person need not be present; empty keypoint results are valid.

## Later robot deployment

The Python nodes can run in a sourced Linux Jazzy environment with OpenCV,
Ultralytics/PyTorch and cv2-enumerate-cameras installed. Linux uses V4L2 camera
capture. The Windows Pixi lock is not a Pi environment and Pi performance has not
been validated. Before deployment, configure ROS discovery/networking for the
robot instead of this test's localhost-only domain.

Add depth-camera and LiDAR drivers as separate nodes. Calibrate intrinsics and
camera/LiDAR-to-body transforms, publish CameraInfo and synchronized depth/scan
streams, then implement fusion and navigation consumers. Add camera mounting,
optical-frame transforms and actual joint-state feedback to the robot model.
Keep hardware actuation separate from the perception nodes.

References: [Ultralytics pose](https://docs.ultralytics.com/tasks/pose/),
[object detection](https://docs.ultralytics.com/tasks/detect/),
[Python prediction API](https://docs.ultralytics.com/usage/python/).

## PostgreSQL memory and identities

See [memory setup](memory/README.md) for the implemented local/base PostgreSQL stores, opt-in face enrollment, synchronization, offline limits and Pi deployment. This supersedes the earlier roadmap's not-yet-implemented identity component; enrollment and Pi validation remain separate steps.

## Restore the Windows dashboard after a restart

Run D:\Robotics\Start UnderBot EMEET Live.cmd to start the base database/tunnel, local demo bridge on port8766, camera/recognition, and headset mic, then open Foxglove. Camera/model warm-up can take a little time. The checked-in start_live.ps1 supports omitting -Microphone to leave audio capture off. The existing Start UnderBot Base.cmd starts only database/tunnel services; it does not start Foxglove's bridge or sensors. The launcher uses this PC's installed D-drive software paths.
