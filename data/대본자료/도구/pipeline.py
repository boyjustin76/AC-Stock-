# -*- coding: utf-8 -*-
"""차트명가 New 대본 — 관문 전부를 한 줄로 돌린다.

    python pipeline.py <초안.md> [...]        # 채점만
    python pipeline.py <초안.md> --docx        # 통과하면 납품용 .docx 까지

**사람 손을 대체하는 것이 목적이다** (이정찬 2026-09-21). 그래서 관문은 전부
`통과/미달` 로 떨어지고, 기준값은 **지어내지 않고 더원 촬영 대본에서 그때그때 잰다.**
하나라도 미달이면 끝 줄이 `미달`이고 exit code 가 1 이다 — 자동화에 걸 수 있다.

단계와 자

| # | 관문 | 자 | 어디서 왔나 |
|---|---|---|---|
| 1 | 어휘   | `novel_words.py`  | 회사 Pool 173편에 없는 말 0종 |
| 2 | 규격   | `grade_draft.py`  | 분량·문장·금지어·근거·수치·반말 (Pool·메이저 실측) |
| 3 | 흐름   | `cohesion.py`     | 섞기 시험을 통과한 자만 씀 |
| 4 | 말수   | `wordy.py`        | 내용어 하나당 글자 — 압축률 |
| 5 | 논리·유지 | `flow_check.py` | 주장 먼저·구간 닫기·이음(bridge)·인터럽트 간격 |
| 6 | 납품   | `md_to_script_docx.py` | 더원 양식 그대로 |

`03_실험기록`·`06_외부스킬` 의 어느 스킬이 어느 관문이 되었는지는
`05_대본자료/워크플로우.md` 에 적어 둔다.
"""
import glob
import os
import random
import re
import statistics as st
import subprocess
import sys

import cohesion as C
import flow_check as F
import wordy as W
from paths import BASE, DOCS

REPO = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\01_저장소\E_Script"


def 더원_대본():
    return sorted(glob.glob(os.path.join(DOCS, "L0*.txt")))


def 흐름z(sents, trials=60, seed=11):
    base = C.m_carry(sents)
    rnd = random.Random(seed)
    sh = []
    for _ in range(trials):
        x = sents[:]
        rnd.shuffle(x)
        sh.append(C.m_carry(x))
    mu, sd = st.mean(sh), st.pstdev(sh) or 1e-9
    return (base - mu) / sd


def 기준선():
    z, dense = [], []
    for p in 더원_대본():
        t = W.body_of(p)
        ss = C.sentences(t)
        if len(ss) < 20:
            continue
        z.append(흐름z(ss))
        dense.append(W.stats(t)["낱말 하나당 글자"])
    return {"흐름z": st.median(z), "낱말당글자": st.median(dense) * 1.10}


def 규격(path):
    r = subprocess.run([sys.executable, os.path.join(REPO, "tools", "grade_draft.py"), path],
                       capture_output=True, text=True, encoding="utf-8")
    o = r.stdout
    g = lambda pat, d=0.0: float(re.search(pat, o).group(1).replace(",", "")) if re.search(pat, o) else d  # noqa: E731
    return {"분량": g(r"낭독 합계 ([\d,]+)자"),
            "문장길이": g(r"평균 ([\d.]+)자"),
            "금지어없음": "금지어    없음" in o,
            "근거": g(r"근거 표현\s+\d+회 \(([\d.]+)/천자\)"),
            "반말": g(r"반말투\s+(\d+)건")}


def 검사(path, base, flow_base):
    t = W.body_of(path)
    ss = C.sentences(t)
    n = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     "novel_words.py"), path],
                       capture_output=True, text=True, encoding="utf-8").stdout
    m = re.search(r"아예 없는 말\*\* (\d+)종", n)
    novel = int(m.group(1)) if m else -1
    sp = 규격(path)
    fl = F.score(path)
    w = W.stats(t)
    rows = [
        ("1 어휘", "Pool 에 없는 말 %d종" % novel, novel == 0, "0종"),
        ("2 규격 · 분량", format(int(sp["분량"]), ",") + "자", 4700 <= sp["분량"] <= 5300, "4,700~5,300자"),
        ("2 규격 · 문장", "%.1f자" % sp["문장길이"], 35 <= sp["문장길이"] <= 43, "39±4자"),
        ("2 규격 · 금지어", "없음" if sp["금지어없음"] else "**있음**", sp["금지어없음"], "0"),
        ("2 규격 · 근거", "%.1f/천자" % sp["근거"], sp["근거"] >= 5.4, "5.4 이상"),
        ("2 규격 · 반말", "%d건" % sp["반말"], sp["반말"] == 0, "0"),
        ("3 흐름", "z %.2f" % 흐름z(ss), 흐름z(ss) >= base["흐름z"], "더원 중앙 %.2f 이상" % base["흐름z"]),
        ("4 말수", "내용어당 %.1f자" % w["낱말 하나당 글자"],
         w["낱말 하나당 글자"] <= base["낱말당글자"], "%.1f자 이하" % base["낱말당글자"]),
    ]
    for k in F.KEYS:
        rows.append(("5 %s" % k, "%.2f" % fl[k], fl[k] >= flow_base[k],
                     "더원 중앙 %.2f 이상" % flow_base[k]))
    return rows


if __name__ == "__main__":
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not paths:
        raise SystemExit(__doc__)
    print("기준선을 더원 촬영 대본에서 재는 중…")
    base = 기준선()
    ref = [s for s in (F.score(p) for p in 더원_대본()) if s["구간"] >= 3]
    flow_base = {k: st.median([s[k] for s in ref]) for k in F.KEYS}
    bad = 0
    for p in paths:
        print("\n" + "=" * 78)
        print("%s" % os.path.basename(p))
        print("%-24s %-20s %-10s %s" % ("관문", "잰 값", "판정", "기준"))
        for name, val, ok, crit in 검사(p, base, flow_base):
            bad += not ok
            print("%-24s %-20s %-10s %s" % (name, val, "통과" if ok else "**미달**", crit))
    print("\n" + ("전부 통과" if not bad else "**미달 %d개 — 고쳐야 한다**" % bad))
    if bad:
        sys.exit(1)
    if "--docx" in sys.argv:
        tmpl = os.path.join(BASE, "..", "02_납품물", "Legacy", "더원트레이더",
                            "L08_더블볼린저밴드매매법_260923",
                            "L07_더블볼린저밴드_매매법_촬영용_스크립트_초안_260903.docx")
        for p in paths:
            out = os.path.splitext(p)[0] + ".docx"
            subprocess.run([sys.executable, os.path.join(REPO, "tools", "md_to_script_docx.py"),
                            p, os.path.normpath(tmpl), out])
