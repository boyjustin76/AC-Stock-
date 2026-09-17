# -*- coding: utf-8 -*-
"""최종본 mp4 에서 참고스틸을 뽑고, 여러 시각을 한 장으로 붙여 훑어본다.

카피맵(어느 편 몇 초의 연출을 가져올지)을 쓰려면 화면을 실제로 봐야 한다.
자막만으로는 '무엇을 말했나'만 알 뿐 '어떻게 보였나'를 모른다.

    # 훑어보기 — 여러 시각을 가로로 붙인 한 장
    python3 tools/theone/stills.py sheet <영상.mp4> <결과.png> 3 12 22 35 42 52

    # 스틸 뽑기 — 파일명이 곧 설명이 되게 (회차_분초_내용)
    python3 tools/theone/stills.py grab <영상.mp4> <폴더> S008 36 라벨_추세추종매매

⚠ 자막 타임코드와 최종본 타임코드가 같은지 먼저 확인할 것. 더원트레이더 숏폼은
   같았다(뒤에 아웃트로만 붙는다). 다른 시리즈는 다시 재 봐야 한다.
   그리고 **자막에는 있는데 최종본에 없는 구간**이 있다 — S006 04;01 뒤,
   S007 01;12 뒤. 길이를 비교해서 걸러라.
"""
import os
import subprocess
import sys

import imageio_ffmpeg


def ff():
    return imageio_ffmpeg.get_ffmpeg_exe()


def frame(src, t, out, width=None):
    vf = f"scale={width}:-1" if width else "null"
    subprocess.run([ff(), "-y", "-hide_banner", "-loglevel", "error", "-ss", str(t),
                    "-i", src, "-frames:v", "1", "-vf", vf, out], check=True)
    return out


def sheet(src, out, times, width=360):
    tmp = []
    for i, t in enumerate(times):
        p = f"{out}.{i}.png"
        frame(src, t, p, width)
        tmp.append(p)
    args = [ff(), "-y", "-hide_banner", "-loglevel", "error"]
    for p in tmp:
        args += ["-i", p]
    args += ["-filter_complex", f"hstack=inputs={len(tmp)}", "-frames:v", "1", out]
    subprocess.run(args, check=True)
    for p in tmp:
        os.remove(p)
    return out


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    if a[0] == "sheet":
        src, out, times = a[1], a[2], [float(x) for x in a[3:]]
        print(sheet(src, out, times))
    elif a[0] == "grab":
        src, folder, ep, t, name = a[1], a[2], a[3], float(a[4]), "_".join(a[5:])
        os.makedirs(folder, exist_ok=True)
        p = os.path.join(folder, f"{ep}_{int(t)//60:02d}{int(t)%60:02d}_{name}.png")
        print(frame(src, t, p))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
