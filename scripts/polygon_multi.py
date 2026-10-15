import cv2
import numpy as np

# ===== 도형 5개 + 노이즈 점 1개 만들기 =====
img = np.zeros((420, 620, 3), np.uint8)
img[:] = (255, 255, 255)

RED = (0, 0, 255); GREEN = (0, 255, 0); BLUE = (255, 0, 0); YELLOW = (0, 255, 255)

# 빨강 삼각형
cv2.fillPoly(img, [np.array([[100, 50], [40, 170], [160, 170]], np.int32)], RED)
# 초록 정사각형
cv2.rectangle(img, (240, 50), (360, 170), GREEN, -1)
# 파랑 원
cv2.circle(img, (480, 110), 60, BLUE, -1)
# 노랑 오각형 (72도씩 5점)
pent = []
import math
for k in range(5):
    a = math.radians(-90 + k * 72)
    pent.append([int(110 + 70 * math.cos(a)), int(310 + 70 * math.sin(a))])
cv2.fillPoly(img, [np.array(pent, np.int32)], YELLOW)
# 파랑 작은 사각형 (같은 색 물체 2개)
cv2.rectangle(img, (250, 280), (310, 340), BLUE, -1)
# 초록 작은 점 (노이즈)
cv2.circle(img, (450, 350), 5, GREEN, -1)

cv2.imwrite('poly_multi.jpg', img)

# ===== 색 범위 4개 =====
RANGES = {
    "빨강": ((0, 100, 100), (10, 255, 255)),
    "초록": ((40, 100, 100), (80, 255, 255)),
    "파랑": ((90, 100, 100), (130, 255, 255)),
    "노랑": ((25, 100, 100), (35, 255, 255)),
}

hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
kernel = np.ones((5, 5), np.uint8)
out = img.copy()

def classify(c, area, circ):
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.02 * peri, True)   # 꼭짓점 몇 개로 단순화되는가
    n = len(approx)
    if n == 3: return "삼각형", approx
    if n == 4: return "사각형", approx
    if circ >= 0.85: return "원", approx
    return f"{n}각형", approx

print("=== 색깔별 물체 찾기 (다중 검출) ===")
for cname, (lo, hi) in RANGES.items():
    mask = cv2.inRange(hsv, np.array(lo), np.array(hi))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    found = 0
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 100:            # 노이즈 점 버림
            continue
        peri = cv2.arcLength(c, True)
        circ = 4 * math.pi * area / (peri * peri)
        M = cv2.moments(c)
        if M['m00'] == 0:
            continue
        cx, cy = int(M['m10'] / M['m00']), int(M['m01'] / M['m00'])
        shape, approx = classify(c, area, circ)

        print(f"[{cname}] 면적={area:7.0f} 중심=({cx:3d},{cy:3d}) "
              f"원형도={circ:.3f} 꼭짓점={len(approx)}개 -> {shape}")

        cv2.drawContours(out, [c], -1, (0, 0, 255), 2)
        cv2.polylines(out, [approx], True, (255, 0, 255), 2)   # 근사 다각형 = 보라
        cv2.circle(out, (cx, cy), 4, (0, 255, 0), -1)
        cv2.putText(out, f"{cname} {shape}", (cx - 60, cy - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        found += 1
    print(f"   -> {cname} 물체 {found}개")

cv2.imshow('polygon_multi', out)
cv2.waitKey(0)
cv2.destroyAllWindows()
