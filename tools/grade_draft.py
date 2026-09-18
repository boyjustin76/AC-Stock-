# -*- coding: utf-8 -*-
"""대본 초안을 규격에 대고 채점한다 — 낭독분만 센다(지시문·제목·주석 제외).

    python grade_draft.py <초안.md>
"""
import io
import re
import statistics as st
import sys
from collections import Counter

BAN = ["무조건", "보장", "100%", "떼돈", "대박", "인생역전", "하루 10만", "월 300", "억대",
       "돈 복사", "수익 인증", "비법", "필승", "승률 9", "마법", "치트키", "꿀팁"]
RIGOR = ["손절", "리스크", "확률", "기준", "조건", "예외", "다만", "주의", "검증", "원칙",
         "관리", "비중", "손익비", "실패", "아닙니다", "않습니다"]
CASUAL = re.compile(r"(거야|했어|하자|야\.|잖아|네가|너는)")
SENT = re.compile(r"(?<=[다요까죠])[.!?]\s*")

path = sys.argv[1]
raw = io.open(path, encoding="utf-8").read()
# 낭독분만: 머리말(---로 시작하는 앞머리) 제거 · 제목/인용/지시문/사전질문지 제거
raw = raw.split("## INTRO", 1)[-1]
lines = []
for ln in raw.split("\n"):
    s = ln.strip()
    if not s or s.startswith(("#", ">", "**[", "---", "|", "1)", "2)", "3)", "4)")):
        continue
    lines.append(s)
body = " ".join(lines)
sents = [x.strip() for x in SENT.split(body) if len(x.strip()) >= 4]
k = len(body) / 1000

# 구간별
secs = re.split(r"\n##\s+", raw)
print(f"{'구간':34} {'글자':>6} {'문장':>4} {'평균':>5}")
for sec in secs:
    t = sec.split("\n", 1)
    head = t[0].strip()[:32]
    txt = " ".join(x.strip() for x in (t[1] if len(t) > 1 else "").split("\n")
                   if x.strip() and not x.strip().startswith(("**[", ">", "-", "|", "#")))
    ss = [x for x in SENT.split(txt) if len(x.strip()) >= 4]
    if txt:
        print(f"{head:34} {len(txt):>6} {len(ss):>4} {st.mean([len(x) for x in ss]):>5.1f}")

print(f"\n낭독 합계 {len(body):,}자 · 문장 {len(sents)}개 · 평균 {st.mean([len(x) for x in sents]):.1f}자")
print("목표      5,000자 ±300 · 문장 평균 39자 ±4")
# 금지어는 부정문 안에서는 세지 않는다 — '반등을 보장하는 장치가 아닙니다' 는 오히려 반대 뜻이다
NEG = ("아닙니다", "않습니다", "없습니다", "아니라", "않는", "못합니다", "아니고")
# 다른 낱말 안에 들어가 있으면 세지 않는다 — '횡보장'의 '보장', '대박'이 든 지명 등
INSIDE = {"보장": ("횡",), "대박": (), "마법": (), "비법": ()}
hits, excused = Counter(), Counter()
for w in BAN:
    for m in re.finditer(re.escape(w), body):
        if any(body[max(0, m.start() - len(p)):m.start()] == p for p in INSIDE.get(w, ())):
            continue
        tail = body[m.end():m.end() + 30]
        (excused if any(n in tail for n in NEG) else hits)[w] += 1
print(f"금지어    {'없음' if not hits else dict(hits)}"
      + (f"  (부정문이라 뺀 것: {dict(excused)})" if excused else ""))
print(f"근거 표현  {sum(body.count(w) for w in RIGOR)}회 ({sum(body.count(w) for w in RIGOR) / k:.1f}/천자) · 목표 27회(5.4)")
nums = re.findall(r"\d+", body)
print(f"수치      {len(nums)}개 ({len(nums) / k:.1f}/천자) · 목표 55개(10.9)")
print(f"반말투    {len(CASUAL.findall(body))}건 · 목표 0")
long_s = [x for x in sents if len(x) > 60]
print(f"60자 넘는 문장 {len(long_s)}개" + (f" — 예: {long_s[0][:60]}…" if long_s else ""))
