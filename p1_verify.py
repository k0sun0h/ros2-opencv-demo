#!/usr/bin/env python3
"""프로젝트 1 통합 검증 노드 (10/18)

ros2 CLI 는 데몬(_ros2_daemon)을 거쳐서 노드를 찾는다.
그런데 WSL2 미러링 모드에서 그 데몬이 hang 되는 문제가 있다
(ros2/ros2#1515: CLI 는 멈추지만 --no-daemon 이면 정상).

그래서 CLI 를 아예 쓰지 않고, 두 토픽을 '직접 구독해서' 메시지 개수를 센다.
노드와 똑같은 DDS 스택을 쓰므로 훨씬 정확하다.

사용법:
    source /opt/ros/humble/setup.bash
    python3 p1_verify.py 10        # 10초 동안 관찰

종료 코드:
    0 = 둘 다 정상
    1 = image_raw 가 안 옴 (발행/입력 문제)
    2 = image_raw 는 오는데 object/center 가 안 옴 (검출 문제)
"""
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point


class P1Verify(Node):
    def __init__(self):
        super().__init__('p1_verify')
        self.img_n = 0
        self.pt_n = 0
        self.img_times = []
        self.last_pt = None
        self.img_shape = None

        self.create_subscription(Image, '/camera/image_raw', self.on_img, 10)
        self.create_subscription(Point, '/object/center', self.on_pt, 10)

    def on_img(self, msg):
        self.img_n += 1
        self.img_times.append(time.time())
        if len(self.img_times) > 300:
            self.img_times.pop(0)
        if self.img_shape is None:
            self.img_shape = (msg.height, msg.width)

    def on_pt(self, msg):
        self.pt_n += 1
        self.last_pt = (msg.x, msg.y, msg.z)

    def stats(self):
        """평균 주기 / 평균 Hz / 최대 간격"""
        ts = self.img_times
        if len(ts) < 2:
            return None
        gaps = [b - a for a, b in zip(ts, ts[1:])]
        avg = sum(gaps) / len(gaps)
        return avg, (1.0 / avg if avg > 0 else 0.0), max(gaps)


def main():
    duration = 10.0
    if len(sys.argv) > 1:
        try:
            duration = float(sys.argv[1])
        except ValueError:
            pass

    rclpy.init(args=[])
    node = P1Verify()

    print(f'{duration:.0f}초 동안 두 토픽을 직접 구독해서 검증합니다... (Ctrl+C 로 중단)')
    end = time.time() + duration
    try:
        while time.time() < end:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        print('중단됨')

    print()
    print('=' * 54)
    print(' 프로젝트 1 통합 검증 결과')
    print('=' * 54)

    st = node.stats()
    if st:
        avg, hz, gap = st
        print(f'/camera/image_raw : {node.img_n}개   '
              f'평균 {hz:.1f} Hz (평균 간격 {avg:.3f}초, 최대 {gap:.3f}초)')
    else:
        print(f'/camera/image_raw : {node.img_n}개')

    if node.img_shape:
        print(f'                    해상도 {node.img_shape[1]}x{node.img_shape[0]}')
    print(f'/object/center    : {node.pt_n}개', end='')
    if node.last_pt:
        x, y, z = node.last_pt
        print(f'   마지막 ({x:.0f}, {y:.0f}, {z:.0f})')
    else:
        print()

    img_ok = node.img_n > 0
    pt_ok = node.pt_n > 0

    print()
    print('판정')
    print(f'  image_raw 발행  : {"OK" if img_ok else "FAIL"}')
    print(f'  object/center   : {"OK" if pt_ok else "FAIL"}')
    print()

    rc = 0
    if img_ok and pt_ok:
        print('>>> 통합 실행 성공')
    elif not img_ok:
        rc = 1
        print('>>> 실패 — /camera/image_raw 로 아무것도 안 옴')
        print('    원인 후보:')
        print('      1) 입력 노드가 안 떴다        → launch 로그 확인')
        print('      2) 영상/카메라를 못 열었다     → launch 로그에 "열기 실패" 확인')
        print('      3) DDS 로컬호스트 불일치       → export ROS_LOCALHOST_ONLY=1 확인')
    else:
        rc = 2
        print('>>> 실패 — 발행은 되는데 /object/center 가 안 옴 (검출 단계)')
        print('    원인 후보:')
        print('      1) 물체를 못 찾고 있다         → HSV 임계값 / min_area 확인')
        print('      2) object_tracker 가 안 떴다   → launch 로그 확인')

    node.destroy_node()
    rclpy.shutdown()
    return rc


if __name__ == '__main__':
    sys.exit(main())
