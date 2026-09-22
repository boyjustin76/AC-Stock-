# -*- coding: utf-8 -*-
"""촬영 대본(초안) ↔ 실제로 나간 영상(자막) 을 짝지어 재 본다.

무엇을 답하는가 — "우리가 쓴 것이 방송까지 가면서 어떻게 달라지는가".
짝짓기는 제목이 아니라 **본문 4글자 겹침**으로 한다 (제목은 바뀌기 때문이다).

    python aired.py

주의 — 자막은 유튜브 자동자막(ASR)이다. 사람이 올린 자막이 아니다.
숫자·지표 이름이 곧잘 깨지므로 **낱말 단위 비교는 믿지 않는다.** 분량·문장 길이·
밀도처럼 덩어리로 보는 값만 쓴다.
"""
import glob
import io
import os
import re

from paths import AIRED, POOL

NUM = re.compile(r"[0-9]+(?:[.,][0-9]+)?")
SENT = re.compile(r"(?<=[다요까죠])[.!?]\s*|(?<=[.!?])\s+")
HEAD = re.compile(r"^(INTRO|Intro|OUTRO|Outro)\b|^[0-9]{1,2}\.\s+\S")
NOTE = re.compile(r"^\[[^\]]*읽지\s*않음[^\]]*\]|^\[[^\]]*·\s*읽지")
DROP = re.compile(r"[^0-9가-힣a-zA-Z]")

BAN = ("무조건", "보장", "100%", "대박", "비법", "필승", "승률 9", "마법", "떼돈")
RULE = ("진입", "손절", "익절", "목표", "손익비", "청산", "기준", "확인", "조건")
RISK = ("아닙니다", "않습니다", "말고", "피해", "주의", "위험", "예외", "실패")


def sub_text(path):
    """.srt 에서 말만 뽑는다."""
    out = []
    for blk in io.open(path, encoding="utf-8").read().split("\n\n"):
        keep = [x for x in blk.splitlines()
                if x.strip() and not x.strip().isdigit() and "-->" not in x]
        out.append(" ".join(keep))
    t = re.sub(r"\s+", " ", " ".join(out)).strip()
    return re.sub(r"\[[^\]]*\]", " ", t)          # [음악] 같은 표시는 뺀다


def draft_text(path):
    """촬영 대본에서 낭독분만 뽑는다 (머리글·지시문 제외)."""
    lines = [x for x in io.open(path, encoding="utf-8").read().split("\n") if x.strip()]
    heads = [x for x in lines if HEAD.match(x)]
    if heads:
        lines = lines[lines.index(heads[0]):]
    return " ".join(x for x in lines if not HEAD.match(x) and not NOTE.match(x))


def grams(s, n=4):
    s = DROP.sub("", s)
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def measure(t):
    sents = [x for x in SENT.split(t) if len(x.strip()) >= 4]
    k = max(1, len(t)) / 1000
    return {
        "자": len(t),
        "문장": len(sents),
        "문장길이": sum(len(x) for x in sents) / max(1, len(sents)),
        "수치": len(NUM.findall(t)) / k,
        "규칙어": sum(t.count(w) for w in RULE) / k,
        "단서어": sum(t.count(w) for w in RISK) / k,
        "과장": sum(t.count(w) for w in BAN) / k,
    }


drafts = {os.path.basename(p)[3:-4]: draft_text(p)
          for p in sorted(glob.glob(os.path.join(POOL, "더원_*.txt")))}
subs = sorted(glob.glob(os.path.join(AIRED, "*", "*.srt")))
print("방송 %d편 ↔ 더원 촬영 대본 %d편\n" % (len(subs), len(drafts)))

pairs = []
for p in subs:
    t = sub_text(p)
    g = grams(t)
    hit = sorted(((len(g & grams(d)) / max(1, len(grams(d))), k)
                  for k, d in drafts.items()), reverse=True)
    if hit[0][0] >= 0.20:
        pairs.append((os.path.basename(p).split(".")[0], hit[0][1], t, drafts[hit[0][1]], hit[0][0]))
    else:
        print("  짝 없음: %s (가장 가까운 것도 %.1f%%)" % (os.path.basename(p), hit[0][0] * 100))

print("\n%-30s %7s %7s %7s %7s %7s %7s" % ("", "자", "문장길이", "수치/천", "규칙어/천", "단서어/천", "과장/천"))
gap = []
for vid, name, aired, draft, ov in pairs:
    a, d = measure(aired), measure(draft)
    print("\n%s  (겹침 %.0f%%)" % (name[:44], ov * 100))
    for lab, m in (("  초안", d), ("  방송", a)):
        print("%-30s %7d %7.1f %7.1f %7.1f %7.1f %7.2f"
              % (lab, m["자"], m["문장길이"], m["수치"], m["규칙어"], m["단서어"], m["과장"]))
    gap.append((d, a))

if gap:
    print("\n초안 → 방송 평균 변화")
    for key in ("자", "문장길이", "수치", "규칙어", "단서어", "과장"):
        d = sum(x[0][key] for x in gap) / len(gap)
        a = sum(x[1][key] for x in gap) / len(gap)
        sign = "+" if a >= d else ""
        print("  %-6s %8.1f → %8.1f  (%s%.1f%%)" % (key, d, a, sign, (a - d) / max(1e-9, d) * 100))
