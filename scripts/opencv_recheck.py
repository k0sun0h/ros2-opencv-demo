#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
opencv_recheck.py — object_tracker.py 의 OpenCV 처리 구간만 떼어내
ROS2 없이 단독으로 재확인하는 스크립트.

왜 필요한가
    파이프라인에 문제가 났을 때 "ROS2 문제인가 / OpenCV 계산 문제인가" 를
    갈라내려면 ROS2 를 빼고 OpenCV 만 돌려봐야 한다. (면접 E2 의 그 방법)
    여기 숫자는 object_tracker.py 와 '똑같은' 기본값을 쓴다.

쓰는 법
    # 0) 먼저 자체 검증 — 합성 이미지로 파이프라인 자체를 확인 (ROS2·영상 불필요)
    python3 opencv_recheck.py --selftest

    # 1) 실제 이미지 1장 (예: 이전에 저장해둔 frame.png)
    python3 opencv_recheck.py --image frame.png

    # 2) 녹화해둔 mp4 — 몇 프레임마다 통계
    python3 opencv_recheck.py --video sample.mp4 --every 10

    # 3) 임계값 실험 (파라미터를 바꿔서 검출률이 오르는지)
    python3 opencv_recheck.py --video sample.mp4 --hmin 100 --hmax 140 --smin 80 --vmin 60

    # 4) 특정 픽셀의 HSV 가 궁금할 때 (범위를 어디로 잡아야 하나?)
    python3 opencv_recheck.py --image frame.png --hsv-probe 320 240

종료코드: 0 = 정상 / 1 = 실패
"""

import argparse
import sys

import numpy as np
import cv2

# ---------------------------------------------------------------- 기본값
# object_tracker.py 와 똑같아야 비교가 의미를 가진다. 여기를 고치면 비교 불가.
H_MIN, H_MAX = 90, 130
S_MIN, V_MIN = 100, 100
MORPH_K = 5
MIN_AREA = 100.0

# usbipd 등시성 버그의 상징색: YUV(0,0,0) -> RGB(0,135,0)
GREEN_BGR = np.array([0, 135, 0], dtype=np.int16)


# ---------------------------------------------------------------- 핵심 처리
def process(frame, hmin=H_MIN, hmax=H_MAX, smin=S_MIN, vmin=V_MIN,
            morph_k=MORPH_K, min_area=MIN_AREA):
    """object_tracker.image_callback 과 '같은 순서'로 처리하고 결과를 dict 로."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lo = np.array([hmin, smin, vmin], dtype=np.uint8)
    hi = np.array([hmax, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lo, hi)

    if morph_k > 0:
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_OPEN, np.ones((morph_k, morph_k), np.uint8))

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    areas = sorted((cv2.contourArea(c) for c in cnts), reverse=True)

    out = {
        'hsv': hsv,
        'mask': mask,
        'n_contours': len(cnts),
        'top_areas': areas[:5],
        'coverage': float(mask.mean()) / 255.0 * 100.0,
        'center': None,
        'area': 0.0,
        'reason': '',
    }

    if not cnts:
        out['reason'] = '컨투어가 없음 (마스크가 비었거나 물체끼리 다 붙음)'
        return out

    c = max(cnts, key=cv2.contourArea)
    area = float(cv2.contourArea(c))
    out['area'] = area
    if area < min_area:
        out['reason'] = f'가장 큰 덩어리 {area:.0f} < min_area {min_area:.0f} (티끌만 있음)'
        return out

    M = cv2.moments(c)
    if M['m00'] == 0:
        out['reason'] = '면적은 있으나 m00=0 (선·점 형태라 중심을 못 구함)'
        return out

    out['center'] = (int(M['m10'] / M['m00']), int(M['m01'] / M['m00']))
    return out


def green_ratio(frame):
    """프레임이 초록(0,135,0)으로 덮였는지 %. usbipd 등시성 버그 판정용."""
    d = np.abs(frame.astype(np.int16) - GREEN_BGR.reshape(1, 1, 3)).sum(axis=2)
    return float((d < 40).mean() * 100.0)


