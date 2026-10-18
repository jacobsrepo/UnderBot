# Underbot R09

Detailed model of the WR141E-based Underbot: **200 × 200 mm floors and frame**, **204 × 204 mm covered tower**, and **500 mm posts**. Two budget arms mount directly to the metal frame; matte-black front/side sheets surround clear polycarbonate floors and a rear service panel.

![Underbot R09 — actual model render](final_exports/Underbot_Final_R09/renders/Underbot_R09_hero.png)

## Open the final model

- [Complete R09 export folder and instructions](final_exports/Underbot_Final_R09/README.md).
- [Assembled STL](final_exports/Underbot_Final_R09/stl/Underbot_R09_assembled_mm.stl) — millimetres; 250 separate closed components.
- [Textured GLB](final_exports/Underbot_Final_R09/models/Underbot_R09_textured.glb) — metres, with embedded 2K PBR textures.
- [Editable Blender scene](final_exports/Underbot_Final_R09/models/Underbot_R09_studio.blend) — packed textures and studio lighting.
- [Portable URDF](underbot_description/urdf/underbot.portable.urdf), [ROS URDF](underbot_description/urdf/underbot.urdf), [modular Xacro](underbot_description/urdf/underbot.urdf.xacro) and [optional textured OBJ URDF](underbot_description/urdf/underbot.textured.urdf).
- [Offline joint viewer](underbot_description/viewer.html) — clone/download the repository, then open locally.
- [Dimensioned floor/frame plan](final_exports/Underbot_Final_R09/docs/floor_plan_R09.svg).

[Download the repository ZIP](https://github.com/gautamsajeen/UnderBot-Personal/archive/refs/heads/main.zip), or clone the repository. Keep each URDF with its package meshes. STL stores geometry only; GLB and Blender carry the full textured appearance. The complete export bundle repeats the ROS package so it can be copied independently. The top-level package is the same current model for convenient ROS workspace use. Older downloads remain historical versions.

## Verification

An independent agent checked the actual exported triangles: **4,730 checks passed**, including the 200/204 mm dimensions, part transforms, unit conversions and closed component surfaces. The model has **250 components, 223,360 triangles, 11 materials and 18 embedded 2048 × 2048 GLB texture images**. The authoring texture library contains 24 maps.

The physical model retains 23 links and 22 joints: four fixed joints, 14 commanded coordinates, two passive caster coordinates and two gripper mimic followers. Four fixed-link merges leave 19 bodies. Joint origins, axes, limits, collision shapes and estimated mass/inertia match the tested physical configuration. Independent PyBullet imports and joint transforms, MuJoCo motion checks, Xacro checks and offline-viewer checks pass. [Independent dimensions](final_exports/Underbot_Final_R09/validation/dimensional_audit.md), [texture audit](final_exports/Underbot_Final_R09/validation/textured_export_audit.md), [final delivery report](final_exports/Underbot_Final_R09/validation/final_delivery.json).

The bare Kinect layout, arm dimensions, actuator ratings and installed mass budget remain unmeasured assumptions. WR141E/GB70 surface contours approximate published envelopes. Estimated total mass is 19.601 kg. This is not factory CAD, fabrication certification or a payload rating. Native Gazebo, Isaac Sim/Lab, RViz2 and FreeCAD execution has not been performed. The STL assembly is a collection of closed parts with intentional interfaces, not a Boolean-unioned printing solid.

## Simulation

Place the top-level `underbot_description` directory in a ROS 2 workspace's `src` folder:

```sh
colcon build --packages-select underbot_description --symlink-install
source install/setup.bash
ros2 launch underbot_description display.launch.py
```

Follow the [simulator import guide](underbot_description/docs/simulation_import.md) and [accuracy register](underbot_description/docs/accuracy_and_physics.md). The historical root URDF files point to this same physical model and current visual meshes. Rebuild instructions for R09 detail and materials are in the [complete export README](final_exports/Underbot_Final_R09/README.md#validation-and-reproduction).
