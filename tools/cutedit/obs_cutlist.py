# -*- coding: utf-8 -*-
"""OBS 녹화 → 프리미어 컷리스트 (테이크만 남기고, 잘라 낸 건 꺼 둔 클립으로 둔다).

촬영 버릇 (이정찬 2026-09-30)
    ("차트설명" 멘트가 있기도 하고 없기도) → **박수** → 스크립트 한 줄 읽기
    → 차트에 펜으로 그리기 → **박수**
  그래서 한 테이크는 **박수와 박수 사이**다. 그 안에 펜 그림이 있으면 쓸 만한 테이크다.

받는 것
  소리.json (obs_scan.py) — 무음·박수    ·    펜.json (obs_pen.py) — 펜으로 그린 구간

내놓는 것 (make_xml.py 가 읽는 컷리스트)
  V1  테이크 — 박수부터 박수까지. 안쪽의 긴 무음은 잘라 붙인다.
  V2  나머지 — **꺼 둔 클립**(사용안함). 지우지 않는다.
  마커  박수(전부) · 펜(구간) · 테이크(구간) · ★읽고그리기(테이크가 이어지는 묶음)
"""
import io, os, sys, json

여유 = 0.15          # 남기는 구간 앞뒤 여유
최소무음 = 1.2       # 테이크 안에서 이보다 긴 조용함만 잘라 낸다
최소길이 = 0.4
앞여유, 뒤여유 = 1.0, 1.0   # 박수 앞뒤로 이만큼 더 붙여 둔다 (박수 소리 자체는 편집에서 뺀다)


def 테이크찾기(박수, 그림, 길이, 최대=75.0):
    """펜 그림 하나마다 그 앞뒤 박수를 찾아 테이크로 묶는다."""
    테 = []
    for a, b, 획 in 그림:
        앞 = [t for t in 박수 if t <= a and a - t <= 최대]
        뒤 = [t for t in 박수 if t >= b and t - b <= 최대]
        시작 = max(앞) if 앞 else max(0.0, a - 60)
        끝 = min(뒤) if 뒤 else min(길이, b + 30)
        if 테 and 시작 <= 테[-1][1]:                  # 겹치면 같은 테이크
            테[-1] = [테[-1][0], max(테[-1][1], 끝), 테[-1][2] + 1]
        else:
            테.append([시작, 끝, 1])
    return [[max(0.0, s - 앞여유), min(길이, e + 뒤여유), n] for s, e, n in 테]


def 무음빼기(시작, 끝, 무음):
    """테이크 안에서 긴 무음만 잘라 낸 조각들."""
    조각, 자리 = [], 시작
    for a, b in 무음:
        if b <= 시작 or a >= 끝 or b - a < 최소무음: continue
        컷끝 = min(끝, a + 여유)
        if 컷끝 - 자리 >= 최소길이: 조각.append([round(자리, 2), round(컷끝, 2)])
        자리 = max(자리, min(끝, b - 여유))
    if 끝 - 자리 >= 최소길이: 조각.append([round(자리, 2), round(끝, 2)])
    return 조각


