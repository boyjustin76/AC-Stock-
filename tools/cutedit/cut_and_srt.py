# -*- coding: utf-8 -*-
"""aligned.json → 컷리스트(json/txt) + 자막(srt).

align_take.py 가 고른 '마지막 테이크' 구간을 붙여 시퀀스용 컷리스트를 만들고,
같은 타임라인 위에 자막을 얹는다.

경계 규칙은 짐작이 아니라 실측이다 — S015 에서 이정찬이 손으로 고친 시퀀스
(컷 12개)의 경계 24개를 실측 무음과 대조해 뽑았다. 24개 중 22개가 오차
0.06초 안에서 아래 식과 맞는다.

    IN  = max(단어 시작, 직전 무음 끝)  - IN_HANDLE
    OUT = min(단어 끝,   직후 무음 시작) + OUT_HANDLE
    무음이 CUT_SIL 이상이면 컷으로 잘라 버린다

무음은 두 벌을 쓴다 — 컷을 끊을지는 거친 것(0.30초+)으로 판단하고, 경계를
붙일 때는 고운 것(0.12초+)에 붙인다. 말과 말 사이 짧은 숨까지 잡아야 경계가
맞는다 (62.50 의 0.16초 무음이 없으면 첫 컷 끝이 0.38초 길어진다).

세 가지가 핵심이다 —
  · **경계는 STT 단어 시각이 아니라 실측 무음에 붙인다.** whisper 는 말 끝을
    0.5초까지 길게 잡는다(166.97 대 167.61). 그대로 쓰면 뒤에 침묵이 붙는다.
  · **말 시작과 무음 끝 중 늦은 쪽**을 쓴다. 무음이 먼저 끝나고 숨소리가 이어지는
    자리(90.93 무음끝 / 91.41 말시작)와 그 반대(138.99 / 138.77)가 둘 다 있다.
  · **확신도 낮은 낱말(p < WEAK_P)은 경계 계산에서 뺀다.** whisper 가 잡음에
    'ㄱ' 같은 유령 낱말을 붙여 시작을 앞으로 끌고 간다(84.74 '그' p=0.06).

자막 문구는 **낭독을 따른다**. 대본과 다르게 읽은 곳은 그대로 싣되, STT 오인식만
대본으로 되돌린다(휘돌이진 → 휘두르진). 둘을 확신도로는 못 가르므로 — 오인식
'휘돌이진'이 0.99, 진짜 바뀐 '보고'가 0.77 이었다 — 갈린 곳은 전부 목록으로 낸다.
큐 나누기는 srt_rules.split_cue 가 진본이다 (14자 규칙).

    python3 tools/cutedit/cut_and_srt.py <작업폴더> --source <원본.mp4> --name <시퀀스이름>
"""
import argparse
import io
import json
import os
import re
import sys
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from srt_rules import LONG_MAX_LEN, LONG_MIN_LEN, MAX_LEN, split_cue

CUT_SIL = 0.65      # 이 이상 무음이면 잘라낸다 (0.56 은 남겼고 0.76 은 잘랐다)
IN_HANDLE = 0.08    # 말 시작 앞에 남기는 여유
OUT_HANDLE = 0.07   # 말 끝 뒤에 남기는 여유
WEAK_P = 0.30       # 이보다 확신도 낮은 낱말은 경계 계산에서 뺀다
OVERRUN = 0.60      # whisper 가 말 끝을 늘려 잡는 최대치 — 이만큼은 되짚어 본다
TAIL_PUNCT = "。.,、"  # 큐 끝에서 떼는 구두점 (물음표·느낌표는 남긴다)
# 자막은 말보다 조금 먼저 뜬다. 사람 수정본(S015·S016 큐 시작 102개)에 당김 값을 채점 —
#   0초 평균오차 0.301 · 0.10초 0.248 · 0.15초 0.240 · 0.20초 0.246 · 0.30초 0.270
# 0.10~0.20 이 고원이라 가운데를 쓴다. 0.3초 넘게 어긋난 큐는 36 → 22 개.
# (글자 수 비례를 낱말 시각 방식으로 바꾸는 것도 채점했는데 더 나빴다 — 0.279 대 0.315)
LEAD = 0.15
# 자막 표기 통일 — 대본과 자막에서 다르게 쓰는 말.
# 채널 이름은 자막에서 늘 붙여 쓴다 (나간 편들 자막 전수: '더원트레이더였습니다',
# '더원트레이더와 함께하는'). 대본만 '더원 트레이더' 로 띄어 쓴다.
TERMS = {"더원 트레이더": "더원트레이더"}


