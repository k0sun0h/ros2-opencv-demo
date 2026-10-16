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
            self.get_logger().info(
                f'영상 열기 성공: {path} ({w}x{h}, {total}프레임)')

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
