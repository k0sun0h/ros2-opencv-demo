import numpy as np
import cv2

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point
from cv_bridge import CvBridge


class ObjectTracker(Node):
    """이미지를 구독해 물체의 중심을 찾아 /object/center 로 발행한다.

    HSV 임계값과 최소 면적은 파라미터로 바꿀 수 있다 (launch 파일 또는 CLI).
    """

    def __init__(self):
        super().__init__('object_tracker')
        self.bridge = CvBridge()

        # --- 파라미터 선언 (기본값 = 지금까지 검증한 값) ---
        self.declare_parameter('h_min', 90)
        self.declare_parameter('h_max', 130)
        self.declare_parameter('s_min', 100)
        self.declare_parameter('v_min', 100)
        self.declare_parameter('min_area', 100)

        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10)
        self.pub = self.create_publisher(Point, '/object/center', 10)
        self.n = 0
        self.get_logger().info('구독: /camera/image_raw  ->  발행: /object/center')

    def _read_params(self):
        g = self.get_parameter
        lower = np.array([g('h_min').value, g('s_min').value, g('v_min').value])
        upper = np.array([g('h_max').value, 255, 255])
        return lower, upper, g('min_area').value

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')  # ROS2 -> OpenCV
        lower, upper, min_area = self._read_params()

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            self.get_logger().warn('물체를 못 찾음')
            return

        c = max(cnts, key=cv2.contourArea)          # 가장 큰 덩어리 = 물체
        area = cv2.contourArea(c)
        if area < min_area:                         # 작은 티끌 버림
            return
        M = cv2.moments(c)
        if M['m00'] == 0:
            return
        cx, cy = int(M['m10'] / M['m00']), int(M['m01'] / M['m00'])

        p = Point()
        p.x = float(cx)
        p.y = float(cy)
        p.z = 0.0
        self.pub.publish(p)

        self.n += 1
        if self.n % 5 == 0:                         # 5프레임마다 로그 (소음 줄이기)
            self.get_logger().info(f'물체 중심=({cx},{cy}) 면적={area:.0f}')

        cv2.imshow('mask', mask)                    # 눈으로 확인용
        cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = ObjectTracker()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