def norm(t):
    return re.sub(r"[^0-9가-힣a-zA-Z]", "", t)


def read_silences(path):
    out, start = [], None
    if not os.path.exists(path):
        return out
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        m = re.search(r"silence_start:\s*([\d.]+)", ln)
        if m:
            start = float(m.group(1))
        m = re.search(r"silence_end:\s*([\d.]+)", ln)
        if m and start is not None:
            out.append((start, float(m.group(1))))
            start = None
    return out


def words_between(tr, a, b, weak=True, overlap=False):
    """[a,b] 안의 낱말. overlap=True 면 걸치기만 해도 센다.

    경계를 잡을 때는 걸친 낱말도 세야 한다 — whisper 는 말 끝을 뒤 무음 속까지
    길게 잡아서(예: '녹입니다' 끝 89.20, 실제 무음 시작 88.68), 완전히 들어온
    낱말만 세면 마지막 낱말이 통째로 빠지고 컷이 잘린다.
    """
    out = []
    for seg in tr:
        for w in seg.get("words") or []:
            hit = (w["s"] < b and w["e"] > a) if overlap else (a - 0.05 <= w["s"] and w["e"] <= b + 0.05)
            if hit and (weak or w.get("p", 1.0) >= WEAK_P):
                out.append(w)
    return out


def bounds(a, b, tr, sil, anchor_lo=None, anchor_hi=None):
    """구간 하나의 실제 컷 경계.

        IN  = max(말 시작, 직전 무음 끝)  - IN_HANDLE
        OUT = min(말 끝,   직후 무음 시작) + OUT_HANDLE

    anchor_lo/hi 는 이 구간이 긴 무음에서 잘려 나온 경우의 그 무음 모서리다.
    """
    ws = (words_between(tr, a, b, weak=False, overlap=True)
          or words_between(tr, a, b, overlap=True))
    w0 = ws[0]["s"] if ws else a
    w1 = ws[-1]["e"] if ws else b

    lo_cand = [w0]
    if anchor_lo is not None:
        lo_cand.append(anchor_lo)
    else:
        # 말 시작 **직전**의 무음 끝 — 가장 늦은 것. 말 안으로 들어가지 않게
        # OVERRUN 까지만 되짚는다 (whisper 가 시작을 앞당겨 잡는 만큼).
        ends = [e for _, e in sil if w0 - 1.5 < e <= w0 + OVERRUN]
        if ends:
            lo_cand.append(max(ends))
    hi_cand = [w1]
    if anchor_hi is not None:
        hi_cand.append(anchor_hi)
    else:
        # 말 끝 **직후**의 무음 시작 — 가장 이른 것. whisper 가 말 끝을 무음
        # 속까지 늘려 잡으므로 w1 보다 OVERRUN 앞선 것까지 후보로 본다.
        starts = [s for s, _ in sil if w1 - OVERRUN <= s < w1 + 1.5]
        if starts:
            hi_cand.append(min(starts))

    lo, hi = max(lo_cand) - IN_HANDLE, min(hi_cand) + OUT_HANDLE
    if hi <= lo + 0.2:
        lo, hi = w0 - IN_HANDLE, w1 + OUT_HANDLE
    return round(lo, 3), round(hi, 3)


def long_sil(sil, a, b):
    """[a,b] 안에 걸치는 CUT_SIL 이상 무음."""
    return [(s, e) for s, e in sil if e - s >= CUT_SIL and s < b and e > a]


