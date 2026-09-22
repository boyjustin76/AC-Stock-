# -*- coding: utf-8 -*-
"""이정찬이 확정한 8차 문체(목표)에 가장 가까운 채널을 축마다 잰다.
자막엔 문장부호가 없으므로 모두 '어절 끝' 기준으로 같은 자로 잰다."""
import io, re, glob, os, statistics as st

BASE = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\05_대본자료"
HERE = os.path.dirname(os.path.abspath(__file__))


def srt_text(p):
    out = []
    for l in io.open(p, encoding="utf-8", errors="ignore").read().split("\n"):
        l = l.strip()
        if not l or l.isdigit() or "-->" in l:
            continue
        out.append(re.sub(r"<[^>]+>", "", l))
    return " ".join(x for i, x in enumerate(out) if i == 0 or x != out[i - 1])


def 잰다(t):
    toks = [re.sub(r"[.,!?…\"'’‘”“]+$", "", w) for w in t.split()]
    kinds = []
    for w in toks:
        if re.search(r"(니다|니까)$", w): kinds.append("H")
        elif re.search(r"(요|죠)$", w) and len(w) >= 2: kinds.append("Y")
    n = len(kinds) or 1
    runs, cur = [], 0
    for k in kinds:
        if k == "H": cur += 1
        else:
            if cur: runs.append(cur)
            cur = 0
    if cur: runs.append(cur)
    c = len(t.replace(" ", "")) or 1
    per = lambda pat: len(re.findall(pat, t)) / c * 1000
    return {
        "-니다%": kinds.count("H") / n * 100,
        "-니다연속": st.mean(runs) if runs else 0,
        "입니다/천자": per(r"입니다"),
        "질문/천자": per(r"(까요|나요|습니까|될까요|을까요|ㄹ까요)"),
        "확인형죠/천자": per(r"(시죠|셨죠|이죠|거죠|잖아요|죠\?)"),
        "화면가리킴/천자": per(r"(보시면|보이시죠|보이시나요|여기|화면|보세요|보시는|이쪽)"),
        "비교/천자": per(r"(보다|반면|대신|차이|달리|비교|반대로)"),
        "권유/천자": per(r"(세요|십시오|봅시다|볼게요|보겠습니다)"),
        "이음어미/천자": per(r"(으면|하면|는데|은데|니까|면서|다가|거든)"),
        "_글자": c,
    }


목표 = 잰다(" ".join(io.open(os.path.join(HERE, "target_8차이정찬.txt"), encoding="utf-8").read().split("\n")))
채널 = {}
for d in sorted(glob.glob(os.path.join(BASE, "메이저자막", "*") + os.sep)):
    fs = glob.glob(os.path.join(d, "*.srt"))
    if not fs:
        continue
    t = " ".join(srt_text(f) for f in fs)
    채널[os.path.basename(os.path.dirname(d))] = (잰다(t), len(fs))
채널["(더원 방송본)"] = (잰다(" ".join(srt_text(f) for f in glob.glob(os.path.join(BASE, "방송본", "더원트레이더", "*.srt")))), 7)

축 = [k for k in 목표 if not k.startswith("_")]
# 축마다 채널 간 표준편차로 나눠 거리를 잰다(단위가 달라서)
sd = {k: (st.pstdev([v[0][k] for v in 채널.values()]) or 1) for k in 축}
거리 = {}
for 이름, (v, n) in 채널.items():
    거리[이름] = (sum(((v[k] - 목표[k]) / sd[k]) ** 2 for k in 축) / len(축)) ** 0.5

print("| 채널 | 편수 | 거리 | " + " | ".join(축) + " |")
print("|---" * (len(축) + 3) + "|")
print("| **목표(8차+이정찬)** | — | 0 | " + " | ".join("%.1f" % 목표[k] for k in 축) + " |")
for 이름 in sorted(거리, key=거리.get):
    v, n = 채널[이름]
    print("| %s | %d | %.2f | " % (이름, n, 거리[이름]) + " | ".join("%.1f" % v[k] for k in 축) + " |")
print("\n축마다 가장 가까운 채널 (상위 3)")
for k in 축:
    top = sorted(채널, key=lambda c: abs(채널[c][0][k] - 목표[k]))[:3]
    print("  %-14s 목표 %5.1f  →  %s" % (k, 목표[k], " · ".join("%s(%.1f)" % (c, 채널[c][0][k]) for c in top)))
