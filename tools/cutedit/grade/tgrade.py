# -*- coding: utf-8 -*-
"""자막 큐 시각 채점대 — 글자 수 비례 vs 낱말 시각.

정답: 이정찬이 손으로 고친 S015·S016 자막(_수정.srt)과 컷(_컷편집_수정.xml).
나누기 차이는 빼고 **시각만** 본다 — 사람이 끊은 큐 그대로를 두 방식으로 배치해
사람 시각과 견준다.
"""
import io
import json
import os
import re
import statistics as st
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                                           # noqa: E402
sys.path.insert(0, paths.CUTEDIT)
from cut_and_srt import norm, words_between   # noqa: E402

FPS = 30000 / 1001
REF = {tag: (paths.truth_xml(tag), paths.truth_srt(tag), paths.work(tag))
       for tag in paths.EPISODE}


def sec(t):
    h, m, r = t.split(":")
    s, ms = r.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def cues(p):
    s = io.open(p, encoding="utf-8-sig", errors="replace").read().replace("\r\n", "\n")
    out = []
    for blk in re.split(r"\n\s*\n", s.strip()):
        L = [x for x in blk.split("\n") if x.strip()]
        i = 1 if L and re.match(r"^\d+$", L[0]) else 0
        if i >= len(L) or "-->" not in L[i]:
            continue
        m = re.search(r"([\d:,]+) --> ([\d:,]+)", L[i])
        out.append((sec(m.group(1)), sec(m.group(2)), " ".join(L[i + 1:]).strip()))
    return out


def human_cuts(p):
    sq = ET.parse(p).getroot().find("sequence")
    cs = []
    for c in sq.find("media/video/track").findall("clipitem"):
        cs.append((int(c.findtext("in")) / FPS, int(c.findtext("out")) / FPS,
                   int(c.findtext("start")) / FPS))
    return sorted(cs, key=lambda x: x[2])


def to_out(t, cuts):
    for a, b, s in cuts:
        if a - 1e-6 <= t <= b + 1e-6:
            return s + (t - a)
    nxt = [(a, s) for a, b, s in cuts if a > t]          # 잘려 나간 틈이면 다음 컷 머리
    return min(nxt)[1] if nxt else cuts[-1][2] + cuts[-1][1] - cuts[-1][0]


def group(cs, rows):
    out, k = [], 0
    for r in rows:
        want, got, parts = norm(r["text"]), "", []
        while k < len(cs) and len(got) < len(want) * 0.85:
            parts.append(cs[k])
            got += norm(cs[k][2])
            k += 1
        if parts:
            out.append((r, parts))
    return out


def main():
    err = {"비례": [], "낱말": []}
    for tag, (XML, SRT, W) in REF.items():
        cuts = human_cuts(XML)
        cs = cues(SRT)
        rows = [r for r in json.load(io.open(os.path.join(W, "aligned.json"), encoding="utf-8"))
                if r["s"] is not None]
        tr = json.load(io.open(os.path.join(W, "cam_transcript.json"), encoding="utf-8"))
        n_tag = 0
        for r, parts in group(cs, rows):
            if len(parts) < 2:
                continue
            s0, e0 = to_out(r["s"], cuts), to_out(r["e"], cuts)
            N = sum(len(norm(p[2])) for p in parts) or 1
            ws = words_between(tr, r["s"], r["e"])
            cum, n = [], 0
            for w in ws:
                L = len(norm(w["w"]))
                cum.append((n, n + L, w))
                n += L
            acc = 0
            for k, (hs, he, t) in enumerate(parts):
                if k > 0:           # 문장 첫 큐는 두 방식이 같다 — 나머지만 센다
                    prop = s0 + (e0 - s0) * acc / N
                    hit = [w for a, b, w in cum if a <= acc < b]
                    if hit:
                        word = to_out(hit[0]["s"], cuts)
                        err["비례"].append(prop - hs)
                        err["낱말"].append(word - hs)
                        n_tag += 1
                acc += len(norm(t))
        print(f"{tag}: 채점한 큐 시작 {n_tag}개")
    print()
    print("방식    평균|오차|  중앙값|오차|  0.1초 넘음  0.2초 넘음  0.3초 넘음  치우침(평균)")
    for k, v in err.items():
        a = [abs(x) for x in v]
        print(f"{k:<6} {st.mean(a):8.3f}   {st.median(a):8.3f}    "
              f"{sum(x > 0.1 for x in a):3d}/{len(a)}    {sum(x > 0.2 for x in a):3d}/{len(a)}"
              f"    {sum(x > 0.3 for x in a):3d}/{len(a)}    {st.mean(v):+.3f}")
    # 낱말 방식에 고정 치우침을 빼면 얼마나 되나 (whisper 가 시작을 일찍 잡는 몫)
    b = st.median(err["낱말"])
    a = [abs(x - b) for x in err["낱말"]]
    print(f"낱말-치우침({b:+.3f}) {st.mean(a):.3f}  중앙값 {st.median(a):.3f}  "
          f"0.1초 넘음 {sum(x > 0.1 for x in a)}/{len(a)}  0.2초 넘음 {sum(x > 0.2 for x in a)}/{len(a)}")


if __name__ == "__main__":
    main()
