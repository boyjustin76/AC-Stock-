# -*- coding: utf-8 -*-
"""구간 머리글이 실제로 박힌 대본(더원 롱폼 촬영본)으로 구간별 분량을 잰다.

차명(Old) 대본의 6단 틀은 기획서 목차에만 있고 본문에는 표시가 없어 비율을 못 잰다.
여기서는 INTRO / 1. / 2. … / OUTRO 가 본문에 박힌 촬영용 대본만 쓴다.
낭독분만 센다 — [읽지 않음] 지시문과 사전 질문지는 뺀다.
"""
import glob
import io
import os
import re
import statistics as st
from paths import DOCS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HEAD = re.compile(r"^(INTRO|Intro|OUTRO|Outro)\b\.?\s*(.*)$|^(\d{1,2})\.\s+(.+)$")
NOTE = re.compile(r"^\[[^\]]*읽지\s*않음|^\[[^\]]*·\s*읽지|^\[촬영 전 확인")

rows = []
for p in sorted(glob.glob(os.path.join(DOCS, "L0*.txt")) + glob.glob(os.path.join(DOCS, "X_*.txt"))):
    name = os.path.basename(p)[:-4]
    if "질문지" in name or "기획서" in name:
        continue
    lines = [x.strip() for x in io.open(p, encoding="utf-8").read().split("\n") if x.strip()]
    heads = [i for i, ln in enumerate(lines) if HEAD.match(ln)]
    if len(heads) < 4:
        continue
    secs = []
    for k, i in enumerate(heads):
        j = heads[k + 1] if k + 1 < len(heads) else len(lines)
        body = [ln for ln in lines[i + 1:j] if not NOTE.match(ln)]
        secs.append((lines[i][:26], sum(len(x) for x in body)))
    tot = sum(n for _, n in secs) or 1
    rows.append((name[:26], tot, secs))

print("구간 머리글이 박힌 촬영용 대본")
for name, tot, secs in rows:
    body = [n for _, n in secs[1:-1]]
    print(f"\n{name}  낭독 {tot:,}자 · 구간 {len(secs)}개")
    print(f"   INTRO {secs[0][1]:>5}자 ({secs[0][1] / tot * 100:4.1f}%) · "
          f"본문 {len(body)}구간 {sum(body):>5}자 (구간당 중앙 {st.median(body):.0f}자) · "
          f"OUTRO {secs[-1][1]:>5}자 ({secs[-1][1] / tot * 100:4.1f}%)")
    for t, n in secs:
        print(f"      {n:>5}자  {t}")

fin = [r for r in rows if "최종" in r[0]]
if fin:
    print("\n── 최종본만 모아 본 기준")
    intro = [s[0][1] / t * 100 for _, t, s in fin]
    outro = [s[-1][1] / t * 100 for _, t, s in fin]
    mids = [n for _, _, s in fin for _, n in s[1:-1]]
    nsec = [len(s) - 2 for _, _, s in fin]
    print(f"   INTRO 중앙 {st.median(intro):.1f}% · OUTRO 중앙 {st.median(outro):.1f}% · "
          f"본문 구간 수 중앙 {st.median(nsec):.0f}개 · 본문 구간당 중앙 {st.median(mids):.0f}자")
    b = 5000
    print(f"   → 5,000자 배분: INTRO {b * st.median(intro) / 100:,.0f}자 · "
          f"OUTRO {b * st.median(outro) / 100:,.0f}자 · "
          f"본문 {b - b * (st.median(intro) + st.median(outro)) / 100:,.0f}자를 "
          f"{st.median(nsec):.0f}구간으로")
