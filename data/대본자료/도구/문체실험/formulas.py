# -*- coding: utf-8 -*-
"""[3. 가장 가까운 공식] 을 53쌍에 대 본다.
문장마다 축 값을 재고 → 사람이 고른 쪽으로 값이 한결같이 움직이는지(부호 검정) →
Bradley–Terry(쌍 차이에 대한 로지스틱)로 묶어 한 쌍씩 빼고 맞혀 본다(LOO)."""
import io, os, re, json, math, glob
import numpy as np
from kiwipiepy import Kiwi

HERE = os.path.dirname(os.path.abspath(__file__))
B = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\05_대본자료"
세트 = json.load(io.open(os.path.join(HERE, "testset.json"), encoding="utf-8"))
kiwi = Kiwi()

# ── 말뭉치 (말 짝 = PMI 용) ─────────────────────────────
def srt(p):
    out = [re.sub(r"<[^>]+>", "", l.strip()) for l in io.open(p, encoding="utf-8", errors="ignore") if l.strip() and not l.strip().isdigit() and "-->" not in l]
    return " ".join(x for i, x in enumerate(out) if i == 0 or x != out[i - 1])
말뭉치 = " ".join(io.open(f, encoding="utf-8", errors="ignore").read() for f in glob.glob(B + r"\Pool\*.txt"))
말뭉치 += " " + " ".join(srt(f) for f in glob.glob(B + r"\메이저자막\**\*.srt", recursive=True) + glob.glob(B + r"\방송본\**\*.srt", recursive=True))
from collections import Counter
형태 = Counter(); 짝 = Counter()
for 문 in re.split(r"(?<=[.?!다요])\s+", 말뭉치):
    toks = [t for t in kiwi.tokenize(문) if t.tag.startswith(("NN", "VV", "VA", "XR"))]
    lem = [(t.form + ("다" if t.tag.startswith(("VV", "VA")) else "")) for t in toks]
    for x in lem: 형태[x] += 1
    for i in range(len(lem) - 1):
        짝[(lem[i], lem[i + 1])] += 1
N = sum(형태.values()) or 1


def 말짝PMI(s):
    toks = [t for t in kiwi.tokenize(s) if t.tag.startswith(("NN", "VV", "VA", "XR"))]
    lem = [(t.form + ("다" if t.tag.startswith(("VV", "VA")) else "")) for t in toks]
    vals = []
    for i in range(len(lem) - 1):
        a, b = lem[i], lem[i + 1]
        c = 짝[(a, b)]
        vals.append(math.log((c + 0.1) * N / ((형태[a] + 1) * (형태[b] + 1))))
    return min(vals) if vals else 0.0          # 가장 어색한 말 짝 하나


# ── 놀람(surprisal) — HyperCLOVAX 0.5B ─────────────────
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
MID = "naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-0.5B"
tok = AutoTokenizer.from_pretrained(MID); lm = AutoModelForCausalLM.from_pretrained(MID, torch_dtype=torch.float32).eval()
def 놀람들(s):
    ids = tok(s, return_tensors="pt").input_ids
    if tok.bos_token_id is not None:
        ids = torch.cat([torch.tensor([[tok.bos_token_id]]), ids], 1)
    with torch.no_grad():
        lp = torch.log_softmax(lm(ids).logits[0, :-1], -1)
    return (-lp.gather(1, ids[0, 1:, None])[:, 0]).numpy()


# ── 축 ───────────────────────────────────────────────
def 끝어미(s):
    ef = [t for t in kiwi.tokenize(s) if t.tag == "EF"]
    return ef[-1].form if ef else "(없음)"


def 축(s):
    u = 놀람들(s)
    ef = 끝어미(s)
    return {
        "입니다로끝남": 1.0 if re.search(r"입니다[.?!]?$", s.strip()) else 0.0,
        "합쇼체": 1.0 if re.search(r"(니다|니까)[.?!]?$", s.strip()) else 0.0,
        "질문": 1.0 if s.strip().endswith("?") else 0.0,
        "문두접속": 1.0 if re.match(r"(하지만|그런데|그래서|그러면|다만|결국)", s.strip()) else 0.0,
        "글자수": float(len(s)),
        "놀람평균(UID)": float(u.mean()),
        "놀람분산(UID 균일성)": float(u.var()),
        "놀람이웃차(UID 국소)": float(np.mean(np.diff(u) ** 2)) if len(u) > 1 else 0.0,
        "말짝PMI최저": 말짝PMI(s),
        "명사+이다서술": 1.0 if re.search(r"(이다|입니다|이에요|예요)[.?!]?$", s.strip()) else 0.0,
        "_어미": ef,
    }


rows = [(축(p["버림"]), 축(p["고름"])) for p in 세트]
이름들 = [k for k in rows[0][0] if not k.startswith("_")]

print("축마다: 사람이 고른 쪽에서 값이 어느 쪽으로 움직였나 (같음은 뺌)")
print("%-22s %6s %6s %6s  %s" % ("축", "올라감", "내려감", "같음", "한쪽으로 몰린 정도(부호검정 p, 양쪽)"))
for k in 이름들:
    up = sum(1 for a, b in rows if b[k] > a[k]); dn = sum(1 for a, b in rows if b[k] < a[k]); eq = len(rows) - up - dn
    n = up + dn; m = max(up, dn)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(m, n + 1)) / 2 ** n) if n else 1.0
    print("%-22s %6d %6d %6d  p=%.3f %s" % (k, up, dn, eq, p, "◀ 유의" if p < 0.05 else ""))

# ── Bradley–Terry (특징 차이 로지스틱), 한 쌍씩 빼고 맞히기 ──
X = np.array([[b[k] - a[k] for k in 이름들] for a, b in rows])
mu, sd = X.mean(0), X.std(0) + 1e-9
Xs = X / sd
# 양쪽 방향을 다 넣어(사람=1 / 뒤집으면 0) 절편 없이 학습
def fit(Xtr, lam=1.0, it=500, lr=0.1):
    Xa = np.vstack([Xtr, -Xtr]); ya = np.r_[np.ones(len(Xtr)), np.zeros(len(Xtr))]
    w = np.zeros(Xa.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-Xa @ w)); w -= lr * (Xa.T @ (p - ya) / len(ya) + lam * w / len(ya))
    return w
맞 = 0
for i in range(len(Xs)):
    w = fit(np.delete(Xs, i, 0)); 맞 += (Xs[i] @ w) > 0
w = fit(Xs)
print("\nBradley–Terry (축 %d개 묶음) — 한 쌍씩 빼고 맞힘: %d/%d = %.0f%%" % (len(이름들), 맞, len(Xs), 맞 / len(Xs) * 100))
print("가중치 (＋ = 사람이 그 방향을 좋아함):")
for k, v in sorted(zip(이름들, w), key=lambda x: -abs(x[1])):
    print("  %-22s %+.2f" % (k, v))
json.dump({"축": 이름들, "쌍": [[a, b] for a, b in rows]}, io.open(os.path.join(HERE, "formula_features.json"), "w", encoding="utf-8"), ensure_ascii=False)
