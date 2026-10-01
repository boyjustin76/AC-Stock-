# -*- coding: utf-8 -*-
"""마01 캠 납품 전수 검증 — 자막 글자(PDF 대조) · 큐 경계 · **소리 싱크** · 시각 규칙.

싱크 검사가 핵심이다. 자막 큐의 시퀀스 시각을 **원본 시각으로 되돌려**, 그 자리에서
실제로 받아쓴 낱말과 큐 글자가 겹치는지 본다. 겹침이 낮으면 자막이 입과 안 맞는다는 뜻이다.
"""
import io, os, re, sys, json, difflib

레포 = r"C:/Users/user/Desktop/이정찬/스크립트_컷편집_통합/01_저장소/E_Script"
sys.path.insert(0, os.path.join(레포, "tools", "cutedit"))
import srt_rules, pdf_script

M = r"C:/Users/user/Desktop/이정찬/마이노_0930~/마01"
작업 = os.path.join(M, "_작업")
군더더기 = re.compile("[" + "".join(["\\s", "'", chr(34), chr(0x2018), chr(0x2019), chr(0x201c), chr(0x201d), "\\.", ",", "!", "?", "\\(", "\\)", "\\[", "\\]", "/", chr(0xb7), chr(0x2026), "~", "\\-", "\\+", ":", ";"]) + "]")
뼈 = lambda s: 군더더기.sub("", s)

대본 = json.load(io.open(os.path.join(작업, "대본.json"), encoding="utf-8"))
컷 = json.load(io.open(os.path.join(작업, "컷리스트.json"), encoding="utf-8"))
파일들 = json.load(io.open(os.path.join(작업, "cam_files.json"), encoding="utf-8"))
받 = json.load(io.open(os.path.join(작업, "cam_transcript.json"), encoding="utf-8"))
큐 = srt_rules.read_srt(os.path.join(M, "마01_캠_컷.srt"))
fps = 29.97

# ── 1. 자막 글자가 대본(=PDF)에 그대로 있나
대본글 = 뼈(" ".join(s for g in 대본 for s in g["문장"]))
자막글 = 뼈(" ".join(q["t"].replace("\n", " ") for q in 큐))
sm = difflib.SequenceMatcher(None, 대본글, 자막글, autojunk=False)
다름 = [(op, 대본글[i1:i2], 자막글[j1:j2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
print("[1] 자막 글자 — 대본 %d자 · 자막 %d자 · 닮음 %.4f · 다른 대목 %d곳"
      % (len(대본글), len(자막글), sm.ratio(), len(다름)))
for op, 왼, 오 in 다름[:20]:
    print("     %-7s 대본 «%s»  자막 «%s»" % (op, 왼[:50], 오[:50]))

# ── 2. 큐 경계 — 큐를 이어 붙이면 대본 문장이 되어야 한다
문장들 = [s for g in 대본 for s in g["문장"]]
남 = 자막글
덜 = [s for s in 문장들 if 뼈(s) and 뼈(s) not in 자막글]
토막 = [q["t"] for q in 큐 if len(뼈(q["t"])) < 4]
긴것 = [q["t"] for q in 큐 if len(뼈(q["t"])) > srt_rules.LONG_MAX_LEN]
여는끝 = [q["t"] for q in 큐 if re.search(r"[('\u2018\u201c\[]$", q["t"].strip())]
print("\n[2] 큐 경계 — 자막에 통째로 빠진 대본 문장 %d · 4자 미만 큐 %d · %d자 넘는 큐 %d · 여는 따옴표로 끝난 큐 %d"
      % (len(덜), len(토막), srt_rules.LONG_MAX_LEN, len(긴것), len(여는끝)))
for s in 덜[:8]: print("     빠짐: %s" % s[:60])
for s in (토막 + 긴것 + 여는끝)[:8]: print("     의심: «%s»" % s.replace("\n", " ")[:60])

# ── 3. 소리 싱크 — 시퀀스 시각 → 원본 시각 → 그 자리의 받아쓴 말과 견준다
시작맵 = {f["파일"][:8]: f["시작"] for f in 파일들}
V1 = [c for c in 컷["cuts"] if c.get("track", 1) == 1]
표, 자리프 = [], 0
for c in V1:
    바닥 = 시작맵.get(c["src"], 0.0)
    길이프 = round(c["out"] * fps) - round(c["in"] * fps)
    표.append((자리프 / fps, (자리프 + 길이프) / fps, 바닥 + c["in"]))
    자리프 += 길이프
총 = 자리프 / fps


def 되돌리기(t):
    for a, b, 원 in 표:
        if a - 1e-6 <= t <= b + 1e-6: return 원 + (t - a)
    return None


낱말 = [w for s in 받 for w in (s.get("words") or [])]
밖, 안맞, 겹침값 = [], [], []
for n, q in enumerate(큐, 1):
    if q["s"] < -1e-6 or q["e"] > 총 + 1e-6:
        밖.append((n, q["s"], q["e"])); continue
    # 당김 0.15초를 되돌려 말이 실제로 나오는 자리를 본다
    a, b = 되돌리기(min(총, q["s"] + 0.15)), 되돌리기(min(총, q["e"]))
    if a is None or b is None:
        밖.append((n, q["s"], q["e"])); continue
    들 = 뼈("".join(w["w"] for w in 낱말 if w["s"] < b + 0.6 and w["e"] > a - 0.6))
    글 = 뼈(q["t"])
    r = difflib.SequenceMatcher(None, 글, 들, autojunk=False).ratio() if 들 else 0.0
    겹침값.append(r)
    if r < 0.45: 안맞.append((n, r, q["t"].replace("\n", " "), 들[:40]))
겹침값.sort()
중앙 = 겹침값[len(겹침값) // 2] if 겹침값 else 0
print("\n[3] 소리 싱크 — 시퀀스 %.2f초 · 큐 %d개 · 구간 밖 %d · 입과 안 맞음(겹침<0.45) %d"
      % (총, len(큐), len(밖), len(안맞)))
print("     받아쓴 말과의 겹침: 중앙값 %.2f · 가장 낮은 다섯 %s"
      % (중앙, " ".join("%.2f" % v for v in 겹침값[:5])))
for n, r, 글, 들 in 안맞[:10]:
    print("     %3d 겹침 %.2f  자막«%s»  들린말«%s»" % (n, r, 글[:30], 들))

# ── 4. 시각 규칙
문제 = []
for n, q in enumerate(큐, 1):
    길이 = q["e"] - q["s"]
    글자 = len(re.sub(r"\s", "", q["t"]))
    if q["e"] <= q["s"]: 문제.append((n, "끝≤시작"))
    if 길이 < 0.3: 문제.append((n, "0.3초 미만 %.2f" % 길이))
    if n < len(큐) and 큐[n]["s"] < q["e"] - 1e-6: 문제.append((n, "다음 큐와 겹침"))
    if 길이 > 0 and 글자 / 길이 > 13: 문제.append((n, "초당 %.1f자" % (글자 / 길이)))
print("\n[4] 시각 규칙 — 문제 %d곳" % len(문제))
for n, 왜 in 문제[:10]: print("     %3d %s" % (n, 왜))

print("\n한 줄 판정: 글자 %s · 경계 %s · 싱크 %s · 시각 %s"
      % ("OK" if not 다름 else "%d곳" % len(다름),
         "OK" if not (덜 or 토막 or 긴것 or 여는끝) else "볼 것 있음",
         "OK" if not (밖 or 안맞) else "%d곳" % (len(밖) + len(안맞)),
         "OK" if not 문제 else "%d곳" % len(문제)))
