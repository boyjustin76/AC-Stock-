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

    python3 tools/cutedit/align_take.py <작업폴더> <대본.txt> [--exclude <다른폴더>/aligned.json]
      입력  <작업폴더>/cam_transcript.json   (transcribe.py 산출물)
            <작업폴더>/align_fix.json       있으면 줄별 s·e 손질 {"74": {"e": 1326.61, "why": "…"}}
      출력  <작업폴더>/aligned.json
    --exclude  다른 녹음에서 이미 확실히 찾은 줄은 비운다. 롱폼은 캠 녹화(형광 줄)와
               PD 설명 녹화(일반 줄)에 같은 대본을 정렬하는데, PD 녹화에도 캠 줄을 따라 읽거나
               상투 문구가 우연히 붙은 자리가 있다 (L08 인트로 1줄 · '감사합니다').
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


FIRM = 0.75         # 이 이상이면 확실한 후보 — 뒤 문장 한계선을 옮길 자격 (main 의 '확인 필요' 기준과 같다)
RUN_GAP = 0.15      # 낱말 사이가 이보다 좁으면 쉬지 않고 이어 말한 것
HEAD_SIM = 0.62     # 이어진 말이 다음 문장 머리와 이만큼 닮으면 다음 문장이다 (candidates 와 같은 값)
# 머리 **앞 10자만** 견준다. 틀린 테이크는 중간에 '다시 할게요'가 끼어 길게 견주면
# 닮음이 떨어진다 (L08 90번: 전체 길이로 견주면 붙어 버렸다).
# 채점 — 말이 이어진 6곳(붙일 것 1): 4·6·8·10·12·15·20자 모두 6/6, 전체 길이 5/6.
# 틀린 머리 0.90~1.00 · 진짜 꼬리 0.00 으로 간격이 넓어 고원 가운데 값을 쓴다.
HEAD_N = 10
# 꼬리는 **짧다**. 문장 끝을 바꿔 읽는 건 어미 한두 어절이다
#   ('확인해 주세요' → '확인해 주시기 바랍니다' = 2어절 1.2초, L08).
# 상한이 없으면 마지막 줄 뒤에 붙은 잡담을 통째로 삼킨다 — S015 마지막 줄에
#   '이 다음 멘트는 쇼치에서는 안 읽어도 될 것 같고 … 끝내겠습니다' 12어절 5.7초가
#   붙었다(사람 컷 끝 173.04 · 대본 끝 173.58). 마지막 줄은 '다음 문장 머리'가 없어서
#   머리 닮음 검사로는 못 막는다. 넘으면 **아예 안 붙인다** (일부만 붙이지 않는다).
TAIL_MAX = 3


def extend_tail(i, lines, chosen, ws):
    """고른 끝 뒤로 말이 쉬지 않고 이어지면 — 이 문장의 끝인가, 다음 문장인가.

    refine 은 대본과 가장 닮은 창을 고르므로, 낭독이 **문장 끝을 바꿔 읽으면**
    ('확인해 주세요' → '확인해 주시기 바랍니다') 바뀐 꼬리를 떼어 낸다. 그대로
    자르면 말이 끊긴다. 반대로 바로 뒤에 붙은 말이 **다음 문장을 읽다 틀린 것**
    ('…함께 사용합니다 | 둘째 21기간…다시 할게요')이면 붙이면 안 된다.

    가르는 잣대는 꼬리 길이가 아니다 — L08 에서 진짜 꼬리가 0.61초, 틀린 머리가
    0.64초였다. **이어진 말이 다음 문장 머리와 닮았나** 로 가른다. L08 에서 쉬지 않고
    말이 이어진 6곳을 6곳 다 맞혔다 (붙일 것 1 · 안 붙일 것 5). 표본이 얇다.
    마지막 줄은 '다음 머리'가 없으니 TAIL_MAX(3어절)로 막는다 (S015 회귀 — 위 설명).
    다음 채택 문장에 닿으면 거기서 멈춘다 (겹치지 않게 · 바뀐 어미가 쉼 없이 다음 문장에 붙은 자리도 살린다).
    회귀: S016·L08 캠 정렬 0줄 바뀜 · S015 5줄 끝 '쇼시든'(=숏이든) 되찾음 — 경계 채점 0.0511 그대로.
    """
    c = chosen[i]
    if not c:
        return None
    # 뒤 문장 중 **이 문장보다 뒤에 놓인** 채택만 본다. 약한 후보는 한계선을 안 옮기므로
    # 대본 순서상 뒤 문장이 시간상 앞에 잡혀 있을 수 있다 (L08 PD 28줄 24.72초).
    nxt_s = min([x[1] for x in chosen[i + 1:] if x and x[1] >= c[1]] or [1e9])
    run, k, prev_e = [], c[5], ws[c[5] - 1][2]
    while k < len(ws) and ws[k][1] - prev_e <= RUN_GAP:
        # 다음 채택 문장에 닿으면 **거기서 멈춘다** (예전엔 통째로 안 붙였다 — 그러면 바뀐 어미가
        # 다음 문장에 쉼 없이 붙은 자리에서 꼬리가 잘린다: L08 PD '계속 오르고' → '계속 올라가고 | 강한')
        if ws[k][1] >= nxt_s - 0.01:
            break
        run.append(k)
        prev_e = ws[k][2]
        k += 1
    if len(run) > TAIL_MAX:
        return None
    txt = "".join(ws[j][0] for j in run)
    if not txt:
        return None
    heads = [norm(t) for _, t in lines[i + 1:i + 3]]
    heads += [norm(lines[j][1]) for j in range(i + 1, len(lines)) if chosen[j]][:1]
    for h in heads:
        n = min(HEAD_N, len(txt), len(h))
        if n and SequenceMatcher(None, txt[:n], h[:n]).ratio() >= HEAD_SIM:
            return None
    return run[-1] + 1


