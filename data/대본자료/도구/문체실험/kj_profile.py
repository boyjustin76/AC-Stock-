# -*- coding: utf-8 -*-
"""김직선만 유독 자주 쓰는 표현 — 다른 12개 채널 대비 Dunning 로그우도비(G²).
형태소 1~3-gram, 김직선 쪽이 더 많은 것만. 트레이딩 주제어(나스닥·볼린저 등)는 말투가 아니므로 뺀다."""
import io, os, re, glob, math, json
from collections import Counter
from kiwipiepy import Kiwi

B = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\05_대본자료\메이저자막"
KJ = "김직선 - 나스닥 트레이더"
kiwi = Kiwi()


def srt(p):
    out = [re.sub(r"<[^>]+>", "", l.strip()) for l in io.open(p, encoding="utf-8", errors="ignore")
           if l.strip() and not l.strip().isdigit() and "-->" not in l]
    return " ".join(x for i, x in enumerate(out) if i == 0 or x != out[i - 1])


def grams(t):
    c = Counter()
    for 조각 in re.findall(r".{1,400}(?:\s|$)", t):
        toks = [x.form + "/" + x.tag[:2] for x in kiwi.tokenize(조각)]
        for n in (1, 2, 3):
            for i in range(len(toks) - n + 1):
                c[" ".join(toks[i:i + n])] += 1
    return c


def 대표자막(폴더):
    # 영상당 하나 — 사람이 올린 ko 가 있으면 그것, 없으면 ko-orig
    fs = glob.glob(os.path.join(B, 폴더, "*.srt"))
    ids = {}
    for f in fs:
        vid = os.path.basename(f).split(".")[0]
        if vid not in ids or f.endswith(".ko.srt"):
            ids[vid] = f
    return list(ids.values())


kj_t = " ".join(srt(f) for f in 대표자막(KJ))
bg_t = " ".join(srt(f) for d in os.listdir(B) if os.path.isdir(os.path.join(B, d)) and d != KJ for f in 대표자막(d))
A, Bc = grams(kj_t), grams(bg_t)
nA, nB = sum(A.values()), sum(Bc.values())

주제어 = re.compile(r"(나스닥|볼린저|이평|이동평균|선물|주식|코인|비트|달러|금리|차트|지표|매수|매도|손절|익절|캔들|추세|RSI|MACD|계좌|수익|/SL|/SN|/SH|/NR)")


def G2(a, b):
    E1 = nA * (a + b) / (nA + nB); E2 = nB * (a + b) / (nA + nB)
    s = 0.0
    for o, e in ((a, E1), (b, E2)):
        if o > 0: s += o * math.log(o / e)
    return 2 * s


out = []
for g, a in A.items():
    b = Bc.get(g, 0)
    if a < 15 or a / nA <= b / nB or 주제어.search(g):
        continue
    out.append((G2(a, b), g, a, b, (a / nA) / ((b + 0.5) / nB)))
out.sort(reverse=True)
print("김직선 자막 %s자 · 배경(12개 채널) %s자" % (format(len(kj_t), ","), format(len(bg_t), ",")))
print("%-28s %6s %6s %7s %8s" % ("표현(형태소)", "김직선", "배경", "배율", "G²"))
for s, g, a, b, r in out[:60]:
    print("%-28s %6d %6d %6.1fx %8.1f" % (g, a, b, r, s))
json.dump([{"표현": g, "김직선": a, "배경": b, "배율": round(r, 2), "G2": round(s, 1)} for s, g, a, b, r in out[:200]],
          io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kj_profile.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
