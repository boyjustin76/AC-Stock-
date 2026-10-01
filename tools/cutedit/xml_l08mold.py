"""컷리스트 → 프리미어 FCP7 XML. **L08·차12 성공본과 같은 꼴**로 찍어 낸다.

    python tools/cutedit/xml_l08mold.py <컷리스트.json> -o <나갈.xml> [--all] [--name 이름]

왜 이 틀인가 (2026-10-01, D)
  프리미어가 가져오기를 거부한 파일들과 **들어간 파일들**을 맞대 보니 구조 차이가 없었다.
  그래서 짐작으로 고치지 않고, **실제로 들어간 적이 있는 두 파일의 꼴을 그대로 뜬다**:
    · L08_더블볼린저밴드매매법_260923_전체_컷편집.xml (클립 158개, 캠+시연 2소스)
    · 차12 시퀀스 xml (tools/legacy/premiere_xml.py, 사용자 실물 확인)
  그 꼴의 특징 — 얇다. masterclipid·pproTicks·logginginfo·colorinfo·labels 가 **없다**.
  대신 **link 세 줄**(영상1 + 소리2)이 모든 clipitem 에 붙고, 소리 트랙 끝에
  outputchannelindex 가 붙는다. <file> 전체 정의는 그 파일을 처음 쓰는 clipitem 안에만 두고,
  그 뒤에는 <file id="..."/> 로만 가리킨다.

컷리스트 꼴
    {"name":…, "fps":29.97, "width":1920, "height":1080,
     "sources": {"키": {"path": "C:/…/x.mp4", "dur": 729.795}},
     "cuts": [{"src":"키", "in":4.24, "out":49.18, "label":"…", "track":1, "enabled":true}, …],
     "markers": [{"at":0.0, "name":"…", "comment":"…"}]}
"""
import argparse
import io
import json
import os
import re
import urllib.parse
from xml.sax.saxutils import escape

NTSC_FPS = 30000 / 1001


def rate(tb=30, ntsc='TRUE'):
    return f'<rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>'


def timecode(tb=30, ntsc='TRUE', df='DF'):
    return (f'<timecode>{rate(tb, ntsc)}<string>00:00:00:00</string>'
            f'<frame>0</frame><displayformat>{df}</displayformat></timecode>')


#  프리미어가 **스스로 내보낸** XML 에서 실측한 표기 (2026-10-01, 차트설명_이정찬.xml):
#     file://localhost/C%3a/Users/user/Desktop/%ec%9d%b4…/…(OBS)[%ed%99%95%eb%b3%b4]/2026-09-30%2015-15-50.mp4
#  → 드라이브 콜론은 %3a · 16진은 **소문자** · 괄호 ( ) [ ] & ~ 는 **안 바꾼다** · 공백만 %20.
#  우리가 ( ) [ ] 를 %28%29%5B%5D 로 바꿔 쓰니 프리미어가 그 경로의 미디어를 못 찾았고,
#  그 상태에서 컷이 여럿이면 변환이 "프로젝트가 손상되어 열 수 없습니다" 로 깨졌다 (실측 10-01).
_URL_SAFE = "/()[]&~!$'*+,;=@_-."


def pathurl(p):
    p = p.replace('\\', '/')
    out = urllib.parse.quote(p, safe=_URL_SAFE, encoding='utf-8')
    out = re.sub(r'%[0-9A-F]{2}', lambda m: m.group(0).lower(), out)
    return 'file://localhost/' + out


def file_block(fid, path, frames, w, h):
    return (f'<file id="{fid}"><name>{escape(os.path.basename(path))}</name>'
            f'<pathurl>{escape(pathurl(path))}</pathurl>{rate()}'
            f'<duration>{frames}</duration>{timecode()}'
            f'<media><video><samplecharacteristics>{rate()}'
            f'<width>{w}</width><height>{h}</height>'
            f'<pixelaspectratio>square</pixelaspectratio><anamorphic>FALSE</anamorphic>'
            f'</samplecharacteristics></video>'
            f'<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate>'
            f'</samplecharacteristics><channelcount>2</channelcount></audio></media></file>')


def links(n):
    """영상1 + 소리2 를 한 덩어리로 묶는 세 줄. L08 과 같은 차례·같은 값."""
    return (f'<link><linkclipref>cv{n}</linkclipref><mediatype>video</mediatype>'
            f'<trackindex>1</trackindex><clipindex>{n}</clipindex></link>'
            f'<link><linkclipref>ca{n}a</linkclipref><mediatype>audio</mediatype>'
            f'<trackindex>1</trackindex><clipindex>{n}</clipindex><groupindex>1</groupindex></link>'
            f'<link><linkclipref>ca{n}b</linkclipref><mediatype>audio</mediatype>'
            f'<trackindex>2</trackindex><clipindex>{n}</clipindex><groupindex>1</groupindex></link>')


