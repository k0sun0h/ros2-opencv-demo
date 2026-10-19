"""카메라(가짜/실기기/영상파일) + 물체 추적을 한 번에 띄운다.

프로젝트 1 통합 실행용 — launch 한 줄로 입력원을 고른다.

사용법:
    # 가짜 프레임 (카메라 없이, 기본값)
    ros2 launch opencv_demo track.launch.py

    # 실제 USB 카메라
    ros2 launch opencv_demo track.launch.py source:=camera

    # 영상 파일 (usbipd 등시성 한계 우회)
    ros2 launch opencv_demo track.launch.py source:=video video_path:=/mnt/c/Users/kimsu/test.mp4

    # 파라미터까지
    ros2 launch opencv_demo track.launch.py source:=camera device_id:=/dev/v4l/by-id/usb-Generic_Web_Camera_200901010001-video-index0 width:=320 height:=240 show_debug:=true
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    source = LaunchConfiguration('source')

    def as_int(name):
        return ParameterValue(LaunchConfiguration(name), value_type=int)

    def as_float(name):
        return ParameterValue(LaunchConfiguration(name), value_type=float)

    # source 값에 따라 셋 중 하나만 뜬다 (상호 배타를 구조적으로 보장)
    is_fake = PythonExpression(["'", source, "' == 'fake'"])
    is_camera = PythonExpression(["'", source, "' == 'camera'"])
    is_video = PythonExpression(["'", source, "' == 'video'"])

    args = [
        DeclareLaunchArgument('source', default_value='fake',
                              description='입력원: fake(가짜) | camera(실기기) | video(영상파일)'),
        DeclareLaunchArgument('video_path', default_value='',
                              description='source:=video 일 때 읽을 영상 파일 경로'),
        DeclareLaunchArgument('loop', default_value='true',
                              description='source:=video 일 때 영상 반복 재생 여부'),
        DeclareLaunchArgument(
            'device_id',
            default_value='/dev/v4l/by-id/usb-Generic_Web_Camera_200901010001-video-index0',
            description='카메라 장치. by-id 경로(권장) 또는 숫자(0)'),
        DeclareLaunchArgument('width', default_value='640'),
        DeclareLaunchArgument('height', default_value='480'),
        DeclareLaunchArgument('fps', default_value='10.0'),
        DeclareLaunchArgument('h_min', default_value='90'),
        DeclareLaunchArgument('h_max', default_value='130'),
        DeclareLaunchArgument('s_min', default_value='100'),
        DeclareLaunchArgument('v_min', default_value='100'),
        DeclareLaunchArgument('min_area', default_value='100'),
        DeclareLaunchArgument('show_debug', default_value='true'),
    ]

    # 통합 실행 시 DDS 발견 문제(미러링 모드)를 launch 안에서 미리 막는다.
    # ⚠️ 다른 터미널에서 ros2 CLI 를 쓸 때도 같은 값이어야 하므로 ~/.bashrc 에도 넣어둘 것.
    localhost_only = SetEnvironmentVariable('ROS_LOCALHOST_ONLY', '1')

    fake_camera = Node(
        package='opencv_demo',
        executable='image_pub',
        name='fake_camera_pub',
        output='screen',
        condition=IfCondition(is_fake),
    )

    real_camera = Node(
        package='opencv_demo',
        executable='camera_pub',
        name='camera_pub',
        output='screen',
        condition=IfCondition(is_camera),
        parameters=[{
            'device_id': LaunchConfiguration('device_id'),   # 문자열(by-id) 그대로 전달
            'width': as_int('width'),
            'height': as_int('height'),
            'fps': as_float('fps'),
        }],
    )

    video_input = Node(
        package='opencv_demo',
        executable='video_pub',
        name='video_pub',
        output='screen',
        condition=IfCondition(is_video),
        parameters=[{
            'video_path': LaunchConfiguration('video_path'),
            'fps': as_float('fps'),          # ★ 10/19 수정: camera 와 동일하게 fps 전달
            'loop': ParameterValue(LaunchConfiguration('loop'), value_type=bool),
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
            'show_debug': ParameterValue(LaunchConfiguration('show_debug'), value_type=bool),
        }],
    )

    return LaunchDescription(
        [localhost_only] + args + [fake_camera, real_camera, video_input, tracker]
    )
