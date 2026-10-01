# -*- coding: utf-8 -*-
"""박수 자리 앞뒤만 받아 적어 **시작 멘트**를 확인한다.

118분을 다 받아 적으면 오래 걸린다. 박수(짝) 뒤에 "차트설명 찍겠습니다" 같은 멘트가
오는 습관을 쓰기로 했으니(이정찬 2026-09-30), 박수 자리 ±창 만 받아 적는다.

  python3 tools/cutedit/obs_cue.py <소리.json> <결과.json> <영상 폴더> [--모델 small]

내놓는 것
  [{"파일": …, "박수": 초, "글": "…", "시작멘트": true/false}, …]
"""
import io, os, sys, json
import numpy as np
import av

앞, 뒤 = 2.0, 9.0                 # 박수 앞 2초, 뒤 9초
멘트 = ["차트설명", "차트 설명", "찍겠습니다", "찍을게요", "시작하겠습니다", "가겠습니다", "갑니다"]


def 소리조각(경로, 시작, 끝, sr=16000):
    조각 = []
    with av.open(경로) as c:
        s = c.streams.audio[0]
        c.seek(int(max(0, 시작 - 1) * av.time_base), stream=s)
        재표본 = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=sr)
        for 프레임 in c.decode(s):
            t = float(프레임.pts * 프레임.time_base)
            if t > 끝: break
            for f in 재표본.resample(프레임):
                if t >= 시작 - 0.5: 조각.append(f.to_ndarray().reshape(-1))
    if not 조각: return np.zeros(1, dtype=np.float32)
    return np.concatenate(조각).astype(np.float32) / 32768.0


if __name__ == "__main__":
    소리 = json.load(io.open(sys.argv[1], encoding="utf-8"))
    낼곳, 폴더 = sys.argv[2], sys.argv[3]
    모델이름 = sys.argv[sys.argv.index("--모델") + 1] if "--모델" in sys.argv else "small"
    from faster_whisper import WhisperModel
    모델 = WhisperModel(모델이름, device="cpu", compute_type="int8")
    결과 = []
    for r in 소리:
        경로 = os.path.join(폴더, r["파일"])
        for t in r["박수"]:
            x = 소리조각(경로, max(0, t - 앞), t + 뒤)
            글 = " ".join(s.text.strip() for s in 모델.transcribe(x, language="ko", beam_size=1)[0])
            결과.append({"파일": r["파일"], "박수": t, "글": 글,
                         "시작멘트": any(m in 글.replace(" ", "") or m in 글 for m in 멘트)})
            print("%s %7.1f초  %s%s" % (r["파일"][11:16], t, "◆ " if 결과[-1]["시작멘트"] else "  ", 글[:70]), flush=True)
    json.dump(결과, io.open(낼곳, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("냈다: %s · 시작멘트 %d / %d" % (낼곳, sum(1 for r in 결과 if r["시작멘트"]), len(결과)))
