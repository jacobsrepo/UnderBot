# UnderBot R09 in MATLAB / Simscape Multibody

This is the first fixed-base import and passive simulation baseline. It uses
the consolidated R09 URDF and existing meshes without changing either.

## Verified on 2026-10-20

MATLAB R2026b successfully imported and assembled the model, then completed the
0.05-second passive gravity simulation. The independent parameter audit confirms
all 23 link inertias/COM offsets and all 22 joint types match the URDF, with all
revolute limits retained. All 45 visual meshes resolve in metres and add no
mass. See both JSON reports under `generated/` for the results and limitations.
This establishes a runnable import baseline, not a completed mobile robot model.

## Open in MATLAB

Set MATLAB's Current Folder to this directory, then run:

```matlab
open_underbot
```

The generated model is `generated/underbot_r09_fixed_base.slx`.
Use **Update Model** to assemble and view the robot in Multibody Explorer.
The base is attached to the world; this is a bench setup for inspecting arms
and joints, not a driving simulation.

To regenerate and verify from the repository's URDF:

```matlab
build_underbot
```

Requires MATLAB, Simulink, Simscape, and Simscape Multibody. Robotics System
Toolbox is not required. The initial verification uses R2026b.
Rebuilding replaces the generated model. Save any manually edited model under
a different name before rebuilding.

## Layout

- `build_underbot.m`: source audit, portable mesh setup, import, model update,
  and a 0.05-second passive simulation.
- `open_underbot.m`: adds the repository's mesh directory to the MATLAB path
  and opens the model.
- `check_import.py`: independently compares the exported block parameters with
  the original URDF using Python's standard library (`python check_import.py`).
- `generated/underbot_r09_fixed_base.slx`: generated model.
- `generated/verification.json`: source inventory and completed smoke-test results.
- `generated/imported_blocks.json`: imported block parameters for auditing.
- `generated/import_audit.json`: mass, inertia, COM, joint-limit comparisons and
  explicit importer limitations.
- `generated/underbot_r09_import.urdf`: derived URDF with mesh basenames;
  generated locally and resolved by the launcher.
- `generated/cache/`, `generated/codegen/`, and `build.log`: local build outputs.

The source remains `models/r09/underbot_description/urdf/underbot.portable.urdf`.
Its 23 links have an estimated total mass of 19.6010078 kg. Its 22 joints
include 4 fixed, 4 continuous, and 14 revolute joints. Two caster coordinates
are passive and two gripper joints are mimic followers in the source.
The camera optical frame and LiDAR scan frame have zero mass and zero inertia;
they are fixed coordinate frames. The audit permits these while requiring
positive mass and physically valid principal inertias for physical bodies.

## Scope and limitations

The short passive run checks that the imported system assembles and integrates.
It does not validate a controller, a payload rating, self-collision, gripper
contact, mobile-base stability, or hardware performance.

- The base is fixed. Mobile driving needs an appropriate base joint, wheel/ground
  contact, friction, and drive models.
- Visual meshes are used for appearance; the source collision geometry does not
  by itself establish active contact forces in Simscape.
- Source masses, inertias, caster geometry, servo effort caps, and joint ranges
  include unmeasured estimates. Positive physical inertia tensors do not prove
  those estimates match the real robot.
- The R09 base visual mesh has touching shells; it is not a unioned solid for
  automatic mass estimation. Explicit URDF inertias must remain authoritative.
- Motors, actuator saturation, sensors, and controllers must be added explicitly.
- **Gripper mimic coupling is not imported.** Both follower joints remain
  independent passive revolute joints. Add and verify their 1:1 coupling before
  using this baseline for grasping or load predictions. This raw import has 18
  independent rotational coordinates; the source intends 16 after coupling.

See the source package's `docs/accuracy_and_physics.md` for the measurement
register. The R09 package retains the R08 physical configuration and those
documents still use the R08 revision label.

Official references:
[smimport](https://www.mathworks.com/help/sm/ref/smimport.html) and
[URDF import](https://www.mathworks.com/help/sm/ug/urdf-import.html).
