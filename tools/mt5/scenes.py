"""대본을 읽고, 각 비트에 맞는 **실제 차트 장면**을 골라 준다.

팀장이 차10(양방향 매매법)에서 실제로 고른 것을 뜯어 보고 뽑은 규칙이다.

 1. 비트 번호 `(4-1)` 는 그림 이름 `차10_4-1.png` 와 1:1 이다.
 2. **원리를 말하는 비트는 지표를 끈 깨끗한 차트**를 쓴다 (2-2 는 BTCUSD M5 민차트).
    가격 움직임만으로 이야기가 보여야 하기 때문이다.
 3. **본론에서 지표를 설명하는 비트는 대본이 말한 그 지표만** 켠다 (4-1·4-2 = 20/200 EMA + ADX).
 4. 고르는 자리는 대본 문장이 말하는 **사건이 실제로 일어난 구간**이다.
    "매수했는데 하락" 이면 진짜 고점 뒤 하락 구간을, "ADX 25 상향 돌파" 면 진짜 그 봉을 찾는다.

그래서 이 파일이 하는 일은 셋이다 — 대본을 비트로 쪼개고, 비트 문장에서 **찾을 사건**을 읽어 내고,
MT5 에서 받은 실제 봉에서 그 사건이 가장 뚜렷한 구간을 점수로 골라낸다.
"""
import io
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import MT5  # noqa: E402

# ─── 대본 ───────────────────────────────────────────────────────────────

BEAT_RE = re.compile(r'\((\d+-\d+)\)')


def read_docx(path):
    z = zipfile.ZipFile(path)
    x = z.read('word/document.xml').decode('utf-8')
    paras = re.findall(r'<w:p[ >].*?</w:p>', x, re.S)
    out = []
    for p in paras:
        t = ''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.S))
        out.append(re.sub(r'<[^>]+>', '', t).strip())
    return '\n'.join(out)


SECTION_RE = re.compile(r'^\s*\[(?:수정된\s*)?(\d+)(?:[+.]\d+)?\.?\s*[^\]]*\]\s*(.*)$')


def split_sections(text, min_chars=60):
    """비트 번호가 없는 대본 — '[2. 소개 (Intro) : …]' 절 제목 + 문단. 문단 하나 = 비트 하나, 번호는 '절-순번'.

    차10 만 '(1-3)' 번호를 달았다. 나머지 15편(차11 등)은 이 양식이다(09-22 확인). 짧은 문단은 다음 문단에 붙인다.
    """
    beats, sec, k, carry = [], None, 0, ''
    for raw in text.split('\n'):
        m = SECTION_RE.match(raw)
        if m:
            sec, k, carry = m.group(1), 0, ''
            raw = m.group(2)                            # 제목 줄 뒤에 본문이 붙어 오는 경우가 있다
        if sec is None:
            continue
        body = (carry + ' ' + raw).strip() if carry else raw.strip()
        if not body:
            continue
        if len(body) < min_chars:
            carry = body
            continue
        carry = ''
        k += 1
        beats.append({'id': f'{sec}-{k}', 'text': re.sub(r'\s+', ' ', body)[:600]})
    return beats


def split_beats(text):
    """'(1-3)본문…' 을 [(번호, 본문)] 로. 목차 뒤쪽만 본다. 번호가 없으면 절·문단으로 나눈다."""
    if '[목차]' in text:
        text = text[text.index('[목차]'):]
    if not BEAT_RE.search(text):
        return split_sections(text)
    hits = list(BEAT_RE.finditer(text))
    beats = []
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        body = text[m.end():end]
        # 다음 절 제목("4+5. 본론#2" 같은 줄)까지 먹으면 엉뚱한 지표 규칙에 걸린다
        cut = re.search(r'\n\s*\d+([+.]\d+)?[.)]\s*\S', body)
        if cut:
            body = body[:cut.start()]
        beats.append({'id': m.group(1), 'text': re.sub(r'\s+', ' ', body).strip()[:600]})
    return beats


# ─── 비트 문장 → 찾을 사건 ─────────────────────────────────────────────
#
# 낱말이 아니라 '무엇을 보여 줘야 하는가' 로 가른다. 위에서부터 먼저 맞는 것을 쓴다.

