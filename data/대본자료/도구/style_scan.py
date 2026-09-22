# -*- coding: utf-8 -*-
"""메이저 채널 자막 코퍼스에서 '전문가스러움'의 여집합을 실측한다.

재는 것
  ① 수익 보장·과장 표현 빈도 (천자당) — 규모별로 다른가
  ② 근거·조건 표현 빈도 (손절·조건·확률·리스크) — 전문가 쪽 표지
  ③ 문장 길이·초당 글자수 (말 속도)
  ④ 종결어미 분포 (구어체 결)
우리 대본(더원 롱폼)과 나란히 놓고 본다.

    python style_scan.py
"""
import glob
import io
import json
import os
import re
import statistics as st
from collections import Counter
from paths import CORP, DOCS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HYPE = ["무조건", "보장", "100%", "확실히 돈", "떼돈", "대박", "인생역전", "하루 10만", "하루 30만",
        "하루 50만", "월 1000", "월 300", "억대", "쉽게 돈", "돈 복사", "수익 인증", "절대 안 잃",
        "비밀 매매법", "비법", "필승", "승률 90", "승률 95", "승률 100"]
RIGOR = ["손절", "리스크", "확률", "기준", "조건", "예외", "다만", "주의", "검증", "백테스트",
         "원칙", "관리", "비중", "손익비", "실패", "틀렸을"]
SENT = re.compile(r"(?<=[다요까죠])[.!?\s]\s*|(?<=[.!?])\s+")


def stats(txt, sec=None):
    s = [x.strip() for x in SENT.split(txt) if len(x.strip()) >= 4]
    k = max(1, len(txt)) / 1000
    ends = Counter()
    for x in s:
        m = re.search(r"(습니다|입니다|합니다|됩니다|세요|겠죠|거든요|잖아요|드립니다|니까요|라고요|어요|해요)$",
                      x.rstrip(".!?"))
        if m:
            ends[m.group(1)] += 1
    return {"chars": len(txt), "sents": len(s),
            "sent_len": round(st.mean([len(x) for x in s]), 1) if s else 0,
            "hype_k": round(sum(txt.count(w) for w in HYPE) / k, 2),
            "rigor_k": round(sum(txt.count(w) for w in RIGOR) / k, 2),
            "cps": round(len(txt) / sec, 2) if sec else None,
            "ends": ends}


def srt_text(p):
    t = io.open(p, encoding="utf-8-sig", errors="replace").read()
    t = re.sub(r"^\d+\s*$|^\d\d:\d\d:\d\d[,.]\d+ -->.*$|^WEBVTT.*$|^Kind:.*$|^Language:.*$", "", t, flags=re.M)
    out, seen = [], None
    for ln in (x.strip() for x in t.split("\n")):
        if ln and ln != seen:
            out.append(ln)
            seen = ln
    return " ".join(out)


idx = json.load(io.open(os.path.join(CORP, "index.json"), encoding="utf-8"))
rows = []
for v in idx:
    if not v.get("file"):
        continue
    p = os.path.join(CORP, v["file"])
    if not os.path.exists(p):
        continue
    txt = srt_text(p)
    if len(txt) < 800:
        continue
    rows.append({**v, **stats(txt, v["sec"]), "txt": txt})

print(f"{'채널':24} {'구독':>8} {'편':>3} {'글자':>7} {'문장길이':>6} {'과장/천자':>8} {'근거/천자':>8} {'자/초':>6}")
by = {}
for r in rows:
    by.setdefault(r["channel"], []).append(r)
for ch, vs in sorted(by.items(), key=lambda x: -x[1][0]["subs"]):
    m = lambda k: round(st.mean([v[k] for v in vs]), 2)  # noqa: E731
    print(f"{ch[:24]:24} {vs[0]['subs']:>8,} {len(vs):>3} {m('chars'):>7.0f} {m('sent_len'):>6.1f} "
          f"{m('hype_k'):>8.2f} {m('rigor_k'):>8.2f} {m('cps'):>6.2f}")

# 우리 대본
print()
for p in sorted(glob.glob(os.path.join(DOCS, "*.txt"))):
    n = os.path.basename(p)[:-4]
    if "질문지" in n or "기획서" in n:
        continue
    t = io.open(p, encoding="utf-8").read()
    s = stats(t)
    print(f"{'[우리] ' + n[:17]:24} {'':>8} {1:>3} {s['chars']:>7} {s['sent_len']:>6.1f} "
          f"{s['hype_k']:>8.2f} {s['rigor_k']:>8.2f} {'':>6}")

allhype = Counter()
for r in rows:
    for w in HYPE:
        allhype[w] += r["txt"].count(w)
print("\n실제로 나온 과장 표현:", ", ".join(f"{w}×{n}" for w, n in allhype.most_common() if n))
ends = Counter()
for r in rows:
    ends.update(r["ends"])
print("메이저 종결어미 상위:", ", ".join(f"{w} {n}" for w, n in ends.most_common(8)))
io.open(os.path.join(CORP, "style.json"), "w", encoding="utf-8").write(
    json.dumps([{k: v for k, v in r.items() if k not in ("txt", "ends")} for r in rows], ensure_ascii=False, indent=1))
