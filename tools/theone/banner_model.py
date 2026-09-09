# -*- coding: utf-8 -*-
"""(대본 ↔ 배너) 관계를 임베딩으로 재고, 새 회차 문구 후보를 채점한다.

왜 임베딩인가 — 글자 겹침으로 재면 '선이 너무 많아서' 와 '다 지우고' 가 남남이다.
뜻으로 재야 팀장이 어디를 보고 문구를 뽑았는지 보인다.
모델은 KURE-v1 (고려대 NLP, 한국어 검색 벤치마크 1위. bge-m3 미세조정).

    python3 tools/theone/banner_model.py <pairs.jsonl> --report
    python3 tools/theone/banner_model.py <pairs.jsonl> --score <대본.srt> "윗줄" "아랫줄"
    python3 tools/theone/banner_model.py <pairs.jsonl> --near <대본.srt>
"""
import argparse
import io
import json
import os
import re
import sys

MODEL = "nlpai-lab/KURE-v1"
_M = None


def model():
    global _M
    if _M is None:
        from sentence_transformers import SentenceTransformer
        _M = SentenceTransformer(MODEL)
    return _M


def emb(texts):
    import numpy as np
    v = model().encode(list(texts), normalize_embeddings=True,
                       show_progress_bar=False, batch_size=16)
    return np.asarray(v, dtype="float32")


def norm(t):
    return re.sub(r"[^0-9가-힣a-zA-Z]", "", t)


def load(p):
    return [json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip()]


def sentences(cues, maxlen=40):
    """자막 큐를 읽기 좋은 문장 덩어리로 (임베딩 단위)."""
    out, cur = [], ""
    for c in cues:
        cur = (cur + " " + c).strip()
        if len(cur) >= maxlen:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def srt_cues(p):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from srt_index import parse
    return [c["t"] for c in parse(p)]


