# -*- coding: utf-8 -*-
"""세 코퍼스를 같은 자로 재서 교집합을 찾는다.

  A 회사 Pool   차트명가(Old) 대본 16편 + 더원트레이더 롱폼 대본 9편   ← 저장소·드라이브
  B 메이저 타채널 12채널 45편 자막                                  ← yt-dlp 로 수집
  C 전문가       (아직 없음 — 자리만 비워 둔다)

재는 것: 길이·문장·수치밀도 / 과장·근거 표현 / 종결어미 / 낱말 DF(어디에나 나오는 말 = 교집합 후보)

    python tri.py
"""
import glob
import io
import json
import os
import re
import statistics as st
from collections import Counter
from paths import BASE, CORP, DOCS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SENT = re.compile(r"(?<=[다요까죠])[.!?\s]\s*|(?<=[.!?])\s+")
NUM = re.compile(r"\d+")
HYPE = ["무조건", "보장", "100%", "떼돈", "대박", "인생역전", "하루 10만", "하루 30만", "하루 50만",
        "월 300", "월 1000", "억대", "돈 복사", "수익 인증", "절대 안 잃", "비밀 매매법", "비법",
        "필승", "승률 9", "마법", "치트키", "꿀팁"]
RIGOR = ["손절", "리스크", "확률", "기준", "조건", "예외", "다만", "주의", "검증", "원칙",
         "관리", "비중", "손익비", "실패", "틀렸을", "보장되지", "아닙니다"]
END = re.compile(r"(습니다|입니다|합니다|됩니다|세요|겠죠|거든요|잖아요|드립니다|니까요|어요|해요|죠|까요)$")


def srt_text(p):
    t = io.open(p, encoding="utf-8-sig", errors="replace").read()
    t = re.sub(r"^\d+\s*$|^\d\d:\d\d:\d\d[,.]\d+ -->.*$|^WEBVTT.*$|^Kind:.*$|^Language:.*$", "", t, flags=re.M)
    out, seen = [], None
    for ln in (x.strip() for x in t.split("\n")):
        if ln and ln != seen:
            out.append(ln)
            seen = ln
    return " ".join(out)


def measure(t):
    s = [x.strip() for x in SENT.split(t) if len(x.strip()) >= 4]
    k = max(1, len(t)) / 1000
    ends = Counter()
    for x in s:
        m = END.search(x.rstrip(".!?…"))
        if m:
            ends[m.group(1)] += 1
    return {"chars": len(t), "sents": len(s),
            "sent_len": round(st.mean([len(x) for x in s]), 1) if s else 0,
            "num_k": round(len(NUM.findall(t)) / k, 2),
            "hype_k": round(sum(t.count(w) for w in HYPE) / k, 2),
            "rigor_k": round(sum(t.count(w) for w in RIGOR) / k, 2),
            "ends": ends, "words": set(re.findall(r"[가-힣]{2,}", t))}


# ── A 회사 Pool
pool = {}
REPO = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\01_저장소\E_Script"
for x in json.load(io.open(os.path.join(REPO, "log", "data", "scripts.json"), encoding="utf-8"))["docs"]:
    if len(x.get("text") or "") > 800:
        pool["차] " + x["ep"][:24]] = x["text"]
for p in sorted(glob.glob(os.path.join(DOCS, "L0*.txt")) + glob.glob(os.path.join(DOCS, "X_*.txt"))):
    n = os.path.basename(p)[:-4]
    if "질문지" in n or "기획서" in n:
        continue
    pool["원] " + n[:24]] = io.open(p, encoding="utf-8").read()

# ── B 메이저
major = {}
for v in json.load(io.open(os.path.join(CORP, "index.json"), encoding="utf-8")):
    if not v.get("file"):
        continue
    p = os.path.join(CORP, v["file"])
    if os.path.exists(p):
        t = srt_text(p)
        if len(t) > 1500:
            major[f"{v['channel'][:12]}/{v['id']}"] = t

A = {k: measure(v) for k, v in pool.items()}
B = {k: measure(v) for k, v in major.items()}


def band(d, key):
    v = sorted(x[key] for x in d.values())
    return v[len(v) // 4], v[len(v) // 2], v[len(v) * 3 // 4]


print(f"{'':16} {'편수':>4} {'글자(P25·중앙·P75)':>26} {'문장길이':>14} {'수치/천자':>14} "
      f"{'과장/천자':>14} {'근거/천자':>14}")
for name, d in (("A 회사 Pool", A), ("B 메이저", B)):
    f = lambda k, w=0: "·".join(f"{x:,.{w}f}" for x in band(d, k))  # noqa: E731
    print(f"{name:16} {len(d):>4} {f('chars'):>26} {f('sent_len',1):>14} {f('num_k',1):>14} "
          f"{f('hype_k',2):>14} {f('rigor_k',2):>14}")

# ── 교집합 낱말: 두 코퍼스 모두에서 문서 절반 이상이 쓰는 말
def df(d):
    c = Counter()
    for m in d.values():
        c.update(m["words"])
    return c


da, db = df(A), df(B)
ca, cb = {w for w, n in da.items() if n >= len(A) * 0.5}, {w for w, n in db.items() if n >= len(B) * 0.5}
both = sorted(ca & cb, key=lambda w: -(da[w] + db[w]))
only_a = sorted(ca - cb, key=lambda w: -da[w])
only_b = sorted(cb - ca, key=lambda w: -db[w])
print(f"\n두 코퍼스 절반 이상이 쓰는 말 — 교집합 {len(both)}개 · 우리만 {len(only_a)}개 · 메이저만 {len(only_b)}개")
print("  교집합 :", " ".join(both[:40]))
print("  우리만 :", " ".join(only_a[:30]))
print("  메이저만:", " ".join(only_b[:30]))

ea, eb = Counter(), Counter()
for m in A.values():
    ea.update(m["ends"])
for m in B.values():
    eb.update(m["ends"])
tot_a, tot_b = sum(ea.values()) or 1, sum(eb.values()) or 1
print("\n종결어미 비율 (우리 / 메이저)")
for w in sorted(set(ea) | set(eb), key=lambda w: -(ea[w] + eb[w]))[:8]:
    print(f"   {w:<6} {ea[w] / tot_a * 100:5.1f}%  /  {eb[w] / tot_b * 100:5.1f}%")

hy = Counter()
for t in major.values():
    for w in HYPE:
        hy[w] += t.count(w)
for t in pool.values():
    for w in HYPE:
        hy[w] -= 0
print("\n메이저에서 실제로 나온 과장 표현:", ", ".join(f"{w}×{n}" for w, n in hy.most_common(12) if n))
json.dump({"A": {k: {x: y for x, y in v.items() if x not in ("words", "ends")} for k, v in A.items()},
           "B": {k: {x: y for x, y in v.items() if x not in ("words", "ends")} for k, v in B.items()},
           "both": both[:200], "only_a": only_a[:100], "only_b": only_b[:100]},
          io.open(os.path.join(BASE, "tri.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
