# -*- coding: utf-8 -*-
"""캠 녹화 여러 개를 **이어 붙인 한 타임라인**으로 보고 단어 단위로 받아 적는다.

align_take.py 는 녹음 하나를 보고 '같은 문장이 여러 번 나오면 마지막 것'을 고른다.
캠 촬영은 파일이 여러 개로 끊겨 있을 뿐 실제로는 한 줄기이므로, 파일 순서대로 시간을
이어 붙여 하나처럼 다룬다. 되돌릴 수 있도록 파일별 시작 시각을 같이 남긴다.

    python3 tools/cutedit/cam_prep.py <작업폴더> <영상…> [--모델 medium]
      내놓는 것  <작업폴더>/cam_transcript.json   (transcribe.py 와 같은 꼴)
                 <작업폴더>/cam_files.json        [{"파일":…, "시작":초, "길이":초}, …]

소리가 작으면(이 PC 의 OBS·아이폰 녹화) 최대값 기준으로 키워서 넣는다.
"""
import io, os, sys, json, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import obs_scan


def 소리토막(경로, 처음, 끝, sr=16000):
    """긴 파일은 토막으로 읽는다 — 백그라운드 작업이 10분에 끊기기 때문이다 (2026-10-01)."""
    import av
    조각 = []
    with av.open(경로) as c:
        s = c.streams.audio[0]
        c.seek(int(max(0, 처음 - 1) / float(s.time_base)), stream=s)     # 스트림 타임베이스 단위
        재표본 = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=sr)
        for 프레임 in c.decode(s):
            t = float(프레임.pts * 프레임.time_base)
            if 끝 and t > 끝: break
            if t >= 처음 - 0.2:
                for f in 재표본.resample(프레임): 조각.append(f.to_ndarray().reshape(-1))
    x = np.concatenate(조각).astype(np.float32) / 32768.0 if 조각 else np.zeros(1, np.float32)
    return x, sr


def 받아적기(경로, 모델, 시작, 범위=None):
    x, sr = 소리토막(경로, *범위) if 범위 else obs_scan.소리읽기(경로)
    배 = 0.9 / max(1e-6, float(np.abs(x).max()))
    구간, _ = 모델.transcribe((x * 배).astype(np.float32), language="ko", beam_size=5,
                              word_timestamps=True, vad_filter=True,
                              vad_parameters=dict(min_silence_duration_ms=300),
                              condition_on_previous_text=False)
    줄 = []
    for s in 구간:
        낱말 = [{"w": w.word, "s": round(w.start + 시작, 3), "e": round(w.end + 시작, 3),
                 "p": round(w.probability, 3)} for w in (s.words or [])]
        줄.append({"s": round(s.start + 시작, 3), "e": round(s.end + 시작, 3), "text": s.text, "words": 낱말})
    return 줄, len(x) / sr, 배


if __name__ == "__main__":
    S = sys.argv[1]
    인자 = sys.argv[2:]
    모델이름, 범위, 꼬리 = "medium", None, ""
    if "--모델" in 인자:
        k = 인자.index("--모델"); 모델이름 = 인자[k + 1]; del 인자[k:k + 2]
    if "--범위" in 인자:                                  # 초 단위 토막 (예: --범위 0 960)
        k = 인자.index("--범위"); 범위 = (float(인자[k + 1]), float(인자[k + 2])); del 인자[k:k + 3]
        꼬리 = "_%05d" % int(범위[0])
    영상 = [a for a in 인자 if not a.startswith("--")]
    os.makedirs(S, exist_ok=True)
    from faster_whisper import WhisperModel
    모델 = WhisperModel(모델이름, device="cpu", compute_type="int8", cpu_threads=4)
    모든줄, 파일들, 시각 = [], [], 0.0
    for p in 영상:
        t0 = time.time()
        줄, 길이, 배 = 받아적기(p, 모델, 시각 + (범위[0] if 범위 else 0.0), 범위)
        모든줄 += 줄
        파일들.append({"파일": os.path.basename(p), "경로": p.replace("\\", "/"),
                       "시작": round(시각, 3), "길이": round(길이, 3), "볼륨배": round(배, 2)})
        print("%-16s %5.1f분 · 구간 %3d개 · %3.0f초 걸림 (이어 붙인 시작 %.1f초)" %
              (os.path.basename(p), 길이 / 60, len(줄), time.time() - t0, 시각), flush=True)
        시각 += 길이
        json.dump(모든줄, io.open(os.path.join(S, "cam_transcript%s.json" % 꼬리), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(파일들, io.open(os.path.join(S, "cam_files%s.json" % 꼬리), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("냈다: %s/cam_transcript.json · 전체 %.1f분" % (S, 시각 / 60))
