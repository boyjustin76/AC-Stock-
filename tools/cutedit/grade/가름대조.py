# -*- coding: utf-8 -*-
"""사람이 손으로 나눈 자막과 내 가름을 맞댄다 — 경계가 몇 개나 같은가.

**정밀**(내가 끊은 자리 가운데 사람도 끊은 비율)이 더 중요하다 — 글자 수를 기준에서 뺀 뒤로는
적게 끊고 끊은 자리는 전부 사람이 받아들일 자리여야 한다 (이정찬 2026-10-02).

    AC_CUT_DIR=<...>/마01 python3 tools/cutedit/grade/가름대조.py [자막.srt] [정답.txt]
"""
import difflib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 자리 as Z

sys.path.insert(0, Z.도구)
import ko_clause
import srt_rules

맨 = ko_clause.맨
인자 = [a for a in sys.argv[1:] if not a.startswith("-")]
회차 = Z.회차폴더()
내길 = 인자[0] if len(인자) > 0 else os.path.join(회차, "%s_캠_컷.srt" % os.path.basename(회차))
정답길 = 인자[1] if len(인자) > 1 else os.path.join(Z.정답자막, "마01_캠_이정찬_손수정본.txt")

사람 = [l.strip() for l in io.open(정답길, encoding="utf-8-sig").read().split("\n") if l.strip()]
내것 = [c["t"].replace("\n", " ").strip() for c in srt_rules.read_srt(내길)]


def 경계(줄들):
    글, 자리들, 쌓 = "", set(), 0
    for l in 줄들:
        글 += 맨(l)
        쌓 += len(맨(l))
        자리들.add(쌓)
    return 글, 자리들


사람글, ㅅ = 경계(사람)
내글, ㄴ = 경계(내것)
print("정답 %d줄 %d자 (평균 %.1f자) · 나 %d줄 %d자 (평균 %.1f자)"
      % (len(사람), len(사람글), len(사람글) / len(사람), len(내것), len(내글), len(내글) / len(내것)))

sm = difflib.SequenceMatcher(None, 사람글, 내글, autojunk=False)
짝 = {}
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == "equal":
        for d in range(i2 - i1 + 1):
            짝[i1 + d] = j1 + d
되짝 = {v: k for k, v in 짝.items()}
공통 = [i for i in ㅅ if i in 짝]
맞 = [i for i in 공통 if 짝[i] in ㄴ]
내공통 = [j for j in ㄴ if j in 되짝]
맞은내것 = [j for j in 내공통 if 되짝[j] in ㅅ]
print("겹치는 대목 — 닮음 %.4f" % sm.ratio())
print("  재현(정답 경계를 내가 맞춘 비율)   %3d/%3d = %.3f" % (len(맞), len(공통), len(맞) / max(1, len(공통))))
print("  **정밀(내 경계가 정답과 같은 비율) %3d/%3d = %.3f**"
      % (len(맞은내것), len(내공통), len(맞은내것) / max(1, len(내공통))))

더끊음 = sorted(j for j in 내공통 if 되짝[j] not in ㅅ)
print("\n내가 끊었는데 정답은 안 끊은 자리 %d곳 — **이것이 결함이다**" % len(더끊음))
for j in 더끊음[:30]:
    print("   …%s | %s…" % (내글[max(0, j - 14):j], 내글[j:j + 14]))
