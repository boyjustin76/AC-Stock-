# -*- coding: utf-8 -*-
"""자 검증 — 이정찬이 고른 문장을 '더 자연스럽다'고 치는가.
쌍: 8차(Claude) → 이정찬 수정. 두 자를 같은 쌍에 댄다.
  ① Kiwi 형태소 언어모델 (설치돼 있음)
  ② 한국어 LLM 퍼플렉서티 (naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-0.5B, 공개 가중치)
점수는 **토큰당 평균 로그확률**(높을수록 자연스럽다고 보는 것). 길이가 달라도 비교되게 평균을 쓴다.
"""
import io, json, math, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
쌍 = [tuple(p) for p in json.load(io.open(os.path.join(HERE, "pairs_8_lee.json"), encoding="utf-8"))]
쌍 = [(a, b) for a, b in 쌍 if a.replace(" ", "") != b.replace(" ", "")]   # 띄어쓰기만 바뀐 쌍은 뺀다


def 부호검정(k, n):
    # 한쪽: 우연(50%)으로 k개 이상 맞힐 확률
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def 보고(이름, 점수):
    맞 = sum(1 for (a, b) in 쌍 if 점수(b) > 점수(a))
    print("%-34s 이정찬 쪽을 높게: %2d/%d = %3.0f%%   (우연일 확률 p=%.3f)" % (이름, 맞, len(쌍), 맞 / len(쌍) * 100, 부호검정(맞, len(쌍))))


from kiwipiepy import Kiwi
kiwi = Kiwi()
def kiwi점수(s):
    a = kiwi.analyze(s, top_n=1)[0]
    return a[1] / max(1, len(a[0]))
보고("① Kiwi 형태소 언어모델", kiwi점수)

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
MID = sys.argv[1] if len(sys.argv) > 1 else "naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-0.5B"
tok = AutoTokenizer.from_pretrained(MID)
model = AutoModelForCausalLM.from_pretrained(MID, torch_dtype=torch.float32)
model.eval()
캐시 = {}
def llm점수(s):
    if s in 캐시: return 캐시[s]
    ids = tok(s, return_tensors="pt").input_ids
    if tok.bos_token_id is not None and ids[0, 0].item() != tok.bos_token_id:
        ids = torch.cat([torch.tensor([[tok.bos_token_id]]), ids], dim=1)
    with torch.no_grad():
        out = model(ids, labels=ids)
    캐시[s] = -out.loss.item()          # 토큰당 평균 로그확률
    return 캐시[s]
보고("② " + MID.split("/")[-1], llm점수)

print("\n쌍별 (② 기준)")
for a, b in 쌍:
    print("  %s  %6.2f → %6.2f  | %s → %s" % ("○" if llm점수(b) > llm점수(a) else "×", llm점수(a), llm점수(b), a[:26], b[:26]))