def build(cl, use_all=False, name=None):
    w, h = cl.get('width', 1920), cl.get('height', 1080)
    seq_name = name or cl.get('name', 'sequence')

    # 소스: 파일 길이를 프레임으로 (초 → 내림. 올리면 out 이 끝을 넘는다 — 09-30 사고)
    srcs, fids = {}, {}
    for i, (key, s) in enumerate(cl['sources'].items(), start=1):
        frames = int(s['dur'] * NTSC_FPS)
        srcs[key] = {'path': s['path'], 'frames': frames}
        fids[key] = f'file-{i}'

    cuts = [c for c in cl['cuts'] if use_all or (c.get('track', 1) in (1, 'V1') and c.get('enabled', True))]

    rows, pos = [], 0
    for c in cuts:
        s = srcs[c['src']]
        fi = round(c['in'] * NTSC_FPS)
        fo = round(c['out'] * NTSC_FPS)
        if fo > s['frames']:                       # 끝을 넘지 않게 자른다
            fo = s['frames']
        if fo <= fi:
            continue
        rows.append({'src': c['src'], 'in': fi, 'out': fo, 'start': pos, 'end': pos + (fo - fi),
                     'label': c.get('label', os.path.basename(s['path']))})
        pos += fo - fi
    total = pos

    seen = set()

    def fref(key, first_use_ok=True):
        fid = fids[key]
        if fid in seen or not first_use_ok:
            return f'<file id="{fid}"/>'
        seen.add(fid)
        return file_block(fid, srcs[key]['path'], srcs[key]['frames'], w, h)

    v, a1, a2 = [], [], []
    for n, r in enumerate(rows, start=1):
        head = (f'<name>{escape(r["label"])}</name><enabled>TRUE</enabled>'
                f'<duration>{srcs[r["src"]]["frames"]}</duration>{rate()}'
                f'<start>{r["start"]}</start><end>{r["end"]}</end>'
                f'<in>{r["in"]}</in><out>{r["out"]}</out>')
        v.append(f'<clipitem id="cv{n}">{head}{fref(r["src"])}'
                 f'<compositemode>normal</compositemode>{links(n)}</clipitem>')
        for ch, bucket in ((1, a1), (2, a2)):
            bucket.append(
                f'<clipitem id="ca{n}{"a" if ch == 1 else "b"}">{head}'
                f'<file id="{fids[r["src"]]}"/>'
                f'<sourcetrack><mediatype>audio</mediatype><trackindex>{ch}</trackindex></sourcetrack>'
                f'{links(n)}</clipitem>')

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4">\n'
        f'<sequence id="{escape(seq_name)}"><name>{escape(seq_name)}</name>'
        f'<duration>{total}</duration>{rate()}{timecode()}'
        '<media><video><format><samplecharacteristics>' + rate() +
        f'<width>{w}</width><height>{h}</height>'
        '<pixelaspectratio>square</pixelaspectratio><anamorphic>FALSE</anamorphic>'
        '</samplecharacteristics></format>'
        f'<track>{"".join(v)}</track></video>'
        '<audio><numOutputChannels>2</numOutputChannels>'
        '<format><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate>'
        '</samplecharacteristics></format>'
        f'<track>{"".join(a1)}<outputchannelindex>1</outputchannelindex></track>'
        f'<track>{"".join(a2)}<outputchannelindex>2</outputchannelindex></track></audio>'
        '</media></sequence>\n</xmeml>\n'), rows, srcs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cutlist')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--all', action='store_true', help='V2·꺼둔 컷까지 전부 넣는다')
    ap.add_argument('--name', default=None)
    ap.add_argument('--limit', type=int, default=0, help='앞에서 N개만 (가르기 시험용)')
    a = ap.parse_args()

    cl = json.load(io.open(a.cutlist, encoding='utf-8'))
    if a.limit:
        keep = [c for c in cl['cuts'] if a.all or (c.get('track', 1) in (1, 'V1') and c.get('enabled', True))]
        cl = dict(cl, cuts=keep[:a.limit])
    xml, rows, srcs = build(cl, a.all, a.name)
    io.open(a.out, 'w', encoding='utf-8', newline='\n').write(xml)

    print('컷 %d개 · 길이 %d프레임(%.1f초) → %s'
          % (len(rows), rows[-1]['end'] if rows else 0,
             (rows[-1]['end'] if rows else 0) / NTSC_FPS, a.out))
    for k, s in srcs.items():
        used = [r for r in rows if r['src'] == k]
        if used:
            print('  소스 %s: %d프레임 · 쓰는 구간 최대 out %d'
                  % (os.path.basename(s['path']), s['frames'], max(r['out'] for r in used)))


if __name__ == '__main__':
    main()
