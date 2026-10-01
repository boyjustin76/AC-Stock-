# -*- coding: utf-8 -*-
"""
신규안 v2 전통 — 박스권 세트 · 더블 볼린저밴드 시안 스틸 (2026-09-15).
AE 는 사용자가 쓰는 중이라 합성기 스틸로 먼저 보여 주고, 고르면 AE 소스(aep·mogrt)로 옮긴다.

  python tools/style/trad_bands.py --cam <신규안_v2_전통/gen/newch-trad.json> --chart out/newch-trad/stills/trad_t0.00s.png --out <폴더> [--inner 0.5 --outer 3]

박스권
  팀장 규칙 ②(brand/EDIT-RULEBOOK.md: 박스권은 검은 선) → 먹(INK) 버튼 '박스 상단'·'박스 하단'(왼쪽 열 x=166)
  + 버튼과 같은 굵은 인주 선 두 줄(화면 전체) + 그 사이 먹 박스(선명한 단색 — 불투명도는 편집자가, 손익비 4차 요청과 같은 방식).
  가격은 v2 합성 시장의 횡보 구간(28~43봉)에서 잰 상단 23,855 · 하단 23,700.

더블 볼린저밴드
  차명03 대본 '지표 설정 팩트': 내부 밴드(20, σ0.5) · 외부 밴드(20, σ3). 차트를 중립 · 매수 우위 · 매도 우위로 나눈다.
  색은 brand/FX-WHITELIST.md #6(매수 우위 = 분홍 대면적 · 매도 우위 = 파랑 · 중립 = 밴드 안)을 전통 팔레트로 — 적 / 쪽 / 비움.
  선은 먹: 외부 밴드 굵게(7px) · 내부 밴드 가늘게(4px) · 중심선(20봉 단순평균) 점선. 구간 이름 낙관은 밴드 오른끝 바깥.
"""
import argparse, io, json, math, os, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trad as T
import trad_rr as RR

W, H = T.W, T.H
XB = RR.XB
BOX_TOP, BOX_BOT = 23855, 23700


def seal_cut(y, w, h, font, color, seed):
    """버튼 면 안쪽 자리 (선에서 비울 곳) — trad_rr.add_set 과 같은 방법"""
    np.random.seed(seed)
    tile = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    T.seal(tile, XB, y, '', color, w, h, font, tilt=0, alpha=255)
    return (tile.getchannel('A').filter(ImageFilter.GaussianBlur(2))
            .point(lambda v: 255 if v > 150 else 0).filter(ImageFilter.MinFilter(5)))


