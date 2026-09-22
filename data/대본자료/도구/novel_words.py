# -*- coding: utf-8 -*-
"""초안에서 **회사 Pool 이 한 번도 쓴 적 없는 낱말**을 찾는다.

    python novel_words.py <초안.md> [...]

낱말은 어절이 아니라 **형태소**로 본다 — 어절로 재면 `추세를`/`추세가` 가 다른 낱말이 되어
없는 말이 잔뜩 잡힌다. 명사·동사·형용사·부사·어근·외국어만 보고 조사·어미는 보지 않는다.

**품사표는 보지 않고 낱말 꼴만 맞춘다.** 같은 `선`을 여기서는 NNG, 저기서는 NNP 로 달아 주는
일이 잦아서, 품사까지 맞추면 Pool 에 멀쩡히 있는 말이 '없는 말'로 잡힌다(2026-09-21 실측 3건).
끝으로 글자 그대로도 Pool 을 뒤져서, 형태소 분석이 갈라놓은 말(`적중`+`률`)을 걸러낸다.
"""
import glob
import io
import os
import re
import sys
from collections import Counter

from kiwipiepy import Kiwi

from paths import POOL

# kiwi 는 동사에 VV-R / VV-I 처럼 갈래를 붙여 준다. 정확히 "VV" 만 보면
# 동사가 통째로 비교에서 빠진다 (2026-09-21 실측 — Pool 에 80번 있는 `잡` 이 없는 말로 잡혔다).
TAGS = ("NNG", "NNP", "VV", "VA", "MAG", "XR", "SL")
SENT = re.compile(r"(?<=[다요까죠])[.!?]\s*")
kiwi = Kiwi()


def toks(text):
    return [(t.form, t.tag) for t in kiwi.tokenize(text) if t.tag.startswith(TAGS)]


def read_draft(path):
    """낭독분만 — 머리말·표·인용·지시문은 뺀다."""
    raw = io.open(path, encoding="utf-8").read()
    raw = raw.split("## INTRO", 1)[-1]
    out = []
    for ln in raw.split("\n"):
        s = ln.strip()
        if not s or s.startswith(("#", ">", "**[", "---", "|", "- ", "1)", "2)", "3)", "4)")):
            continue
        out.append(s)
    return " ".join(out)


print("Pool 을 형태소로 읽는 중…")
forms, raw_pool = Counter(), []
files = sorted(glob.glob(os.path.join(POOL, "*.txt")))
for p in files:
    t = io.open(p, encoding="utf-8").read()
    raw_pool.append(t)
    forms.update(f for f, _ in toks(t))
blob = "\n".join(raw_pool)
print("  %d편 · 서로 다른 낱말 %d개\n" % (len(files), len(forms)))

for path in sys.argv[1:]:
    body = read_draft(path)
    tk = toks(body)
    novel = Counter(f for f, _ in tk if f not in forms)
    sents = [s.strip() for s in SENT.split(body) if s.strip()]
    rows = []
    for form, n in novel.most_common():
        lit = blob.count(form)                    # 글자 그대로는 Pool 에 있는가
        rows.append((form, n, lit, [s for s in sents if form in s]))
    real = [r for r in rows if r[2] == 0]
    print("=" * 78)
    print("%s — 낭독 %d자 · 낱말 %d개" % (os.path.basename(path), len(body), len(tk)))
    print("  Pool 에 **아예 없는 말** %d종 %d번 / 형태소만 갈린 것 %d종\n"
          % (len(real), sum(r[1] for r in real), len(rows) - len(real)))
    for form, n, lit, where in rows:
        mark = "없음" if lit == 0 else "글자로는 %d번 있음" % lit
        print("  %-8s ×%-3d [%s]" % (form, n, mark))
        for s in where[:2]:
            print("      %s" % s[:108])
