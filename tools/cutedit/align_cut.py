# -*- coding: utf-8 -*-
"""원테이크 녹음 → 대본 정렬 → 편별 컷리스트.

녹음 습관(사용자 확인): 발음이 틀리면 쉬고, 헛기침 후 넉넉히 앞으로 돌아가 다시 읽는다.
→ 같은 문장이 여러 번 나오면 '마지막 테이크'가 최종본이다.
구현: 대본 문장을 뒤에서부터 훑으며, 다음 문장의 채택 위치보다 앞에 있는
가장 늦은 후보를 고른다 (역방향 최장 사슬).
"""
import json, os, re, sys
from difflib import SequenceMatcher

# 작업 폴더. 차11-4·5 때는 클라우드 스크래치가 박혀 있었다 —
# 환경변수나 첫 인자로 받는다. 회차마다 폴더 하나를 잡고 거기에 다 넣는다.
#   set CUTEDIT_DIR=...\ch11-6   또는   python tools/cutedit/xxx.py <폴더>
S = os.environ.get("CUTEDIT_DIR") or (sys.argv[1] if len(sys.argv) > 1 else "")
if not S or not os.path.isdir(S):
    sys.exit("작업 폴더를 정하세요 — 환경변수 CUTEDIT_DIR 또는 첫 인자로 폴더 경로."
             f" (지금: {S or '없음'})")

def norm(t):
    return re.sub(r"[^0-9가-힣a-zA-Z]", "", t)

def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()

# ── 대본: 편별 문장 목록 ──────────────────────────────────────────────
script = open(f"{S}/test_script.txt", encoding="utf-8").read()

def split_sentences(block):
    # 낭독되지 않는 줄(헤더·제목·단계 마커·메타 지시문)을 걸러낸 뒤 문장 단위로.
    lines = []
    in_title = False
    for ln in block.splitlines():
        t = ln.strip()
        if not t:
            in_title = False
            continue
        if in_title:
            continue
        if t.startswith("[제목]") or t.startswith("제목:"):
            in_title = t.startswith("[제목]")
            continue
        if (t.startswith("###") or t.startswith("(중간)[") or t.startswith("--->")
                or t.startswith("레퍼런스:") or re.match(r"^[①②③④]", t)
                or re.match(r"^\d+\.\s", t) or t.startswith("여기서부터를")):
            continue
        t = re.sub(r"\([^)]*보며\)", "", t).strip()
        if t:
            lines.append(t)
    text = " ".join(lines)
    parts = re.split(r"(?<=[.?!])\s+", text)
    return [p.strip() for p in parts if norm(p)]

blocks = re.split(r"\n(?=\(중간\)\[)", script)
episodes = []
for b in blocks:
    m = re.match(r"\(중간\)\[(SL|포인트_차)\]([^\[\n]+)", b)
    if not m:
        continue
    episodes.append({"kind": m.group(1), "title": m.group(2).strip(), "sents": split_sentences(b)})

# 포인트 편은 컷 대상 아님 — 경계 확인용으로만 유지
for ep in episodes:
    print(f"== [{ep['kind']}] {ep['title']} — {len(ep['sents'])}문장")
    for s in ep["sents"]:
        print("   ·", s[:60])

# ── 전사 ──────────────────────────────────────────────────────────────
segs = json.load(open(f"{S}/cam_transcript.json", encoding="utf-8"))

# 후보: 연속 1~3개 세그먼트 묶음
cands = []
for i in range(len(segs)):
    for k in (1, 2, 3):
        if i + k > len(segs):
            break
        text = "".join(s["text"] for s in segs[i:i + k])
        words = [w for s in segs[i:i + k] for w in s["words"]]
        if not words:
            continue
        cands.append({"i": i, "k": k, "text": text, "s": words[0]["s"], "e": words[-1]["e"], "words": words})

def pick(ep_sents, t_lo, t_hi, thr=0.52):
    """[t_lo, t_hi] 창 안에서 역방향 최장 사슬로 문장별 최종 테이크 선택."""
    chosen = [None] * len(ep_sents)
    limit = t_hi
    for idx in range(len(ep_sents) - 1, -1, -1):
        sent = ep_sents[idx]
        pool = []
        for c in cands:
            if c["e"] > limit + 0.01 or c["s"] < t_lo - 0.01:
                continue
            r = sim(sent, c["text"])
            if r >= thr:
                pool.append((r, c))
        best = None
        if pool:
            top = max(r for r, _ in pool)
            # 유사도 상위 밴드(문장 전체를 덮는 후보) 안에서 가장 늦은 테이크
            band = [(r, c) for r, c in pool if r >= top - 0.07]
            best = max(band, key=lambda rc: rc[1]["s"])
        if best:
            chosen[idx] = best
            limit = best[1]["s"]
        else:
            print(f"  !! 미매칭: {sent[:50]}")
    return chosen

# 편 경계: 각 편 첫 문장(훅)의 마지막 등장 위치로 창을 나눈다
def hook_pos(sent, lo=0.0):
    best_t, best_r = None, 0
    for c in cands:
        if c["s"] < lo:
            continue
        r = sim(sent, c["text"])
        if r > 0.6 and (best_t is None or c["s"] > best_t):
            best_t, best_r = c["s"], r
    return best_t

h1 = 0.0
h2 = hook_pos(episodes[1]["sents"][0])
h3 = hook_pos(episodes[2]["sents"][0])
total_end = segs[-1]["e"]
print(f"\n경계: ep2 훅 {h2}, ep3 훅 {h3}, 끝 {total_end}")

windows = [(0.0, h2 - 0.3), (h2 - 2.0, h3 - 0.3), (h3 - 2.0, total_end)]
result = []
for ep, (lo, hi) in zip(episodes, windows):
    print(f"\n== 정렬: {ep['title']}  창 {lo:.1f}~{hi:.1f}")
    chosen = pick(ep["sents"], lo, hi)
    rows = []
    for sent, ch in zip(ep["sents"], chosen):
        if ch:
            r, c = ch
            rows.append({"script": sent, "heard": c["text"].strip(), "sim": round(r, 3),
                         "s": c["s"], "e": c["e"], "words": c["words"]})
            print(f"  {c['s']:7.2f}-{c['e']:7.2f} r={r:.2f} {c['text'].strip()[:55]}")
    result.append({"kind": ep["kind"], "title": ep["title"], "rows": rows})

json.dump(result, open(f"{S}/aligned.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nsaved aligned.json")
