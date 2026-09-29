# -*- coding: utf-8 -*-
"""문장대조.json 을 손봐서 대본을 다시 짠다 (모델을 다시 부르지 않는다).
 · 원문이 물음표인데 마침표로 끝난 것을 되돌린다
 · 바뀐 문장과 덧붙인 문장을 표시한 대조표도 함께 낸다"""
import io, os, re, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen13

HERE = os.path.dirname(os.path.abspath(__file__))
대조 = json.load(io.open(os.path.join(HERE, "차13_문장대조.json"), encoding="utf-8"))


def 물음표(원, 새):
    if 원.rstrip().endswith("?") and 새.rstrip().endswith("."):
        몸 = 새.rstrip().rstrip(".")
        if re.search(r"(까요|나요|가요|을까|ㄹ까|습니까|인가요|신가요)$", 몸): return 몸 + "?"
    return 새


블록 = gen13.문서읽기()
대상 = [(bi, si) for bi, b in enumerate(블록) if b[0] == "para" for si, c in enumerate(b[1]) if c[0] == "text"]
새 = {}
for i, x in enumerate(대조):
    if x["새"]: 새[i] = 물음표(x["원"], x["새"])

out = []
for bi, b in enumerate(블록):
    if b[0] != "para": out.append(b[1]); continue
    문장 = []
    for si, c in enumerate(b[1]):
        if c[0] == "skip": 문장.append(c[1]); continue
        문장.append(c[1] + 새.get(대상.index((bi, si)), c[2]) + c[3])
    out.append(" ".join(문장))
io.open(os.path.join(HERE, "차13_김직선말투.md"), "w", encoding="utf-8").write("\n".join(out))

쪼갬 = lambda t: [x for x in re.split(r"(?<=[.?!])\s+", t.strip()) if x]
표 = ["# 차13 문장 대조 — Pool 정보 + 김직선 말투 (2026-09-23)", "",
      "`〃` = 원문 그대로 둠 · **굵게** = 원문에 없던 문장을 덧붙인 자리", "",
      "| # | 원문 (Pool 조각) | 김직선 말투 |", "|---|---|---|"]
for i, x in enumerate(대조):
    b = 새.get(i, "")
    if not b: 표.append("| %d | %s | 〃 |" % (i + 1, x["원"]))
    else:
        덧 = 쪼갬(b)[len(쪼갬(x["원"])):]
        보임 = b
        for d in 덧: 보임 = 보임.replace(d, "**" + d + "**")
        표.append("| %d | %s | %s |" % (i + 1, x["원"], 보임))
io.open(os.path.join(HERE, "차13_문장대조.md"), "w", encoding="utf-8").write("\n".join(표))
print("대본 %d자 · 바뀐 문장 %d / %d · 덧붙인 자리 %d" %
      (sum(len(l) for l in out), len(새), len(대조),
       sum(1 for i, x in enumerate(대조) if 새.get(i) and len(쪼갬(새[i])) > len(쪼갬(x["원"])))))
