# -*- coding: utf-8 -*-
"""이정찬 손수정본을 정답지로 삼아 ko_clause 의 값들을 맞춰 본다.

경계 일치율만 보면 안 된다 — 끊는 자리를 늘리면 우연히 맞는 것도 늘어난다.
그래서 **맞춘 경계 / 내가 끊은 경계**(정밀)와 **맞춘 경계 / 이정찬 경계**(재현)를 같이 본다.
"""
import io, os, sys, difflib

레포 = r"C:/Users/user/Desktop/이정찬/스크립트_컷편집_통합/01_저장소/E_Script"
sys.path.insert(0, os.path.join(레포, "tools", "cutedit"))
import ko_clause

사람길 = r"C:/Users/user/.claude/uploads/e1fa110c-f82d-4e3c-a7f3-2b7d8284ef16/937c78e7-_____________.txt"
대본길 = r"C:/Users/user/Desktop/이정찬/마이노_0930~/마01/_작업/대본.json"
import json
대본 = json.load(io.open(대본길, encoding="utf-8"))
문장들 = [s for g in 대본 for s in g["문장"]]
사람 = [l.strip() for l in io.open(사람길, encoding="utf-8-sig").read().split("\n") if l.strip()]
맨 = ko_clause.맨


def 경계(줄들):
    글, 자리 = "", set()
    for l in 줄들:
        글 += 맨(l)
        자리.add(len(글))
    return 글, 자리


사람글, 사람자리 = 경계(사람)


def 재기():
    내줄 = []
    for s in 문장들:
        내줄 += ko_clause.조각내기(s)
    내글, 내자리 = 경계(내줄)
    sm = difflib.SequenceMatcher(None, 사람글, 내글, autojunk=False)
    짝 = {}
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for d in range(i2 - i1 + 1): 짝[i1 + d] = j1 + d
    공통 = [i for i in 사람자리 if i in 짝]
    맞 = [i for i in 공통 if 짝[i] in 내자리]
    되짝 = {v: k for k, v in 짝.items()}
    내공통 = [j for j in 내자리 if j in 되짝]
    재현 = len(맞) / max(1, len(공통))
    정밀 = len(맞) / max(1, len(내공통))
    길이 = [len(맨(c)) for c in 내줄]
    return 재현, 정밀, len(내줄), sum(길이) / len(길이)


print("%-22s %-7s %-7s %-6s %s" % ("값", "재현", "정밀", "줄수", "평균자"))
for 이상 in (9, 10, 11, 12, 13, 14):
    for 길어짐 in (13, 15, 17):
        ko_clause.이상기본 = 이상
        ko_clause.길어짐기준 = 길어짐
        재현, 정밀, n, 평 = 재기()
        print("이상 %-2d 길어짐 %-2d      %.3f   %.3f   %-6d %.1f" % (이상, 길어짐, 재현, 정밀, n, 평))
