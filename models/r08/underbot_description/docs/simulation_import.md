# Underbot R08 simulator import and validation

Official documentation checked 11 October 2026. This guide accompanies the WR141E-based R08 model with **200 × 200 mm frame and floors**. The outside 2 mm panels give a **204 × 204 mm covered body**, excluding projecting hinges and arm mounts. The clear opening between 20 mm posts is 160 × 160 mm, and the posts are 500 mm long. The installed ROS 2, Gazebo, Isaac Sim and Isaac Lab versions have not been supplied. Use documentation for the installed release; `latest` and `main` links are moving targets. Native RViz2, Gazebo, Isaac Sim and Isaac Lab execution is not claimed here. See the delivered validation reports for checks actually run.

## Model and file selection

The root is `base_link`, at the ground datum, with no joint to `world`. Body axes are X forward, Y left, Z up; camera optical axes are Z forward, X right, Y down. Keep the entire package together so meshes remain resolvable.

| File | Purpose |
|---|---|
| `urdf/underbot.urdf` | Expanded ROS description using `package://underbot_description/` mesh paths |
| `urdf/underbot.portable.urdf` | Expanded core for direct import, using relative mesh paths |
| `urdf/underbot.urdf.xacro` | Modular authoring entry point; expand before generic import |
| `urdf/underbot.gazebo.urdf` | Optional Gazebo wrapper with simulator-specific systems; regenerate after changing the core |

R08 has 23 links and 22 joints: 4 fixed, 4 continuous and 14 arm/jaw revolute joints. Two jaw joints are mimic followers. There are 16 independent joint coordinates: **14 actuated commands and 2 passive caster coordinates**. A floating base additionally has six spatial degrees of freedom in 3D physics. Merging all four fixed joints leaves 19 bodies. Body counts change when an importer merges fixed links; there is no universal required fixed-body quota.

The Kinect V2 external case is removed in R08. The camera geometry is an **uncalibrated bare-electronics reservation**, not a measurement of the disassembled sensor. The 249 mm cased Kinect is not represented as fitting inside this tower. Measure the retained electronics, optical module, cooling and cables after disassembly, then update geometry, mass/inertia and the optical-frame transform. No camera image, depth stream, field of view or intrinsic calibration is supplied by the reservation. The NOCO battery is installed upright with its 222 mm body dimension vertical; the shelf arrangement follows that packaging assumption.

The caster has a passive swivel joint and a passive rolling joint. Do not add drives to `caster_swivel_joint` or `caster_wheel_joint`. It replaces the previous revision's sliding sphere. Caster dimensions, bearing resistance, wheel geometry, arm pivots, installed masses and motor limits include unmeasured estimates. The rear service door is fixed closed.

## ROS 2 / RViz2

From a sourced ROS 2 workspace containing this package:

```sh
colcon build --packages-select underbot_description --symlink-install
source install/setup.bash
ros2 launch underbot_description display.launch.py
```

