# -*- coding: utf-8 -*-
"""aligned.json → 컷리스트(json/txt) + 자막(srt).

align_take.py 가 고른 '마지막 테이크' 구간을 붙여 시퀀스용 컷리스트를 만들고,
같은 타임라인 위에 자막을 얹는다.

  · 이어지는 문장은 한 컷으로 묶는다(사이 공백이 MERGE 미만).
    묶지 않으면 한 호흡을 프레임 단위로 쪼개 붙이는 꼴이라 이음매가 튄다.
  · 컷 경계는 실측 무음(ffmpeg silencedetect)에 붙인다 — 앞의 헛기침을 떨구고
    뒤의 STT 꼬리 과대평가를 자른다.
  · 자막 문구는 **대본 표기가 진본**이다. 낭독이 확실히 다를 때만(STT 확신도
    SURE 이상) 음성을 따른다 — STT 오인식을 자막에 싣지 않기 위해서다.
  · 큐 나누기는 srt_rules.split_cue 가 진본이다 (14자 규칙).

    python3 tools/cutedit/cut_and_srt.py <작업폴더> --source <원본.mp4> --name <시퀀스이름>
"""
import argparse
import io
import json
import os
import re
import sys
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from srt_rules import split_cue

MERGE = 0.60        # 이 미만으로 붙은 문장은 한 컷
PAD_PRE = 0.12
PAD_POST = 0.18
SURE = 0.95         # 낭독이 대본과 다를 때 음성을 따르는 STT 확신도 문턱


def norm(t):
    return re.sub(r"[^0-9가-힣a-zA-Z]", "", t)


def read_silences(path):
    out, start = [], None
    if not os.path.exists(path):
        return out
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        m = re.search(r"silence_start:\s*([\d.]+)", ln)
        if m:
            start = float(m.group(1))
        m = re.search(r"silence_end:\s*([\d.]+)", ln)
        if m and start is not None:
            out.append((start, float(m.group(1))))
            start = None
    return out


def snap(a, b, sil):
    """시작은 직전 무음의 끝에, 끝은 직후 무음의 시작에 붙인다."""
    a2, b2 = a - PAD_PRE, b + PAD_POST
    ends = [e for s, e in sil if a - 1.2 < e < a + 0.5]
    if ends:
        a2 = max(a2, max(ends) - 0.08)
    starts = [s for s, e in sil if b - 0.5 < s < b + 1.2]
    if starts:
        b2 = min(b2, min(starts) + 0.08)
    if b2 <= a2 + 0.2:
        a2, b2 = a - PAD_PRE, b + PAD_POST
    return round(a2, 3), round(b2, 3)


def words_between(tr, a, b):
    out = []
    for seg in tr:
        for w in seg.get("words") or []:
            if a - 0.05 <= w["s"] and w["e"] <= b + 0.05:
                out.append(w)
    return out


def spoken_text(script, ws):
    """대본 표기가 진본. 낭독이 확실히 다르면(확신도 SURE 이상) 음성을 따른다."""
    heard = " ".join(w["w"].strip() for w in ws).strip()
    if not heard:
        return script, None
    if SequenceMatcher(None, norm(script), norm(heard)).ratio() >= 0.92:
        return script, None
    if ws and min(w["p"] for w in ws) >= SURE:
        # 대본의 문장부호·따옴표는 살리고 글자만 음성으로 바꾼다
        tail = "".join(re.findall(r"[.,!?”\"]+$", script.strip()) or [""])
        return heard.rstrip(".,!?") + tail, heard
    return script, heard


def fmt(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    return f"{h:02d}:{m:02d}:{t % 60:06.3f}".replace(".", ",")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--source", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--fps", type=float, default=29.97)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--src-dur", type=float, default=0.0)
    a = ap.parse_args()
    S = a.dir

    rows = json.load(io.open(f"{S}/aligned.json", encoding="utf-8"))
    tr = json.load(io.open(f"{S}/cam_transcript.json", encoding="utf-8"))
    sil = read_silences(f"{S}/silences.txt")
    rows = [r for r in rows if r["s"] is not None]

    # ── 1) 이어지는 문장을 한 컷으로 ──────────────────────────────
    groups = []
    for r in rows:
        if groups and r["s"] - groups[-1][-1]["e"] < MERGE:
            groups[-1].append(r)
        else:
            groups.append([r])

    cuts, changed = [], []
    for g in groups:
        a0, b0 = snap(g[0]["s"], g[-1]["e"], sil)
        cuts.append({"in": a0, "out": b0, "label": f'{g[0]["sec"]} {g[0]["text"][:14]}',
                     "lines": [r["i"] for r in g]})

    # ── 2) 소스 시각 → 출력 타임라인 ─────────────────────────────
    def to_out(t):
        acc = 0.0
        for c in cuts:
            if t <= c["out"]:
                return acc + max(0.0, t - c["in"])
            acc += c["out"] - c["in"]
        return acc

    # ── 3) 자막 큐 ───────────────────────────────────────────────
    cues = []
    for r in rows:
        ws = words_between(tr, r["s"], r["e"])
        text, heard = spoken_text(r["text"], ws)
        if heard and text != r["text"]:
            changed.append((r["i"], r["text"], text))
        elif heard:
            changed.append((r["i"], r["text"], f"(낭독 '{heard}' — 대본 유지)"))
        chunks = split_cue(text)
        n = sum(len(norm(c)) for c in chunks) or 1
        s0, e0 = to_out(r["s"]), to_out(r["e"])
        acc = 0
        for ch in chunks:
            k = len(norm(ch))
            cs = s0 + (e0 - s0) * acc / n
            ce = s0 + (e0 - s0) * (acc + k) / n
            acc += k
            if cues and cs - cues[-1]["e"] < 0.08:
                cs = cues[-1]["e"]
            cues.append({"s": cs, "e": ce, "t": ch})

    # ── 4) 내보내기 ──────────────────────────────────────────────
    spec = {"source": os.path.abspath(a.source), "name": a.name, "fps": a.fps,
            "width": a.width, "height": a.height, "src_dur": a.src_dur,
            "cuts": [{k: c[k] for k in ("in", "out", "label")} for c in cuts]}
    json.dump(spec, io.open(f"{S}/cuts.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    srt = []
    for i, c in enumerate(cues, 1):
        srt.append(f"{i}\n{fmt(c['s'])} --> {fmt(c['e'])}\n{c['t']}\n")
    io.open(f"{S}/out.srt", "w", encoding="utf-8-sig", newline="\n").write("\n".join(srt))

    lst, acc = [], 0.0
    for i, c in enumerate(cuts, 1):
        d = c["out"] - c["in"]
        lst.append(f"{i:2d}  소스 {c['in']:7.2f}-{c['out']:7.2f}  "
                   f"→ 타임라인 {acc:6.2f}-{acc + d:6.2f}  ({d:5.2f}초)  {c['label']}")
        acc += d
    io.open(f"{S}/컷리스트.txt", "w", encoding="utf-8", newline="\n").write("\n".join(lst) + "\n")

    print("\n".join(lst))
    print(f"\n컷 {len(cuts)}개 · 완성 길이 {acc:.2f}초 · 자막 큐 {len(cues)}개")
    if changed:
        print("\n대본과 낭독이 다른 곳:")
        for i, was, now in changed:
            print(f"  {i:3d}  대본: {was}\n       →   {now}")


if __name__ == "__main__":
    main()
