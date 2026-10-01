# -*- coding: utf-8 -*-
"""정렬 결과(aligned.json) → 캠 컷리스트 (구간별 테이크 + 안 쓴 것은 꺼 둔 클립).

align_take.py 가 대본 문장마다 '마지막 테이크'의 시각을 잡아 준다. 캠 파일 여러 개를
이어 붙인 한 타임라인으로 다뤘으므로(cam_prep.py), 여기서 다시 **파일별 시각으로 되돌린다.**

  V1   대본 순서대로 이은 낭독분. 문장 사이가 가까우면 한 컷으로 묶는다.
  V2   안 쓴 구간 — 꺼 둔 클립(사용안함). 지우지 않는다.
  마커  구간 머리글(INTRO·1·2·3·4·OUTRO) + 박수

    python3 tools/cutedit/cam_cutlist.py <작업폴더> <대본.json> <소리.json> <컷리스트.json> [이름]
"""
import io, os, sys, json

붙임 = 1.2          # 문장 사이가 이 안쪽이면 한 컷으로 잇는다
머리여유, 꼬리여유 = 0.25, 0.35


def 파일찾기(파일들, t):
    for f in 파일들:
        if f["시작"] <= t < f["시작"] + f["길이"]: return f
    return 파일들[-1]


def 묶기(행들):
    """시간순으로 이어진 문장을 컷으로 묶는다."""
    컷, 지금 = [], None
    for r in 행들:
        if 지금 and r["s"] - 지금["끝"] <= 붙임 and r["구간"] == 지금["구간"]:
            지금["끝"] = max(지금["끝"], r["e"]); 지금["문장"] += 1
        else:
            if 지금: 컷.append(지금)
            지금 = {"시작": r["s"], "끝": r["e"], "구간": r["구간"], "문장": 1}
    if 지금: 컷.append(지금)
    return 컷


def 만들기(작업, 대본, 소리, 이름, fps=30.0, w=1920, h=1080):
    파일들 = json.load(io.open(os.path.join(작업, "cam_files.json"), encoding="utf-8"))
    정렬 = json.load(io.open(os.path.join(작업, "aligned.json"), encoding="utf-8"))
    구간이름 = [g["구간"] for g in 대본]
    # aligned 행에 구간 꼬리표를 붙인다 — 머리글 줄이 나오면 그 뒤 문장은 그 구간
    행들 = []
    for r in 정렬:
        if r.get("s") is None: continue
        if (r.get("score") or 0) < 0.75: continue      # 약하게 걸린 줄은 쓰지 않는다 (엉뚱한 조각이 생긴다)
        꼬리 = (r.get("sec") or "").strip()            # align_take 가 머리글을 줄마다 붙여 둔다
        행들.append({"s": r["s"], "e": r["e"], "구간": (꼬리.split() or ["?"])[0],
                     "글": (r.get("text") or "").strip()})
    행들.sort(key=lambda r: r["s"])
    컷들 = 묶기(행들)

    def 박자(경로):                       # 아이폰 원본은 240fps 도 섞여 있다 — 자리 계산에 꼭 필요하다
        try:
            import av
            with av.open(경로) as c: return float(c.streams.video[0].average_rate)
        except Exception: return fps
    sources = {f["파일"][:8]: {"path": f["경로"], "dur": f["길이"], "fps": 박자(f["경로"])} for f in 파일들}
    cuts, markers, 시간, 쓴구간 = [], [], 0.0, []
    for c in 컷들:
        f = 파일찾기(파일들, c["시작"])
        a = max(0.0, c["시작"] - f["시작"] - 머리여유)
        b = min(f["길이"], c["끝"] - f["시작"] + 꼬리여유)
        if b - a < 0.3: continue
        if not 쓴구간 or 쓴구간[-1] != c["구간"]:
            markers.append({"at": round(시간, 2), "name": "구간 %s" % c["구간"],
                            "comment": "%s %.0f초부터" % (f["파일"], a)})
            쓴구간.append(c["구간"])
        cuts.append({"src": f["파일"][:8], "in": round(a, 2), "out": round(b, 2),
                     "label": "%s %s" % (c["구간"], f["파일"][4:8])})
        쓴것 = (f["파일"], a, b, 시간)
        시간 += b - a
    # 안 쓴 구간 — 파일마다 쓴 자리를 빼고 남는 것
    쓴자리 = {}
    for c in cuts: 쓴자리.setdefault(c["src"], []).append((c["in"], c["out"]))
    for f in 파일들:
        키 = f["파일"][:8]
        자리, 남 = 0.0, []
        for a, b in sorted(쓴자리.get(키, [])):
            if a - 자리 >= 1.0: 남.append((자리, a))
            자리 = max(자리, b)
        if f["길이"] - 자리 >= 1.0: 남.append((자리, f["길이"]))
        for a, b in 남:
            cuts.append({"src": 키, "in": round(a, 2), "out": round(b, 2), "track": 2,
                         "at": 0.0, "audio": False, "enabled": False,
                         "label": "안 씀 %s %.0f초" % (키, a)})
    # 꺼 둔 클립은 V2 에, **V1 이 끝난 뒤부터** 차례로 늘어놓는다.
    # 0초부터 깔면 시퀀스가 원본 전체 길이(1시간 40분)로 늘어나 편집에 걸리적거린다 (2026-10-01).
    자리 = sum(c["out"] - c["in"] for c in cuts if c.get("track", 1) == 1)
    for c in cuts:
        if c.get("track") == 2:
            c["at"] = round(자리, 2); 자리 += c["out"] - c["in"]
    for r in 소리:
        키 = r["파일"][:8]
        if 키 not in sources: continue
    return {"name": 이름, "fps": fps, "width": w, "height": h,
            "sources": sources, "cuts": cuts, "markers": markers}


if __name__ == "__main__":
    작업, 대본길, 소리길, 낼곳 = sys.argv[1:5]
    이름 = sys.argv[5] if len(sys.argv) > 5 else "마01_캠_컷"
    대본 = json.load(io.open(대본길, encoding="utf-8"))
    소리 = json.load(io.open(소리길, encoding="utf-8")) if os.path.exists(소리길) else []
    spec = 만들기(작업, 대본, 소리, 이름)
    json.dump(spec, io.open(낼곳, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    남 = [c for c in spec["cuts"] if c.get("track", 1) == 1]
    잘 = [c for c in spec["cuts"] if c.get("track", 1) == 2]
    print("%s\n  V1 컷 %d개 %.1f분 · V2 안 쓴 것 %d개 %.1f분 · 마커 %d개" %
          (낼곳, len(남), sum(c["out"] - c["in"] for c in 남) / 60,
           len(잘), sum(c["out"] - c["in"] for c in 잘) / 60, len(spec["markers"])))
    for m in spec["markers"]: print("   %6.1f초  %s  (%s)" % (m["at"], m["name"], m["comment"]))
