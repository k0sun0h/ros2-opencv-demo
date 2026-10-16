# opencv_demo — ROS2 + OpenCV 물체 추적 실습

ROS2 Humble에서 **cv_bridge**로 OpenCV를 연결해, 카메라 이미지에서 색으로 물체를 찾고
그 **중심 좌표를 토픽으로 발행**하는 학습용 패키지입니다.

## 1. 무엇을 하는가

| 노드 | 하는 일 | 토픽 |
|---|---|---|
| `image_pub` | 이미지를 만들어 발행 (현재는 **카메라 없이 가짜 프레임**, 10 Hz) | 발행 `/camera/image_raw` |
| `object_tracker` | 이미지를 받아 색 분리 → 최대 윤곽의 중심 계산 | 구독 `/camera/image_raw`, 발행 `/object/center` |

```
[image_pub] --/camera/image_raw--> [object_tracker] --/object/center--> (확인용)
```

- `cv_bridge` 를 **양방향**으로 사용: `cv2_to_imgmsg` (OpenCV→ROS2), `imgmsg_to_cv2` (ROS2→OpenCV)
- 색 분리는 OpenCV **BGR → HSV** 변환 후 `inRange` (파랑 H 90~130)
- 중심은 윤곽의 **모멘트**(`M['m10']/M['m00']`)로 계산
- `scripts/` 폴더는 ROS 없이 OpenCV만 연습한 파일들입니다 (색공간·윤곽·추적).

## 2. 요구사항

| 항목 | 값 |
|---|---|
| OS | WSL2 Ubuntu 22.04 |
| ROS2 | Humble |
| Python | 3.10 (ROS2 시스템 파이썬) |
| OpenCV | apt `python3-opencv` (pip 아님 — ROS2 파이썬과 맞추기 위해) |

```bash
sudo apt install -y ros-humble-cv-bridge python3-opencv
```

## 3. 빌드

```bash
cd ~/ros2-opencv-demo
source /opt/ros/humble/setup.bash
colcon build --packages-select opencv_demo
source install/setup.bash          # 워크스페이스 루트에서만 동작 (상대경로)
```

## 4. 실행 (터미널 3개)

**터미널 1 — 이미지 발행**
```bash
source /opt/ros/humble/setup.bash
cd ~/ros2-opencv-demo && source install/setup.bash
ros2 run opencv_demo image_pub
```

**터미널 2 — 물체 추적**
```bash
source /opt/ros/humble/setup.bash
cd ~/ros2-opencv-demo && source install/setup.bash
ros2 run opencv_demo object_tracker
```

**터미널 3 — 결과 확인**
```bash
source /opt/ros/humble/setup.bash
cd ~/ros2-opencv-demo && source install/setup.bash
ros2 topic echo /object/center
ros2 topic hz /camera/image_raw
```

## 5. 토픽 구조

| 토픽 | 타입 | 주기 | 내용 |
|---|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | 10 Hz | `encoding=bgr8`, `frame_id=camera`, 420x620 |
| `/object/center` | `geometry_msgs/Point` | 검출 시 | `x,y` = 물체 중심 픽셀 좌표, `z` = 0 (미사용) |

## 6. 검증 결과 (실측)

| 항목 | 값 |
|---|---|
| 검출 로그 | `물체 중심=(390,247) 면적=1886` |
| 중심 x 범위 | 82 ~ 497 (이론 80~500) |
| 중심 y 범위 | 151 ~ 269 (이론 150~270) |
| 발행 주기 | 약 10 Hz |
| 공 면적 | 1886 (이론 1963 — 이진화 경계로 약간 작음) |

## 7. 자주 나는 함정

- `source install/setup.bash` 는 **상대경로** → 반드시 워크스페이스 **루트**에서 실행
- `source /opt/ros/humble/setup.bash` 는 **터미널(셸)마다** 필요 (환경변수는 셸마다 별개)
- OpenCV 색 순서는 **BGR** — `(255,0,0)` 은 파랑이 아니라 **빨강**
- HSV의 H는 **0~180** (일반적인 0~360이 아님)
- `cv2.waitKey(0)` 은 **무한 대기** — 키를 눌러야 다음으로 넘어감
- `cv2.putText` 는 **ASCII만** 지원 → 한글은 `????` 로 나옴 (PIL `ImageDraw` 로 대체)

## 8. 현재 상태 / 다음 단계

- [x] OpenCV 처리 (HSV 이진화 → 윤곽 → 중심)
- [x] ROS2 노드 pub/sub + cv_bridge 연결
- [x] 수동 실행 검증 (3터미널)
- [ ] **실제 USB 카메라 입력** (`usbipd-win` 으로 WSL에 연결) — 현재는 가짜 프레임
- [ ] launch 파일로 3터미널 통합
- [ ] HSV 임계값 파라미터화
