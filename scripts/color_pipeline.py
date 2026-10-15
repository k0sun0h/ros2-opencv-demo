import cv2
import numpy as np

img = cv2.imread('test.jpg')
if img is None:
    print("이미지를 못 읽었어!")
    raise SystemExit

# 1) 색공간 변환 + 마스크 (파란색 찾기)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
lower = np.array([90, 100, 100])
upper = np.array([130, 255, 255])
mask = cv2.inRange(hsv, lower, upper)

# 2) 필터링 (작은 점 제거)
kernel = np.ones((5, 5), np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

# 3) 이진화
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
ret, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
print("Otsu 자동 기준값:", ret)

# 4) 결과 보기
cv2.imshow('mask', mask)
cv2.imshow('binary', bw)
cv2.waitKey(0)
cv2.destroyAllWindows()
