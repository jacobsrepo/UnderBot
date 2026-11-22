# Native Windows Gazebo

This environment runs Gazebo Harmonic on Windows, without WSL or Linux.
The local installation is `D:\Robotics\gazebo-harmonic`, with Pixi package
caches in `D:\Robotics\cache` and download staging in `D:\Robotics\downloads`.
The existing ROS station and Python/PyBullet environments are separate.

Gazebo documents Windows support as experimental:
https://gazebosim.org/docs/harmonic/install_windows/
Harmonic requires separate server and GUI processes on Windows.

`prepare.py` creates an ignored local world and URDF with absolute mesh paths
from the R09 Gazebo profile. It does not change the source model.
`run.ps1` launches the server and viewer, starting paused. The Play button
enables physics. Close the viewer to stop the server launched with it.
`run.ps1 -Headless -Iterations 1000` runs a finite physics check.

## Arm controls

`D:\Robotics\Start UnderBot Gazebo.cmd` opens the viewer and the **Underbot —
Gazebo Arm Controls** window. For an already running simulator, use
`D:\Robotics\UnderBot Gazebo Arm Controls.cmd` or `open-controls.ps1` here.

1. Click **Play** in the control panel.
2. Drag a left- or right-arm slider and release it. Targets are in degrees.
3. Compare the target with **Measured**, the angle reported by Gazebo.
4. **Pause** freezes physics; **Reset Arm Pose** sends zero targets to the ten
   arm/wrist joints (click Play to execute them). **Focus Robot** zooms the viewer.

Sliders use the URDF's joint limits, rounded inward to whole degrees. They do
not send commands on startup. Target updates replace pending values for the
same joint. The panel displays disconnected/paused/running state and uses the
isolated `underbot-r09-native` Gazebo partition, with no hardware or ROS output.
Grippers are available through **Move Gripper XYZ**; wheels are excluded. Closing the panel leaves the simulation and
its last joint targets in place; use Pause first if you want to freeze it.

`verify_controls.py` is an integration check against a running simulator: it
rejects invalid targets, commands the elbow, verifies measured motion and pause,
then restores the prior elbow angle and paused/running state. Latest results
are in `generated/control-verification.json`.

The model includes estimated arm controllers and differential-drive settings.
Importing it is not validation of contact stability, gripper mimic execution,
motor ratings, or physical accuracy. Sensors and ROS/Foxglove bridging are
not yet included in this launcher.

## Joint demonstrations

The arm panel now includes **Record Demo**, **Save Demo**, **Replay File**, and
**Stop Replay**. This is a demonstration collection tool, not a trained policy.

1. Click **Play**, position the arms, and let them settle.
2. Click **Record Demo**, then use **Move Gripper XYZ** for coordinated motion
   (or individual sliders for joint checks). Only commands sent
   from this panel are recorded; do not use another controller during recording.
3. Click **Save Demo**. Files are saved in `simulation/gazebo/demonstrations/`
   on D: and excluded from Git. Each timestamped JSONL file is flushed as it is
   written, so an interrupted session retains its collected data.
4. With physics running, click **Replay File** and select a saved file. Replay
   first commands the recorded initial arm pose and waits for it to settle,
   then sends recorded targets. It pauses physics on completion or failure.
5. **Stop Replay** cancels playback and requests a pause. A native command already
   in flight may finish first. Manual target changes are blocked during replay.

The version 2 JSONL format contains a header (joint limits, initial pose, radians),
observations (`positions`, held `targets`, available model `world_poses`), actions
(full `targets`, pre-command `positions` and `world_poses`, `observation_sim_time`),
and an end marker. Version 1 files are readable only if their joint inventory
matches; old ten-joint recordings do not include grippers and must be recorded
again for the twelve-target controller. `t`
is elapsed simulation time from the latest world-status message. Observations
are sampled by the panel approximately every 150 ms of wall time; they are not
camera observations or a fixed-rate training dataset. Action timestamps are
local successful publisher completion, not acknowledgements from the motor
controller. Measured motion is stored separately from the commanded target.

Replay validates the whole file before moving, rejects unfinished recordings,
and aborts on stale feedback, pause, clock reset, or failure to reach the initial
pose. Native CLI publishing adds latency, so replay timing is best effort. The
initial pose covers arm joints only: base pose, object state, controller state,
and velocities are not restored. Let the robot settle before recording. This
is suitable for slow arm demonstrations, not precision trajectory playback.
Other control panels or Gazebo clients can still interfere; use one operator.

For imitation learning, the next steps are choosing a task, adding the task's
observations, collecting varied demonstrations, and building a training/evaluation
pipeline. These recordings alone do not teach grasping or validate real hardware.

Tests: `..\pybullet\.venv\Scripts\python.exe -m unittest test_demonstrations -v`.
With Gazebo running, `verify_demonstrations.py` checks actual record/replay of a
small elbow movement, writes `generated/demonstration-verification.json`, and
leaves physics paused. It moves both arms to neutral before the test.

## Installation verification

Gazebo Sim 8.10.0 installed natively on Windows on 22 November 2026.
The R09 world loads, the viewer renders the robot and ground plane, and a
100-iteration headless run completes. This is an import/startup smoke test,
not a stability or driving acceptance test.

Known runtime limitations: the packaged DART backend lacks gripper mimic
constraints. The generated model now removes those constraints and drives the
two fingers with separate force-limited controllers sharing the same target.
This is software coupling, not a rigid mechanical constraint; contact can cause
different measured finger angles. The CLI reports a protobuf descriptor warning;
automatic console logging uses an invalid Windows timestamp path. The launcher
captures server output under `generated/` on D: instead. Small default Gazebo
settings may still be created in the Windows user profile on C:.

## Coordinated motion and pick-and-place preparation

**Move Gripper XYZ** opens controls for 5 mm position steps in robot-base axes
and open/close commands for both grippers. Inverse kinematics finds a bounded
five-joint solution; all twelve independent arm/finger targets are sent in one
`gz.msgs.Actuators` message on `/underbot/arm_targets`. The target ordering is
defined in `arm_model.py`. Generated controllers use `use_actuator_msg` and
`actuator_number`; individual `/underbot/{joint}/cmd_pos` topics are no longer
used by this launcher. See the upstream controller implementation:
https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/joint_position_controller/JointPositionController.cc

The solver controls position only, not orientation, and does not perform collision
avoidance. Jogging uses the previous target, so repeated clicks accumulate while
the arm catches up. This enables coordinated demonstrations but is still a slow,
discrete control interface. Do not describe its output as smooth teleoperation.

Open `Start UnderBot Pick Place.cmd` (or run `run.ps1 -PickPlace`) to load a
side table, a 25 x 25 x 40 mm / 20 g physical block, and
a green placement marker. Close an existing Gazebo viewer before launching
another world, since both use the same isolated partition. `verify_pick_place.py`
checks actual finger motion and attempts a physical lift/place with feedback
correction. It does not attach objects or train a model, and writes its outcome
to `generated/pick-place-verification.json`. A failed attempt is not a successful
expert demonstration. Training requires a validated task and varied successful
demonstrations first.

Run all local checks with:
`..\pybullet\.venv\Scripts\python.exe -m unittest discover -p "test_*.py" -v`.