The launch reads expanded URDF or processes a `.xacro` entry point, starts the transform publisher and one joint-state publisher, and opens RViz2. Both GUI and headless joint-state publishers honor URDF mimic tags. The GUI can display passive caster sliders for kinematic inspection; those sliders do not make the caster actuated in physics. [Joint State Publisher documentation](https://github.com/ros/joint_state_publisher/blob/ros2/joint_state_publisher/README.md).

For simulator feedback:

```sh
ros2 launch underbot_description display.launch.py publish_joint_states:=false use_sim_time:=true joint_states_topic:=/joint_states
```

Publish `/clock` and joint feedback from the simulator. Include the two caster states for their transforms. The transform publisher converts joint feedback to `/tf` and publishes fixed transforms through `/tf_static`; do not run a competing slider publisher. RViz defaults to `base_link` to inspect the robot; select `odom` in RViz only when an odometry-to-base transform is available. [Robot State Publisher documentation](https://github.com/ros/robot_state_publisher/blob/rolling/README.md).

Use `gui:=false` for default joint states without sliders, or `rviz:=false` to omit RViz. Boolean launch arguments accept `true` or `false`. Joint sliders validate transforms and limits, not gravity or contact.

## Gazebo Harmonic / Ionic

Use expanded URDF. Gazebo's create service converts it through libsdformat. A minimal direct import is below; substitute the absolute path and actual world service name. The initial 2 mm elevation provides settling clearance above the ground datum. [Official Harmonic URDF spawn tutorial](https://gazebosim.org/docs/harmonic/spawn_urdf/).

```sh
gz sim empty.sdf
gz service -s /world/empty/create --reqtype gz.msgs.EntityFactory --reptype gz.msgs.Boolean --timeout 5000 --req 'sdf_filename: "/absolute/path/underbot_description/urdf/underbot.portable.urdf", name: "underbot", pose: {position: {z: 0.002}}'
```

The portable core supplies geometry, inertia and joints without actuator systems. The unsupported arms respond passively to gravity. For the optional controlled wrapper, run `python scripts/prepare_simulation.py`, start `gz sim config/underbot_empty.sdf`, and spawn `urdf/underbot.gazebo.urdf` through `/world/underbot_world/create`. If relative meshes fail to resolve, regenerate with `--absolute-meshes`; that result is specific to the local machine.

The generated wrapper uses differential drive for the two rear drive wheels, position controllers for the twelve independent arm/gripper leaders, and joint-state publication. Zero arm command means the authored folded pose. Caster joints remain passive. Wheel dimensions are derived from the core model; PID gains and contact coefficients remain proposed settings. Velocity-controlled drive wheels approximate ideal drives rather than measured motors. Choose either the standalone systems or a `gz_ros2_control` integration, so two controllers do not command the same joints. [Harmonic DiffDrive tutorial](https://gazebosim.org/docs/harmonic/moving_robot/), [Ionic joint controller reference](https://gazebosim.org/api/sim/9/jointcontrollers.html).

```sh
gz topic -t /underbot/cmd_vel -m gz.msgs.Twist -p 'linear: {x: 0.05}, angular: {z: 0.0}'
gz topic -t /underbot/left_elbow_joint/cmd_pos -m gz.msgs.Double -p 'data: 0.1'
```

Keep commands within the URDF limits and the generated controller caps. Send an explicit zero velocity command to stop. The standalone plugin does not add a deadman mechanism. Its initial disabled self-collision setting does not establish arm-to-tower or arm-to-arm collision safety; inspect adjacent overlaps before enabling useful collision pairs. Retain caster contact friction for rolling and steering; do not reuse the old low-friction sliding-ball setting.

`config/gazebo_bridge.example.yaml` optionally bridges clock, joint states, velocity commands, odometry and odometry TF to ROS 2. Launch the RViz display with sliders disabled and use one odometry-TF publisher. The alternative ROS controller YAML needs a matching hardware/simulator interface; it is not loaded by the display launch.

Fixed-link reduction combines mass, centre of mass and inertia into the retained parent. Keep decorative parts within fixed assemblies; use `preserveFixedJoint` selectively only when a separate physical body is needed, with valid mass/inertia. Inspect `gz sdf -p urdf/underbot.gazebo.urdf` to review conversion. [SDFormat URDF extensions](https://sdformat.org/tutorials/specification/sdformat_urdf_extensions/1.6/).

libsdformat 14.1 introduced URDF mimic parsing. Parsing a mimic relation does not prove its execution by the installed physics backend. Inspect converted jaw constraints and test both fingers under load. If mimic enforcement is unavailable, implement a version-specific coupled constraint/controller and exclude the follower from independent actuation; document that adaptation. [Official sdformat release notes](https://gazebosim.org/libs/sdformat/).

## Isaac Sim: choose the installed-version path

Import the expanded core, retain explicit collision geometry and inspect the resulting USD, including articulation root, units, axes, effort limits and inertial values. Keep the base mobile. Turn off cylinder-to-capsule substitution if offered, so wheel contact geometry retains the authored radius. Wheel drives need velocity targets; arm/gripper leaders need position targets for first commissioning; both caster joints need no drive. Avoid applying a global position drive to every joint.

| Importer documentation | Base and gripper settings |
|---|---|
| [Isaac Sim 5.1.0](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/importer_exporter/ext_isaacsim_asset_importer_urdf.html) | Select Moveable base. Leave Ignore Mimic unchecked so the follower gets the PhysX mimic relation. Disable Replace Cylinders with Capsules for wheel contact fidelity. |
| [Current `latest` importer](https://docs.isaacsim.omniverse.nvidia.com/latest/importer_exporter/ext_isaacsim_asset_importer_urdf.html) | Select Mobile base and Mobile Manipulators robot type. This documentation authors mimic relations through `NewtonMimicAPI`; its schema/runtime differs from the older PhysX path. |

Read the selected release's import log and verify the follower relationship. Package mappings can resolve the ROS version; the portable core avoids ROS package lookup. Do not import the Gazebo wrapper as the Isaac source. Source mass/inertia should govern; do not overwrite them with an automatic density estimate. Validate adjacent collision filtering before turning on full self-collision. Sensors and their ROS bridges need separate configuration; electronics reservation meshes and frame transforms produce no observations. Configure a simulated camera only after choosing and recording calibrated optical parameters.

## Isaac Lab

Use a USD validated with a mutually supported Isaac Sim/Lab release, or the installed Lab repository's `scripts/tools/convert_urdf.py`. Inspect `--help` first. The documented converter supports `--merge-joints`; omit `--fix-base` for this mobile robot. [Official asset import guide](https://isaac-sim.github.io/IsaacLab/main/source/how-to/import_new_asset.html).

```bat
isaaclab.bat -p scripts\tools\convert_urdf.py C:\path\underbot_description\urdf\underbot.portable.urdf C:\path\underbot.usd --merge-joints
```

Query joint and body names after conversion. Define actuators for the fourteen commanded joints only, preserve mimic coupling, and leave the two caster joints passive. Training additionally needs reset poses, observations, action scaling, contacts, rewards and termination rules. This package supplies an asset rather than a finished Lab task. `main` documentation still describes PhysX options while Isaac Sim `latest` describes Newton schemas; check installed-version compatibility instead of mixing these examples. Global importer stiffness/damping options are not a motor calibration.

## Foxglove

Load expanded URDF in the 3D panel and use TF control for normal ROS feedback. Desktop package lookup or an asset-fetching connection such as Foxglove Bridge resolves `package://` assets; desktop local-file loading supports absolute file paths. Keep the package directory intact. Joint states control is also available, but each message must contain every joint required by that mode; partial updates are not merged. Visual/collision display modes allow inspection of the distinct geometry. Foxglove visualizes transforms rather than simulating physics. [Official 3D panel documentation](https://docs.foxglove.dev/docs/visualization/panels/3d).

## Installed-simulator acceptance checks

1. Verify the imported scale, wheel radius/separation, ground clearance, root mobility and optical frame orientation.
2. Compare mass, centre of mass and principal inertia values before/after fixed-link merging. Do not double-count battery, frame or sensor masses.
3. Settle on the two rear drive wheels and front caster, then check caster swivel and rolling freedom. The support triangle changes with caster swivel; no hidden rear support is added.
4. Command equal positive drive-wheel velocities, then opposite velocities. Confirm forward and positive-yaw signs and the expected travel/turn rate.
5. Move each arm joint separately, then combined poses; inspect tower, opposite-arm and ground clearance. Verify leader/follower jaw motion and grasp contact.
6. Check estimated effort, velocity, damping, friction and gains against actual hardware. No rated payload is established by this model.
7. Exercise collision pairs, contact stability and centre-of-mass projection under extension, payload and acceleration.
8. Measure the bare Kinect installation and calibrate its optical frame before adding camera/depth simulation. Add calibrated LiDAR simulation separately, and record exact application/backend versions and import settings.

These checks describe required application validation. Passing an independent numerical smoke test does not establish native Gazebo, Isaac or ROS compatibility, or measure the physical WR141E assembly.
