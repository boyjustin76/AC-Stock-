# -*- coding: utf-8 -*-
"""OBS 화면녹화(차트 설명) 훑기 — 무음 구간과 박수(짝 소리)를 찾는다.

ffmpeg 실행파일 없이 PyAV 로 소리를 직접 읽는다 (이 PC 에 ffmpeg 이 없다, 2026-09-30).

내놓는 것 (json)
  {"파일": …, "길이": 초, "무음": [[시작, 끝], …], "박수": [초, …], "소리크기": [[초, dBFS], …]}

무음 판정 — 20ms 마다 RMS 를 재고, 말소리 중앙값보다 훨씬 낮은 구간이 이어지면 무음.
  문턱은 고정 dB 가 아니라 **그 파일의 중앙값 기준**이다. 녹화마다 마이크 볼륨이 다르다.
박수 판정 — 앞 0.2초보다 갑자기 크게 튀고(+20dB), 그 자체가 아주 큰(상위 1%) 자리.
  차트 설명을 새로 시작할 때 손뼉을 치는 습관을 신호로 쓴다 (이정찬 2026-09-30).
"""
import io, os, sys, json
import numpy as np
import av

홉 = 0.02                 # 20ms
무음최소 = 0.6            # 이보다 짧은 조용함은 숨이다


def 소리읽기(경로, 샘플레이트=16000):
    """모노 파형 (numpy float32) 으로."""
    조각 = []
    with av.open(경로) as c:
        s = c.streams.audio[0]
        재표본 = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=샘플레이트)
        for 프레임 in c.decode(s):
            for f in 재표본.resample(프레임):
                조각.append(f.to_ndarray().reshape(-1))
    x = np.concatenate(조각).astype(np.float32) / 32768.0
    return x, 샘플레이트


def 크기(x, sr):
    n = int(홉 * sr)
    끝 = len(x) - len(x) % n
    틀 = x[:끝].reshape(-1, n)
    rms = np.sqrt((틀 ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-12)          # dBFS


def 무음구간(db, 문턱):
    구간, 시작 = [], None
    for i, v in enumerate(db):
        if v < 문턱 and 시작 is None: 시작 = i
        elif v >= 문턱 and 시작 is not None:
            if (i - 시작) * 홉 >= 무음최소: 구간.append([시작 * 홉, i * 홉])
            시작 = None
    if 시작 is not None and (len(db) - 시작) * 홉 >= 무음최소:
        구간.append([시작 * 홉, len(db) * 홉])
    return 구간


def 박수(db):
    """앞 0.2초 평균보다 20dB 이상 튀고, 상위 1% 크기인 자리."""
    앞 = 10                                     # 0.2초 = 10홉
    큰 = np.percentile(db, 99)
    후보 = []
    for i in range(앞, len(db)):
        if db[i] >= 큰 and db[i] - db[i - 앞:i].mean() >= 20:
            t = i * 홉
            if not 후보 or t - 후보[-1] > 1.0: 후보.append(round(t, 2))
    return 후보


def 훑기(경로):
    x, sr = 소리읽기(경로)
    db = 크기(x, sr)
    # 문턱은 배경과 말소리 사이 계곡에 둔다. 이 녹화는 전체 볼륨이 아주 낮아서(말 -45dBFS)
    # 고정 dB 로는 안 잡힌다 — 파일마다 상대값으로 잡는다 (2026-09-30 실측).
    배경, 말 = np.percentile(db, 10), np.percentile(db, 95)
    문턱 = 배경 + 0.35 * (말 - 배경)
    무음 = 무음구간(db, 문턱)
    return {"파일": os.path.basename(경로), "길이": round(len(x) / sr, 2),
            "문턱dB": round(float(문턱), 1), "말dB": round(float(말), 1),
            "무음": [[round(a, 2), round(b, 2)] for a, b in 무음],
            "박수": 박수(db),
            "소리크기": [[round(i * 홉, 2), round(float(v), 1)] for i, v in enumerate(db[::50])]}


if __name__ == "__main__":
    낼곳 = sys.argv[1]
    결과 = []
    for p in sys.argv[2:]:
        r = 훑기(p)
        총무음 = sum(b - a for a, b in r["무음"])
        print("%s  길이 %.1f분 · 무음 %d곳 %.1f분(%.0f%%) · 박수 후보 %d개" %
              (r["파일"], r["길이"] / 60, len(r["무음"]), 총무음 / 60, 총무음 / r["길이"] * 100, len(r["박수"])), flush=True)
        결과.append(r)
    json.dump(결과, io.open(낼곳, "w", encoding="utf-8"), ensure_ascii=False)
    print("냈다:", 낼곳)
