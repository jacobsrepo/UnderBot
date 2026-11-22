# Two-robot Foxglove simulation

The fleet demo loads two independent instances of the active
`models/r09/underbot_description/urdf/underbot.portable.urdf`,
with `robot_1/` and `robot_2/` link and joint names. Both move in the same `map`.
The existing single-robot demo remains available.

From the repository root in a sourced ROS environment:

```sh
python robot_station/start.py --demo --fleet-demo --port 8767
```

On this Windows workstation, `robot_station/start-fleet-live.ps1` starts the full
dashboard: fleet simulation, live EMEET camera, object/pose and enrolled-face
recognition, local recognition database, and existing Pi Qwen tunnel, all on
domain 75. It reuses running services and rejects a camera pipeline running on
another domain instead of opening the webcam twice. Microphone capture remains
operator-controlled. Run it with `powershell -ExecutionPolicy Bypass -File
robot_station/start-fleet-live.ps1`.

`robot_station/open-fleet.ps1` starts only the station, with AI and memory settings;
use the full launcher above when you also need camera/recognition services.
Connect Foxglove to
`ws://127.0.0.1:8767` and import `navigation/underbot-fleet-layout.json`.
Fleet mode uses ROS domain 75; the original demo uses 74.

The layout includes two topic-backed URDF layers and cyan/orange planned paths.
URDF layers use TF transforms. If setting up a view manually, add two URDF custom
layers sourced from `/navigation/robot_1/robot_description` and
`/navigation/robot_2/robot_description`, with an empty frame prefix and display
frame `map`. See [Foxglove's 3D panel documentation](https://docs.foxglove.dev/docs/visualization/panels/3d).

Use the existing chat panel:

- `run team demo` — get into position, cross paths, swap places, rendezvous,
  then return to each robot's original home. This is five coordinated stages.
- `swap places` — exchange the robots' current positions.
- `rendezvous` — meet at two separated positions in a nearby validated clear area.
- `both robots return home` — return to their startup poses.

The **Team mission** controls provide the same commands without typing. Mission
progress and each robot's moving/yielding/waiting state appear in the panel;
labels above the robots also show their current state. The coordinator validates
every stage before replacing an existing plan. Both robots must finish each stage
before the next starts, with a one-second pause between stages. Planning priority
alternates between stages; this does not guarantee fairness or completeness for
arbitrary traffic. Team missions have a 900-second simulation-time deadline.

An accepted individual goal cancels the team mission and parks the teammate;
an invalid replacement preserves the previous safe schedule. **Stop both** or
Cancel clears the entire mission, including future stages. Completed, cancelled,
and failed mission records remain visible in `/station/nav/status`. Chat receives
correlated stage-start and terminal events. A collision-guard stop is reported as
a mission failure. Switching windows while manual controls are unarmed does not
cancel an autonomous mission.

Individual commands remain available:

- `robot 1 go to 2, 3`
- `robot 2 go to 3, 2` (send while robot 1 is moving)
- `robot 1 go to robot_1_start`
- `robot 2 go to robot_2_start`
- `stop navigation` stops both robots and clears their goals.

Unqualified goals target robot 1. Any stop, including `robot 2 stop`, stops the
whole fleet so that stopping one robot cannot invalidate the other's reservation.
Manual control and Cancel also stop the fleet. Direct teleoperation, turns,
forward/reverse skills and saving waypoints are not enabled in fleet mode.
Only destinations that fit the footprint are listed; the original map-edge
`goal_a` is excluded because the robot would extend outside the known map.

The updated extension provides a robot selector for **Go to coordinates** and
shows both positions. Build/install it from `robot-station-extension` with
`npm.cmd run build` and `npm.cmd run local-install`, then reload the panel.
The explicit chat commands work with the previously installed extension too.
For click-to-publish goals, select `/station/nav/robot_1/goal` or
`/station/nav/robot_2/goal` and frame `map`. Fleet state is also available as JSON
on `/station/nav/status`, with correlated execution events on `/station/nav/events`.

To load two supplied URDF files (the same path may be supplied twice):

```sh
python robot_station/start.py --demo --fleet-demo --port 8767 --urdf first.urdf second.urdf
```

This version supports box, sphere and cylinder geometry. Mesh URDFs are rejected
explicitly. All joints stay at zero; it does not plan arm motion or robot
self-collision. A conservative enclosing circle is computed from all visual and
collision primitives in this fixed pose. The larger radius is used for both
robots, with an extra 10 cm of inter-robot separation. The bundled rover radius
is about 0.2502 m, giving about 0.6004 m minimum centre separation.

The planner inflates blocked/unknown cells further for the footprint. It plans
one robot first, then searches position/time states for the second, including
waiting and detours. It retries in the opposite priority order on failure.
Continuous relative-motion checks reject head-on swaps and crossing collisions;
completed and idle robots reserve their positions indefinitely. New goals replan
both active robots from their current positions. Invalid requests preserve the
previous safe schedule. Motion uses one simulation clock, frozen while planning,
and a runtime collision guard. Speed is at most 0.4 m/s; heading changes are
instantaneous and joints remain fixed.

Search is bounded to 500 time slots and 150,000 expanded states per priority
attempt. This prioritized method is neither complete nor globally optimal: some
solvable bottlenecks can be rejected. It is a static-map kinematic simulation,
not physical navigation, dynamics, live obstacle avoidance, or a safety controller.

Validation:

```sh
cd robot_station
python -m unittest test_fleet test_navigation -v
# Requires ROS, preferably ROS_DOMAIN_ID=75:
python -m unittest test_fleet_execution test_navigation_execution test_navigation_language test_gateway -v
```

Tests cover crossing paths, head-on swaps, idle robots, footprint inflation,
unreachable/overlapping goals, bounded search, distinct URDF frames, two-goal
execution on the bundled map, cancellation and preserving a plan after rejection.
The ROS-node tests execute the follower to completion and check separation each
tick. The full workstation dashboard was visually checked on 2026-11-05: both
URDF instances and live raw/annotated camera panels render, recognition reports
ready, Qwen inference succeeds, and the Problems panel is clear. The direct ROS
launcher sets `ROS_DISTRO=jazzy` so Foxglove recognizes ROS publishing schemas.
The `/odom` and `/imu/data` dashboard gauges describe simulated robot 1; both
robots additionally publish namespaced odometry.

The coordinated team demo was also run through the live gateway on 2026-11-05:
all five stages completed and both robots returned home. Minimum sampled
separation was 0.624 m against the required 0.600 m. All 80 station tests,
extension build, and TypeScript check passed. See `team-mission-verification.json`.
Repeat the live simulation check with
`python tools/diagnostics/check_fleet_mission_live.py` in a sourced ROS environment
with `ROS_DOMAIN_ID=75`. This diagnostic sends a real simulation mission request.
