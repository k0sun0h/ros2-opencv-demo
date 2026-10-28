#!/usr/bin/env bash
# enhance_readme.sh — 프로젝트1 README 보강 + opencv_recheck.py 정리
#
#   bash enhance_readme.sh          # 미리보기
#   bash enhance_readme.sh --run    # 실제 수정 + 커밋
#
# 하는 일
#   1) opencv_recheck.py → scripts/ 로 이동
#   2) README "검증 결과" 섹션을 성능 실측 표로 확장 (10/19 재확인 수치)
#   3) 함정 표에 2줄 추가 (로그 스로틀 / 노드 2개 통신)
#   4) usbipd 한계 섹션에 반증 수치 보강
#   5) 커밋

set -u
REPO="$HOME/ros2-opencv-demo"
RUN=0
[ "${1:-}" = "--run" ] && RUN=1
[ -d "$REPO/.git" ] || { echo ">>> 저장소 없음: $REPO"; exit 1; }
cd "$REPO" || exit 1

echo "======================================================"
echo " 프로젝트1 README 보강  ($([ $RUN = 1 ] && echo 실행 || echo 미리보기))"
echo "======================================================"
echo

BEFORE=$(wc -l < README.md)
echo "  현재 README.md: ${BEFORE}줄"
echo

echo "  1) opencv_recheck.py → scripts/  ($([ -f opencv_recheck.py ] && echo '있음' || echo '없음'))"
echo "  2) '검증 결과' 섹션 → 성능 실측 표로 확장"
echo "  3) 함정 표 +2줄 (로그 스로틀, 노드 2개 통신)"
echo "  4) usbipd 한계 → 반증 수치 3줄 추가"
echo

if [ "$RUN" = "0" ]; then
  echo ">>> 미리보기입니다. 진행하려면: bash enhance_readme.sh --run"
  exit 0
fi

# ---------------------------------------------------------------- 1. scripts/
echo "---------- 1. opencv_recheck.py 이동 ----------"
mkdir -p scripts
if [ -f opencv_recheck.py ]; then
  git mv opencv_recheck.py scripts/ 2>/dev/null || mv opencv_recheck.py scripts/
  echo "  이동: scripts/opencv_recheck.py"
else
  echo "  (이미 이동됨 또는 없음)"
fi

# ---------------------------------------------------------------- 2~4. README 수정
echo
echo "---------- 2. README 수정 ----------"
python3 <<'PYEOF'
import re, io

p = 'README.md'
s = open(p, encoding='utf-8').read()
orig = s

START = '## 검증 결과 (10/18)'
END = '## 자주 나는 함정'

new_section = '''## 검증 결과 — 실측 성능

### 통합 실행 (10/18)

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

### 검출률·면적 (10/19 재확인)

`p1_verify.py` 로 토픽을 직접 구독해 센다. 183프레임 기준.

| 지표 | 값 |
|---|---|
| 검출 프레임 | **183 / 183 = 100%** |
| 검출 면적 범위 | 15,994 ~ 37,048 px (최대/최소 **2.32배**) |
| 중심 좌표 | 320, 240 (화면 중앙) |

면적이 2.32배 차이 나는 것은 물체가 카메라에서 멀어졌다 가까워졌기 때문이다.
검출률은 거리와 무관하게 100% 였다.

### 처리율 — 입력 fps 를 올리면 처리가 못 따라간다

| 입력 fps | 처리/수신 | 처리율 | 비고 |
|---|---|---|---|
| 10.0 Hz | 99 / 100 | **99%** | 여유 있음 |
| 28.7 Hz | 188 / 238 | **79.0%** | **천장에 걸림** |

1장 처리에 약 **44ms** 걸린다(≈22.5Hz). 그래서 입력이 초당 28.7장이면
초당 6.7장을 놓친다. 천장은 대략 **22~23Hz** 로 보인다.

임계값(85~140)·채도(S80)·명도(V60)를 모두 풀어도 검출률 100% 가 유지됐다.
→ **원래 값을 그대로 쓰는 것이 맞다**. 민감도를 올려 얻는 게 없다.

### 로그로 처리율을 판단하면 안 된다

`video_pub.py` 는 로그를 `_once_per_second('last_log', now)` 로 **1초에 한 번만**
찍는다. 그래서 로그만 보면 실제 처리율을 알 수 없다. 실제로는 28.7Hz 로 돌면서
로그는 1Hz 로 찍혀 "4.8Hz" 처럼 잘못 읽기 쉽다.

→ 처리율은 **`p1_verify.py` 처럼 토픽을 직접 구독해 세야** 정확하다.
→ `ros2 topic hz` 는 WSL2 에서 DDS 디스커버리가 느려 6~8초 안에 답을 못 낸다.
   이것도 거짓 실패를 만든다.

'''

