# -*- coding: utf-8 -*-
"""롤링 광고 배너를 .ai 로 옮기기 위해 — D 의 roll_ad.py 가 **무엇을 어디에 그렸는지** 적는다.

roll_ad.py 는 PIL 로 픽셀을 바로 찍는다. 팀장이 고칠 수 있는 원본(.ai)을 만들려면
글자·판·무늬를 따로따로 알아야 한다. 새로 그리면 두 벌이 어긋나므로 roll_ad.py 를
**고치지 않고 불러와서** 그리기 호출만 가로채 기록한다. D 가 문구·좌표를 고쳐도 다시 돌리면 따라간다.

가로채는 것
  V2.btext              글자 (내용 · 궁서 크기 · 색 · 굵기 · 잉크 상자)
  ImageDraw.rectangle   옻칠 면 · 금테 · 현판 · 테두리 박스 · 밑줄
  ImageDraw.polygon     ▼
  Image.alpha_composite 로고 무늬 · 가로 로고 (그림은 png 로 떨궈 둔다)

그리는 것은 원래대로 그린다 — 그래서 기록하면서 뽑은 그림이 납품된 jpg 와 같은지로
"지금 작업트리의 roll_ad.py 가 납품본을 만든 그 코드인가"를 확인할 수 있다 (--check).

  python tools/illustrator/rollad_layout.py --theme lacquer --out <자료 폴더> [--check <옻칠판 폴더>]
"""
import argparse
import hashlib
import io
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
STYLE = os.path.join(HERE, '..', 'style')
sys.path.insert(0, STYLE)
import roll_ad as RA                   # noqa: E402
V2 = RA.V2

BOARD = None          # 지금 그리는 판 {name, w, h, items}
OUT = None


def rgb(c):
    c = tuple(int(v) for v in c[:3])
    return '#%02X%02X%02X' % c


# ---------------------------------------------------------------- 글자
_btext = V2.btext


def btext(canvas, xy, s, font, fill=V2.INK, anchor='lm', bold=0, halo=None):
    if BOARD is not None:
        # 잉크 상자는 실제로 찍어서 잰다 — textbbox 는 글꼴 지표 상자라 획 끝과 다르다.
        # .ai 쪽도 글자를 윤곽으로 바꿔 잉크 상자를 재서 이 상자에 가운데를 맞춘다.
        m = Image.new('L', canvas.size, 0)
        ImageDraw.Draw(m).text(xy, s, font=font, fill=255, anchor=anchor)
        bb = m.getbbox()
        BOARD['items'].append(dict(
            kind='text', text=s, size=font.size, font=os.path.basename(font.path),
            index=getattr(font, 'index', 0), color=rgb(fill), bold=bold,
            anchor=anchor, x=xy[0], y=xy[1], ink=list(bb)))
    return _btext(canvas, xy, s, font, fill, anchor, bold, halo)


V2.btext = btext


# ---------------------------------------------------------------- 도형
class Draw:
    def __init__(self, im, mode=None):
        self._d = ImageDraw.Draw(im, mode)
        self._full = im.size

    def rectangle(self, xy, fill=None, outline=None, width=1):
        if BOARD is not None:
            x0, y0, x1, y1 = [float(v) for v in xy]
            it = dict(kind='rect', x0=x0, y0=y0, x1=x1, y1=y1)
            if fill is not None:
                it['fill'] = rgb(fill)
                if len(fill) == 4 and fill[3] < 255:
                    it['alpha'] = fill[3]
            if outline is not None:
                it['stroke'] = rgb(outline)
                it['width'] = width
            BOARD['items'].append(it)
        return self._d.rectangle(xy, fill=fill, outline=outline, width=width)

    def polygon(self, pts, fill=None, outline=None):
        if BOARD is not None:
            BOARD['items'].append(dict(kind='poly', pts=[[float(a), float(b)] for a, b in pts],
                                       fill=rgb(fill)))
        return self._d.polygon(pts, fill=fill, outline=outline)


class _ImageDrawShim:
    Draw = Draw


RA.ImageDraw = _ImageDrawShim


# ---------------------------------------------------------------- 그림
MARKS = {}           # id(무늬 이미지) -> (크기, 불투명 0~255, 색)
_mark = RA.mark


def mark(size, alpha, color=RA.PINK):
    im = _mark(size, alpha, color)
    MARKS[id(im)] = (size, alpha, color)
    return im


