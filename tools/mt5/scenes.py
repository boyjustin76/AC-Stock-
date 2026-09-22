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


def split_beats(text):
    """'(1-3)본문…' 을 [(번호, 본문)] 로. 목차 뒤쪽만 본다."""
    if '[목차]' in text:
        text = text[text.index('[목차]'):]
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


def find(name, bars, page=110):
    """이름난 사건이 가장 뚜렷한 구간을 (점수, 가운데 index, 메모) 로 돌려준다."""
    n = len(bars)
    closes = [b['close'] for b in bars]
    best = []
    half = page // 2

    if name in ('high_then_drop', 'support_break', 'whipsaw'):
        # 고점 뒤 낙폭이 큰 자리 — 화면 안에 고점과 바닥이 같이 들어와야 한다
        for i in range(half, n - half):
            a, b = _win(bars, i, half, half)
            seg = bars[a:b]
            hi = max(s['high'] for s in seg[:len(seg) // 2])
            lo = min(s['low'] for s in seg[len(seg) // 2:])
            rng = max(s['high'] for s in seg) - min(s['low'] for s in seg)
            if rng <= 0:
                continue
            best.append(((hi - lo) / rng, i, f'낙폭 {hi - lo:.1f} (구간폭의 {100 * (hi - lo) / rng:.0f}%)'))

    elif name == 'zigzag3':
        # 세 번 꺾이는 톱니 — 1/4 씩 쪼개 방향이 번갈아야 한다
        for i in range(half, n - half):
            a, b = _win(bars, i, half, half)
            seg = closes[a:b]
            q = len(seg) // 4
            legs = [seg[k * q:(k + 1) * q] for k in range(4)]
            d = [le[-1] - le[0] for le in legs if le]
            if len(d) < 4:
                continue
            alt = all((d[k] > 0) != (d[k + 1] > 0) for k in range(3))
            rng = max(seg) - min(seg)
            if alt and rng > 0:
                # 가장 작은 다리 / 구간폭 — 네 번 다 크게 꺾여야 높다. 비율이라 종목·주기끼리 견줄 수 있다.
                # (전엔 등락 합을 가격 그대로 써서 BTCUSD 가 늘 이겼고, 한 다리만 큰 톱니가 뽑혔다 — 09-22)
                best.append((min(abs(x) for x in d) / rng, i, f'네 구간 등락 {[round(x, 1) for x in d]}'))

    elif name == 'chop_box':
        # 좁은 박스 — 전체 폭 대비 순이동이 작을수록 좋다
        for i in range(half, n - half):
            a, b = _win(bars, i, half, half)
            seg = bars[a:b]
            rng = max(s['high'] for s in seg) - min(s['low'] for s in seg)
            net = abs(seg[-1]['close'] - seg[0]['close'])
            if rng <= 0:
                continue
            best.append((1 - net / rng, i, f'폭 {rng:.1f} · 순이동 {net:.1f}'))

    elif name == 'trend_burst':
        for i in range(half, n - half):
            a, b = _win(bars, i, half, half)
            seg = bars[a:b]
            rng = max(s['high'] for s in seg) - min(s['low'] for s in seg)
            net = abs(seg[-1]['close'] - seg[0]['close'])
            if rng <= 0:
                continue
            best.append((net / rng, i, f'순이동 {net:.1f} / 폭 {rng:.1f}'))

    elif name in ('ema200_adx_entry', 'ema20_switch'):
        e200, e20 = ema(closes, 200), ema(closes, 20)
        ax = adx(bars)
        for i in range(max(210, half), n - half):
            if ax[i] is None or ax[i - 1] is None:
                continue
            cross = ax[i - 1] < 25 <= ax[i]
            if not cross:
                continue
            above = closes[i] > e200[i]
            if name == 'ema200_adx_entry':
                best.append((ax[i], i, f'ADX {ax[i - 1]:.1f}→{ax[i]:.1f} · 200EMA {"위" if above else "아래"}'))
            else:
                # 진입 뒤 20EMA 를 반대로 깨는 봉이 화면 안에 있어야 한다
                for j in range(i + 1, min(n, i + half)):
                    broke = (closes[j] < e20[j]) if above else (closes[j] > e20[j])
                    if broke:
                        best.append((ax[i] + (j - i), (i + j) // 2,
                                     f'{j - i}봉 뒤 20EMA {"하향" if above else "상향"} 이탈'))
                        break

    elif name == 'session_burst':
        # 미국 개장(서버시간 기준 오후) 뒤 변동폭이 앞 시간대보다 큰 날
        for i in range(half, n - half):
            a, b = _win(bars, i, half, half)
            seg = bars[a:b]
            mid = len(seg) // 2
            r1 = max(s['high'] for s in seg[:mid]) - min(s['low'] for s in seg[:mid])
            r2 = max(s['high'] for s in seg[mid:]) - min(s['low'] for s in seg[mid:])
            if r1 <= 0:
                continue
            best.append((r2 / r1, i, f'뒤 절반 변동폭이 앞의 {r2 / r1:.1f}배'))

    if not best:
        return None
    best.sort(reverse=True)
    return best


def pick(spec, bars, page=110, used=None, step_sec=300):
    """점수 높은 후보부터 보되, 시간 구멍이 있거나 이미 쓴 구간과 겹치면 건너뛴다."""
    cands = find(spec['name'], bars, page)
    if not cands:
        return None
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
    return {'id': spec['id'], 'pattern': spec['name'], 'why': spec['why'],
            'indicators': spec['indicators'], 'score': round(sc, 3), 'note': note,
            'from': bars[a]['time'], 'to': bars[b - 1]['time'], 'bars': b - a}


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
