# -*- coding: utf-8 -*-
# 문체를 먼저 읽힌 뒤 채점 — 앞 문맥(prefix)은 점수에서 빼고 해당 문장 토큰만 센다
import io, json, math, glob, re, os, sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
HERE = os.path.dirname(os.path.abspath(__file__))
쌍 = [tuple(p) for p in json.load(io.open(os.path.join(HERE, "pairs_8_lee.json"), encoding="utf-8"))]
쌍 = [(a, b) for a, b in 쌍 if a.replace(" ", "") != b.replace(" ", "")]
MID = "naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-0.5B"
tok = AutoTokenizer.from_pretrained(MID); model = AutoModelForCausalLM.from_pretrained(MID, torch_dtype=torch.float32).eval()
def srt(p):
    out = [re.sub(r"<[^>]+>", "", l.strip()) for l in io.open(p, encoding="utf-8", errors="ignore") if l.strip() and not l.strip().isdigit() and "-->" not in l]
    return " ".join(x for i, x in enumerate(out) if i == 0 or x != out[i-1])
B = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\05_대본자료"
문맥들 = {
  "더원 방송본 자막": srt(sorted(glob.glob(B + r"\방송본\더원트레이더\*.srt"))[0])[:700],
  "메이저 김직선 자막": srt(sorted(glob.glob(B + r"\메이저자막\김직선*\*.srt"))[0])[:700],
}
def 점수(prefix, s):
    p = tok(prefix, return_tensors="pt").input_ids if prefix else torch.zeros((1,0), dtype=torch.long)
    q = tok((" " if prefix else "") + s, return_tensors="pt").input_ids
    ids = torch.cat([p, q], dim=1)
    labels = ids.clone(); labels[:, :p.shape[1]] = -100
    with torch.no_grad(): return -model(ids, labels=labels).loss.item()
def 검정(k, n): return sum(math.comb(n, i) for i in range(k, n+1)) / 2**n
for 이름, pre in [("문맥 없음", "")] + list(문맥들.items()):
    맞 = sum(1 for a, b in 쌍 if 점수(pre, b) > 점수(pre, a))
    print("%-18s 이정찬 쪽을 높게 %2d/%d = %3.0f%%  p=%.3f" % (이름, 맞, len(쌍), 맞/len(쌍)*100, 검정(맞, len(쌍))))
