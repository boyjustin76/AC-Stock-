# -*- coding: utf-8 -*-
# C판(선택만) — 모델이 다시 쓰지 않는다. A판 한 줄마다 Pool 통째에서 뜻이 같은 실제 문장을 골라 그대로 쓴다.
import io, os, re, json, sys, contextlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    import pool_c as C, kj_retrieve as R
HERE = os.path.dirname(os.path.abspath(__file__))
VP = os.path.join(HERE, "pool_vecs_plain_all.npy")
if os.path.exists(VP): V = np.load(VP)
else:
    V = R.임베딩([d["문장"] for d in C.문장들], "embedding-passage"); np.save(VP, V)
원, 고정, 바꿀 = C.원, C.고정, C.바꿀
Q = R.임베딩([원[i] for i in 바꿀], "embedding-query")   # 뜻으로 찾기 (틀이 아니라 내용이 같아야 그대로 쓸 수 있다)
S = Q @ V.T
새, 기록 = list(원), []
def 통과(a, s):
    if s.replace(" ", "") == a.replace(" ", ""): return False
    if sorted(re.findall(r"\d+", a)) != sorted(re.findall(r"\d+", s)): return False
    if any(w in a.replace(" ", "") and w not in s.replace(" ", "") for w in ("빨간", "검정", "보조밴드", "메인밴드", "중심선", "안쪽", "20일", "타고", "따라", "이탈")): return False
    if re.match(r"(첫째|둘째|셋째|넷째|그래서|결국|정리하면)", s) and not re.match(r"(첫째|둘째|셋째|넷째|그래서|결국|정리하면)", a): return False
    return not any(b in s for b in C.BAN) and "21" not in s
후보 = {i: [C.문장들[j]["문장"] for j in np.argsort(-S[k])[:30] if 통과(원[i], C.문장들[j]["문장"])] for k, i in enumerate(바꿀)}
모두 = sorted({s for v in 후보.values() for s in v} | {원[i] for i in 바꿀})
E = dict(zip(모두, R.임베딩(모두, "embedding-query")))       # 한 번에 묶어서
원고 = {d["문장"]: d["원고"] for d in C.문장들}
기준 = 0.80        # 문장을 통째로 고를 때 — 0.72(다시 쓰기용)는 뜻이 다른 문장을 들여보냈다(2026-09-22)
지운 = []
for i in 바꿀:
    if i in 지운: continue
    best = max(((float(E[원[i]] @ E[s]), s) for s in 후보[i]), default=(0, None))
    if best[0] >= 기준:
        새[i] = best[1]; 기록.append((i + 1, 원[i], best[1], 원고[best[1]], best[0]))
        # 고른 문장이 다음 줄 내용까지 품고 있으면 다음 줄을 지운다(같은 말 두 번 방지)
        j = i + 1
        if j in 바꿀:
            e = R.임베딩([best[1], 원[j]], "embedding-query")
            if 원[j].rstrip(".").split(",")[0] in best[1] or float(e[0] @ e[1]) >= 0.85:
                새[j] = ""; 지운.append(j)
io.open(os.path.join(HERE, "C_판.txt"), "w", encoding="utf-8").write("\n".join(새))
json.dump([{"줄": n, "A": a, "C": s, "출처": f, "뜻유사도": round(c, 3)} for n, a, s, f, c in 기록], io.open(os.path.join(HERE, "C_출처.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("Pool 에서 뜻이 같은 문장으로 바꾼 줄 %d / %d (나머지는 A판)" % (len(기록), len(바꿀)))
for n, a, s, f, c in 기록:
    print("%2d A  %s\n   C  %s\n      ← %s (뜻 %.2f)" % (n, a, s, f, c))