RULES = [
    # 본론: 대본이 지표를 직접 설명하는 자리 — 그 지표를 켠다
    dict(name='ema200_adx_entry', need=['200', 'ADX'],
         indicators=['EMA200', 'EMA20', 'ADX'],
         why='200EMA 로 방향을 정하고 ADX 25 상향 돌파로 첫 진입하는 자리'),
    dict(name='ema20_switch', need=['20', '스위칭'],
         indicators=['EMA200', 'EMA20', 'ADX'],
         why='첫 진입 뒤 20EMA 를 깨고 반대로 스위칭하는 자리'),
    # 원리 설명: 지표 없이 움직임만
    dict(name='zigzag3', need=['매도로 1계약', '상승 전환'], any_need=['또 다른 예시', '3계약'],
         indicators=[], why='하락→상승전환→다시 하락, 세 번 꺾이는 톱니'),
    dict(name='high_then_drop', need=['매수로 1계약'], any_need=['하락하였습니다', '매도로 2계약'],
         indicators=[], why='고점에서 매수했다가 밀리고, 그 뒤 하락이 이어지는 구간'),
    # 이평선 기준 (차11) — 지지선·박스권 규칙보다 먼저 본다. 이평선 말이 함께 있어야 한다
    dict(name='ma_support_bounce', need=['상승 추세'], any_need=['20일선에 닿', '이평선에 닿', '부근까지 내려', '눌림'],
         indicators=[], why='상승 추세 중 되돌림이 이평선에 닿고 다시 오르는 자리'),
    dict(name='ma_resist_drop', need=['하락 추세'], any_need=['20일선에 도달', '이평선 부근까지 올라', '저항으로 작용', '재차 하락'],
         indicators=[], why='하락 추세 중 반등이 이평선에 막혀 다시 내리는 자리'),
    dict(name='ma_flat_box', need=['눕'], any_need=['이평선', '이동평균선', '20일선'],
         indicators=[], why='이평선이 옆으로 눕고 가격이 그 위아래를 오가는 횡보'),
    dict(name='ma_break_down', need=['이탈'], any_need=['이평선', '20일선', '이동평균선'],
         indicators=[], why='이평선을 아래로 뚫고 하락 추세가 이어지는 자리'),
    dict(name='ma_break_up', need=['돌파'], any_need=['이평선', '20일선', '이동평균선'],
         indicators=[], why='이평선을 위로 뚫고 상승이 이어지는 자리'),
    # 후킹·원칙
    dict(name='support_break', need=['지지선'], indicators=[],
         why='지지선을 깨고 내려가는 움직임'),
    dict(name='chop_box', need=['박스권'], indicators=[],
         why='추세 없이 위아래로만 흔드는 좁은 박스권'),
    dict(name='session_burst', need=['개장'], any_need=['10시 30분', '변동성'],
         indicators=[], why='미국 본장 개장 뒤 변동성이 터지는 시간대'),
    dict(name='whipsaw', need=['계좌를 갉아'], indicators=[],
         why='방향을 맞추려다 양쪽으로 쓸리는 구간'),
]

FALLBACK = dict(name='trend_burst', indicators=[], why='한 방향으로 시원하게 터진 추세')


# ─── 대본이 말한 지표 → 켤 지표 ────────────────────────────────────────
#
# 차10 에서 확실했던 단 하나의 규칙: **대본이 지표를 설명하는 비트는 그 지표를 켠다** (4-x 가 20/200 EMA + ADX).
# 차10 은 RULES 에 지표를 박아 뒀지만, 다른 회차는 대본에서 읽어야 한다 (09-22 차11 검증에서 드러남).
# 이름은 CMG_Shot 이 알아듣는 것: MA<n>(단순) · EMA<n> · BB · RSI · STOCH · MACD · ADX

MA_RE = re.compile(r'(\d{1,3})\s*(?:일\s*)?(?:이동\s*평균선?|이평선?|일선)')
EMA_RE = re.compile(r'(\d{1,3})\s*EMA|EMA\s*(\d{1,3})', re.I)
NAMED = [('BB', r'볼린저'), ('RSI', r'RSI'), ('STOCH', r'스토캐스틱'), ('MACD', r'MACD'), ('ADX', r'ADX')]
MAX_INDS = 4


def main_ma(text):
    """회차 전체에서 가장 많이 나온 이평선 기간 — 숫자 없이 '이평선' 이라고만 할 때 쓴다."""
    from collections import Counter
    c = Counter(int(m.group(1)) for m in MA_RE.finditer(text) if 2 <= int(m.group(1)) <= 400)
    return c.most_common(1)[0][0] if c else None


