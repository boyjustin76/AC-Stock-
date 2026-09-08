# -*- coding: utf-8 -*-
"""원테이크 녹음 → 최종 대본 정렬 → 컷리스트(json).

녹음 습관(확인됨): 틀리면 쉬었다가 넉넉히 앞으로 돌아가 다시 읽는다.
→ 같은 문장이 여러 번 나오면 **마지막 테이크**가 최종본이다.
   뒤에서부터 훑으며, 다음 문장의 채택 위치보다 앞에 있는 가장 늦은 후보를 고른다.

align_cut.py 와 논리는 같지만 대본 형식이 다르다. 이쪽은 요즘 쓰는
`[제목] [인트로] [본문] [마무리] [고정 멘트]` 한 편짜리 대본을 읽는다.
머리글에 '읽지 않음'이 붙은 덩어리는 낭독분이 아니다.
`[제목]`·`제목:` 은 화면 배너이면서 오프닝 훅으로 낭독되기도 한다. 낭독되지 않았으면
정렬에서 후보가 안 잡혀 저절로 빠진다.

    python3 tools/cutedit/align_take.py <작업폴더> <대본.txt>
      입력  <작업폴더>/cam_transcript.json   (transcribe.py 산출물)
      출력  <작업폴더>/aligned.json
"""
import io
import json
import os
import re
import sys
from difflib import SequenceMatcher

SKIP_HEAD = ()                       # 통째로 낭독 안 하는 덩어리 (지금은 없음)
SKIP_MARK = ("읽지 않음", "읽지않음", "차트 설명", "차트설명")
# 머리글 두 가지를 다 받는다 —
#   S015 형식   [제목] [인트로] [본문] [마무리] [고정 멘트]
#   포인트 형식  ① 훅   ② 근거   ③ 본론   ④ 결론      (tools/shortform.py 뼈대)
HEAD = re.compile(r"^\[([^\]]+)\]\s*$|^([①②③④⑤⑥⑦⑧⑨])\s*(.*)$")
TITLE = re.compile(r"^제목\s*[::]\s*(.+)$")
# 낭독분이 아닌 줄 — 레퍼런스·굵은 글씨·주소
DROP = re.compile(r"^\s*(레퍼런스|참고)\s*[::]|^\s*\*\*|https?://")


def norm(t):
    return re.sub(r"[^0-9가-힣a-zA-Z]", "", t)


def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def read_script(path):
    """낭독 문장 목록 — [(구간이름, 문장), ...]. 줄 하나가 문장 하나다.

    이 대본은 이미 한 줄 = 한 호흡으로 끊겨 있다. 마침표로 다시 쪼개면
    낭독 리듬과 어긋나므로 줄을 그대로 쓴다.
    """
    raw = io.open(path, encoding="utf-8-sig").read()
    out, sec, skip, para = [], "", True, False
    for ln in raw.splitlines():
        t = ln.strip()
        if not t:
            para = False
            continue
        if DROP.search(t):
            continue

        mt = TITLE.match(t)
        if mt:                        # '제목: …' — 훅으로 낭독되기도 한다
            sec, skip, para = "제목", False, False
            out.append((sec, mt.group(1).strip()))
            continue

        m = HEAD.match(t)
        if m:
            head = (m.group(1) or m.group(3) or "").strip()
            para = any(k in head for k in SKIP_MARK)
            if not para:              # '읽지 않음' 은 구간 이름을 바꾸지 않는다
                sec = head or sec
            skip = sec in SKIP_HEAD
            # '읽지 않음'·'차트 설명' 은 그 **문단 하나**만 건너뛴다 (빈 줄에서 끝).
            # 머리글까지 끌고 가면 뒤 본문이 통째로 사라진다 (S015 에서 8줄 날렸다).
            continue

        # 한 줄짜리 지시문 — '[차트 설명: …]' 처럼 대괄호로 감싼 것
        if t.startswith("[") and t.endswith("]"):
            if any(k in t for k in SKIP_MARK):
                continue
        if skip or para:
            continue
        out.append((sec, t))
    return out


def word_stream(tr):
    """STT 단어를 한 줄로 편다 — [(글자, 시각)] 과 이어붙인 문자열."""
    ws = []
    for seg in tr:
        for w in seg.get("words") or []:
            ws.append((norm(w["w"]), w["s"], w["e"]))
    chars, idx = [], []       # idx[i] = chars[i] 가 속한 단어 번호
    for k, (t, _, _) in enumerate(ws):
        for ch in t:
            chars.append(ch)
            idx.append(k)
    return ws, "".join(chars), idx


