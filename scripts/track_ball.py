import cv2
import numpy as np
import math

# 카메라 없이 "프레임"을 직접 만들어 프레임 간 추적을 익힌다
W, H = 620, 420
TRAIL = []                      # 공이 지나간 중심 좌표들

for i in range(60):             # 60 프레임
    frame = np.zeros((H, W, 3), np.uint8)
    frame[:] = (255, 255, 255)

    # 공 위치: 오른쪽으로 이동 + 위아래로 물결
    x = 60 + i * 8
    y = 210 + int(60 * math.sin(i / 6.0))
    cv2.circle(frame, (x, y), 25, (255, 0, 0), -1)     # 파란 공

    # 색 마스크 -> 윤곽 -> 중심
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([90, 100, 100]), np.array([130, 255, 255]))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    cx = cy = None
    if cnts:
        c = max(cnts, key=cv2.contourArea)     # 가장 큰 덩어리 = 공
        M = cv2.moments(c)
        if M['m00'] != 0:
            cx, cy = int(M['m10'] / M['m00']), int(M['m01'] / M['m00'])
            TRAIL.append((cx, cy))

    if i % 10 == 0:
        print(f"프레임 {i:2d} : 그린 위치=({x},{y})  검출 중심=({cx},{cy})")

    # 지나온 길(궤적) 그리기
    for p in range(1, len(TRAIL)):
        cv2.line(frame, TRAIL[p - 1], TRAIL[p], (0, 0, 255), 2)
    if cx is not None:
        cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

    cv2.imshow('track_ball', frame)
    if cv2.waitKey(50) & 0xFF == ord('q'):
        break

cv2.waitKey(0)
cv2.destroyAllWindows()
