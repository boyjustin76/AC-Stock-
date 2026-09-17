# -*- coding: utf-8 -*-
"""녹음에서 무음 구간을 뽑는다. 문턱은 그 녹음의 잡음 바닥에서 정한다.

기본 문턱은 **-30dB** 다. S015 수정본(사람이 손으로 고친 컷 12개)에 맞춰
검증한 값이고, 그 조건에서 경계 평균오차가 0.057초였다.

바닥에서 자동으로 잡아 보려 했지만 근거가 없었다 — 두 녹음의 음량 분포가
거의 같은 모양이고(S016 이 일괄 2dB 낮을 뿐) S015 에 자동값(-36.7dB)을 쓰면
컷이 12개에서 9개로 무너진다. 그래서 바닥은 **참고로 찍어만 주고**, 문턱은
검증값을 쓰되 필요하면 --db 로 바꾼다. 고를 때는 make_cuts 의 '말 가운데를
자르는 경계' 수를 보면 된다.

두 벌을 만든다 (cut_and_srt.py 가 둘 다 쓴다) —
  silences.txt       0.30초+  컷을 끊을지 판단
  silences_fine.txt  0.12초+  컷 경계를 붙일 자리

    python3 tools/cutedit/silences.py <작업폴더>
      입력  <작업폴더>/cam16k.wav
"""
import argparse
import io
import os
import re
import subprocess
import sys

WIN = 0.20          # 음량을 재는 창 길이
DEFAULT_DB = -30.0  # S015 수정본으로 검증한 값
FLOOR_PCT = 10      # 바닥을 볼 때 쓰는 퍼센타일 (참고용)


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def levels(ff, wav):
    """창 단위 RMS(dB) 목록 — astats 로 한 번에 뽑는다."""
    p = subprocess.run(
        [ff, "-hide_banner", "-nostats", "-i", wav,
         "-af", f"astats=metadata=1:reset={max(1, int(WIN * 50))},"
                f"ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
         "-f", "null", "-"],
        capture_output=True, text=True, errors="replace")
    out = []
    for m in re.finditer(r"RMS_level=(-?[\d.]+|-inf)", p.stdout):
        v = m.group(1)
        out.append(-120.0 if v == "-inf" else float(v))
    return out


def noise_floor(ff, wav):
    v = sorted(x for x in levels(ff, wav) if x > -119)
    if not v:
        return -40.0
    return v[max(0, len(v) * FLOOR_PCT // 100 - 1)]


def detect(ff, wav, db, dur, path):
    p = subprocess.run(
        [ff, "-hide_banner", "-nostats", "-i", wav,
         "-af", f"silencedetect=noise={db:.1f}dB:d={dur}", "-f", "null", "-"],
        capture_output=True, text=True, errors="replace")
    lines = [l for l in (p.stderr or "").splitlines()
             if "silence_start" in l or "silence_end" in l]
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return sum(1 for l in lines if "silence_start" in l)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--db", type=float, default=None, help="문턱을 손으로 정할 때")
    a = ap.parse_args()
    S = a.dir
    wav = f"{S}/cam16k.wav"
    if not os.path.exists(wav):
        sys.exit(f"{wav} 가 없습니다.")
    ff = ffmpeg()

    db = DEFAULT_DB if a.db is None else a.db
    print(f"잡음 바닥 {noise_floor(ff, wav):.1f}dB (참고) · 문턱 {db:.1f}dB")

    n1 = detect(ff, wav, db, 0.30, f"{S}/silences.txt")
    n2 = detect(ff, wav, db, 0.12, f"{S}/silences_fine.txt")
    print(f"무음 {n1}구간 (0.30초+) · {n2}구간 (0.12초+)")


if __name__ == "__main__":
    main()
