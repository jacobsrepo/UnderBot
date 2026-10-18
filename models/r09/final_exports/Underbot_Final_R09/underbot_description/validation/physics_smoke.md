# Independent physics smoke test

PASS — MuJoCo 3.15.0 imported the actual portable URDF.

Source SHA-256: `589055d459d67174ca98c76689f6f99c45dc8ab15cf91992ec5ae4d87fbd9b97`.
Declared / imported mass: 19.601007800 / 19.601007800 kg (estimated hardware inputs).
Motors: 14. Caster swivel and rolling joints are passive; all recorded ground contacts belong to the three intended rolling bodies.
Rest tilt: [-6.851687404090413e-06, 0.05694478237824664] degrees; contacts: 6.
Resting COM: [-0.06369535625410272, 4.1055072966551786e-05, 0.2977380629849531] m in world coordinates; margin inside the actual ground support polygon: 0.1162 m.
Gentle forward translation: 0.0878 m.
Positive turn: 0.2571 rad.
Caster alignment transient: 0.0447 rad in the first 1.5 s. Final turn follows a 0.5 s ramp and 4 s hold at a commanded 0.25 rad/s; this is a sign and stability check, not accurate velocity tracking.
Maximum jaw-coupling error: 0.000016 rad.

| Commanded joint (both arms) | Target rad | Left / right achieved rad | Maximum final speed rad/s |
|---|---:|---:|---:|
| arm_base_joint | 0.100 | 0.097733 / 0.097735 | 0.000198 |
| shoulder_joint | 0.100 | 0.073902 / 0.073901 | 0.000066 |
| elbow_joint | 0.100 | 0.085367 / 0.085367 | 0.000003 |
| wrist_pitch_joint | 0.100 | 0.097131 / 0.097130 | 0.000000 |
| wrist_roll_joint | 0.100 | 0.100026 / 0.100026 | 0.000000 |

The adapter adds the ground, floating root and test motors. It verifies native jaw mimic constraints, only adds a relation if the importer omitted it, and uses an explicit 2 ms equality time constant for the ideal jaw coupling. It preserves the URDF mass, inertia and collision model. See physics_smoke.json for passive caster angles/rates, contact history, observed effort caps and exact configuration. The generated MJCF is a reproducible test scene, not an Isaac or Gazebo profile.

These tests validate import, numerical behavior and motion signs for this estimated model. They do not measure the real robot or prove payload capability, full-range collision freedom or compatibility with other engines.
