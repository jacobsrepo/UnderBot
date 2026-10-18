#!/usr/bin/env python3
"""Build optional Gazebo/ROS controller resources from the expanded core URDF.

No simulator or ROS installation is required. This preserves the portable core
and adds only simulator-specific tags to underbot.gazebo.urdf. Regenerate after
changing dimensions or joint limits. PID/contact settings are initial estimates.
"""
import argparse
import copy
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def child(parent, tag, value=None, **attributes):
    element = ET.SubElement(parent, tag, attributes)
    if value is not None:
        element.text = str(value)
    return element


def number(value):
    return format(float(value), ".12g")


def xml_write(element, path):
    ET.indent(element, space="  ")
    path.write_bytes(ET.tostring(element, encoding="utf-8", xml_declaration=True) + b"\n")


def main():
    package = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=package / "urdf" / "underbot.portable.urdf")
    parser.add_argument("--output", type=Path, default=package / "urdf" / "underbot.gazebo.urdf")
    parser.add_argument("--absolute-meshes", action="store_true",
                        help="Resolve mesh paths to file:// URLs for this machine")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if source == output:
        raise ValueError("Gazebo output must differ from the portable core source")
    robot = ET.parse(source).getroot()
    if robot.tag != "robot":
        raise ValueError("Source must be an expanded URDF robot")
    if robot.findall("gazebo"):
        raise ValueError("Source already contains Gazebo tags; use the portable core")
    joints = {joint.attrib["name"]: joint for joint in robot.findall("joint")}
    links = {link.attrib["name"]: link for link in robot.findall("link")}
    wheel_names = ["left_wheel_joint", "right_wheel_joint"]
    arm_suffixes = ["arm_base_joint", "shoulder_joint", "elbow_joint",
                    "wrist_pitch_joint", "wrist_roll_joint", "gripper_left_joint"]
    arm_names = [f"{side}_{suffix}" for side in ["left", "right"] for suffix in arm_suffixes]
    for name in wheel_names + arm_names:
        if name not in joints or joints[name].find("limit") is None:
            raise ValueError(f"Required command joint or limit missing: {name}")
        if joints[name].find("mimic") is not None:
            raise ValueError(f"Command joint is unexpectedly a mimic follower: {name}")
    wheel_origins = []
    radii = []
    for name in wheel_names:
        joint = joints[name]
        wheel_origins.append([float(x) for x in joint.find("origin").attrib["xyz"].split()])
        link = links[joint.find("child").attrib["link"]]
        cylinder = link.find("collision/geometry/cylinder")
        if cylinder is None:
            raise ValueError(f"Expected cylindrical wheel collision for {name}")
        radii.append(float(cylinder.attrib["radius"]))
    if not math.isclose(radii[0], radii[1], rel_tol=1e-8):
        raise ValueError("This profile assumes equal wheel radii")
    separation = abs(wheel_origins[0][1] - wheel_origins[1][1])
    radius = radii[0]
    if separation <= 0 or radius <= 0:
        raise ValueError("Invalid wheel geometry")

    config = package / "config"
    config.mkdir(parents=True, exist_ok=True)
    limits_yaml = ["# Generated directly from expanded URDF; all actuator limits remain estimates.",
                   "# Companion integration data; URDF remains the authoritative model.",
                   "joint_limits:"]
    for name, joint in joints.items():
        if joint.attrib.get("type") == "fixed":
            continue
        limit = joint.find("limit")
        if limit is None:
            continue
        limits_yaml.append(f"  {name}:")
        bounded = joint.attrib["type"] != "continuous"
        limits_yaml.append(f"    has_position_limits: {str(bounded).lower()}")
        if bounded:
            limits_yaml.extend([f"    min_position: {limit.attrib['lower']}",
                                f"    max_position: {limit.attrib['upper']}"])
        limits_yaml.extend(["    has_velocity_limits: true",
                            f"    max_velocity: {limit.attrib['velocity']}",
                            "    has_acceleration_limits: false",
                            "    has_effort_limits: true",
                            f"    max_effort: {limit.attrib['effort']}"])
    (config / "joint_limits.yaml").write_text("\n".join(limits_yaml) + "\n", encoding="utf-8")

    controller_yaml = [
        "# OPTIONAL ROS 2 Jazzy controller integration template; NOT loaded by display.launch.py.",
        "# Requires a hardware/simulator ros2_control interface, absent from the portable core.",
        "# Do not enable together with the standalone Gazebo controller profile.",
        "# Wheel dimensions and joint names below are generated from the core URDF.",
        "controller_manager:", "  ros__parameters:", "    update_rate: 100",
        "    joint_state_broadcaster:", "      type: joint_state_broadcaster/JointStateBroadcaster",
        "    base_controller:", "      type: diff_drive_controller/DiffDriveController",
        "    left_arm_controller:", "      type: joint_trajectory_controller/JointTrajectoryController",
        "    right_arm_controller:", "      type: joint_trajectory_controller/JointTrajectoryController",
        "base_controller:", "  ros__parameters:",
        "    left_wheel_names: [left_wheel_joint]", "    right_wheel_names: [right_wheel_joint]",
        f"    wheel_separation: {number(separation)}", f"    wheel_radius: {number(radius)}",
        "    base_frame_id: base_link", "    odom_frame_id: odom", "    enable_odom_tf: true",
        "    position_feedback: true", "    open_loop: false", "    publish_rate: 50.0",
        "    cmd_vel_timeout: 0.5",
    ]
    for side in ["left", "right"]:
        controller_yaml.extend([f"{side}_arm_controller:", "  ros__parameters:", "    joints:"])
        controller_yaml.extend(f"      - {side}_{suffix}" for suffix in arm_suffixes)
        controller_yaml.extend(["    command_interfaces: [position]", "    state_interfaces: [position, velocity]",
                                "    allow_partial_joints_goal: false", "    action_monitor_rate: 20.0"])
    (config / "ros2_controllers.example.yaml").write_text("\n".join(controller_yaml) + "\n", encoding="utf-8")

    profile = ET.Element("gazebo_profile")
    profile.append(ET.Comment("Optional Gazebo Harmonic/Ionic systems; estimated PID/contact values; not runtime tested."))
    gazebo = child(profile, "gazebo")
    child(gazebo, "self_collide", "false")
    diff = child(gazebo, "plugin", filename="gz-sim-diff-drive-system", name="gz::sim::systems::DiffDrive")
    for tag, value in [("left_joint", wheel_names[0]), ("right_joint", wheel_names[1]),
                       ("wheel_separation", number(separation)), ("wheel_radius", number(radius)),
                       ("topic", "/underbot/cmd_vel"), ("odom_topic", "/underbot/odometry"),
                       ("tf_topic", "/underbot/odom_tf"), ("frame_id", "odom"),
                       ("child_frame_id", "base_link"), ("odom_publish_frequency", 50),
                       ("min_linear_velocity", -0.2), ("max_linear_velocity", 0.2),
                       ("min_angular_velocity", -0.8), ("max_angular_velocity", 0.8),
                       ("min_linear_acceleration", -0.25), ("max_linear_acceleration", 0.25),
                       ("min_angular_acceleration", -1.0), ("max_angular_acceleration", 1.0)]:
        child(diff, tag, value)
    publisher = child(gazebo, "plugin", filename="gz-sim-joint-state-publisher-system",
                      name="gz::sim::systems::JointStatePublisher")
    child(publisher, "topic", "/underbot/joint_states")
    child(publisher, "update_rate", 50)
    for name in arm_names:
        effort = float(joints[name].find("limit").attrib["effort"])
        # Starting values screened in the independent engine; tune in Gazebo.
        # Tiny roll/jaw inertias are unstable with a uniform derivative gain.
        p_gain, d_gain = (12, 0) if "wrist_roll" in name else (30, 0.05) if "wrist_pitch" in name else (8, 0.03) if "gripper" in name else (30, 1)
        position = child(gazebo, "plugin", filename="gz-sim-joint-position-controller-system",
                         name="gz::sim::systems::JointPositionController")
        for tag, value in [("joint_name", name), ("topic", f"/underbot/{name}/cmd_pos"),
                           ("initial_position", 0), ("p_gain", p_gain), ("i_gain", 0),
                           ("d_gain", d_gain), ("i_max", 0), ("i_min", 0),
                           ("cmd_max", number(effort)), ("cmd_min", number(-effort))]:
            child(position, tag, value)
    for name in wheel_names:
        wheel_link = joints[name].find("child").attrib["link"]
        surface = child(profile, "gazebo", reference=wheel_link)
        child(surface, "mu1", 0.8)
        child(surface, "mu2", 0.8)
    if "caster_link" in links:
        surface = child(profile, "gazebo", reference="caster_link")
        child(surface, "mu1", 0.8)
        child(surface, "mu2", 0.8)
    xml_write(profile, config / "gazebo_plugins.xml")
    for fragment in profile:
        if isinstance(fragment.tag, str):
            robot.append(copy.deepcopy(fragment))
    for mesh in robot.findall(".//mesh"):
        filename = mesh.attrib["filename"]
        if filename.startswith("package://underbot_description/"):
            asset = package / filename.removeprefix("package://underbot_description/")
        elif "://" not in filename:
            asset = source.parent / filename
        else:
            continue
        asset = asset.resolve()
        if not asset.is_file():
            raise FileNotFoundError(f"Missing mesh: {asset}")
        if args.absolute_meshes:
            mesh.attrib["filename"] = asset.as_uri()
        else:
            import os
            mesh.attrib["filename"] = Path(os.path.relpath(asset, output.parent)).as_posix()
    output.parent.mkdir(parents=True, exist_ok=True)
    xml_write(robot, output)
    print(f"Wrote {output}")
    print(f"Wheel radius {radius:g} m; separation {separation:g} m; 12 independent position controllers")
    print("No simulator was launched; gains, friction and motor response require runtime validation.")


if __name__ == "__main__":
    main()
