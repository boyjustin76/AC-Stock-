# -*- coding: utf-8 -*-
"""
신규안 v2 전통 — '차11-4 손익비' 모션(익절·손절 박스)을 전통 문법으로 다시 짓는 재료 (2026-09-14).

  python tools/style/trad_rr.py --cam <신규안_v2_전통/gen/newch-trad.json> --chart out/newch-trad/stills/trad_t0.00s.png --out C:/aelab/pack/trad_rr

옛 파일(C:/aelab/mogrt/차11-4 손익비.mogrt, tools/ae/jobs/a3_build.jsx)의 요소·등장 순서를 그대로 옮기고 모양만 바꾼다.
  매수 태그      → 매수 낙관               익절/손절 색박스(채움+굵은 선) → 적/쪽 담채 + 점선
  라벨판(익절/손절) → 오른쪽 낙관 열(익절·진입·손절)   진입 라인 → 먹선
  손익비 뱃지    → 손익비 현판(옻칠·금테)    익절 버튼 → 익절 낙관(청산 봉 위)
  놓친 구간 빗금 → 황 담채 + 먹 빗금        '놓친 구간' 글자 → 궁서 먹글씨     손그림 밑줄 → 인주 붓 밑줄
차트 바닥은 넣지 않는다 — 소스별로 잘라 쓴다(사용자 2026-09-14). 좌표만 v2 차트(카메라)에 맞춘다.

질감이 있는 것(낙관 면·담채·점선·빗금·붓 밑줄)은 PNG, 바꿔 쓸 글자는 AE 텍스트로 넘긴다.
그래서 낙관 PNG 는 **글자 없는 면**만 굽고, 대조용 기준(_ref.png)은 글자까지 합성기로 그린다.
출력: <out>/footage/*.png · rr.json · rr.jsx · _ref.png(투명 기준) · _ref_on_chart.png(배치 확인용)
"""
import argparse, io, json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trad as T

W, H, FPS, FRAMES = T.W, T.H, 30, 176      # 옛 컴포지션과 같은 길이 (176프레임)
OUT_AT = (155, 165)                        # 옛 퇴장 5.15~5.5초


def hx(c):
    return '#%02X%02X%02X' % c


def crop_box(layer, pad=2):
    b = layer.getbbox()
    return (max(0, b[0] - pad), max(0, b[1] - pad), min(W, b[2] + pad), min(H, b[3] + pad))


def ink_offset(font, text):
    """anchor='mm' 로 찍었을 때 잉크 상자 중심이 기준점에서 얼마나 떨어지나 — AE 는 잉크 상자로 가운데를 맞춘다"""
    l, t, r, b = font.getbbox(text, anchor='mm')
    return (l + r) / 2.0, (t + b) / 2.0


def dashed(canvas, x0, x1, y, width, color, dash):
    T.ink_line(ImageDraw.Draw(canvas), x0, x1, y, width, color, dash=dash)


def hatch(canvas, box, wash_color=T.YEL, wash_alpha=40, line_color=T.INK, line_alpha=52, gap=22, width=2):
    """놓친 구간: 황 담채 + 45° 먹 빗금 (상자 밖으로 안 나가게 자른다)"""
    T.wash(canvas, box, wash_color, wash_alpha, radius=6)
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    hh = y1 - y0
    ln = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ln)
    k = 0
    while x0 - hh + k * gap < x1:
        sx = x0 - hh + k * gap
        d.line((sx, y1, sx + hh, y0), fill=line_color + (line_alpha,), width=width)
        k += 1
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rectangle((x0, y0, x1, y1), fill=255)
    a = np.minimum(np.array(ln.getchannel('A')), np.array(m))
    ln.putalpha(Image.fromarray(a))
    canvas.alpha_composite(ln)


def underline_pts(cx, cy, wid, steps=48):
    x = cx - wid / 2
    return [(x + wid * i / steps, cy + math.sin(i / steps * 7.3 + 1.1) * 3.2 + math.sin(i / steps * 2.1) * 2.4) for i in range(steps + 1)]


