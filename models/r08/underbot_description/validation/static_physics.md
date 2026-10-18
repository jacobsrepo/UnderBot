# Independent static physics audit

URDF SHA-256: `805ae58b87af3d3030c201def6d7126b09fd0e907e6bebbdabf9e0db6059e3c7`

Model mass: **19.601008 kg**. Gravity: 9.80665 m/s². No added payload.

Evaluated 2000 simultaneous arm configurations, including zero, limit probes and a deterministic Halton sequence.
For every sampled arm pose, evaluated 720 full-circle caster angles and used a derivative bound to cover the angles between samples.

Minimum sampled support margin: **101.694 mm**.
Guaranteed lower bound across the full caster rotation, for these sampled arm poses: **101.648 mm**.
Support status: **POSITIVE_FOR_SAMPLED_ARM_POSES_AT_ALL_CASTER_ANGLES**. This is a level-ground point-contact calculation, not a dynamic tip test or an exhaustive arm-workspace proof.

| Independent input | Max absolute no-load holding torque (Nm) | URDF effort (Nm) | Samples over effort |
|---|---:|---:|---:|
| left_wheel_joint | 0.000000 | 2.500000 | 0 |
| right_wheel_joint | 0.000000 | 2.500000 | 0 |
| left_arm_base_joint | 0.661496 | 1.000000 | 0 |
| left_shoulder_joint | 0.942630 | 1.000000 | 0 |
| left_elbow_joint | 0.486534 | 1.000000 | 0 |
| left_wrist_pitch_joint | 0.146705 | 1.000000 | 0 |
| left_wrist_roll_joint | 0.006594 | 1.000000 | 0 |
| left_gripper_left_joint | 0.003406 | 0.300000 | 0 |
| right_arm_base_joint | 0.661496 | 1.000000 | 0 |
| right_shoulder_joint | 0.944059 | 1.000000 | 0 |
| right_elbow_joint | 0.487309 | 1.000000 | 0 |
| right_wrist_pitch_joint | 0.146368 | 1.000000 | 0 |
| right_wrist_roll_joint | 0.006616 | 1.000000 | 0 |
| right_gripper_left_joint | 0.003566 | 0.300000 | 0 |

Effort status: **WITHIN_PROVISIONAL_LIMITS_IN_SAMPLES**. URDF efforts are provisional modelling values; these results do not establish the servo kit's rated or continuous capacity.

Mimic jaw torques are combined by virtual work: input torque equals the driven jaw torque plus multiplier × mimicked jaw torque. Individual jaw-coordinate moments are retained in the JSON.

Independent central-difference potential-energy check: 72 coordinate evaluations; maximum error 1.17e-08 Nm.

The computation reads masses and COM origins from the URDF inertials. Inertia tensors are checked for positive definiteness; static gravity requires mass and COM, not the rotational tensor values.

## Scope and limits

- All mass/COM, arm geometry, motor limits and contact dimensions inherit the model's unmeasured hardware assumptions. Positive numerical results cannot verify actual hardware.
- Arm-space sampling does not prove extrema across every allowed simultaneous pose. Limit probes and Halton points improve coverage but are not a continuous workspace bound.
- No payload, inertial acceleration, slopes, traction, braking, servo friction, gearbox efficiency, cable loads, battery sag, thermal duty, collision validity, or control tracking is included.
- Support uses the centers of three ideal tire contacts on a rigid level plane. No suspension, tire deformation or uneven-ground model is used.
- Holding torque is a static actuator-input requirement. Mimic coupling uses ideal, unit-efficiency virtual work; real linkage transmission is unmeasured.
- Passive caster moments are reported as coordinates and are not interpreted as commanded actuator capacities.
- No Gazebo, Isaac Sim, Isaac Lab, RViz, ros2_control, USD importer, or hardware test is performed by this script.
