# -*- coding: utf-8 -*-
"""이정찬이 손으로 나눈 자막과 내 가름을 맞댄다 — 경계가 몇 개나 같은가."""
import io, os, re, sys

레포 = r"C:/Users/user/Desktop/이정찬/스크립트_컷편집_통합/01_저장소/E_Script"
sys.path.insert(0, os.path.join(레포, "tools", "cutedit"))
import srt_rules, ko_clause

사람길 = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:/Users/user/.claude/uploads/e1fa110c-f82d-4e3c-a7f3-2b7d8284ef16/937c78e7-_____________.txt"
내길 = r"C:/Users/user/Desktop/이정찬/마이노_0930~/마01/마01_캠_컷.srt"
맨 = ko_clause.맨

사람 = [l.strip() for l in io.open(사람길, encoding="utf-8-sig").read().split("\n") if l.strip()]
내것 = [c["t"].replace("\n", " ").strip() for c in srt_rules.read_srt(내길)]


def 경계자리(줄들):
    """이어 붙인 글에서 **줄이 끝나는 글자 자리**의 집합. 글 자체도 같이 돌려준다."""
    글, 자리 = "", set()
    for l in 줄들:
        글 += 맨(l)
        자리.add(len(글))
    return 글, 자리


사람글, 사람자리 = 경계자리(사람)
내글, 내자리 = 경계자리(내것)
print("이정찬 %d줄 %d자 (평균 %.1f자) · 나 %d줄 %d자 (평균 %.1f자)"
      % (len(사람), len(사람글), len(사람글) / len(사람), len(내것), len(내글), len(내글) / len(내것)))

if 사람글 != 내글:
    import difflib
    sm = difflib.SequenceMatcher(None, 사람글, 내글, autojunk=False)
    print("글이 다르다 — 닮음 %.4f. 겹치는 대목만 견준다" % sm.ratio())
    # 사람 글자 자리 → 내 글자 자리
    짝 = {}
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for d in range(i2 - i1 + 1):
                if i1 + d <= len(사람글) and j1 + d <= len(내글): 짝[i1 + d] = j1 + d
    공통 = [i for i in 사람자리 if i in 짝]
    맞 = [i for i in 공통 if 짝[i] in 내자리]
    print("견줄 수 있는 이정찬 경계 %d개 중 **내가 같은 자리에 끊은 것 %d개 (%.0f%%)**"
          % (len(공통), len(맞), 100 * len(맞) / max(1, len(공통))))
    안맞 = sorted(i for i in 공통 if 짝[i] not in 내자리)
    print("\n이정찬은 끊었는데 나는 안 끊은 자리 %d곳" % len(안맞))
    for i in 안맞[:25]:
        print("   …%s | %s…" % (사람글[max(0, i - 14):i], 사람글[i:i + 14]))
    # 반대 — 내가 끊었는데 이정찬은 안 끊은 자리
    되짝 = {v: k for k, v in 짝.items()}
    내공통 = [j for j in 내자리 if j in 되짝]
    더끊음 = sorted(j for j in 내공통 if 되짝[j] not in 사람자리)
    print("\n나는 끊었는데 이정찬은 안 끊은 자리 %d곳 (짧게 자른 쪽)" % len(더끊음))
    for j in 더끊음[:25]:
        print("   …%s | %s…" % (내글[max(0, j - 14):j], 내글[j:j + 14]))
else:
    맞 = 사람자리 & 내자리
    print("글이 같다. 경계 %d / %d 일치" % (len(맞), len(사람자리)))
