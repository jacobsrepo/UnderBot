# R08 in Foxglove

The UnderBot Control Station, UnderBot EMEET Live and underbot-navigation-layout working layouts now load:

`D:\Robotics\underbot-r08\underbot_description\urdf\underbot.foxglove.urdf`

This is the R08 URDF with only mesh references rewritten to absolute local file URLs. All 45 meshes match the source; the 23 links, 22 joints, geometry, inertia and joint origins are unchanged. Each 3D scene uses Z-up for STL assets, with frame labels hidden. The navigation layout hides its previous simple `/navigation/robot` marker and uses the URDF attached to the existing `map -> base_link` transform.

The navigation simulation, planner, ROS publishers, hardware settings, camera feeds and controls were not changed. This is a visualization update, not a new collision-footprint or dynamics calibration. A recording should be described as a path-planning simulation using the R08 design model.

Foxglove was visually checked with the assembled model upright and the path visible. Its Problems tab reports no problems. The navigation view is left connected to `ws://127.0.0.1:8766`.

For recording, use the existing navigation controls and the 3D panel's expand button if desired. The window can return to the full panel layout with its restore button.

Original saved-layout files are in the timestamped directory recorded in `installation.json`. Updated importable exports are in `layouts/`. The original remote layout baselines remain intact; these are persisted local working edits. Camera orbit and last-viewed metadata may change during inspection.

To restore a layout, close Foxglove, copy that layout's original backup file to its matching file in the Foxglove `studio-datastores/layouts-remote-om_0ec7fcCTjGIDJARN` directory, then reopen Foxglove. No robot assets need to be deleted.

Run `python verify.py` while Foxglove is closed for a strict model and configuration comparison. The check allows camera orbit and last-viewed metadata to differ, but rejects unrelated panel changes.
