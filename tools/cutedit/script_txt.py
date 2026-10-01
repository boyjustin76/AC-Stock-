# -*- coding: utf-8 -*-
"""대본.json (pdf_script.py 산출물) → align_take.py 가 읽는 대본.txt

    python3 tools/cutedit/script_txt.py <대본.json> <대본.txt>
"""
import io, json, sys

구간 = json.load(io.open(sys.argv[1], encoding="utf-8"))
줄 = []
for g in 구간:
    줄.append("[%s %s]" % (g["구간"], g["제목"]))
    줄 += g["문장"]
    줄.append("")
io.open(sys.argv[2], "w", encoding="utf-8").write("\n".join(줄))
print("%s — 구간 %d · 문장 %d" % (sys.argv[2], len(구간), sum(len(g["문장"]) for g in 구간)))
