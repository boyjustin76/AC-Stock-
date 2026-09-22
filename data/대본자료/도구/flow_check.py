# -*- coding: utf-8 -*-
"""논리 이음 + 시청 유지 검사 — 받아 온 두 스킬을 **기계가 재는 꼴**로 옮긴 것.

    python flow_check.py <초안.md>        # 채점
    python flow_check.py --기준선          # 더원 9편으로 기준선을 다시 잰다

어디서 왔나 (둘 다 MIT · `06_외부스킬/`)
  · `academic-writing-agents` 의 원칙 — A5 주장 먼저 · A4 문단 닫기 · A2 이음말로 사슬 걸기,
    그리고 `logic-reviewer` 의 "구간 끝이 다음 구간 시작을 불러야 한다".
  · `creator-studio/youtube-script-writer` 의 beat 구조 — beat 마다 mini-hook · delivery ·
    **bridge**(다음 beat 로 여는 고리), 그리고 60~90초마다 pattern interrupt.

**원칙을 그대로 두면 사람이 읽고 판단해야 한다.** 그래서 넷만 남기고 기계가 세게 바꿨다.
  ① 주장 먼저  구간 첫 문장이 그 구간 제목의 핵심어를 담는가
  ② 구간 닫기  구간 끝 문장이 닫는 말인가 (정리·그래서·따라서·뜻입니다 …)
  ③ 이음       구간 끝 문장과 다음 구간 첫 문장이 같은 개체를 공유하는가  ← bridge
  ④ 인터럽트   화면 지시문 사이 간격이 60~90초(≈370~550자)에 드는가

**기준은 지어내지 않는다.** 더원 촬영 대본 9편을 같은 자로 재서 나온 값을 쓴다(`--기준선`).
"""
import glob
import io
import os
import re
import statistics as st
import sys

from cohesion import ents, sentences
from paths import DOCS

CLOSE = ("정리하", "그래서", "따라서", "즉 ", "결국", "뜻입니다", "때문입니다", "됩니다",
         "보겠습니다", "말씀드리", "기억하", "확인합니다", "않습니다")
PROMISE = ("보여 드리", "정리하겠", "알려 드리", "설명드리", "말씀드리겠", "찾아보겠")
CPS = 6.2                       # 자/초 — 우리 실측 5.4~7.1 의 가운데
NOTE = re.compile(r"^\s*(\*\*)?\[[^\]]*읽지\s*않음[^\]]*\]")
HEAD_TXT = re.compile(r"^(INTRO|Intro|OUTRO|Outro)\b|^[0-9]{1,2}\.\s+\S")


def read_sections(path):
    """[(제목, [낭독 문단…], [지시문 위치(자)…])] — .md 와 더원 .txt 를 같이 읽는다."""
    raw = io.open(path, encoding="utf-8").read()
    secs, cur, notes, pos = [], None, [], 0
    if path.lower().endswith(".md"):
        raw = raw.split("## INTRO", 1)[-1]
        lines = ("## INTRO" + raw).split("\n")
        is_head = lambda s: s.startswith("## ")            # noqa: E731
        head_of = lambda s: s[3:].strip()                  # noqa: E731
        skip = lambda s: s.startswith(("#", ">", "---", "|", "- ", "1)", "2)", "3)", "4)"))  # noqa: E731
    else:
        lines = raw.split("\n")
        is_head = lambda s: bool(HEAD_TXT.match(s))        # noqa: E731
        head_of = lambda s: s.strip()                      # noqa: E731
        skip = lambda s: False                             # noqa: E731

    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if is_head(s):
            if cur is not None:
                secs.append((cur[0], cur[1], notes))
            cur, notes, pos = [head_of(s), []], [], 0
            continue
        if cur is None:
            continue
        if NOTE.match(s):
            notes.append(pos)
            continue
        if skip(s):
            continue
        cur[1].append(s)
        pos += len(s)
    if cur is not None:
        secs.append((cur[0], cur[1], notes))
    return [x for x in secs if x[1]]


def score(path):
    secs = read_sections(path)
    claim = close = bridge = 0
    gaps = []
    for i, (head, body, notes) in enumerate(secs):
        ss = sentences(" ".join(body))
        if not ss:
            continue
        key = ents(head)
        claim += bool(key & ents(ss[0])) or not key
        close += any(w in ss[-1] for w in CLOSE)
        if i + 1 < len(secs):
            nxt = sentences(" ".join(secs[i + 1][1]))
            if nxt:
                bridge += bool(ents(ss[-1]) & ents(nxt[0]))
        total = sum(len(x) for x in body)
        marks = [0] + notes + [total]
        gaps += [(marks[j + 1] - marks[j]) / CPS for j in range(len(marks) - 1) if marks[j + 1] > marks[j]]
    n = len(secs)
    if n == 0:                       # 대본 장르가 아닌 파일(질문지·기획서)
        return dict({"구간": 0, "인터럽트 중앙(초)": 0}, **{k: 0.0 for k in KEYS})
    ok = [g for g in gaps if 60 <= g <= 90]
    return {"구간": n,
            "① 주장 먼저": claim / n,
            "② 구간 닫기": close / n,
            "③ 이음(bridge)": bridge / max(1, n - 1),
            "④ 인터럽트 60~90초": len(ok) / max(1, len(gaps)),
            "인터럽트 중앙(초)": st.median(gaps) if gaps else 0}


KEYS = ["① 주장 먼저", "② 구간 닫기", "③ 이음(bridge)", "④ 인터럽트 60~90초"]


def baseline():
    rows = []
    for p in sorted(glob.glob(os.path.join(DOCS, "L0*.txt"))):
        try:
            s = score(p)
        except Exception:
            continue
        if s["구간"] >= 3:
            rows.append((os.path.basename(p)[:14], s))
    print("더원 촬영 대본 %d편 — 기준선\n" % len(rows))
    print("%-16s %6s %s" % ("글", "구간", "".join("%18s" % k for k in KEYS)))
    for nm, s in rows:
        print("%-16s %6d %s" % (nm, s["구간"], "".join("%18.2f" % s[k] for k in KEYS)))
    print("\n%-16s %6s %s" % ("중앙값", "", "".join("%18.2f" % st.median([s[k] for _, s in rows]) for k in KEYS)))
    print("인터럽트 중앙 %.0f초" % st.median([s["인터럽트 중앙(초)"] for _, s in rows]))
    return {k: st.median([s[k] for _, s in rows]) for k in KEYS}


if __name__ == "__main__":
    if "--기준선" in sys.argv:
        baseline()
    else:
        base = baseline()
        print()
        for p in [a for a in sys.argv[1:] if not a.startswith("--")]:
            s = score(p)
            print("=" * 74)
            print("%s — 구간 %d · 인터럽트 중앙 %.0f초" % (os.path.basename(p), s["구간"], s["인터럽트 중앙(초)"]))
            for k in KEYS:
                mark = "통과" if s[k] >= base[k] else "**미달**"
                print("   %-20s %5.2f  (더원 중앙 %.2f)  %s" % (k, s[k], base[k], mark))
