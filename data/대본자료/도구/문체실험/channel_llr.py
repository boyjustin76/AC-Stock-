# -*- coding: utf-8 -*-
"""'사람이 고친 문장은 어느 채널 말투 쪽으로 움직였나'
채널마다 글자 3-gram 모델 P_c, 나머지 채널을 합친 배경 P_bg.
그 채널다움 = (log P_c(s) - log P_bg(s)) / 글자수. 사람이 고른 쪽이 더 그 채널다운 비율을 잰다."""
import io, os, re, glob, json, math
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
B = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\05_대본자료"
세트 = json.load(io.open(os.path.join(HERE, "testset.json"), encoding="utf-8"))


def srt(p):
    out = [re.sub(r"<[^>]+>", "", l.strip()) for l in io.open(p, encoding="utf-8", errors="ignore")
           if l.strip() and not l.strip().isdigit() and "-->" not in l]
    return " ".join(x for i, x in enumerate(out) if i == 0 or x != out[i - 1])


def 정리(t):
    return re.sub(r"\s+", " ", re.sub(r"[^가-힣0-9 ]", " ", t)).strip()


채널 = {}
for d in glob.glob(os.path.join(B, "메이저자막", "*") + os.sep):
    fs = glob.glob(os.path.join(d, "*.srt"))
    if fs:
        채널[os.path.basename(os.path.dirname(d))] = 정리(" ".join(srt(f) for f in fs))
채널["(더원 방송본)"] = 정리(" ".join(srt(f) for f in glob.glob(os.path.join(B, "방송본", "더원트레이더", "*.srt"))))


class 삼그램:
    def __init__(self, t, k=0.1):
        t = "^^" + t + "$"
        self.c3 = Counter(t[i:i + 3] for i in range(len(t) - 2))
        self.c2 = Counter(t[i:i + 2] for i in range(len(t) - 1))
        self.V = len(set(t)) + 1
        self.k = k

    def lp(self, s):
        s = "^^" + 정리(s) + "$"
        return sum(math.log((self.c3[s[i:i + 3]] + self.k) / (self.c2[s[i:i + 2]] + self.k * self.V)) for i in range(len(s) - 2))


def 검정(m, n):
    return sum(math.comb(n, i) for i in range(m, n + 1)) / 2 ** n


결과 = []
for c, t in (채널.items() if __name__ == "__main__" else []):
    Pc = 삼그램(t)
    Pbg = 삼그램(" ".join(v for k, v in 채널.items() if k != c))
    def 다움(s):
        return (Pc.lp(s) - Pbg.lp(s)) / max(1, len(정리(s)))
    m = sum(1 for p in 세트 if 다움(p["고름"]) > 다움(p["버림"]))
    결과.append((m / len(세트) * 100, c, m, 검정(m, len(세트)), len(t)))

if __name__ == "__main__":
    print("사람이 고른 문장이 '그 채널다운' 쪽이었던 비율 (53쌍, 우연 50%%)")
for acc, c, m, p, n in sorted(결과, reverse=True):
    print("  %-34s %2d/53 = %3.0f%%  한쪽 p=%.3f   (자막 %s자)" % (c, m, acc, p, format(n, ",")))
