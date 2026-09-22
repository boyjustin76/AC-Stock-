# -*- coding: utf-8 -*-
import io, json, math, sys, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
세트 = json.load(io.open("testset.json", encoding="utf-8"))
def 검정(m, n): return sum(math.comb(n, i) for i in range(m, n + 1)) / 2 ** n
for MID in sys.argv[1:]:
    try:
        tok = AutoTokenizer.from_pretrained(MID); lm = AutoModelForCausalLM.from_pretrained(MID, dtype=torch.float32).eval()
    except Exception as e:
        print("%-45s 불러오기 실패: %s" % (MID, str(e)[:120])); continue
    def s(x):
        ids = tok(x, return_tensors="pt").input_ids
        if tok.bos_token_id is not None and ids[0, 0].item() != tok.bos_token_id:
            ids = torch.cat([torch.tensor([[tok.bos_token_id]]), ids], 1)
        with torch.no_grad(): return lm(ids, labels=ids).loss.item()   # 토큰당 평균 놀람
    m = sum(1 for p in 세트 if s(p["고름"]) < s(p["버림"]))
    print("%-45s 사람 쪽이 덜 놀라움 %d/%d = %.0f%%  (한쪽 p=%.4f)" % (MID.split("/")[-1], m, len(세트), m / len(세트) * 100, 검정(m, len(세트))), flush=True)
    del lm
