# -*- coding: utf-8 -*-
"""A판 한 줄마다 뜻이 가장 가까운 김직선 실제 문장을 찾는다 (Upstage 임베딩, 코사인).
김직선 문장 벡터는 한 번 만들어 캐시한다."""
import io, os, re, glob, json, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kapi
from kiwipiepy import Kiwi

HERE = os.path.dirname(os.path.abspath(__file__))
KJ = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\05_대본자료\메이저자막\김직선 - 나스닥 트레이더"
CACHE_T, CACHE_V = os.path.join(HERE, "kj_sents.json"), os.path.join(HERE, "kj_vecs.npy")
kiwi = Kiwi()


def srt(p):
    out = [re.sub(r"<[^>]+>", "", l.strip()) for l in io.open(p, encoding="utf-8", errors="ignore")
           if l.strip() and not l.strip().isdigit() and "-->" not in l]
    return " ".join(x for i, x in enumerate(out) if i == 0 or x != out[i - 1])


def 임베딩(texts, model):
    out = []
    import time
    for i in range(0, len(texts), 100):
        for 시도 in range(6):
            try:
                r = kapi._post("https://api.upstage.ai/v1/embeddings", {"model": model, "input": texts[i:i + 100]},
                               {"Authorization": "Bearer " + kapi.K["UPSTAGE_API_KEY"], "Content-Type": "application/json"}, timeout=120)
                break
            except RuntimeError as e:
                if "429" not in str(e) or 시도 == 5: raise
                time.sleep(15 * (시도 + 1))        # 요청 한도 — 쉬었다가 다시
        out += [d["embedding"] for d in sorted(r["data"], key=lambda d: d["index"])]
    v = np.array(out, dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def 김직선문장():
    if os.path.exists(CACHE_T) and os.path.exists(CACHE_V):
        return json.load(io.open(CACHE_T, encoding="utf-8")), np.load(CACHE_V)
    본, 문장들 = set(), []
    for f in sorted(glob.glob(os.path.join(KJ, "*.srt"))):
        vid = os.path.basename(f).split(".")[0]
        t = srt(f)
        for 조각 in re.findall(r".{1,600}(?:\s|$)", t):
            for s in kiwi.split_into_sents(조각):
                x = s.text.strip()
                if 8 <= len(x) <= 90 and x not in 본 and "[음악]" not in x:
                    본.add(x); 문장들.append({"문장": x, "영상": vid})
    v = 임베딩([d["문장"] for d in 문장들], "embedding-passage")
    json.dump(문장들, io.open(CACHE_T, "w", encoding="utf-8"), ensure_ascii=False)
    np.save(CACHE_V, v)
    return 문장들, v


def 찾기(줄들, k=3):
    문장들, V = 김직선문장()
    Q = 임베딩(줄들, "embedding-query")
    S = Q @ V.T
    return [[(문장들[j]["문장"], 문장들[j]["영상"], float(S[i, j])) for j in np.argsort(-S[i])[:k]] for i in range(len(줄들))]


if __name__ == "__main__":
    문장들, V = 김직선문장()
    print("김직선 문장 %d개 · 벡터 %s" % (len(문장들), V.shape))
    원 = [l for l in io.open(os.path.join(HERE, "A_판.txt"), encoding="utf-8").read().split("\n") if l.strip()]
    바꿀 = [l for l in 원 if not l.startswith(("[차트", "INTRO.", "3."))]
    for a, hits in zip(바꿀[:6], 찾기(바꿀[:6])):
        print("\nA  " + a)
        for s, vid, c in hits:
            print("   %.2f  %s  (%s)" % (c, s, vid))