# ---------------------------------------------------------------- 출력
def analyze(frame, args, tag='frame'):
    info = process(frame, args.hmin, args.hmax, args.smin, args.vmin,
                   args.morph, args.min_area)
    h, w = frame.shape[:2]
    gr = green_ratio(frame)

    print(f'--- {tag} ---')
    print(f'  해상도      : {w}x{h}')
    line = f'  초록 덮임   : {gr:5.1f}%'
    if gr > 50:
        line += '   <-- usbipd 등시성 의심 (영상파일 입력으로 우회할 것)'
    print(line)
    print(f'  마스크 점유 : {info["coverage"]:5.2f}%  (0%면 임계값이 안 맞음, 100%면 너무 느슨)')
    print(f'  컨투어 개수 : {info["n_contours"]}')
    if info['top_areas']:
        print('  상위 면적   : ' + ', '.join(f'{a:.0f}' for a in info['top_areas']))

    if info['center']:
        cx, cy = info['center']
        hh, ss, vv = info['hsv'][cy, cx]
        print(f'  중심        : ({cx}, {cy})   면적={info["area"]:.0f}')
        print(f'  중심 픽셀 HSV: ({hh}, {ss}, {vv})')
        print(f'  판정        : 검출 성공  '
              f'(H {args.hmin}~{args.hmax} / S>={args.smin} / V>={args.vmin})')
    else:
        print(f'  중심        : 없음')
        print(f'  판정        : 검출 실패 — {info["reason"]}')
    return info


# ---------------------------------------------------------------- 자체 검증
def make_synth_blue(center=(320, 240), radius=30,
                    bg=(50, 50, 50), fg=(200, 120, 60)):
    img = np.full((480, 640, 3), bg, dtype=np.uint8)
    cv2.circle(img, center, radius, fg, -1)
    return img


