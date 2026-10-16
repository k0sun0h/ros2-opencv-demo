import numpy as np
import cv2

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point
from cv_bridge import CvBridge


class ObjectTracker(Node):
    """이미지를 구독해 물체의 중심을 찾아 /object/center 로 발행한다.

    show_debug=true 이면 'frame'(원본+검출 표시) 과 'mask' 창을 띄운다.
    HSV 임계값 / 최소 면적은 파라미터로 바꿀 수 있다.
    """

    def __init__(self):
        super().__init__('object_tracker')
        self.bridge = CvBridge()

        self.declare_parameter('h_min', 90)
        self.declare_parameter('h_max', 130)
        self.declare_parameter('s_min', 100)
        self.declare_parameter('v_min', 100)
        self.declare_parameter('min_area', 100)
        self.declare_parameter('show_debug', True)

        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self.image_callback, 10)
        self.pub = self.create_publisher(Point, '/object/center', 10)
        self.n = 0
        self.miss = 0
        self.get_logger().info('구독: /camera/image_raw  ->  발행: /object/center')

    def _read_params(self):
        g = self.get_parameter
        lower = np.array([g('h_min').value, g('s_min').value, g('v_min').value])
        upper = np.array([g('h_max').value, 255, 255])
        return lower, upper, g('min_area').value, g('show_debug').value

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        lower, upper, min_area, show = self._read_params()

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        found = False
        if cnts:
            c = max(cnts, key=cv2.contourArea)      # 가장 큰 덩어리 = 물체
            area = cv2.contourArea(c)
            if area >= min_area:
                M = cv2.moments(c)
                if M['m00'] != 0:
                    cx, cy = int(M['m10'] / M['m00']), int(M['m01'] / M['m00'])

                    p = Point()
                    p.x = float(cx)
                    p.y = float(cy)
                    p.z = 0.0
                    self.pub.publish(p)
                    found = True

                    self.n += 1
                    if self.n % 5 == 0:             # 5프레임마다 로그
                        self.get_logger().info(
                            f'물체 중심=({cx},{cy}) 면적={area:.0f}')

                    if show:
                        cv2.drawContours(frame, [c], -1, (0, 0, 255), 2)
                        cv2.circle(frame, (cx, cy), 6, (0, 255, 0), -1)
                        cv2.putText(frame, f'({cx},{cy}) area={int(area)}',
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.7, (0, 255, 255), 2)

        if found:
            self.miss = 0
        else:
            self.miss += 1
            if self.miss % 20 == 1:                 # 로그 폭주 방지
                self.get_logger().warn(f'물체를 못 찾음 ({self.miss}회 연속)')

        if show:
            h, w = frame.shape[:2]
            # 화면 중앙 십자선 — 물체를 여기에 맞춰라
            cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 0, 255), 1)
            cv2.line(frame, (0, h // 2), (w, h // 2), (255, 0, 255), 1)
            cv2.putText(frame, 'aim here', (w // 2 + 8, h // 2 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
            cv2.imshow('frame', frame)
            cv2.imshow('mask', mask)
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
