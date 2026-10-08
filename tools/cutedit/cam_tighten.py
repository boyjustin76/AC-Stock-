"""컷 경계를 **말에 딱 붙여** 다시 잡는다 (무음·박수·잡소리·대본 밖 말 제거).

    python tools/cutedit/cam_tighten.py <작업폴더> [--gap 0.30] [--lead 0.10] [--tail 0.20] [--쓰기]

왜 (이정찬 피드백 11개, 2026-10-01)
  지금 컷은 **문장 정렬 구간**을 그대로 썼다. 그 구간 끝에는 말이 끝난 뒤의 침묵·박수·헛기침이
  같이 들어 있어서 "무음 제거 안 됨"(9건)·"박수"(2건)·"잡소리"(1건)·"대본과 무관"(1건)이 나왔다.
  고치는 길은 하나다 — **낱말 타임스탬프**로 경계를 잡는다.

어떻게 — 세 가지를 겹쳐 쓴다. 하나만으로는 다 못 잡는다(실측 10-01).
  1. **대본과 글자 맞대기** — 문장 구간 안의 낱말을 대본 문장과 맞춰, 앞뒤로 **안 맞는 낱말을 떼어낸다.**
     이것이 재촬영 말("아 다시 하겠습니다")·헛말·되풀이한 앞머리를 잡는다.
     (낱말만 믿으면 안 된다: 받아쓰기가 대본에 없는 말도 같은 문장에 붙여 놓는다.)
  2. **소리 지도와 겹치기** — 받아쓰기의 낱말 끝 시각은 **실제보다 길다.** 예: '알려드리겠습니다' 가
     65.31~67.21 로 적혀 있는데 소리는 66.04 에서 이미 끊긴다(1.2초 차이). 그래서 무음 구간을 빼낸다.
  3. **벌어진 자리에서 끊기** — 남은 조각 사이가 `--gap` 보다 벌어지면 컷을 나눈다.
  그리고 앞뒤로 `--lead`·`--tail` 만큼만 숨 쉴 틈을 주되, **무음·문장 밖으로는 안 넘어간다.**
  남는 구간은 **버리지 않고 V2**(enabled=false, audio=true)로 옮긴다 — 이정찬 상시 지시.
  왜 버렸는지 꼬리표를 붙인다: 무음 / 대본 밖 말 / 소리 있음(박수 등).

쓰는 자료 (전부 _작업 폴더)
  aligned.json       정렬된 57문장 (s·e·sec·text)
  cam_transcript.json  받아쓰기 113조각 + 낱말 타임스탬프
  소리.json           무음 구간 (꼬리표용)
  컷리스트.json        원본 메타(소스·fps·크기)를 가져온다
"""
import argparse
import io
import json
import os
from difflib import SequenceMatcher

FPS = 30000 / 1001


def load(work):
    g = lambda n: json.load(io.open(os.path.join(work, n), encoding='utf-8'))  # noqa: E731
    return (g('aligned.json'), g('cam_transcript.json'), g('소리.json'), g('컷리스트.json'),
            g('cam_files.json'))


def 이어붙인자리(파일들):
    """캠 파일들을 **한 타임라인**으로 본 자리 — [(처음, 끝, 키), …].

    `cam_prep.py` 가 파일 순서대로 시각을 이어 붙여 받아쓴다. 정렬·컷도 그 시각으로 돈다.
    컷리스트로 낼 때만 **파일별 시각으로 되돌린다** (키 규칙은 `cam_cutlist.py` 와 같은 `파일[:8]`).
    """
    return [(float(f['시작']), float(f['시작']) + float(f['길이']), f['파일'][:8]) for f in 파일들]


def 파일조각(자리, s, e, 최소=0.12):
    """이어 붙인 구간 (s, e) 를 **파일 경계에서 갈라** [(키, 그 파일 안 시작, 끝, …), …] 로.

    `최소`(4프레임)보다 짧은 조각은 버린다. 숨 쉴 틈(`lead`)이 파일 경계를 넘으면 앞 파일 끝에
    0.1초짜리 부스러기가 남는데, 화면에서는 번쩍임일 뿐이다
    (마02 실측: 새 아웃트로 첫 컷이 옛 모음 파일 끝 803.248~803.348 을 물고 나왔다).
    """
    out = []
    for a, b, 키 in 자리:
        lo, hi = max(s, a), min(e, b)
        if hi - lo > 최소:
            out.append((키, lo - a, hi - a, lo, hi))
    return out


