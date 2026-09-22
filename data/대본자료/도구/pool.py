# -*- coding: utf-8 -*-
"""회사 Pool 을 한 덩어리로 모은다 — 차트명가(Old) · 더원트레이더 · 트레이딩팩토리.

원본: 드라이브 `05_문서_기획+스크립트(아카이브)` 의 02·03·04·01·05 폴더 + 저장소 scripts.json
산출: ../Pool/<갈래>_<이름>.txt · ../Pool/index.json
"""
import glob
import io
import json
import os
import re
import sys

REPO = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\01_저장소\E_Script"
ARCH = r"G:\내 드라이브\트레이딩팩토리\05_문서_기획+스크립트(아카이브)"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "Pool")
sys.path.insert(0, os.path.join(REPO, "tools", "cutedit"))
from docx_script import paragraphs  # noqa: E402

os.makedirs(OUT, exist_ok=True)
rows = []


def put(kind, name, text, src=""):
    """이름이 겹쳐도 덮어쓰지 않는다.

    갈래가 달라도 제목이 같은 원고가 있다 (`[스타일A_전문가 형]000` 이 폴더 세 곳에).
    2026-09-18 이전 판은 뒤에 읽은 것이 앞을 **조용히 덮어써서** 목록은 181편인데
    디스크에는 168개뿐이었다. 같은 내용이면 한 번만 쓰고, 다르면 `_2`, `_3` 을 붙인다.
    """
    if len(text) < 600:
        return
    safe = re.sub(r'[\/:*?"<>|]', "_", name)[:60].strip(" .")
    base = os.path.join(OUT, kind + "_" + safe)
    p, n = base + ".txt", 1
    while os.path.exists(p):
        if io.open(p, encoding="utf-8").read() == text:
            rows.append({"kind": kind, "name": name, "chars": len(text),
                         "file": os.path.basename(p), "src": src, "같은내용": True})
            return
        n += 1
        p = "%s_%d.txt" % (base, n)
    io.open(p, "w", encoding="utf-8", newline="\n").write(text)
    rows.append({"kind": kind, "name": name, "chars": len(text),
                 "file": os.path.basename(p), "src": src})


def read_any(p):
    if p.lower().endswith(".docx"):
        return "\n".join(x for x in paragraphs(p) if x)
    return io.open(p, encoding="utf-8-sig", errors="replace").read()


# 차트명가(Old) — 저장소에 본문이 있다
for x in json.load(io.open(os.path.join(REPO, "log", "data", "scripts.json"), encoding="utf-8"))["docs"]:
    put("차명", x["ep"], x.get("text") or "", "log/data/scripts.json")

# 더원트레이더 · 트레이딩팩토리 · 공용(라이브 질문) · 숏츠
FOLDERS = [("더원", "04.더원트레이더"), ("트팩", "02.트레이딩 팩토리"),
           ("라이브", "01.공용 아카이브"), ("숏츠", "05.숏츠 스크립트")]
for kind, sub in FOLDERS:
    for p in sorted(glob.glob(os.path.join(ARCH, sub, "**", "*.*"), recursive=True)):
        if os.path.basename(p).startswith("~$") or not p.lower().endswith((".docx", ".txt")):
            continue
        try:
            put(kind, os.path.basename(p).rsplit(".", 1)[0], read_any(p),
                os.path.relpath(p, ARCH).replace("\\", "/"))
        except Exception as e:
            print("  건너뜀:", os.path.basename(p)[:40], type(e).__name__)

json.dump(rows, io.open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
tot, same = {}, 0
for r in rows:
    if r.get("같은내용"):
        same += 1
        continue
    tot.setdefault(r["kind"], []).append(r["chars"])
print("Pool 구성 —")
for k, v in tot.items():
    print("   %-5s %3d편 · %7s자 · 편당 중앙 %s자" % (k, len(v), format(sum(v), ","), format(sorted(v)[len(v) // 2], ",")))
n = sum(len(v) for v in tot.values())
print("   합계  %d편 · %s자 → %s" % (n, format(sum(sum(v) for v in tot.values()), ","), OUT))
print("   (제목·내용이 똑같아 한 번만 센 것 %d건 — 목록 %d줄)" % (same, len(rows)))