def pick_last_takes(lines, ws, flat, idx):
    """뒤에서부터 — 다음 문장 채택 위치보다 앞에 있는 가장 늦은 후보."""
    cands = [candidates(t, ws, flat, idx) for _, t in lines]
    chosen = [None] * len(lines)
    limit = len(flat)
    for i in range(len(lines) - 1, -1, -1):
        ok = [c for c in cands[i] if c[3] < limit]
        # 다음 문장보다 앞에 후보가 없으면 **안 읽은 것**으로 둔다.
        # 예전엔 순서를 무시하고 뒤쪽 후보로 물러섰는데, 그러면 컷 순서가 뒤집힌다
        # (L08 '두 번째로 볼린저밴드를 하나 더 추가하겠습니다' 가 아웃트로의
        #  '볼린저밴드를 하나 더 추가한다고' 768.97초에 0.65로 붙었다).
        if not ok:
            continue
        # 확실한 후보(≥ FIRM)가 있으면 그중 가장 늦은 것 = 마지막 테이크.
        # 약한 후보만 있으면 고르되 **앞 문장을 막지 않는다** — 약한 헛짚음 하나가
        # 한계선이 되면 그 앞 문장이 통째로 못 찾음이 된다
        # (L08 PD 녹화: '밴드에 닿았다는 개념을' 이 24.72초에 0.67로 붙어 13~26줄이 사라졌다).
        firm = [c for c in ok if c[0] >= FIRM]
        best = max(firm or ok, key=lambda c: c[3])
        chosen[i] = best
        if firm:
            limit = best[3]
    return cands, chosen


def main():
    args = sys.argv[1:]
    excl = None
    if "--exclude" in args:
        k = args.index("--exclude")
        excl = args[k + 1]
        del args[k:k + 2]
    if len(args) < 2:
        sys.exit("사용법: align_take.py <작업폴더> <대본.txt> [--exclude <다른폴더>/aligned.json]")
    S, script = args[0], args[1]
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
    # 끝을 바꿔 읽어 떨어져 나간 꼬리를 되붙인다 (뒤에서부터 — 다음 문장 자리가 확정된 뒤)
    for i in range(len(lines) - 1, -1, -1):
        b = extend_tail(i, lines, chosen, ws)
        if b:
            c = chosen[i]
            print(f"  꼬리 붙임 {i:3d}  {c[2]:7.2f} → {ws[b - 1][2]:7.2f}  "
                  f"'{' '.join(x[0] for x in ws[c[5]:b])}'", flush=True)
            chosen[i] = (c[0], c[1], ws[b - 1][2], c[3], c[4], b)

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

    if excl:
        taken = {r["i"] for r in json.load(io.open(excl, encoding="utf-8"))
                 if r["s"] is not None and (r["score"] or 0) >= FIRM}
        for r in rows:
            if r["i"] in taken or (r["s"] is not None and r["score"] < FIRM):
                r["s"] = r["e"] = r["score"] = None
        print(f"다른 녹음에서 찾은 줄·약한 후보 비움 → 남은 줄 {sum(r['s'] is not None for r in rows)}개")
    fx = os.path.join(S, "align_fix.json")
    if os.path.exists(fx):
        for k, v in json.load(io.open(fx, encoding="utf-8")).items():
            for r in rows:
                if str(r["i"]) == k and r["s"] is not None:
                    r.update({kk: vv for kk, vv in v.items() if kk in ("s", "e")})
                    r["note"] = v.get("why", "align_fix.json")
                    print(f"줄 손질 {k}: {v}")
    json.dump(rows, io.open(os.path.join(S, "aligned.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    bad = [r for r in rows if r["s"] is None or r["score"] < 0.75]
    print(f"\n문장 {len(rows)}개 · 확인 필요 {len(bad)}개 → {S}/aligned.json")


if __name__ == "__main__":
    main()