def 무음모으기(소리, 파일들, minsil):
    """파일마다의 무음을 **이어 붙인 시각**으로 모은다. 짧은 숨은 남긴다."""
    자리 = {f['파일']: float(f['시작']) for f in 파일들}
    out = []
    for r in 소리:
        off = 자리.get(r.get('파일'), 0.0)
        out += [(float(a) + off, float(b) + off) for a, b in r['무음']
                if float(b) - float(a) >= minsil]
    out.sort()
    return out


def words_of(tr):
    """받아쓰기에서 낱말을 (시작, 끝, 글자) 로 쭉 편다."""
    out = []
    for seg in tr:
        for w in seg.get('words') or []:
            if w.get('s') is None or w.get('e') is None:
                continue
            out.append((float(w['s']), float(w['e']), str(w['w']).strip(), float(w.get('p', 1.0))))
    out.sort()
    return out


def norm(s):
    """맞대기용으로 글자만 남긴다 (공백·문장부호 버림)."""
    return ''.join(ch for ch in str(s) if ch.isalnum())


def trim_to_script(ws, text, 여유=0.03):
    """낱말 목록 양끝에서 **대본과 안 맞는 것**을 떼어낸다 (재촬영 말·헛말·되풀이한 앞머리).

    앞 또는 뒤의 낱말 하나를 빼서 닮음이 **`여유` 넘게** 올라가면 뺀다. 더 못 올리면 멈춘다.

    여유를 두는 까닭 (이정찬 2026-10-08: "대본과 사람 말이 많이 다를거야")
      낭독이 대본과 조금 다르면, 멀쩡히 말한 낱말을 빼는 쪽이 닮음이 **아주 조금** 높아진다.
      실측 — 대본 `순서는 셋이에요.` 를 `순서는 셋입니다.` 로 말했다. `셋입니다` 를 빼면
      0.571 → 0.600 (0.029 차이). 그래서 말한 낱말이 통째로 컷에서 빠졌다.
      헛말·재촬영 말을 뗄 때는 닮음이 0.09 씩 뛴다 — 여유 0.03 이면 그건 그대로 뗀다.
    """
    want = norm(text)
    if not ws or not want:
        return ws
    lo, hi = 0, len(ws)

    def sim(a, b):
        return SequenceMatcher(None, norm(''.join(w[2] for w in ws[a:b])), want).ratio()

    best = sim(lo, hi)
    while hi - lo > 1:
        cand = []
        if hi - lo > 1:
            cand.append((sim(lo + 1, hi), lo + 1, hi))
            cand.append((sim(lo, hi - 1), lo, hi - 1))
        s2, l2, h2 = max(cand)
        if s2 <= best + 여유:
            break
        best, lo, hi = s2, l2, h2
    return ws[lo:hi]


def subtract(spans, holes):
    """spans 에서 holes 를 빼낸다 (무음 빼기)."""
    out = []
    for s, e in spans:
        cur = [(s, e)]
        for hs, he in holes:
            nxt = []
            for a, b in cur:
                if he <= a or hs >= b:
                    nxt.append((a, b))
                    continue
                if hs > a:
                    nxt.append((a, min(hs, b)))
                if he < b:
                    nxt.append((max(he, a), b))
            cur = nxt
        out += [(a, b) for a, b in cur if b > a]
    return out


def conf(ws, s, e):
    """그 구간에 걸친 낱말들의 확신도 (겹친 길이로 가중)."""
    num = den = 0.0
    for a, b, _t, p in ws:
        ov = min(e, b) - max(s, a)
        if ov > 0:
            num += p * ov
            den += ov
    return (num / den) if den else 1.0


def words_touch(words, s, e):
    """그 구간에 **조금이라도 걸친** 낱말. 걸치기만 해도 소리는 난다."""
    return [w for w in words if w[1] > s + 0.02 and w[0] < e - 0.02]