def 만들기(소리, 펜, 폴더, 이름, fps=30.0, w=1920, h=1080):
    펜맵 = {p["파일"]: p.get("그림구간", []) for p in 펜}
    sources, cuts, markers = {}, [], []
    시간 = 0.0
    for r in 소리:
        키 = r["파일"][11:16]
        sources[키] = {"path": os.path.join(폴더, r["파일"]).replace("\\", "/"), "dur": r["길이"]}
        그림 = 펜맵.get(r["파일"], [])
        테이크 = 테이크찾기(r.get("박수", []), 그림, r["길이"])
        옮김 = []
        for n, (시작, 끝, 펜수) in enumerate(테이크, 1):
            머리 = 시간
            for a, b in 무음빼기(시작, 끝, r["무음"]):
                cuts.append({"src": 키, "in": a, "out": b, "label": "%s 테이크%d" % (키, n)})
                옮김.append((a, b, 시간)); 시간 += b - a
            markers.append({"at": round(머리, 2), "dur": round(시간 - 머리, 2), "name": "테이크 %s-%d" % (키, n),
                            "comment": "원본 %.0f~%.0f초 · 펜 %d번" % (시작, 끝, 펜수)})
        def 옮기기(t):
            for a, b, 자리 in 옮김:
                if a <= t <= b: return 자리 + (t - a)
                if t < a: return 자리
            return 시간
        # 테이크 밖(안 쓰는 데)은 꺼 둔 클립으로 남긴다
        경계, 자리 = [], 0.0
        for 시작, 끝, _ in 테이크:
            if 시작 - 자리 >= 1.0: 경계.append([자리, 시작])
            자리 = 끝
        if r["길이"] - 자리 >= 1.0: 경계.append([자리, r["길이"]])
        for a, b in 경계:
            cuts.append({"src": 키, "in": round(a, 2), "out": round(b, 2), "track": 2,
                         "at": round(옮기기(a), 2), "audio": False, "enabled": False,
                         "label": "안 씀 %s %.0f초" % (키, a)})
        for t in r.get("박수", []):
            markers.append({"at": round(옮기기(t), 2), "name": "박수", "comment": "%s 원본 %.2f초" % (키, t)})
        for g in 그림:
            시, 끝 = 옮기기(g[0]), 옮기기(g[1])
            markers.append({"at": round(시, 2), "dur": round(max(0.5, 끝 - 시), 2), "name": "펜",
                            "comment": "%s 원본 %.1f~%.1f초 · 획 %d" % (키, g[0], g[1], g[2])})
        # 테이크가 잇따라 붙는 묶음 = '한 줄 읽고 그리고' 가 반복되는 구간
        뭉, 현재 = [], []
        for 시작, 끝, _ in 테이크:
            if 현재 and 시작 - 현재[-1][1] <= 120: 현재.append([시작, 끝])
            else:
                if len(현재) >= 3: 뭉.append(현재)
                현재 = [[시작, 끝]]
        if len(현재) >= 3: 뭉.append(현재)
        for 묶 in 뭉:
            a, b = 묶[0][0], 묶[-1][1]
            markers.append({"at": round(옮기기(a), 2), "dur": round(옮기기(b) - 옮기기(a), 2),
                            "name": "★ 읽고 그리기",
                            "comment": "%s 원본 %.0f~%.0f초 · 테이크 %d개" % (키, a, b, len(묶))})
    markers.sort(key=lambda m: m["at"])
    return {"name": 이름, "fps": fps, "width": w, "height": h,
            "sources": sources, "cuts": cuts, "markers": markers}


if __name__ == "__main__":
    소리 = json.load(io.open(sys.argv[1], encoding="utf-8"))
    펜 = json.load(io.open(sys.argv[2], encoding="utf-8")) if os.path.exists(sys.argv[2]) else []
    폴더, 낼곳 = sys.argv[3], sys.argv[4]
    이름 = sys.argv[5] if len(sys.argv) > 5 else "마01_차트설명_컷"
    spec = 만들기(소리, 펜, 폴더, 이름)
    json.dump(spec, io.open(낼곳, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    남 = [c for c in spec["cuts"] if c.get("track", 1) == 1]
    잘 = [c for c in spec["cuts"] if c.get("track", 1) == 2]
    셈 = lambda 이름: sum(1 for m in spec["markers"] if m["name"].startswith(이름))
    print("%s\n  V1 테이크 컷 %d개 %.1f분 · V2 안 쓴 것 %d개 %.1f분\n  마커 %d개 (박수 %d · 펜 %d · 테이크 %d · ★ %d)" % (
        낼곳, len(남), sum(c["out"] - c["in"] for c in 남) / 60,
        len(잘), sum(c["out"] - c["in"] for c in 잘) / 60,
        len(spec["markers"]), 셈("박수"), 셈("펜"), 셈("테이크"), 셈("★")))
