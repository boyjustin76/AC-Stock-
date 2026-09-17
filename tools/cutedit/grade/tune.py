# -*- coding: utf-8 -*-
"""컷 경계 규칙 시험대 — S015·S016 수정본(정답)에 대고 채점한다.

cut_and_srt.py 의 build_cuts 를 파라미터로 흉내 내서, 어떤 규칙이 사람 손과
가장 가까운지 고른다. 감으로 고르지 않기 위해서다.
"""
import io
import json
import os
import re
import xml.etree.ElementTree as ET

FPS = 30000 / 1001
import sys                                                             # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths                                                           # noqa: E402

S15, S16 = paths.work("S015"), paths.work("S016")
X15, X16 = paths.truth_xml("S015"), paths.truth_xml("S016")


def read_sil(p):
    out, s0 = [], None
    for ln in io.open(p, encoding="utf-8"):
        m = re.search(r"silence_start:\s*([\d.]+)", ln)
        if m:
            s0 = float(m.group(1))
        m = re.search(r"silence_end:\s*([\d.]+)", ln)
        if m and s0 is not None:
            out.append((s0, float(m.group(1))))
            s0 = None
    return out


def load(W, X):
    rows = [r for r in json.load(io.open(f"{W}/aligned.json", encoding="utf-8"))
            if r["s"] is not None]
    tr = json.load(io.open(f"{W}/cam_transcript.json", encoding="utf-8"))
    sq = ET.parse(X).getroot().find("sequence")
    ref = sorted((int(c.findtext("in")) / FPS, int(c.findtext("out")) / FPS)
                 for c in sq.find("media/video/track").findall("clipitem"))
    return {"rows": rows, "tr": tr, "ref": ref,
            "sil": read_sil(f"{W}/silences.txt"), "fine": read_sil(f"{W}/silences_fine.txt")}


def words(tr, a, b, weak_p, overlap=True):
    out = []
    for seg in tr:
        for w in seg.get("words") or []:
            hit = (w["s"] < b and w["e"] > a) if overlap else (a - .05 <= w["s"] and w["e"] <= b + .05)
            if hit and w.get("p", 1.0) >= weak_p:
                out.append(w)
    return out


def build(d, P):
    rows, tr, sil, fine = d["rows"], d["tr"], d["sil"], d["fine"]

    def longsil(a, b):
        return [(s, e) for s, e in sil if e - s >= P["CUT_SIL"] and s < b and e > a]

    groups = []
    for r in rows:
        if groups:
            prev = groups[-1][-1]
            if r["s"] - prev["e"] < P["CUT_SIL"] and not longsil(prev["e"], r["s"]):
                groups[-1].append(r)
                continue
        groups.append([r])

    spans = []
    for g in groups:
        a, b = g[0]["s"], g[-1]["e"]
        cur, alo = a, None
        for s, e in longsil(a, b):
            if s > cur + 0.2:
                spans.append((cur, s, alo, s))
            cur, alo = e, e
        spans.append((cur, b, alo, None))

    cuts = []
    for a, b, alo, ahi in spans:
        ws = words(tr, a, b, P["WEAK_P"]) or words(tr, a, b, 0.0)
        w0 = ws[0]["s"] if ws else a
        w0e = ws[0]["e"] if ws else a
        w1 = ws[-1]["e"] if ws else b
        w1s = ws[-1]["s"] if ws else b

        if P.get("MODE") == "current":
            # 지금 저장소에 들어 있는 로직 (S015 만 보고 맞춘 것)
            if alo is not None:
                lo = alo - 0.08
            else:
                e = [x for _, x in fine if w0 - 1.5 < x <= w0 + 0.60]
                lo = max([w0] + ([max(e)] if e else [])) - 0.08 - P.get("IN_BIAS", 0.0)
            if ahi is not None:
                hi = ahi + 0.07
            else:
                st = [x for x, _ in fine if w1 - 0.60 <= x < w1 + 1.5]
                hi = min([w1] + ([min(st)] if st else [])) + 0.07
            if hi - lo < 0.25:
                continue
            cuts.append((round(lo, 3), round(hi, 3)))
            continue
        if alo is not None:
            lo = alo - P["HEAD"]
        else:
            c = [e for _, e in fine
                 if w0 - P["BACK_IN"] <= e <= min(w0 + P["FWD_IN"], w0e)]
            lo = (max(c) - P["HEAD"]) if c else (w0 - P["WHEAD"])
        if ahi is not None:
            hi = ahi + P["TAIL"]
        else:
            c = [s for s, _ in fine
                 if max(w1 - P["BACK_OUT"], w1s) <= s <= w1 + P["FWD_OUT"]]
            hi = (min(c) + P["TAIL"]) if c else (w1 + P["WTAIL"])
        if hi - lo < 0.25:
            continue
        cuts.append((round(lo, 3), round(hi, 3)))
    return cuts


