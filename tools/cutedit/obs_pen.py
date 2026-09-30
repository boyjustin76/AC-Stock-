# -*- coding: utf-8 -*-
"""OBS 화면녹화(MT5 차트)에서 **펜으로 그린 자국**이 있는 구간을 찾는다.

화면은 메타트레이더5다. 차트가 이미 빨강·파랑이라 '진한 색'만으로는 안 갈린다.
그래서 **차트가 쓰는 색(빨강 캔들·파랑 캔들)을 빼고** 남는 진한 색을 펜으로 본다.
펜 색은 회차마다 다르다 — 자홍·하늘색·노랑을 쓴다 (이정찬 2026-09-30).

  · 1초에 두 장만 본다(30fps 를 다 볼 필요가 없다)
  · 채도 높고 밝은 픽셀 중 빨강·파랑 대역을 뺀다
  · 점 하나짜리 경계 얼룩은 열림 연산으로 지우고, 25픽셀 이상 덩어리만 센다
  · 그 덩어리 넓이가 바탕보다 뚜렷이 크면 '그림 있음'

내놓는 것 (json)
  {"파일": …, "길이": 초, "그림구간": [[시작, 끝, 최대넓이], …], "자국": [[초, 넓이, 덩어리수], …]}
"""
import io, os, sys, json
import numpy as np
import cv2

간격 = 0.5
채도, 밝기 = 140, 120
덩어리최소 = 25
# 차트가 쓰는 색 — 빨강 캔들·빨강 밴드(0 부근, 179 부근), 파랑 캔들(100~132)
차트색 = [(0, 12), (168, 179), (100, 132)]


def 펜넓이(장):
    hsv = cv2.cvtColor(cv2.resize(장, (960, 540)), cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0].astype(np.int16), hsv[:, :, 1], hsv[:, :, 2]
    m = (s >= 채도) & (v >= 밝기)
    for 아래, 위 in 차트색:
        m &= ~((h >= 아래) & (h <= 위))
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    개수, _, 통계, _ = cv2.connectedComponentsWithStats(m, 8)
    넓이 = [int(통계[i, cv2.CC_STAT_AREA]) for i in range(1, 개수) if 통계[i, cv2.CC_STAT_AREA] >= 덩어리최소]
    return sum(넓이), len(넓이)


def 훑기(경로, 진행알림=300):
    cap = cv2.VideoCapture(경로)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    걸음 = max(1, int(round(fps * 간격)))
    자국, i, 다음 = [], 0, 진행알림
    while cap.grab():
        if i % 걸음 == 0:
            ok, 장 = cap.retrieve()
            if ok:
                넓이, 수 = 펜넓이(장)
                t = i / fps
                자국.append([round(t, 2), 넓이, 수])
                if t >= 다음:
                    print("   %.0f분" % (t / 60), flush=True); 다음 += 진행알림
        i += 1
    cap.release()
    return 자국, i / fps


def 그림구간(자국, 최소길이=2.0):
    값 = np.array([a for _, a, _ in 자국], dtype=np.float32)
    시각 = [t for t, _, _ in 자국]
    바탕 = np.percentile(값, 25)                       # 아무것도 안 그린 화면의 잡티
    켜짐 = 값 > 바탕 + 300
    구간, 시작 = [], None
    for i, on in enumerate(켜짐):
        if on and 시작 is None: 시작 = i
        elif not on and 시작 is not None:
            구간.append([시각[시작], 시각[i], int(값[시작:i].max())]); 시작 = None
    if 시작 is not None: 구간.append([시각[시작], 시각[-1], int(값[시작:].max())])
    # 사이가 5초 안쪽이면 같은 설명으로 묶는다
    묶음 = []
    for g in 구간:
        if 묶음 and g[0] - 묶음[-1][1] <= 5: 묶음[-1] = [묶음[-1][0], g[1], max(묶음[-1][2], g[2])]
        else: 묶음.append(g)
    return [g for g in 묶음 if g[1] - g[0] >= 최소길이]


if __name__ == "__main__":
    낼곳, 결과 = sys.argv[1], []
    for p in sys.argv[2:]:
        print("보는 중:", os.path.basename(p), flush=True)
        자국, 길이 = 훑기(p)
        구간 = 그림구간(자국)
        print("  그림 구간 %d개 · 합 %.1f분" % (len(구간), sum(b - a for a, b, _ in 구간) / 60), flush=True)
        결과.append({"파일": os.path.basename(p), "길이": round(길이, 2),
                     "그림구간": [[round(a, 2), round(b, 2), c] for a, b, c in 구간], "자국": 자국})
        json.dump(결과, io.open(낼곳, "w", encoding="utf-8"), ensure_ascii=False)
    print("냈다:", 낼곳)
