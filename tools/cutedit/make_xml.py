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

    python3 tools/cutedit/make_xml.py cuts.json out.xml
"""
import html
import io
import json
import os
import sys
from urllib.parse import quote


def rate(fps):
    """29.97 → (timebase 30, ntsc TRUE). 30 → (30, FALSE)."""
    tb = int(round(fps))
    ntsc = abs(fps - tb) > 0.001
    return tb, ("TRUE" if ntsc else "FALSE")


def frames(sec, fps):
    return int(round(sec * fps))


def pathurl(p):
    """프리미어가 내보내는 형태 그대로 — 퍼센트 인코딩한 file URL."""
    p = os.path.abspath(p).replace("\\", "/")
    return "file://localhost/" + quote(p.lstrip("/"), safe="/:")


def build(spec):
    fps = float(spec.get("fps", 29.97))
    tb, ntsc = rate(fps)
    w = int(spec.get("width", 1080))
    h = int(spec.get("height", 1920))
    name = spec.get("name", "sequence")
    R = f"<rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>"
    DF = "DF" if ntsc == "TRUE" else "NDF"

    # 원본 목록 — 한 개짜리 spec 도 여기로 모은다
    srcs = dict(spec.get("sources") or {})
    if "source" in spec:
        srcs.setdefault("_main", {"path": spec["source"],
                                  "dur": float(spec.get("src_dur", 0))})
    fid = {k: f"file-{i}" for i, k in enumerate(sorted(srcs), 1)}
    sfr = {k: frames(float(v.get("dur", 0)), fps) or 1 for k, v in srcs.items()}
    defined = set()

    def file_ref(k):
        """원본 파일은 처음 한 번만 자세히 적고, 뒤에서는 id 로만 가리킨다."""
        if k in defined:
            return f'<file id="{fid[k]}"/>'
        defined.add(k)
        p = srcs[k]["path"]
        return (
            f'<file id="{fid[k]}"><name>{html.escape(os.path.basename(p))}</name>'
            f"<pathurl>{html.escape(pathurl(p))}</pathurl>{R}"
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
        i_f, o_f = frames(float(c["in"]), fps), frames(float(c["out"]), fps)
        if o_f <= i_f:
            continue
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
        if has_video:
            en = "TRUE" if c.get("enabled", True) else "FALSE"   # 꺼 둔 클립 = 골라 쓸 참고 소스
            tracks.setdefault(("v", tr), []).append(dict(base, id=vid, en=en))
        if has_audio:
            for ch, aid in ((1, a1id), (2, a2id)):
                tracks.setdefault(("a", ch), []).append(dict(base, id=aid, en="TRUE"))

    for v in tracks.values():
        v.sort(key=lambda x: x["s"])
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
    def vclip(x):
        return (f'<clipitem id="{x["id"]}"><name>{x["label"]}</name><enabled>{x["en"]}</enabled>'
                f"<duration>{sfr[x['k']]}</duration>{R}"
                f"<start>{x['s']}</start><end>{x['e']}</end><in>{x['in']}</in><out>{x['out']}</out>"
                f"{file_ref(x['k'])}<compositemode>normal</compositemode>{link(x)}</clipitem>")

    def aclip(x, ch):
        return (f'<clipitem id="{x["id"]}"><name>{x["label"]}</name><enabled>TRUE</enabled>'
                f"<duration>{sfr[x['k']]}</duration>{R}"
                f"<start>{x['s']}</start><end>{x['e']}</end><in>{x['in']}</in><out>{x['out']}</out>"
                f"{file_ref(x['k'])}"
                f"<sourcetrack><mediatype>audio</mediatype>"
                f"<trackindex>{ch}</trackindex></sourcetrack>{link(x)}</clipitem>")

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
        "</audio></media></sequence>\n</xmeml>\n"), vtracks


def main():
    if len(sys.argv) < 3:
        sys.exit("사용법: make_xml.py 컷리스트.json 결과.xml")
    spec = json.load(io.open(sys.argv[1], encoding="utf-8"))
    xml, vtracks = build(spec)
    io.open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(xml)
    tb, _ = rate(float(spec.get("fps", 29.97)))
    print(sys.argv[2])
    for t in sorted(vtracks):
        cs = [c for c in spec["cuts"] if int(c.get("track", 1)) == t]
        total = sum(float(c["out"]) - float(c["in"]) for c in cs)
        print(f"   V{t}  컷 {len(vtracks[t])}개 · 길이 {total:.2f}초")
    print(f"   {tb}fps · {spec.get('width', 1080)}x{spec.get('height', 1920)}")


if __name__ == "__main__":
    main()
