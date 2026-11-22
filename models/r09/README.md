# UnderBot R09 model

`underbot_description/` is the active and only robot-description source in this
repository. It contains the URDF/Xacro model, simulator configuration, meshes,
textures, limits, estimated mass/inertia data, documentation, and validation
records required by the current software.

Use `underbot_description/urdf/underbot.portable.urdf` for tools that require a
plain portable URDF. Gazebo preparation starts from
`underbot_description/urdf/underbot.gazebo.urdf` and resolves its mesh paths into
an ignored generated world.

The model includes estimated dynamics. Its dimensions, joint conventions, and
import checks are useful software inputs, but payload, torque, contact, balance,
and physical accuracy require measurements from the real robot.