def indicators_of(text, episode_ma=None):
    out = []
    for m in EMA_RE.finditer(text):
        out.append(f'EMA{m.group(1) or m.group(2)}')
    for m in MA_RE.finditer(text):
        n = int(m.group(1))
        if 2 <= n <= 400 and f'EMA{n}' not in out:
            out.append(f'MA{n}')
    if not any(x.startswith(('MA', 'EMA')) for x in out) and episode_ma and re.search(r'이평선|이동\s*평균', text):
        out.append(f'MA{episode_ma}')
    for name, pat in NAMED:
        if re.search(pat, text):
            out.append(name)
    seen = []
    for x in out:
        if x not in seen:
            seen.append(x)
    return seen[:MAX_INDS]


def spec_for(beat):
    t = beat['text']
    for r in RULES:
        if all(k in t for k in r.get('need', [])):
            anyk = r.get('any_need')
            if anyk and not any(k in t for k in anyk):
                continue
            return dict(r, id=beat['id'])
    return dict(FALLBACK, id=beat['id'])


# ─── 지표 (봉 데이터에서 직접 계산한다) ────────────────────────────────

def ema(vals, n):
    k = 2 / (n + 1)
    out, cur = [], None
    for v in vals:
        cur = v if cur is None else v * k + cur * (1 - k)
        out.append(cur)
    return out


def adx(bars, n=14):
    """Wilder ADX. 값이 없는 앞쪽은 None."""
    tr, pdm, ndm = [], [], []
    for i in range(1, len(bars)):
        h, l_, pc = bars[i]['high'], bars[i]['low'], bars[i - 1]['close']
        ph, pl = bars[i - 1]['high'], bars[i - 1]['low']
        tr.append(max(h - l_, abs(h - pc), abs(l_ - pc)))
        up, dn = h - ph, pl - l_
        pdm.append(up if (up > dn and up > 0) else 0.0)
        ndm.append(dn if (dn > up and dn > 0) else 0.0)

    def wilder(x):
        out, s = [], None
        for i, v in enumerate(x):
            s = sum(x[:n]) if i == n - 1 else (None if i < n - 1 else s - s / n + v)
            out.append(s)
        return out

    atr, pd_, nd_ = wilder(tr), wilder(pdm), wilder(ndm)
    dx = []
    for i in range(len(tr)):
        if not atr[i]:
            dx.append(None)
            continue
        p = 100 * pd_[i] / atr[i]
        m = 100 * nd_[i] / atr[i]
        dx.append(100 * abs(p - m) / (p + m) if (p + m) else 0.0)
    out = [None]
    run = None
    for i, v in enumerate(dx):
        if v is None:
            out.append(None)
            continue
        vals = [d for d in dx[:i + 1] if d is not None]
        if run is None and len(vals) >= n:
            run = sum(vals[:n]) / n
        elif run is not None:
            run = (run * (n - 1) + v) / n
        out.append(run)
    return out


# ─── 장면 찾기 ─────────────────────────────────────────────────────────

def _win(bars, i, back, fwd):
    a, b = max(0, i - back), min(len(bars), i + fwd)
    return a, b


def _tsec(t):
    """'2026.09.11 23:45:00' → 초."""
    import datetime
    return datetime.datetime.strptime(t, '%Y.%m.%d %H:%M:%S').timestamp()


def has_gap(bars, a, b, step_sec):
    """주말·장 마감 구멍이 든 구간은 차트가 뚝 끊겨 보인다 — 버린다."""
    for i in range(a + 1, b):
        if _tsec(bars[i]['time']) - _tsec(bars[i - 1]['time']) > step_sec * 3:
            return True
    return False


# ── 장면마다 전용 탐색 하나 (FINDERS) ─────────────────────────────────
#
# 규칙: **장면 하나 = 전용 함수 하나.** 남의 계산을 빌려 쓰지 않는다.
#   09-22 차10 1-2: 지지선 이탈·쓸림이 '고점 뒤 하락' 계산을 빌려 써서 점수가 100% 로 꽉 찼고,
#   아무 구간이나 뽑혔다(떨어졌다 다시 오르는 그림). tests/test_scene_finders.py 가 세 겹으로 막는다 —
#     ① RULES·FALLBACK 의 모든 장면이 여기 등록돼 있고 함수가 서로 다르다
#     ② 가짜 차트에 진짜 장면 하나 + 미끼를 심고, 탐색이 진짜를 고른다
#     ③ 점수가 비율(종목·주기끼리 견줄 수 있다)이고 한 값으로 몰리지 않는다
#   실행 중에는 pick() 이 점수 몰림을 재서 경고를 붙인다.
#
# 함수 모양: f(bars, closes, half, direction) → [(점수, 가운데 index, 메모)]
#   점수는 **비율**로 쓴다(가격 그대로 쓰면 비싼 종목이 늘 이긴다 — 09-22 톱니).
#   direction: 'up' · 'down' · None — 대본이 방향을 말할 때만 쓴다.

