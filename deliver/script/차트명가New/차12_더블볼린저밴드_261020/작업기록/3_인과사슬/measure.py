# -*- coding: utf-8 -*-
"""차12 판마다 같은 자로 잰다 + '팀장 표시 문장은 L07 밖 문장에 몰린다' 가설 시험."""
import io, re, json, difflib, statistics as st

HERE = r"C:\Users\user\AppData\Local\Temp\claude\C--Users-user-Desktop-----------------01-----E-Script\e1fa110c-f82d-4e3c-a7f3-2b7d8284ef16\scratchpad\chain"
판 = [("D0 더원 L07", "D0_L07.txt"), ("D1 원본(Claude)", "D1_원본.txt"), ("D2a A 피드백적용", "D2a_A.txt"),
     ("D2b B 워크플로우", "D2b_B.txt"), ("D3 이정찬 수정", "D3_이정찬.txt"), ("D4 6차(Claude)", "D4_6차.txt"),
     ("D5 6차 이정찬", "D5_6차이정찬.txt"), ("D6 7차(Claude)", "D6_7차.md"), ("D7 수정_1(이정찬)", "D7_수정1.txt")]


def 낭독(path):
    t = io.open(HERE + "\\" + path, encoding="utf-8").read()
    if path.endswith(".md"):
        t = t.split("## INTRO", 1)[1]
        ls = [l.strip().replace("**", "") for l in t.split("\n")]
        ls = [l for l in ls if l and not l.startswith(("#", ">", "[", "|", "---"))]
    else:
        t = t[t.index("INTRO"):].split("현재 해당 매매법에 대한")[0]
        ls = [l.strip() for l in t.split("\n")]
        ls = [l for l in ls if l and not l.startswith(("[", "INTRO", "OUTRO", "---", "사전 질문지", "※"))
              and not re.match(r"^\d+\.\s", l)]
    글 = " ".join(ls)
    문장 = [s.strip() for s in re.split(r"(?<=[.?!])\s+", 글) if s.strip()]
    return 글, 문장


def 끝(s):
    s = s.rstrip()
    if re.search(r"(니다|니까)[.?!]?$", s): return "H"
    if re.search(r"(요|죠)[.?!]?$", s): return "Y"
    return "O"


def 잰다(글, 문장):
    k = [끝(s) for s in 문장]
    runs, cur = [], 0
    for x in k:
        if x == "H": cur += 1
        else:
            if cur: runs.append(cur)
            cur = 0
    if cur: runs.append(cur)
    c = len(글.replace(" ", "")) or 1
    per = lambda pat: len(re.findall(pat, 글)) / c * 1000
    문두 = lambda ws: sum(1 for s in 문장 if s.startswith(ws)) / len(문장) * 100
    return {
        "글자": c, "문장": len(문장), "평균길이": st.mean(len(s) for s in 문장),
        "합쇼%": k.count("H") / len(k) * 100, "입니다%": sum(1 for s in 문장 if re.search(r"입니다[.?!]?$", s)) / len(문장) * 100,
        "합쇼연속": st.mean(runs) if runs else 0, "합쇼최장": max(runs or [0]),
        "질문%": sum(1 for s in 문장 if s.endswith("?")) / len(문장) * 100,
        "여러분/천자": per(r"여러분"), "저/천자": per(r"(저는|제가|저도|제 )"),
        "하지만그런데 문두%": 문두(("하지만", "그런데")), "접속 문두%": 문두(("하지만", "그런데", "그래서", "그러면", "다만", "결국", "이때")),
        "비교/천자": per(r"(보다|반면|달리|대신|차이|비교|반대로|하나만|두 개|2개)"),
        "화면가리킴/천자": per(r"(화면|보시면|보고 계신|보시겠습니다|확대|빨간색|검정색|빨강|검정)"),
    }


결과 = {}
for 이름, f in 판:
    글, 문장 = 낭독(f)
    결과[이름] = 잰다(글, 문장)
keys = list(next(iter(결과.values())).keys())
print("| 판 | " + " | ".join(keys) + " |")
print("|---" * (len(keys) + 1) + "|")
for 이름, d in 결과.items():
    print("| %s | " % 이름 + " | ".join(("%d" % d[k]) if k in ("글자", "문장", "합쇼최장") else ("%.1f" % d[k]) for k in keys) + " |")
json.dump(결과, io.open(HERE + "\\metrics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ── 가설 시험: 팀장이 표시한 문장(D3 기준)은 L07 에 없던 문장인가 ──
_, L07 = 낭독("D0_L07.txt")
_, D3 = 낭독("D3_이정찬.txt")
def 닮음(s):
    return max(difflib.SequenceMatcher(None, s, t, autojunk=False).ratio() for t in L07)
표시 = ["많은 분들이 볼린저밴드를 쓰고 계실 겁니다", "볼린저밴드 하나에 세팅만 두개를 겹쳐서", "순서는 방향을 먼저 보고",
        "마지막에는 이 규칙을 쓰면 안 되는 자리", "저도 여러분처럼 이 세팅을", "지금 화면을 보시면 실제로 그 방식이",
        "이 구간에서 상단에 닿았다고 매도하면", "오늘 제가 이 ‘접촉’의 의미를", "밴드 접촉은 정답이 아니라",
        "그러면 왜 굳이 밴드를 2개나", "통계적인 오류를 줄이는 가장 쉬운 방법이 교차 확인이기", "기본 밴드 하나만 보면 하단을 이탈하는",
        "자주 나오는 신호에는 잘못된 신호도", "그런데 편차 4짜리 보조밴드는", "두 밴드를 같은 자리에서 동시에 이탈한다면"]
표시문장 = [s for s in D3 if any(k in s for k in 표시)]
나머지 = [s for s in D3 if s not in 표시문장]
a = [닮음(s) for s in 표시문장]; b = [닮음(s) for s in 나머지]
print("\n가설: 팀장 표시 문장은 L07 에 없던 문장에 몰린다")
print("  D3 문장 %d개 중 팀장 표시 %d개" % (len(D3), len(표시문장)))
print("  L07 과 가장 닮은 문장과의 유사도 — 표시 중앙 %.2f · 표시 안 됨 중앙 %.2f" % (st.median(a), st.median(b)))
기준 = 0.6
print("  L07 에서 온 문장(유사도 ≥ %.1f) 비율 — 표시 %.0f%% · 표시 안 됨 %.0f%%" % (기준, sum(x >= 기준 for x in a) / len(a) * 100, sum(x >= 기준 for x in b) / len(b) * 100))
# 무작위로 같은 수를 뽑았을 때 표시 중앙값만큼 낮게 나올 확률(순열 검정)
import random
random.seed(0)
모두 = a + b; n = len(a); 관측 = st.median(a); 낮음 = 0
for _ in range(5000):
    random.shuffle(모두)
    if st.median(모두[:n]) <= 관측: 낮음 += 1
print("  순열 검정 5,000회 — 무작위로 뽑아 이만큼 낮게 나올 확률 p = %.4f" % (낮음 / 5000))
