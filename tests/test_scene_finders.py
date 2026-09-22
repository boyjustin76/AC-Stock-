# -*- coding: utf-8 -*-
"""대본→차트 장면 탐색(tools/mt5/scenes.py) 이 **아무 구간이나 뽑지 않는지** 잰다. MT5 없이 돈다.

09-22 차10 1-2 사고: 지지선 이탈·쓸림에 전용 탐색이 없어 '고점 뒤 하락' 계산을 빌려 썼고, 점수가 100% 로
꽉 차 아무 구간이나 뽑혔다(떨어졌다 다시 오르는 그림). 같은 일을 세 겹으로 막는다.

  ① 규칙에 있는 장면은 전부 **전용** 탐색이 있다 (등록돼 있고, 함수가 서로 다르다)
  ② 가짜 차트에 진짜 장면 하나 + **예전 구멍을 재현하는 미끼** 하나를 심고, 탐색이 진짜를 고른다
  ③ 점수는 비율이다 — 가격을 1000배 해도 같고, 0~1 안에 있다 (가격 그대로 쓰면 비싼 종목이 늘 이긴다)
     그리고 심은 장면에서 1등 점수가 여러 사건에 똑같이 몰리지 않는다

새 장면을 RULES 에 넣으면 ①이 깨진다 — FINDERS 에 전용 함수를 등록하고 여기 ②에 심은 장면을 하나 보태라.
"""
import math
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'mt5'))
S = pytest.importorskip('scenes')

PAGE = 110
HALF = PAGE // 2


# ─── 가짜 차트 만들기 ─────────────────────────────────────────────────

def bars_from(closes):
    out, prev = [], closes[0]
    for k, c in enumerate(closes):
        wick = 0.0005 * c                              # 꼬리도 가격 비례 — 1000배 시험에서 모양이 같아야 한다
        hi, lo = max(prev, c) + wick, min(prev, c) - wick
        out.append({'time': f'2026.09.{1 + k // 1440:02d} {(k // 60) % 24:02d}:{k % 60:02d}:00',
                    'open': prev, 'high': hi, 'low': lo, 'close': c})
        prev = c
    return out


def calm(n, level, rnd, amp=0.15):
    """아무 일도 없는 바탕 — 작게 떠는 제자리."""
    return [level + rnd.uniform(-amp, amp) for _ in range(n)]


def line(a, b, n):
    return [a + (b - a) * k / max(1, n - 1) for k in range(n)]


def zig(points, per):
    out = []
    for a, b in zip(points, points[1:]):
        out += line(a, b, per)[:-1]
    return out + [points[-1]]


def series(*parts):
    out = []
    for p in parts:
        out += p
    return out


def planted(name):
    """(closes, 진짜 장면 가운데 index). 앞뒤 바탕 + 진짜 + 바탕 + 미끼 + 바탕."""
    r = random.Random(7)
    L = 100.0
    if name == 'support_break':
        real = series(zig([L + 4, L, L + 4, L, L + 4, L, L + 3], 13), line(L + 3, L - 8, 32))
        decoy = series(line(L, L + 10, 45), line(L + 10, L - 2, 45))                    # 예전 1-2: 봉우리
    elif name == 'whipsaw':
        real = zig([L, L + 8, L, L + 8, L, L + 8, L, L + 8], 16)
        decoy = zig([L, L + 8, L, L + 8, L], 28)                                          # 매끈한 톱니 네 다리
    elif name == 'high_then_drop':
        real = series(line(L, L + 10, 50), line(L + 10, L, 50))
        decoy = line(L + 10, L, 100)                                                      # 그냥 내림 (고점이 맨 앞)
    elif name == 'zigzag3':
        real = zig([L, L - 8, L, L - 8, L], 27)
        decoy = zig([L, L - 2, L, L - 2, L], 27)                                          # 작은 톱니
    elif name == 'chop_box':
        # 박스 안은 몇 봉에 걸쳐 오르내린다 (봉마다 무작위로 떨면 '읽히는 움직임' 이 아니다)
        real = series(line(L, L + 20, 150), [L + 20 + 1.5 * math.sin(k / 3.5) for k in range(110)], line(L + 20, L + 40, 150))
        decoy = zig([L + 40, L + 48, L + 32, L + 48, L + 40], 27)                         # 예전 3-3: 넓게 출렁이는 제자리
    elif name == 'trend_burst':
        real = line(L, L + 20, 110)
        decoy = zig([L, L + 6, L, L + 6], 36)
    elif name == 'session_burst':
        real = series(calm(55, L, r, 0.1), zig([L, L + 6, L - 6, L + 6, L - 6, L], 11))
        decoy = zig([L, L + 6, L - 6, L + 6, L - 6, L + 6, L - 6, L + 6, L - 6, L], 12)    # 처음부터 끝까지 출렁
    elif name in ('ma_support_bounce', 'ma_resist_drop'):
        # 기울기 0.3/봉 오름세의 20이평은 약 2.85 아래를 따라온다 → 3 만큼 되돌리면 닿는다
        real = series(line(L, L + 18, 60), line(L + 18, L + 15, 6)[1:], line(L + 15, L + 30, 45)[1:])
        decoy = series(line(L, L + 18, 60), line(L + 18, L + 5, 15)[1:], line(L + 5, L + 10, 35)[1:])   # 이평선을 깊게 깨고 무너진다
        if name == 'ma_resist_drop':
            real, decoy = [2 * L - c for c in real], [2 * L - c for c in decoy]
    elif name in ('ma_break_down', 'ma_break_up'):
        real = series(line(L, L + 10, 55), line(L + 10, L - 12, 60)[1:])                                    # 뚫고 계속 내려간다
        decoy = series(line(L, L + 10, 55), line(L + 10, L + 7, 12)[1:], line(L + 7, L + 16, 48)[1:])     # 잠깐 뚫고 되돌아온다
        if name == 'ma_break_up':
            real, decoy = [2 * L - c for c in real], [2 * L - c for c in decoy]
    elif name == 'ma_flat_box':
        real = [L + 3 * math.sin(2 * math.pi * k / 22) for k in range(132)]
        decoy = [L + 0.25 * k + 3 * math.sin(2 * math.pi * k / 22) for k in range(132)]          # 오르는 추세 위의 출렁임
    else:
        raise KeyError(name)
    # 바탕은 진짜 장면의 **가운데 높이**에 둔다. 첫 가격(예: 박스 윗선)에 두면 바탕→장면 전환이
    # 그 자체로 지지선 이탈 모양이 된다 — 09-22 처음 짠 시험이 그랬다(탐색이 옳았다).
    midlv = (max(real) + min(real)) / 2
    pre = calm(280, midlv, r) + line(midlv, real[0], 20)[1:]     # 한 봉에 뛰지 않게 이어 준다
    mid = calm(200, real[-1], r)
    closes = series(pre, real, mid, [c - decoy[0] + real[-1] for c in decoy], calm(200, real[-1], r))
    return closes, len(pre) + len(real) // 2


