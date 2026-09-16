# Working on UnderBot

## Branch workflow

`EM-URDF-Body` is the current integration branch for the initial body and station
handoff. Keep this combined snapshot there. After team review, open a pull request
to `main` so it can become the shared baseline.

Each teammate should branch from the same baseline and open a pull request back
to the integration branch (or to `main` after the baseline is merged):

```sh
git fetch origin
git switch EM-URDF-Body
git pull --ff-only
git switch -c feature/your-change
```

Do not have all eight people push directly to the same branch. Agree who owns
geometry, joints, sensor drivers, base control, navigation, perception,
communications/AI, and the station UI. Small pull requests reduce overlap.

## Editing and checks

- Geometry and joints: edit `compact_lab_rover/build_model.py`, regenerate with
  `pixi run build-model`, then inspect the result using `pixi run view`.
- Dashboard arrangement: edit `robot_station/build_layout.py`, run it, then import
  `underbot-station.json` into Foxglove. Desktop export format is required.
- Extension: run `npm ci`, `npm run build`, and `npx tsc --noEmit` inside
  `robot-station-extension`; install locally and verify against the synthetic demo.
- Gateway: run `python -m unittest test_gateway -v` in sourced ROS 2 Jazzy, or
  `pixi run test` inside `robot_station` on Windows.
- Before committing: `git diff --check`; inspect `git diff` and `git status`.

Preserve the documented topic names, units, frames and JSON request/response
formats or update both producers and consumers together. Report actual sensor
state separately from requests. Never represent synthetic messages as live data.
Keep hardware forwarding disabled until controller integration is reviewed.

Use environment variables or local ignored configuration for credentials. Do not
commit API keys, passwords, SSH keys, recordings, dependencies or machine caches.
The Pi username/address in the docs are deployment defaults, not credentials;
change the launcher/deployment parameters for your own machine.

## Suggested next pull requests

1. Replace provisional dimensions, axes and geometry with measured CAD exports.
2. Connect the URDF and real joint states to the station's 3D view.
3. Implement sensor publishers and consistent TF, timestamps and calibration.
4. Add the controller adapter, motor-side watchdog and manual/Nav2 arbitration.
5. Add physics parameters and a separately validated Gazebo simulation.
6. Integrate SLAM/Nav2, perception, audio and AI backends behind the topic contract.

The station demo is a UI/transport test, not validation of robot physics,
collision avoidance, hardware performance or navigation accuracy.
