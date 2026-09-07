# -*- coding: utf-8 -*-
"""컷리스트 → 프리미어가 읽는 시퀀스 XML (FCP7 xmeml v4).

원테이크 원본 하나에서 구간을 골라 순서대로 이어 붙인 시퀀스를 만든다.
영상·오디오는 링크시켜서 프리미어에서 한 덩어리로 잡히게 한다.

컷리스트(json) 모양 —
  {"source": "C:/.../원본.mp4", "name": "시퀀스 이름",
   "fps": 29.97, "width": 1080, "height": 1920, "src_dur": 184.48,
   "cuts": [{"in": 12.34, "out": 15.10, "label": "인트로 1"}, ...]}

  in/out 은 원본 기준 초. 시퀀스 위 자리는 컷 순서대로 자동으로 이어진다.

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
    src = spec["source"]
    src_frames = frames(float(spec.get("src_dur", 0)), fps) or 1
    R = f"<rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>"

    # 원본 파일은 한 번만 자세히 적고, 뒤에서는 id 로만 가리킨다.
    filedef = (
        f'<file id="file-1"><name>{html.escape(os.path.basename(src))}</name>'
        f"<pathurl>{html.escape(pathurl(src))}</pathurl>{R}"
        f"<duration>{src_frames}</duration>"
        f"<timecode>{R}<string>00:00:00:00</string><frame>0</frame>"
        f"<displayformat>{'DF' if ntsc == 'TRUE' else 'NDF'}</displayformat></timecode>"
        f"<media><video><samplecharacteristics>{R}"
        f"<width>{w}</width><height>{h}</height>"
        f"<pixelaspectratio>square</pixelaspectratio><anamorphic>FALSE</anamorphic>"
        f"</samplecharacteristics></video>"
        f"<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate>"
        f"</samplecharacteristics><channelcount>2</channelcount></audio></media></file>"
    )

    v, a1, a2 = [], [], []
    at = 0                       # 시퀀스 위 현재 자리 (프레임)
    for i, c in enumerate(spec["cuts"], 1):
        i_f, o_f = frames(float(c["in"]), fps), frames(float(c["out"]), fps)
        if o_f <= i_f:
            continue
        n = o_f - i_f
        s, e = at, at + n
        at = e
        label = html.escape(c.get("label") or f"cut{i}")
        vid, a1id, a2id = f"cv{i}", f"ca{i}a", f"ca{i}b"
        f_ref = filedef if i == 1 else '<file id="file-1"/>'
        link = (
            f"<link><linkclipref>{vid}</linkclipref><mediatype>video</mediatype>"
            f"<trackindex>1</trackindex><clipindex>{i}</clipindex></link>"
            f"<link><linkclipref>{a1id}</linkclipref><mediatype>audio</mediatype>"
            f"<trackindex>1</trackindex><clipindex>{i}</clipindex>"
            f"<groupindex>1</groupindex></link>"
            f"<link><linkclipref>{a2id}</linkclipref><mediatype>audio</mediatype>"
            f"<trackindex>2</trackindex><clipindex>{i}</clipindex>"
            f"<groupindex>1</groupindex></link>")
        v.append(
            f'<clipitem id="{vid}"><name>{label}</name><enabled>TRUE</enabled>'
            f"<duration>{src_frames}</duration>{R}"
            f"<start>{s}</start><end>{e}</end><in>{i_f}</in><out>{o_f}</out>"
            f"{f_ref}<compositemode>normal</compositemode>{link}</clipitem>")
        for ch, aid, bucket in ((1, a1id, a1), (2, a2id, a2)):
            bucket.append(
                f'<clipitem id="{aid}"><name>{label}</name><enabled>TRUE</enabled>'
                f"<duration>{src_frames}</duration>{R}"
                f"<start>{s}</start><end>{e}</end><in>{i_f}</in><out>{o_f}</out>"
                f'<file id="file-1"/>'
                f"<sourcetrack><mediatype>audio</mediatype>"
                f"<trackindex>{ch}</trackindex></sourcetrack>{link}</clipitem>")

    def atrack(items, ch):
        return ("<track>" + "".join(items) +
                f"<outputchannelindex>{ch}</outputchannelindex></track>")

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4">\n'
        f"<sequence id=\"{html.escape(name)}\"><name>{html.escape(name)}</name>"
        f"<duration>{at}</duration>{R}"
        f"<timecode>{R}<string>00:00:00:00</string><frame>0</frame>"
        f"<displayformat>{'DF' if ntsc == 'TRUE' else 'NDF'}</displayformat></timecode>"
        "<media><video><format><samplecharacteristics>"
        f"{R}<width>{w}</width><height>{h}</height>"
        "<pixelaspectratio>square</pixelaspectratio><anamorphic>FALSE</anamorphic>"
        "</samplecharacteristics></format>"
        "<track>" + "".join(v) + "</track></video>"
        "<audio><numOutputChannels>2</numOutputChannels>"
        "<format><samplecharacteristics><depth>16</depth>"
        "<samplerate>48000</samplerate></samplecharacteristics></format>"
        + atrack(a1, 1) + atrack(a2, 2) +
        "</audio></media></sequence>\n</xmeml>\n")


def main():
    if len(sys.argv) < 3:
        sys.exit("사용법: make_xml.py 컷리스트.json 결과.xml")
    spec = json.load(io.open(sys.argv[1], encoding="utf-8"))
    xml = build(spec)
    io.open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(xml)
    tb, _ = rate(float(spec.get("fps", 29.97)))
    total = sum(float(c["out"]) - float(c["in"]) for c in spec["cuts"])
    print(f"{sys.argv[2]} — 컷 {len(spec['cuts'])}개, 길이 {total:.2f}초 ({tb}fps 기준)")


if __name__ == "__main__":
    main()
