# -*- coding: utf-8 -*-
"""대본 두 벌을 나란히 놓고 **'말이 많은가'** 를 재는 자들.

    python wordy.py <대본1> <대본2> ...

'말이 많다'는 느낌을 셋으로 갈라 센다.
  ① 부피     — 낭독 글자, 문장 수, 문장 길이
  ② 알맹이   — 내용어(명사·동사·형용사·부사) 비율, 서로 다른 낱말 수,
               **서로 다른 내용어 하나당 글자수**(같은 말을 늘려 쓰면 커진다)
  ③ 군더더기 — 되풀이되는 4글자 토막, 늘어나는 말버릇(`~하는 것입니다` 따위),
               문장을 여는 접속 부사

`.md` 초안이면 낭독분만, `.txt` 촬영 대본이면 머리글·지시문을 뺀 낭독분만 센다.
"""
import io
import os
import re
import sys
from collections import Counter

from kiwipiepy import Kiwi

CONTENT = ("NNG", "NNP", "VV", "VA", "MAG", "XR", "SL")
SENT = re.compile(r"(?<=[다요까죠])[.!?]\s*")
HEAD = re.compile(r"^(INTRO|Intro|OUTRO|Outro)\b|^[0-9]{1,2}\.\s+\S")
NOTE = re.compile(r"^\[[^\]]*읽지\s*않음[^\]]*\]|^\[[^\]]*·\s*읽지")
DROP = re.compile(r"[^0-9가-힣a-zA-Z]")
NUM = re.compile(r"[0-9]+(?:[.,][0-9]+)?")

# 늘어나는 말버릇 — 뜻을 더하지 않고 길이만 늘리는 꼴
FILLER = ("하는 것입니다", "라는 것입니다", "는 것이 좋습니다", "하게 됩니다", "되는 것입니다",
          "할 수 있습니다", "수 있게 됩니다", "기도 합니다", "라고 할 수 있습니다",
          "하시면 됩니다", "해 주셔야 합니다", "라는 뜻입니다", "이라고 보시면 됩니다")
OPENER = ("그리고", "그래서", "그런데", "하지만", "또한", "즉", "사실", "이때", "여기서", "다만")

kiwi = Kiwi()


def body_of(path):
    raw = io.open(path, encoding="utf-8").read()
    if path.lower().endswith(".md"):
        raw = raw.split("## INTRO", 1)[-1]
        keep = []
        for ln in raw.split("\n"):
            s = ln.strip()
            if not s or s.startswith(("#", ">", "**[", "---", "|", "- ", "1)", "2)", "3)", "4)")):
                continue
            keep.append(s)
        return " ".join(keep)
    lines = [x for x in raw.split("\n") if x.strip()]
    heads = [x for x in lines if HEAD.match(x)]
    if heads:
        lines = lines[lines.index(heads[0]):]
    return " ".join(x for x in lines if not HEAD.match(x) and not NOTE.match(x))


def stats(text):
    sents = [s.strip() for s in SENT.split(text) if len(s.strip()) >= 4]
    tk = kiwi.tokenize(text)
    content = [t.form for t in tk if t.tag.startswith(CONTENT)]
    uniq = set(content)
    flat = DROP.sub("", text)
    g4 = Counter(flat[i:i + 4] for i in range(len(flat) - 3))
    rep = sum(n for n in g4.values() if n > 1) / max(1, sum(g4.values()))
    k = max(1, len(text)) / 1000
    return {
        "낭독 글자": len(text),
        "문장": len(sents),
        "문장 길이": sum(len(s) for s in sents) / max(1, len(sents)),
        "내용어 비율%": len(content) / max(1, len(tk)) * 100,
        "서로 다른 낱말": len(uniq),
        "낱말 하나당 글자": len(text) / max(1, len(uniq)),
        "되풀이 4글자%": rep * 100,
        "말버릇/천자": sum(text.count(w) for w in FILLER) / k,
        "여는 접속어/천자": sum(len(re.findall(r"(?:^|[.!?]\s*)" + w, text)) for w in OPENER) / k,
        "수치/천자": len(NUM.findall(text)) / k,
    }


if __name__ == "__main__":
    cols = []
    for p in sys.argv[1:]:
        cols.append((os.path.basename(p)[:26], stats(body_of(p))))

    keys = list(cols[0][1])
    w = max(len(k) for k in keys) + 2
    print(" " * w + "".join("%18s" % c[0][:17] for c in cols))
    for key in keys:
        line = "%-*s" % (w, key)
        for _, s in cols:
            v = s[key]
            line += "%18s" % (("%d" % v) if float(v).is_integer() else ("%.1f" % v))
        print(line)
