# OpenCV 시작 — 설치 / 이미지 입출력 / 카메라 입력 (10/13)

## 개념
- OpenCV = 이미지·영상을 "숫자 배열"로 다루는 라이브러리 (컴퓨터 비전 표준)
- 이미지 = 숫자 표
  - 흑백 : 높이 × 너비 개의 밝기(0~255)
  - 컬러 : 높이 × 너비 × 3 개의 숫자 (B,G,R)
- shape = (높이, 너비, 채널). 컬러는 채널 3, 흑백은 채널 없음
- OpenCV 색 순서는 RGB 가 아니라 BGR
- ROS2 연결 : sensor_msgs/Image 를 cv_bridge 로 OpenCV 배열로 변환 (10/16~)

## 설치
| 명령 | 하는 일 |
| --- | --- |
| sudo apt install -y python3-opencv | OpenCV (ROS2 python 과 같은 시스템 python 에 설치) |
| sudo apt install -y ros-humble-cv-bridge | ROS2 이미지 ↔ OpenCV 변환 브리지 |
- pip 대신 apt 를 쓰는 이유 : ROS2 Humble 도 시스템 python3(3.10) 사용 → 같은 python 에 맞춰야 충돌이 없다
- 검증 : python3 -c "import cv2; print(cv2.__version__)"

## 이미지 입출력
| 함수 | 하는 일 |
| --- | --- |
| cv2.imread(path) | 이미지 읽기 → 숫자 배열 (실패 시 None) |
| img.shape | (높이, 너비, 채널) |
| cv2.imshow(창이름, img) | 화면에 표시 |
| cv2.waitKey(0) | 키 입력까지 대기 (없으면 창이 바로 닫힘) |
| cv2.imwrite(path, img) | 저장 |
| cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) | 흑백으로 변환 |

```
import cv2

img = cv2.imread('test.jpg')
if img is None:
    print("이미지를 못 읽었어. 파일 이름/경로 확인!")
else:
    print("shape (높이, 너비, 채널):", img.shape)

    cv2.imshow('window', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cv2.imwrite('out_gray.png', gray)
```

## 카메라 입력
- cv2.VideoCapture(0) 로 카메라(또는 동영상) 열고, cap.read() 로 프레임 한 장씩
- 구조 : VideoCapture → read() 루프 → imshow → release()

```
import cv2

cap = cv2.VideoCapture(0)
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
```

- 카메라가 없어도 구조는 동일 → 가짜 프레임(numpy)으로 루프를 익힐 수 있다
- WSL2 는 기본적으로 USB 카메라를 못 본다 → usbipd-win 으로 장치를 넘겨야 /dev/video0 이 생긴다

## 실험 결과 (10/13 실제 관찰값)
- 설치 검증 : python3 -c "import cv2; print(cv2.__version__)" → 4.5.x 출력
- 이미지 입출력 : shape (300, 400, 3) 출력 + "저장 완료: out_gray.png"
  - (300, 400, 3) = np.zeros((300, 400, 3)) 로 만든 이미지와 정확히 일치 → 이미지 = 숫자 배열 증거
- 카메라 : ls /dev/video* → No such file or directory (WSL 에 USB 카메라 미연결)
- camera.py 실행 → [WARN:0] GStreamer/V4L2 경고 4줄 후 "카메라를 못 열었어!" (isOpened() 가 False 인 정상 분기)
- camera_fake.py 실행 → 노란 원이 좌우로 움직이는 창 확인 (카메라 루프 구조 체험)

## 자주 나는 함정
| 증상 | 원인 / 해결 |
| --- | --- |
| Command 'import' not found / syntax error near '(' | Python 코드를 터미널에 직접 붙여넣음 → 파일로 저장 후 python3 파일.py |
| imread 가 에러 없이 None | 파일이 없거나 경로가 다름 → if img is None 체크 필수 |
| 카메라를 못 열었어! + WARN | /dev/video0 없음 (WSL 미연결) → usbipd 로 연결하거나 가짜 프레임 사용 |
| 색이 RGB 와 다르게 보임 | OpenCV 는 BGR 순서 (RGB 아님) |

## 배운 점
- 이미지도 결국 숫자 배열 (10/11 의 LaserScan=숫자 배열, PointCloud2=이진 덩어리와 같은 결)
- Python 코드는 반드시 파일로 저장 후 실행 (터미널 직접 입력 X)
- OpenCV 색 순서는 BGR (10/8 image_raw 와 색이 뒤집혀 보이면 이 때문)
- 카메라 = VideoCapture → read() 루프 → release(). 장치가 없을 때(isOpened False)를 항상 처리
- 경로는 현재 위치 기준 (10/9 source, 10/11 bag 과 같은 종류의 함정)

## 어제(10/11)와의 연결
- 10/11 : 센서 데이터는 "숫자 배열 + header(frame_id)" 로 온다
- 10/13 : 그 숫자를 다루는 도구가 OpenCV. 이미지도 숫자 배열
- 다음(10/14~) : 색공간·이진화·필터링 → 윤곽 → 10/16~ cv_bridge 로 ROS2 이미지와 연결

## 실행
- python3 scripts/img_basic.py
- python3 scripts/camera.py        (카메라 있을 때)
- python3 scripts/camera_fake.py   (카메라 없을 때)
