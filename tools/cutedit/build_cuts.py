# -*- coding: utf-8 -*-
"""aligned.json → 컷리스트 + 편별 내레이션(wav/mp3) + 참고영상(mp4) + 자막(srt).

srt 텍스트는 대본 표기를 따르고(STT 오인식 배제), 낭독자가 의도적으로 바꾼
문구 하나만 음성을 따른다(짧게 실현합니다 → 짧게 수익 실현합니다).
"""
import json, re, subprocess, sys
import imageio_ffmpeg

S = "/tmp/claude-0/-home-user-AC-Stock-/2aa738bb-430f-52e0-bfd6-c6b618c5db6c/scratchpad"
FF = imageio_ffmpeg.get_ffmpeg_exe()
CAM = f"{S}/cam.mp4"
PAD_PRE, PAD_POST, MERGE_GAP = 0.12, 0.20, 0.7

aligned = json.load(open(f"{S}/aligned.json", encoding="utf-8"))

# ── 무음 실측(ffmpeg silencedetect -35dB, 0.8s+)으로 STT 단어 시각 보정 ──
# whisper 가 단어 안에 침묵을 삼키는 경우가 있다 (예: '누워버리면' 88.16~92.38).
SILENCES = [(0.39,1.35),(2.22,3.22),(6.30,7.93),(7.94,9.39),(9.73,10.97),(37.78,39.31),
            (56.69,57.60),(60.02,60.89),(67.24,69.06),(69.42,74.09),(74.60,76.54),
            (89.40,90.56),(100.52,101.98),(113.20,115.52),(130.79,131.98),(138.18,139.27),
            (147.75,148.85),(156.60,157.89),(167.63,169.59),(179.34,181.54),(181.74,183.65),
            (183.99,185.15),(196.77,197.83),(199.68,200.58),(207.31,208.18),(210.68,211.77),
            (213.77,215.39),(223.98,224.88),(234.92,235.79),(245.40,246.46),(251.85,252.78),
            (258.67,259.54),(266.09,267.91)]

def fix_word(w):
    s, e = w["s"], w["e"]
    for s0, e0 in SILENCES:
        if s <= s0 < e - 0.05:   # 단어 꼬리가 침묵을 물었다
            e = s0
        if s < e0 <= e - 0.05 and s0 <= s + 0.05:  # 단어 머리가 침묵을 물었다
            s = e0
    w["s"], w["e"] = round(s, 3), round(e, 3)
    return w

for ep in aligned:
    for row in ep["rows"]:
        if row.get("words"):
            row["words"] = [fix_word(dict(w)) for w in row["words"]]
            row["s"], row["e"] = row["words"][0]["s"], row["words"][-1]["e"]

# ── 오버라이드: #11-5 익절 문장 — 마지막 테이크가 문구를 바꿔 두 조각이다 ──
ep5 = aligned[1]
for i, r in enumerate(ep5["rows"]):
    if r["script"].startswith("익절은 상단"):
        base_words = r["words"]
        r_new = {
            "script": "익절은 상단 저항까지 노리되, 직전 양봉을 덮는 장대 음봉이 나오면 욕심 없이 짧게 수익 실현합니다.",
            "heard": "(이어붙임) 익절은 … 나오면 + 욕심없이 짧게 수익 실현합니다",
            "sim": 1.0,
            "spans": [(148.39, 153.27), (157.80, 160.46)],
            "words": None,  # 조각별로 아래에서 구성
        }
        ep5["rows"][i] = r_new

# 대본 표기 정정본 (srt 용): script 그대로 쓰되 낭독 안 된 괄호 제거는 이미 됨

def spans_of(row):
    if row.get("spans"):
        return row["spans"]
    words = row.get("words")
    if not words:
        return [(row["s"], row["e"])]
    # 행 안에서 1.2초 넘는 공백(보정된 단어 시각 기준)은 잘라낸다
    out, start, prev_e = [], words[0]["s"], words[0]["e"]
    for w in words[1:]:
        if w["s"] - prev_e > 1.2:
            out.append((start, prev_e))
            start = w["s"]
        prev_e = w["e"]
    out.append((start, prev_e))
    return out

