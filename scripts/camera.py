import cv2

cap = cv2.VideoCapture(0)        # ← 지금은 카메라 없어서 isOpened()가 False
if not cap.isOpened():
    print("카메라를 못 열었어! (WSL이면 usbipd 확인)")
else:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow('camera', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
