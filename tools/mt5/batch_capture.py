"""대본 한 편 → 비트마다 차트 장면을 **골라서 찍는다** (next_step 45 ①).

scenes.py 는 '무엇을 보여 줄지' 와 '어느 구간인지' 를 고르는 데서 멈췄고, 열린 차트 하나(종목·주기 고정)만 봤다.
여기서는 그 뒤를 잇는다.

 1. 비트 → 찾을 움직임.  scenes.RULES 가 먼저. 낱말이 하나도 안 맞아 기본값(trend_burst)으로 떨어진 비트만
    **Jev 에게 뜻으로 묻는다** (confidence 0.7 미만이면 기본값 그대로). 뜻만 보고 가르는 자리라 맡긴다 —
    수를 견주는 자리는 안 맡긴다(D-4, constraint 67).
 2. 종목·주기도 고른다. 팀장 그림 14장은 BTCUSD M1 9 · BTCUSD M5 3 · US100 M1 4(겹침 있음) · 일봉 1 이었다
    (tools/jev/d2_labels.json). 후보마다 같은 움직임을 찾아 **점수가 가장 높은 곳**을 쓴다.
    점수는 전부 비율(낙폭/구간폭 등)이라 주기가 달라도 견줄 수 있다. 같으면 BTCUSD M1 (팀장이 가장 많이 쓴 것).
 3. 찍는다. 비트마다 **새 차트를 열어** 템플릿을 입히고, CMG_Shot 으로 그 시각에 옮기고 지표를 켠 뒤
    창을 PrintWindow 로 찍고, 차트를 닫는다 — 사람이 보던 차트는 안 건드린다.

    python tools/mt5/batch_capture.py <대본.docx|.txt> <출력폴더> [--dry] [--no-jev]
           [--cands BTCUSD:M1,BTCUSD:M5,US100.:M1] [--from 2026-09-01] [--to 2026-09-22]

  --dry     고르기만 하고 찍지 않는다 (MT5 창을 안 건드린다)
  출력      <폴더>/<비트>.png · 콘티.json · 콘티.md(비트마다 왜 이 장면인지)

trade_* 도구는 부르지 않는다. 읽기만 한다.
"""
import argparse
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'jev'))
import scenes as S  # noqa: E402
from mcp import MT5  # noqa: E402

STEP = {'M1': 60, 'M2': 120, 'M5': 300, 'M15': 900, 'M30': 1800, 'H1': 3600, 'H4': 14400, 'D1': 86400}
TEMPLATE = '기본값.tpl'            # 지표 없는 깨끗한 판 — 켤 지표는 CMG_Shot 이 붙인다
SCALE = 4                          # 봉 하나 16px → 1920 폭에 약 117봉 (탐색 창 110봉과 맞춘다)
JEV_GATE = 0.7
JEV_OVERRIDE = 0.8                 # 규칙이 고른 장면을 Jev 가 뒤집으려면 이만큼 확신해야 한다 (차10 은 규칙이 맞았다)
BOX_GATE = 0.6                     # '이 대목은 횡보장인가' 판정의 문 (둘 중 하나 고르기라 0.5 가 찍기다)
THEME_MIN = 8                      # 이평선이 대본에 이만큼 넘게 나오면 회차 주제 지표로 보고 모든 비트에 켠다
LONG_FROM = '2026-03-01'           # M15 이상은 여기서부터 봉을 받는다
PAGE_BARS = 110                    # 장면 구간 봉 수 (scenes.pick 의 page)
MIN_CHART_W = 1900                 # 16px/봉 × 110봉 + 가격축 ≈ 1900 — 이보다 좁으면 구간이 잘린다

