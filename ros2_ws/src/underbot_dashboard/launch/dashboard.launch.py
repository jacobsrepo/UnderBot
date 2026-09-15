from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    dashboard_node = Node(
        package='underbot_dashboard',
        executable='dashboard_server',
        name='dashboard_server',
        output='screen'
    )

    return LaunchDescription([
        dashboard_node
    ])
