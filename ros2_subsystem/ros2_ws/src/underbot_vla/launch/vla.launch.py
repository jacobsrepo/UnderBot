from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    model_arg = DeclareLaunchArgument(
        'model_name',
        default_value='moondream',
        description='Model name in Ollama (e.g. moondream, qwen2.5:1.5b)'
    )
    ollama_url_arg = DeclareLaunchArgument(
        'ollama_url',
        default_value='http://127.0.0.1:11434',
        description='Ollama server URL'
    )
    camera_topic_arg = DeclareLaunchArgument(
        'camera_topic',
        default_value='/camera/image_raw',
        description='Camera image topic for visual reasoning'
    )

    vla_node = Node(
        package='underbot_vla',
        executable='vla_node',
        name='vla_brain_node',
        output='screen',
        parameters=[{
            'model_name': LaunchConfiguration('model_name'),
            'ollama_url': LaunchConfiguration('ollama_url'),
            'camera_topic': LaunchConfiguration('camera_topic')
        }]
    )

    return LaunchDescription([
        model_arg,
        ollama_url_arg,
        camera_topic_arg,
        vla_node
    ])