# Jev 에게 보이는 선택지 설명. RULES 의 why 는 **차트 말**뿐이라 대본 문장과 잇지 못했다 —
# 차10 3-4("1단계 매수, 2단계 매도 후 다시 올라 3단계 매수") 에 톱니를 못 골랐다(0.46).
# 그래서 '대본이 이런 말을 할 때 → 차트는 이렇게' 로 쓴다.
JEV_DESC = {
    'ema200_adx_entry': '대본이 200EMA·ADX 로 방향을 정하고 첫 진입하는 법을 설명할 때 → 200EMA 위(아래)에서 ADX 가 25 를 넘는 자리',
    'ema20_switch': '대본이 첫 진입 뒤 20EMA 를 기준으로 반대 포지션으로 바꾸는 법을 설명할 때 → 20EMA 를 반대로 깨는 자리',
    'zigzag3': '대본이 매수·매도를 번갈아 넣는 단계(1단계 매수 → 2단계 매도 → 3단계 매수…)를 말할 때 → 올랐다 내렸다 다시 오르는 톱니',
    'high_then_drop': '대본이 매수했는데 가격이 밀려 손실이 난 상황을 말할 때 → 고점 뒤로 하락이 이어지는 구간',
    'support_break': '대본이 지지선이 깨지는 상황을 말할 때 → 지지선을 뚫고 내려가는 움직임',
    'chop_box': '대본이 방향 없이 오르내리기만 하는 장, 박스권, 횡보를 말할 때 → 좁은 박스 안의 등락',
    'session_burst': '대본이 장 시작·개장 시간·변동성이 커지는 시간대를 말할 때 → 조용하다가 크게 흔들리기 시작하는 구간',
    'whipsaw': '대본이 방향을 맞히려다 양쪽으로 손실을 보는 상황을 말할 때 → 위아래로 크게 쓸리는 구간',
    'ma_support_bounce': '대본이 상승 추세 중 가격이 이평선(예: 20일선)까지 내려왔다가 지지받고 다시 오르는 것을 말할 때 → 이평선에 닿고 반등',
    'ma_resist_drop': '대본이 하락 추세 중 반등이 이평선에 막혀 다시 내리는 것을 말할 때 → 이평선 저항 뒤 재하락',
    'ma_flat_box': '대본이 이평선이 평평하게 눕고 가격이 그 위아래를 오가는 횡보·휩소를 말할 때 → 누운 이평선 주변 등락',
    'ma_break_down': '대본이 가격이 이평선 아래로 내려가 매도 우위·하락 추세가 되는 것을 말할 때 → 이평선 하향 이탈 뒤 하락',
    'ma_break_up': '대본이 가격이 이평선 위로 올라서 매수 우위·상승 추세가 되는 것을 말할 때 → 이평선 상향 돌파 뒤 상승',
}


# ─── 1. 비트 → 움직임 ──────────────────────────────────────────────────

def ask_jev(beat, rules, allow_none=True, gate=None):
    """규칙이 못 잡은 비트를 Jev 에게 뜻으로 묻는다 → (규칙 dict | 'none' | None, confidence).

    allow_none=False 는 **이미 성격이 정해진 자리**에 쓴다(예: 대본이 횡보장이라고 말한 비트).
    선택지를 줄이면서 '해당 없음' 을 남겨 두면 그쪽으로 도망간다 — 09-28 4-4: 전체 선택지에선 whipsaw 0.70 인데
    박스 셋으로 줄이니 '해당 없음' 0.31 이었다.
    """
    try:
        import jev
    except Exception:
        return None, 0.0
    opts = {r['name']: JEV_DESC.get(r['name'], r['why']) for r in rules}
    if allow_none:
        opts['none'] = '대본이 특정 움직임을 말하지 않는다(질문·원칙·숫자 설명 등) → 한 방향으로 뻗는 추세면 충분하다'
    try:
        ans = jev.ask({'대본 대목': beat['text'][:500]},
                      {'q': jev.choice('이 대목을 말할 때 화면의 차트는 어떤 움직임을 보여 줘야 하는가', opts)})
        got, conf = jev.pick(ans, 'q')
    except Exception as e:                          # 값·망 문제로 막혀도 촬영은 계속한다
        print(f'   (Jev 실패: {e})')
        return None, 0.0
    if got == 'none':
        return 'none', conf
    if conf < (JEV_GATE if gate is None else gate):      # 문은 부르는 쪽이 정한다 (자리마다 다르다)
        return None, conf
    return next(r for r in rules if r['name'] == got), conf