def fmt_tc(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

def cue_chunks(sentence):
    """대본 문장 → 자막 큐 조각 (기존 srt 실측: 큐당 8~12자, 2~4어절)."""
    words = sentence.replace(",", ",†").split()  # 쉼표 뒤는 끊기 좋은 자리
    chunks, cur = [], ""
    for w in words:
        w_clean = w.replace("†", "")
        cand = (cur + " " + w_clean).strip()
        if cur and len(re.sub(r"\s", "", cand)) > 12:
            chunks.append(cur)
            cur = w_clean
        else:
            cur = cand
        if w.endswith("†") and cur:
            chunks.append(cur); cur = ""
    if cur:
        chunks.append(cur)
    return [re.sub(r"[.,]$", "", c).strip() for c in chunks if c.strip()]

FPS30 = 30.0
results = {}
for ep in aligned[:2]:  # SL 두 편만
    tag = "차11-4" if "추세" in ep["title"] else "차11-5"
    rows = ep["rows"]
    # 1) 소스 스팬 나열 (행 → 조각들)
    raw = []
    for row in rows:
        for (a, b) in spans_of(row):
            raw.append([a, b, row])
    raw.sort(key=lambda x: x[0])
    # 2) 패딩 + 병합 — 패딩이 잘려나갈 이웃 테이크의 단어를 물지 않게 클램프
    all_words = sorted(
        [(w["s"], w["e"]) for sg in json.load(open(f"{S}/cam_transcript.json", encoding="utf-8")) for w in sg["words"]])
    def clamp(a_raw, b_raw):
        a2, b2 = a_raw - PAD_PRE, b_raw + PAD_POST
        prev_end = max((we for ws, we in all_words if we <= a_raw + 0.01), default=0.0)
        next_start = min((ws for ws, we in all_words if ws >= b_raw - 0.01), default=1e9)
        if prev_end < a_raw - 0.01:
            a2 = max(a2, prev_end + 0.02)
        else:
            a2 = a_raw
        if next_start > b_raw + 0.01:
            b2 = min(b2, next_start - 0.02)
        else:
            b2 = b_raw
        return a2, b2
    spans = []
    for a, b, row in raw:
        a2, b2 = clamp(a, b)
        if spans and a2 - spans[-1][1] < MERGE_GAP:
            spans[-1][1] = b2
        else:
            spans.append([a2, b2])
    # 3) 출력 타임라인 매핑
    def to_out(t_src):
        acc = 0.0
        for a, b in spans:
            if t_src <= b + 1e-6:
                return acc + max(0.0, t_src - a)
            acc += b - a
        return acc
    total = sum(b - a for a, b in spans)
    # 4) srt 큐: 행별 대본 문장을 조각으로 나누고 STT 단어 경계에 스냅
    cues = []
    for row in rows:
        row_spans = spans_of(row)
        script_txt = row["script"].replace("알려드릴게요 ", "알려드릴게요. ")
        sents = re.split(r"(?<=[.?!])\s+", script_txt)
        sents = [s for s in sents if re.sub(r"\W", "", s)]
        all_chunks = []
        for sent in sents:
            all_chunks += cue_chunks(sent)
        n_chars = sum(len(re.sub(r"\s", "", c)) for c in all_chunks)
        words = row.get("words")
        if words:
            wl = [(w["s"], w["e"], len(re.sub(r"[^0-9가-힣a-zA-Z]", "", w["w"]))) for w in words]
            total_w = sum(n for _, _, n in wl) or 1
            bounds = [wl[0][0]]  # 누적 글자수 → 단어 경계 시각
            cum = 0
            cum_targets = []
            c_acc = 0
            for c in all_chunks:
                c_acc += len(re.sub(r"\s", "", c))
                cum_targets.append(c_acc / n_chars * total_w)
            wi, cum = 0, 0
            times = []
            for tgt in cum_targets:
                while wi < len(wl) and cum + wl[wi][2] <= tgt + 1e-9:
                    cum += wl[wi][2]; wi += 1
                # tgt 는 wl[wi] 중간이거나 경계 — 가까운 쪽 경계로
                if wi >= len(wl):
                    times.append(wl[-1][1])
                elif tgt - cum < wl[wi][2] / 2:
                    times.append(wl[wi][0])
                else:
                    cum += wl[wi][2]; wi += 1
                    times.append(wl[wi - 1][1])
            times[-1] = wl[-1][1]
            prev = wl[0][0]
            for c, t in zip(all_chunks, times):
                t = max(t, prev + 0.15)  # 0 길이 방지
                cues.append({"text": c, "s_out": to_out(prev), "e_out": to_out(t)})
                prev = t
        else:
            # 오버라이드 행: 조각 이어붙인 가상 타임라인에 글자 비례 배치
            seg_lens = [b - a for a, b in row_spans]
            row_dur = sum(seg_lens)
            def virt_to_src(v):
                for (a, b), L in zip(row_spans, seg_lens):
                    if v <= L + 1e-9:
                        return a + v
                    v -= L
                return row_spans[-1][1]
            v = 0.0
            for c in all_chunks:
                dur = row_dur * len(re.sub(r"\s", "", c)) / n_chars
                cues.append({"text": c, "s_out": to_out(virt_to_src(v)), "e_out": to_out(virt_to_src(min(v + dur, row_dur)))})
                v += dur
    # 버트조인: 다음 큐와 0.5초 미만이면 붙인다
    for i in range(len(cues) - 1):
        if cues[i + 1]["s_out"] - cues[i]["e_out"] < 0.5:
            cues[i]["e_out"] = cues[i + 1]["s_out"]
    # 5) 파일 출력
    srt = []
    for i, c in enumerate(cues, 1):
        srt.append(f"{i}\n{fmt_tc(c['s_out'])} --> {fmt_tc(c['e_out'])}\n{c['text']}\n")
    open(f"{S}/out_{tag}.srt", "w", encoding="utf-8-sig").write("\n".join(srt))
    # 컷리스트
    lst = [f"# {ep['title']} — 컷리스트 (원본: 20260828_CAM 파일.mp4, 초 단위)",
           f"# 총 {len(spans)}스팬, 출력 길이 {total:.2f}초"]
    for a, b in spans:
        lst.append(f"원본 {a:8.2f} ~ {b:8.2f}  ({b-a:6.2f}s)  → 출력 {to_out(a+0.001):7.2f} ~ {to_out(b-0.001):7.2f}")
    open(f"{S}/out_{tag}_컷리스트.txt", "w", encoding="utf-8").write("\n".join(lst) + "\n")
    # ffmpeg: 오디오(원본 48k 스테레오) + 영상(h264 재인코딩)
    fc_parts, an, vn = [], [], []
    for i, (a, b) in enumerate(spans):
        fc_parts.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}];")
        fc_parts.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}];")
        vn.append(f"[v{i}]"); an.append(f"[a{i}]")
    fc = "".join(fc_parts) + "".join(v + a for v, a in zip(vn, an)) + f"concat=n={len(spans)}:v=1:a=1[v][a]"
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", CAM,
                    "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "256k", f"{S}/out_{tag}_컷편집영상(참고).mp4"], check=True)
    fca = "".join(p for p in fc_parts if "[0:a]" in p) + "".join(an) + f"concat=n={len(spans)}:v=0:a=1[a]"
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", CAM,
                    "-filter_complex", fca, "-map", "[a]", f"{S}/out_{tag}_내레이션.wav"], check=True)
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", f"{S}/out_{tag}_내레이션.wav",
                    "-b:a", "320k", f"{S}/out_{tag}_내레이션.mp3"], check=True)
    results[tag] = {"spans": spans, "dur": total, "cues": len(cues)}
    print(f"{tag}: {len(spans)}스팬 {total:.2f}초, 큐 {len(cues)}개")

json.dump(results, open(f"{S}/cut_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done")
