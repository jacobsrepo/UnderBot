# Underbot WR141E — R08, 200 mm tower

The tower frame and each floor blank are now **200 × 200 mm**. Four 20 × 20 × 500 mm posts surround a 160 × 160 mm clear opening. The original sixteen 200 mm rails are cut to 160 mm. Each 3 mm clear polycarbonate floor has 20 mm corner reliefs to clear the posts and rests on the perimeter rails. Flat 2 mm matte-black plastic front/side panels attach outside the frame; the rear service panel remains clear. The covered tower is **204 × 204 mm**, as selected by the user. Hinges, fasteners and the directly mounted arms project locally beyond the nominal tower body.

The full Kinect casing has been removed from the model as requested. Internal PCB, heat-spreader and optical-module geometry is an **unmeasured packaging reservation**, with a 156 mm-wide collision envelope and open front aperture. Its shapes, mounts and optical datum need replacement/calibration after the real electronics are arranged. The previous 0.97 kg camera allocation is retained conservatively until the installed bare assembly is weighed; it is not a measured bare-Kinect mass.

The GB70 is upright with its 222 mm length vertical. Floor-ring bottoms are 205,480,555 and 685 mm above ground. This accommodates the battery below the second level and compute/cooling below the sensor. Tower width/depth changed; the 500 mm post length and stock mower envelope remain.

## Files to use

| File | Purpose |
|---|---|
| `urdf/underbot.portable.urdf` | Direct simulator import with relative mesh paths |
| `urdf/underbot.urdf` | ROS package mesh paths |
| `urdf/underbot.urdf.xacro` | Modular source entry point |
| `urdf/underbot.gazebo.urdf` | Optional Gazebo controller/surface profile |
| `viewer.html` | Offline joint and geometry inspector |
| `docs/floor_plan_R08.svg` | Dimensioned 200 mm floor/frame plan |
| `config/model_parameters.json` | Dimensions and evidence classification |
| `config/actuation.json` | Commanded, passive and mimic joints |
| `cad/build_underbot.FCMacro` | FreeCAD native-solid reconstruction source |
| `validation/` | Current authoring, static, import and dynamics evidence |

Keep the whole package together; copying a URDF alone loses its meshes. Visual STL vertices are in metres, with mesh scale 1 1 1. URDF assigns colours/transparency; importer appearance may differ. Geometry is a dimensioned assembly proposal, not a fabrication-qualified or measured digital twin.

## ROS 2 / RViz2

Place this folder in a ROS 2 workspace's `src` directory. In a sourced Linux ROS 2 shell:

```sh
colcon build --packages-select underbot_description --symlink-install
source install/setup.bash
ros2 launch underbot_description display.launch.py
```

Joint sliders inspect transforms rather than simulate force. For simulator feedback:

```sh
ros2 launch underbot_description display.launch.py publish_joint_states:=false use_sim_time:=true joint_states_topic:=/joint_states
```

The simulator supplies clock and joint feedback. [Import guidance](docs/simulation_import.md) covers Gazebo, Isaac Sim/Lab and Foxglove, including version-dependent mimic handling.

## Physics and verification scope

The model has 23 links and 22 joints: 4 fixed, 4 continuous and 14 arm/jaw revolute joints. Two jaw coordinates are mimic followers, leaving 14 commanded joints and 2 passive caster coordinates. The root is mobile, without a world attachment. Fixed-link merging leaves 19 bodies. Body axes are X forward,Y left,Z up; camera optical axes are X right,Y down,Z forward. Both rear wheel axes are+Y, so equal positive velocities drive forward. Caster swivel/roll are unactuated.

Estimated mass is **19.6010078 kg**. Massive links have explicit mass, COM and valid tensors; fixed shape-free sensor frames explicitly have zero mass/tensor. The stock 9.1 kg mower baseline is split among chassis, rear wheels and caster; the added NOCO is separate. Arm dimensions, installed masses, actuator ratings and bare-camera packaging remain estimates. [Accuracy register](docs/accuracy_and_physics.md) and [static review](docs/physics_review.md) describe their practical limits. No payload rating is established.

Independent authoring checks cover dimensions, STL resources/topology, joint bases, mirrored FK, inertias and sampled clearances. MuJoCo imports the actual portable URDF with a mobile-root/ground/control adapter; PyBullet separately imports/renders and compares nonzero FK. Reports identify actual settings and source hashes. ROS/RViz2, Gazebo, Isaac Sim/Lab and FreeCAD native execution was unavailable. The FreeCAD macro is supplied as syntax-checked source; no native FCStd/STEP export is claimed.

## Rebuild after measurements

Update source parameters and component definitions, then run Python 3 with NumPy:

```sh
python scripts/generate_model.py
python scripts/prepare_simulation.py
python scripts/build_viewer.py
python scripts/validate_model.py --report validation/authoring_checks.json
python scripts/validate_model.py urdf/underbot.portable.urdf --report validation/portable_checks.json
```

Optional checks: `check_sources.py` needs Xacro; `physics_smoke_test.py` needs MuJoCo/NumPy; `static_physics_audit.py` needs NumPy. Regenerate and repeat checks after changing geometry, joints, mass or controllers. See [FreeCAD instructions](cad/README.md) for reconstruction and unit conversion.
