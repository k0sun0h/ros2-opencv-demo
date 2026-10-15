import cv2
import numpy as np

# 1) 연습용 이미지 만들기 (파란 도형 3개 + 작은 점 1개)
img = np.zeros((400, 600, 3), np.uint8)
img[:] = (255, 255, 255)                                   # 흰 배경

blue = (200, 80, 60)                                       # BGR: B=200 → 진짜 파랑
cv2.circle(img, (150, 120), 70, blue, -1)                  # 큰 원
cv2.rectangle(img, (330, 60), (500, 190), blue, -1)        # 사각형
cv2.circle(img, (140, 300), 35, blue, -1)                  # 작은 원
cv2.circle(img, (400, 320), 6, blue, -1)                   # 아주 작은 점(노이즈)
cv2.imwrite('shapes.jpg', img)

# 2) 색 마스크 (10/14 에 배운 것)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, np.array([90, 100, 100]), np.array([130, 255, 255]))

# 3) 노이즈 정리 (open = 작은 점 제거)
kernel = np.ones((5, 5), np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

# 4) ★ 윤곽 검출
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print("찾은 윤곽 개수:", len(contours))

# 5) 윤곽마다 특징 계산 + 그리기
out = img.copy()
for i, c in enumerate(contours):
    area = cv2.contourArea(c)
    if area < 100:                    # 작은 티끌 버림
        continue
    peri = cv2.arcLength(c, True)
    circ = 4 * np.pi * area / (peri * peri)   # 원형도 (1에 가까우면 원)
    M = cv2.moments(c)
    if M['m00'] == 0:
        continue
    cx, cy = int(M['m10'] / M['m00']), int(M['m01'] / M['m00'])
    x, y, w, h = cv2.boundingRect(c)

    print(f"[{i}] 면적={area:.0f}, 둘레={peri:.0f}, 중심=({cx},{cy}), "
          f"원형도={circ:.2f}, 박스=({x},{y},{w},{h})")

    cv2.drawContours(out, [c], -1, (0, 0, 255), 3)   # 윤곽선 = 빨강
    cv2.circle(out, (cx, cy), 5, (0, 255, 0), -1)    # 중심 = 초록 점
    cv2.rectangle(out, (x, y), (x + w, y + h), (255, 0, 0), 2)  # 외접 박스 = 파랑

cv2.imshow('mask', mask)
cv2.imshow('contours', out)
cv2.waitKey(0)
cv2.destroyAllWindows()