RA.mark = mark

_ac = Image.Image.alpha_composite


def alpha_composite(self, im, dest=(0, 0), source=(0, 0)):
    if BOARD is not None and im.size != self.size:
        it = dict(kind='image', x=dest[0], y=dest[1], w=im.size[0], h=im.size[1])
        if id(im) in MARKS:
            size, alpha, color = MARKS[id(im)]
            it.update(role='mark', opacity=round(alpha / 255 * 100, 2), tint=rgb(color),
                      src=asset(_mark(size, 255, color), 'mark'))
        else:
            it.update(role='logo', opacity=100, src=asset(im, 'logo'))
        BOARD['items'].append(it)
    return _ac(self, im, dest, source)


Image.Image.alpha_composite = alpha_composite


def asset(im, stem):
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    h = hashlib.md5(buf.getvalue()).hexdigest()[:10]
    name = '%s_%s.png' % (stem, h)
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        with open(p, 'wb') as f:
            f.write(buf.getvalue())
    return name


# ---------------------------------------------------------------- 판마다
def record(name, w, h, bg, make):
    global BOARD
    BOARD = dict(name=name, w=w, h=h, bg=rgb(bg) if bg else None, items=[])
    im = make()
    b, BOARD = BOARD, None
    return b, im


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument('--theme', default='lacquer', choices=tuple(RA.THEMES))
    ap.add_argument('--out', required=True, help='layout.json 과 그림 자료를 둘 폴더')
    ap.add_argument('--check', help='납품본 폴더 — 같은 그림이 나오는지 해시로 본다')
    a = ap.parse_args()
    OUT = a.out
    os.makedirs(OUT, exist_ok=True)
    RA.TH = RA.THEMES[a.theme]
    bg = RA.TH['bg']

    boards, bad = [], []
    groups = [('long', '원본(방송 라이브 버전)_long', RA.LONG),
              ('short', '원본(하이라이트 버전)_short', RA.SHORT)]
    for kind, sub, table in groups:
        W, H = RA.SPEC[kind]['size']
        for name, fn, dk in table:
            # 기본 인자로 묶는다 — record() 가 바로 부르니 버그는 아니지만 ruff B023 경고를 없앤다 (총괄 개선안 D-6)
            b, im = record(name, W, H, bg,
                           lambda kind=kind, name=name, fn=fn, dk=dk: RA.build(kind, name, fn, dk)[1])
            ext = '.png' if '배경' in name else '.jpg'
            b['file'] = sub + '/' + name + ext
            boards.append(b)
            keep(im, name)
            if a.check:
                bad += compare(im, os.path.join(a.check, b['file']), ext)

    def pinned():
        c = Image.new('RGBA', (377, 71), (0, 0, 0, 0))
        RA.cta(c, (0, 0, 376, 70), 26)
        return c
    b, im = record('고정댓글', 377, 71, None, pinned)
    b['file'] = '원본(방송 라이브 버전)_long/고정댓글.png'
    boards.append(b)
    keep(im, '고정댓글')
    if a.check:
        bad += compare(im, os.path.join(a.check, b['file']), '.png')

    with open(os.path.join(OUT, 'layout.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(theme=a.theme, boards=boards), f, ensure_ascii=False, indent=1)
    n = sum(len(b['items']) for b in boards)
    print('판 %d · 항목 %d · %s' % (len(boards), n, os.path.join(OUT, 'layout.json')))
    if a.check:
        print('납품본과 같음' if not bad else '납품본과 다름: ' + ', '.join(bad))
        sys.exit(1 if bad else 0)


def keep(im, name):
    """무손실 기준 그림 — .ai 에서 뽑은 png 와 비교할 때 jpg 압축 잡음이 끼지 않게."""
    d = os.path.join(OUT, 'ref')
    os.makedirs(d, exist_ok=True)
    im.save(os.path.join(d, name + '.png'))


def compare(im, path, ext):
    """jpg 는 같은 코드로 같은 품질로 저장해 바이트를 비교한다 (roll_ad.main 과 같은 저장)."""
    buf = io.BytesIO()
    (im.convert('RGB') if ext == '.jpg' else im).save(buf, 'JPEG' if ext == '.jpg' else 'PNG', quality=95)
    with open(path, 'rb') as f:
        same = f.read() == buf.getvalue()
    return [] if same else [os.path.basename(path)]


if __name__ == '__main__':
    main()
