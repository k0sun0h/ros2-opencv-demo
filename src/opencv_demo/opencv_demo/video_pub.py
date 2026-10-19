import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class VideoPublisher(Node):
    """영상 파일(mp4/avi)을 읽어 /camera/image_raw 로 반복 발행한다.

    카메라가 USB/IP 로 온전히 넘어오지 않을 때의 대체 입력원.
    영상 경로/주기/반복 여부는 파라미터로 바꿀 수 있다.
    """

    def __init__(self):
        super().__init__('video_pub')
        self.declare_parameter('video_path', '/mnt/c/Users/kimsu/test.mp4')
        self.declare_parameter('fps', 10.0)
        self.declare_parameter('loop', True)

        path = self.get_parameter('video_path').value
        fps = self.get_parameter('fps').value
        self.loop = self.get_parameter('loop').value

        self.cap = cv2.VideoCapture(path)
        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, '/camera/image_raw', 10)
        self.n = 0

        if not self.cap.isOpened():
            self.get_logger().error(f'영상 열기 실패: {path}')
        else:
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            video_fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.get_logger().info(
                f'영상 열기 성공: {path} ({w}x{h}, {total}프레임)')

            # ★ 10/19 추가: 요청값이 아니라 '실제값' 을 찍는다 (10/18 원칙)
            #   영상 자체 fps 와 발행 fps 가 다르면 재생 속도가 왜곡된다.
            #   예) 28.7fps 영상을 10Hz 로 내보내면 -> 2.87배 느린 슬로모션.
            if video_fps > 0:
                ratio = video_fps / fps if fps > 0 else 0.0
                self.get_logger().info(
                    f'영상 자체 fps={video_fps:.1f} / 발행 fps={fps:.1f} '
                    f'-> {ratio:.2f}배 속도로 재생')
                if fps > 0 and abs(video_fps - fps) / video_fps > 0.2:
                    self.get_logger().warn(
                        '영상 fps 와 발행 fps 차이가 20% 이상입니다. '
                        '실시간 재생이 필요하면 fps 를 영상에 맞추세요 '
                        f'(예: fps:={video_fps:.1f}).')

        self.timer = self.create_timer(1.0 / fps, self.timer_callback)

    def timer_callback(self):
        ok, frame = self.cap.read()
        if not ok:
            if self.loop:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return

        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera'
        self.pub.publish(msg)

        self.n += 1
        if self.n % 50 == 0:
            self.get_logger().info(f'{self.n} 프레임 발행 {frame.shape}')

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = VideoPublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
