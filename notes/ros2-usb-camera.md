# USB 카메라 연결 — usbipd-win + uvcvideo (10/17)

> 계획표 기준일 10/17. **10/16(금)에 하루 앞당겨 진행**했다.
> 결과물: `39bb156 feat: USB 카메라 노드 + launch use_camera 스위치 + 영상파일 입력(video_pub)`

## 개념

Windows에 꽂힌 USB 카메라를 WSL2 안에서 `/dev/video*` 으로 쓰려면 **네 겹**을 통과해야 한다.

| 겹 | 무엇 | 왜 필요한가 |
|---|---|---|
| ① 공유 | `usbipd bind` | Windows가 장치를 USB/IP 서버로 내보냄 (한 번만, 재부팅에도 유지) |
| ② 연결 | `usbipd attach --wsl` | WSL VM이 그 장치를 가져감 (**재시작마다 풀림**) |
| ③ 네트워크 | WSL ↔ Windows TCP 3240 | attach 자체가 네트워크로 이뤄짐 |
| ④ 드라이버 | `uvcvideo` 커널 모듈 | USB로 온 영상을 V4L2 장치로 만들어 `/dev/video*` 생성 |

**핵심 구조**

```
[USB 카메라] → Windows (usbipd 서비스, TCP 3240)
                    ↓ attach
              WSL2 VM 커널 (vhci_hcd → uvcvideo)
                    ↓
              /dev/video*  →  cv2.VideoCapture  →  ROS2 Image 토픽
```

**용어**

| 용어 | 뜻 |
|---|---|
| USB/IP | USB 장치를 네트워크로 전송하는 프로토콜 |
| `bind` / `attach` | 내보내기(영구) / 가져오기(휘발성) |
| UVC | USB Video Class — 웹캠 표준 규격 (드라이버 불필요한 장치) |
| V4L2 | Linux Video4Linux2 — 리눅스의 카메라 인터페이스 |
| `vhci_hcd` | USB/IP 가상 호스트 컨트롤러 (WSL 쪽 수신부) |

## 실험 결과

**환경**

| 항목 | 값 |
|---|---|
| Windows | 11 25H2 (빌드 26200.9711), **Home** 에디션 |
| WSL | 3.0.3.0 |
| 커널 | **6.18.54.1-microsoft-standard-WSL2** (업데이트 전 5.15.167.4) |
| 네트워크 모드 | **mirrored** (변경 전 nat) |
| 카메라 | `2232:1080 Silicon Motion Web Camera` (BUSID `2-5`) |
| OpenCV | 4.5.4 (apt `python3-opencv`) |

**단계별 확인**

| 단계 | 명령 | 결과 |
|---|---|---|
| 공유 | `usbipd bind --busid 2-5` | STATE `Shared` |
| 연결 | `usbipd attach --wsl --busid 2-5` | `Detected networking mode 'mirrored'`, warning 없음 |
| USB 인식 | `lsusb` | `2232:1080 Silicon Motion Web Camera` |
| 드라이버 | `modinfo uvcvideo` | `uvcvideo.ko` version 1.1.1 |
| 로그 | `dmesg` | `uvcvideo 1-1:1.0: Found UVC 1.00 device Web Camera (2232:1080)` |
| 장치 노드 | `ls /dev/video*` | `/dev/video0`, `/dev/video1` |
| 장치 정보 | `v4l2-ctl --list-devices` | `Web Camera: /dev/video0, /dev/video1, /dev/media0` |

**카메라 열기**

```
--- /dev/video0 ---
isOpened: True
read: True (480, 640, 3)
--- /dev/video1 ---
can't open camera by index      ← 정상 (메타데이터 전용)
```

**ROS2 노드 검증 (단일 노드)**

```
[camera_pub-1] 카메라 열기 성공: /dev/video0 (640x480)
[camera_pub-1] 50 프레임 발행 (shape=(480, 640, 3))
[camera_pub-1] 400 프레임 발행 (shape=(480, 640, 3))

$ ros2 topic hz /camera/image_raw
average rate: 약 8 Hz      ← 타이머 10 Hz 대비 정상
```

| 항목 | 값 |
|---|---|
| 노드 | `/camera_pub` |
| 토픽 | `/camera/image_raw` (Image) |
| 해상도 | 640x480 (shape `(480, 640, 3)`) |

## 막힌 것 ① — 영상이 초록으로 깨진다

**증상**: `frame` 창이 초록으로 덮이고 상단 2~4%만 실제 영상. `mask` 는 전부 검정.

**원인**: 이 카메라는 **MJPG(압축)를 지원하지 않고 YUYV(비압축)만** 지원한다.

```
$ v4l2-ctl -d /dev/video1 --list-formats
        [0]: 'YUYV' (YUYV 4:2:2)      ← MJPG 없음!
                Size: 640x480, 320x240, 160x120, 352x288
                Interval: 30.000 fps
```