def 두번말했나(w1, w2):
    """앞 컷 꼬리와 뒤 컷 머리가 **같은 말을 두 번** 하는가.

    글자만 보면 안 된다. 두 가지가 똑같이 '앞 끝 = 뒤 처음' 으로 보이지만 뜻이 반대다 —
      · **두 번 말한 것** — 더듬거나 다시 찍은 자리. 낱말이 **둘**이다. 앞 것을 떼어 낸다.
        (마01 `변동성이` 가 0.2초 사이로 두 번 들렸다, E 지적 2026-10-01)
      · **낱말 하나가 컷 경계에 걸친 것** — 낱말은 **하나**다. 떼어 내면 그 말이 사라진다.
        (마02 `입니다`[105.80~106.86] 한가운데 무음 0.62초가 잡혀 두 컷으로 갈렸다)
    둘을 가르는 것은 닮은 글자가 아니라 **같은 낱말이냐**다. 받아쓰기가 준 낱말 하나면 한 번 말한 것이다.
    """
    if not w1 or not w2:
        return False
    끝, 처음 = w1[-1], w2[0]
    if 끝 is 처음:                       # noqa: F632 — 같은 낱말 하나가 걸친 것
        return False
    return bool(norm(끝[2])) and norm(끝[2]) == norm(처음[2])


def retake_spans(a, segs, words, 남의구간=()):
    """재촬영을 이어 붙인다.

    말하다 끊고 **뒤만 다시 말한** 자리가 있다(실측: 문장13 — 앞 테이크가 '경고를 신호로' 에서 잘리고
    "아 다시 하겠습니다" 뒤에 '변동성이…받아들여야 합니다' 를 다시 말함).
    그럴 때는 뒤 테이크가 대본의 **어디서부터** 다시 말한 것인지 찾아, 앞 테이크는 거기까지만 쓴다.
    돌려주는 것: [(시작, 끝), …] 또는 못 가르면 None.
    """
    want = norm(a.get('text', ''))
    #  **가까운 데서만 찾는다.** 같은 말이 영상 다른 데서 또 나오면(예: "감사합니다") 엉뚱한 자리를
    #  이어 붙여 차례가 뒤집힌다 (실측 10-01: OUTRO 가 중간으로 끌려왔다).
    lo, hi = float(a['s']) - 5.0, float(a['e']) + 25.0

    def 남의것(g):
        """**옆 문장이 차지한 자리**는 재촬영 후보가 아니다.

        이웃한 두 문장이 글자로 거의 같을 때 뒷문장을 앞문장의 재촬영으로 보고 이어 붙여,
        앞문장의 뒷머리를 통째로 버린다 (마02 실측: `청록색으로 바뀐 캔들의 종가에서 매수로
        들어갑니다` 가 `반대로 자홍색으로 바뀐 …` 과 0.45 넘게 닮아, 매수 쪽 5초가 날아갔다).
        """
        길이 = g['e'] - g['s']
        return any(min(g['e'], e2) - max(g['s'], s2) > 길이 * 0.5 for s2, e2 in 남의구간)

    cand = [g for g in segs
            if g['s'] >= lo and g['e'] <= hi and not 남의것(g)
            and SequenceMatcher(None, norm(g['text']), want).ratio() > 0.45]
    if len(cand) < 2:
        return None
    last, prev = cand[-1], cand[-2]
    if last['s'] - prev['e'] < 0.3:
        return None
    tail_txt = norm(last['text'])
    m = SequenceMatcher(None, want, tail_txt).find_longest_match(0, len(want), 0, len(tail_txt))
    p = m.a                                   # 뒤 테이크가 대본의 몇 글자째부터인가
    if p <= 0 or m.size < 6:
        return None                           # 뒤 테이크가 문장 전체면 가를 것이 없다

    def span_of(seg, limit_chars=None):
        ws = [w for w in words if w[1] > seg['s'] - 0.05 and w[0] < seg['e'] + 0.05]
        if limit_chars is not None:
            #  **넘기기 전에 멈춘다.** 넘겨서 담으면 뒤 테이크가 다시 말하는 첫 낱말을 앞에서도
            #  가져가 같은 말이 두 번 들린다 (E 지적 10-01: '변동성이' 가 0.2초 간격으로 두 번).
            keep, n = [], 0
            for w in ws:
                ln = len(norm(w[2]))
                if keep and n + ln > limit_chars:
                    break
                n += ln
                keep.append(w)
            ws = keep
        return (ws[0][0], ws[-1][1]) if ws else None

    head = span_of(prev, p)
    tail_s = span_of(last)
    if not head or not tail_s:
        return None
    #  안전장치: 이어 붙인 앞머리가 문장 첫머리에서 시작해야 한다.
    #  (실측 10-01: 문장11 에서 앞 다섯 낱말이 통째로 날아갔다 — 엉뚱한 조각을 앞 테이크로 집었다.)
    if head[0] > float(a['s']) + 1.0 or tail_s[0] < head[1]:
        return None
    return [head, tail_s]