DIRECTED = ('trend_burst', 'ema200_adx_entry')     # 방향이 그림을 바꾸는 장면만

# 요청한 지표 종류 → MT5 list_open_charts 가 돌려주는 이름에 든 글자 (찍기 전 대조용)
KIND = {'ma': 'Moving Average', 'bb': 'Bollinger', 'adx': 'Average Directional',
        'rsi': 'Relative Strength', 'stoch': 'Stochastic', 'macd': 'MACD'}


def kind_of(x):
    if x.startswith(('EMA', 'MA')) and not x.startswith('MACD'):
        return 'ma'
    return {'BB': 'bb', 'ADX': 'adx', 'RSI': 'rsi', 'STOCH': 'stoch', 'MACD': 'macd'}.get(x)


def direction_of(beat):
    """대본 대목이 말하는 가격 방향 → ('up'|'down'|None, 메모). Jev 에게 뜻으로 묻는다.

    낱말로 가르지 않는다 — '매수·매도' 는 방향이 아니라 행동이고, '하락을 예상했지만 상승' 처럼 뒤집힌다.
    """
    try:
        import jev
        ans = jev.ask({'대본 대목': beat['text'][:500]}, {'q': jev.choice(
            '이 대목을 말할 때 화면의 가격은 어느 쪽으로 움직여야 하는가',
            {'up': '가격이 오른다 (상승 추세·급등·상승 전환 뒤 이어짐)',
             'down': '가격이 내린다 (하락 추세·급락·하락이 이어짐)',
             'none': '대본이 방향을 말하지 않는다 (원칙·숫자·질문 등)'})})
        got, conf = jev.pick(ans, 'q')
    except Exception as e:
        return None, f'방향 못 물음({e})'
    if got in ('up', 'down') and conf >= JEV_GATE:
        return got, f'방향 {"상승" if got == "up" else "하락"} (Jev {conf:.2f})'
    return None, f'방향 없음 (Jev {got} {conf:.2f})'


# 대본이 횡보장을 말하는데 추세·돌파 장면을 고르면 화면과 말이 정반대가 된다
# (09-28 검수: 4-4 "횡보장에서 돌파에 속아 손절" 에 깨끗한 돌파, 5-9 "채널 하단 복귀 매수" 에 추세)
BOX_WORDS = ('횡보', '박스권', '박스 권', '채널', '눕')
BOXY = ('chop_box', 'ma_flat_box', 'whipsaw')
TRENDY = ('trend_burst', 'ma_break_up', 'ma_break_down', 'ema200_adx_entry', 'ema20_switch',
          'ma_support_bounce', 'ma_resist_drop')


def is_sideways(beat):
    """이 대목의 화면은 추세장인가 횡보장인가 — 둘 중 하나로 묻는다 → (횡보인가, confidence).

    '횡보·박스권' 낱말만으로는 못 가른다. "박스권이 아니라 추세장이면…" 같은 문장이 있기 때문이다.
    """
    try:
        import jev
        ans = jev.ask({'대본 대목': beat['text'][:500]}, {'q': jev.choice(
            '이 대목을 말할 때 화면에 보여야 하는 장은 어느 쪽인가',
            {'sideways': '옆으로 오가는 장 — 횡보·박스권·채널 안 등락, 방향이 없어 속임수 신호가 잦다',
             'trend': '한 방향으로 가는 장 — 추세·돌파·눌림 뒤 이어짐'})})
        got, conf = jev.pick(ans, 'q')
        return got == 'sideways', conf
    except Exception:
        return False, 0.0