**대역폭 계산**

| 해상도/포맷 | 대역폭 | USB/IP 통과 |
|---|---|---|
| 640x480 YUYV @ 30fps | 18.4 MB/s | ❌ 유실 |
| 640x480 YUYV @ 10fps | 6.1 MB/s | ❌ 유실 |
| 320x240 YUYV @ 10fps | 1.5 MB/s | ⚠️ 일부만 |
| 160x120 YUYV @ 10fps | **0.4 MB/s** | ❌ **여전히 71.7% 초록** |

**초록색의 정체**: YUV `(Y=0, U=0, V=0)` 을 RGB로 변환하면

```
G = 0 − 0.344×(0−128) − 0.714×(0−128) = +135   →   RGB(0,135,0) = 초록
```

즉 **초록 = 채워지지 않은 빈 버퍼**. 카메라가 초록을 보내는 게 아니라 **프레임이 끝까지 전송되지 못한 것**이다.

**실측**

| 도구 | 결과 |
|---|---|
| `ffmpeg` (160x120~640x480) | ❌ 전부 `Terminated` (타임아웃) |
| OpenCV (320x240) | ✅ `opened: True` / `read: True (240, 320, 3)` |

> **320x240 으로 낮추면 `read` 는 성공**하지만, 화면은 여전히 초록이었다. `read: True` 가 "영상이 정상"이라는 뜻은 아니다 — **열렸고 버퍼가 왔다는 뜻일 뿐**이다.

## 막힌 것 ② — usbipd 등시성 전송 한계 (해결 불가)

**해상도를 낮춰도 초록이 남는다.**

| 해상도 | 대역폭 | 초록(빈 버퍼) 비율 |
|---|---|---|
| 640x480 | 18.4 MB/s | ~97% |
| 320x240 | 1.5 MB/s | ~88% |
| **160x120** | **0.4 MB/s** | **71.7%** |

**160x120(0.4 MB/s)에서도 71.7%가 초록** → **대역폭 문제가 아니다.**

**시도했지만 효과 없던 것**

| 시도 | 결과 |
|---|---|
| `usbfs_memory_mb` 16 → 1000 | 초록 그대로 |
| `uvcvideo nodrop=1` | 초록 그대로 |
| 해상도 160x120 (최저) | 초록 71.7% |
| `usbipd detach/attach` 반복 | 초록 그대로 |

**진짜 원인 — `dmesg` 의 결정적 증거**

```
[vhci_hcd] unlink->seqnum 54187
[vhci_hcd] urb->status -104      ← ECONNRESET (연결 리셋)
[vhci_hcd] urb->status -104      ← 수십~수백 회 반복
```

USB 카메라 영상은 **등시성(isochronous) 전송**만 사용한다(재전송 없음).
usbipd 는 이 등시성 URB 를 **정상 중계하지 못하고 계속 리셋**(-104)한다.
→ **프레임 앞부분만 도착**하고 나머지가 빈 버퍼(=초록)로 남는다.

**증거: 해상도와 무관하게 도착량이 일정**

| 해상도 | 프레임 크기 | 실제 도착(추정) |
|---|---|---|
| 640x480 | 614,400 B | ~4% = 약 20~25 KB |
| 320x240 | 153,600 B | ~12% = 약 18 KB |
| 160x120 | 38,400 B | ~28% = 약 11 KB |

> 도착량이 **약 10~25 KB 로 비슷**하다 → 전송이 **일정 지점에서 잘린다**.

**관련 이슈**

