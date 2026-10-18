#!/usr/bin/env bash
# 프로젝트 1 통합 실행 + 자동 검증   (10/18)
#   사용: bash check_pipeline.sh [source] [video_path]
#     source: fake | camera | video   (기본 video)
#
# 검증은 ros2 CLI 를 쓰지 않는다 (미러링 모드에서 데몬이 hang 되기 때문).
# p1_verify.py 가 두 토픽을 직접 구독해서 판정한다.
#
# 주의: set -u 를 쓰면 ROS2 setup.bash 가 죽는다 (AMENT_TRACE_SETUP_FILES).

SCRIPT_VERSION="v3-p1verify"   # 이 줄이 보이면 최신본

SRC="${1:-video}"
VIDEO="${2:-/mnt/c/Users/kimsu/OneDrive/사진/카메라 앨범/test.mp4}"
WS="$HOME/ros2-opencv-demo"
LOG=/tmp/p1_launch.log
VERIFY="$WS/p1_verify.py"

cd "$WS" || { echo "워크스페이스 없음: $WS"; exit 1; }

if [ ! -f /opt/ros/humble/setup.bash ]; then
  echo ">>> ROS2 가 없습니다: /opt/ros/humble/setup.bash"; exit 1
fi
if [ ! -f install/setup.bash ]; then
  echo ">>> 아직 빌드가 안 됐습니다. 먼저: colcon build --packages-select opencv_demo"
  exit 1
fi

# ROS2 setup 스크립트가 미정의 변수를 참조하므로 -u 를 잠시 끈다
set +u
source /opt/ros/humble/setup.bash
source install/setup.bash
set -u
export ROS_LOCALHOST_ONLY=1
echo "확인: ROS_DISTRO=${ROS_DISTRO:-?}  ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY  RMW=${RMW_IMPLEMENTATION:-default}"

echo
echo "---------- 0. 정리 ----------"
pkill -f "ros2 launch"   2>/dev/null
pkill -f video_pub       2>/dev/null
pkill -f camera_pub      2>/dev/null
pkill -f object_tracker  2>/dev/null
pkill -9 -f _ros2_daemon 2>/dev/null
sleep 2
pgrep -af "video_pub|camera_pub|object_tracker" || echo "(남은 노드 없음 — 깨끗함)"

if [ "$SRC" = "video" ] && [ ! -f "$VIDEO" ]; then
  echo
  echo ">>> 영상 파일이 없습니다: $VIDEO"
  echo ">>> Windows 카메라 앱으로 녹화했는지, 경로가 맞는지 확인하세요."
  echo ">>> (녹화하려면 관리자 PowerShell: usbipd unbind --busid 2-5)"
  exit 1
fi

echo
echo "---------- 1. 통합 실행 (launch 1줄) ----------"
nohup ros2 launch opencv_demo track.launch.py \
      source:="$SRC" video_path:="$VIDEO" show_debug:=false > "$LOG" 2>&1 &
LJOB=$!
echo "launch PID=$LJOB   로그=$LOG"
sleep 6

echo
echo "---------- 2. launch 로그 (노드가 떴는지) ----------"
tail -20 "$LOG"

echo
echo "---------- 3. 통합 검증 (직접 구독) [핵심] ----------"
if [ -f "$VERIFY" ]; then
  python3 "$VERIFY" 12
  VRC=$?
else
  echo ">>> p1_verify.py 가 없습니다: $VERIFY"; VRC=9
fi

echo
echo "---------- 4. 참고: ros2 CLI (데몬 문제로 실패할 수 있음) ----------"
echo "[node list]"
timeout 8 ros2 node list --no-daemon 2>&1 | head -10 || echo "(CLI 실패 — 정상일 수 있음)"
echo "[topic list]"
timeout 8 ros2 topic list --no-daemon 2>&1 | head -10 || echo "(CLI 실패 — 정상일 수 있음)"

echo
echo "---------- 5. 정리 ----------"
kill "$LJOB" 2>/dev/null
pkill -f "ros2 launch"   2>/dev/null
pkill -f video_pub       2>/dev/null
pkill -f camera_pub      2>/dev/null
pkill -f object_tracker  2>/dev/null
sleep 2
echo "정리 완료"

echo
echo "======================================================"
if [ "$VRC" = "0" ]; then
  echo " >>> 통합 실행 성공  (source=$SRC)"
  echo "======================================================"
  echo
  echo "다음: 캡처용 실행 (창까지 보기)"
  echo "  cd ~/ros2-opencv-demo && source /opt/ros/humble/setup.bash && source install/setup.bash"
  echo "  export ROS_LOCALHOST_ONLY=1"
  echo "  ros2 launch opencv_demo track.launch.py source=$SRC \\"
  echo "    video_path=\"$VIDEO\" show_debug:=true"
else
  echo " >>> 실패 (검증 종료코드=$VRC)  (source=$SRC)"
  echo "======================================================"
  echo
  echo "붙여줄 것:"
  echo "  tail -30 $LOG"
fi
