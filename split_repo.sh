#!/usr/bin/env bash
# split_repo.sh — slam_demo/ 를 별도 저장소 ros2-slam-demo 로 분리한다.
#
#   bash split_repo.sh          # 미리보기 (아무것도 안 바뀜)
#   bash split_repo.sh --run    # 실제 분리 + 커밋
#
# 사전 준비 (사람이 할 일)
#   GitHub 에 빈 저장소 ros2-slam-demo 를 만든다.
#   ★ README / .gitignore / license 체크를 모두 해제 (안 하면 push 충돌)
#
# 하는 일
#   1) ~/ros2-slam-demo 새 폴더에 slam_demo 파일 복사
#   2) 그 폴더를 git 저장소로 초기화 + 첫 커밋
#   3) ~/ros2-opencv-demo 에서 slam_demo/ 제거
#   4) 메인 README 의 slam_demo 링크를 새 저장소 URL 로 교체
#   5) 양쪽 커밋 (push 는 사람이 직접)

set -u
SRC="$HOME/ros2-opencv-demo"
DST="$HOME/ros2-slam-demo"
GHUSER="k0sun0h"
NEWURL="https://github.com/$GHUSER/ros2-slam-demo"
RUN=0
[ "${1:-}" = "--run" ] && RUN=1

[ -d "$SRC/.git" ] || { echo ">>> 저장소 없음: $SRC"; exit 1; }
[ -d "$SRC/slam_demo" ] || { echo ">>> 이미 분리됐거나 폴더 없음: $SRC/slam_demo"; exit 1; }

FILES="README.md fake_robot.py slam_params_local.yaml check_map.py
run_slam_demo.sh save_map_demo_v2.sh check_scan_v4.py isolate_scan.sh
fix_scan_dds.sh udp_only.xml room.pgm room.yaml .gitignore"

echo "======================================================"
echo " slam_demo → ros2-slam-demo 분리  ($([ $RUN = 1 ] && echo 실행 || echo 미리보기))"
echo "======================================================"
echo
echo "  원본: $SRC/slam_demo"
echo "  대상: $DST"
echo "  새 저장소: $NEWURL"
echo

echo "---------- 옮길 파일 ----------"
N=0
for f in $FILES; do
  if [ -f "$SRC/slam_demo/$f" ]; then
    printf "  OK   %-26s %8s B\n" "$f" "$(stat -c%s "$SRC/slam_demo/$f" 2>/dev/null || echo 0)"
    N=$((N+1))
  else
    printf "  없음 %-26s\n" "$f"
  fi
done
echo "  총 ${N}개"
echo

echo "---------- 기존 저장소에서 제거될 것 ----------"
echo "  $SRC/slam_demo/ (${N}개 파일 + __pycache__)"
echo

echo "---------- 메인 README 에서 바뀔 링크 ----------"
echo "  slam_demo/README.md  →  $NEWURL"
echo

if [ "$RUN" = "0" ]; then
  echo ">>> 미리보기입니다. 진행하려면:"
  echo "    ① GitHub 에 ros2-slam-demo 빈 저장소 생성 (README 체크 해제)"
  echo "    ② bash split_repo.sh --run"
  exit 0
fi

if [ -e "$DST" ]; then
  echo ">>> $DST 가 이미 있습니다. 지우거나 이름을 바꾼 뒤 다시 실행하세요."
  exit 1
fi

# ---------------------------------------------------------------- 1. 새 저장소
echo "---------- 1. 새 폴더 + 복사 ----------"
mkdir -p "$DST"
for f in $FILES; do
  [ -f "$SRC/slam_demo/$f" ] || continue
  cp "$SRC/slam_demo/$f" "$DST/$f"
done
# __pycache__ 는 복사하지 않고, 새 .gitignore 를 확실히 만든다
cat > "$DST/.gitignore" <<'EOF'
__pycache__/
map_preview.png
*.pyc
EOF
ls -la "$DST"

echo
echo "---------- 2. git 초기화 + 첫 커밋 ----------"
cd "$DST" || exit 1
git init -q
git add -A
UNAME=$(git -C "$SRC" config user.name 2>/dev/null)
UMAIL=$(git -C "$SRC" config user.email 2>/dev/null)
if [ -z "${UNAME:-}" ] || [ -z "${UMAIL:-}" ]; then
  UNAME="$(id -un)"
  UMAIL="$(id -un)@localhost"
  echo "  (저장소에 user.name/email 이 없어 임시값 사용: $UNAME <$UMAIL>)"
