# -*- coding: utf-8 -*-
"""흐름(응집성)을 재는 자를 **먼저 검증하고** 쓴다.

    python cohesion.py            # 자 검증 + 대본 채점

2026-09-21, 이정찬 지적으로 만든다. 그날 내가 한 잘못 —
대본을 쓰면서 흐름을 아예 재지 않았고, 뒤늦게 `낱말 이어받기`로 재서
"차12가 L07보다 낫다"는 답을 얻자 **자를 검증하지 않은 채 그 답을 근거로 썼다.**

## 자를 검증하는 법 — 섞기 시험 (Barzilay & Lapata)

흐름을 재는 자가 맞는 자인지 보려면, **답을 아는 자료**에 대 본다.
같은 글의 문장 순서를 무작위로 섞으면 흐름은 반드시 나빠진다. 그러니
**원본 점수 > 섞은 판 점수** 가 거의 100% 나와야 쓸 수 있는 자다.
(`aclanthology.org/P17-1121` · `arxiv.org/html/2312.16893v1` 에서 표준 시험으로 쓰인다)

섞기 시험은 **이웃한 문장끼리 이어지는가**(local coherence)만 검증한다.
'화자가 누구 편에서 말하는가' 같은 **글 전체의 축**은 섞어도 안 변하므로
섞기 시험으로 검증할 수 없다. 그런 자는 **사람이 판정을 준 자료**에 대고 본다
(이정찬 2026-09-21: 차12 는 흐름이 끊긴다 / L07·방송본은 우리 기준선).
"""
import glob
import io
import os
import random
import re
import sys

from kiwipiepy import Kiwi

from paths import AIRED, DOCS, POOL

kiwi = Kiwi()
ENT = ("NNG", "NNP", "SL")                       # 개체로 볼 품사
SENT = re.compile(r"(?<=[다요까죠])[.!?]\s*|(?<=[.!?])\s+")
HEAD = re.compile(r"^(INTRO|Intro|OUTRO|Outro)\b|^[0-9]{1,2}\.\s+\S")
NOTE = re.compile(r"^\[[^\]]*읽지\s*않음[^\]]*\]|^\[[^\]]*·\s*읽지")

# 화자 축 — 피드백이 짚은 것 ([너] → [나] 미러링)
ME = ("저는", "제가", "저도", "제 ", "저의")
YOU = ("여러분", "시청자", "쓰시", "해 보시", "보시면", "하시면", "계신", "계실")


def sentences(text):
    return [s.strip() for s in SENT.split(text) if len(s.strip()) >= 4]


def ents(s):
    return {t.form for t in kiwi.tokenize(s) if t.tag.startswith(ENT) and len(t.form) > 1}


# ── 자 세 개 ───────────────────────────────────────────────────────────
def m_carry(sents):
    """① 이웃한 두 문장이 같은 개체를 공유하는 비율 (entity grid 의 가장 단순한 꼴)."""
    if len(sents) < 2:
        return 0.0
    es = [ents(s) for s in sents]
    return sum(1 for i in range(1, len(es)) if es[i - 1] & es[i]) / (len(es) - 1)


def m_overlap(sents):
    """② 이웃한 두 문장의 개체 겹침 비율 평균 (내가 처음에 쓴 자의 문장판)."""
    if len(sents) < 2:
        return 0.0
    es = [ents(s) for s in sents]
    v = [len(es[i - 1] & es[i]) / max(1, len(es[i])) for i in range(1, len(es))]
    return sum(v) / len(v)


