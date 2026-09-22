# -*- coding: utf-8 -*-
"""어색한 표현 찾기 — **회사 Pool 이 한 번도 붙여 쓴 적 없는 말 짝**을 짚는다.

    python awkward.py <초안.md>      # 어색한 짝 + 더원 원고 기준선
    python awkward.py --기준선        # 기준선만 (leave-one-out)

## 왜 외부 맞춤법 검사기를 안 쓰나 (2026-09-21 실측)

바른(bareun.ai)을 붙여 A판을 검사했더니 받은 교정 20줄 중 여럿이 우리 용어를 망가뜨렸다 —
`볼린저밴드`→`밸린저밴드`(2회), `보조밴드`→`보호밴드`, `1시간봉`→`1시간별`,
`이동평균선`→`이동 평균선`. `않다는 데`→`않다는데` 는 오히려 틀린 교정이다(의존명사 '데').
`et5-typos-corrector` 를 반려한 것과 같은 실패다. **범용 사전에 우리 용어가 없어서 생긴다.**

**그래서 정답지를 Pool 로 바꾼다.** 173편 46만 자가 회사가 실제로 써 온 어법이다.
낱말 단위는 `novel_words.py` 가 본다. 여기서는 **말 짝(내용 형태소 두 개가 이웃한 것)** 을 본다.
Pool 에 한 번도 없는 짝이 곧 "우리가 안 쓰는 말투"다.

## 자를 먼저 검증한다 ([[validate-the-ruler-first]])

기준선은 **leave-one-out** 으로 잰다 — 더원 원고 한 편을 뺀 Pool 로 그 한 편을 채점한다.
합격한 원고들이 내는 값이 곧 정상 범위다. 우리 초안이 그보다 높으면 어색한 것이다.
"""
import collections
import glob
import io
import os
import statistics as st
import sys

from kiwipiepy import Kiwi

from cohesion import body_md, body_txt
from paths import DOCS, POOL

kiwi = Kiwi()
TAGS = ("NNG", "NNP", "VV", "VA", "MAG", "XR", "SL")


def 짝(text):
    """이웃한 내용 형태소 두 개. 조사·어미는 건너뛰고 붙인다."""
    f = [t.form for t in kiwi.tokenize(text) if t.tag.startswith(TAGS)]
    return [(f[i], f[i + 1]) for i in range(len(f) - 1)]


def pool_짝(제외=None):
    c = collections.Counter()
    for p in sorted(glob.glob(os.path.join(POOL, "*.txt"))):
        if 제외 and os.path.basename(p) == 제외:
            continue
        c.update(짝(io.open(p, encoding="utf-8").read()))
    return c


def 채점(text, pool):
    ps = 짝(text)
    새 = [x for x in ps if x not in pool]
    return len(새) / max(1, len(ps)), collections.Counter(새)


if __name__ == "__main__":
    print("Pool 의 말 짝을 세는 중…")
    full = pool_짝()
    print("  서로 다른 짝 %s개\n" % format(len(full), ","))

    # 기준선 — 더원 원고를 제 Pool 에서 빼고 채점 (leave-one-out)
    base = []
    for p in sorted(glob.glob(os.path.join(DOCS, "L0*.txt"))):
        name = "더원_" + os.path.basename(p)
        if not os.path.exists(os.path.join(POOL, name)):
            continue
        r, _ = 채점(body_txt(p), pool_짝(제외=name))
        base.append((os.path.basename(p)[:22], r))
    print("기준선 — 더원 원고를 Pool 에서 빼고 채점")
    for nm, r in base:
        print("   %-24s 새 짝 %5.1f%%" % (nm, r * 100))
    med = st.median([r for _, r in base])
    hi = max(r for _, r in base)
    print("   중앙 %.1f%% · 최대 %.1f%%\n" % (med * 100, hi * 100))

    for path in [a for a in sys.argv[1:] if not a.startswith("--")]:
        text = body_md(path) if path.lower().endswith(".md") else body_txt(path)
        r, c = 채점(text, full)
        mark = "통과" if r <= hi else "**기준선 밖**"
        print("=" * 76)
        print("%s — 새 짝 %.1f%% (더원 중앙 %.1f%% · 최대 %.1f%%)  %s"
              % (os.path.basename(path), r * 100, med * 100, hi * 100, mark))
        print("\n   Pool 이 한 번도 붙여 쓴 적 없는 짝 %d종 — 잦은 순" % len(c))
        sents = [s for s in text.split(". ")]
        for (a, b), n in c.most_common(25):
            보기 = next((s for s in sents if a in s and b in s), "")
            print("   %-22s ×%-2d %s" % ("%s + %s" % (a, b), n, 보기[:58]))
