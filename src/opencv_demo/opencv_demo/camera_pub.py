import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class CameraPublisher(Node):
    """실제 USB 카메라(/dev/videoN)를 열어 /camera/image_raw 로 발행한다.

    WSL2 + usbipd 환경에서는 백엔드를 CAP_V4L2 로 명시해야 열린다.
    """

    def __init__(self):
        super().__init__('camera_pub')

        self.declare_parameter('device_id', '/dev/v4l/by-id/usb-Generic_Web_Camera_200901010001-video-index0')
        self.declare_parameter('width', 320)
        self.declare_parameter('height', 240)
        self.declare_parameter('fps', 10.0)
        self.declare_parameter('frame_id', 'camera')

        device_id = self.get_parameter('device_id').value
        width = self.get_parameter('width').value
        height = self.get_parameter('height').value
        fps = self.get_parameter('fps').value
        self.frame_id = self.get_parameter('frame_id').value

        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, '/camera/image_raw', 10)

        # ★ WSL2 에서는 백엔드를 V4L2 로 명시 (자동 선택이 멈추는 경우가 있음)
        dev = int(device_id) if str(device_id).isdigit() else device_id
        self.cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
        # ★ WSL2 + usbipd 는 등시성 전송 유실이 있어서 MJPG(압축)로 대역폭을 줄여야 한다
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        if not self.cap.isOpened():
            self.get_logger().error(
                f'카메라를 열 수 없음: {device_id}  '
                '(usbipd attach 확인 / video 그룹 확인)')
        else:
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.get_logger().info(
                f'카메라 열기 성공: /dev/video{device_id} ({w}x{h})')

        self.n = 0
        self.fail = 0
        self.timer = self.create_timer(1.0 / fps, self.timer_callback)

    def timer_callback(self):
        ok, frame = self.cap.read()
        if not ok:
            self.fail += 1
            if self.fail <= 3 or self.fail % 100 == 0:
                self.get_logger().warn(f'프레임 읽기 실패 ({self.fail}회)')
            return

        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        self.pub.publish(msg)

        self.n += 1
        if self.n % 50 == 0:
            self.get_logger().info(f'{self.n} 프레임 발행 (shape={frame.shape})')

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraPublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
