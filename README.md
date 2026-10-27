# opencv_demo — ROS2 Humble + OpenCV 물체 추적

카메라(또는 영상 파일) 영상에서 **색(HSV)으로 물체를 찾아 중심 좌표를 토픽으로 발행**하는 최소 예제.
ROS2 의 pub/sub 구조를 익히는 것이 목적이라, **입력원을 바꿔도 뒤 단계는 코드 수정 없이** 그대로 동작한다.

```
[입력 노드]  --/camera/image_raw-->  [object_tracker]  --/object/center-->
  image_pub (가짜 프레임)             cv_bridge → HSV 마스크
  camera_pub (USB 카메라)                       → 윤곽 → 중심
  video_pub  (영상 파일)
```

| 토픽 | 타입 | 방향 |
|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | 발행 |
| `/object/center` | `geometry_msgs/Point` | 발행 (`x=cx, y=cy, z=0`) |

## 요구사항

| 항목 | 값 |
|---|---|
| ROS2 | Humble |
| 패키지 | `ros-humble-cv-bridge`, `python3-opencv` |
| Python | `rclpy`, `cv_bridge`, `opencv-python`, `numpy` |
| 카메라(선택) | WSL2 + `usbipd-win` 으로 `/dev/video*` 노출 |

## 빌드

```bash
cd ~/ros2-opencv-demo
source /opt/ros/humble/setup.bash
colcon build --packages-select opencv_demo
source install/setup.bash
```

## 실행 — 입력원 3가지

노드는 `source` 인자 하나로 고른다 (**상호 배타를 구조로 보장**).

```bash
# 1) 가짜 프레임 (카메라 없이 개발)
ros2 launch opencv_demo track.launch.py

# 2) 실제 USB 카메라
ros2 launch opencv_demo track.launch.py source:=camera

# 3) 영상 파일 (usbipd 등시성 한계 우회)
ros2 launch opencv_demo track.launch.py source:=video \
  video_path:="/mnt/c/Users/kimsu/OneDrive/사진/카메라 앨범/test.mp4" \
  show_debug:=true
```

> launch 인자는 **`인자:=값`** 형태다. `use_camera` 같은 2지선다 인자는 더 이상 쓰지 않는다.

## 자동 검증

`ros2` CLI 는 데몬(`_ros2_daemon`)을 거치는데, WSL2 미러링 모드에서 그 데몬이 멈추는 문제가 있다.
그래서 검증은 **토픽을 직접 구독하는 노드**로 한다.

```bash
# launch + 검증을 한 번에
bash check_pipeline.sh video "/mnt/c/Users/kimsu/OneDrive/사진/카메라 앨범/test.mp4"

# 검증 노드만 따로
python3 p1_verify.py 12
```

`p1_verify.py` 종료 코드

| 코드 | 뜻 |
|---|---|
| `0` | 둘 다 정상 |
| `1` | `/camera/image_raw` 가 안 옴 (입력/발행 문제) |
| `2` | 발행은 되는데 `/object/center` 가 안 옴 (검출 문제) |

CLI 로 확인할 때는 **`--no-daemon`** 을 붙인다.

```bash
ros2 node list --no-daemon
ros2 topic list --no-daemon
```

## launch 인자

| 인자 | 기본값 | 설명 |
|---|---|---|
| `source` | `fake` | `fake` \| `camera` \| `video` |
| `video_path` | `''` | `source:=video` 일 때 읽을 파일 (loop 재생) |
| `device_id` | `/dev/v4l/by-id/usb-Generic_Web_Camera_200901010001-video-index0` | 숫자(`0`)도 허용 — 재attach 시 번호가 바뀌므로 **by-id 권장** |
| `width` / `height` | `640` / `480` | 카메라 해상도 |
| `fps` | `10.0` | 캡처·발행 주기 |
| `h_min` / `h_max` | `90` / `130` | HSV 색 범위 (H는 0~180) |
| `s_min` / `v_min` | `100` / `100` | 채도·밝기 최소 |
| `min_area` | `100` | 물체로 인정할 최소 면적 |
| `show_debug` | `true` | `frame` / `mask` 창 표시 (`DISPLAY` 없으면 자동 해제) |

`object_tracker` 의 `frame` 창에는 **마젠타 십자선**이 있어 물체를 화면 중앙에 맞추기 쉽다.

## 검증 결과 (10/18)