def 토막내기(ws, sil, gap=0.5):
    """낱말을 **벌어진 자리와 침묵**으로 토막 낸다.

    벌어짐만 보면 안 된다 — 받아쓰기는 낱말 끝을 다음 낱말 머리까지 늘여 적어서, 사이에
    0.8초 침묵이 있어도 낱말 시각상으로는 딱 붙어 있다 (마02 `나온…`[~820.97]·`직전`[820.97~]).
    """
    토막, 지금 = [], []
    for k, w in enumerate(ws):
        지금.append(w)
        if k + 1 == len(ws):
            break
        뒤 = ws[k + 1]
        가운데 = (w[1] + 뒤[0]) / 2.0
        if 뒤[0] - w[1] >= gap or any(a < 가운데 < b for a, b in sil):
            토막.append(지금)
            지금 = []
    if 지금:
        토막.append(지금)
    return 토막


def 되풀이빼기(ws, sil, gap=0.5, 닮음=0.75):
    """한 문장 안에서 **토막째 다시 말한** 자리를 가려, 앞엣것을 버린다.

    이 분은 말하다 막히면 그 토막을 처음부터 다시 말한다. 둘 다 쓰면 같은 말이 두 번 들린다.
    `align_take` 의 '마지막 테이크가 최종본' 규칙을 **문장 안에서** 한 번 더 적용한다.
    (마02 OUTRO: `…정해둔 자리에서 나온—` 하고 끊은 뒤 그 토막을 통째로 다시 말했는데,
     받아쓰기가 두 테이크를 한 구간으로 묶어 `retake_spans` 가 못 가렸다. 그대로 두면
     `trim_to_script` 가 **완성 테이크 쪽을** 떼어 내고 끊긴 쪽을 남긴다.)
    한 문장 안에서만 본다 — 이웃 문장이 서로 닮은 자리가 있다 (마02 `청록색/자홍색`).

    되풀이는 토막 전체가 아니라 **꼬리**에만 붙기도 한다. 한 문장이 세 토막인데 마지막 토막만
    다시 말하면 앞 토막은 `…맞춘다 …들어간다 직전…나온—` 처럼 멀쩡한 앞부분을 달고 있다.
    그래서 앞 토막을 통째로 보지 않고 **꼬리부터 되짚어** 닮은 만큼만 떼어 낸다.

    돌려주는 것: (남은 낱말, 버린 구간들). 버린 구간은 **무음과 같은 구멍**으로 넘겨야 한다 —
    낱말만 빼면 구간은 여전히 '첫 낱말~끝 낱말' 이라 그 자리가 그대로 컷에 남는다.
    """
    토막 = 토막내기(ws, sil, gap)
    남, 구멍 = [], []
    for k, t in enumerate(토막):
        뒤 = norm(''.join(w[2] for w in 토막[k + 1])) if k + 1 < len(토막) else ''
        if 뒤:
            꼬리, 가장, 몇 = '', 0.0, 0
            for j in range(len(t) - 1, -1, -1):
                꼬리 = norm(t[j][2]) + 꼬리
                if len(꼬리) > len(뒤) * 1.6:
                    break
                r = SequenceMatcher(None, 꼬리, 뒤).ratio()
                if r > 가장:
                    가장, 몇 = r, len(t) - j
            if 가장 >= 닮음 and 몇:
                구멍.append((t[len(t) - 몇][0], t[-1][1]))
                t = t[:len(t) - 몇]
        남 += t
    return 남, 구멍