def box_override(beat, sp, use_jev):
    """횡보 대목에 추세 장면이 걸렸으면 박스 계열로 바꾼다.

    두 걸음이다 — ① 횡보장인가(둘 중 하나) ② 박스 셋 중 어느 것인가.
    ②는 문을 두지 않는다. 셋 다 옆으로 가는 그림이라 어느 것이든 추세·돌파 그림보다 낫고,
    Jev 는 셋 사이에서 잘 못 가른다(09-28 4-4: 1등이 0.26). 고른 값과 확신은 by 에 남긴다.
    """
    if not use_jev or sp['name'] not in TRENDY or not any(w in beat['text'] for w in BOX_WORDS):
        return sp
    # '채널·박스권·횡보장' 처럼 분명히 이름을 부르면 문을 낮춘다 (09-28 3차: 5-9 가 0.62 로 아깝게 걸렸다)
    gate = 0.5 if any(w in beat['text'] for w in ('박스권', '채널', '횡보장')) else BOX_GATE
    side, sconf = is_sideways(beat)
    if not side or sconf < gate:
        return sp
    r, conf = ask_jev(beat, [x for x in S.RULES if x['name'] in BOXY], allow_none=False, gate=0.0)
    if r in (None, 'none'):
        return sp
    return dict(r, id=beat['id'], by=f"Jev 횡보 {sconf:.2f}/{r['name']} {conf:.2f} ({sp['name']} 대신)")


def spec_of(beat, use_jev, episode_ma=None, always_on=None):
    sp = S.spec_for(beat)
    sp['by'] = '규칙'
    if sp['name'] != S.FALLBACK['name'] and use_jev:
        # 낱말 규칙은 뜻을 거꾸로 읽는다 — 차11 3-4 "20일선이 지지선 역할(지지 성공)" 에 '지지선' 이 걸려 지지선 **붕괴**,
        # 4-4 "돌파했으니 매도(횡보장 속임수)" 에 '돌파' 가 걸려 깨끗한 돌파가 뽑혔다(09-22 검수). Jev 가 다르게 보면 따른다.
        r, conf = ask_jev(beat, S.RULES)
        if r not in (None, 'none') and r['name'] != sp['name'] and conf >= JEV_OVERRIDE:
            sp = dict(r, id=beat['id'], by=f"Jev {conf:.2f} (규칙 {sp['name']} 을 뒤집음)")
    if sp['name'] == S.FALLBACK['name'] and use_jev:
        r, conf = ask_jev(beat, S.RULES)
        if r == 'none':
            sp['by'] = f'기본값 (Jev: 특정 움직임 없음 {conf:.2f})'
        elif r:
            sp = dict(r, id=beat['id'], by=f'Jev {conf:.2f}')
        else:
            sp['by'] = f'기본값 (Jev {conf:.2f} — 문 {JEV_GATE} 아래)'
    sp = box_override(beat, sp, use_jev)
    # 지표는 **장면을 다 정한 뒤에** 붙인다. 먼저 붙이면 장면을 바꾸는 순간 같이 날아간다 —
    # 09-28 검수: 4-4 가 whipsaw 로 바뀌며 MA20 이 사라졌는데 대본은 "20일선에 닿았으니 매수" 였다.
    read = S.indicators_of(beat['text'], episode_ma)
    # 회차 주제 지표는 늘 켠다 — 차11 팀장 그림 42장 중 35장에 20이평 (09-22 판독)
    base = [always_on] if always_on and not any(kind_of(x) == 'ma' for x in read + list(sp.get('indicators') or [])) else []
    sp['indicators'] = list(dict.fromkeys(base + list(sp.get('indicators') or []) + read))[:S.MAX_INDS]
    # 이평선 기준 장면은 그 이평선이 화면에 있어야 이야기가 된다
    mas = [int(x[2:]) for x in sp['indicators'] if x.startswith('MA') and not x.startswith('MACD')]
    sp['ma'] = mas[0] if mas else (episode_ma or 20)
    if sp['name'].startswith('ma_') and not mas:
        sp['indicators'] = ([f"MA{sp['ma']}"] + sp['indicators'])[:S.MAX_INDS]
    if use_jev and sp['name'] in DIRECTED:
        sp['direction'], memo = direction_of(beat)
        sp['by'] += ' · ' + memo
    return sp


