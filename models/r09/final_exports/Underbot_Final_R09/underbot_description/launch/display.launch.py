"""Show Underbot in RViz2; use sliders only for kinematic inspection.

With a simulator providing /joint_states, launch with
publish_joint_states:=false use_sim_time:=true.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _boolean(context, name):
    value = LaunchConfiguration(name).perform(context).strip().lower()
    if value not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false, got {value!r}")
    return value == "true"


def _setup(context):
    model_path = Path(LaunchConfiguration("model").perform(context)).expanduser().resolve()
    if not model_path.is_file():
        raise FileNotFoundError(f"Robot description does not exist: {model_path}")
    if model_path.suffix == ".xacro":
        import xacro
        description = xacro.process_file(str(model_path)).toxml()
    else:
        description = model_path.read_text(encoding="utf-8")

    robot = ET.fromstring(description)
    if robot.tag != "robot":
        raise ValueError(f"Expected an expanded URDF robot in {model_path}")
    if any(element.tag.startswith("{http://www.ros.org/wiki/xacro}") for element in robot.iter()):
        raise ValueError("Unexpanded Xacro tags remain; select the .xacro entry point instead")
    use_sim_time = _boolean(context, "use_sim_time")
    publish_states = _boolean(context, "publish_joint_states")
    gui = _boolean(context, "gui")
    show_rviz = _boolean(context, "rviz")
    joint_states_topic = LaunchConfiguration("joint_states_topic").perform(context).strip()
    if not joint_states_topic:
        raise ValueError("joint_states_topic must not be empty")
    state_remapping = [("joint_states", joint_states_topic)]
    common = {"robot_description": ParameterValue(description, value_type=str),
              "use_sim_time": use_sim_time}
    nodes = [Node(
        package="robot_state_publisher", executable="robot_state_publisher",
        name="robot_state_publisher", output="screen", parameters=[common],
        remappings=state_remapping)]
    if publish_states:
        # Both publishers honor URDF mimic joints; the follower is not a command.
        publisher = "joint_state_publisher_gui" if gui else "joint_state_publisher"
        nodes.append(Node(
            package=publisher, executable=publisher, name=publisher,
            parameters=[common, {"use_mimic_tags": True, "use_smallest_joint_limits": True}],
            remappings=state_remapping))
    if show_rviz:
        rviz_config = Path(LaunchConfiguration("rviz_config").perform(context)).expanduser().resolve()
        if not rviz_config.is_file():
            raise FileNotFoundError(f"RViz configuration does not exist: {rviz_config}")
        nodes.append(Node(
            package="rviz2", executable="rviz2", name="rviz2", output="screen",
            arguments=["-d", str(rviz_config)], parameters=[{"use_sim_time": use_sim_time}]))
    return nodes


def generate_launch_description():
    share = Path(get_package_share_directory("underbot_description"))
    return LaunchDescription([
        DeclareLaunchArgument("model", default_value=str(share / "urdf" / "underbot.urdf"),
                              description="Expanded URDF or Xacro file"),
        DeclareLaunchArgument("gui", default_value="true", description="Joint sliders"),
        DeclareLaunchArgument("publish_joint_states", default_value="true",
                              description="Disable when simulator/hardware publishes joint states"),
        DeclareLaunchArgument("joint_states_topic", default_value="joint_states",
                              description="Joint state input; sliders also publish here when enabled"),
        DeclareLaunchArgument("rviz", default_value="true"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        DeclareLaunchArgument("rviz_config", default_value=str(share / "rviz" / "underbot.rviz")),
        OpaqueFunction(function=_setup),
    ])