def chunks(al, words, sil, gap, lead, tail, minlen, segs=None,
           junk_len=2.5, junk_p=0.40, frag=1.2, frag_gap=1.2):
    """문장마다: 재촬영을 가려내고 → 대본과 맞대 양끝을 떼고 → 무음을 빼고 → 벌어진 자리에서 끊는다."""
    out = []
    자리 = [(float(x['s']), float(x['e'])) for x in al if x.get('s') is not None]
    for a in al:
        #  정렬이 자리를 못 찾은 문장은 건너뛴다 — 낭독이 대본과 많이 다르면 나온다
        #  (마02 '색.' 한 글자: 후보 0개). 없는 자리를 쓰면 통째로 멈춘다.
        if a.get('s') is None or a.get('e') is None:
            continue
        sec = str(a.get('sec', '')).split()[0] if a.get('sec') else ''
        s, e = float(a['s']), float(a['e'])

        남의 = [p for p in 자리 if p != (s, e)]
        rs = retake_spans(a, segs or [], words, 남의) if segs else None
        구멍 = []
        if rs:
            span = rs
        else:
            ws = [w for w in words if w[1] > s - 0.05 and w[0] < e + 0.05]
            #  토막째 다시 말한 자리 — **대본과 맞대기 전에** 가린다.
            #  `trim_to_script` 는 대본에 한 번 있는 말을 두 번 들으면 **뒤엣것을** 떼어 낸다.
            ws, 구멍 = 되풀이빼기(ws, sil)
            ws = trim_to_script(ws, a.get('text', ''))
            if not ws:
                continue
            span = [(max(ws[0][0], s), min(ws[-1][1], e))]
        for lo_i, hi_i in span:                       # 조각마다 (재촬영이면 둘)
            for a2, b2 in subtract([(lo_i, hi_i)], sil + 구멍):   # 무음·되풀이 빼기
                if b2 - a2 <= 0:
                    continue
                if out and a2 - out[-1]['end'] <= gap and sec == out[-1]['sec']:
                    out[-1]['end'] = b2
                    out[-1]['sent'].add(a['i'])
                    out[-1]['hi'] = hi_i
                else:
                    out.append({'start': a2, 'end': b2, 'sec': sec, 'sent': {a['i']},
                                'lo': lo_i, 'hi': hi_i})

    #  **말이 하나도 안 든 조각은 버린다** — 무음 지도가 놓친 침묵이다 (아래 끝 맞추기의 짝).
    out = [c for c in out if words_touch(words, c['start'], c['end'])]

    #  숨 쉴 틈 — 무음·문장 밖으로는 안 넘어간다
    for k, c in enumerate(out):
        prev_end = out[k - 1]['end'] if k else 0.0
        next_start = out[k + 1]['start'] if k + 1 < len(out) else 1e9
        #  **끝은 정렬 구간이 아니라 마지막 낱말에 붙인다.** 정렬 구간은 문장 끝 뒤의 침묵까지
        #  품고 있어서, 무음 지도가 그 침묵을 놓치면 말 없는 꼬리가 그대로 남는다
        #  (마02 실측: `…나온다` 뒤에 6.4초짜리 빈 컷이 섰다).
        안 = words_touch(words, c['start'], c['end'])
        c['start'] = max(c['start'] - lead, prev_end, c.get('lo', c['start']) - lead,
                         안[0][0] - lead, 0.0)
        c['end'] = min(c['end'] + tail, next_start, c.get('hi', c['end']) + tail,
                       안[-1][1] + tail)
        if c['end'] <= c['start']:
            c['end'] = c['start'] + 0.05
        #  숨 쉴 틈이 **다음 낱말 머리를 물면** 안 된다 — 이어 붙인 자리에서 같은 말이 두 번 들린다
        #  (E 지적 10-01: '변동성이' 가 앞 테이크 꼬리와 뒤 테이크 머리에 겹쳤다).
        nxt = next((w[0] for w in words if w[0] >= c['end'] - tail - 0.01), None)
        if nxt is not None and nxt < c['end']:
            c['end'] = max(c['start'] + 0.05, nxt - 0.02)

    #  짧으면서 받아쓰기 확신이 낮은 조각은 버린다 — 헛말·재촬영 알림("아 다시 하겠습니다")이 여기 걸린다
    kept = []
    for c in out:
        if c['end'] - c['start'] < minlen:
            continue
        if c['end'] - c['start'] < junk_len and conf(words, c['start'], c['end']) < junk_p:
            continue                       # 헛말
        #  이 분은 다시 찍을 때 "(아) 다시 하겠습니다/가겠습니다" 라고 말한다 — 그 말은 대본에 없다.
        txt = norm(' '.join(w[2] for w in words if w[1] > c['start'] and w[0] < c['end']))
        if ('다시하겠습니다' in txt or '다시가겠습니다' in txt) and c['end'] - c['start'] < 4.0:
            continue
        kept.append(c)

    #  재촬영을 이어 붙이면 차례가 뒤집힐 수 있다 — **시각 순으로 세우고 겹친 것은 합친다.**
    kept.sort(key=lambda c: c['start'])
    tidy = []
    for c in kept:
        if tidy and c['start'] < tidy[-1]['end']:
            tidy[-1]['end'] = max(tidy[-1]['end'], c['end'])
            tidy[-1]['sent'] |= c['sent']
        else:
            tidy.append(c)
    kept = tidy

    #  이어 붙인 자리에서 **같은 말이 두 번** 들리지 않게 — 앞 컷 꼬리의 그 낱말을 떼어낸다.
    #  (말을 더듬어 되풀이한 자리·재촬영 이음매에서 나온다. E 지적 10-01 뒤 전수로 네 군데 더 나왔다.)
    for _ in range(3):            # 세 번까지 되풀이 — 같은 말을 두 번 넘게 더듬은 자리가 있다
        changed = False
        for c1, c2 in zip(kept, kept[1:]):
            w1 = words_touch(words, c1['start'], c1['end'])
            w2 = words_touch(words, c2['start'], c2['end'])
            if 두번말했나(w1, w2):
                cut_at = w1[-1][0] - 0.02
                if cut_at - c1['start'] >= 0.4:
                    c1['end'] = cut_at
                    changed = True
        if not changed:
            break

    #  너무 잔 조각은 **도로 붙인다** — 0.4초짜리 컷은 화면에서 번쩍이기만 한다.
    #  사이의 침묵을 살리더라도 이어 붙이는 쪽이 보기 낫다.
    merged = []
    for c in kept:
        if merged and (c['end'] - c['start'] < frag or merged[-1]['end'] - merged[-1]['start'] < frag) \
           and c['start'] - merged[-1]['end'] < frag_gap and c['sec'] == merged[-1]['sec']:
            merged[-1]['end'] = c['end']
            merged[-1]['sent'] |= c['sent']
        else:
            merged.append(c)

    #  붙이고 나서 한 번 더 — 되풀이한 말이 다시 맞붙을 수 있다.
    #  떼어내면 너무 짧아지는 조각(말 더듬은 토막)은 통째로 버린다.
    for _ in range(3):
        out2, changed = [], False
        for k, c in enumerate(merged):
            nxt = merged[k + 1] if k + 1 < len(merged) else None
            w1 = words_touch(words, c['start'], c['end'])
            w2 = words_touch(words, nxt['start'], nxt['end']) if nxt else []
            if 두번말했나(w1, w2):
                cut_at = w1[-1][0] - 0.02
                changed = True
                if cut_at - c['start'] >= 0.4:
                    c['end'] = cut_at
                else:
                    continue                      # 토막째 버린다
            out2.append(c)
        merged = out2
        if not changed:
            break
    return merged