def brush_under(canvas, pts, color=T.RED, wmin=3.0, wmax=9.0):
    """인주 붓 밑줄 — 옛 손그림 밑줄과 같은 흔들림 식, 굵기는 가운데가 굵고 양끝이 가늘다"""
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    dense = []
    for i in range(len(pts) - 1):
        for s in range(6):
            u = s / 6.0
            dense.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u))
    dense.append(pts[-1])
    n = len(dense)
    for i, (px, py) in enumerate(dense):
        p = i / (n - 1)
        wd = wmin + (wmax - wmin) * (math.sin(math.pi * min(1, p * 1.15)) ** 0.6)   # 끝이 조금 더 가늘게 빠진다
        d.ellipse((px - wd / 2, py - wd / 2, px + wd / 2, py + wd / 2), fill=color + (225,))
    canvas.alpha_composite(ov.filter(ImageFilter.GaussianBlur(0.5)))
    return wmax


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cam', required=True)
    ap.add_argument('--chart', required=True)
    ap.add_argument('--bars', default='data/synth/newch-trad.json')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    foot = os.path.join(a.out, 'footage'); os.makedirs(foot, exist_ok=True)
    for f in os.listdir(foot):
        if f.endswith('.png'): os.remove(os.path.join(foot, f))

    cam = T.Cam(json.load(io.open(a.cam, encoding='utf-8'))['cuts'][0]['cam'])
    bars = json.load(io.open(a.bars, encoding='utf-8'))['bars']
    bar = lambda i: bars[i + T.WARM]
    # 청산 봉 = 진입 뒤 처음 익절가에 닿은 봉 · 놓친 고점 = 그 뒤 최고가 (옛 컷②: 53봉 · 24,418.25)
    exit_bar = next(i for i in range(45, 64) if bar(i)['h'] >= T.LV_TARGET)
    missed_hi = max(bar(i)['h'] for i in range(exit_bar, 64))

    xr = cam.x(63) + cam.BW * 0.8          # trad.toolkit_layers 와 같은 자리
    xs = xr + 132
    x44 = cam.x(44) - cam.BW / 2
    yT, yE, yS = cam.y(T.LV_TARGET), cam.y(T.LV_ENTRY), cam.y(T.LV_STOP)
    xX, yHi, yMiss = cam.x(exit_bar), cam.y(bar(exit_bar)['h']), cam.y(missed_hi)

    items, ref = [], Image.new('RGBA', (W, H), (0, 0, 0, 0))
    refs = os.path.join(a.out, 'refs'); os.makedirs(refs, exist_ok=True)
    for f in os.listdir(refs):
        os.remove(os.path.join(refs, f))

    def R(slug, draw, seed=None):
        """대조 기준을 요소마다 따로 그려 refs/<slug>.png 로 남기고 전체 기준(ref)에 얹는다 — 소스 컴포지션 캡처와 1:1 로 댄다"""
        if seed is not None:
            np.random.seed(seed)
        L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); draw(L)
        path = os.path.join(refs, slug + '.png')
        if os.path.exists(path):                    # 한 소스가 여러 조각(담채+선)이면 이어 붙인다
            prev = Image.open(path).convert('RGBA'); prev.alpha_composite(L); prev.save(path)
        else:
            L.save(path)
        ref.alpha_composite(L)

    def png(name, draw, seed):
        np.random.seed(seed)
        L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); draw(L)
        x0, y0, x1, y1 = crop_box(L)
        fn = name + '.png'
        L.crop((x0, y0, x1, y1)).save(os.path.join(foot, fn))
        return {'file': fn, 'x': x0, 'y': y0, 'w': x1 - x0, 'h': y1 - y0}

    def add_seal(slug, title, beat, cx, cy, text, color, w, h, size, tilt, alpha=235, seed=0):
        f = T.gung(size)
        face = png(slug + '_face', lambda c: T.seal(c, cx, cy, '', color, w, h, f, tilt=0, alpha=alpha), seed)
        R(slug, lambda c: T.seal(c, cx, cy, text, color, w, h, f, tilt=tilt, alpha=alpha), seed)
        dx, dy = ink_offset(f, text)
        items.append(dict(id=slug, title=title, kind='seal', beat=beat, intro=10, cx=cx, cy=cy, text=text, size=size,
                          color=hx(color), fg=hx(T.HANJI2), tilt=tilt, sw=w, sh=h, pad=w - T.tw(f, text),
                          tdx=dx, tdy=2 + dy, face=face, box=[cx - w / 2 - 12, cy - h / 2 - 12, cx + w / 2 + 12, cy + h / 2 + 12]))

    def add_wipe(slug, title, beat, dur, direction, parts, seed):
        layers = []
        for k, (nm, draw, color) in enumerate(parts):
            p = png('%s_%s' % (slug, nm), draw, seed + k)
            p['fill'] = hx(color) if color else None
            p['name'] = nm
            R(slug, draw, seed + k)
            layers.append(p)
        bx = [min(p['x'] for p in layers), min(p['y'] for p in layers), max(p['x'] + p['w'] for p in layers), max(p['y'] + p['h'] for p in layers)]
        items.append(dict(id=slug, title=title, kind='wipe', beat=beat, intro=dur, dir=direction, layers=layers, box=bx))

    # ── 바닥에서 위로 (옛 a3_build 순서와 등장 시각) ──
    add_wipe('sl_box', '손절 박스', 21, 12, 'lr', [
        ('zone', lambda c: T.wash(c, (x44, yE, xr, yS), T.JJOK, 30), T.JJOK),
        ('line', lambda c: dashed(c, x44, xs - 50, yS, 2, T.JJOK, (10, 8)), T.JJOK)], 11)
    add_wipe('tp_box', '익절 박스', 9, 12, 'lr', [
        ('zone', lambda c: T.wash(c, (x44, yT, xr, yE), T.RED, 34), T.RED),
        ('line', lambda c: dashed(c, x44, xs - 50, yT, 2, T.RED, (10, 8)), T.RED)], 21)
    add_wipe('entry', '진입선', 9, 12, 'lr', [
        ('line', lambda c: T.ink_line(ImageDraw.Draw(c), x44, xs - 50, yE, 3), T.INK)], 31)
    add_wipe('missed', '놓친 구간', 107, 27, 'bt', [
        ('hatch', lambda c: hatch(c, (xX, yMiss, xr, yT)), None)], 41)

    # 손익비 현판 — 오른쪽 낙관 열 아래
    rr_text, rr_size = '손익비  1 : 2', 36
    fp = T.gung(rr_size)
    pw, ph = T.tw(fp, rr_text) + 64, rr_size + 40
    px, py = xs - pw / 2, yS + 42
    R('rr', lambda c: T.hyeonpan(c, px, py, rr_text, rr_size), 51)
    dx, dy = ink_offset(fp, rr_text)
    items.append(dict(id='rr', title='손익비 현판', kind='plate', beat=39, intro=12, cx=xs, top=py, text=rr_text, size=rr_size,
                      pad=64, ph=ph, tdx=dx, tdy=1 + dy, bg=hx(T.LACQ), gold=hx(T.GOLD), fg=hx(T.HANJI2),
                      box=[px - 8, py - 8, px + pw + 14, py + ph + 16]))

    add_seal('tp_seal', '익절 낙관', 19, xs, yT, '익절', T.RED, 96, 50, 32, 0, seed=61)
    add_seal('entry_seal', '진입 낙관', 22, xs, yE, '진입', T.INK, 96, 50, 32, 0, alpha=210, seed=62)
    add_seal('sl_seal', '손절 낙관', 31, xs, yS, '손절', T.JJOK, 96, 50, 32, 0, seed=63)
    add_seal('buy', '매수 낙관', 0, cam.x(43), yS + 108, '매수', T.RED, 104, 104, int(104 * 0.48), -5, seed=64)
    add_seal('exit', '익절 실행 낙관', 99, xX, yHi - 39, '익절', T.RED, 96, 50, 32, 4, seed=65)

    # 놓친 구간 문구 + 붓 밑줄 — 빗금 왼쪽 위 빈자리 (캔들이 지나가는 빗금 안은 피한다)
    nt, ns = '놓친 구간', 44
    fn_ = T.gung(ns)
    nw = T.tw(fn_, nt)
    ncx, ncy = xX - 92 - nw / 2, yMiss + 16     # 밑줄 오른끝과 익절 실행 낙관 사이 35px
    R('note', lambda c: T.btext(c, (ncx, ncy), nt, fn_, T.INK, anchor='mm', halo=T.HANJI))
    dx, dy = ink_offset(fn_, nt)
    items.append(dict(id='note', title='놓친 구간 문구', kind='note', beat=122, intro=13, cx=ncx, cy=ncy, text=nt, size=ns,
                      tdx=dx, tdy=dy, fill=hx(T.INK), halo=hx(T.HANJI), box=[ncx - nw / 2 - 8, ncy - 34, ncx + nw / 2 + 8, ncy + 34]))

    pts = underline_pts(ncx, ncy + 36, nw + 12)
    p = png('under', lambda c: brush_under(c, pts), 71)
    R('under', lambda c: brush_under(c, pts), 71)
    items.append(dict(id='under', title='붓 밑줄', kind='brush', beat=129, intro=11, layer=p, fill=hx(T.RED),
                      pts=[[round(x, 2), round(y, 2)] for x, y in pts], stroke=9 * 2 + 10, box=[p['x'], p['y'], p['x'] + p['w'], p['y'] + p['h']]))

    ref.save(os.path.join(a.out, '_ref.png'))
    # 배치 확인용 — v2 차트(한지 + 곱하기 차트) 위에 얹은 그림. 납품물엔 바닥이 없다.
    np.random.seed(7)
    base = T.hanji().convert('RGB')
    from PIL import ImageChops
    chart = Image.open(a.chart).convert('RGB')
    base = ImageChops.multiply(base, chart).convert('RGBA')
    base.alpha_composite(ref)
    base.convert('RGB').save(os.path.join(a.out, '_ref_on_chart.png'))

    order = ['buy', 'tp_box', 'entry', 'tp_seal', 'sl_box', 'entry_seal', 'sl_seal', 'rr', 'exit', 'missed', 'note', 'under']
    items.sort(key=lambda i: order.index(i['id']))
    man = {'fps': FPS, 'frames': FRAMES, 'out': list(OUT_AT), 'w': W, 'h': H, 'name': '차11-4 손익비 (전통)',
           'geo': dict(x44=x44, xr=xr, xs=xs, yT=yT, yE=yE, yS=yS, exit_bar=exit_bar, xX=xX, yHi=yHi, missed_hi=missed_hi, yMiss=yMiss),
           'items': items}
    io.open(os.path.join(foot, 'rr.json'), 'w', encoding='utf-8').write(json.dumps(man, ensure_ascii=False, indent=1))
    io.open(os.path.join(foot, 'rr.jsx'), 'w', encoding='ascii').write('var RR = ' + json.dumps(man, ensure_ascii=True) + ';\n')
    print('청산 봉', exit_bar, '놓친 고점', missed_hi, '| 소스', len(items), [i['title'] for i in items])


if __name__ == '__main__':
    main()
