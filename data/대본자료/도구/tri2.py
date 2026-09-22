# -*- coding: utf-8 -*-
"""매체를 맞춘 대조 — 우리 채널 '실제 발화 자막' vs 메이저 '실제 발화 자막'.

대본(글)과 자막(말)을 견주면 문장 길이·종결어미 차이가 매체 탓인지 문체 탓인지 갈리지 않는다.
그래서 우리 쪽도 사람이 읽은 결과(납품 자막·원본 영상 자동자막)로 잰다.
"""
import glob
import io
import json
import os
import re
import statistics as st
from collections import Counter
from paths import CORP, YT  # noqa: E402

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
    return {"chars": len(t), "sent_len": round(st.mean([len(x) for x in s]), 1) if s else 0,
            "num_k": round(len(NUM.findall(t)) / k, 2),
            "hype_k": round(sum(t.count(w) for w in HYPE) / k, 2),
            "rigor_k": round(sum(t.count(w) for w in RIGOR) / k, 2),
            "ends": ends, "words": set(re.findall(r"[가-힣]{2,}", t))}


HERE = os.path.dirname(os.path.abspath(__file__))
ours = {}
for p in (glob.glob(r"C:\Users\user\Desktop\이정찬\더원트레이더\0910\L08_*\*전체.srt")
          + glob.glob(r"C:\Users\user\Desktop\이정찬\더원트레이더\더원트레이더_JG\숏폼_프로젝트모음\**\*.srt",
                      recursive=True)
          + glob.glob(os.path.join(YT, "orig_*.srt"))):
    t = srt_text(p)
    if len(t) > 1200:
        ours[os.path.basename(p)[:30]] = t

major = {}
for v in json.load(io.open(os.path.join(CORP, "index.json"), encoding="utf-8")):
    p = os.path.join(CORP, v["file"]) if v.get("file") else None
    if p and os.path.exists(p):
        t = srt_text(p)
        if len(t) > 1500:
            major[v["id"]] = t

A2 = {k: measure(v) for k, v in ours.items()}
B = {k: measure(v) for k, v in major.items()}


def band(d, k, w=1):
    v = sorted(x[k] for x in d.values())
    return "·".join(f"{x:.{w}f}" for x in (v[len(v) // 4], v[len(v) // 2], v[len(v) * 3 // 4]))


print(f"{'':22} {'편수':>4} {'문장길이':>16} {'수치/천자':>14} {'과장/천자':>14} {'근거/천자':>14}")
for name, d in (("A2 우리 실제 발화", A2), ("B 메이저 발화", B)):
    print(f"{name:22} {len(d):>4} {band(d, 'sent_len'):>16} {band(d, 'num_k'):>14} "
          f"{band(d, 'hype_k', 2):>14} {band(d, 'rigor_k', 2):>14}")

print()
for name, d in (("A2 우리", A2), ("B 메이저", B)):
    e = Counter()
    for m in d.values():
        e.update(m["ends"])
    tot = sum(e.values()) or 1
    print(f"{name:10}", " · ".join(f"{w} {n / tot * 100:.0f}%" for w, n in e.most_common(7)))

da, db = Counter(), Counter()
for m in A2.values():
    da.update(m["words"])
for m in B.values():
    db.update(m["words"])
ca = {w for w, n in da.items() if n >= len(A2) * 0.5}
cb = {w for w, n in db.items() if n >= len(B) * 0.5}
print(f"\n절반 이상이 쓰는 말 — 교집합 {len(ca & cb)} · 우리만 {len(ca - cb)} · 메이저만 {len(cb - ca)}")
print("  우리만  :", " ".join(sorted(ca - cb, key=lambda w: -da[w])[:25]))
print("  메이저만:", " ".join(sorted(cb - ca, key=lambda w: -db[w])[:25]))