# ─── 2. 종목·주기·구간 ────────────────────────────────────────────────

NEAR_TIE = 0.9    # 1등 점수의 이만큼 안이면 사실상 동점 — 그때는 회차에 맞는 주기를 먼저 쓴다

# 동점일 때 먼저 볼 순서. 팀장 실측(09-22 판독):
#   주제 지표가 없는 회차(차10)  BTCUSD M1 9/14 — 24시간 거래라 빈 구멍이 없다
#   'N일선' 이 주제인 회차(차11)  US100 M15·H1·D1 이 대부분, M1 은 0장 — 일 단위 이평선 이야기라 긴 주기
ORDER_PLAIN = ['BTCUSD:M1', 'BTCUSD:M5', 'US100.:M1', 'US100.:M15', 'US100.:H1']
ORDER_DAILY_MA = ['US100.:H1', 'US100.:M15', 'US100.:M1', 'BTCUSD:M5', 'BTCUSD:M1']

# 대본이 종목을 말하면 그 종목을 먼저 본다 (09-28 검수: 2-3 은 암호화폐 대목인데 US100 이 뽑혔다)
SYMBOL_WORDS = {'BTCUSD': ('비트코인', '암호화폐', '코인', 'BTC'), 'US100.': ('나스닥', 'US100', '지수')}


def order_for(beat, order):
    """대본이 부른 종목을 순서 앞으로 당긴다. 없으면 회차 순서 그대로."""
    for sym, words in SYMBOL_WORDS.items():
        if any(w in beat['text'] for w in words):
            mine = [k for k in order if k.startswith(sym)]
            return mine + [k for k in order if k not in mine]
    return order


def choose(sp, pools, order=ORDER_PLAIN):
    """후보 (종목, 주기) 마다 pick 을 해 보고 하나를 고른다.

    점수 1등만 쓰면 **봉이 많은 주기(M1)가 늘 이긴다** — 후보 구간이 많을수록 최고 점수가 우연히 높아진다.
    09-22 차11: 35비트 중 34비트가 M1·M5, 팀장은 M1 을 한 장도 안 썼다. 그래서 1등의 NEAR_TIE 안은 동점으로 보고
    회차 성격에 맞는 주기(order)를 먼저 쓴다. 점수가 몰린 후보(가르지 못함)는 늘 뒤로.
    """
    tried = []
    for key, pool in pools.items():
        trial = list(pool['used'])
        got = S.pick(sp, pool['bars'], used=trial, step_sec=STEP.get(key[1], 60), cache=pool.setdefault('cache', {}))
        if got:
            tried.append((key, got, trial))
    if not tried:
        return None
    ok = [t for t in tried if t[1]['ties'] < S.SATURATED] or tried
    top = max(t[1]['score'] for t in ok)
    near = [t for t in ok if t[1]['score'] >= NEAR_TIE * top]
    rank = {k: i for i, k in enumerate(order)}
    key, got, trial = min(near, key=lambda t: (rank.get(f'{t[0][0]}:{t[0][1]}', 99), -t[1]['score']))
    # 구간 마지막 봉의 **다음 봉 시각** — 찍은 자리 확인에 쓴다(주말·휴장 구멍이 있어 시계로 못 센다)
    bars = pools[key]['bars']
    times = pools[key].setdefault('times', [b['time'] for b in bars])
    j = times.index(got['to'])
    got['to_next'] = times[j + 1] if j + 1 < len(times) else None
    pools[key]['used'] = trial                      # 고른 후보에만 '쓴 구간' 을 남긴다
    got.update(symbol=key[0], period=key[1])
    return got


# ─── 3. 찍기 ──────────────────────────────────────────────────────────

