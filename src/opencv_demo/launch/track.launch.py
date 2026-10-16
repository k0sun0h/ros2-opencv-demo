"""카메라(가짜/실기기) + 물체 추적을 한 번에 띄운다.

사용법:
    ros2 launch opencv_demo track.launch.py                          # 가짜 프레임
    ros2 launch opencv_demo track.launch.py use_camera:=true         # 실제 USB 카메라
    ros2 launch opencv_demo track.launch.py use_camera:=true h_min:=100 h_max:=140
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    use_camera = LaunchConfiguration('use_camera')

    def as_int(name):
        return ParameterValue(LaunchConfiguration(name), value_type=int)

    args = [
        DeclareLaunchArgument('use_camera', default_value='false',
                              description='true = 실제 USB 카메라, false = 가짜 프레임'),
        DeclareLaunchArgument('device_id', default_value='/dev/v4l/by-id/usb-Generic_Web_Camera_200901010001-video-index0'),
        DeclareLaunchArgument('width', default_value='320'),
        DeclareLaunchArgument('height', default_value='240'),
        DeclareLaunchArgument('h_min', default_value='90'),
        DeclareLaunchArgument('h_max', default_value='130'),
        DeclareLaunchArgument('s_min', default_value='100'),
        DeclareLaunchArgument('v_min', default_value='100'),
        DeclareLaunchArgument('min_area', default_value='100'),
    ]

    fake_camera = Node(
        package='opencv_demo',
        executable='image_pub',
        name='fake_camera_pub',
        output='screen',
        condition=UnlessCondition(use_camera),
    )

    real_camera = Node(
        package='opencv_demo',
        executable='camera_pub',
        name='camera_pub',
        output='screen',
        condition=IfCondition(use_camera),
        parameters=[{
            'device_id': ParameterValue(LaunchConfiguration('device_id'), value_type=str),
            'width': as_int('width'),
            'height': as_int('height'),
        }],
    )

    tracker = Node(
        package='opencv_demo',
        executable='object_tracker',
        name='object_tracker',
        output='screen',
        parameters=[{
            'h_min': as_int('h_min'),
            'h_max': as_int('h_max'),
            's_min': as_int('s_min'),
            'v_min': as_int('v_min'),
            'min_area': as_int('min_area'),
        }],
    )

    return LaunchDescription(args + [fake_camera, real_camera, tracker])