def report(rows):
    import numpy as np
    eps = sorted({r["ep"] for r in rows if r["cues"]})
    print(f"대본이 있는 회차 {len(eps)}편 — {' '.join(eps)}\n")

    # 회차별: 배너 두 줄 · 대본 전체 · 대본 문장들
    data = {}
    for ep in eps:
        rs = [r for r in rows if r["ep"] == ep]
        up = next((r["text"] for r in rs if r["kind"] == "배너_윗줄"), None)
        lo = next((r["text"] for r in rs if r["kind"] == "배너_아랫줄"), None)
        cues = rs[0]["cues"]
        data[ep] = dict(up=up, lo=lo, script=" ".join(cues), sents=sentences(cues))

    texts, idx = [], {}
    for ep, d in data.items():
        for key in ("up", "lo", "script"):
            idx[(ep, key)] = len(texts)
            texts.append(d[key])
        idx[(ep, "sents")] = (len(texts), len(texts) + len(d["sents"]))
        texts += d["sents"]
    V = emb(texts)

    print("── ① 윗줄/아랫줄이 '대본 전체'와 얼마나 가까운가 ──")
    print("   (아랫줄=주제 요약이면 전체와 가깝고, 윗줄=한 문장 발췌면 덜 가깝다)")
    us, ls = [], []
    for ep, d in data.items():
        s = V[idx[(ep, "script")]]
        u = float(V[idx[(ep, "up")]] @ s)
        l = float(V[idx[(ep, "lo")]] @ s)
        us.append(u)
        ls.append(l)
        print(f"   {ep}  윗줄 {u:.3f}  아랫줄 {l:.3f}   |{d['up']}| / |{d['lo']}|")
    print(f"   평균  윗줄 {np.mean(us):.3f}   아랫줄 {np.mean(ls):.3f}"
          f"   → 아랫줄이 {np.mean(ls)-np.mean(us):+.3f} 더 가깝다")

    print("\n── ② 배너가 대본의 '어느 대목'에서 나왔나 (가장 가까운 문장) ──")
    for ep, d in data.items():
        a, b = idx[(ep, "sents")]
        S = V[a:b]
        for key, name in (("up", "윗줄"), ("lo", "아랫줄")):
            sim = S @ V[idx[(ep, key)]]
            k = int(sim.argmax())
            pos = k / max(1, len(d["sents"]) - 1)
            where = "앞" if pos < 0.34 else ("중간" if pos < 0.67 else "뒤")
            print(f"   {ep} {name}  {sim[k]:.3f} [{where}]  |{d[key]}|")
            print(f"{'':22}← {d['sents'][k][:52]}")

    print("\n── ③ 압축률 (글자 수) ──")
    for ep, d in data.items():
        n = len(norm(d["script"]))
        print(f"   {ep}  대본 {n:4d}자 → 윗줄 {len(d['up']):2d}자 · 아랫줄 {len(d['lo']):2d}자"
              f"   (1/{n//max(1,len(d['up']))} · 1/{n//max(1,len(d['lo']))})")

    print("\n── ④ 배너 낱말이 대본에 그대로 있나 ──")
    for key, name in (("up", "윗줄"), ("lo", "아랫줄")):
        keep = []
        for ep, d in data.items():
            body = norm(d["script"])
            ws = [norm(w) for w in d[key].split() if len(norm(w)) >= 2]
            if ws:
                keep.append(sum(1 for w in ws if w in body) / len(ws))
        print(f"   {name}  대본에 그대로 있는 낱말 비율 평균 {np.mean(keep)*100:.0f}%")
    return data, V, idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--near", help="이 대본과 가장 비슷한 과거 회차를 찾는다 (.srt)")
    ap.add_argument("--score", nargs="+",
                    help="<대본.srt> <문구> [문구...] — 후보 문구를 채점한다")
    ap.add_argument("--chroma", help="쌍 corpus 를 이 폴더에 Chroma 로 저장한다")
    a = ap.parse_args()
    rows = load(a.pairs)

    if a.report:
        report(rows)
        return

    if a.chroma:
        # 다음 세션에서 그대로 꺼내 쓰라고 파일로 남긴다 (chroma-mcp 가 이 폴더를 본다).
        import chromadb
        cl = chromadb.PersistentClient(path=a.chroma)
        try:
            cl.delete_collection("theone_banner")
        except Exception:
            pass
        col = cl.create_collection("theone_banner", metadata={"hnsw:space": "cosine"})
        keep = [r for r in rows if r["text"]]
        docs = [r["text"] for r in keep]
        col.add(ids=[f"{r['ep']}_{r['kind']}_{i}" for i, r in enumerate(keep)],
                documents=docs,
                embeddings=emb(docs).tolist(),
                metadatas=[{"ep": r["ep"], "kind": r["kind"],
                            "script": (r["script"] or "")[:2000]} for r in keep])
        print(f"Chroma 저장 {len(keep)}건 → {a.chroma} (collection: theone_banner)")
        return

    import numpy as np
    eps = sorted({r["ep"] for r in rows if r["cues"]})
    data = {}
    for ep in eps:
        rs = [r for r in rows if r["ep"] == ep]
        data[ep] = dict(
            up=next((r["text"] for r in rs if r["kind"] == "배너_윗줄"), None),
            lo=next((r["text"] for r in rs if r["kind"] == "배너_아랫줄"), None),
            script=" ".join(rs[0]["cues"]))

    if a.near:
        new = " ".join(srt_cues(a.near))
        V = emb([new] + [data[e]["script"] for e in eps])
        sim = V[1:] @ V[0]
        print("새 대본과 가장 비슷한 과거 회차 (그때 쓴 배너를 본보기로)")
        for k in np.argsort(-sim):
            e = eps[k]
            print(f"   {sim[k]:.3f}  {e}  |{data[e]['up']}| / |{data[e]['lo']}|")
        return

    if a.score:
        srt, cands = a.score[0], a.score[1:]
        new = " ".join(srt_cues(srt))
        V = emb([new] + cands + [data[e]["script"] for e in eps]
                + [data[e]["up"] for e in eps] + [data[e]["lo"] for e in eps])
        n = len(eps)
        s_new, s_c = V[0], V[1:1 + len(cands)]
        s_scr = V[1 + len(cands):1 + len(cands) + n]
        s_up = V[1 + len(cands) + n:1 + len(cands) + 2 * n]
        s_lo = V[1 + len(cands) + 2 * n:]
        up_ref = np.array([float(s_up[i] @ s_scr[i]) for i in range(n)])
        lo_ref = np.array([float(s_lo[i] @ s_scr[i]) for i in range(n)])
        print(f"기준 — 과거 {n}편에서")
        print(f"   윗줄↔대본  {up_ref.mean():.3f} (±{up_ref.std():.3f})  "
              f"범위 {up_ref.min():.3f}~{up_ref.max():.3f}")
        print(f"   아랫줄↔대본 {lo_ref.mean():.3f} (±{lo_ref.std():.3f})  "
              f"범위 {lo_ref.min():.3f}~{lo_ref.max():.3f}")
        print("\n후보 채점 (대본과의 가까움)")
        for c, v in zip(cands, s_c):
            sim = float(v @ s_new)
            inu = up_ref.min() <= sim <= up_ref.max()
            inl = lo_ref.min() <= sim <= lo_ref.max()
            tag = ("윗줄 범위" if inu else "") + (" 아랫줄 범위" if inl else "")
            print(f"   {sim:.3f}  |{c}|   {tag or '범위 밖'}")


if __name__ == "__main__":
    main()
