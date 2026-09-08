# -*- coding: utf-8 -*-
"""대본과 낭독이 갈린 자리만 큰 모델로 다시 듣는다.

숏폼 낭독자는 대본을 그대로 읽지 않는다. 어미를 바꾸고('아니잖아요'→'아닙니다'),
조사를 넣고('생각합니다'→'생각을 합니다'), 접미를 붙인다('불안'→'불안함').
이건 자막에 그대로 실어야 싱크가 맞다. 반면 STT 오인식('휘두르진'→'휘돌이진')은
자막에 실으면 안 된다.

**확신도로는 이 둘이 안 갈린다.** S015 실측 — 오인식 '휘돌이진'이 0.99,
진짜 바뀐 '보고'가 0.77 이었다. 문턱을 어디에 두든 한쪽이 틀린다.

갈리는 것은 모델 크기다. 갈린 7곳을 large-v3 로 다시 들으니 7곳 다 맞았다 —
오인식은 제 모습을 찾고('휘두르지는', '놓칠까봐 라면') 진짜 변경은 그대로 남는다.
medium 은 정렬용(빠르고 시각이 정확)으로 두고, 갈린 구간만 large 로 확인한다.
S015 기준 7구간에 147초(모델 적재 70초 포함).

    python3 tools/cutedit/verify_text.py <작업폴더> [--model large-v3]
      입력  <작업폴더>/aligned.json · cam_transcript.json · cam16k.wav
      출력  <작업폴더>/verified.json   (cut_and_srt.py 가 있으면 자동으로 쓴다)
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
from difflib import SequenceMatcher

PAD = 0.35          # 구간 앞뒤로 이만큼 더 들려준다 (끝 낱말이 잘리지 않게)
SAME = 0.995        # 정규화해서 이 이상 같으면 '대본대로 읽은 것'
SWAP_MAX = 3        # 이 길이까지의 '같은 길이 치환' 은 오인식으로 본다


def norm(t):
    return re.sub(r"[^0-9가-힣a-zA-Z]", "", t)


def heard_of(tr, a, b):
    ws = [w for seg in tr for w in (seg.get("words") or [])
          if a - 0.05 <= w["s"] and w["e"] <= b + 0.05]
    return " ".join(w["w"].strip() for w in ws).strip()


def trim_to(heard, script):
    """받아쓴 말에서 대본 한 줄에 해당하는 구간만 남긴다.

    앞뒤를 더 들려준 대가로 옆 문장 낱말이 붙어 온다. 낱말 단위로 창을 옮겨
    가며 대본을 가장 많이 덮는 구간을 고른다.

    점수를 그냥 닮은 정도로 매기면 안 된다 — 끝 낱말이 오인식된 경우
    ('숏이든'→'쇼시든') 그 낱말을 **버리는 쪽**이 더 닮아 보여서 통째로
    잘려 나간다. 그래서 '대본을 얼마나 덮었나'를 보고, 남는 군더더기에만
    가벼운 벌점을 준다.
    """
    ws = heard.split()
    if len(ws) < 2:
        return heard
    t, best = norm(script), None
    for i in range(len(ws)):
        for j in range(i + 1, len(ws) + 1):
            w = norm(" ".join(ws[i:j]))
            m = sum(b.size for b in SequenceMatcher(None, t, w).get_matching_blocks())
            score = (m - 0.3 * (len(w) - m)) / max(1, len(t))
            if best is None or score > best[0]:
                best = (score, i, j)
    return " ".join(ws[best[1]:best[2]])


def only_swaps(script, heard):
    """다른 곳이 전부 **한 글자 대 한 글자** 바뀜인가?

    한글 STT 오인식은 음절 하나가 비슷한 소리로 바뀐다 —
        일목→일모 · 반등→방등 · 지지→기지 · 구름대→구름때 · 숏이→쇼시
    반면 낭독자가 진짜로 바꾼 것은 글자를 **넣거나 빼거나** 어미를 통째로 간다 —
        불안→불안함 · 나오면→나온다면 · 생각합니다→생각을 합니다 · 아니잖아요→아닙니다

    그래서 차이가 **길이가 같은 짧은 치환**뿐이면 오인식으로 보고 대본을 쓴다.
    글자 수가 그대로라는 게 핵심이다 — 소리는 같고 글자만 잘못 붙은 것이니까.
    ('숏이'→'쇼시' 처럼 두 음절이 한 덩어리로 바뀌기도 해서 1:1 로만 보면 놓친다.)

    S015·S016 두 편에서 갈린 13곳 중 12곳이 이 규칙으로 맞았다. 틀린 하나는
    '휘두르진'→'휘두르지는'(글자 삽입)인데 뜻이 같아 크게 문제되지 않는다.
    """
    a, b = norm(script), norm(heard)
    if a == b:
        return True
    ops = [o for o in SequenceMatcher(None, a, b).get_opcodes() if o[0] != "equal"]
    if not ops:
        return True
    return all(o[0] == "replace" and o[2] - o[1] == o[4] - o[3] <= SWAP_MAX
               for o in ops)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--model", default="large-v3")
    a = ap.parse_args()
    S = a.dir

    rows = [r for r in json.load(io.open(f"{S}/aligned.json", encoding="utf-8"))
            if r["s"] is not None]
    tr = json.load(io.open(f"{S}/cam_transcript.json", encoding="utf-8"))
    # 사람이 손으로 정한 것이 제일 세다. {"9": "야구도 ... 휘두르진 않습니다"}
    fix = {}
    if os.path.exists(f"{S}/text_fix.json"):
        fix = json.load(io.open(f"{S}/text_fix.json", encoding="utf-8"))

    todo = []
    for r in rows:
        h = heard_of(tr, r["s"], r["e"])
        if h and SequenceMatcher(None, norm(r["text"]), norm(h)).ratio() < SAME:
            todo.append((r, h))
    print(f"대본과 갈린 곳 {len(todo)}개 — {a.model} 로 다시 듣는다", flush=True)
    if not todo:
        json.dump({}, io.open(f"{S}/verified.json", "w", encoding="utf-8"))
        return

    import imageio_ffmpeg
    from faster_whisper import WhisperModel
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    m = WhisperModel(a.model, device="cpu", compute_type="int8", cpu_threads=4)

    out = {}
    for r, h in todo:
        # 앞뒤를 조금 더 들려준다. 딱 잘라 무음으로 채우면 끝 낱말이 뭉개진다
        # ('숏이든'→'논의…', '나오면'→'나온다'). 대신 받아쓴 뒤 대본에 해당하는
        # 구간만 남긴다 — 안 그러면 옆 문장 낱말이 붙어 온다('계좌를','어쨌든').
        subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error",
                        "-i", f"{S}/cam16k.wav", "-ss", str(max(0, r["s"] - PAD)),
                        "-to", str(r["e"] + PAD), f"{S}/_span.wav"], check=True)
        segs, _ = m.transcribe(f"{S}/_span.wav", language="ko",
                               vad_filter=False, beam_size=5)
        big = trim_to(" ".join(x.text.strip() for x in segs).strip(), r["text"])

        # 정규화해서 대본과 같으면 = 대본대로 읽은 것. 표기는 대본을 쓴다
        # (띄어쓰기·구두점까지 대본이 진본이다: '놓칠까봐 라면' → '놓칠까 봐”라면').
        if SequenceMatcher(None, norm(r["text"]), norm(big)).ratio() >= SAME:
            use, why = r["text"], "대본대로 읽음 (STT 오인식이었음)"
        elif only_swaps(r["text"], big):
            use, why = r["text"], "한 음절씩만 바뀜 = STT 오인식 → 대본"
        else:
            tail = "".join(re.findall(r"[?!”\"']+$", r["text"].strip()) or [""])
            use, why = big.rstrip(" .,!?") + tail, "낭독이 대본과 다름 — 낭독을 따름"
        if str(r["i"]) in fix:
            use, why = fix[str(r["i"])], "text_fix.json — 사람이 정함"
        out[str(r["i"])] = {"script": r["text"], "medium": h, "large": big,
                            "use": use, "why": why}
        print(f"\n{r['i']:3d} 대본   {r['text']}\n    medium {h}\n    {a.model:<7}{big}"
              f"\n    자막   {use}   ← {why}", flush=True)

    if os.path.exists(f"{S}/_span.wav"):
        os.remove(f"{S}/_span.wav")
    json.dump(out, io.open(f"{S}/verified.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # 사람이 훑을 목록. 뒤집을 게 있으면 text_fix.json 에 번호와 문구를 적는다.
    rv = ["대본과 낭독이 갈린 곳 — 자막에 쓴 문구를 확인하세요.",
          "뒤집으려면 같은 폴더에 text_fix.json 을 만들고 {\"번호\": \"쓸 문구\"} 로 적은 뒤",
          "verify_text.py 를 다시 돌리면 됩니다.", ""]
    for k, v in out.items():
        rv += [f"[{k}] {v['why']}",
               f"   대본   {v['script']}",
               f"   medium {v['medium']}",
               f"   large  {v['large']}",
               f"   자막   {v['use']}", ""]
    io.open(f"{S}/자막_검수.txt", "w", encoding="utf-8",
            newline="\n").write("\n".join(rv))
    n = sum(1 for v in out.values() if v["use"] != v["script"])
    print(f"\n{len(out)}곳 확인 · 낭독을 따른 것 {n}곳 · 대본으로 되돌린 것 {len(out)-n}곳"
          f"\n→ {S}/verified.json")


if __name__ == "__main__":
    main()
