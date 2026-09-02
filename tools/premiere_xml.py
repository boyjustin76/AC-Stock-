#!/usr/bin/env python3
"""프리미어가 가져올 수 있는 시퀀스 XML(FCP7 xmeml)을 만든다.

.prproj 는 직접 쓰지 않는다(금지 규칙 — psd 전례). 대신 프리미어가 공식으로
가져오는 교환 포맷(Final Cut Pro XML, xmeml v4)을 쓴다: 파일 > 가져오기로
.xml 을 열면 컷들이 타임라인에 배치된 시퀀스가 프로젝트에 생긴다.

미디어 연결: pathurl 은 절대경로라 사용자의 압축 해제 위치와 다르면 오프라인으로
뜬다. 첫 파일 하나만 '미디어 연결'로 찾아 주면 같은 폴더의 나머지는 프리미어가
자동으로 찾는다. pathurl 을 C:/<zip 폴더명>/... 으로 박아 두므로 zip 을 C:\ 바로
아래에 풀면 연결까지 자동이다.

사용:
  python3 tools/premiere_xml.py --name ch11-4_chart --fps 30 --size 1080x1080 \
      --root ch11-4_v9 --clips chart/cut1.mp4:245,chart/cut2.mp4:176,... \
      --audio narration.wav:1301 --out seq.xml

클립 길이는 프레임 수(시퀀스 timebase 기준). --at 로 갭 배치도 된다:
  --clips "chart/cut1.mp4:245@0,chart/cut2.mp4:176@300"  (300프레임 지점에 배치)
"""
import argparse
from xml.sax.saxutils import escape


def rate(tb, ntsc='FALSE'):
    return f'<rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>'


def build(name, fps, w, h, root, clips, audio=None, ntsc='FALSE'):
    tb = fps
    total = 0
    for _, dur, at in clips:
        total = max(total, (at if at is not None else total) + dur)
    if audio:
        total = max(total, audio[1])

    vitems = []
    pos = 0
    files = {}

    def fileref(path, dur, has_audio):
        fid = f'file-{len(files) + 1}'
        if path in files:
            return f'<file id="{files[path]}"/>'
        files[path] = fid
        url = f'file://localhost/C:/{root}/{path}'.replace(' ', '%20')
        media = f'<video><samplecharacteristics><width>{w}</width><height>{h}</height></samplecharacteristics></video>'
        if has_audio:
            media += '<audio><samplecharacteristics><samplerate>48000</samplerate><depth>16</depth></samplecharacteristics><channelcount>2</channelcount></audio>'
        if path == (audio[0] if audio else None):
            media = '<audio><samplecharacteristics><samplerate>48000</samplerate><depth>16</depth></samplecharacteristics><channelcount>2</channelcount></audio>'
        return (f'<file id="{fid}"><name>{escape(path.split("/")[-1])}</name>'
                f'<pathurl>{escape(url)}</pathurl>{rate(tb, ntsc)}'
                f'<duration>{dur}</duration><media>{media}</media></file>')

    for i, (path, dur, at) in enumerate(clips):
        start = at if at is not None else pos
        end = start + dur
        pos = end
        vitems.append(
            f'<clipitem id="v{i + 1}"><name>{escape(path.split("/")[-1])}</name><enabled>TRUE</enabled>'
            f'<duration>{dur}</duration>{rate(tb, ntsc)}'
            f'<start>{start}</start><end>{end}</end><in>0</in><out>{dur}</out>'
            f'{fileref(path, dur, False)}'
            f'<compositemode>normal</compositemode></clipitem>'
        )

    aitems = []
    if audio:
        apath, adur = audio
        aitems.append(
            f'<clipitem id="a1"><name>{escape(apath.split("/")[-1])}</name><enabled>TRUE</enabled>'
            f'<duration>{adur}</duration>{rate(tb, ntsc)}'
            f'<start>0</start><end>{adur}</end><in>0</in><out>{adur}</out>'
            f'{fileref(apath, adur, False)}'
            f'<sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack></clipitem>'
        )

    audio_block = f'<audio><track>{"".join(aitems)}</track></audio>' if aitems else '<audio/>'
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
<sequence id="{escape(name)}">
 <name>{escape(name)}</name>
 <duration>{total}</duration>
 {rate(tb, ntsc)}
 <media>
  <video>
   <format><samplecharacteristics>{rate(tb, ntsc)}<width>{w}</width><height>{h}</height>
    <pixelaspectratio>square</pixelaspectratio><anamorphic>FALSE</anamorphic>
   </samplecharacteristics></format>
   <track>{''.join(vitems)}</track>
  </video>
  {audio_block}
 </media>
</sequence>
</xmeml>
'''


def parse_clips(s):
    out = []
    for part in s.split(','):
        part = part.strip()
        at = None
        if '@' in part:
            part, at = part.rsplit('@', 1)
            at = int(at)
        path, dur = part.rsplit(':', 1)
        out.append((path, int(dur), at))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True)
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--ntsc', default='FALSE')
    ap.add_argument('--size', default='1080x1080')
    ap.add_argument('--root', required=True, help='C:/ 아래 기준 폴더명 (zip 폴더명)')
    ap.add_argument('--clips', required=True, help='경로:프레임수[@시작프레임],...')
    ap.add_argument('--audio', help='경로:프레임수')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    w, h = map(int, a.size.split('x'))
    audio = None
    if a.audio:
        p, d = a.audio.rsplit(':', 1)
        audio = (p, int(d))
    xml = build(a.name, a.fps, w, h, a.root, parse_clips(a.clips), audio, a.ntsc)
    open(a.out, 'w', encoding='utf-8').write(xml)
    print(a.out, '완료')
