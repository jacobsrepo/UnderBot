# R09 Python simulation

Python and PyBullet load the existing R09 URDF and all 45 visual meshes directly.
The base is fixed to the world for inspecting the arms, wheels and grippers.
The default headless run is a passive 0.05-second gravity smoke test. GUI mode
adds joint target sliders, using the source effort and velocity limits; the
caster joints remain passive. Both gripper followers have explicit 1:1 gear
constraints. Joint values and targets use radians.

The integrator runs at 24 kHz (100 physics steps per 240 Hz control interval)
to resolve the stiff combination of small finger inertias and source damping.
Playback may run slower than real time on slower computers. Source damping and
inertias are preserved; the smaller timestep prevents the numerical instability
seen with a single 1/240-second physics step.

## Install and run

Use Python 3.11 and an isolated environment. From this directory on Windows:

PyBullet 3.2.7 currently builds from source on Windows. Install the Visual Studio
C++ Build Tools and Windows SDK, open an **x64 Native Tools Command Prompt**, and
set `DISTUTILS_USE_SDK=1` before running the installation commands below. The
current workstation already has these build tools. Linux wheels do not require
this compiler setup.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe simulator.py
.venv\Scripts\python.exe simulator.py --gui
.venv\Scripts\python.exe -m unittest -v
```

If Python 3.11 is not installed, `uv venv --python 3.11 .venv` can provision it.
On Linux use `python3.11 -m venv .venv` and `.venv/bin/python` for the commands.
Close the viewer or press Ctrl+C in the terminal to exit. The GUI activates
position control; its sliders initially request zero. Continuous wheel sliders
cover one revolution for inspection, not vehicle driving.

On this workstation, `powershell -File run.ps1` opens the viewer using the
prepared environment; `powershell -File run.ps1 -Headless` runs the smoke test.

For a longer passive run: `python simulator.py --seconds 1`.
The generated JSON report is written to `generated/verification.json` (ignored
by Git); override the destination with `--report path.json`.

## Validation and boundaries

The import audit compares engine link/joint names, masses, COM offsets, full
inertia tensors (accounting for principal-axis rotation), joint types and
revolute limits with the URDF. Visual mesh paths are checked. The fixed base
intentionally has zero engine mass and inertia; the source mass is retained
in the report. Source total mass is 19.6010078 kg across 23 links and 22 joints.
Tests also check a one-second passive run, a stationary base, invalid target
rejection, and both grippers opening and closing with coupled followers.

This is a fixed-base model, not a mobile driving simulation. No ground plane,
self-collision, contact/grasping validation, sensors or ROS adapter is provided.
URDF collision shapes load, but self-collision is disabled. A 100 N m constraint
force ceiling is a numerical coupling setting, not a gripper hardware rating.
Existing source inertias, motor limits and geometry contain unmeasured estimates;
see `models/r09/underbot_description/docs/accuracy_and_physics.md`. Visual meshes
do not determine mass. The existing navigation/fleet demonstrations remain
separate from these dynamics.

The earlier MATLAB implementation is recoverable from Git history. Python
simulation is the maintained workflow; no MATLAB installation is required.

Reference: [PyBullet guide](https://github.com/bulletphysics/bullet3/blob/master/docs/pybullet_quickstart_guide/PyBulletQuickstartGuide.md.html).
