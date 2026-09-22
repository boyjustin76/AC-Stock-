# -*- coding: utf-8 -*-
"""회사 Pool 롱폼 대본의 '구간 뼈대'와 구간별 분량 비율을 잰다.

차명(Old) 대본은 6단(후킹·소개·본론#1·문제제시·본론#2·아웃트로) 틀을 쓴다 — 몇 편이 그런지,
각 구간이 전체의 몇 %인지 재서 차12 의 구간별 분량을 그 비율로 잡는다.
"""
import glob
import io
import os
import re
import statistics as st
from paths import POOL  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SEC = [("후킹", r"^\s*1[\.\)]\s*후킹"), ("소개", r"^\s*2[\.\)]\s*소개"),
       ("본론1", r"^\s*3[\.\)]\s*본론\s*#?1"), ("문제제시", r"^\s*4[\.\)]\s*문제"),
       ("본론2", r"^\s*5[\.\)]\s*본론\s*#?2"), ("아웃트로", r"^\s*6[\.\)]\s*(아웃트로|마무리)")]

rows, prop = [], {k: [] for k, _ in SEC}
for p in sorted(glob.glob(os.path.join(POOL, "차명_*.txt"))):
    t = io.open(p, encoding="utf-8").read()
    lines = t.split("\n")
    idx = {}
    for name, pat in SEC:
        hits = [i for i, ln in enumerate(lines) if re.match(pat, ln)]
        if hits:
            idx[name] = hits[-1]                      # 목차가 아니라 본문 쪽(뒤에 나오는 것)
    if len(idx) < 5:
        continue
    order = sorted(idx.items(), key=lambda x: x[1])
    lens = {}
    for k, (name, i) in enumerate(order):
        j = order[k + 1][1] if k + 1 < len(order) else len(lines)
        lens[name] = len("\n".join(lines[i:j]))
    tot = sum(lens.values()) or 1
    rows.append((os.path.basename(p)[3:28], tot, lens))
    for name in lens:
        prop[name].append(lens[name] / tot * 100)

print(f"6단 틀을 쓰는 차명 대본 {len(rows)}편")
print(f"{'회차':26} {'본문자수':>7} " + " ".join(f"{k:>7}" for k, _ in SEC))
for name, tot, lens in rows:
    print(f"{name:26} {tot:>7} " + " ".join(f"{lens.get(k, 0):>7}" for k, _ in SEC))

print(f"\n구간 비율 (%) — {len(rows)}편 중앙값")
budget = 5000
print(f"{'구간':10} {'중앙 %':>7} {'최소':>6} {'최대':>6} {'5,000자 배분':>12}")
for k, _ in SEC:
    v = prop[k]
    if not v:
        continue
    m = st.median(v)
    print(f"{k:10} {m:>7.1f} {min(v):>6.1f} {max(v):>6.1f} {round(budget * m / 100, -1):>10,.0f}자")
