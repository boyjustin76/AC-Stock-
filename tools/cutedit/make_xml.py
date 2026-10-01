# -*- coding: utf-8 -*-
"""컷리스트 → 프리미어가 읽는 시퀀스 XML (FCP7 xmeml v4).

원본에서 구간을 골라 V1 에 순서대로 이어 붙인다. 영상·오디오는 링크시켜서
프리미어에서 한 덩어리로 잡히게 한다. 위 트랙(V2~)에 시각자료를 얹을 수도 있다.

컷리스트(json) 모양 — 원본 하나
  {"source": "C:/.../원본.mp4", "name": "시퀀스 이름",
   "fps": 29.97, "width": 1080, "height": 1920, "src_dur": 184.48,
   "cuts": [{"in": 12.34, "out": 15.10, "label": "인트로 1"}, ...]}

원본 여럿 · 트랙 여럿
  {"sources": {"캠": {"path": "...", "dur": 882.2}, "PD": {"path": "...", "dur": 1682.4}},
   "cuts": [{"src": "캠", "in": 1.2, "out": 5.0},
            {"src": "PD", "in": 300.0, "out": 312.5, "track": 2, "at": 40.1, "audio": false}]}

  in/out 은 원본 기준 초. V1 컷은 순서대로 자동으로 이어진다.
  V2 이상은 'at'(시퀀스 위 시작 초)이 있어야 한다. audio:false 면 영상만 올린다.

    python3 tools/cutedit/make_xml.py cuts.json out.xml [--source-root <원본폴더>]

  컷리스트에 적힌 원본 경로는 **컷을 딴 그 PC 의 자리**다. 꾸러미를 다른 PC 에 풀었거나 원본을
  옮겼으면 `--source-root` 로 원본이 든 폴더를 준다 — 파일 이름만 떼어 그 폴더에 붙인다.
  (json 은 손대지 않는다. 컷 값은 원본 파일에 대한 것이라 그대로 맞는다.)
"""
import html
import io
import json
import os
import re
import sys
from urllib.parse import quote


def rate(fps):
    """29.97 → (timebase 30, ntsc TRUE). 30 → (30, FALSE)."""
    tb = int(round(fps))
    ntsc = abs(fps - tb) > 0.001
    return tb, ("TRUE" if ntsc else "FALSE")


def frames(sec, fps):
    return int(round(sec * fps))


# 프리미어가 **스스로 내보낸** XML 의 pathurl 에서 그대로 두는 글자 (차트설명_이정찬.xml 실측).
# 괄호·대괄호·& 를 퍼센트로 바꾸면 프리미어가 그 경로를 못 찾고, 그 상태에서 clipitem 이 여럿이면
# 임시 .prproj 변환이 깨진다 → "프로젝트가 손상되어 열 수 없습니다". 컷이 적을 때만 통과해서
# 클립 수 문제로 보였다 (D 세션이 프리미어 27.10.0 에 직접 넣어 확정, 2026-10-01).
_SAFE = "/()[]&~!$'*+,;=@_-."


def pathurl(p):
    """프리미어가 내보내는 형태 그대로 — 퍼센트 인코딩한 file URL."""
    # 드라이브 문자로 시작하는 윈도우 경로는 abspath 를 거치지 않는다 — 리눅스(총괄 컨테이너)에서 abspath 가
    # 앞에 cwd 를 붙여 'file://localhost/home/…/C:/…' 이 됐다 (tests/test_cutedit.py 가 잡음, 2026-09-17 총괄)
    if not re.match(r"^[A-Za-z]:[\\/]", p):
        p = os.path.abspath(p)
    p = p.replace("\\", "/")
    # 드라이브 콜론도 인코딩한다 — 프리미어는 `C%3a/` 로 쓴다 (safe 에 ':' 를 넣지 않는다)
    u = quote(p.lstrip("/"), safe=_SAFE)
    # 16진은 **소문자**다 — 프리미어 표기 그대로
    u = re.sub(r"%[0-9A-F]{2}", lambda m: m.group(0).lower(), u)
    return "file://localhost/" + u