def near_enough(seen, want, want_next=None):
    """화면 오른쪽 끝 봉이 목표와 같은가. 목표 봉이나 **바로 다음 봉**이면 맞다.

    ChartNavigate 가 목표를 오른쪽에서 두 번째에 놓아 늘 한 봉이 더 보인다(09-28: 35장 전부 +1봉).
    다음 봉의 시각은 **데이터에서 가져온다** — 시계로 재면 주말·휴장 구멍에서 오탐이 난다
    (금 23:00 다음 봉이 월 01:00 이라 사흘 차이로 보였다). 그보다 벌어지면 다른 구간이다(09-22: 하루 뒤를 찍었다)."""
    if not seen:
        return False
    return seen == want or (want_next is not None and seen == want_next[:16])


def _warn(got, msg):
    got['warn'] = (got['warn'] + ' / ' + msg) if got.get('warn') else msg
    print(f'   경고 — {msg}')


def capture(m, got, out, tries=2):
    """한 장을 찍는다. **자리와 지표를 확인하고**, 어긋나면 차트를 닫고 처음부터 다시 한다.

    고쳐 가며 붙인 '한 번 더 시키기' 들이 서로 엉켰다 — 다시 붙인 지표는 스스로 빠지며 제가 그린 선도
    같이 가져갔고(09-28 5-6), 두 번째 CMG_Shot 이 같은 상태 파일에 겹쳐 썼다. 통째로 다시 하는 쪽이 단순하다.
    """
    import capture as CAP
    from capture_scene import IND, MQL5
    global MQL5_FILES
    MQL5_FILES = os.path.join(MQL5, 'Files')
    want, nxt = got['to'][:16], got.get('to_next')
    inds = '+'.join(got['indicators'])          # 쉼표는 MCP 가 인자 구분자로 먹는다 — '+' 로 잇는다
    last = None

    for k in range(tries):
        cid = str(m.call('chart_open', {'symbol': got['symbol'], 'period': got['period']})['chart_id'])
        nav = os.path.join(MQL5_FILES, f'cmg_nav_{cid}.txt')
        try:
            m.call('chart_apply_template', {'chart_id': cid, 'template_filename': TEMPLATE})
            time.sleep(3.0)                     # 템플릿이 지표를 갈아 끼우는 중에 붙이면 같이 지워진다
            m.call('chart_add_indicator', {
                'chart_id': cid, 'indicator_name': 'CMG_Shot', 'custom_indicator_path': IND,
                'indicator_parameters': f"ShotFile=,ShotEndTime={want},ShotScale={SCALE},"
                                        f"ShotInds={inds},SelfRemove=true,KeepInds=true,Hold=true"})

            def status():
                """(화면 오른쪽 끝 시각, 그린 이평선) — CMG_Shot(Hold) 이 적어 둔다."""
                try:
                    lines = io.open(nav, encoding='ascii', errors='ignore').read().split('\n')
                except OSError:
                    return None, []
                edge = lines[0].strip() if lines else None
                mas = []
                for ln in lines[1:]:
                    if ln.startswith('MA:'):
                        mas = [x for x in ln[3:].split('|')[0].split(',') if x]
                return edge, mas

            t0 = time.time()
            while time.time() - t0 < 25:        # 옮겼다고 믿지 않는다 — 자리가 맞을 때까지 기다린다
                time.sleep(1.0)
                if near_enough(status()[0], want, nxt):
                    time.sleep(1.5)             # 지표·축이 다 그려지게
                    break

            ch = next((c for c in m.open_charts() if str(c['chart_id']) == cid), None)
            on = [i.get('name', '') for i in (ch or {}).get('indicators', [])]
            edge, mas = status()
            # 이평선은 CMG_Shot 이 제 버퍼로 그린다(색을 달리하려고) — 차트 지표 목록에 안 나오니 상태 파일로 센다
            short = [kind for kind, pat in KIND.items()
                     if sum(1 for x in got['indicators'] if kind_of(x) == kind)
                     > (len(mas) if kind == 'ma' else sum(1 for n in on if pat in n))]

            full = CAP.shoot(CAP.find_window())
            top = CAP.chart_top(full)
            w = ch['rect_right'] if ch else full.size[0]
            h = ch['rect_bottom'] if ch else full.size[1] - top
            after = status()[0]                 # 찍는 사이 되돌아갔을 수 있다
            ok = near_enough(after, want, nxt) and not short and w >= MIN_CHART_W
            last = {'ch': ch, 'on': on, 'mas': mas, 'short': short, 'after': after, 'w': w}
            if ok or k == tries - 1:
                full.crop((0, top, w, top + h)).save(out)
                break
            print(f'   다시 찍는다 ({k + 2}번째) — 자리 {after} · 모자란 지표 {short}')
        finally:
            m.call('chart_close', {'chart_id': cid})
            try:
                os.remove(nav)
            except OSError:
                pass

    got['indicators_on'] = last['on']
    got['ma_drawn'] = last['mas']
    got['right_edge'] = last['after']
    if last['short']:
        _warn(got, f"지표가 덜 붙었다: 요청 {got['indicators']} · 그린 이평 {last['mas']} · 차트 {last['on']}")
    if not near_enough(last['after'], want, nxt):
        got['bad_capture'] = True               # 콘티에서 **못 쓰는 장**으로 표시된다
        _warn(got, f"엉뚱한 구간을 찍었다 — 화면 오른쪽 끝 {last['after']} (목표 {want})")
    if last['w'] < MIN_CHART_W:
        _warn(got, f"그림 폭 {last['w']}px — 구간이 잘렸다 ({last['w'] // 16}/{PAGE_BARS}봉만 보인다)")
    return last['ch']


