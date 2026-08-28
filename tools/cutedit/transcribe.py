import json, sys, time
from faster_whisper import WhisperModel

S = "/tmp/claude-0/-home-user-AC-Stock-/2aa738bb-430f-52e0-bfd6-c6b618c5db6c/scratchpad"
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
