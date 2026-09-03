import json, os, sys, time
from faster_whisper import WhisperModel

# 작업 폴더. 차11-4·5 때는 클라우드 스크래치가 박혀 있었다 —
# 환경변수나 첫 인자로 받는다. 회차마다 폴더 하나를 잡고 거기에 다 넣는다.
#   set CUTEDIT_DIR=...\ch11-6   또는   python tools/cutedit/xxx.py <폴더>
S = os.environ.get("CUTEDIT_DIR") or (sys.argv[1] if len(sys.argv) > 1 else "")
if not S or not os.path.isdir(S):
    sys.exit("작업 폴더를 정하세요 — 환경변수 CUTEDIT_DIR 또는 첫 인자로 폴더 경로."
             f" (지금: {S or '없음'})")
t0 = time.time()
model = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=4)
print(f"model loaded {time.time()-t0:.0f}s", flush=True)

segments, info = model.transcribe(
    f"{S}/cam16k.wav",
    language="ko",
    word_timestamps=True,
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=300),
    beam_size=5,
)

out = []
for seg in segments:
    words = [{"w": w.word, "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)} for w in (seg.words or [])]
    out.append({"s": round(seg.start, 3), "e": round(seg.end, 3), "text": seg.text, "words": words})
    print(f"[{seg.start:7.2f}-{seg.end:7.2f}] {seg.text}", flush=True)

with open(f"{S}/cam_transcript.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"done {time.time()-t0:.0f}s, {len(out)} segments", flush=True)