fi
git -c user.name="$UNAME" -c user.email="$UMAIL" \
    commit -q -m "feat: slam_toolbox 2D 매핑 실습 (가짜 로봇 + 지도 저장)

- fake_robot.py: 방 8x6m 주행, /scan 360빔 5Hz, odom 오차 3% 주입
- slam_toolbox online_async (CeresSolver, resolution 0.05)
- room.pgm 189x163 @ 0.05m — 방 커버리지 96.65%
- 20/60/90초 세 회차 실측: 빈 공간 18,556칸 ±1칸으로 동일
  → 볼록한 방에서는 시간이 아니라 경로가 지도를 결정
- /scan 실제 발행률 5.0Hz 확정 (고유 stamp 61개, 중복 0)
- 진단 도구: check_scan_v4 / isolate_scan / fix_scan_dds
  → WSL2 mirrored 에서 노드 2개 구성은 통신 실패, 3개면 정상
- README: 실행 3단계 + 파라미터 8개 + 실험 결론 3개" || echo "  (커밋 실패)"
git log --oneline
echo
echo "  원격 연결:"
git remote add origin "https://github.com/$GHUSER/ros2-slam-demo.git" 2>/dev/null || \
  git remote set-url origin "https://github.com/$GHUSER/ros2-slam-demo.git"
git branch -M main
git remote -v

# ---------------------------------------------------------------- 3. 기존 저장소 정리
echo
echo "---------- 3. 기존 저장소에서 slam_demo 제거 ----------"
cd "$SRC" || exit 1
if git rm -r -q slam_demo 2>/dev/null; then
  echo "  git rm 완료"
else
  echo "  [경고] git rm 실패 — 추적 상태를 확인하세요"
fi
# __pycache__ 처럼 추적 안 된 잔여물 정리 (원본은 이미 새 저장소에 복사됨)
if [ -d slam_demo ]; then
  rm -rf slam_demo
  echo "  잔여 폴더 삭제"
fi
echo "  제거 완료"

echo
echo "---------- 4. 메인 README 링크 교체 ----------"
python3 - "$NEWURL" <<'PYEOF'
import sys
new_url = sys.argv[1]
p = 'README.md'
s = open(p, encoding='utf-8').read()
before = s

# a) 하위 폴더 링크 → 새 저장소 URL
s = s.replace('[`slam_demo/README.md`](slam_demo/README.md)',
              f'[`ros2-slam-demo`]({new_url})')
s = s.replace('(slam_demo/README.md)', f'({new_url})')

# b) 실행 예시의 경로를 새 저장소 기준으로
s = s.replace('''```bash
cd slam_demo
bash run_slam_demo.sh 20          # 20초 검증
bash save_map_demo_v2.sh 90 room  # 90초 매핑 + 지도 저장
```''', f'''별도 저장소로 분리했다 → [{new_url}]({new_url})

```bash
git clone {new_url}
cd ros2-slam-demo
bash run_slam_demo.sh 20          # 20초 검증
bash save_map_demo_v2.sh 90 room  # 90초 매핑 + 지도 저장
```''')

if s != before:
    open(p, 'w', encoding='utf-8').write(s)
    print('  README.md 수정 완료')
else:
    print('  (README.md 에서 바꿀 패턴을 못 찾음 — 수동 확인 필요)')
PYEOF

echo
echo "---------- 5. 기존 저장소 커밋 ----------"
git add README.md
git status --short
git commit -q -m "refactor: slam_demo 를 별도 저장소 ros2-slam-demo 로 분리

- slam_demo/ 12개 파일을 새 저장소로 이동 (이력은 새로 시작)
- 메인 README 의 링크를 새 저장소 URL 로 교체
- 이 저장소는 OpenCV 프로젝트1 전용으로 유지" || echo "  (커밋할 변경 없음)"
git log --oneline -2

echo
echo "======================================================"
echo " 분리 완료"
echo "======================================================"
echo
echo "  새 저장소: $DST"
echo "  기존 저장소: $SRC (slam_demo 제거됨)"
echo
echo "  이제 두 곳 모두 push:"
echo "    cd $DST && git push -u origin main"
echo "    cd $SRC && git push origin main"
echo
echo "  push 후 확인:"
echo "    $NEWURL"
echo "    → 첫 화면에 README 219줄이 바로 보여야 함"
echo
echo "  ※ 되돌리려면 (분리를 취소):"
echo "      cp -r $DST/* $SRC/slam_demo/ 2>/dev/null || mkdir -p $SRC/slam_demo && cp -r $DST/* $SRC/slam_demo/"
echo "      cd $SRC && git add slam_demo && git commit -m 'revert: slam_demo 복원'"