def build_cuts(rows, tr, sil, fine=None):
    """채택 구간을 이어 붙이되, 그 안팎의 긴 무음에서 끊는다."""
    # 1) 문장을 덩어리로 — 사이에 긴 무음이 있거나 사이가 벌어지면 끊는다
    groups = []
    for r in rows:
        if groups:
            prev = groups[-1][-1]
            gap = r["s"] - prev["e"]
            if gap < CUT_SIL and not long_sil(sil, prev["e"], r["s"]):
                groups[-1].append(r)
                continue
        groups.append([r])

    # 2) 덩어리 안에 긴 무음이 있으면 거기서 또 끊는다 (문장 중간 쉼)
    spans = []
    for g in groups:
        a, b = g[0]["s"], g[-1]["e"]
        cur, alo = a, None
        for s, e in long_sil(sil, a, b):
            if s > cur + 0.2:
                spans.append((cur, s, alo, s, g))
            cur, alo = e, e
        spans.append((cur, b, alo, None, g))

    cuts = []
    for a, b, alo, ahi, g in spans:
        lo, hi = bounds(a, b, tr, fine or sil, alo, ahi)
        if hi - lo < 0.25:
            continue
        cuts.append({"in": lo, "out": hi,
                     "label": f'{g[0]["sec"]} {g[0]["text"][:14]}'})
    return cuts


def spoken_text(script, ws, verified=None):
    """자막 문구 — 낭독을 따르되 STT 오인식은 대본으로 되돌린다.

    verify_text.py 가 큰 모델로 확인해 둔 게 있으면 그걸 쓴다. 없으면 medium
    결과로 판단하는데, 그건 오인식을 자막에 실을 수 있다 (확신도로는 못 가른다).
    """
    if verified:
        return verified["use"], (verified["use"] if verified["use"] != script else None)
    heard = " ".join(w["w"].strip() for w in ws).strip()
    if not heard or SequenceMatcher(None, norm(script), norm(heard)).ratio() >= 0.995:
        return script, None
    tail = "".join(re.findall(r"[?!”\"']+$", script.strip()) or [""])
    return heard.rstrip(" .,!?") + tail, heard


def fix_terms(t):
    """자막 표기 통일 (TERMS). 구두점 처리는 srt_rules.split_cue 가 맡는다."""
    for a, b in TERMS.items():
        t = t.replace(a, b)
    return t


