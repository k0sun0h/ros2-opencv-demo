import math
import numpy as np
import cv2

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class FakeCameraPublisher(Node):
    """카메라 없이 가짜 프레임을 만들어 /camera/image_raw 로 발행한다."""

    def __init__(self):
        super().__init__('fake_camera_pub')
        self.pub = self.create_publisher(Image, '/camera/image_raw', 10)
        self.bridge = CvBridge()
        self.i = 0
        self.timer = self.create_timer(0.1, self.timer_callback)   # 10 Hz
        self.get_logger().info('가짜 카메라 발행 시작: /camera/image_raw')

    def make_frame(self, i):
        frame = np.zeros((420, 620, 3), np.uint8)
        frame[:] = (255, 255, 255)
        x = 80 + int(420 * (0.5 + 0.5 * math.sin(i / 8.0)))
        y = 210 + int(60 * math.sin(i / 6.0))
        cv2.circle(frame, (x, y), 25, (255, 0, 0), -1)     # BGR: 파란 공
        return frame

    def timer_callback(self):
        frame = self.make_frame(self.i)
        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')   # OpenCV -> ROS2
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera'
        self.pub.publish(msg)
        self.i += 1


def main(args=None):
    rclpy.init(args=args)
    node = FakeCameraPublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
