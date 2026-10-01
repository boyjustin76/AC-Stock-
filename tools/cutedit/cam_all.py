# -*- coding: utf-8 -*-
"""캠 한 파일 → 정렬 → 컷리스트 → 자막 → 프리미어 XML 을 한 번에.

전제 (2026-10-01 마01 에서 확정)
  · 캠 소스는 **29.97 고정 .mp4 한 개**다. 아이폰 .MOV(가변 240fps)는 프리미어가
    XML 가져오기에서 통째로 거부한다 — 성공한 회차는 모두 고정 프레임 .mp4 였다.
  · XML 은 **얇게** 쓴다(masterclipid·pproTicks·link 없이). 프리미어가 알아서 채운다.

    python3 tools/cutedit/cam_all.py <작업폴더> <대본.json> <영상.mp4> <낼 XML> <낼 SRT> [이름]
      작업폴더에 cam_transcript.json · cam_files.json 이 미리 있어야 한다 (cam_prep.py)
"""
import io, os, sys, json, subprocess

여기 = os.path.dirname(os.path.abspath(__file__))


def 돌리기(*인자):
    print("$", " ".join(os.path.basename(str(a)) for a in 인자), flush=True)
    r = subprocess.run([sys.executable] + [str(a) for a in 인자], capture_output=True, text=True, encoding="utf-8")
    print((r.stdout or "").strip()[-1500:], flush=True)
    if r.returncode: sys.exit((r.stderr or "")[-800:])
    return r.stdout


if __name__ == "__main__":
    작업, 대본길, 영상, 낼xml, 낼srt = sys.argv[1:6]
    이름 = sys.argv[6] if len(sys.argv) > 6 else "마01_캠_컷"
    대본txt = os.path.join(작업, "대본.txt")
    if not os.path.exists(대본txt):
        돌리기(os.path.join(여기, "script_txt.py"), 대본길, 대본txt)
    돌리기(os.path.join(여기, "align_take.py"), 작업, 대본txt)
    컷길 = os.path.join(작업, "컷리스트.json")
    돌리기(os.path.join(여기, "cam_cutlist.py"), 작업, 대본길, os.path.join(작업, "소리.json"), 컷길, 이름)
    # 원본 길이는 실제 초로 — 끝을 넘기면 프리미어가 거부한다
    import av
    with av.open(영상) as c:
        길이 = float(c.duration) / av.time_base
    spec = json.load(io.open(컷길, encoding="utf-8"))
    spec["fps"] = 29.97
    for v in spec["sources"].values():
        v["dur"] = 길이; v.pop("fps", None)
    spec["얇게"] = True
    json.dump(spec, io.open(컷길, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    돌리기(os.path.join(여기, "cam_srt.py"), 작업, 컷길, 낼srt)
    돌리기(os.path.join(여기, "make_xml.py"), 컷길, 낼xml)
    돌리기(os.path.join(여기, "srt_rules.py"), "check", 낼srt)
    print("\n끝. XML %s · SRT %s" % (낼xml, 낼srt))
