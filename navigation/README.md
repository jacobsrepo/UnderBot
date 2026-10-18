# UnderBot navigation demonstration â€” 2026-10-06

Foxglove connection: ws://127.0.0.1:8766. Imported layout:
underbot-navigation-layout.json. The previous UnderBot EMEET Live layout remains
available in Foxglove. VS Code/Codex, camera capture, PostgreSQL and Qwen were not
stopped. Only the station simulation/bridge and Foxglove were refreshed.

The map is a 40 Ã— 40 metre crop from Autoware's public sample point-cloud map.
Source: https://docs.autoware.org/main/demos/planning-sim/
Download: https://autoware-files.s3.us-west-2.amazonaws.com/maps/demos/sample-map-planning.zip
SHA256 matches the upstream published value:
5536fce7bb8db7688fdf94ec004118b898637ad0d5b6175108b10989dd6e93b9.
The displayed cloud has 39,581 points. The robot position, IMU and odometry are
simulated; this is not a map or localization of the user's actual room.

## Use in the UnderBot chat panel

- `go to goal_a` â€” plan and follow a route to the named sample goal.
- `go to start` â€” route back to the sample starting location.
- `go to 2, 3` â€” use map coordinates in metres; occupied/unknown goals fail.
- `go forward 1 metre` â€” request a checked straight segment, maximum 5 m.
- `go backward 0.5 metre` â€” checked reverse segment, without turning around.
- `spin 360 degrees` â€” full in-place rotation; default direction is left.
- `turn right 90 degrees` / `turn left` â€” specified turn / default 90Â°.
- `save waypoint desk at 2, 3` / `save waypoint desk here` â€” save a custom
  destination in known free space. Names use lowercase letters, numbers and
  underscores, beginning with a letter. Built-in goals cannot be replaced.
- `go to desk` / `list waypoints` â€” navigate to / inspect saved destinations.
- `turn right then go forward 0.5 metre then go backward 0.5 metre then turn left`
  â€” ordered sequence, maximum eight steps. Each step is checked before running;
  rejection or cancellation drops all remaining steps.
- `stop navigation` â€” stop the simulation. Manual movement requests also cancel
  its autonomous route.

Explicit phrases use navigation_core.py. Other movement requests use the Pi's
Qwen model through navigation_language.py, with Ollama JSON-schema output and
independent Python validation. Qwen translates language into supported skills;
A* still calculates the path on the PC. This is a bounded language interface,
not arbitrary tools or code execution. Destinations must be saved waypoint names
explicitly mentioned in the request. No person/object location is inferred.
Polite prefixes such as "can you please" are accepted for these supported skills.
Distances require units and are limited to (0,5] metres per step; rotations are
limited to (0,360] degrees. A real camera does not rotate with the simulated base.

Foxglove now includes X/Y inputs, Go to coordinates, Save at X/Y, Spin 360Â° and
Cancel navigation controls. The yellow arrow above the cyan robot shows heading;
status reports heading, accumulated rotation progress and remaining queued steps.
Custom waypoints persist in the installed navigation-data/custom_waypoints.json.
The Cancel navigation button uses the direct simulation velocity topic, so it
does not wait for Qwen or a pending chat response. All navigation still runs on
the PC; Qwen inference continues on the Pi.

## Varied wording and execution feedback

- `Make one full clockwise revolution` â€” Qwen translates to turn right 360Â°.
- `Back up fifty centimetres` â€” Qwen translates to reverse 0.5 m.
- `Turn around and return to start` â€” Qwen proposes two ordered actions.
- `Move forward` â€” asks for distance; does not execute an invented amount.
- `Take me to the chair` â€” asks for a saved destination; no chair position exists.

Chat first displays the interpreted simulation plan. The executor then publishes
correlated started/completed/rejected/cancelled/timed-out events, which appear
in chat even after the initial reply. Physical execution remains disabled.
The small 1.5B model can misinterpret wording; this is not reliable unrestricted
language understanding. The displayed plan is its interpretation. For precision,
use explicit commands or coordinate controls. Clarifications are independent
requests: respond with a complete command such as `go forward 1 metre`, rather
than only `one`. No conversational pronoun or "there" resolution is implemented.

Cancel increments the gateway command generation. A model result received after
manual control, Cancel or Stop is discarded. Stop bypasses a busy AI request.
The executor enforces 300 seconds per step and 900 seconds per task. Model calls
have a 90-second network timeout; tested warm-model replies took roughly 7â€“12 s.
No new model was downloaded and no physical LiDAR is required for this demo.
Structured output reference: https://docs.ollama.com/capabilities/structured-outputs

Topics: /navigation/pointcloud, /navigation/robot, /map,
/navigation/costmap, /plan, /navigation/goal, /odom, /station/nav/status.
Foxglove's 3D publish tool can publish geometry_msgs/msg/PoseStamped in frame
map on /station/nav/goal; the bridge allows this simulation goal topic. Chat
commands and ROS goal publication were tested; interactive click-to-publish
configuration is not separately validated.

