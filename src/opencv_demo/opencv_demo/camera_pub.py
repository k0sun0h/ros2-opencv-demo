import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class CameraPublisher(Node):
    """실제 USB 카메라를 열어 /camera/image_raw 로 발행한다.

    ★ 버그 수정 (10/18)
      - cv2.VideoCapture(device) → cv2.VideoCapture(device, cv2.CAP_V4L2)
        백엔드를 명시하지 않으면 WSL2 에서 출력 없이 멈춘다(hang).
      - device_id 를 문자열(by-id)로 지정 가능하게. 재attach 마다 번호가 바뀌므로 by-id 가 안전.
        숫자 문자열('0')은 그대로 인덱스로 변환해 하위 호환.
      - fps 파라미터를 실제 캡처에 적용 (전에는 타이머에만 쓰였음).
      - 로그에 실제로 열린 장치/해상도/fps 를 찍는다 (요청값이 아니라 '읽어온 값').
    """

    def __init__(self):
        super().__init__('camera_pub')

        self.declare_parameter(
            'device_id',
            '/dev/v4l/by-id/usb-Generic_Web_Camera_200901010001-video-index0')
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 10.0)
        self.declare_parameter('frame_id', 'camera')

        raw = self.get_parameter('device_id').value
        # '0' 처럼 숫자면 인덱스로, 그 외에는 경로 문자열로 쓴다
        self.device = int(raw) if str(raw).strip().isdigit() else str(raw)

        width = int(self.get_parameter('width').value)
        height = int(self.get_parameter('height').value)
        fps = float(self.get_parameter('fps').value)
        self.frame_id = self.get_parameter('frame_id').value

        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, '/camera/image_raw', 10)

        # ★ 백엔드 명시 — 없으면 조용히 멈춘다
        self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        if width > 0:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height > 0:
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if fps > 0:
            self.cap.set(cv2.CAP_PROP_FPS, fps)

        if not self.cap.isOpened():
            self.get_logger().error(
                f'카메라를 열 수 없음: {self.device}  '
                '(usbipd attach 확인 / sudo usermod -aG video $USER 후 WSL 재시작)')
        else:
            # 요청값이 아니라 실제 적용된 값을 읽어서 로그로 남긴다
            got_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            got_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            got_fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.get_logger().info(
                f'카메라 열기 성공: {self.device} '
                f'({got_w}x{got_h}, {got_fps:.1f} fps) — 요청 {width}x{height} @ {fps}')

        self.n = 0
        self.fail = 0
        self.timer = self.create_timer(1.0 / fps if fps > 0 else 0.1, self.timer_callback)

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