FINDERS = {}


def finder(name):
    def reg(fn):
        FINDERS[name] = fn
        return fn
    return reg


READABLE = 6      # 구간폭이 봉 하나 높이(중앙값)의 몇 배는 돼야 '읽히는 움직임' 인가


def _rng(seg):
    return max(s['high'] for s in seg) - min(s['low'] for s in seg)


def readable(seg, k=READABLE):
    """점수를 비율로 쓰면 **가격이 거의 안 움직이는 구간**도 흔들림 ÷ 폭이 커져 장면처럼 보인다.
    (09-22 시험: 바탕 노이즈에서 '꺾임 37번' · '오름 100% 내림 100%' 가 1등.)
    MT5 는 화면을 세로로 꽉 채워 그리니, 봉 하나가 화면을 다 차지하면 움직임이 안 읽힌다 —
    구간폭이 봉 높이 중앙값의 k 배는 넘어야 한다. 이것도 비율이라 종목·주기와 상관없다."""
    hs = sorted(s['high'] - s['low'] for s in seg)
    med = hs[len(hs) // 2]
    return med > 0 and _rng(seg) >= k * med


def _windows(bars, half):
    """읽히는 창만 돌려준다 — 모든 탐색이 이걸 거친다."""
    for i in range(half, len(bars) - half):
        seg = bars[i - half:i + half]
        if readable(seg):
            yield i, seg


@finder('support_break')
def _support_break(bars, closes, half, direction, **kw):
    # 앞 70% 에서 같은 바닥을 두 번 이상 찍은 수평선 → 뒤 30% 가 그 아래에 머문다
    out = []
    for i, seg in _windows(bars, half):
        cut = int(len(seg) * 0.7)
        head, tail = seg[:cut], seg[cut:]
        rng = _rng(seg)
        if rng <= 0:
            continue
        sup = min(s['low'] for s in head)
        tol = 0.06 * rng
        touches, last = 0, -99
        for k, s in enumerate(head):
            if s['low'] - sup <= tol and k - last >= 8:
                touches, last = touches + 1, k
        if touches < 2:
            continue
        below = sum(1 for s in tail if s['close'] < sup) / len(tail)
        depth = (sup - min(s['low'] for s in tail)) / rng
        if below < 0.6 or depth <= 0:
            continue
        out.append((depth * min(touches, 3) / 3, i, f'지지 {touches}번 확인 뒤 이탈 · 깊이 {100 * depth:.0f}%'))
    return out


@finder('whipsaw')
def _whipsaw(bars, closes, half, direction, **kw):
    # 구간폭 30% 넘는 꺾임이 다섯 번 이상 — 크게 양쪽으로 쓸린다 (톱니 네 다리와 다르다)
    out = []
    for i in range(half, len(bars) - half):
        if not readable(bars[i - half:i + half]):
            continue
        seg = closes[i - half:i + half]
        rng = max(seg) - min(seg)
        if rng <= 0:
            continue
        # 꺾임마다 크기를 잰다 — 횟수만 세면 8번 넘는 구간이 전부 100% 로 같아진다(09-22 자기검토)
        # 꼭짓점(되돌림이 구간폭 30% 를 넘은 극값)을 차례로 적고, 이웃 꼭짓점 사이를 꺾임 크기로 본다
        th, piv, dirn, tops = 0.3 * rng, seg[0], 0, [seg[0]]
        for v in seg[1:]:
            if dirn >= 0 and v <= piv - th:
                tops.append(piv)
                dirn, piv = -1, v
            elif dirn <= 0 and v >= piv + th:
                tops.append(piv)
                dirn, piv = 1, v
            elif (dirn >= 0 and v > piv) or (dirn < 0 and v < piv):
                piv = v
        sizes = [abs(tops[k + 1] - tops[k]) for k in range(1, len(tops) - 1)]   # 첫 칸(시작점→첫 꼭짓점)은 뺀다
        if len(sizes) >= 4:                           # 꼭짓점 다섯 이상 = 크게 다섯 번 넘게 꺾였다
            amp = sum(sizes) / len(sizes) / rng
            out.append((min(len(sizes), 10) / 10 * amp, i, f'구간폭 30% 넘는 꺾임 {len(sizes)}번 · 평균 크기 {100 * amp:.0f}%'))
    return out


@finder('high_then_drop')
def _high_then_drop(bars, closes, half, direction, **kw):
    # 올라서 고점을 찍고 꺾여 떨어진다 — **오름폭과 내림폭 중 작은 쪽 / 구간폭**.
    # (전엔 '고점이 앞 절반·바닥이 뒤 절반' 이기만 하면 100% 라 가르지 못했다 — 09-22)
    out = []
    for i, seg in _windows(bars, half):
        rng = _rng(seg)
        if rng <= 0:
            continue
        k = max(range(len(seg)), key=lambda j: seg[j]['high'])
        if k < len(seg) * 0.2 or k > len(seg) * 0.7:
            continue                                  # 고점이 화면 가운데쯤 있어야 '뒤' 가 보인다
        rise = seg[k]['high'] - min(s['low'] for s in seg[:k + 1])
        drop = seg[k]['high'] - min(s['low'] for s in seg[k:])
        out.append((min(rise, drop) / rng, i, f'오름 {100 * rise / rng:.0f}% · 내림 {100 * drop / rng:.0f}%'))
    return out


@finder('zigzag3')
def _zigzag3(bars, closes, half, direction, **kw):
    # 세 번 꺾이는 톱니 — 네 토막의 방향이 번갈고, **가장 작은 다리 / 구간폭**
    out = []
    for i in range(half, len(bars) - half):
        if not readable(bars[i - half:i + half]):
            continue
        seg = closes[i - half:i + half]
        q = len(seg) // 4
        d = [seg[(k + 1) * q - 1] - seg[k * q] for k in range(4)]
        rng = max(seg) - min(seg)
        if rng <= 0 or not all((d[k] > 0) != (d[k + 1] > 0) for k in range(3)):
            continue
        if direction and (d[0] > 0) != (direction == 'up'):
            continue
        out.append((min(abs(x) for x in d) / rng, i, f'네 구간 등락 {[round(x, 1) for x in d]}'))
    return out


@finder('chop_box')
def _chop_box(bars, closes, half, direction, **kw):
    # 좁은 박스 — 제자리(순이동 작음) × **앞뒤 넓은 구간에 비해 좁음**.
    # (전엔 제자리만 봐서 시작·끝 가격이 같으면 100% — 넓게 출렁여도 뽑혔다, 09-22)
    out = []
    n = len(bars)
    for i, seg in _windows(bars, half):
        rng = _rng(seg)
        if rng <= 0:
            continue
        ctx = bars[max(0, i - 3 * half):min(n, i + 3 * half)]
        crng = _rng(ctx)
        net = abs(seg[-1]['close'] - seg[0]['close'])
        narrow = 1 - rng / crng if crng > 0 else 0
        out.append(((1 - net / rng) * narrow, i, f'넓은 구간의 {100 * rng / crng:.0f}% 폭 · 순이동 {100 * net / rng:.0f}%'))
    return out


@finder('trend_burst')
def _trend_burst(bars, closes, half, direction, **kw):
    out = []
    for i, seg in _windows(bars, half):
        rng = _rng(seg)
        if rng <= 0:
            continue
        net = seg[-1]['close'] - seg[0]['close']
        if direction and (net > 0) != (direction == 'up'):
            continue
        out.append((abs(net) / rng, i, f'{"상승" if net > 0 else "하락"} · 순이동이 구간폭의 {100 * abs(net) / rng:.0f}%'))
    return out


def _ema_adx(bars, closes, half, switch, direction):
    n = len(bars)
    e200, e20 = ema(closes, 200), ema(closes, 20)
    ax = adx(bars)
    out = []
    for i in range(max(210, half), n - half):
        if ax[i] is None or ax[i - 1] is None or not (ax[i - 1] < 25 <= ax[i]):
            continue
        if not readable(bars[i - half:i + half]):
            continue
        above = closes[i] > e200[i]
        if direction and above != (direction == 'up'):
            continue
        if not switch:
            # ADX 가 25 를 얼마나 힘 있게 넘었나 (0~1) — ADX 값 그대로는 비율이 아니다
            out.append((min(1.0, (ax[i] - 20) / 20), i, f'ADX {ax[i - 1]:.1f}→{ax[i]:.1f} · 200EMA {"위" if above else "아래"}'))
            continue
        for j in range(i + 1, min(n, i + half)):
            if (closes[j] < e20[j]) if above else (closes[j] > e20[j]):
                # 진입 뒤 추세가 붙었다가(길수록) 20EMA 를 깨야 이야기가 된다 — 화면 반 안에서
                # 봉 수만 쓰면 값이 띄엄띄엄해 서로 다른 사건이 같은 점수가 된다 — ADX 세기를 조금 섞는다
                sc = 0.8 * (j - i) / half + 0.2 * min(1.0, (ax[i] - 20) / 20)
                out.append((sc, (i + j) // 2, f'{j - i}봉 뒤 20EMA {"하향" if above else "상향"} 이탈'))
                break
    return out


@finder('ema200_adx_entry')
def _ema200_adx_entry(bars, closes, half, direction, **kw):
    return _ema_adx(bars, closes, half, False, direction)


@finder('ema20_switch')
def _ema20_switch(bars, closes, half, direction, **kw):
    return _ema_adx(bars, closes, half, True, direction)


@finder('session_burst')
def _session_burst(bars, closes, half, direction, **kw):
    # 조용하다가 크게 흔들리기 시작한다 — 뒤 절반 변동폭이 앞의 몇 배인가 (1 을 빼고 0~1 로 누른다)
    out = []
    for i, seg in _windows(bars, half):
        mid = len(seg) // 2
        r1, r2 = _rng(seg[:mid]), _rng(seg[mid:])
        if r1 <= 0:
            continue
        x = r2 / r1
        out.append(((x - 1) / x if x > 1 else 0.0, i, f'뒤 절반 변동폭이 앞의 {x:.1f}배'))
    return out


# ── 이평선 기준 장면 (차11 '20일선의 비밀' 검증에서 필요해졌다, 09-22) ──

def sma(vals, n):
    out, s = [], 0.0
    for i, v in enumerate(vals):
        s += v
        if i >= n:
            s -= vals[i - n]
        out.append(s / n if i >= n - 1 else None)
    return out


def _ma_touch(bars, closes, half, up, ma):
    """추세 중 되돌림이 이평선에 닿고 다시 추세 쪽으로 가는 자리.
    점수 = (닿은 뒤 추세 쪽으로 간 폭 / 구간폭) × (추세 쪽에 머문 비율). 둘 다 비율."""
    m = sma(closes, ma)
    out = []
    for i, seg in _windows(bars, half):
        a = i - half
        mm = m[a:a + len(seg)]
        if mm[0] is None:
            continue
        rng = _rng(seg)
        slope = (mm[-1] - mm[0]) / rng
        if (slope <= 0.15) if up else (slope >= -0.15):
            continue                                  # 이평선이 추세 쪽으로 기울어 있어야 한다
        side = sum(1 for s, v in zip(seg, mm) if (s['close'] > v) == up) / len(seg)
        tol = 0.05 * rng
        lo, hi = len(seg) // 5, len(seg) * 4 // 5     # 닿는 자리는 화면 가운데 쪽 — 앞뒤가 보여야 한다
        k = min(range(lo, hi), key=lambda j: (seg[j]['low'] - mm[j]) if up else (mm[j] - seg[j]['high']))
        gap = (seg[k]['low'] - mm[k]) if up else (mm[k] - seg[k]['high'])
        if gap > tol or gap < -2 * tol:
            continue                                  # 닿거나 살짝 파고든 정도여야 한다
        # 닿기 전에 이평선에서 **벌어져 있다가 내려왔어야** 되돌림이다. 쉬던 가격이 이평선에 얹혀 있으면
        # 늘 '닿은' 것으로 보인다 — 09-22 시험에서 '평평히 쉬다 오른 곳' 이 지지 반등 1등이었다.
        pre = max(((s['close'] - v) if up else (v - s['close'])) for s, v in zip(seg[:k], mm[:k])) if k else 0
        # 문턱 8%: 추세 중 가격은 이평선 위로 구간폭의 ~10% 쯤 떠 있다(시험의 0.3/봉 오름세 11%). 쉬다 오른 곳은 1% 미만.
        if pre < 0.08 * rng:
            continue
        after = seg[k:]
        go = (max(s['high'] for s in after) - seg[k]['low']) if up else (seg[k]['high'] - min(s['low'] for s in after))
        out.append((go / rng * side * min(1.0, pre / (0.15 * rng)), a + k,
                    f'{ma}이평 {"지지" if up else "저항"} 뒤 {100 * go / rng:.0f}% · 닿기 전 벌어짐 {100 * pre / rng:.0f}% · 추세 쪽 {100 * side:.0f}%'))
    return out


@finder('ma_support_bounce')
def _ma_support_bounce(bars, closes, half, direction, **kw):
    return _ma_touch(bars, closes, half, True, kw.get('ma') or 20)


@finder('ma_resist_drop')
def _ma_resist_drop(bars, closes, half, direction, **kw):
    return _ma_touch(bars, closes, half, False, kw.get('ma') or 20)


@finder('ma_flat_box')
def _ma_flat_box(bars, closes, half, direction, **kw):
    # 이평선이 눕고(기울기 작음) 가격이 그 위아래를 여러 번 넘나든다.
    # 점수 = (1 - |기울기|/구간폭) × min(넘나든 횟수, 8)/8 — 좁은 박스권(chop_box)과 달리 이평선이 기준이다
    ma = kw.get('ma') or 20
    m = sma(closes, ma)
    out = []
    for i, seg in _windows(bars, half):
        a = i - half
        mm = m[a:a + len(seg)]
        if mm[0] is None:
            continue
        rng = _rng(seg)
        flat = 1 - min(1.0, abs(mm[-1] - mm[0]) / rng)
        sides = [s['close'] > v for s, v in zip(seg, mm)]
        cross = sum(1 for x, y in zip(sides, sides[1:]) if x != y)
        if cross < 3:
            continue
        # 넘나들되 이평선 근처에서만 떨면 안 읽힌다 — 이평선에서 벌어진 폭의 평균도 본다
        spread = sum(abs(s['close'] - v) for s, v in zip(seg, mm)) / len(seg) / rng
        out.append((flat * min(cross, 8) / 8 * min(1.0, 4 * spread), i,
                    f'{ma}이평 기울기 {100 * (1 - flat):.0f}% · 넘나듦 {cross}번'))
    return out


def _ma_break(bars, closes, half, down, ma):
    """이평선을 반대편으로 뚫고 그쪽으로 추세가 이어진다 (차11 팀장 그림 42장 중 '20일선 하향 이탈 뒤 하락' 10 ·
    '급락 뒤 20일선 돌파 V반등' 6 — 09-22 판독). 점수 = (뚫기 전 반대편 비율) × (뚫은 뒤 이 편 비율) × (뚫은 뒤 간 폭/구간폭)."""
    m = sma(closes, ma)
    out = []
    for i, seg in _windows(bars, half):
        a = i - half
        mm = m[a:a + len(seg)]
        if mm[0] is None:
            continue
        rng = _rng(seg)
        below = [s['close'] < v for s, v in zip(seg, mm)]
        mid = len(seg) // 2
        k = next((j for j in range(mid - 10, mid + 10) if below[j] == down and below[j - 1] != down), None)
        if k is None:
            continue                                  # 화면 가운데쯤에서 뚫어야 앞뒤가 다 보인다
        before = sum(1 for x in below[:k] if x != down) / k
        after = sum(1 for x in below[k:] if x == down) / (len(seg) - k)
        tail = seg[k:]
        go = (seg[k]['close'] - min(s['low'] for s in tail)) if down else (max(s['high'] for s in tail) - seg[k]['close'])
        out.append((before * after * min(1.0, go / (0.5 * rng)), a + k,
                    f'{ma}이평 {"하향 이탈" if down else "상향 돌파"} · 앞 {100 * before:.0f}% 반대편 · 뒤 {100 * after:.0f}% 이 편 · {100 * go / rng:.0f}% 진행'))
    return out


@finder('ma_break_down')
def _ma_break_down(bars, closes, half, direction, **kw):
    return _ma_break(bars, closes, half, True, kw.get('ma') or 20)


@finder('ma_break_up')
def _ma_break_up(bars, closes, half, direction, **kw):
    return _ma_break(bars, closes, half, False, kw.get('ma') or 20)


def find(name, bars, page=110, direction=None, ma=None):
    """이름난 사건이 가장 뚜렷한 구간을 [(점수, 가운데 index, 메모)] 로, 점수 높은 순."""
    if name not in FINDERS:
        raise KeyError(f'{name} 전용 탐색이 없다 — FINDERS 에 등록하라 (남의 계산을 빌려 쓰지 않는다)')
    closes = [b['close'] for b in bars]
    best = FINDERS[name](bars, closes, page // 2, direction, ma=ma)
    if not best:
        return None
    best.sort(reverse=True)
    return best


SATURATED = 3     # 1등 점수가 서로 다른 사건 셋 이상에 똑같이 나오면 '가르지 못한다'


def ties(cands, page=110):
    """1등과 **같은 점수**를 받은 서로 겹치지 않는 사건의 수.

    한 봉씩 밀린 옆 창은 같은 사건이라 점수가 같은 게 정상이다 — 그래서 겹치지 않는 것만 센다.
    이 수가 SATURATED 이상이면 탐색이 구간을 가르지 못한 것이다(09-22 1-2 는 100% 가 수십 곳이었다).
    """
    if not cands:
        return 0
    top = cands[0][0]
    picked = []
    for sc, i, _ in cands:
        if sc < top - 1e-9:
            break
        if all(abs(i - j) >= page for j in picked):
            picked.append(i)
    return len(picked)


def pick(spec, bars, page=110, used=None, step_sec=300, cache=None):
    """점수 높은 후보부터 보되, 시간 구멍이 있거나 이미 쓴 구간과 겹치면 건너뛴다.
    cache(dict) 를 주면 같은 (장면, 봉, 방향, 이평선) 의 탐색을 한 번만 한다 — 차11 은 35비트 중 18비트가 같은 장면이었다."""
    key = (spec['name'], id(bars), page, spec.get('direction'), spec.get('ma'))
    if cache is not None and key in cache:
        cands = cache[key]
    else:
        cands = find(spec['name'], bars, page, spec.get('direction'), spec.get('ma'))
        if cache is not None:
            cache[key] = cands
    if not cands:
        return None
    tie = ties(cands, page)
    used = used if used is not None else []
    chosen = None
    for sc, i, note in cands[:400]:
        a, b = _win(bars, i, page // 2, page // 2)
        if has_gap(bars, a, b, step_sec):
            continue
        if any(not (b <= ua or a >= ub) for ua, ub in used):
            continue
        chosen = (sc, i, note, a, b)
        break
    if chosen is None:
        return None
    sc, i, note, a, b = chosen
    used.append((a, b))
    got = {'id': spec['id'], 'pattern': spec['name'], 'why': spec['why'],
           'indicators': spec['indicators'], 'score': round(sc, 3), 'note': note,
           'from': bars[a]['time'], 'to': bars[b - 1]['time'], 'bars': b - a,
           'ties': tie, 'direction': spec.get('direction')}
    if tie >= SATURATED:
        got['warn'] = f'점수 몰림 — 1등 점수가 서로 다른 {tie}곳에 똑같다. 탐색이 가르지 못한다({spec["name"]})'
    return got


if __name__ == '__main__':
    docx = sys.argv[1]
    symbol = sys.argv[2] if len(sys.argv) > 2 else 'US100.'
    period = sys.argv[3] if len(sys.argv) > 3 else 'M5'
    dt_from = sys.argv[4] if len(sys.argv) > 4 else '2026-09-01T00:00:00'
    dt_to = sys.argv[5] if len(sys.argv) > 5 else '2026-09-18T00:00:00'

    beats = split_beats(read_docx(docx))
    print(f'대본 비트 {len(beats)}개: {[b["id"] for b in beats]}')
    bars = MT5().history(symbol, period, dt_from, dt_to)
    print(f'{symbol} {period} 봉 {len(bars)}개 ({bars[0]["time"]} ~ {bars[-1]["time"]})\n')
    step = {'M1': 60, 'M2': 120, 'M5': 300, 'M15': 900, 'M30': 1800, 'H1': 3600}.get(period, 300)
    used = []
    conti = []
    for be in beats:
        sp = spec_for(be)
        got = pick(sp, bars, used=used, step_sec=step)
        head = be['text'][:38].replace('\n', ' ')
        if got:
            got.update(symbol=symbol, period=period, text=be['text'][:200])
            conti.append(got)
            ind = ','.join(got['indicators']) or '지표없음'
            print(f"({be['id']}) {sp['name']:<18} [{ind}] {got['from'][5:]} ~ {got['to'][5:]}")
            print(f"        왜: {sp['why']} | {got['note']}")
        else:
            print(f"({be['id']}) {sp['name']:<18} 못 찾음")
        print(f"        본문: {head}…")
    import json
    # 회사 드라이브에는 쓰지 않는다 — 현재 폴더에 남긴다
    out = os.environ.get('CONTI_OUT', '콘티_차트장면.json')
    try:
        json.dump(conti, io.open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    except Exception:
        out = '콘티_차트장면.json'
        json.dump(conti, io.open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n콘티 {len(conti)}장 → {out}')