def score(P, verbose=False):
    tot, worst, lines = [], 0.0, []
    for tag, d in DATA.items():
        cuts, ref = build(d, P), d["ref"]
        if len(cuts) != len(ref):
            return None, f"{tag} 컷 수 {len(cuts)}≠{len(ref)}"
        for k, ((a, b), (ra, rb)) in enumerate(zip(cuts, ref), 1):
            for kind, m, r in (("in", a, ra), ("out", b, rb)):
                e = abs(m - r)
                tot.append(e)
                worst = max(worst, e)
                if verbose and e > 0.10:
                    lines.append(f"   {tag} {k:2d} {kind:<3} 내 {m:7.2f} 정답 {r:7.2f} Δ{m-r:+.2f}")
    m = sum(tot) / len(tot)
    if verbose:
        print("\n".join(lines))
    return (m, worst, len(tot)), None


BASE = dict(CUT_SIL=0.65, WEAK_P=0.30, HEAD=0.05, TAIL=0.07,
            WHEAD=0.08, WTAIL=0.07, BACK_IN=0.45, FWD_IN=0.60,
            BACK_OUT=0.60, FWD_OUT=0.40)

DATA = {"S015": load(S15, X15), "S016": load(S16, X16)}

if __name__ == "__main__":
    import itertools, sys
    if "--bias" in sys.argv:
        print("편향   평균     최대    (지금 로직 + IN 을 이만큼 앞으로)")
        for bias in (-0.04, -0.02, 0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12):
            r, err = score(dict(BASE, MODE="current", IN_BIAS=bias))
            print(f"{bias:+.2f}  {r[0]:.4f}  {r[1]:.3f}" if r else f"{bias:+.2f}  {err}")
        raise SystemExit
    if "--current" in sys.argv:
        r, err = score(dict(BASE, MODE="current"), verbose=True)
        print("=>", err or f"평균 {r[0]:.3f}초 · 최대 {r[1]:.2f}초 · 경계 {r[2]}개")
        raise SystemExit
    if "--base" in sys.argv:
        r, err = score(BASE, verbose=True)
        print(BASE)
        print("=>", err or f"평균 {r[0]:.3f}초 · 최대 {r[1]:.2f}초 · 경계 {r[2]}개")
        raise SystemExit
    best = []
    for HEAD in (0.02, 0.04, 0.05, 0.06, 0.08):
        for TAIL in (0.05, 0.06, 0.07, 0.08):
            for WHEAD in (0.06, 0.08, 0.10):
                for BI in (0.35, 0.45, 0.55):
                    for FI in (0.40, 0.60, 0.80):
                        P = dict(BASE, HEAD=HEAD, TAIL=TAIL, WHEAD=WHEAD,
                                 BACK_IN=BI, FWD_IN=FI)
                        r, err = score(P)
                        if r:
                            best.append((r[0], r[1], HEAD, TAIL, WHEAD, BI, FI))
    best.sort()
    print("평균   최대   HEAD TAIL WHEAD BACK_IN FWD_IN")
    for b in best[:12]:
        print(f"{b[0]:.4f} {b[1]:.3f}   {b[2]:.2f} {b[3]:.2f} {b[4]:.2f}  {b[5]:.2f}   {b[6]:.2f}")
    print(f"\n시도 {len(best)}가지")
