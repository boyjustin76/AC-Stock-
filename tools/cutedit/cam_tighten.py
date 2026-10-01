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
    return g('aligned.json'), g('cam_transcript.json'), g('소리.json')[0], g('컷리스트.json')


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


def trim_to_script(ws, text):
    """낱말 목록 양끝에서 **대본과 안 맞는 것**을 떼어낸다 (재촬영 말·헛말·되풀이한 앞머리).

    앞 또는 뒤의 낱말 하나를 빼서 닮음이 올라가면 뺀다. 더 못 올리면 멈춘다.
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
        if s2 <= best + 1e-6:
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


def retake_spans(a, segs, words):
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
    cand = [g for g in segs
            if g['s'] >= lo and g['e'] <= hi
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
            keep, n = [], 0
            for w in ws:
                n += len(norm(w[2]))
                keep.append(w)
                if n >= limit_chars:
                    break
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


def chunks(al, words, sil, gap, lead, tail, minlen, segs=None,
           junk_len=2.5, junk_p=0.40, frag=1.2, frag_gap=1.2):
    """문장마다: 재촬영을 가려내고 → 대본과 맞대 양끝을 떼고 → 무음을 빼고 → 벌어진 자리에서 끊는다."""
    out = []
    for a in al:
        sec = str(a.get('sec', '')).split()[0] if a.get('sec') else ''
        s, e = float(a['s']), float(a['e'])

        rs = retake_spans(a, segs or [], words) if segs else None
        if rs:
            span = rs
        else:
            ws = [w for w in words if w[1] > s - 0.05 and w[0] < e + 0.05]
            ws = trim_to_script(ws, a.get('text', ''))
            if not ws:
                continue
            span = [(max(ws[0][0], s), min(ws[-1][1], e))]
        for lo_i, hi_i in span:                       # 조각마다 (재촬영이면 둘)
            for a2, b2 in subtract([(lo_i, hi_i)], sil):   # 무음 빼기
                if b2 - a2 <= 0:
                    continue
                if out and a2 - out[-1]['end'] <= gap and sec == out[-1]['sec']:
                    out[-1]['end'] = b2
                    out[-1]['sent'].add(a['i'])
                    out[-1]['hi'] = hi_i
                else:
                    out.append({'start': a2, 'end': b2, 'sec': sec, 'sent': {a['i']},
                                'lo': lo_i, 'hi': hi_i})

    #  숨 쉴 틈 — 무음·문장 밖으로는 안 넘어간다
    for k, c in enumerate(out):
        prev_end = out[k - 1]['end'] if k else 0.0
        next_start = out[k + 1]['start'] if k + 1 < len(out) else 1e9
        c['start'] = max(c['start'] - lead, prev_end, c.get('lo', c['start']) - lead, 0.0)
        c['end'] = min(c['end'] + tail, next_start, c.get('hi', c['end']) + tail)

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
    al, tr, snd, cl = load(work)
    words = words_of(tr)
    #  **짧은 숨은 남긴다** — 다 빼면 말이 토막 나 듣기 사납다. minsil 이상만 뺀다.
    sil = [(float(a), float(b)) for a, b in snd['무음'] if float(b) - float(a) >= minsil]
    dur = float(list(cl['sources'].values())[0]['dur'])
    srckey = list(cl['sources'].keys())[0]

    keep = chunks(al, words, sil, gap, lead, tail, minlen, segs=tr)

    cuts, pos = [], 0.0
    for c in keep:
        cuts.append({'src': srckey, 'in': round(c['start'], 3), 'out': round(c['end'], 3),
                     'label': '%s 이정찬.' % c['sec']})
        pos += c['end'] - c['start']
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
        cuts.append({'src': srckey, 'in': round(s, 3), 'out': round(e, 3), 'track': 2,
                     'at': round(at, 3), 'audio': True, 'enabled': False,
                     'label': '안 씀(%s) %s %d초' % (tag, srckey, int(s))})
        at += e - s

    #  구간 마커 — 새 타임라인 시각으로 다시 잡는다
    markers, seen, t = [], set(), 0.0
    for c in keep:
        if c['sec'] and c['sec'] not in seen:
            seen.add(c['sec'])
            markers.append({'at': round(t, 3), 'name': '구간 %s' % c['sec'],
                            'comment': '%smp4 %d초부터' % (srckey, int(c['start']))})
        t += c['end'] - c['start']

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
