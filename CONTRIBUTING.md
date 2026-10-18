ï»¿# Working on UnderBot

## Branch workflow

`main` is the consolidated baseline. Historical development branches remain intact. Use a feature branch for new work and open a pull request to `main`:

```sh
git fetch origin
git switch main
git pull --ff-only
git switch -c feature/your-change
```

Keep each implementation in its documented component folder. See [the project map](docs/PROJECT_MAP.md) before changing shared ROS topics or choosing a robot model. Imported desktop, ROS and website snapshots retain their own setup instructions and are not automatically deployed from this repository.

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

## Next integration work

1. Select the robot revision and measured physical assumptions for MATLAB/Simulink modelling.
2. Reconcile `/station/...` and `/underbot/...` topic contracts before connecting alternate stacks.
3. Integrate measured sensor/controller interfaces, watchdogs and command arbitration.
4. Validate real localization/navigation independently of the sample-map demonstration.
5. Decide ownership and update paths for the imported website and model snapshots.

Preserve every independent development line until its replacement has been tested and agreed. The simulation and UI demonstrations do not establish physical robot capabilities.