def m_stance(sents):
    """③ 화자 축 — '저/제'와 '여러분'이 글 전체에 얼마나 고르게 깔려 있는가.

    섞어도 안 변한다. 그래서 섞기 시험으로는 검증할 수 없고, 사람 판정으로 본다.
    구간을 5토막으로 나눠, 화자 표현이 **몇 토막에 나타나는가**를 센다.
    """
    n = max(1, len(sents) // 5)
    parts = [" ".join(sents[i:i + n]) for i in range(0, len(sents), n)][:5]
    hit = sum(1 for p in parts if any(w in p for w in ME) or any(w in p for w in YOU))
    return hit / max(1, len(parts))


METRICS = [("① 개체 공유(이웃 문장)", m_carry),
           ("② 개체 겹침 비율", m_overlap),
           ("③ 화자 축 퍼짐", m_stance)]


# ── 자료 ───────────────────────────────────────────────────────────────
def body_md(p):
    raw = io.open(p, encoding="utf-8").read().split("## INTRO", 1)[-1]
    keep = [s.strip() for s in raw.split("\n")
            if s.strip() and not s.strip().startswith(("#", ">", "**[", "---", "|", "- "))]
    return " ".join(keep)


def body_txt(p):
    lines = [x.strip() for x in io.open(p, encoding="utf-8") if x.strip()]
    h = [x for x in lines if HEAD.match(x)]
    if h:
        lines = lines[lines.index(h[0]):]
    return " ".join(x for x in lines if not HEAD.match(x) and not NOTE.match(x))


def load():
    d = {}
    R = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\01_저장소\E_Script\log"
    d["차12(내 것)"] = body_md(os.path.join(R, "차12_더블볼린저_초안.md"))
    d["차13(내 것)"] = body_md(os.path.join(R, "차13_테스타칼만ATR_초안.md"))
    for p in sorted(glob.glob(os.path.join(DOCS, "L0*.txt"))):
        d["더원 " + os.path.basename(p)[:3]] = body_txt(p)
    return d


# ── 1. 섞기 시험 ───────────────────────────────────────────────────────
def shuffle_test(texts, trials=50, seed=7):
    rnd = random.Random(seed)
    print("1. 섞기 시험 — 문장 순서를 섞은 판보다 원본을 높게 매기는가")
    print("   (%d개 글 × %d번 섞기. 쓸 수 있는 자라면 95%% 위여야 한다)\n" % (len(texts), trials))
    print("   %-22s %10s %10s" % ("자", "원본이 높음", "판정"))
    ok = {}
    for name, fn in METRICS:
        win = total = 0
        for t in texts.values():
            ss = sentences(t)
            base = fn(ss)
            for _ in range(trials):
                sh = ss[:]
                rnd.shuffle(sh)
                win += base > fn(sh)
                total += 1
        rate = win / total
        ok[name] = rate >= 0.95
        print("   %-22s %9.1f%% %10s" % (name, rate * 100,
                                         "쓸 수 있다" if ok[name] else "**못 쓴다**"))
    return ok


# ── 2. 사람 판정에 대보기 ──────────────────────────────────────────────
def label_test(texts):
    print("\n2. 사람 판정에 대보기 — 이정찬: 차12 는 흐름이 끊긴다 / 더원 원고가 기준선")
    print("   자가 맞다면 **차12 가 더원 원고들보다 낮게** 나와야 한다\n")
    names = list(texts)
    print("   %-16s %s" % ("글", "".join("%18s" % m for m, _ in METRICS)))
    vals = {m: {} for m, _ in METRICS}
    for nm in names:
        ss = sentences(texts[nm])
        row = ""
        for m, fn in METRICS:
            v = fn(ss)
            vals[m][nm] = v
            row += "%18.3f" % v
        print("   %-16s%s" % (nm, row))
    print()
    for m, _ in METRICS:
        mine = [v for k, v in vals[m].items() if "내 것" in k]
        theirs = [v for k, v in vals[m].items() if "더원" in k]
        avg_m, avg_t = sum(mine) / len(mine), sum(theirs) / len(theirs)
        verdict = "잡아낸다" if avg_m < avg_t else "**못 잡는다** (내 것이 더 높게 나온다)"
        print("   %-22s 내 것 %.3f · 더원 %.3f → %s" % (m, avg_m, avg_t, verdict))


if __name__ == "__main__":
    texts = load()
    ok = shuffle_test(texts)
    label_test(texts)
    print("\n결론 — 두 시험을 **다 통과한 자만** 쓴다.")