- [usbipd-win #530](https://github.com/dorssel/usbipd-win/issues/530) — 등시성 엔드포인트에서 `USBSUP_XFER_STALL` / `-EPIPE` 반복
- [usbipd-win #658](https://github.com/dorssel/usbipd-win/issues/658) — 고해상도에서 `Resource temporarily unavailable`
- [usbipd-win #1006](https://github.com/dorssel/usbipd-win/issues/1006) — USB2 포트에서 1280x720 이상 실패

## 해결 — 영상 파일 입력으로 우회 (video_pub)

카메라가 USB/IP 로 온전히 넘어오지 않으므로, **Windows 에서 녹화한 영상을 입력원**으로 쓴다.
**뒤 단계(`object_tracker`)는 코드 수정 0줄**로 그대로 동작한다 (토픽 이름·타입이 같으므로).

```
[Windows 카메라 앱] → test.mp4 → [video_pub] --/camera/image_raw--> [object_tracker]
```

**중요 — 카메라를 Windows 로 돌려주기**

`usbipd bind` 를 하면 장치는 **usbipd 서비스가 점유**한다. attach 를 안 해도 **Windows 앱은 그 카메라를 못 쓴다** (그래서 Windows 카메라 앱이 `0xA00F4244 NoCamerasAreAttached` 를 띄운다).

```powershell
usbipd list
usbipd unbind --busid 2-5     # ← Windows 로 반환
```

녹화 후 다시 WSL 로 쓰고 싶으면 `bind` → `attach` 를 다시 하면 된다.

**검증**

```
영상 열기 성공: /mnt/c/Users/kimsu/OneDrive/사진/카메라 앨범/test.mp4 (640x480, 183프레임)
50 프레임 발행 (shape=(480, 640, 3))
```

## 결과물 — 핵심 코드 commit

```
$ git log --oneline -1
39bb156 feat: USB 카메라 노드 + launch use_camera 스위치 + 영상파일 입력(video_pub)

 5 files changed, 253 insertions(+), 40 deletions(-)
 create mode 100644 src/opencv_demo/opencv_demo/camera_pub.py
 create mode 100644 src/opencv_demo/opencv_demo/video_pub.py
```

| 파일 | 역할 |
|---|---|
| `opencv_demo/camera_pub.py` | **신규** — 실기기 카메라(`CAP_V4L2`) → `/camera/image_raw` |
| `opencv_demo/video_pub.py` | **신규** — mp4 파일 → `/camera/image_raw` (loop) |
| `launch/track.launch.py` | `use_camera` 스위치 (`IfCondition` / `UnlessCondition`) |
| `opencv_demo/object_tracker.py` | 디버그 창(`show_debug`) 추가 |
| `setup.py` | 두 노드 entry point 등록 |

> **핵심 설계**: 두 발행 노드가 **같은 토픽 이름·타입**을 쓰므로, launch 인자 하나로
> `use_camera:=true/false` 만 바꾸면 입력원이 교체된다. 뒤 단계는 손댈 필요가 없다.

## 자주 나는 함정

| # | 함정 | 증상 | 해결 |
|---|---|---|---|
| 1 | PowerShell에 `<BUSID>` 자리표시자를 그대로 붙여넣음 | `'<' 연산자는 나중에 사용하도록 예약되어 있습니다` | **꺾쇠 없이** 실제 값(`2-5`)만 입력 |
| 2 | 여러 줄 한 번에 붙여넣기 | `>>` 대기 상태 → 뒤 명령 실행 안 됨 | **한 줄씩** 입력, `>>` 보이면 `Enter` 또는 `Ctrl+C` |
| 3 | 설치 직후 같은 창에서 `usbipd` 실행 | `'usbipd' 용어가 ... 인식되지 않습니다` | PowerShell **새 창** 열기 (PATH 반영) |
| 4 | 네트워크가 `Public` | `warning: A firewall appears to be blocking the connection` | `Set-NetConnectionProfile -Name "<SSID>" -NetworkCategory Private` |
| 5 | WSL이 **NAT** 모드 | 위 warning 지속 (방화벽 규칙이 안 먹음) | WSL 설정 → 네트워킹 모드 **mirrored** + **Hyper-V 방화벽 끔** |
| 6 | 커널에 `uvcvideo` 없음 | `modinfo: ERROR: Module uvcvideo not found` → `/dev/video*` 없음 | `wsl --update` 로 커널 6.18 로 (5.15엔 드라이버 미포함) |
| 7 | `cv2.VideoCapture(0)` 자동 백엔드 | **출력 없이 멈춤(hang)** | `cv2.VideoCapture(0, cv2.CAP_V4L2)` 로 **백엔드 명시** |
| 8 | `video1` 을 열려고 함 | `can't open camera by index` | UVC는 `video0`(영상) + `video1`(메타데이터) → **`video0` 사용** |
| 9 | WSL 재시작 후 카메라 사라짐 | `/dev/video*` 없음 | **정상** → `usbipd attach --wsl --busid 2-5` 다시 |
| 10 | `wsl --update` 직후 attach | `error: Device ... is already attached to a client` | `usbipd detach --busid 2-5` → `attach` 다시 |
| 11 | 재attach 후 **장치 번호가 바뀜** | `/dev/video0` 없음 → `/dev/video1`, `/dev/video2` | **`/dev/v4l/by-id/...`** 심볼릭 링크 사용 |
| 12 | `video2` 는 **메타데이터 장치** | 포맷 목록이 비어 있음 | **포맷(MJPG/YUYV)이 보이는 장치**를 골라라 |
| 13 | **비압축(YUYV) + 고해상도** | 초록/분홍 화면, 상단만 정상 | 해상도·fps 를 낮춰라 |
| 14 | 녹화하려 `unbind` 한 뒤 다시 WSL 로 | `usbipd: error: Device is not shared` | 관리자로 **`usbipd bind --busid 2-5`** 부터 다시 |

**Windows Home 에디션 주의**: `secpol.msc`(네트워크 목록 관리자 정책)가 **없다** → 미러링 모드가 사실상 유일한 해법.

**안정적인 장치 경로 (실측)**

```
/dev/v4l/by-id/usb-Generic_Web_Camera_200901010001-video-index0 -> ../../video1
/dev/v4l/by-id/usb-Generic_Web_Camera_200901010001-video-index1 -> ../../video2
```

## 배운 점

- **`bind` 는 영구, `attach` 는 휘발성.** 이 비대칭이 usbipd 함정의 절반이다. 재부팅·WSL 재시작마다 `attach` 부터 확인.
- **`bind` 는 장치를 usbipd 가 점유한다.** attach 를 안 해도 Windows 앱은 못 쓴다 — 돌려주려면 `unbind`.
- **에러 메시지가 층을 알려준다.** `firewall` → 네트워크 층, `Module not found` → 커널 층, `can't open camera by index` → 장치 층. 메시지를 읽으면 어느 겹인지 바로 나온다.
- **`lsusb` 에 보이는데 `/dev/video*` 가 없으면 드라이버 문제**다. 이 분기만 알면 진단이 3분이면 끝난다.
- **OpenCV 백엔드는 명시하는 습관.** `CAP_V4L2` 없이 자동 선택에 맡기면 조용히 멈춘다 — 에러도 안 낸다.
- **`read: True` 를 성공으로 착각하지 말 것.** 열렸고 버퍼가 왔다는 뜻일 뿐, 내용이 온전하다는 뜻은 아니다.
- **초록/분홍 화면 = 데이터 미도착 신호.** 색 자체가 아니라 **빈 버퍼**다.
- **대역폭 가설을 반증하는 법**: 해상도를 최저로 낮춰도 증상이 남으면 대역폭이 아니다.
- **`urb->status -104`(ECONNRESET) = 등시성 중계 실패.** 이 한 줄이 "대역폭 문제"와 "usbipd 한계"를 가른다.
- **환경 한계와 코드 실수를 구분하라.** 코드는 `opened: True` / `read: True` / 100+ 프레임 발행으로 정상이었고, 잘린 데이터가 들어온 것뿐이다.
- **입력원을 분리해 두면 대안이 생긴다.** 토픽 인터페이스만 맞추면 카메라 대신 영상 파일로 교체 가능 — 이게 ROS2 pub/sub 설계의 힘.
- **WSL 커널은 버전별로 드라이버 포함 여부가 다르다.** 5.15 는 `uvcvideo` 미포함, 6.18 은 포함.

## 어제와의 연결

| 어제 (10/16 cv_bridge) | 오늘 (10/17 USB 카메라) |
|---|---|
| 가짜 프레임 `image_pub` (`make_frame`) | **실기기 `camera_pub`** (`VideoCapture`) |
| `cv_bridge.cv2_to_imgmsg` 검증 | 그대로 재사용 (코드 변경 없음) |
| `/camera/image_raw` 10 Hz | 같은 토픽·같은 주기 |
| `object_tracker` 는 가짜 영상 구독 | **`object_tracker` 코드 수정 0줄** |

> **핵심**: 토픽 이름과 타입만 맞춰두면 **입력원을 갈아끼워도 뒤 단계는 그대로** 동작한다. 이게 ROS2 pub/sub 구조의 힘이다 — launch 의 `use_camera` 스위치 하나로 전환.

## 실행

**1) Windows (관리자 PowerShell, 한 줄씩)**

```powershell
usbipd list
usbipd bind --busid 2-5
usbipd attach --wsl --busid 2-5
```

**2) WSL 확인**

```bash
lsusb
ls /dev/video*
v4l2-ctl --list-devices
modinfo uvcvideo
```

**3) 카메라 열기**

```bash
python3 -c "
import cv2
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
print('isOpened:', cap.isOpened())
ok, f = cap.read()
print('read:', ok, None if not ok else f.shape)
cap.release()
"
```

**4) ROS2 (가짜 / 실기기 / 영상파일 전환)**

```bash
cd ~/ros2-opencv-demo
source /opt/ros/humble/setup.bash
colcon build --packages-select opencv_demo
source install/setup.bash

# 가짜 프레임
ros2 launch opencv_demo track.launch.py

# 실제 USB 카메라
ros2 launch opencv_demo track.launch.py use_camera:=true

# 영상 파일 (usbipd 한계 우회)
ros2 run opencv_demo video_pub --ros-args -p video_path:=/mnt/c/Users/kimsu/test.mp4
ros2 run opencv_demo object_tracker
```

**5) 확인 (다른 터미널)**

```bash
ros2 node list
ros2 topic hz /camera/image_raw
ros2 topic echo /object/center --once
```
