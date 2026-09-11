# -*- coding: utf-8 -*-
"""PD 설명 녹화 → 컷편집본 V2 시각자료. **대본 자리로** 얹는다.

롱폼 촬영은 두 번 한다 (L08 에서 확인) —
  캠 녹화      카메라 보고 읽는 줄(대본 형광 줄)만. PD 가 '챕터 N 인트로 멘트' 식으로 끊어 딴다.
  PD 설명 녹화 차트 화면 녹화. 챕터마다 형광 아닌 줄을 **나레이션으로 읽고**, 이어서 PD 에게
               어느 구간을 쓰라고 설명한다. 나레이션은 멈춘 차트 한 화면 위에서 읽힌다.

그래서 컷 하나(대본 몇 줄)에 얹을 차트는 **같은 챕터에서 가장 가까운 나레이션 덩어리**가
띄워 둔 화면이다.
  컷 줄이 곧 덩어리면 그것 — 일반 줄이 없는 챕터(L08 INTRO)는 PD 가 캠 줄을 읽으며 띄운 화면
  뒤 덩어리가 앞 덩어리보다 가깝거나 같으면 뒤 (컷 문장이 차트를 연다)
  아니면 앞 (컷 문장이 차트를 닫는다)
  같은 덩어리를 쓰는 컷은 PD 도 이어서 튼다 — 사이에 얼굴 컷이 끼어도 되감지 않는다
  화면 전환(스크롤·창 바꿈)을 넘으면 거기서 멈추고 그 덩어리의 나머지 컷은 얼굴
  나레이션이 없는 챕터(OUTRO)는 얼굴
V2 자리는 V1 과 **프레임 단위로** 같게 둔다. 영상만 올린다 (오디오 없음).

버린 방법 — KURE-v1 임베딩 닮음으로 컷×PD 말 덩어리를 짝지었더니 닮음이 0.53~0.82 로
뭉개져 문턱을 못 잡았고(가장 큰 틈 0.032), 4장 스퀴즈 컷에 1장 밴드 타기 차트가 붙었다.
낱말이 겹치는 앞쪽 덩어리로 끌려간다.

    python3 tools/cutedit/pd_overlay.py <캠 작업폴더> <PD 작업폴더> <대본.txt> --pd-src <PD.mp4>
      입력  캠폴더/cuts.json · aligned.json        (align_take · cut_and_srt 산출물)
            PD폴더/aligned.json                    (PD 녹음에 align_take 를 같은 대본으로 돌린 것)
      출력  캠폴더/cuts_pd.json   → make_xml.py 로 V2 시퀀스
            PD폴더/overlay.json   컷마다 근거 · PD폴더/scene_diff.json 화면 변화 캐시
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from align_take import FIRM, read_script   # noqa: E402

CHG = 0.08          # 1초 간격 화면에서 이만큼(화소 비율) 바뀌면 전환 — L08 스크롤·창 바꿈이 8~17%
JUMP = 5.0          # 이어진 대본 줄이라도 PD 에서 이만큼 떨어져 읽혔으면 다른 차트
                    # (L08 4장 71~73줄 1140초 스퀴즈 화면 · 74~80줄 1321초 뒤 손절 화면)


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def duration(src):
    p = subprocess.run([ffmpeg(), "-hide_banner", "-i", src],
                       capture_output=True, text=True, errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", p.stderr or "")
    if not m:
        raise SystemExit(f"길이를 못 읽었습니다: {src}")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def scene_diff(src, cache):
    """1초 간격 회색조 192×108 에서 앞 초와 달라진 화소 비율. 정지 차트에선 커서만 움직인다."""
    if os.path.exists(cache):
        return json.load(io.open(cache, encoding="utf-8"))
    import numpy as np
    W, H = 192, 108
    p = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-threads", "1",
                        "-i", src, "-vf", f"fps=1,scale={W}:{H}",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    a = np.frombuffer(p.stdout, dtype=np.uint8).reshape(-1, H, W).astype(np.int16)
    d = [float((abs(a[i] - a[i - 1]) > 30).mean()) for i in range(1, len(a))]
    json.dump(d, io.open(cache, "w", encoding="utf-8"))
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cam")
    ap.add_argument("pd")
    ap.add_argument("script")
    ap.add_argument("--pd-src", required=True)
    ap.add_argument("--pd-dur", type=float, default=None)
    a = ap.parse_args()

    lines = read_script(a.script)
    spec = json.load(io.open(os.path.join(a.cam, "cuts.json"), encoding="utf-8"))
    fps = float(spec.get("fps", 29.97))

    def frames(t):
        return int(round(t * fps))

    cam = [r for r in json.load(io.open(os.path.join(a.cam, "aligned.json"), encoding="utf-8"))
           if r["s"] is not None and r["score"] >= FIRM]
    pd = {r["i"]: r for r in json.load(io.open(os.path.join(a.pd, "aligned.json"), encoding="utf-8"))
          if r["s"] is not None and r["score"] >= FIRM}
    cam_idx = {r["i"] for r in cam}
    pd_dur = a.pd_dur or duration(a.pd_src)
    diff = scene_diff(a.pd_src, os.path.join(a.pd, "scene_diff.json"))
    chg = sorted(k + 1 for k, d in enumerate(diff) if d > CHG)

    # 캠 줄은 덩어리에서 뺀다 — 단, PD 에 일반 줄 나레이션이 하나도 없는 챕터는 캠 줄을 읽은 자리를 쓴다.
    # 그때도 **10자 미만 캠 줄은 안 쓴다**. 짧은 상투 문구는 아무 데나 붙는다 — L08 OUTRO
    # '감사합니다'(5자)가 PD 손절 나레이션 끝 '…대응을 합니다' 에 0.75 로 붙어(후보 13곳)
    # 아웃트로 컷 3개에 손절 차트가 얹혔다. 쓰려던 INTRO 는 40자 문장을 PD 가 통째로 읽었다(후보 1곳).
    cam_min = 10
    narrated = {lines[i][0] for i in pd if i not in cam_idx}
    runs = []
    for i in sorted(pd):
        sec = lines[i][0]
        if i in cam_idx and (sec in narrated
                             or len(re.sub(r"[^0-9가-힣a-zA-Z]", "", lines[i][1])) < cam_min):
            continue
        if (runs and runs[-1]["sec"] == sec and i == runs[-1]["b"] + 1
                and pd[i]["s"] - runs[-1]["e"] <= JUMP):
            runs[-1]["b"], runs[-1]["e"] = i, pd[i]["e"]
            continue
        runs.append({"sec": sec, "a": i, "b": i, "t": pd[i]["s"], "e": pd[i]["e"]})
    print("PD 나레이션 덩어리")
    for r in runs:
        print(f"   [{r['sec']}] 줄 {r['a']}~{r['b']}  PD {r['t']:.2f}초  {lines[r['a']][1][:30]}")

    cuts, at_f = [], 0
    for k, c in enumerate(spec["cuts"], 1):
        n = frames(c["out"]) - frames(c["in"])
        idx = [r["i"] for r in cam if min(r["e"], c["out"]) - max(r["s"], c["in"]) > 0.3]
        cuts.append({"k": k, "at_f": at_f, "n": n, "idx": idx,
                     "sec": lines[idx[0]][0] if idx else None})
        at_f += n

    def anchor(c):
        if not c["idx"]:
            return None, "대본 줄 없음"
        lo, hi, sec = min(c["idx"]), max(c["idx"]), c["sec"]
        same = [r for r in runs if r["sec"] == sec]
        own = [r for r in same if r["a"] <= hi and r["b"] >= lo]
        if own:
            return own[0], f"자기 줄 덩어리 (줄 {own[0]['a']}~{own[0]['b']})"
        nxt = [r for r in same if r["a"] > hi]
        prv = [r for r in same if r["b"] < lo]
        f = min(nxt, key=lambda r: r["a"]) if nxt else None
        p = max(prv, key=lambda r: r["b"]) if prv else None
        if f and (not p or f["a"] - hi <= lo - p["b"]):
            return f, f"뒤 덩어리 (줄 {f['a']}~{f['b']}, {f['a'] - hi}줄 뒤)"
        if p:
            return p, f"앞 덩어리 (줄 {p['a']}~{p['b']}, {lo - p['b']}줄 앞)"
        return None, f"{sec} 에 PD 나레이션 없음"

    v2, pos, stopped, rows = [], {}, set(), []
    print("\n 컷 타임라인   길이   대본줄    PD 시작~끝       근거")
    for c in cuts:
        at, dur = c["at_f"] / fps, c["n"] / fps
        r, why = anchor(c)
        rng = f"{min(c['idx'])}~{max(c['idx'])}" if c["idx"] else "-"
        row = {"k": c["k"], "at": round(at, 2), "dur": round(dur, 2), "lines": rng, "why": why}
        if r is None:
            print(f"{c['k']:3d} {at:7.2f} {dur:6.2f}  {rng:>7}   얼굴                 {why}")
            rows.append(row)
            continue
        key = (r["a"], r["b"])
        if key in stopped:
            why = "화면 전환에서 멈춘 덩어리"
            print(f"{c['k']:3d} {at:7.2f} {dur:6.2f}  {rng:>7}   얼굴                 {why}")
            rows.append(dict(row, why=why))
            continue
        pin_f = pos.get(key, frames(r["t"]))
        pin_f = min(pin_f, frames(pd_dur) - c["n"])
        pout_f = pin_f + c["n"]
        cross = [x for x in chg if pin_f / fps < x <= pout_f / fps]
        if cross:
            stopped.add(key)
            why = f"{why} — PD {pin_f/fps:.1f}~{pout_f/fps:.1f} 가 {cross[0]}초 화면 전환을 넘음"
            print(f"{c['k']:3d} {at:7.2f} {dur:6.2f}  {rng:>7}   얼굴                 {why}")
            rows.append(dict(row, why=why))
            continue
        v2.append({"src": "PD", "in": pin_f / fps, "out": pout_f / fps, "track": 2,
                   "at": c["at_f"] / fps, "audio": False, "label": f"PD {c['k']:02d}"})
        rows.append(dict(row, pd_in=round(pin_f / fps, 2), pd_out=round(pout_f / fps, 2)))
        print(f"{c['k']:3d} {at:7.2f} {dur:6.2f}  {rng:>7}   {pin_f/fps:7.2f}~{pout_f/fps:7.2f}   {why}")
        pos[key] = pout_f

    spec2 = dict(spec)
    spec2["name"] = spec["name"] + "_PD"
    spec2["sources"] = {"PD": {"path": os.path.abspath(a.pd_src), "dur": pd_dur}}
    spec2["cuts"] = list(spec["cuts"]) + v2
    json.dump(spec2, io.open(os.path.join(a.cam, "cuts_pd.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(rows, io.open(os.path.join(a.pd, "overlay.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    cover = sum(x["out"] - x["in"] for x in v2)
    print(f"\nV2 클립 {len(v2)}개 · 덮는 길이 {cover:.1f}초 / {sum(c['n'] for c in cuts)/fps:.1f}초"
          f"\n→ {os.path.join(a.cam, 'cuts_pd.json')}")


if __name__ == "__main__":
    main()
