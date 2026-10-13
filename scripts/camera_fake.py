import cv2, numpy as np

# 진짜 카메라 대신 매 프레임을 직접 만든다 (구조는 카메라와 동일)
cap_like = 0
while cap_like < 100:
    frame = np.zeros((300, 400, 3), dtype=np.uint8)
    x = 20 + (cap_like * 3) % 300
    cv2.circle(frame, (x, 150), 40, (0, 255, 255), -1)   # 노란 원이 이동
    cv2.imshow('camera(fake)', frame)
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break
    cap_like += 1

cv2.destroyAllWindows()
