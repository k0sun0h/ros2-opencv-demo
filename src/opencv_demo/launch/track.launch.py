"""image_pub + object_tracker 를 한 번에 띄운다.

사용법:
    ros2 launch opencv_demo track.launch.py
    ros2 launch opencv_demo track.launch.py h_min:=100 h_max:=140   # 임계값 바꿔서
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    args = [
        DeclareLaunchArgument('h_min', default_value='90'),
        DeclareLaunchArgument('h_max', default_value='130'),
        DeclareLaunchArgument('s_min', default_value='100'),
        DeclareLaunchArgument('v_min', default_value='100'),
        DeclareLaunchArgument('min_area', default_value='100'),
    ]

    image_pub = Node(
        package='opencv_demo',
        executable='image_pub',
        name='fake_camera_pub',
        output='screen',
    )

    tracker = Node(
        package='opencv_demo',
        executable='object_tracker',
        name='object_tracker',
        output='screen',
        parameters=[{
            'h_min': LaunchConfiguration('h_min'),
            'h_max': LaunchConfiguration('h_max'),
            's_min': LaunchConfiguration('s_min'),
            'v_min': LaunchConfiguration('v_min'),
            'min_area': LaunchConfiguration('min_area'),
        }],
    )

    return LaunchDescription(args + [image_pub, tracker])