def candidates(target, ws, flat, idx, lo=0.62):
    """문장 하나의 후보 구간 전부 — [(점수, 시작초, 끝초, 문자위치)]."""
    t = norm(target)
    n = len(t)
    if n < 2:
        return []
    out = []
    step = max(1, n // 12)
    # 길이를 0.8~1.35배로 흔들며 훑는다 (낭독이 늘어지거나 말을 줄인 경우)
    for st in range(0, max(1, len(flat) - n // 2), step):
        best = None
        for f in (0.85, 1.0, 1.2):
            en = min(len(flat), st + int(n * f))
            if en - st < n * 0.6:
                continue
            r = SequenceMatcher(None, t, flat[st:en]).ratio()
            if best is None or r > best[0]:
                best = (r, en)
        if best and best[0] >= lo:
            en = best[1]
            out.append((best[0], ws[idx[st]][1], ws[idx[en - 1]][2],
                        st, idx[st], idx[en - 1] + 1))
    # 겹치는 후보는 점수 높은 것만 남긴다
    out.sort(key=lambda c: -c[0])
    keep = []
    for c in out:
        if all(abs(c[3] - k[3]) > n * 0.5 for k in keep):
            keep.append(c)
    keep.sort(key=lambda c: c[3])
    return keep


def refine(target, w0, w1, ws, span=4):
    """단어 경계를 앞뒤로 흔들어 점수가 제일 높은 자리를 찾는다.

    거친 탐색은 글자 위치로 하는데, 낭독이 대본과 한 글자 다르면
    ('그 불안' → '그 불안함') 시작이 한 단어 밀린다. 여기서 되돌린다.
    """
    t = norm(target)
    best = None
    for a in range(max(0, w0 - span), min(len(ws), w0 + span)):
        for b in range(max(a + 1, w1 - span), min(len(ws), w1 + span) + 1):
            r = SequenceMatcher(None, t, "".join(x[0] for x in ws[a:b])).ratio()
            if best is None or r > best[0]:
                best = (r, a, b)
    return best


def pick_last_takes(lines, ws, flat, idx):
    """뒤에서부터 — 다음 문장 채택 위치보다 앞에 있는 가장 늦은 후보."""
    cands = [candidates(t, ws, flat, idx) for _, t in lines]
    chosen = [None] * len(lines)
    limit = len(flat)
    for i in range(len(lines) - 1, -1, -1):
        ok = [c for c in cands[i] if c[3] < limit]
        if not ok:
            ok = cands[i]
        if not ok:
            continue
        best = max(ok, key=lambda c: c[3])       # 가장 늦은 = 마지막 테이크
        chosen[i] = best
        limit = best[3]
    return cands, chosen


def main():
    if len(sys.argv) < 3:
        sys.exit("사용법: align_take.py <작업폴더> <대본.txt>")
    S, script = sys.argv[1], sys.argv[2]
    tr = json.load(io.open(os.path.join(S, "cam_transcript.json"), encoding="utf-8"))
    lines = read_script(script)
    ws, flat, idx = word_stream(tr)
    cands, chosen = pick_last_takes(lines, ws, flat, idx)

    # 고른 자리를 단어 경계로 다듬는다
    for i, (_, t) in enumerate(lines):
        c = chosen[i]
        if not c:
            continue
        r = refine(t, c[4], c[5], ws)
        if r and r[0] >= c[0] - 0.01:
            chosen[i] = (r[0], ws[r[1]][1], ws[r[2] - 1][2], c[3], r[1], r[2])

    rows = []
    for i, (sec, t) in enumerate(lines):
        c = chosen[i]
        rows.append({"i": i, "sec": sec, "text": t,
                     "score": round(c[0], 3) if c else None,
                     "s": round(c[1], 3) if c else None,
                     "e": round(c[2], 3) if c else None,
                     "takes": len(cands[i])})
        mark = " " if c and c[0] >= 0.75 else "?"
        st = f"{c[1]:7.2f}-{c[2]:7.2f} {c[0]:.2f}" if c else "   못 찾음        "
        print(f"{mark}{i:3d} [{sec}] {st}  x{len(cands[i])}  {t[:38]}", flush=True)

    json.dump(rows, io.open(os.path.join(S, "aligned.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    bad = [r for r in rows if r["s"] is None or r["score"] < 0.75]
    print(f"\n문장 {len(rows)}개 · 확인 필요 {len(bad)}개 → {S}/aligned.json")


if __name__ == "__main__":
    main()