def make_synth_green_buffer(frac=0.9):
    """usbipd 버그 재현: 위쪽 frac 만큼이 초록으로 덮인 프레임."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:int(480 * frac), :] = (0, 135, 0)
    return img


def selftest(args):
    """ROS2 없이 파이프라인 자체를 검증한다. 통과하면 계산은 정상."""
    print('=' * 60)
    print('자체 검증 (합성 이미지) — ROS2 없이 OpenCV 계산만 확인')
    print('=' * 60)

    fails = []

    # 케이스 1: 파란 원 → 중심과 면적이 기대대로 나오나
    cx0, cy0, r0 = 320, 240, 30
    frame = make_synth_blue((cx0, cy0), r0)
    info = analyze(frame, args, 'case1: 파란 원 (BGR 200,120,60) r=30')

    if info['center'] is None:
        fails.append('case1: 검출 자체가 실패')
    else:
        cx, cy = info['center']
        if abs(cx - cx0) > 2 or abs(cy - cy0) > 2:
            fails.append(f'case1: 중심 오차 ({cx},{cy}) vs 기대 ({cx0},{cy0})')
        expect_area = 3.141592 * r0 * r0
        err = abs(info['area'] - expect_area) / expect_area * 100.0
        print(f'  면적 기대값 : {expect_area:.0f} (πr²) / 실제 {info["area"]:.0f} '
              f'/ 오차 {err:.1f}%')
        if err > 8.0:
            fails.append(f'case1: 면적 오차 {err:.1f}% > 8%')

    # 케이스 2: 파란 원 위치를 옮기면 따라가는가 (좌표 검증)
    cx0, cy0 = 100, 400
    frame = make_synth_blue((cx0, cy0), 25)
    info2 = analyze(frame, args, 'case2: 파란 원을 (100,400) 으로 이동')
    if info2['center'] is None:
        fails.append('case2: 검출 실패')
    elif abs(info2['center'][0] - cx0) > 2 or abs(info2['center'][1] - cy0) > 2:
        fails.append(f'case2: 중심이 안 따라감 {info2["center"]} vs ({cx0},{cy0})')

    # 케이스 3: 초록 덮임 프레임 → 초록으로 오검출하지 '않아야' 정상
    frame = make_synth_green_buffer()
    gr = green_ratio(frame)
    info3 = analyze(frame, args, 'case3: 초록 덮임 90% (usbipd 버그 재현)')
    print(f'  초록 판정   : {gr:.1f}%  (50% 초과면 정상 판정)')
    if gr < 50:
        fails.append(f'case3: 초록 덮임을 못 잡음 ({gr:.1f}%)')
    if info3['center'] is not None:
        fails.append('case3: 초록 프레임을 파란 물체로 오검출함')

    # 케이스 4: 마스크 점유율 0% (물체 없음) → 실패로 나와야 정상
    frame = np.full((480, 640, 3), (50, 50, 50), dtype=np.uint8)
    info4 = analyze(frame, args, 'case4: 물체 없는 회색 화면')
    if info4['center'] is not None:
        fails.append('case4: 빈 화면에서 검출됨 (오검출)')

    print('=' * 60)
    if fails:
        print('자체 검증 실패:')
        for f in fails:
            print('  - ' + f)
        return 1
    print('자체 검증 통과 — OpenCV 계산 경로는 정상.')
    print('이제 실제 이미지/영상으로 넘어가면 된다:')
    print('  python3 opencv_recheck.py --image frame.png')
    print('  python3 opencv_recheck.py --video sample.mp4 --every 10')
    return 0


# ---------------------------------------------------------------- 실행
def run_image(path, args):
    frame = cv2.imread(path)
    if frame is None:
        print(f'[실패] 이미지를 못 읽었습니다: {path}')
        return 1
    if args.hsv_probe:
        x, y = args.hsv_probe
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        print(f'HSV probe ({x},{y}) = {tuple(int(v) for v in hsv[y, x])}')
        print(f'BGR probe ({x},{y}) = {tuple(int(v) for v in frame[y, x])}')
    info = analyze(frame, args, f'이미지: {path}')
    if args.save_mask:
        cv2.imwrite(args.save_mask, info['mask'])
        print(f'  마스크 저장 : {args.save_mask}')
    return 0 if info['center'] else 1


def run_video(path, args):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f'[실패] 영상을 못 열었습니다: {path}')
        print('  WSL2 에서는 코덱 문제로 열리기도 합니다. mp4(H.264)로 다시 시도해보세요.')
        return 1

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f'영상: {path}   fps={fps:.1f}   총 {total_frames} 프레임')

    n = 0
    seen = 0
    hit = 0
    areas = []
    green_sum = 0.0
    first_saved = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        n += 1
        if n % max(1, args.every) != 0:
            continue

        info = process(frame, args.hmin, args.hmax, args.smin, args.vmin,
                       args.morph, args.min_area)
        seen += 1
        green_sum += green_ratio(frame)
        if info['center']:
            hit += 1
            areas.append(info['area'])
            if args.save_mask and not first_saved:
                cv2.imwrite(args.save_mask, info['mask'])
                print(f'  (검출 프레임의 마스크 저장: {args.save_mask})')
                first_saved = True
        elif seen == 1:
            analyze(frame, args, '첫 샘플 프레임 (검출 실패 — 원인 확인용)')

    cap.release()

    print('-' * 60)
    if seen == 0:
        print('[실패] 검사한 프레임이 0개입니다.')
        return 1

    rate = hit / seen * 100.0
    print(f'검사 프레임   : {seen}  (every={args.every})')
    print(f'검출 성공     : {hit}   검출률 {rate:.1f}%')
    print(f'평균 초록 덮임: {green_sum / seen:.1f}%')
    if areas:
        print(f'면적 최소/평균/최대 : {min(areas):.0f} / {sum(areas)/len(areas):.0f} / {max(areas):.0f}')
    print(f'임계값        : H {args.hmin}~{args.hmax}, S>={args.smin}, V>={args.vmin}')

    if rate >= 90:
        print('판정: 정상 (이전 통합 실행의 99% 와 같은 수준)')
        return 0
    if rate >= 50:
        print('판정: 부분 검출 — 임계값을 조정해보세요 (--hmin/--hmax/--smin/--vmin)')
        return 1
    print('판정: 검출률 낮음 — --hsv-probe 로 물체 픽셀의 HSV 를 직접 확인하세요')
    return 1


def main():
    p = argparse.ArgumentParser(
        description='object_tracker.py 의 OpenCV 처리만 ROS2 없이 재확인')
    src = p.add_mutually_exclusive_group()
    src.add_argument('--image', help='이미지 파일 1장')
    src.add_argument('--video', help='영상 파일 (mp4)')
    src.add_argument('--selftest', action='store_true',
                     help='합성 이미지로 파이프라인 자체 검증 (ROS2·영상 불필요)')

    p.add_argument('--every', type=int, default=1, help='영상에서 몇 프레임마다 검사 (기본 1)')
    p.add_argument('--hmin', type=int, default=H_MIN)
    p.add_argument('--hmax', type=int, default=H_MAX)
    p.add_argument('--smin', type=int, default=S_MIN)
    p.add_argument('--vmin', type=int, default=V_MIN)
    p.add_argument('--morph', type=int, default=MORPH_K, help='MORPH_OPEN 커널 크기 (0=끄기)')
    p.add_argument('--min-area', type=float, default=MIN_AREA)
    p.add_argument('--hsv-probe', nargs=2, type=int, metavar=('X', 'Y'),
                   help='그 픽셀의 BGR/HSV 를 출력')
    p.add_argument('--save-mask', help='마스크를 이 파일로 저장 (Notion 캡처용)')
    args = p.parse_args()

    print(f'OpenCV {cv2.__version__} / numpy {np.__version__}')

    if args.selftest:
        return selftest(args)
    if args.image:
        return run_image(args.image, args)
    if args.video:
        return run_video(args.video, args)

    print('무엇을 검사할지 정해주세요. 예:')
    print('  python3 opencv_recheck.py --selftest')
    print('  python3 opencv_recheck.py --image frame.png')
    print('  python3 opencv_recheck.py --video sample.mp4 --every 10')
    return 1


if __name__ == '__main__':
    sys.exit(main())