def why(s, e, words, silences):
    """버린 구간에 왜 버렸는지 꼬리표를 붙인다."""
    has_word = any(w[1] > s + 0.05 and w[0] < e - 0.05 for w in words)
    if has_word:
        return '대본 밖 말'
    sil = sum(max(0.0, min(e, b) - max(s, a)) for a, b in silences)
    if sil >= (e - s) * 0.8:
        return '무음'
    return '소리 있음(박수 등)'


def build(work, gap, lead, tail, minlen, minsil=0.35):
    al, tr, 소리, cl, 파일들 = load(work)
    words = words_of(tr)
    #  **짧은 숨은 남긴다** — 다 빼면 말이 토막 나 듣기 사납다. minsil 이상만 뺀다.
    sil = 무음모으기(소리, 파일들, minsil)
    자리 = 이어붙인자리(파일들)
    dur = 자리[-1][1]

    keep = chunks(al, words, sil, gap, lead, tail, minlen, segs=tr)

    #  **놓은 조각으로 길이를 센다.** 버린 부스러기까지 세면 V2 를 놓을 자리가 어긋난다.
    cuts, pos = [], 0.0
    for c in keep:
        쪽 = 파일조각(자리, c['start'], c['end'])
        c['놓은자리'] = pos
        for 키, a, b, _s, _e in 쪽:
            cuts.append({'src': 키, 'in': round(a, 3), 'out': round(b, 3),
                         'label': '%s 이정찬.' % c['sec']})
            pos += b - a
    v1_total = pos

    #  남는 구간 → V2 (버리지 않는다)
    drops, prev = [], 0.0
    for c in keep:
        if c['start'] - prev > 0.5:
            drops.append((prev, c['start']))
        prev = c['end']
    if dur - prev > 0.5:
        drops.append((prev, dur))

    at = v1_total
    for s, e in drops:
        tag = why(s, e, words, sil)
        for 키, a, b, s2, _e2 in 파일조각(자리, s, e):
            cuts.append({'src': 키, 'in': round(a, 3), 'out': round(b, 3), 'track': 2,
                         'at': round(at, 3), 'audio': True, 'enabled': False,
                         'label': '안 씀(%s) %s %d초' % (tag, 키, int(a))})
            at += b - a

    #  구간 마커 — 새 타임라인 시각으로 다시 잡는다
    markers, seen = [], set()
    for c in keep:
        쪽 = 파일조각(자리, c['start'], c['end'])
        if c['sec'] and c['sec'] not in seen and 쪽:
            seen.add(c['sec'])
            markers.append({'at': round(c['놓은자리'], 3), 'name': '구간 %s' % c['sec'],
                            'comment': '%s %d초부터' % (쪽[0][0], int(쪽[0][1]))})

    out = dict(cl)
    out['cuts'] = cuts
    out['markers'] = markers
    return out, keep, drops, v1_total, words, al


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('--gap', type=float, default=0.30, help='이보다 긴 침묵은 끊는다 (초)')
    ap.add_argument('--lead', type=float, default=0.10)
    ap.add_argument('--tail', type=float, default=0.20)
    ap.add_argument('--min', dest='minlen', type=float, default=0.25)
    ap.add_argument('--무음최소', dest='minsil', type=float, default=0.35,
                    help='이보다 짧은 숨은 그냥 둔다 (초)')
    ap.add_argument('--쓰기', dest='write', action='store_true', help='컷리스트.json 을 덮어쓴다')
    a = ap.parse_args()

    out, keep, drops, total, words, al = build(a.work, a.gap, a.lead, a.tail, a.minlen, a.minsil)
    v2 = [c for c in out['cuts'] if c.get('track') == 2]
    print('컷 %d개(V1) · 버림 %d개(V2) · 길이 %.2f초 = %d프레임'
          % (len(keep), len(v2), total, round(total * FPS)))
    tags = {}
    for c in v2:
        t = c['label'].split('(')[1].split(')')[0]
        tags[t] = tags.get(t, 0) + 1
    print('버린 까닭:', ', '.join('%s %d개' % kv for kv in sorted(tags.items())))
    print('구간 마커:', ', '.join('%s@%.1f초' % (m['name'][3:], m['at']) for m in out['markers']))

    if a.write:
        p = os.path.join(a.work, '컷리스트.json')
        io.open(p, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
        print('썼다 →', p)
    else:
        print('(미리보기다. 덮어쓰려면 --쓰기)')


if __name__ == '__main__':
    main()