def ink_path(canvas, pts, thick, color, alpha=235):
    """차트를 따라가는 굵은 인주 선 — seal_line 과 같은 재질(가장자리 침식·빈틈)"""
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    d.line(pts, fill=255, width=int(round(thick)), joint='curve')
    r = thick / 2.0
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=255)
    m = T.rough_mask(m, blur=1.2, erode=0.45, holes=0.02)
    face = Image.new('RGBA', (W, H), color + (0,))
    face.putalpha(m.point(lambda v: v * alpha // 255))
    canvas.alpha_composite(face)


def dashed_path(canvas, pts, width, color, dash=(14, 10), alpha=220):
    """중심선 점선 — 꺾은선 길이를 따라 dash/gap 을 번갈아 긋는다"""
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    on, pos, cycle = True, 0.0, dash[0]
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        t = 0.0
        while t < seg:
            step = min(cycle - pos, seg - t)
            if on:
                a, b = t / seg, (t + step) / seg
                d.line((x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b),
                       fill=color + (alpha,), width=width)
            t += step
            pos += step
            if pos >= cycle - 1e-6:
                on, pos = not on, 0.0
                cycle = dash[0] if on else dash[1]
    canvas.alpha_composite(ov)


def fill_between(canvas, upper, lower, color, alpha):
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).polygon(list(upper) + list(reversed(lower)), fill=color + (alpha,))
    canvas.alpha_composite(ov)


def labeled_seal(canvas, cx, cy, text, color, seed, alpha=235):
    f = T.gung(32)
    w = T.tw(f, text) + 32
    np.random.seed(seed)
    T.seal(canvas, cx, cy, text, color, w, 50, f, tilt=0, alpha=alpha)
    return w


def box_set(canvas, cam, box_alpha):
    """박스권 세트: 먹 박스(바닥) → 두 선 → 두 버튼(맨 위)"""
    yU, yL = cam.y(BOX_TOP), cam.y(BOX_BOT)
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle((0, round(yU), W, round(yL)), fill=T.INK + (box_alpha,))
    canvas.alpha_composite(ov)
    f = T.gung(32)
    for k, (y, text) in enumerate(((yU, '박스 상단'), (yL, '박스 하단'))):
        w = T.tw(f, text) + 32
        cut = seal_cut(y, w, 50, f, T.INK, 300 + k)
        np.random.seed(310 + k)
        RR.seal_line(canvas, y, 13, T.INK, 235, cut)
    for k, (y, text) in enumerate(((yU, '박스 상단'), (yL, '박스 하단'))):
        w = T.tw(f, text) + 32
        np.random.seed(300 + k)
        T.seal(canvas, XB, y, text, T.INK, w, 50, f, tilt=0)
    return yU, yL


def bands(cam, bars, n, k_in, k_out, b0=12, b1=63):
    closes = [b['c'] for b in bars]
    rows = []
    for b in range(b0, b1 + 1):
        i = b + T.WARM
        win = closes[i - n + 1:i + 1]
        m = sum(win) / n
        sd = math.sqrt(sum((x - m) ** 2 for x in win) / n)
        rows.append((cam.x(b), m, m + k_out * sd, m + k_in * sd, m - k_in * sd, m - k_out * sd))
    pick = lambda j: [(x, cam.y(r[j])) for (x, *_), r in zip(rows, rows)]
    return rows, {'mid': pick(1), 'up_o': pick(2), 'up_i': pick(3), 'lo_i': pick(4), 'lo_o': pick(5)}


def double_bb(canvas, cam, bars, k_in, k_out, zone_alpha):
    rows, P = bands(cam, bars, 20, k_in, k_out)
    fill_between(canvas, P['up_o'], P['up_i'], T.RED, zone_alpha)     # 매수 우위 (상단 존)
    fill_between(canvas, P['lo_i'], P['lo_o'], T.JJOK, zone_alpha)    # 매도 우위 (하단 존)
    np.random.seed(401); ink_path(canvas, P['up_o'], 7, T.INK)
    np.random.seed(402); ink_path(canvas, P['lo_o'], 7, T.INK)
    np.random.seed(403); ink_path(canvas, P['up_i'], 4, T.INK, 215)
    np.random.seed(404); ink_path(canvas, P['lo_i'], 4, T.INK, 215)
    dashed_path(canvas, P['mid'], 3, T.INK)
    # 구간 이름 낙관 — 밴드 오른끝 바깥, 각 구간의 세로 가운데
    xl = P['mid'][-1][0] + 120
    yc_up = (P['up_o'][-1][1] + P['up_i'][-1][1]) / 2
    yc_lo = (P['lo_i'][-1][1] + P['lo_o'][-1][1]) / 2
    labeled_seal(canvas, xl, yc_up, '매수 우위', T.RED, 411)
    labeled_seal(canvas, xl, P['mid'][-1][1], '중립', T.INK, 412, alpha=210)
    labeled_seal(canvas, xl, yc_lo, '매도 우위', T.JJOK, 413)
    last = rows[-1]
    return dict(xl=xl, 외부상단=last[2], 내부상단=last[3], 중심=last[1], 내부하단=last[4], 외부하단=last[5])


def caption(canvas, text):
    T.btext(canvas, (40, 50), text, T.gung(34), T.INK, anchor='lm', halo=T.HANJI)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cam', required=True)
    ap.add_argument('--chart', required=True)
    ap.add_argument('--bars', default='data/synth/newch-trad.json')
    ap.add_argument('--out', required=True)
    ap.add_argument('--inner', type=float, default=0.5, help='내부 밴드 표준편차 (차명03 대본 0.5)')
    ap.add_argument('--outer', type=float, default=3.0, help='외부 밴드 표준편차 (차명03 대본 3)')
    a = ap.parse_args()
    # 윈도우는 경로 끝의 공백·마침표를 조용히 떼어 낸다 — 만들 때 떼지 않으면
    # 끝 공백은 그 뒤 파일 쓰기가 FileNotFoundError 로 터지고, 끝 마침표는
    # 아무 소리 없이 다른 이름의 폴더에 쌓인다 (B·E 실측 + D 재현 2026-09-18).
    a.out = a.out.rstrip(' .')
    os.makedirs(a.out, exist_ok=True)
    cam = T.Cam(json.load(io.open(a.cam, encoding='utf-8'))['cuts'][0]['cam'])
    bars = json.load(io.open(a.bars, encoding='utf-8'))['bars']
    np.random.seed(7)
    base = ImageChops.multiply(T.hanji().convert('RGB'), Image.open(a.chart).convert('RGB')).convert('RGBA')

    for alpha, fn, note in ((255, '시안A_박스권_기본100.png', '기본 불투명 100%'), (77, '시안A_박스권_불투명도30.png', '박스 불투명도 30% 로 내린 예')):
        c = base.copy()
        yU, yL = box_set(c, cam, alpha)
        caption(c, '시안 A · 박스권 세트 (%s) — 상단 %s · 하단 %s' % (note, format(BOX_TOP, ','), format(BOX_BOT, ',')))
        c.convert('RGB').save(os.path.join(a.out, fn))

    c = base.copy()
    info = double_bb(c, cam, bars, a.inner, a.outer, 90)
    caption(c, '시안 B · 더블 볼린저밴드 — 내부(20, σ%g) · 외부(20, σ%g)' % (a.inner, a.outer))
    c.convert('RGB').save(os.path.join(a.out, '시안B_더블볼린저.png'))
    print('박스권 y', round(yU, 1), round(yL, 1))
    print('볼린저 오른끝', {k: round(v, 1) for k, v in info.items()})


if __name__ == '__main__':
    main()
