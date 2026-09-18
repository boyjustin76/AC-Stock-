"""찍은 MT5 차트에서 봉 격자와 가격축을 스스로 맞춘다.

왜 이렇게 하나
 - 이동평균선이 봉과 **같은 빨강**이라 색만으로는 못 가른다. 그래서
   ① 청록(상승봉)만으로 칸 간격을 먼저 구하고 (이동평균에는 청록이 없다)
   ② 칸 **중심 열**에서 가장 긴 세로 줄기(꼬리+몸통)만 봉으로 본다. 지나가는 이동평균은 떼어 낸다.
 - 그 다음 실제 OHLC 를 받아 고가·저가 픽셀에 최소제곱 직선을 맞춰 가격→y 를 구한다.

쓰기: python mt5_calib.py <차트.png> <가격판_아래y> <심볼> <주기> <from> <to>
"""
import io
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import MT5  # noqa: E402

RED = (255, 0, 0)
TEAL = (0, 128, 128)


def runs(px, x, bottom, colors, min_len):
    """세로로 이어진 색 줄기 목록 [(y0, y1)]."""
    out, y = [], 0
    while y < bottom:
        if px[x, y] in colors:
            y0 = y
            while y < bottom and px[x, y] in colors:
                y += 1
            if y - y0 >= min_len:
                out.append((y0, y - 1))
        else:
            y += 1
    return out


def bar_pitch(px, W, bottom):
    """청록(상승봉)만 써서 칸 간격을 구한다 — 이동평균은 청록이 아니다."""
    cols = [x for x in range(W) if runs(px, x, bottom, {TEAL}, 3)]
    groups, cur = [], [cols[0]]
    for a, b in zip(cols, cols[1:]):
        if b - a <= 1:
            cur.append(b)
        else:
            groups.append(cur)
            cur = [b]
    groups.append(cur)
    centers = [sum(g) / len(g) for g in groups if len(g) >= 4]
    diffs = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
    lo = min(diffs)
    small = sorted(d for d in diffs if d <= lo * 1.6)
    return small[len(small) // 2], centers


def read_bars(img_path, pane_bottom):
    im = Image.open(img_path).convert('RGB')
    px = im.load()
    W, H = im.size
    bottom = min(pane_bottom, H)
    pitch, centers = bar_pitch(px, W, bottom)
    phase = sorted(c % pitch for c in centers)[len(centers) // 2]
    bars = []
    i = 0
    while True:
        cx = phase + i * pitch
        if cx > W - 4:
            break
        got = []
        for dx in (-1, 0, 1):
            x = int(round(cx)) + dx
            if 0 <= x < W:
                got += runs(px, x, bottom, {RED, TEAL}, 3)
        if got:
            longest = max(got, key=lambda r: r[1] - r[0])
            # 가장 긴 줄기(꼬리)에 붙어 있는 것만 합친다 — 지나가는 이동평균선을 뺀다
            keep = [r for r in got if not (r[1] < longest[0] - 2 or r[0] > longest[1] + 2)]
            bars.append({'slot': i, 'x': cx,
                         'y_high': min(r[0] for r in keep), 'y_low': max(r[1] for r in keep)})
        i += 1
    return (W, H), pitch, phase, bars


def fetch(symbol, period, dt_from, dt_to):
    return MT5().history(symbol, period, dt_from, dt_to)


def fit(bars, hist):
    span = bars[-1]['slot'] + 1
    best = None
    for s in range(0, len(hist) - span + 1):
        xs, ys = [], []
        for b in bars:
            h = hist[s + b['slot']]
            xs += [h['high'], h['low']]
            ys += [b['y_high'], b['y_low']]
        k = len(xs)
        mx, my = sum(xs) / k, sum(ys) / k
        sxx = sum((v - mx) ** 2 for v in xs)
        if sxx == 0:
            continue
        a = sum((xs[i] - mx) * (ys[i] - my) for i in range(k)) / sxx
        b0 = my - a * mx
        res = sum((ys[i] - (a * xs[i] + b0)) ** 2 for i in range(k)) / k
        if best is None or res < best[0]:
            best = (res, s, a, b0)
    return best


if __name__ == '__main__':
    img, pane_bottom = sys.argv[1], int(sys.argv[2])
    size, pitch, phase, bars = read_bars(img, pane_bottom)
    print(f'그림 {size} · 칸 간격 {pitch:.2f}px · 기준 x {phase:.1f} · '
          f'칸 {bars[-1]["slot"] + 1}개 중 봉 {len(bars)}개')
    hist = fetch(*sys.argv[3:7])
    print(f'받은 봉 {len(hist)}개 ({hist[0]["time"]} ~ {hist[-1]["time"]})')
    res, s, a, b0 = fit(bars, hist)
    print(f'맞춘 자리: {hist[s]["time"]} ~ {hist[s + bars[-1]["slot"]]["time"]}')
    print(f'  가격→y: y = {a:.6f} * price + {b0:.3f}  (RMS {res ** 0.5:.2f}px)')
    io.open('calib.json', 'w', encoding='utf-8').write(json.dumps({
        'image': img, 'size': size, 'pitch': pitch, 'phase': phase, 'a': a, 'b': b0,
        'symbol': sys.argv[3], 'period': sys.argv[4], 'first_time': hist[s]['time'],
        'rms': res ** 0.5,
        'bars': [{'slot': b['slot'], 'x': b['x'], 'time': hist[s + b['slot']]['time'],
                  'high': hist[s + b['slot']]['high'], 'low': hist[s + b['slot']]['low'],
                  'close': hist[s + b['slot']]['close']} for b in bars],
    }, ensure_ascii=False))
    print('  calib.json 저장')