def planted_ema(switch):
    """200EMA 아래서 오래 눕다가 강하게 올라 ADX 가 25 를 넘고, (switch 면) 되밀려 20EMA 를 깬다."""
    r = random.Random(3)
    L = 100.0
    base = [L + 0.4 * math.sin(k / 3) + r.uniform(-0.1, 0.1) for k in range(400)]
    up = line(L, L + 25, 40)
    tail = line(L + 25, L + 12, 40) if switch else line(L + 25, L + 30, 40)
    closes = series(base, up, tail, calm(200, tail[-1], r))
    return closes, len(base) + 20


NAMES = [r['name'] for r in S.RULES] + [S.FALLBACK['name']]
PLANTED = ['support_break', 'whipsaw', 'high_then_drop', 'zigzag3', 'chop_box', 'trend_burst', 'session_burst',
           'ma_support_bounce', 'ma_resist_drop', 'ma_flat_box', 'ma_break_down', 'ma_break_up']


# ─── ① 전용 탐색 ──────────────────────────────────────────────────────

def test_every_rule_has_its_own_finder():
    missing = sorted(set(NAMES) - set(S.FINDERS))
    assert not missing, f'전용 탐색이 없는 장면: {missing} — scenes.FINDERS 에 등록하라'
    fns = [S.FINDERS[n] for n in set(NAMES)]
    assert len({id(f) for f in fns}) == len(fns), '두 장면이 같은 탐색 함수를 쓴다 — 빌려 쓰지 않는다'


def test_every_rule_has_a_planted_scene():
    covered = set(PLANTED) | {'ema200_adx_entry', 'ema20_switch'}
    assert set(NAMES) <= covered, f'심은 장면 시험이 없는 장면: {sorted(set(NAMES) - covered)}'


def test_unknown_scene_is_an_error_not_a_guess():
    with pytest.raises(KeyError):
        S.find('없는_장면', bars_from(line(100, 110, 300)))


# ─── ② 심은 장면을 고르나 ────────────────────────────────────────────

@pytest.mark.parametrize('name', PLANTED)
def test_finds_the_planted_scene_not_the_decoy(name):
    closes, center = planted(name)
    cands = S.find(name, bars_from(closes), PAGE)
    assert cands, f'{name}: 후보가 없다'
    sc, i, note = cands[0]
    assert abs(i - center) <= HALF, f'{name}: 1등이 심은 자리({center})가 아니라 {i} — {note}'


@pytest.mark.parametrize('switch', [False, True])
def test_ema_scenes(switch):
    closes, center = planted_ema(switch)
    name = 'ema20_switch' if switch else 'ema200_adx_entry'
    cands = S.find(name, bars_from(closes), PAGE)
    assert cands, f'{name}: 후보가 없다'
    assert abs(cands[0][1] - center) <= PAGE, f'{name}: 1등 {cands[0][1]} · 심은 자리 {center}'


# ─── ③ 비율·몰림 ─────────────────────────────────────────────────────

@pytest.mark.parametrize('name', PLANTED)
def test_scores_are_ratios(name):
    closes, _ = planted(name)
    a = S.find(name, bars_from(closes), PAGE)
    b = S.find(name, bars_from([c * 1000 for c in closes]), PAGE)   # 1000배만 (더하면 꼬리 비율이 바뀐다)
    assert a and b
    assert abs(a[0][0] - b[0][0]) < 1e-6, f'{name}: 가격을 1000배 하니 점수가 {a[0][0]:.4f} → {b[0][0]:.4f} — 비율이 아니다'
    assert all(0 <= c[0] <= 1 for c in a), f'{name}: 점수가 0~1 밖이다'


@pytest.mark.parametrize('name', PLANTED)
def test_top_score_is_not_shared_by_many_events(name):
    closes, _ = planted(name)
    cands = S.find(name, bars_from(closes), PAGE)
    assert S.ties(cands, PAGE) < S.SATURATED, f'{name}: 1등 점수가 서로 다른 사건 {S.ties(cands, PAGE)}곳에 똑같다'


def test_direction_filter():
    closes = series(line(100, 120, 110), [120] * 100, line(120, 100, 110))
    bars = bars_from(closes)
    up = S.find('trend_burst', bars, PAGE, 'up')
    down = S.find('trend_burst', bars, PAGE, 'down')
    assert up[0][1] < 150 and down[0][1] > 250, f'방향을 안 가른다: up {up[0][1]} · down {down[0][1]}'
