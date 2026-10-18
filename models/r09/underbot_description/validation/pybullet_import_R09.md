# R09 actual-URDF PyBullet inspection

PASS: imported `underbot.portable.urdf` with `URDF_USE_INERTIA_FROM_FILE` and a floating base. The import contains 23 links and 22 joints, with 14 actuated and two passive independent coordinates. Imported mass 19.601007800 kg matches the URDF sum.

At an independently selected nonzero pose, all 22 child link frames agree with separate URDF forward kinematics: maximum position error 5.01e-08 m; maximum rotation-matrix element error 1.74e-07. Mimic follower positions were explicitly calculated from the URDF equations because this PyBullet load does not implement a mimic actuator constraint.

This check does not establish dynamic stability, measured hardware accuracy, or native ROS/Gazebo/Isaac compatibility. Exact source and asset hashes are recorded in the adjacent JSON.
