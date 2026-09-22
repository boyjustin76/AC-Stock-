# -*- coding: utf-8 -*-
"""더원 롱폼 촬영 대본 11편을 같은 자로 재 본다 (읽기 전용 · 학습용).

재는 것: 구간 수 · 낭독분/지시문 글자 · 문장 길이 · 수치 밀도 ·
매매 규칙 낱말(진입·손절·익절·손익비·조건) 밀도 · 금지/예외 표현.
"""
import glob
import io
import os
import re

from paths import DOCS as D  # 05_대본자료/레퍼런스
HEAD = re.compile(r"^(INTRO|Intro|OUTRO|Outro)\b|^\d{1,2}\.\s+\S")
NOTE = re.compile(r"^\[[^\]]*읽지\s*않음[^\]]*\]|^\[[^\]]*·\s*읽지")
NUM = re.compile(r"\d+(?:[.,]\d+)?")
RULE = ("진입", "손절", "익절", "목표", "손익비", "청산", "기준", "확인", "조건")
RISK = ("아닙니다", "않습니다", "말고", "피해", "주의", "위험", "보장", "예외", "실패")
SENT = re.compile(r"(?<=[다요까죠])[.!?]\s*|(?<=[.!?])\s+")

print(f"{'회차':38} {'상태':6} {'구간':>3} {'낭독자':>6} {'지시문':>6} {'문장':>4} "
      f"{'문장길이':>6} {'수치/천자':>7} {'규칙어/천자':>9} {'단서어/천자':>9}")
for p in sorted(glob.glob(os.path.join(D, "*.txt"))):
    name = os.path.basename(p)[:-4]
    if "질문지" in name or "기획서" in name:
        continue                                   # 대본 장르가 아니다
    lines = [x for x in io.open(p, encoding="utf-8").read().split("\n") if x.strip()]
    heads = [x for x in lines if HEAD.match(x)]
    notes = [x for x in lines if NOTE.match(x)]
    body = [x for x in lines if not HEAD.match(x) and not NOTE.match(x)]
    # 사전 질문지 구역(첫 머리글 앞)은 낭독분이 아니다
    if heads:
        i = lines.index(heads[0])
        body = [x for x in lines[i:] if not HEAD.match(x) and not NOTE.match(x)]
    read = " ".join(body)
    note = " ".join(notes)
    sents = [s for s in SENT.split(read) if len(s.strip()) >= 4]
    k = max(1, len(read)) / 1000
    state = "최종" if "최종" in name else ("2차초안" if "2차초안" in name else "초안")
    print(f"{name[:38]:38} {state:6} {len(heads):3d} {len(read):6d} {len(note):6d} {len(sents):4d} "
          f"{sum(len(s) for s in sents) / max(1, len(sents)):6.1f} "
          f"{len(NUM.findall(read)) / k:7.2f} "
          f"{sum(read.count(w) for w in RULE) / k:9.2f} "
          f"{sum(read.count(w) for w in RISK) / k:9.2f}")
