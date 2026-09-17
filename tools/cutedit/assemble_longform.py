# -*- coding: utf-8 -*-
"""롱폼 합본 — 캠 컷(형광 줄) + PD 설명 녹화 나레이션(일반 줄)을 대본 순서로 잇는다.

롱폼 촬영은 두 번이다 (L08 확인).
  캠 녹화        카메라 보고 읽는 형광 줄. 얼굴 영상 + 소리를 그대로 쓴다.
  PD 설명 녹화   차트 화면 녹화. 일반 줄을 **읽고**, 바로 이어서 그 내용을 차트로 **시연**한다.
                 → 읽는 부분은 **소리만**, 읽기가 끝난 직후부터 다음 읽기 전까지가 그 부분의 **화면**.

그래서 합본 시퀀스는 —
  V1   캠 컷(영상+소리 링크) · 나레이션 자리에는 시연 화면(영상만)
  A1·A2 캠 소리 · PD 나레이션 소리(소리만)
  V2~  포인터 시연이 모자란 덩어리만, 시연 구간 전체를 **꺼 둔 클립**으로 (골라 쓸 참고)
       시연 전체는 나레이션보다 길어서 서로 겹치면 V3 으로 올린다 — 한 트랙 안에서 겹치면 프리미어가 잘라 읽는다.
  XML 은 트랙마다 클립을 시작 순서로 적는다 (make_xml) — 뒤섞이면 프리미어에서 클립이 사라지고 깜빡인다.

나레이션 덩어리 — 시간순으로 이어진 PD 나레이션 줄. 줄 사이가 BLOCK_GAP 을 넘으면 다음 덩어리.
  L08 줄 간격은 0~8.8초(재녹음·숨)와 36.5초 이상(시연) 두 무리뿐이라 20초에서 가른다.

시연 화면 고르기 (이정찬 지시 2026-09-11 — '마우스 포인터(연필) 움직임에 맞춰, 어려우면 시연 전체를 V2') —
  포인터 프레임  5fps 차분에서 작고(≤250화소) 뭉친(≤60화소 폭·높이) 변화, 작업표시줄·가격축만 바뀐 것 제외.
                 L08 검증: 짚으며 설명하는 구간 76~88% · 나레이션 읽는 중 6%.
  포인터 구간    포인터 프레임을 1초 틈까지 잇고 앞뒤 0.2초 여유. **2초 이상 · 밀도 0.5 이상**만 후보.
                 (짧고 성긴 것은 PD 와 대화하며 커서를 만지작거린 것이다)
  채우기         후보를 밀도 높은 순으로 통째로 담고 넘친 만큼은 **가장 긴 구간** 끝에서 깎아 딱 맞춘 뒤
                 시간순으로. 80% 이상 차면 고른 구간을 앞뒤로 한쪽 1초까지 넓혀 메운다.
  모자라면       V1 은 시연 구간 머리부터 나레이션 길이만큼, V2 에 시연 전체(꺼 둠).
  움직임 파일    --motion 경로에 없으면 PD 영상을 5fps 480×270 으로 훑어 만들고 남긴다(28분에 수 분).

자막 — 두 녹음의 문장을 각자 cut_and_srt 와 같은 규칙(낭독 문구·text_fix·21자·짧은 조각 벌점·당김)으로
만든 뒤 합본 타임라인에 옮긴다.

    python3 tools/cutedit/assemble_longform.py <캠폴더> <PD폴더> <대본.txt> --pd-src <PD에게 설명.mp4> \\
            --motion <pd_motion5fps.json> --name <시퀀스이름> --out <결과폴더>
      입력  캠폴더·PD폴더 각각 aligned.json · cam_transcript.json · cuts.json (cut_and_srt --long 산출)
            (verified.json · text_fix.json 있으면 쓴다)
      출력  결과폴더/assembled.json (make_xml 입력) · assembled.srt · assemble_report.json
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from align_take import FIRM, read_script                                  # noqa: E402
from cut_and_srt import LEAD, fix_terms, fmt, norm, spoken_text, words_between  # noqa: E402
from srt_rules import LONG_MAX_LEN, LONG_MIN_LEN, split_cue               # noqa: E402

BLOCK_GAP = 20.0
PTR_MAX_N, PTR_MAX_BOX = 250, 60
PTR_BOTTOM_Y, PTR_AXIS_X = 250, 440      # 480×270 기준 — 작업표시줄 줄 · 가격축
SEG_GAP, SEG_PAD = 1.0, 0.2
SEG_MIN, SEG_DENS = 2.0, 0.5


def duration(src):
    import imageio_ffmpeg
    p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", src],
                       capture_output=True, text=True, errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", p.stderr or "")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def load_side(d):
    rows = [r for r in json.load(io.open(os.path.join(d, "aligned.json"), encoding="utf-8"))
            if r["s"] is not None and (r["score"] or 0) >= FIRM]
    tr = json.load(io.open(os.path.join(d, "cam_transcript.json"), encoding="utf-8"))
    spec = json.load(io.open(os.path.join(d, "cuts.json"), encoding="utf-8"))
    vf = {}
    if os.path.exists(os.path.join(d, "verified.json")):
        vf = json.load(io.open(os.path.join(d, "verified.json"), encoding="utf-8"))
    if os.path.exists(os.path.join(d, "text_fix.json")):
        for k, v in json.load(io.open(os.path.join(d, "text_fix.json"), encoding="utf-8")).items():
            vf.setdefault(k, {})["use"] = v
    return rows, tr, spec, vf


def measure_motion(src, path):
    """5fps 480×270 회색조 — 프레임마다 앞 프레임과 달라진 화소 수·범위·중앙 위치."""
    import imageio_ffmpeg
    import numpy as np
    W, H, FPS = 480, 270, 5
    p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
                          "-threads", "2", "-i", src, "-vf", f"fps={FPS},scale={W}:{H}",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    fs, prev, rows, k = W * H, None, [], 0
    while True:
        b = p.stdout.read(fs)
        if len(b) < fs:
            break
        a = np.frombuffer(b, dtype=np.uint8).astype(np.int16).reshape(H, W)
        if prev is not None:
            m = np.abs(a - prev) > 28
            n = int(m.sum())
            if n:
                ys, xs = np.nonzero(m)
                rows.append([round(k / FPS, 2), n, int(xs.min()), int(xs.max()), int(ys.min()),
                             int(ys.max()), float(np.median(xs)), float(np.median(ys))])
            else:
                rows.append([round(k / FPS, 2), 0, -1, -1, -1, -1, -1, -1])
        prev = a
        k += 1
    out = {"fps": FPS, "w": W, "h": H, "rows": rows}
    json.dump(out, open(path, "w"))
    return out


def pointer_segments(motion, a, b):
    fps = motion["fps"]
    ts = []
    for t, n, x0, x1, y0, y1, _, _ in motion["rows"]:
        if not (a <= t < b) or n <= 0 or n > PTR_MAX_N:
            continue
        if x1 - x0 > PTR_MAX_BOX or y1 - y0 > PTR_MAX_BOX or y0 >= PTR_BOTTOM_Y or x0 >= PTR_AXIS_X:
            continue
        ts.append(t)
    raw = []
    for t in ts:
        if raw and t - raw[-1][1] <= SEG_GAP:
            raw[-1][1] = t
        else:
            raw.append([t, t])
    out = []
    for s, e in raw:
        cnt = sum(1 for x in ts if s <= x <= e)
        s, e = max(a, s - SEG_PAD), min(b, e + SEG_PAD)
        if e - s >= SEG_MIN and cnt / ((e - s) * fps) >= SEG_DENS:
            out.append((s, e, cnt / ((e - s) * fps)))
    return out


# 포인터가 거의 채우면(나레이션의 80% 이상) 고른 구간을 앞뒤로 넓혀 메운다. 한쪽 최대 1초.
# L08: 13~19줄 36.2/37.0초(98%)는 0.8초 모자라 통째로 버리기 아깝고, 21~26줄 16.2/23.9초(68%)는
# 정말 모자라다. 70~97% 어디에 둬도 두 덩어리 판정이 같다.
PAD_FILL, PAD_MAX = 0.8, 1.0


def fill(segs, need_f, lo_f, hi_f, frames):
    """포인터 구간으로 나레이션 길이(프레임)를 딱 채운다. 못 채우면 (None, 이유)."""
    cand = sorted([[frames(s), frames(e), d] for s, e, d in segs], key=lambda x: -x[2])
    pick, got = [], 0
    for c in cand:                               # 밀도 높은 순으로 통째로 담는다
        if got >= need_f:
            break
        pick.append(c)
        got += c[1] - c[0]
    pick.sort(key=lambda x: x[0])
    mode = "포인터"
    if got < need_f:
        if got < PAD_FILL * need_f:
            return None, "모자람"
        step = frames(PAD_MAX)
        for k in sorted(range(len(pick)), key=lambda j: -pick[j][2]):
            if got >= need_f:
                break
            left = pick[k - 1][1] if k > 0 else lo_f
            right = pick[k + 1][0] if k + 1 < len(pick) else hi_f
            add = min(step, right - pick[k][1], need_f - got)
            pick[k][1] += add
            got += add
            add = min(step, pick[k][0] - left, need_f - got)
            pick[k][0] -= add
            got += add
        if got < need_f:
            return None, "모자람"
        mode = "포인터 + 앞뒤 여유"
    # 넘친 만큼은 **가장 긴 구간** 끝에서 깎는다 — 마지막 구간을 깎으면 1초도 안 되는 조각이 생긴다
    excess = got - need_f
    while excess > 0:
        k = max(range(len(pick)), key=lambda j: pick[j][1] - pick[j][0])
        cut = min(excess, max(1, pick[k][1] - pick[k][0] - frames(SEG_MIN)))
        pick[k][1] -= cut
        excess -= cut
    return [tuple(p) for p in pick], mode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cam")
    ap.add_argument("pd")
    ap.add_argument("script")
    ap.add_argument("--pd-src", required=True)
    ap.add_argument("--motion", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    lines = read_script(a.script)
    cam_rows, cam_tr, cam_spec, cam_vf = load_side(a.cam)
    pd_rows, pd_tr, pd_spec, pd_vf = load_side(a.pd)
    fps = float(cam_spec.get("fps", 29.97))
    motion = (json.load(io.open(a.motion, encoding="utf-8")) if os.path.exists(a.motion)
              else measure_motion(a.pd_src, a.motion))
    pd_dur = duration(a.pd_src)

    def frames(t):
        return int(round(t * fps))

    # ── 컷마다 대본 줄 → 대본 순서로 줄 세우기 ─────────────────────────
    items = []
    for side, spec, rows in (("캠", cam_spec, cam_rows), ("PD", pd_spec, pd_rows)):
        for c in spec["cuts"]:
            idx = [r["i"] for r in rows if min(r["e"], c["out"]) - max(r["s"], c["in"]) > 0.3]
            if not idx:
                raise SystemExit(f"{side} 컷 {c['in']:.2f}~{c['out']:.2f} 에 대본 줄이 없다")
            items.append({"side": side, "cut": c, "idx": idx, "key": (min(idx), c["in"]),
                          "n": frames(c["out"]) - frames(c["in"])})
    items.sort(key=lambda x: x["key"])
    pos = 0
    for it in items:
        it["at_f"] = pos
        pos += it["n"]
    total_f = pos

    # ── PD 나레이션 덩어리 (PD 녹음 시간순) ─────────────────────────────
    pd_sorted = sorted(pd_rows, key=lambda r: r["s"])
    blocks = []
    for r in pd_sorted:
        if blocks and r["s"] - blocks[-1]["read_e"] <= BLOCK_GAP:
            blocks[-1]["read_e"] = r["e"]
            blocks[-1]["lines"].append(r["i"])
        else:
            blocks.append({"read_s": r["s"], "read_e": r["e"], "lines": [r["i"]]})
    for k, bl in enumerate(blocks):
        bl["demo_s"] = bl["read_e"]
        bl["demo_e"] = blocks[k + 1]["read_s"] if k + 1 < len(blocks) else pd_dur
        its = [it for it in items if it["side"] == "PD" and set(it["idx"]) & set(bl["lines"])]
        bl["at_f"] = min(it["at_f"] for it in its)
        bl["end_f"] = max(it["at_f"] + it["n"] for it in its)
        if bl["end_f"] - bl["at_f"] != sum(it["n"] for it in its):
            raise SystemExit(f"덩어리 줄 {bl['lines'][0]}~ 사이에 캠 컷이 끼었다 — 화면을 한 줄로 못 깐다")

    # ── 시퀀스 컷 ─────────────────────────────────────────────────────
    cuts, report = [], []
    upper = {}                   # V2 이상 트랙 → 이미 놓은 (시작, 끝) 프레임

    def free_track(s_f, e_f):
        """시연 전체는 나레이션보다 길어 다음 덩어리 자리까지 덮는다. 겹치지 않는 가장 낮은 V2~ 트랙.
        L08: 21~26줄 시연 전체(108.85초)가 44~46줄 V2 클립과 겹쳐 프리미어가 둘을 잘라 읽었다."""
        t = 2
        while any(s_f < b and a < e_f for a, b in upper.get(t, [])):
            t += 1
        upper.setdefault(t, []).append((s_f, e_f))
        return t
    for it in items:
        c = it["cut"]
        base = {"in": c["in"], "out": c["out"], "at": it["at_f"] / fps, "track": 1,
                "label": f"{it['side']} {c['label'][:18]}"}
        if it["side"] == "캠":
            cuts.append(dict(base, src="캠"))
        else:
            cuts.append(dict(base, src="PD", video=False))
    for bl in blocks:
        need_f = bl["end_f"] - bl["at_f"]
        segs = pointer_segments(motion, bl["demo_s"], bl["demo_e"])
        have_f = sum(frames(e) - frames(s) for s, e, _ in segs)
        rep = {"lines": f"{bl['lines'][0]}~{bl['lines'][-1]}", "read": [round(bl["read_s"], 2), round(bl["read_e"], 2)],
               "demo": [round(bl["demo_s"], 2), round(bl["demo_e"], 2)], "need": round(need_f / fps, 2),
               "pointer": round(have_f / fps, 2), "at": round(bl["at_f"] / fps, 2)}
        pick, mode = fill(segs, need_f, frames(bl["demo_s"]), frames(bl["demo_e"]), frames)
        if pick:
            at = bl["at_f"]
            for s_f, e_f, dens in pick:
                cuts.append({"src": "PD", "in": s_f / fps, "out": e_f / fps, "at": at / fps, "track": 1,
                             "audio": False, "label": f"시연 {bl['lines'][0]}~ 포인터 {dens:.2f}"})
                at += e_f - s_f
            rep.update(mode=mode, clips=[[round(s / fps, 2), round(e / fps, 2)] for s, e, _ in pick])
        else:
            s_f = frames(bl["demo_s"])
            cuts.append({"src": "PD", "in": s_f / fps, "out": (s_f + need_f) / fps, "at": bl["at_f"] / fps,
                         "track": 1, "audio": False, "label": f"시연 {bl['lines'][0]}~ 머리부터"})
            t = free_track(bl["at_f"], bl["at_f"] + frames(bl["demo_e"]) - frames(bl["demo_s"]))
            cuts.append({"src": "PD", "in": bl["demo_s"], "out": bl["demo_e"], "at": bl["at_f"] / fps,
                         "track": t, "audio": False, "enabled": False,
                         "label": f"시연 {bl['lines'][0]}~ 전체(골라 쓰기)"})
            rep.update(mode=f"모자람 → V1 머리부터 · V{t} 전체(꺼 둠)")
        report.append(rep)

    # ── 자막 ──────────────────────────────────────────────────────────
    # 줄의 시작·끝을 **그 줄이 든 컷** 안에서 옮긴다 (컷 밖으로 나간 만큼은 컷 끝에 붙인다).
    # 예전에는 원본 시각으로 '끝이 t 이상인 첫 컷'을 찾았는데, 줄 끝이 컷 OUT 을 조금 넘으면
    # 다음 컷 머리로 튀었다 — L08 캠 12줄 끝이 46초 → 96초로 가서 뒤 큐가 0.2초씩 밀리고
    # 끝이 시작보다 앞선 큐가 생겨 프리미어가 1:41 에서 자막을 끊었다 (2026-09-11).
    def placed(side, r):
        its = sorted((it for it in items if it["side"] == side and r["i"] in it["idx"]),
                     key=lambda x: x["cut"]["in"])

        def at(it, t):
            return (it["at_f"] + min(max(0.0, t * fps - frames(it["cut"]["in"])), it["n"])) / fps
        return at(its[0], r["s"]), at(its[-1], r["e"])

    lines_out = []
    for side, rows, tr, vf in (("캠", cam_rows, cam_tr, cam_vf), ("PD", pd_rows, pd_tr, pd_vf)):
        for r in rows:
            text, _ = spoken_text(r["text"], words_between(tr, r["s"], r["e"]), vf.get(str(r["i"])))
            lines_out.append((*placed(side, r), text))
    lines_out.sort()
    cues = []
    for s0, e0, text in lines_out:
        chunks = [fix_terms(c) for c in split_cue(text, max_len=LONG_MAX_LEN, min_len=LONG_MIN_LEN) if c.strip()]
        chunks = [c for c in chunks if c]
        N = sum(len(norm(c)) for c in chunks) or 1
        acc = 0
        for ch in chunks:
            k = len(norm(ch))
            cs, ce = s0 + (e0 - s0) * acc / N, s0 + (e0 - s0) * (acc + k) / N
            acc += k
            if cues and cs - cues[-1]["e"] < 0.08:
                cs = cues[-1]["e"]
            cues.append({"s": cs, "e": ce, "t": ch})
    for k, c in enumerate(cues):
        s = max(0.0, c["s"] - LEAD)
        if k and cues[k - 1]["e"] > s:
            s = max(s, cues[k - 1]["s"] + 0.2)
            cues[k - 1]["e"] = s
        c["s"] = s

    spec = {"name": a.name, "fps": fps, "width": cam_spec.get("width", 1920),
            "height": cam_spec.get("height", 1080),
            "sources": {"캠": {"path": cam_spec["source"], "dur": cam_spec.get("src_dur", 0)},
                        "PD": {"path": os.path.abspath(a.pd_src), "dur": pd_dur}},
            "cuts": cuts}
    json.dump(spec, io.open(os.path.join(a.out, "assembled.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    io.open(os.path.join(a.out, "assembled.srt"), "w", encoding="utf-8-sig", newline="\n").write(
        "\n".join(f"{i}\n{fmt(c['s'])} --> {fmt(c['e'])}\n{c['t']}\n" for i, c in enumerate(cues, 1)))
    json.dump({"order": [{"side": it["side"], "lines": f"{min(it['idx'])}~{max(it['idx'])}",
                          "at": round(it["at_f"] / fps, 2), "dur": round(it["n"] / fps, 2)} for it in items],
               "blocks": report},
              io.open(os.path.join(a.out, "assemble_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"합본 {len(items)}컷 (캠 {sum(i['side'] == '캠' for i in items)} · PD 나레이션 "
          f"{sum(i['side'] == 'PD' for i in items)}) · 길이 {total_f / fps:.2f}초 · 자막 {len(cues)}큐")
    print("\n나레이션 덩어리 → 시연 화면")
    for r in report:
        print(f"  줄 {r['lines']:>7}  타임라인 {r['at']:7.2f}  나레이션 {r['need']:5.1f}초  "
              f"시연 {r['demo'][0]:.1f}~{r['demo'][1]:.1f}  포인터 {r['pointer']:5.1f}초  → {r['mode']}")
        for cl in r.get("clips", []):
            print(f"      {cl[0]:8.2f}~{cl[1]:8.2f}")


if __name__ == "__main__":
    main()
