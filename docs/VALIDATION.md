# Validation status

## Verified locally

- The active R09 portable URDF imports into PyBullet and passes its model,
  gripper-coupling, limit, and fixed-base tests.
- Native Windows Gazebo Harmonic loads R09 and runs headless physics.
- Gazebo joint controls move simulated joints and report measured state.
- Coordinated arm targets, bounded position inverse kinematics, demonstration
  validation, and replay logic pass the local automated tests.
- The ROS/Foxglove station publishes ROS 2 demo topics and accepts its bounded
  station command topic.
- The R09 fleet loader, planner, namespaced frames, collision guards, mission
  execution, cancellation, and deadlines pass 17 automated tests.

## Not yet validated

- Physical motor, arm, gripper, T12, LiDAR, encoder, or emergency-stop control.
- Gazebo-to-ROS integration for the current native Windows world.
- Payload, torque, balance, grasp robustness, self-collision, friction, backlash,
  or sim-to-real accuracy.
- A successful physical pick-and-place in Gazebo after the latest task-scene
  clearance adjustment. No imitation-learning policy has been trained.

Passing software tests means the interfaces behave as specified; it does not
establish real-robot safety or performance.
