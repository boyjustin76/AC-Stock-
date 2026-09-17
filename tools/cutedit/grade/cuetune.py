# -*- coding: utf-8 -*-
"""자막 큐 나누기 시험대.

수정본 .srt 의 큐를 **대본 줄** 단위로 도로 이어 붙인 뒤, 같은 문장을 split_cue 로
다시 나눠 본다. 끊는 자리가 사람이 고른 자리와 얼마나 겹치는지만 본다
(문구 판단은 빼고 순수하게 나누기 로직만).
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                                           # noqa: E402
sys.path.insert(0, paths.CUTEDIT)
from srt_rules import read_srt                                         # noqa: E402
from textnorm import norm                                              # noqa: E402

REF = {tag: (paths.truth_srt(tag), os.path.join(paths.work(tag), "aligned.json"))
       for tag in paths.EPISODE}


def cues(p):
    return [c["t"] for c in read_srt(p)]


def sentences(cs, align):
    """수정본 큐를 대본 줄 단위로 묶는다.

    큐가 빈틈없이 붙어 있어 시간 간격으로는 못 가른다. 대본 줄의 글자 수만큼
    큐를 차례로 삼켜서 묶는다.
    """
    rows = [r for r in json.load(io.open(align, encoding="utf-8")) if r["s"] is not None]
    out, k = [], 0
    for r in rows:
        want, got, parts = norm(r["text"]), "", []
        while k < len(cs) and len(got) < len(want) * 0.85:
            parts.append(cs[k])
            got += norm(cs[k])
            k += 1
        if parts:
            out.append(parts)
    return out


def breaks(parts):
    """조각 목록 → 어절 몇 개째에서 끊었나 (누적 어절 수 집합)."""
    n, s = 0, set()
    for p in parts[:-1]:
        n += len(p.split())
        s.add(n)
    return s


def evaluate(split_fn, show=False):
    hit = tot = exact = lines = extra = miss = 0
    for tag, (p, al) in REF.items():
        for parts in sentences(cues(p), al):
            joined = " ".join(parts)
            if len(joined.split()) < 2:
                continue
            gold, got = breaks(parts), breaks(split_fn(joined))
            lines += 1
            exact += (gold == got)
            hit += len(gold & got)
            tot += len(gold)
            extra += len(got - gold)
            miss += len(gold - got)
            if show and gold != got:
                print(f"  [{tag}] 사람 {parts}")
                print(f"        기계 {split_fn(joined)}")
    return dict(lines=lines, exact=exact, hit=hit, tot=tot, extra=extra, miss=miss)


def report(name, r):
    print(f"{name:<20} 문장 {r['lines']:3d} · 똑같이 {r['exact']:3d}"
          f"({r['exact']/max(1,r['lines'])*100:4.1f}%) · 끊는자리 {r['hit']}/{r['tot']}"
          f" · 더 끊음 {r['extra']} · 덜 끊음 {r['miss']}")


if __name__ == "__main__":
    import srt_rules
    if "--show" in sys.argv:
        report("지금 규칙", evaluate(srt_rules.split_cue, show=True))
        raise SystemExit
    report("지금 규칙", evaluate(srt_rules.split_cue))
    src = io.open(os.path.join(os.path.dirname(srt_rules.__file__), "srt_rules.py"),
                  encoding="utf-8").read()
    for cost in (100, 70, 50, 35, 25, 18, 12, 8, 5):
        ns = {}
        exec(src.replace("dp[i][0] + 100 +", f"dp[i][0] + {cost} +"), ns)
        report(f"큐 비용 {cost}", evaluate(ns["split_cue"]))