def fmt(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    return f"{h:02d}:{m:02d}:{t % 60:06.3f}".replace(".", ",")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--source", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--fps", type=float, default=29.97)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--src-dur", type=float, default=0.0)
    ap.add_argument("--script-text", action="store_true",
                    help="자막을 낭독이 아니라 대본 표기로 낸다")
    ap.add_argument("--long", action="store_true",
                    help="롱폼(1920x1080) — 자막 큐 21자, 시퀀스 가로. 컷 경계 값은 그대로")
    a = ap.parse_args()
    max_len = LONG_MAX_LEN if a.long else MAX_LEN
    if a.long and (a.width, a.height) == (1080, 1920):
        a.width, a.height = 1920, 1080
    S = a.dir

    rows = [r for r in json.load(io.open(f"{S}/aligned.json", encoding="utf-8"))
            if r["s"] is not None]
    tr = json.load(io.open(f"{S}/cam_transcript.json", encoding="utf-8"))
    vf = {}
    if os.path.exists(f"{S}/verified.json"):
        vf = json.load(io.open(f"{S}/verified.json", encoding="utf-8"))
    # 사람이 정한 것이 제일 세다 — {"9": "야구도 ... 휘두르진 않습니다"}
    if os.path.exists(f"{S}/text_fix.json"):
        for k, v in json.load(io.open(f"{S}/text_fix.json", encoding="utf-8")).items():
            vf.setdefault(k, {})["use"] = v
    sil = read_silences(f"{S}/silences.txt")            # 컷 판단용 (0.30s+)
    fine = read_silences(f"{S}/silences_fine.txt")      # 경계 스냅용 (0.12s+)
    cuts = build_cuts(rows, tr, sil, fine)
    # 경계 손질 — {"in": {"207.45": 207.14}, "out": {...}, "why": {...}}
    # 자동 경계가 **음량·VAD 로 재서 틀렸다고 확인된 자리만** 적는다 (text_fix.json 과 같은 자리).
    # 자막 시각이 고친 경계를 따라가도록 to_out 보다 먼저 건다.
    if os.path.exists(f"{S}/cut_fix.json"):
        cf = json.load(io.open(f"{S}/cut_fix.json", encoding="utf-8"))
        for c in cuts:
            for kind in ("in", "out"):
                for k, v in (cf.get(kind) or {}).items():
                    if abs(c[kind] - float(k)) < 0.02:
                        print(f"경계 손질 {kind.upper()} {c[kind]:.2f} → {float(v):.2f}"
                              f"  {(cf.get('why') or {}).get(k, '')}")
                        c[kind] = float(v)

    def to_out(t):
        acc = 0.0
        for c in cuts:
            if t <= c["out"]:
                return acc + max(0.0, t - c["in"])
            acc += c["out"] - c["in"]
        return acc

    cues, changed = [], []
    for r in rows:
        # 문구 비교는 확신도로 거르지 않는다 — 거르면 낱말이 통째로 빠진다
        # ('내가 칠 수 있는' → '칠 수 있는'). 확신도 필터는 경계 계산 전용이다.
        ws = words_between(tr, r["s"], r["e"])
        text, heard = spoken_text(r["text"], ws, vf.get(str(r["i"])))
        if heard:
            changed.append((r["i"], r["text"], text))
        if a.script_text:
            text = r["text"]
        s0, e0 = to_out(r["s"]), to_out(r["e"])
        chunks = [fix_terms(c) for c in split_cue(text, max_len=max_len, min_len=LONG_MIN_LEN if a.long else 0) if c.strip()]
        chunks = [c for c in chunks if c]
        n = sum(len(norm(c)) for c in chunks) or 1
        acc = 0
        for ch in chunks:
            k = len(norm(ch))
            cs, ce = s0 + (e0 - s0) * acc / n, s0 + (e0 - s0) * (acc + k) / n
            acc += k
            if cues and cs - cues[-1]["e"] < 0.08:
                cs = cues[-1]["e"]
            cues.append({"s": cs, "e": ce, "t": ch})

    # 당김(LEAD) — 앞 큐와 붙어 있으면 앞 큐 끝도 같이 당긴다 (겹치지 않게).
    for k, c in enumerate(cues):
        s = max(0.0, c["s"] - LEAD)
        if k and cues[k - 1]["e"] > s:
            s = max(s, cues[k - 1]["s"] + 0.2)
            cues[k - 1]["e"] = s
        c["s"] = s

    spec = {"source": os.path.abspath(a.source), "name": a.name, "fps": a.fps,
            "width": a.width, "height": a.height, "src_dur": a.src_dur, "cuts": cuts}
    json.dump(spec, io.open(f"{S}/cuts.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    io.open(f"{S}/out.srt", "w", encoding="utf-8-sig", newline="\n").write(
        "\n".join(f"{i}\n{fmt(c['s'])} --> {fmt(c['e'])}\n{c['t']}\n"
                  for i, c in enumerate(cues, 1)))

    lst, acc = [], 0.0
    for i, c in enumerate(cuts, 1):
        d = c["out"] - c["in"]
        lst.append(f"{i:2d}  소스 {c['in']:7.2f}-{c['out']:7.2f}  "
                   f"→ 타임라인 {acc:6.2f}-{acc + d:6.2f}  ({d:5.2f}초)  {c['label']}")
        acc += d
    io.open(f"{S}/컷리스트.txt", "w", encoding="utf-8", newline="\n").write(
        "\n".join(lst) + "\n")

    # '경계가 낱말 한가운데를 자르는 수'를 문턱 고르는 지표로 써 보려 했는데
    # 쓸모가 없었다 — 정답이 확인된 S015 도 24개 중 12개가 그렇게 나온다.
    # whisper 가 말 끝을 길게 잡는 양을 재고 있을 뿐이라, 문턱이 낮을수록
    # (= 덜 다듬을수록) 좋아 보이는 거꾸로 된 지표다. 그래서 빼 두었다.
    print("\n".join(lst))
    print(f"\n컷 {len(cuts)}개 · 완성 길이 {acc:.2f}초 · 자막 큐 {len(cues)}개")
    if changed:
        print("\n대본과 다르게 읽은 곳 — 자막은 낭독을 실었다. STT 오인식이면 되돌릴 것:")
        for i, was, now in changed:
            print(f"  {i:3d}  대본 {was}\n       자막 {now}")


if __name__ == "__main__":
    main()
