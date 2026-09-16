# -*- coding: utf-8 -*-
"""롤링 광고 배너 검사 — 본문 글자 오른쪽 끝 ↔ CTA 현판 왼쪽 바깥 변 간격.

  python tools/style/roll_ad_check.py


주의 — 한지 결(닥종이 섬유)이 합 419 근처라 느슨한 기준(<420)으로 재면 **섬유를 글자로 잡는다.**
글자는 먹 #1C1A17(합 85) · 인주 #D42A26(합 292) · 단청 황 #9E7B12(합 299) 이므로 합 310 으로 끊는다.
게다가 글자는 세로로 이어지므로 '세로 6px 이상 이어진 열'만 인정한다.

⚠ 다만 이 모양 조건은 **참을 거짓으로 만들 수도 있다.** 문장 끝이 마침표나 가운뎃점처럼
   짧은 글자면 섬유와 함께 걸러진다. 숫자가 의심스러우면 원본 해상도로 잘라 눈으로 본다.

실제 이력 (2026-09-16) — "본문이 현판에 붙는다(3px)" 보고를 처음엔 섬유 오검출로 봤는데,
그 시점 코드를 git 에서 꺼내 되살려 재보니 라이브_a_2 는 **진짜로 붙어 있었다**
(임계 3가지 × 세로조건 2가지 = 6조합 전부 3~4px). 같이 온 라이브_B_2 의 13px 만 섬유였다.
한 메시지에 온 두 건을 하나로 묶어 판단한 것이 잘못이었다.
"""
import io, os, sys
import numpy as np
from PIL import Image
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
OUT = "C:/Users/user/Desktop/이정찬/차트명가NEW_통합/01_납품_차트명가NEW/라이브화면/롤링광고"

def ink_cols(a, x1):
    m = (a[:, :x1].sum(axis=2) < 310)
    # 세로로 6px 이상 이어진 것만 (섬유 점 배제)
    k = m.copy()
    for s in range(1, 6):
        k[:-s] &= m[s:]
    return np.flatnonzero(k.any(axis=0))

def plaque_x0(a, W):
    dark = (a.sum(axis=2) < 200)
    colr = dark.mean(axis=0) > 0.35
    runs, s = [], None
    for x, v in enumerate(list(colr) + [False]):
        if v and s is None: s = x
        elif not v and s is not None:
            runs.append((s, x - 1)); s = None
    tall = [r for r in runs if r[0] > W * 0.55]
    # 현판이 진짜 있으려면 **폭 150 이상 이어진 어두운 덩어리**가 하나는 있어야 한다.
    # (글자 획도 어두워서, 이 조건이 없으면 제목만 있는 판에서 헛검출이 난다 — B 가 겪은 그것)
    if not tall or not any(e - s >= 150 for s, e in tall):
        return None
    # 판은 여러 덩어리로 쪼개지므로 오른쪽 무리의 맨 앞 시작점
    return tall[0][0]

for sub in ("원본(방송 라이브 버전)_long", "원본(하이라이트 버전)_short"):
    for f in sorted(os.listdir(os.path.join(OUT, sub))):
        if not f.endswith(".jpg"): continue
        a = np.asarray(Image.open(os.path.join(OUT, sub, f)).convert("RGB")).astype(np.int16)
        W = a.shape[1]
        px0 = plaque_x0(a, W)
        if px0 is None:
            print("  %-20s 현판 없음" % f); continue
        cols = ink_cols(a, px0 - 2)
        end = int(cols[-1]) if cols.size else 0
        gap = px0 - end
        s = gap * 1920.0 / W
        mark = "붙음!!" if s < 8 else ("좁음" if s < 16 else "ok")
        print("  %-20s 판 x%4d · 글자 끝 %4d · 사이 %4dpx (1920환산 %5.1f) %s" % (f, px0, end, gap, s, mark))