`source:=video`, 12초 관찰, `ROS_LOCALHOST_ONLY=1`

| 지표 | 값 |
|---|---|
| `/camera/image_raw` | 120개 / **10.0 Hz** (평균 간격 0.100초, 최대 0.116초) |
| 해상도 | 640x480 |
| `/object/center` | 119개 (**검출률 99%**) |
| 판정 | **image_raw OK / object/center OK** |

```
>>> 통합 실행 성공
```

## 자주 나는 함정

| # | 함정 | 해결 |
|---|---|---|
| 1 | `cv2.VideoCapture(0)` 자동 백엔드 → **출력 없이 멈춤** | `cv2.VideoCapture(dev, cv2.CAP_V4L2)` 로 명시 |
| 2 | 재attach 후 장치 번호가 바뀜 | `/dev/v4l/by-id/...` 사용 |
| 3 | `DISPLAY` 없이 `cv2.imshow` → 노드 죽음 | 헤드리스면 `show_debug:=false` (수정본은 자동 해제) |
| 4 | `ros2` CLI 가 전부 hang | `--no-daemon` 또는 `p1_verify.py` |
| 5 | 미러링 모드에서 DDS 발견 실패 | `ROS_LOCALHOST_ONLY=1` (launch 안에 내장) |
| 6 | `set -u` + ROS2 `setup.bash` → `unbound variable` | 스크립트에서 `set -u` 쓰지 않기 |
| 7 | launch 인자를 `=` 로 씀 | **`:=`** 형태로 |
| 8 | 로그가 프레임률에 따라 폭주 | 로그를 **시간 기준**(1초에 한 번)으로 |

## 알려진 한계 — usbipd 등시성 전송

실기기 USB 카메라(`source:=camera`)는 **영상이 초록으로 깨진다.**

- USB 카메라 영상은 **등시성(isochronous) 전송**만 쓰는데(재전송 없음), `usbipd` 가 이를 중계하지 못하고 계속 리셋한다
- 증거: `dmesg | grep vhci` → `urb->status -104` (ECONNRESET) 반복
- 해상도를 최저(160x120)로 낮춰도 남는다 → **대역폭 문제가 아니다**
- 관련 이슈: [usbipd-win#530](https://github.com/dorssel/usbipd-win/issues/530), [#658](https://github.com/dorssel/usbipd-win/issues/658), [#1006](https://github.com/dorssel/usbipd-win/issues/1006)
- **우회**: Windows 에서 녹화한 영상을 `source:=video` 로 입력 (뒤 단계 코드 수정 0줄)

## 파일

| 경로 | 역할 |
|---|---|
| `src/opencv_demo/opencv_demo/image_pub.py` | 가짜 프레임 발행 |
| `src/opencv_demo/opencv_demo/camera_pub.py` | USB 카메라 발행 (`CAP_V4L2`, by-id) |
| `src/opencv_demo/opencv_demo/video_pub.py` | 영상 파일 발행 (loop) |
| `src/opencv_demo/opencv_demo/object_tracker.py` | 물체 중심 검출·발행 |
| `src/opencv_demo/launch/track.launch.py` | 통합 실행 (입력원 스위치) |
| `p1_verify.py` | 통합 검증 (토픽 직접 구독) |
| `check_pipeline.sh` | 실행 + 검증 자동화 |
| `notes/` | 학습 노트 |

## 2D 매핑 (slam_demo)

라이다 스캔만으로 방의 지도를 그리는 실습. 가짜 로봇이 방(8×6m)을 돌며
`/scan` 을 발행하고 `slam_toolbox` 가 격자 지도를 만든다.

```bash
cd slam_demo
bash run_slam_demo.sh 20          # 20초 검증
bash save_map_demo_v2.sh 90 room  # 90초 매핑 + 지도 저장
```

결과: `room.pgm` 189×163 @ 0.05m, 방 커버리지 96.65%, `/scan` 5.0Hz.

주요 결론 3개 — ①볼록한 방에서는 오래 돌려도 커버리지가 늘지 않는다(경로가 지도를 결정)
②WSL2 mirrored 환경에서 **노드 2개 구성은 통신이 깨진다**, 3개면 정상
③`ros2 topic hz` 같은 CLI 측정은 이 환경에서 거짓 실패를 낸다.

자세한 실행법·파라미터·실험 기록은 [`slam_demo/README.md`](slam_demo/README.md).