## What this implementation demonstrates

Eight-neighbour A* searches only known free cells, using diagonal costs and
an octile heuristic. Diagonals cannot cut between touching blocked/unknown cells.
Clear start-to-goal segments are used directly. Otherwise, cell-based routes
are simplified with collision-checked line-of-sight shortcuts. Each segment
uses grid traversal rather than sparse point sampling, including corner checks.
The route retains the exact requested coordinates; it no longer snaps the goal
to a cell centre. The path follower stops within 0.02 m and aligns its heading
before translating. Direct open-space routes are Euclidean shortest paths;
obstacle detours are not guaranteed globally optimal in continuous space.
The experimental grid has
0.2 m resolution, a flat-ground candidate band and 0.4 m inflation around
height-selected obstacles. A simple simulated controller follows the route,
checks its next centre position and stops if it is blocked. It is a static-map
demonstration with a simplified kinematic model, not a Gazebo dynamics model,
SLAM/localization system, Nav2 installation or validated safety controller.
Ground filtering ignores slope, curbs, overhangs, drop-offs and dynamic obstacles
outside its chosen height band; footprint/thermal/hardware qualification is not
provided. It must not control the real T12 base.

## Verified

57 unit tests passed in the installed ROS environment. check_navigation_ros.py
originally verified a forward displacement greater than 0.75 m and the former
195-point four-neighbour A* route; it now checks for a valid simplified route,
stopping, rejection of a goal at (999,999), and physical hardware remaining
disabled. Foxglove's 3D view was visually checked and its chat used to send a
return-to-start request. Example screenshot: foxglove-navigation.png.
check_navigation_skills_ros.py additionally verified a complete accumulated 360Â°
rotation with no translation, a four-step turn/forward/reverse/turn sequence,
return to a saved custom waypoint, listing destinations, cancellation of the
whole pending queue, invalid waypoint rejection and hardware staying disabled.
The Foxglove extension build and TypeScript check passed.
check_navigation_language_ros.py additionally passed the complete PC/Pi flow:
varied-language full clockwise spin, centimetre conversion, ordered return to
start, ambiguous instructions not executing, invalid-goal rejection feedback,
and cancelling a request while the model was generating. Unit tests exercise
schema/type/bounds validation, unmentioned goal names, hypothetical/negative
request filtering, stale generation rejection, executor events and deadlines.

check_navigation_routes_ros.py verified the corrected planner live on the public
map. From (0.1,0.1) to (2.037,3.081), the former cardinal grid path was 5.00 m
and the direct path is 3.555 m (28.9% shorter). The published path has exactly
two endpoints, preserving the requested coordinates. Final pose was
(2.0264293,3.0646396), 1.9478 cm from the destination. A route to goal_a has
three simplified waypoints; every segment passed collision checking. Full
results: route-verification.json. New tests cover octile route cost, direct
Euclidean routes, thin obstacles, unknown space, corner-cut rejection, boundary
endpoints and controller execution of diagonal and obstacle-detour routes.
Foxglove now displays planned route length and remaining goal error in cm.

## Next development milestones

1. Extend the bounded language interface with short-lived clarification context,
   explicit "there"/pronoun grounding, a larger evaluation set and task progress.
   The validated skills, initial plan display, terminal feedback and deadlines
   are now implemented. Pause/resume and speech input remain future work.
2. Add an indoor simulation world with moving obstacles, a simulated LiDAR and
   wheel odometry; no physical LiDAR is required for these development tests.
3. Bring up Nav2 on the Pi/Linux or a Linux simulation with map server, AMCL
   localization, planner/controller, collision monitoring and clear TF frames.
4. Establish T12 /scan access, wheel-encoder odometry, controller interface,
   real footprint and independent emergency-stop behavior.
5. Build a map of the actual room with SLAM Toolbox, validate localization and
   compare commanded/observed motion before enabling physical navigation.
6. Integrate the same Qwen skill interface with Nav2 actions. Validate model-produced goals
   against the map, require clarification when a destination is ambiguous, and
   let Nav2 calculate/follow the route with live obstacle updates.

References:
https://docs.nav2.org/jazzy/configuration_and_development/
https://docs.foxglove.dev/docs/visualization/panels/3d

## Run from the consolidated checkout

From the repository root, use your sourced ROS environment:

```sh
python robot_station/start.py --demo --navigation-demo --port 8766
```

The station loads the bundled map from this folder when no installed `robot_station/navigation-data` exists. Existing deployed maps take precedence. Custom waypoints are local runtime state and ignored by Git. Optional AI and memory still require the parameters documented in `robot_station/AI_CHAT.md`. Original deployment diagnostics are preserved in `tools/diagnostics/`; review their machine-specific paths before running them.
