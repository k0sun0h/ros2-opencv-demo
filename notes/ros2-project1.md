# 프로젝트 1 통합 실행 + 버그 수정 (10/18)

> 결과물: **실행 성공** — `video_pub` → `object_tracker` 파이프라인을 **launch 한 줄**로 구동

## 개념

**통합 실행**이란 여러 노드를 **launch 파일 하나로** 띄우는 것이다.
10/16~10/17에는 터미널 2개로 각각 실행했는데, 그러면 시작 순서·파라미터·환경변수를 **사람이 손으로** 맞춰야 한다. launch는 그것을 **코드로 고정**한다.

| | 터미널 2개 (10/17) | launch 1줄 (10/18) |
|---|---|---|
| 실행 | `ros2 run` × 2 | `ros2 launch` × 1 |
| 파라미터 | 각 터미널에 `--ros-args -p` | launch 인자로 한 번에 |
| 환경변수 | 터미널마다 `export` | launch 안에 내장 |
| 순서 | 사람이 판단 | launch가 보장 |
| 재현 | 명령 2개 기억 | 명령 1개 |

## 설계 ① 입력원 3개를 `source` 한 인자로

입력원이 **3개**가 되면서 2지선다(`use_camera`)로는 부족해졌다.

| `source` | 노드 | 쓰임 |
|---|---|---|
| `fake` | `image_pub` | 카메라 없이 개발 |
| `camera` | `camera_pub` | 실기기 USB 카메라 |
| `video` | `video_pub` | 영상 파일 (usbipd 한계 우회) |

```python
is_fake   = PythonExpression(["'", source, "' == 'fake'"])
is_camera = PythonExpression(["'", source, "' == 'camera'"])
is_video  = PythonExpression(["'", source, "' == 'video'"])
# 각 노드에 IfCondition(is_*) → 셋 중 하나만 뜬다
```

> **상호 배타를 조건문이 아니라 구조로 보장한다.** `use_camera:=true` + `video_path:=...` 를 동시에 주면
> 발행자가 둘 다 떠서 토픽이 섞인다. `source` 하나면 그런 상태가 **만들어질 수 없다**.

## 설계 ② 검증은 `ros2` CLI 가 아니라 **노드**로

