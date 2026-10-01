# -*- coding: utf-8 -*-
"""나눠 받아 적은 것들을 **촬영 순서 한 타임라인**으로 합친다.

왜 나눠 적었나 — 백그라운드 작업이 10분에 끊겨서, 긴 파일(IMG_0019 64분)은 16분씩 토막냈다.
합칠 때 토막 파일(`cam_transcript_00000.json` 처럼 숫자 꼬리)은 **같은 원본의 이어진 부분**으로 본다.

    python3 tools/cutedit/cam_merge.py <작업폴더> <영상…>
      영상은 촬영 순서대로 준다. 각 영상의 받아쓰기를 작업폴더(또는 작업폴더/<번호>)에서 찾는다.
      내놓는 것  <작업폴더>/cam_transcript.json · cam_files.json  (align_take.py 가 읽는 꼴)
"""
import io, os, re, sys, json, glob
import av


def 길이재기(경로):
    with av.open(경로) as c:
        s = c.streams.audio[0]
        return float(s.duration * s.time_base) if s.duration else float(c.duration) / av.time_base


def 받아쓰기모으기(작업, 이름):
    """<작업>/… 아래에서 그 영상의 받아쓰기 조각을 모은다 (토막 파일 포함)."""
    번호 = re.search(r"(\d{4})", 이름)
    후보 = []
    for 폴더 in [작업, os.path.join(작업, 번호.group(1) if 번호 else "")]:
        if not os.path.isdir(폴더): continue
        for f in sorted(glob.glob(os.path.join(폴더, "cam_transcript*.json"))):
            이것 = json.load(io.open(f, encoding="utf-8"))
            짝 = f.replace("cam_transcript", "cam_files")
            if os.path.exists(짝):
                파일들 = json.load(io.open(짝, encoding="utf-8"))
                if not any(p["파일"] == 이름 for p in 파일들): continue
                if len(파일들) == 1:
                    pass        # 그 영상 하나만 적은 파일 — 토막이어도 시각이 이미 원본 기준이다
                else:
                    # 여러 영상이 한 파일에 들어 있으면 이 영상 몫만 뽑아 상대 시각으로 되돌린다
                    p = [q for q in 파일들 if q["파일"] == 이름][0]
                    끝 = p["시작"] + p["길이"]
                    이것 = [dict(s, s=s["s"] - p["시작"], e=s["e"] - p["시작"],
                                 words=[dict(w, s=w["s"] - p["시작"], e=w["e"] - p["시작"]) for w in s.get("words", [])])
                            for s in 이것 if p["시작"] - 0.1 <= s["s"] < 끝 + 0.1]
            후보 += 이것
    본, 깨끗 = set(), []
    for s in sorted(후보, key=lambda s: s["s"]):
        열쇠 = (round(s["s"], 1), s["text"][:20])
        if 열쇠 in 본: continue
        본.add(열쇠); 깨끗.append(s)
    return 깨끗


if __name__ == "__main__":
    작업, 영상 = sys.argv[1], sys.argv[2:]
    모든줄, 파일들, 시각 = [], [], 0.0
    for p in 영상:
        이름 = os.path.basename(p)
        줄 = 받아쓰기모으기(작업, 이름)
        길이 = 길이재기(p)
        모든줄 += [dict(s, s=round(s["s"] + 시각, 3), e=round(s["e"] + 시각, 3),
                        words=[dict(w, s=round(w["s"] + 시각, 3), e=round(w["e"] + 시각, 3)) for w in s.get("words", [])])
                   for s in 줄]
        파일들.append({"파일": 이름, "경로": p.replace("\\", "/"), "시작": round(시각, 3), "길이": round(길이, 3)})
        print("%-16s %6.1f분 · 구간 %4d개 · 이어 붙인 시작 %7.1f초" % (이름, 길이 / 60, len(줄), 시각))
        시각 += 길이
    json.dump(모든줄, io.open(os.path.join(작업, "cam_transcript.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(파일들, io.open(os.path.join(작업, "cam_files.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("합쳤다 · 전체 %.1f분 · 구간 %d개" % (시각 / 60, len(모든줄)))