def build(spec, source_root=None):
    fps = float(spec.get("fps", 29.97))
    tb, ntsc = rate(fps)
    w = int(spec.get("width", 1080))
    h = int(spec.get("height", 1920))
    name = spec.get("name", "sequence")
    R = f"<rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>"
    DF = "DF" if ntsc == "TRUE" else "NDF"

    # 원본 목록 — 한 개짜리 spec 도 여기로 모은다
    srcs = {k: dict(v) for k, v in (spec.get("sources") or {}).items()}   # 원본 spec 은 안 건드린다
    if "source" in spec:
        srcs.setdefault("_main", {"path": spec["source"],
                                  "dur": float(spec.get("src_dur", 0))})
    if source_root:                      # 원본이 다른 자리에 있을 때 — 이름만 떼어 그 폴더에 붙인다
        for k, v in srcs.items():
            p = os.path.join(source_root, os.path.basename(v["path"].replace("\\", "/")))
            if not os.path.exists(p):
                raise SystemExit(f"원본을 못 찾았습니다: {p}")
            v["path"] = p
    fid = {k: f"file-{i}" for i, k in enumerate(sorted(srcs), 1)}
    # 원본 박자. FCP7 XML 의 timebase 는 24·25·30·50·60 만 쓴다 — 아이폰 240fps 를 그대로 적으면
    # 프리미어가 "프로젝트가 손상되어 열 수 없습니다" 로 가져오기를 통째로 실패한다 (마01 캠 2026-10-01).
    # 그런 원본은 시퀀스 박자로 적는다. in/out 을 '초 × 시퀀스 박자' 로 세면 자리는 그대로 맞는다.
    sfps = {k: (float(v["fps"]) if v.get("fps") and float(v["fps"]) <= 60.5 else fps)
            for k, v in srcs.items()}
    import math
    # 끝 프레임은 **내림**으로 센다. 반올림하면 실제 미디어 끝을 1~8프레임 넘고,
    # 프리미어는 그런 클립이 하나라도 있으면 가져오기를 통째로 거부한다 (D 세션 실측 2026-10-01).
    sfr = {k: max(1, math.floor(float(v.get("dur", 0)) * sfps[k])) for k, v in srcs.items()}
    defined = set()

    def file_ref(k):
        """원본 파일은 처음 한 번만 자세히 적고, 뒤에서는 id 로만 가리킨다."""
        if k in defined:
            return f'<file id="{fid[k]}"/>'
        defined.add(k)
        p = srcs[k]["path"]
        ftb, fntsc = rate(sfps[k])
        FR = f"<rate><timebase>{ftb}</timebase><ntsc>{fntsc}</ntsc></rate>"
        return (
            f'<file id="{fid[k]}"><name>{html.escape(os.path.basename(p))}</name>'
            f"<pathurl>{html.escape(pathurl(p))}</pathurl>{FR}"
            f"<duration>{sfr[k]}</duration>"
            f"<timecode>{R}<string>00:00:00:00</string><frame>0</frame>"
            f"<displayformat>{DF}</displayformat></timecode>"
            f"<media><video><samplecharacteristics>{R}"
            f"<width>{w}</width><height>{h}</height>"
            f"<pixelaspectratio>square</pixelaspectratio><anamorphic>FALSE</anamorphic>"
            f"</samplecharacteristics></video>"
            f"<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate>"
            f"</samplecharacteristics><channelcount>2</channelcount></audio></media></file>")

    # 트랙 → 클립들. 다 모은 뒤 트랙마다 시작 순서로 세워서 적는다.
    # 프리미어는 트랙 안 클립 순서가 뒤섞인 XML 을 제대로 못 읽는다 — L08 합본에서 캠 컷 27개 뒤에
    # 시연 클립 30개를 붙여 적었더니 시연 클립이 대부분 안 보이고 남은 것도 깜빡였다 (2026-09-11).
    tracks = {}
    at = 0                       # V1 위 현재 자리 (프레임)
    end_max = 0
    for i, c in enumerate(spec["cuts"], 1):
        k = c.get("src", "_main")
        if k not in srcs:
            raise SystemExit(f"컷 {i}: 원본 '{k}' 이 sources 에 없습니다")
        i_f = frames(float(c["in"]), sfps[k])
        o_f = min(frames(float(c["out"]), sfps[k]), sfr[k])     # 원본 끝을 넘지 않게
        i_f = min(i_f, max(0, sfr[k] - 1))
        if o_f <= i_f:
            continue
        # **타임라인 길이와 원본 구간 길이는 반드시 같아야 한다.** 따로 반올림했더니 1~2프레임씩
        # 어긋났고, 프리미어가 "프로젝트가 손상되어 열 수 없습니다" 로 가져오기를 통째로 거부했다
        # (마01 캠 2026-10-01 — 컷이 서넛일 땐 우연히 맞아 넘어가고 일곱 개부터 걸렸다).
        n = o_f - i_f
        tr = int(c.get("track", 1))
        has_audio = c.get("audio", True)
        has_video = c.get("video", True)
        if not (has_audio or has_video):
            continue
        if "at" in c:
            s = frames(float(c["at"]), fps)
        elif tr == 1 and has_video:
            s = at
        else:
            raise SystemExit(f"V{tr}·오디오만 클립은 'at' 이 필요합니다 (컷 {i})")
        e = s + n
        if tr == 1 and has_video:
            at = e
        end_max = max(end_max, e)
        label = html.escape(c.get("label") or f"cut{i}")
        vid, a1id, a2id = f"cv{i}", f"ca{i}a", f"ca{i}b"
        linked = (vid, a1id, a2id) if has_audio and has_video else None
        base = {"s": s, "e": e, "in": i_f, "out": o_f, "k": k, "label": label, "linked": linked}
        en = "TRUE" if c.get("enabled", True) else "FALSE"       # 꺼 둔 클립 = 골라 쓸 참고 소스
        if has_video:
            tracks.setdefault(("v", tr), []).append(dict(base, id=vid, en=en))
        if has_audio:
            # 소리도 영상과 같이 끈다 — 안 쓰는 테이크 소리가 울리면 안 된다
            for ch, aid in ((1, a1id), (2, a2id)):
                tracks.setdefault(("a", ch), []).append(dict(base, id=aid, en=en))

    for v in tracks.values():
        v.sort(key=lambda x: x["s"])
        # 한 트랙 안에서 1프레임이라도 겹치면 프리미어가 프로젝트를 못 읽는다 (마01 캠 2026-10-01).
        # 'at' 을 초로 줘서 생기는 반올림 겹침은 여기서 뒤로 민다.
        for 앞, 뒤 in zip(v, v[1:]):
            if 뒤["s"] < 앞["e"]:
                밀기 = 앞["e"] - 뒤["s"]
                뒤["s"] += 밀기; 뒤["e"] += 밀기
                end_max = max(end_max, 뒤["e"])
    where = {x["id"]: (key[1], j) for key, v in tracks.items() for j, x in enumerate(v, 1)}

    def link(x):
        if not x["linked"]:
            return ""
        vid, a1id, a2id = x["linked"]
        (vt, vi), (_, i1), (_, i2) = where[vid], where[a1id], where[a2id]
        return (
            f"<link><linkclipref>{vid}</linkclipref><mediatype>video</mediatype>"
            f"<trackindex>{vt}</trackindex><clipindex>{vi}</clipindex></link>"
            f"<link><linkclipref>{a1id}</linkclipref><mediatype>audio</mediatype>"
            f"<trackindex>1</trackindex><clipindex>{i1}</clipindex>"
            f"<groupindex>1</groupindex></link>"
            f"<link><linkclipref>{a2id}</linkclipref><mediatype>audio</mediatype>"
            f"<trackindex>2</trackindex><clipindex>{i2}</clipindex>"
            f"<groupindex>1</groupindex></link>")

    # 파일은 문서에 처음 나오는 클립에서 자세히 적는다 (영상 트랙 → 오디오 트랙 순서로 적으므로 여기서 부른다)
    def 클립박자(k):
        ftb, fntsc = rate(sfps[k])
        return f"<rate><timebase>{ftb}</timebase><ntsc>{fntsc}</ntsc></rate>"

    얇게 = bool(spec.get("얇게"))

    def vclip(x):
        return (f'<clipitem id="{x["id"]}"><name>{x["label"]}</name><enabled>{x["en"]}</enabled>'
                f"<duration>{sfr[x['k']]}</duration>{클립박자(x['k'])}"
                f"<start>{x['s']}</start><end>{x['e']}</end><in>{x['in']}</in><out>{x['out']}</out>"
                f"{file_ref(x['k'])}<compositemode>normal</compositemode>"
                f"{'' if 얇게 else link(x)}</clipitem>")

    def aclip(x, ch):
        return (f'<clipitem id="{x["id"]}"><name>{x["label"]}</name><enabled>{x["en"]}</enabled>'
                f"<duration>{sfr[x['k']]}</duration>{클립박자(x['k'])}"
                f"<start>{x['s']}</start><end>{x['e']}</end><in>{x['in']}</in><out>{x['out']}</out>"
                f"{file_ref(x['k'])}"
                f"<sourcetrack><mediatype>audio</mediatype>"
                f"<trackindex>{ch}</trackindex></sourcetrack>"
                f"{'' if 얇게 else link(x)}</clipitem>")

    # 시퀀스 마커 — 컷리스트의 "markers": [{"at": 초, "name": "박수", "comment": "…", "dur": 초}]
    # 프리미어는 <marker> 를 시퀀스 바로 아래에서 읽는다. 시작 프레임만 있으면 점 마커가 된다.
    def 마커(m):
        s = frames(float(m["at"]), fps)
        끝 = s + frames(float(m.get("dur", 0)), fps)
        return ("<marker>"
                f"<name>{html.escape(str(m.get('name', '')))}</name>"
                f"<comment>{html.escape(str(m.get('comment', '')))}</comment>"
                f"<in>{s}</in><out>{끝 if 끝 > s else -1}</out></marker>")
    마커들 = "" if spec.get("마커빼기") else "".join(마커(m) for m in spec.get("markers", []))

    nv = max([t for kind, t in tracks if kind == "v"] or [1])
    vtracks = {t: tracks.get(("v", t), []) for t in range(1, nv + 1) if ("v", t) in tracks}
    vxml = "".join("<track>" + "".join(vclip(x) for x in tracks.get(("v", t), [])) + "</track>"
                   for t in range(1, nv + 1))

    def atrack(ch):
        return ("<track>" + "".join(aclip(x, ch) for x in tracks.get(("a", ch), [])) +
                f"<outputchannelindex>{ch}</outputchannelindex></track>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4">\n'
        f"<sequence id=\"{html.escape(name)}\"><name>{html.escape(name)}</name>"
        f"<duration>{end_max}</duration>{R}"
        f"<timecode>{R}<string>00:00:00:00</string><frame>0</frame>"
        f"<displayformat>{DF}</displayformat></timecode>"
        "<media><video><format><samplecharacteristics>"
        f"{R}<width>{w}</width><height>{h}</height>"
        "<pixelaspectratio>square</pixelaspectratio><anamorphic>FALSE</anamorphic>"
        "</samplecharacteristics></format>"
        + vxml + "</video>"
        "<audio><numOutputChannels>2</numOutputChannels>"
        "<format><samplecharacteristics><depth>16</depth>"
        "<samplerate>48000</samplerate></samplecharacteristics></format>"
        + atrack(1) + atrack(2) +
        "</audio></media>" + 마커들 + "</sequence>\n</xmeml>\n"), vtracks


def main():
    args = sys.argv[1:]
    root = None
    if "--source-root" in args:
        k = args.index("--source-root")
        root = args[k + 1]
        del args[k:k + 2]
    if len(args) < 2:
        sys.exit("사용법: make_xml.py 컷리스트.json 결과.xml [--source-root <원본폴더>]")
    spec = json.load(io.open(args[0], encoding="utf-8"))
    xml, vtracks = build(spec, source_root=root)
    io.open(args[1], "w", encoding="utf-8", newline="\n").write(xml)
    tb, _ = rate(float(spec.get("fps", 29.97)))
    print(args[1])
    for t in sorted(vtracks):
        cs = [c for c in spec["cuts"] if int(c.get("track", 1)) == t]
        total = sum(float(c["out"]) - float(c["in"]) for c in cs)
        print(f"   V{t}  컷 {len(vtracks[t])}개 · 길이 {total:.2f}초")
    print(f"   {tb}fps · {spec.get('width', 1080)}x{spec.get('height', 1920)}")


if __name__ == "__main__":
    main()
