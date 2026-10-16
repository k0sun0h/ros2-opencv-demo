# cv_bridge — ROS2 ↔ OpenCV 연결 (10/16)

## 개념
- ROS2 에서 이미지는 `sensor_msgs/Image` **메시지**로 흐른다. OpenCV 는 **numpy 배열**로 다룬다 → **형식이 다르다**
- cv_bridge = 두 세상 사이의 **통역사**. 메시지 ↔ 배열을 서로 바꿔준다
- Image 메시지도 header(stamp, frame_id) + 크기(height, width) + **encoding** + step + data[] 구조
  - **encoding = "설명서"** (bgr8=컬러, mono8=흑백) → PointCloud2 의 fields 와 같은 결
- 두 함수만 알면 된다
  - `imgmsg_to_cv2(msg, desired_encoding='bgr8')` : 구독 → 처리 (메시지 → 배열)
  - `cv2_to_imgmsg(frame, encoding='bgr8')` : 발행 (배열 → 메시지)
- 흐름 : 가짜 카메라(발행) → `/camera/image_raw` → 추적 노드(구독→검출→발행) → `/object/center`

## Image 메시지 구조
| 필드 | 뜻 |
| --- | --- |
| header | stamp(시각) + frame_id(좌표계) |
| height / width | 세로 / 가로 크기 |
| encoding | bgr8(컬러) / mono8(흑백) — 픽셀 해석 설명서 |
| step | 한 줄이 몇 바이트인지 |
| data[] | 실제 픽셀 이진 덩어리 |

## cv_bridge 두 함수
```
from cv_bridge import CvBridge
bridge = CvBridge()

frame = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')   # ROS2 -> OpenCV
msg   = bridge.cv2_to_imgmsg(frame, encoding='bgr8')        # OpenCV -> ROS2
```

- `desired_encoding='bgr8'` 을 꼭 붙인다 → 안 붙이면 보낸 encoding 대로 나와 **색이 뒤집힘** (10/13 BGR 함정과 같은 결)

## 코드 — 노드 2개
| 파일 | 역할 |
| --- | --- |
| image_pub.py | 카메라 없이 가짜 프레임(numpy)을 만들어 `/camera/image_raw` 발행 (10 Hz) |
| object_tracker.py | 구독 → cv_bridge → HSV 마스크 → 윤곽 → 중심 → `/object/center` 발행 |

```
# image_pub.py (발행)
msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
msg.header.stamp = self.get_clock().now().to_msg()
msg.header.frame_id = 'camera'
self.pub.publish(msg)

# object_tracker.py (구독 + 검출 + 발행)
frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, np.array([90,100,100]), np.array([130,255,255]))
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
c = max(cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0],
        key=cv2.contourArea)
M = cv2.moments(c)
cx, cy = int(M['m10']/M['m00']), int(M['m01']/M['m00'])
p = Point(); p.x = float(cx); p.y = float(cy); p.z = 0.0
self.pub.publish(p)
```

## 실험 결과 (10/16 실제 관찰값)
- 빌드 : `colcon build --packages-select opencv_demo` → `entry_points 추가 완료`, `geometry_msgs 의존성 추가 완료`, `Finished <<< opencv_demo [0.97s]`
- 터미널1 : `ros2 run opencv_demo image_pub` → "가짜 카메라 발행 시작: /camera/image_raw"
- 터미널2 : `ros2 run opencv_demo object_tracker` → "물체 중심=(390,247) 면적=1886" 이 계속 바뀜
- 터미널3 : `ros2 topic echo /object/center` → `x: 440.0 / y: 158.0 / z: 0.0` 이 계속 출력됨

### 중심 좌표 검산 (공식 x = 80 + 420×(0.5+0.5·sin(i/8)), y = 210 + 60·sin(i/6))

| 값 | 이론 범위 | 관측값 |
| --- | --- | --- |
| x | 80 ~ 500 | 82 ~ 497 |
| y | 150 ~ 270 | 151 ~ 269 |
| 면적 | π·25² ≈ 1963 | 1886 (10/15 와 동일) |

- 관측 로그 : (390,247) → (479,269) → (496,253) → (435,209) → (319,165) → (192,151) → (102,176) → (82,222) → (141,262) → (256,267) → (384,234) → (476,187) → (497,154) → (440,158)
- x 가 좌우로, y 가 위아래로 움직이는 것이 공식과 일치 → **검출 결과가 토픽으로 그대로 흘러나온다**
- `mask` 창 : 검은 배경 + 흰 원 (색 마스크 정상)

## 자주 나는 함정
| 증상 | 원인 / 해결 |
| --- | --- |
| `ImportError: No module named 'cv_bridge'` | `ros-humble-cv-bridge` 미설치 또는 source 안 함 |
| `ModuleNotFoundError: geometry_msgs` | package.xml 에 `<exec_depend>geometry_msgs</exec_depend>` 추가 후 **다시 빌드** |
| `ros2 run` 이 실행파일을 못 찾음 | setup.py `entry_points` 미등록 또는 빌드·source 안 함 |
| 색이 뒤집혀 보임 | `desired_encoding='bgr8'` 빠짐 |
| 코드를 고쳤는데 그대로 동작 | `colcon build` → `source install/setup.bash` 다시 (빌드 사이클) |
| `/object/center` 가 안 나옴 | 발행 노드가 안 돌거나 물체를 못 찾음 (로그 확인) |

## 배운 점
- cv_bridge = ROS2 `Image` 메시지 ↔ OpenCV 배열 **통역사**. 두 함수(`imgmsg_to_cv2`, `cv2_to_imgmsg`)로 끝난다
- 메시지의 **encoding(bgr8/mono8)** 이 "설명서" 역할 → PointCloud2 의 `fields` 와 같은 결
- 지금까지 배운 검출(10/14 색공간 → 10/15 윤곽·중심)이 **그대로 노드 안에 들어간다**
- 노드를 **토픽으로 이으면** 다른 노드(모터 제어 등)가 그 값을 **구독해서** 쓸 수 있다 → 이게 로봇 비전의 연결점
- **의존성(package.xml)과 entry_points 를 안 맞추면 실행이 안 된다** — 코드가 맞아도 등록이 빠지면 못 돈다
- 빌드 사이클 : **코드 수정 → `colcon build` → `source` → `ros2 run`**

## 어제(10/15)와의 연결
- 10/14 : 색공간 → 마스크 만들기
- 10/15 : 마스크 → 윤곽·중심·다각형·추적 (OpenCV 안에서)
- 10/16 : 그 중심 좌표를 **ROS2 토픽(`/object/center`)** 으로 발행 → **로봇과 연결**
- 다음(10/17) : 가짜 프레임 대신 **실제 USB 카메라**(`usbipd-win` 으로 `/dev/video0` 연결)로 같은 파이프라인 돌리기

## 실행
- ros2 run opencv_demo image_pub      (터미널 1 — 가짜 카메라)
- ros2 run opencv_demo object_tracker (터미널 2 — 검출 + 발행)
- ros2 topic echo /object/center      (터미널 3 — 확인)
- ros2 topic hz /object/center        (약 10 Hz)
