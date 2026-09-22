# -*- coding: utf-8 -*-
"""낱말이 회사 Pool 에 몇 번 나오는지 센다 — 바꿔 쓸 말을 고를 때.

    python inpool.py 이탈 돌파 터치 확률

Pool 형태소 셈은 `_pool_forms.json` 에 캐시한다 (Pool 이 바뀌면 지우고 다시 돌린다).
"""
import glob
import io
import json
import os
import sys
from collections import Counter

from kiwipiepy import Kiwi

from paths import POOL

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_pool_forms.json")
# kiwi 는 동사에 VV-R / VV-I 처럼 갈래를 붙여 준다. 정확히 "VV" 만 보면
# 동사가 통째로 비교에서 빠진다 (2026-09-21 실측 — Pool 에 80번 있는 `잡` 이 없는 말로 잡혔다).
TAGS = ("NNG", "NNP", "VV", "VA", "MAG", "XR", "SL")

if os.path.exists(CACHE):
    forms = Counter(json.load(io.open(CACHE, encoding="utf-8")))
else:
    kiwi = Kiwi()
    forms = Counter()
    for p in sorted(glob.glob(os.path.join(POOL, "*.txt"))):
        for t in kiwi.tokenize(io.open(p, encoding="utf-8").read()):
            if t.tag.startswith(TAGS):
                forms[t.form] += 1
    json.dump(forms, io.open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    if __name__ == "__main__":
        print("캐시 만듦: %d개 낱말" % len(forms))

def 글자그대로(w):
    """형태소로는 안 잡히는 말을 글자 그대로 센다.

    kiwi 는 `되돌림` 을 `되돌리`+`ㅁ` 으로 쪼갠다. 그래서 형태소만 보면 Pool 에 68번 있는 말이
    '없음' 으로 나온다 (2026-09-21 실측). 바꿔 쓸 말을 고를 때 이걸 믿으면 멀쩡한 말을 버린다.
    """
    import glob
    n = 0
    for p in glob.glob(os.path.join(POOL, "*.txt")):
        n += io.open(p, encoding="utf-8").read().count(w)
    return n


if __name__ == "__main__":
    for w in sys.argv[1:]:
        n = forms.get(w, 0)
        if n:
            print("%-10s Pool %d번" % (w, n))
        else:
            g = 글자그대로(w)
            print("%-10s %s" % (w, ("**형태소로는 없지만 글자로는 %d번**" % g) if g else "**없음**"))