`ros2` CLI는 **데몬(`_ros2_daemon`)** 을 거쳐 노드를 찾는다.
그런데 WSL2 미러링 모드에서 그 데몬이 **hang** 된다([ros2/ros2#1515](https://github.com/ros2/ros2/issues/1515)).
게다가 데몬은 오래 사는 프로세스라 **`ROS_LOCALHOST_ONLY=1` 없이 시작된 옛 데몬**이 남아 있으면
로컬호스트 전용 노드를 못 본다 → **CLI만 눈이 먼 상태**.

그래서 검증 노드(`p1_verify.py`)가 **두 토픽을 직접 구독해서** 개수를 센다.
노드와 똑같은 DDS 스택을 쓰므로 훨씬 정확하다.

| 검증 수단 | 신뢰도 |
|---|---|
| `ros2 topic hz` / `echo` | 데몬에 의존 → hang 가능 |
| `ros2 node list --no-daemon` | 데몬 우회 |
| **`p1_verify.py` (직접 구독)** | **가장 정확** |

## 실험 결과

**환경**

| 항목 | 값 |
|---|---|
| ROS2 | Humble |
| `ROS_LOCALHOST_ONLY` | `1` (launch 안에 내장) |
| 입력 | `test.mp4` (640x480, 183프레임) |
| 실행 | `ros2 launch opencv_demo track.launch.py source:=video video_path:=...` |

**launch 로그 (터미널 1개)**

```
[INFO] [video_pub-1]: process started with pid [745]
[INFO] [object_tracker-2]: process started with pid [747]
[video_pub-1] 영상 열기 성공: .../test.mp4 (640x480, 183프레임)
[object_tracker-2] 구독: /camera/image_raw  ->  발행: /object/center (show_debug=False)
[object_tracker-2] 물체 중심=(380,136) 면적=15994
[video_pub-1] 50 프레임 발행 (480, 640, 3)
```

> **터미널 하나에서 두 노드의 로그가 같이 나온다** — 이게 통합의 증거다.

**검증 (`p1_verify.py`, 12초 관찰)**

```
/camera/image_raw : 120개   평균 10.0 Hz (평균 간격 0.100초, 최대 0.116초)
                    해상도 640x480
/object/center    : 119개   마지막 (340, 224, 0)

판정
  image_raw 발행  : OK
  object/center   : OK

>>> 통합 실행 성공
```

| 지표 | 값 | 해석 |
|---|---|---|
| 발행 주기 | **10.0 Hz** (간격 0.100초) | 타이머 10 Hz와 일치 |
| 최대 간격 | **0.116초** | 12초 관찰이라 **loop 경계(18.3초)를 안 만남** |
| 검출률 | **119 / 120 = 99%** | 거의 모든 프레임에서 검출 |
| 해상도 | 640x480 | 원본 유지 |

> **loop 경계**: 영상이 끝나면 처음으로 되돌아가며 프레임을 다시 찾는다 → 그 순간만 간격이 커진다(10/17 측정값 `0.799초`).

**CLI 확인 (데몬 우회)**

```
$ ros2 node list --no-daemon
/object_tracker
/video_pub

$ ros2 topic list --no-daemon
/camera/image_raw
/object/center
/parameter_events
/rosout
```

## 오늘 고친 버그 (6개)

`colcon build` 없이 돌리던 어제 코드를 읽어보니, 통합 실행에서 문제가 될 것들이 남아 있었다.

| # | 파일 | 버그 | 증상 |
|---|---|---|---|
| 1 | `camera_pub.py` | `cv2.VideoCapture(device_id)` — **`CAP_V4L2` 미지정** | WSL2에서 **출력 없이 멈춤(hang)** |
| 2 | `camera_pub.py` | `device_id` 가 **int만** 허용 | `by-id` 경로를 못 씀 → 재attach 때 번호가 바뀌면 실패 |
| 3 | `camera_pub.py` | `fps` 가 **타이머에만** 적용, 캡처엔 미적용 | 카메라는 30fps로 돌고 발행만 10Hz → 협상 어긋남 |
| 4 | `camera_pub.py` | 로그가 **요청값**을 찍음 (`/dev/video{id}`, `(640x480)`) | 실제로 열린 값과 달라 **진단을 오도** |
| 5 | `object_tracker.py` | `show_debug=True` 기본 + **무조건 `cv2.imshow`** | `DISPLAY` 없으면(WSLg 미실행) **노드가 죽음** |
| 6 | `track.launch.py` | **`video_pub` 경로가 없음** | 터미널 2개로만 실행 가능 → **통합 실행이 안 됨** |
| + | `track.launch.py` | `use_camera` 2지선다 | 입력원 3개를 표현 못 하고 **상호 배타 보장 불가** |

**수정 내용**

| 파일 | 바뀐 것 |
|---|---|
| `track.launch.py` | `source:=fake\|camera\|video` **단일 인자** + `video_path` + `show_debug` + **launch 안에서 `ROS_LOCALHOST_ONLY=1`** |
| `camera_pub.py` | `CAP_V4L2` 명시 / `device_id` **문자열(by-id) 지원**(숫자는 자동 변환) / `fps` 실제 적용 / **실제 값**을 로그로 |
| `object_tracker.py` | **헤드리스 가드**(`DISPLAY` 없으면 창 자동 해제 + 경고 1회) / 로그를 **5프레임마다 → 1초에 한 번** |

## 자주 나는 함정

| # | 함정 | 증상 | 해결 |
|---|---|---|---|
| 1 | **`set -u` + ROS2 `setup.bash`** | `AMENT_TRACE_SETUP_FILES: unbound variable` → 스크립트 즉사 | `set -u` **쓰지 말 것** (또는 source 전후 `set +u`) |
| 2 | **`ros2` CLI 데몬 hang** | `node list`/`hz`/`echo` 가 전부 실패 | **`--no-daemon`** 또는 **검증 노드(직접 구독)** |
| 3 | 옛 스크립트가 실행됨 | 고친 줄이 반영 안 됨 | 스크립트에 **버전 상수**를 넣고 확인 (`SCRIPT_VERSION`) |
| 4 | launch 인자를 `=` 로 씀 | 인자가 안 먹거나 해석이 어긋남 | **`인자:=값`** (`:=`) 형태로 |
| 5 | 영상 loop 경계의 긴 간격 | `max` 간격이 갑자기 큼 | **정상** — 영상 길이보다 긴 구간을 관찰해야 드러남 |
| 6 | 문서와 코드의 인터페이스 불일치 | README엔 `use_camera`, 코드엔 `source` | 인터페이스를 바꾸면 **문서도 같이** |
| 7 | 문자열 파라미터에 `value_type=int` | launch에서 `invalid literal for int()` | 경로 문자열은 `LaunchConfiguration` **그대로** 전달 |
| 8 | `show_debug` 가 bool 로 안 넘어감 | `'false'` 문자열이 참으로 취급 | `ParameterValue(..., value_type=bool)` |
| 9 | `DISPLAY` 없는 환경에서 `imshow` | 노드가 죽음 | **`os.environ.get('DISPLAY')` 확인 후** 창 생성 |
| 10 | 로그를 프레임 수 기준으로 | `n % 5` → 프레임률이 변하면 로그량도 변함 | **시간 기준**(1초에 한 번)으로 |

## 배운 점

- **검증 도구가 틀리면 성공도 실패로 보인다.** 파이프라인은 처음부터 정상이었고, `ros2` CLI가 데몬 때문에 눈이 먼 것이었다. **"무엇이 실패했는지"를 먼저 특정해야 한다** — 이번엔 *검증 계층*이 실패했다.
- **"발행은 되는데 구독이 안 된다"에 원인이 둘.** ① DDS 디스커버리(10/16, 실제 문제) ② CLI 데몬(10/18, 검증 도구 문제). **로그로 ①과 ②를 구분**할 수 있다 — 노드끼리 대화 중이면 ①은 아니다.
- **`--no-daemon` 한 줄로 원인이 갈린다.** CLI가 hang 되면 ① 데몬 문제인지 ② 진짜 통신 문제인지 이걸로 판정.
- **상호 배타는 조건문이 아니라 구조로.** 3지선다 인자 하나면 "둘 다 켜진 상태"가 **표현 불가능**해진다.
- **환경변수도 launch에 넣어라.** 터미널마다 `export` 하면 언젠가 빠뜨린다. `SetEnvironmentVariable` 로 **실행 정의에 포함**시키면 재현이 보장된다.
- **`set -u` 같은 좋은 습관도 상대가 있다.** 남의 스크립트(ROS2 setup)를 source 할 때는 꺼야 한다 — **내 코드에만 적용**해야 한다.
- **인터페이스 변경은 문서까지 한 세트.** 코드를 고치고 문서를 안 고치면 다음에 나를 속인다.
- **버전을 찍어라.** "고쳤는데 그대로다"의 절반은 **옛 파일을 실행 중**인 것.

## 어제(10/17)와의 연결

| 10/17 (USB 카메라) | 10/18 (통합 실행) |
|---|---|
| 터미널 2개로 각각 실행 | **launch 1줄** |
| `use_camera` 2지선다 | **`source` 3지선다** |
| `CAP_V4L2` 를 노트에 **함정으로** 기록 | **코드에 반영** |
| `ros2 topic hz` 로 확인 | **검증 노드로 직접 구독** |
| DDS 문제를 손으로 `export` 해서 해결 | **launch 안에 내장** |
| 결과물: 핵심 코드 commit | 결과물: **실행 성공** |

> **10/17은 "입력원을 바꿀 수 있게" 만들었고, 10/18은 "바꿔도 한 줄로 돌아가게"** 만들었다.

## 실행

**빌드**

```bash
cd ~/ros2-opencv-demo
source /opt/ros/humble/setup.bash
colcon build --packages-select opencv_demo
source install/setup.bash
```

**통합 실행 (3가지 입력원)**

```bash
# 가짜 프레임
ros2 launch opencv_demo track.launch.py

# 실제 USB 카메라
ros2 launch opencv_demo track.launch.py source:=camera

# 영상 파일 (usbipd 한계 우회)
ros2 launch opencv_demo track.launch.py source:=video \
  video_path:="/mnt/c/Users/kimsu/OneDrive/사진/카메라 앨범/test.mp4" \
  show_debug:=true
```

**자동 검증**

```bash
bash check_pipeline.sh video "/mnt/c/Users/kimsu/OneDrive/사진/카메라 앨범/test.mp4"

# 또는 검증 노드만 따로
python3 p1_verify.py 12
```

**launch 인자 전체**

| 인자 | 기본값 | 설명 |
|---|---|---|
| `source` | `fake` | `fake` \| `camera` \| `video` |
| `video_path` | `''` | `source:=video` 일 때 읽을 파일 |
| `device_id` | `by-id` 경로 | 숫자(`0`)도 허용 |
| `width` / `height` | `640` / `480` | 카메라 해상도 |
| `fps` | `10.0` | 캡처·발행 주기 |
| `h_min` / `h_max` | `90` / `130` | HSV 색 범위 |
| `s_min` / `v_min` | `100` / `100` | 채도·밝기 최소 |
| `min_area` | `100` | 물체로 인정할 최소 면적 |
| `show_debug` | `true` | `frame`/`mask` 창 표시 |
