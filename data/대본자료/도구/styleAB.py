# -*- coding: utf-8 -*-
"""① 회사가 만든 A(전문가 형) ↔ B(인플루 형) 같은 주제 대조 — '전문가스러움'의 실측 정의
   ② 채널 규모 ↔ 과장 표현 빈도 상관 — '메이저일수록 덜 쓴다'가 사실인가
"""
import glob
import io
import json
import os
import re
import statistics as st
from collections import Counter
from paths import CORP, POOL  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SENT = re.compile(r"(?<=[다요까죠])[.!?\s]\s*|(?<=[.!?])\s+")
HYPE = ["무조건", "보장", "100%", "떼돈", "대박", "인생역전", "하루 10만", "억대", "돈 복사",
        "비법", "필승", "승률 9", "마법", "치트키", "꿀팁", "찍었", "녹아", "망하는"]
RIGOR = ["손절", "리스크", "확률", "기준", "조건", "예외", "다만", "주의", "검증", "원칙", "관리",
         "비중", "손익비", "실패", "아닙니다", "않습니다"]
YOU_CASUAL = ["너", "네가", "너만", "-야", "거야", "했어", "먹히네", "하자", "봐", "~잖아"]
YOU_POLITE = ["여러분", "시청자", "분들", "하시면", "보세요", "드리겠습니다", "습니다"]
END = re.compile(r"(습니다|입니다|합니다|됩니다|세요|겠죠|거든요|잖아요|드립니다|어요|해요|죠|까요|야|어|지)$")


def stat(t):
    s = [x.strip() for x in SENT.split(t) if len(x.strip()) >= 4]
    k = max(1, len(t)) / 1000
    e = Counter()
    for x in s:
        m = END.search(x.rstrip(".!?…\"'"))
        if m:
            e[m.group(1)] += 1
    return {"chars": len(t), "sent_len": round(st.mean([len(x) for x in s]), 1) if s else 0,
            "hype_k": round(sum(t.count(w) for w in HYPE) / k, 2),
            "rigor_k": round(sum(t.count(w) for w in RIGOR) / k, 2),
            "casual_k": round(sum(t.count(w) for w in YOU_CASUAL) / k, 2),
            "polite_k": round(sum(t.count(w) for w in YOU_POLITE) / k, 2),
            "num_k": round(len(re.findall(r"\d+", t)) / k, 2), "ends": e}


rows = json.load(io.open(os.path.join(POOL, "index.json"), encoding="utf-8"))
print("① 같은 주제(쿠리마기) 세 벌 — 회사가 만든 것")
print(f"{'':16} {'글자':>6} {'문장길이':>7} {'과장/천자':>8} {'근거/천자':>8} {'반말투/천자':>9} {'존대/천자':>8} {'수치/천자':>8}")
for tag in ("스타일0", "스타일A", "스타일B"):
    r = next((x for x in rows if tag in x["name"]), None)
    if not r:
        continue
    m = stat(io.open(os.path.join(POOL, r["file"]), encoding="utf-8").read())
    print(f"{tag:16} {m['chars']:>6} {m['sent_len']:>7.1f} {m['hype_k']:>8.2f} {m['rigor_k']:>8.2f} "
          f"{m['casual_k']:>9.2f} {m['polite_k']:>8.2f} {m['num_k']:>8.2f}")
    print(f"{'':16} 종결: " + " · ".join(f"{w} {n}" for w, n in m["ends"].most_common(5)))

print("\n② 채널 규모 ↔ 과장 표현 (메이저 45편)")
idx = json.load(io.open(os.path.join(CORP, "index.json"), encoding="utf-8"))


def srt_text(p):
    t = io.open(p, encoding="utf-8-sig", errors="replace").read()
    t = re.sub(r"^\d+\s*$|^\d\d:\d\d:\d\d[,.]\d+ -->.*$|^WEBVTT.*$|^Kind:.*$|^Language:.*$", "", t, flags=re.M)
    out, seen = [], None
    for ln in (x.strip() for x in t.split("\n")):
        if ln and ln != seen:
            out.append(ln)
            seen = ln
    return " ".join(out)


by = {}
for v in idx:
    p = os.path.join(CORP, v["file"]) if v.get("file") else None
    if not p or not os.path.exists(p):
        continue
    t = srt_text(p)
    if len(t) < 1500:
        continue
    by.setdefault((v["channel"], v["subs"]), []).append(stat(t))
print(f"{'채널':24} {'구독자':>9} {'편':>3} {'과장/천자':>9} {'근거/천자':>9} {'문장길이':>7}")
pts = []
for (ch, subs), ms in sorted(by.items(), key=lambda x: -x[0][1]):
    h = st.mean([m["hype_k"] for m in ms])
    r = st.mean([m["rigor_k"] for m in ms])
    pts.append((subs, h))
    print(f"{ch[:24]:24} {subs:>9,} {len(ms):>3} {h:>9.2f} {r:>9.2f} "
          f"{st.mean([m['sent_len'] for m in ms]):>7.1f}")
if len(pts) > 2:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in pts)
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** .5
    print(f"\n구독자 ↔ 과장 빈도 상관계수 r = {num / den:+.2f}  (채널 {len(pts)}개)")