# 섹션 교체
i = s.find(START)
j = s.find(END)
if i == -1 or j == -1 or j < i:
    print('  [경고] 섹션 경계를 못 찾음 — README 수정 생략')
else:
    s = s[:i] + new_section + s[j:]
    print('  검증 결과 섹션 확장 완료')

# --- 함정 표에 2줄 추가
anchor = '| 8 | 로그가 프레임률에 따라 폭주 | 로그를 **시간 기준**(1초에 한 번)으로 |'
add = anchor + '''
| 9 | 로그는 1초 스로틀이라 **처리율을 알 수 없음** | `p1_verify.py` 로 토픽을 직접 구독해 센다 |
| 10 | 노드 2개만 띄우면 통신이 조용히 깨짐 | 파이프라인 전체(노드 3개 이상)를 띄우고 측정 |'''
if anchor in s:
    s = s.replace(anchor, add)
    print('  함정 표 +2줄')
else:
    print('  [경고] 함정 표 anchor 못 찾음')

# --- usbipd 반증 수치 보강
anc2 = '- **우회**: Windows 에서 녹화한 영상을 `source:=video` 로 입력 (뒤 단계 코드 수정 0줄)'
add2 = '''- **우회**: Windows 에서 녹화한 영상을 `source:=video` 로 입력 (뒤 단계 코드 수정 0줄)

### 대역폭이 아니라는 증거

- 해상도를 **160x120** 까지 낮춰도 초록 비율이 **71.7%** 로 남는다
  → 대역폭 부족 가설은 **반증**된다. 대역폭을 1/16 로 줄여도 그대로다.
- 깨진 색의 정체: `YUV(0,0,0)` → `RGB(0,135,0)`. 프레임 앞부분만 도착하고
  나머지가 0 으로 채워져 초록으로 보인다.
- 즉 **전송 계층(등시성 미지원)** 문제이지 해상도·대역폭 문제가 아니다.
  usbipd 로는 해결되지 않는다.'''
if anc2 in s:
    s = s.replace(anc2, add2)
    print('  usbipd 반증 수치 추가')
else:
    print('  [경고] usbipd anchor 못 찾음')

# --- 파일 표에 scripts/ 반영
s = s.replace('| `p1_verify.py` | 통합 검증 (토픽 직접 구독) |',
              '| `p1_verify.py` | 통합 검증 (토픽 직접 구독) |\n| `scripts/opencv_recheck.py` | 셀프테스트 + 검출률/면적 재측정 |')

if s != orig:
    open(p, 'w', encoding='utf-8').write(s)
    print(f'  README.md 저장 ({len(orig.splitlines())} → {len(s.splitlines())}줄)')
else:
    print('  [경고] 변경 없음')
PYEOF

# ---------------------------------------------------------------- 5. 커밋
echo
echo "---------- 3. 커밋 ----------"
git status --short
git add -A
git commit -q -m "docs: 프로젝트1 README 에 실측 성능과 측정 함정 보강

- scripts/opencv_recheck.py 로 이동 (저장소 루트 정리)
- 검증 결과 섹션을 3개 표로 확장
  · 검출률 183/183 = 100%, 면적 15,994~37,048 (2.32배)
  · 처리율 10Hz 99% / 28.7Hz 79.0% (천장 22~23Hz, 1장 44ms)
  · 임계값을 모두 풀어도 100% → 원래 값 유지 결론
- 로그 1초 스로틀 함정 추가: 로그로 처리율을 판단할 수 없음
- 함정 표 +2줄 (로그 스로틀, 노드 2개 통신 실패)
- usbipd 대역폭 가설 반증 수치 추가 (160x120 에서도 초록 71.7%)" || echo "  (커밋할 변경 없음)"

echo
echo "======================================================"
echo " 결과"
echo "======================================================"
git log --oneline -3
echo
echo "  README.md: $(wc -l < README.md)줄"
echo "  push: git push origin main"
