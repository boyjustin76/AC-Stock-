# -*- coding: utf-8 -*-
"""롱폼 자막(.srt)의 무음 텀으로 챕터를 끊는다. 표준 라이브러리만 쓴다.

롱폼은 챕터마다 녹음을 끊어서 읽는다. 그래서 자막 큐 사이의 빈 시간이
챕터 경계와 같다. 큐 사이 간격을 재서 큰 것부터 경계로 삼는다.

    python3 tools/cutedit/chapters.py gaps  자막.srt [--min 2.0]
        큐 사이 간격을 큰 순서로 본다. 경계를 어디로 잡을지 정하는 용도.

    python3 tools/cutedit/chapters.py split 자막.srt [--min 2.0] [--max-parts N]
        간격으로 끊은 챕터를 시각·길이·첫 문장과 함께 낸다.

간격 기준값(--min)은 회차마다 다르다. gaps 로 분포를 먼저 보고 정한다.
숏폼 자막(shortform)과 달리 여기서는 14자 규칙을 보지 않는다 — 롱폼 자막은
이미 나간 것이고, 이 도구는 자르기만 한다.
"""
import argparse
import io
import re
import sys

TC = re.compile(r"(\d\d):(\d\d):(\d\d)[,.](\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d)[,.](\d\d\d)")


def _sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse(path):
    """[(시작초, 끝초, 텍스트), ...]"""
    txt = io.open(path, encoding="utf-8-sig", errors="replace").read()
    out = []
    for block in re.split(r"\n\s*\n", txt.strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        tc = next((l for l in lines if "-->" in l), None)
        if not tc:
            continue
        m = TC.search(tc)
        if not m:
            continue
        g = m.groups()
        body = " ".join(l.strip() for l in lines[lines.index(tc) + 1:])
        out.append((_sec(*g[:4]), _sec(*g[4:]), body.strip()))
    return out


def gaps(cues):
    """(간격초, 앞 큐 index, 앞 큐 끝, 뒤 큐 시작) — 큰 순서."""
    g = []
    for i in range(len(cues) - 1):
        d = cues[i + 1][0] - cues[i][1]
        if d > 0:
            g.append((round(d, 3), i, cues[i][1], cues[i + 1][0]))
    return sorted(g, reverse=True)


def split(cues, min_gap):
    """무음 간격 min_gap 이상에서 끊는다 → [[큐, ...], ...]"""
    parts, cur = [], [cues[0]]
    for i in range(1, len(cues)):
        if cues[i][0] - cues[i - 1][1] >= min_gap:
            parts.append(cur)
            cur = []
        cur.append(cues[i])
    parts.append(cur)
    return parts


def hhmmss(t):
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def cmd_gaps(a):
    cues = parse(a.srt)
    g = gaps(cues)
    print(f"\n  {a.srt}")
    print(f"  큐 {len(cues)}개 · 총 {hhmmss(cues[-1][1])}\n")
    print(f"  {'간격':>7}  {'앞 큐 끝':>8}  앞 큐 / 뒤 큐")
    for d, i, e, s in g:
        if d < a.min:
            break
        print(f"  {d:6.2f}초  {hhmmss(e):>8}  {cues[i][2][-22:]}  →  {cues[i + 1][2][:22]}")
    small = [d for d, *_ in g if d < a.min]
    print(f"\n  {a.min}초 미만 간격 {len(small)}개 (최대 {max(small) if small else 0:.2f}초)"
          " — 문장 사이 숨이다. 경계로 보지 않는다.\n")


def cmd_split(a):
    cues = parse(a.srt)
    parts = split(cues, a.min)
    print(f"\n  {a.srt}")
    print(f"  큐 {len(cues)}개 → 챕터 {len(parts)}개 (간격 {a.min}초 이상에서 끊음)\n")
    for k, p in enumerate(parts, 1):
        st, en = p[0][0], p[-1][1]
        chars = sum(len(re.sub(r"\s", "", c[2])) for c in p)
        print(f"  [{k:2}] {hhmmss(st)}~{hhmmss(en)}  {en - st:6.1f}초  {len(p):3}큐  {chars:4}자")
        print(f"       {p[0][2][:56]}")
        print(f"       … {p[-1][2][-40:]}")
    print()


def main():
    ap = argparse.ArgumentParser(description="롱폼 자막 → 무음 텀으로 챕터 끊기")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, help_ in (("gaps", cmd_gaps, "큐 사이 간격을 큰 순서로 본다"),
                            ("split", cmd_split, "간격으로 끊은 챕터를 낸다")):
        c = sub.add_parser(name, help=help_)
        c.add_argument("srt")
        c.add_argument("--min", type=float, default=2.0, help="경계로 볼 최소 간격(초)")
        c.set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
