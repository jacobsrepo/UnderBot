# Consolidation validation ? 2026-10-18

Passed:
- Existing station suite: 60 tests covering gateway bounds/watchdog, navigation planning/execution/cancellation, language constraints, AI backend, memory responses and world-state freshness. Run with the installed ROS environment: `pixi run --manifest-path D:/Robotics/rviz2-jazzy/pixi.toml python -m unittest discover -s robot_station -p "test_*.py" -v`.
- Perception unit tests: 5 audio-device and face-matching tests (`python -m unittest test_pi_audio_device test_memory.Matching -v` from perception).
- Foxglove extension: `npm run build` and `tsc --noEmit`.
- Existing `hardware/electrical/check_schematic_r05.py` connectivity assertions. This does not revalidate electronics, thermal performance, current ratings or other revisions.

Scope:
- Live database integration tests were not run: they require private database configuration and are not necessary for source organization.
- Robot services, microphone/camera capture and hardware actuation were not restarted or exercised.
- Imported historical desktop/ROS stacks are preserved as independent implementations; no end-to-end integration or physical robot capability is claimed.
- MATLAB/Simulink modelling and simulation have not started.

Additional consolidation checks:
- Website lint/build and all 5 Playwright browser tests passed from `website/`.
- Website model sync reproduced the bundled R08 assets without changes and retained upstream commit 3f28a65.
- Cortex's 2 isolated memory tests passed; Python 3.14 reported existing unclosed-SQLite resource warnings in those historical tests. No live memory database was used.
- All 174 Python/FreeCAD files present at initial import parsed successfully; final syntax and source-preservation counts are recorded in CONSOLIDATION_CHECK.json.
- R08 model validation: PASS, no errors/warnings, 23 links and 22 joints.
- R09 model validation: no errors, 23 links and 22 joints; review note that base_link.stl visual shells touch at four nonmanifold edges. It is not a unioned physics solid. Collision/dynamics choices need review for the MATLAB task.
- The fresh-checkout navigation loader now falls back to the bundled map; three regression tests cover repository, installed and missing-data cases. Existing installed-map precedence is retained.
- Snapshot source trees matched upstream exactly before the documented website path adaptation. Original commits are preserved in merge ancestry.

Model validator reports from this run are stored in the local consolidation backup folder. Historical per-model reports remain unmodified. The validators need an activated Pixi environment for numerical-library DLLs on this PC.