# ─── 실행 ─────────────────────────────────────────────────────────────

def read_script(path):
    if path.lower().endswith('.docx'):
        return S.read_docx(path)
    return io.open(path, encoding='utf-8').read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('script')
    ap.add_argument('out')
    # 차10 팀장은 BTCUSD M1·M5, 차11 팀장은 US100 M15·H1·D1 이 많았다(09-22 판독) — 회차마다 달라 넓게 둔다
    ap.add_argument('--cands', default='BTCUSD:M1,BTCUSD:M5,US100.:M1,US100.:M15,US100.:H1')
    ap.add_argument('--from', dest='dt_from', default='2026-09-01')
    ap.add_argument('--to', dest='dt_to', default=time.strftime('%Y-%m-%d'))
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--no-jev', action='store_true')
    ap.add_argument('--resume', action='store_true', help='이미 찍은 비트는 건너뛴다 (콘티.json + 그림이 있는 것)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    text = read_script(a.script)
    beats = S.split_beats(text)
    if not a.dry:
        # MT5 창이 줄어 있으면 화면에 구간의 절반만 담긴다 — 09-22 차11 을 958px 로 35장 찍었다(이탈 순간이 화면 밖).
        # 조용히 반쪽을 찍지 않고 여기서 멈춘다.
        w = max((c.get('rect_right', 0) for c in MT5().open_charts()), default=0)
        if w < MIN_CHART_W:
            raise SystemExit(f'MT5 차트 폭이 {w}px 다(필요 {MIN_CHART_W}px 이상). MT5 창을 최대화하고 다시 부르라 — '
                             f'구간 {PAGE_BARS}봉 중 {w // 16}봉만 화면에 들어간다.')
    ep_ma = S.main_ma(text)
    # 회차 주제 지표: 그 이평선이 대본에 THEME_MIN 번 넘게 나오면 모든 비트에 켠다 (차10 은 0번이라 민차트 그대로)
    n_ma = sum(1 for m in S.MA_RE.finditer(text) if ep_ma and int(m.group(1)) == ep_ma)
    always_on = f'MA{ep_ma}' if ep_ma and n_ma >= THEME_MIN else None
    print(f'비트 {len(beats)}개 · 회차 주 이평선 {ep_ma or "없음"}({n_ma}번) · 늘 켜기 {always_on or "없음"}')
    m = MT5()
    pools = {}
    for c in a.cands.split(','):
        sym, per = c.split(':')
        # 긴 주기는 같은 날짜 범위면 봉이 모자란다 — 약 반년 전부터 받는다
        start = a.dt_from if STEP.get(per, 60) < 900 else LONG_FROM
        bars = m.history(sym, per, start + 'T00:00:00', a.dt_to + 'T00:00:00')
        pools[(sym, per)] = {'bars': bars, 'used': []}
        print(f'  {sym} {per}: 봉 {len(bars)}')

    # 이어 찍기 — 이미 찍은 비트는 그대로 쓰고, 그 구간은 '쓴 구간' 으로 되살린다(겹치지 않게)
    done = {}
    jpath = os.path.join(a.out, '콘티.json')
    if a.resume and os.path.exists(jpath):
        for c in json.load(io.open(jpath, encoding='utf-8')):
            if c.get('png') and not c.get('bad_capture') and os.path.exists(os.path.join(a.out, c['png'])):
                done[c['id']] = c
                pool = pools.get((c.get('symbol'), c.get('period')))
                if pool:
                    times = [b['time'] for b in pool['bars']]
                    if c['from'] in times and c['to'] in times:
                        pool['used'].append((times.index(c['from']), times.index(c['to']) + 1))
        print(f'  이어 찍기: {len(done)}장은 그대로 쓴다')

    conti = []
    for be in beats:
        if be['id'] in done:
            conti.append(done[be['id']])
            continue
        sp = spec_of(be, not a.no_jev, ep_ma, always_on)
        got = choose(sp, pools, order_for(be, ORDER_DAILY_MA if always_on else ORDER_PLAIN))
        line = f"({be['id']}) {sp['name']:<17} [{sp['by']}]"
        if not got:
            print(line + '  못 찾음')
            conti.append({'id': be['id'], 'pattern': sp['name'], 'by': sp['by'], 'text': be['text'][:200], 'png': None})
            continue
        got.update(by=sp['by'], text=be['text'][:200])
        png = os.path.join(a.out, f"{be['id']}.png")
        if not a.dry:
            capture(m, got, png)
            got['png'] = os.path.basename(png)
        conti.append(got)
        print(f"{line}  {got['symbol']} {got['period']} {got['from'][5:16]}~{got['to'][5:16]}  {got['note']}")
        if got.get('warn'):
            print(f"   경고 — {got['warn']}")
        with io.open(jpath, 'w', encoding='utf-8') as f:   # 한 장마다 저장 — 끊겨도 --resume 으로 잇는다
            json.dump(conti, f, ensure_ascii=False, indent=1)

    with io.open(os.path.join(a.out, '콘티.json'), 'w', encoding='utf-8') as f:
        json.dump(conti, f, ensure_ascii=False, indent=1)
    md = ['# 차트 장면 콘티', '', '| 비트 | 장면 | 누가 골랐나 | 종목·주기 | 구간 | 지표 | 왜 | 대본 |', '|---|---|---|---|---|---|---|---|']
    for c in conti:
        if not c.get('symbol'):
            md.append(f"| {c['id']} | 못 찾음 | {c['by']} | | | | | {c['text'][:40]} |")
            continue
        img = f"![]({c['png']})" if c.get('png') else c['pattern']
        md.append(f"| {c['id']} | {img} | {c['by']} | {c['symbol']} {c['period']} | {c['from'][5:16]} ~ {c['to'][5:16]} "
                  f"| {','.join(c['indicators']) or '없음'}{' ⚠ ' + c['warn'] if c.get('warn') else ''} "
                  f"| {c['why']} · {c['note']} | {c['text'][:40]}… |")
    with io.open(os.path.join(a.out, '콘티.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(md) + '\n')
    print(f"\n콘티 {sum(1 for c in conti if c.get('symbol'))}/{len(conti)}장 → {a.out}")


if __name__ == '__main__':
    main()
