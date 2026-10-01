# -*- coding: utf-8 -*-
"""OBS 녹화를 통째로 받아 적는다 (ffmpeg 없이 PyAV 로 소리를 읽는다).

이 녹화는 볼륨이 아주 작다(말소리 -45dBFS). 그대로 넣으면 whisper 가 아무것도 못 잡는다.
그래서 **최대값 기준으로 키운 뒤** 넣는다 (2026-09-30 실측: 5.4배).

  python3 tools/cutedit/obs_stt.py <결과.json> <영상…> [--모델 small]

내놓는 것
  [{"파일": …, "구간": [{"s":…, "e":…, "글":…}, …]}, …]
"""
import io, os, sys, json, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import obs_scan


def 받아적기(경로, 모델):
    x, sr = obs_scan.소리읽기(경로)
    배 = 0.9 / max(1e-6, float(np.abs(x).max()))
    구간, _ = 모델.transcribe((x * 배).astype(np.float32), language="ko", beam_size=1,
                              vad_filter=True, vad_parameters=dict(min_silence_duration_ms=700, speech_pad_ms=200),
                              condition_on_previous_text=False)
    return [{"s": round(s.start, 2), "e": round(s.end, 2), "글": s.text.strip()} for s in 구간], 배


if __name__ == "__main__":
    낼곳 = sys.argv[1]
    인자 = sys.argv[2:]
    이름 = "small"
    if "--모델" in 인자:                                  # 값까지 같이 빼야 한다 ('small' 을 영상으로 넘겼었다)
        k = 인자.index("--모델"); 이름 = 인자[k + 1]; del 인자[k:k + 2]
    영상 = [a for a in 인자 if not a.startswith("--")]
    from faster_whisper import WhisperModel
    모델 = WhisperModel(이름, device="cpu", compute_type="int8", cpu_threads=4)
    결과 = []
    for p in 영상:
        t0 = time.time()
        구간, 배 = 받아적기(p, 모델)
        print("%s  구간 %d개 · %.0f초 걸림 (볼륨 %.1f배)" % (os.path.basename(p), len(구간), time.time() - t0, 배), flush=True)
        결과.append({"파일": os.path.basename(p), "볼륨배": round(배, 2), "구간": 구간})
        json.dump(결과, io.open(낼곳, "w", encoding="utf-8"), ensure_ascii=False)
    print("냈다:", 낼곳)
