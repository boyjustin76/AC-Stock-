# -*- coding: utf-8 -*-
"""
신규안 v2 "병풍 위의 차트" — 전통 소재 합성기 (2026-09-11).

기존 차트명가 문법(frame.py)은 쓰지 않는다. 렌더러가 뽑은 흰 바탕 차트 PNG 를 한지에 곱하기로 얹고,
그 위에 병풍 테두리 · 창호 실물 띠(레퍼런스 사진 크롭) · 낙관(음각 도장) 태그 · 오방색 담채 존 ·
먹선 · 붓 원 · 현판 타이틀 · 세로 먹글씨 · 족자 자막을 카메라 좌표로 얹는다.

  python tools/style/trad.py --chart out/newch-trad/stills/trad_t0.00s.png --cam gen/newch-trad.json --out <폴더>

이미지 생성 AI 는 쓰지 않는다 (무료 등급 품질 불가). 실물 사진 크롭(창호) + 폰트(궁서·나눔붓) + 노이즈 침식(인주 질감).
"""
import argparse, io, json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H = 1920, 1080
HERE = os.path.dirname(os.path.abspath(__file__))
REF = r'C:\Users\user\Desktop\이정찬\차트명가 NEW\신규안_v2_전통\레퍼런스'
LOGO = os.path.join(HERE, '..', '..', 'brand', 'logo', '차트명가_로고(투명).png')

# 팔레트 (무드보드.md · 판독/색실측.md)
HANJI = (0xEC, 0xE3, 0xD3)   # 바탕 한지 — 창호 띠 종이(실측 D5C6B1)를 밝혀 둘을 같은 톤으로 맞춘 값 (2026-09-14)
TEX = os.path.join(HERE, 'tex', 'hanji_mulberry.jpg')   # 실사 닥종이 (Magnific 무료 사진 53876-102589)
HANJI2 = (0xFA, 0xF6, 0xEE)
INK = (0x1C, 0x1A, 0x17)
RED = (0xD4, 0x2A, 0x26)      # 인주 적
JJOK = (0x2C, 0x33, 0x58)     # 쪽
YEL = (0xC9, 0xA2, 0x27)      # 단청 황
GRN = (0x0B, 0x8A, 0x4C)      # 단청 녹
YEL_TXT = (0x9E, 0x7B, 0x12)  # 황 글자용(한지 위 대비)
WOOD = (0x5A, 0x40, 0x29)
GOLD = (0xB0, 0x8D, 0x3C)
LACQ = (0x22, 0x1E, 0x1B)     # 옻칠

LV_ENTRY, LV_STOP, LV_TARGET = 23795, 23665, 24055

random.seed(7); np.random.seed(7)


def gung(size):
    return ImageFont.truetype(r'C:\Windows\Fonts\batang.ttc', size, index=2)   # Gungsuh


def brush(size):
    return ImageFont.truetype(os.path.join(HERE, 'fonts', 'NanumBrushScript.ttf'), size)


def tw(f, s):
    b = f.getbbox(s); return b[2] - b[0]


def btext(canvas, xy, s, font, fill=INK, anchor='lm', bold=0, halo=None):
    """궁서는 획이 얇다. PIL 의 stroke_width 는 겹치는 윤곽(한글 대부분)에서 구멍을 내므로 쓰지 않는다 —
    L 마스크에 글자를 찍고 MaxFilter 로 팽창시켜 굵기·후광을 만든다. canvas 는 RGBA 이미지."""
    if isinstance(canvas, ImageDraw.ImageDraw):
        canvas = canvas._image
    m = Image.new('L', canvas.size, 0)
    ImageDraw.Draw(m).text(xy, s, font=font, fill=255, anchor=anchor)
    if halo:
        hm = m.filter(ImageFilter.MaxFilter(2 * (bold + 3) + 1))
        canvas.paste(Image.new('RGBA', canvas.size, halo + (255,)), (0, 0), hm)
    if bold:
        m = m.filter(ImageFilter.MaxFilter(2 * bold + 1))
    canvas.paste(Image.new('RGBA', canvas.size, fill + (255,)), (0, 0), m)


WARM = 60   # data/synth/newch-trad.json 앞의 워밍업 봉 수 (tools/style/trad-bars.mjs)


class Cam:
    def __init__(self, c):
        self.X0, self.BW, self.Y0, self.K = (c[k]['v'][0] for k in ('X0', 'BW', 'Y0', 'K'))
    def x(self, bar): return self.X0 + (bar + WARM) * self.BW   # bar 는 워밍업 전 번호 (0~63)
    def y(self, price): return self.Y0 - price * self.K


# ---------- 재질 ----------
_TEX = {}


def _tex_dev():
    """닥종이 사진의 밝기 편차만 뽑는다(색은 버린다). 크기는 1920×1280 로 한 번 고정 — 어디서 잘라도 섬유 굵기가 같다."""
    if 'dev' not in _TEX:
        t = np.array(Image.open(TEX).convert('L')).astype(np.float32)
        dev = t - t.mean()
        dev = np.where(dev < 0, dev * 0.7, dev)            # 굵은 섬유 조각은 조금 누른다 — 차트 뒤에서 정신없지 않게
        img = Image.fromarray(dev.astype(np.float32), 'F').resize((1920, 1280), Image.LANCZOS)
        _TEX['dev'] = np.array(img)
    return _TEX['dev']


def hanji(w=W, h=H, base=HANJI, strength=1.0):
    """한지: 실사 닥종이 사진의 밝기 결 + 바탕색.
    예전(2026-09-11)은 노이즈로 흉내 냈더니 편차 2 로 사실상 단색이었다 — 창호 사진의 종이(편차 15)와 따로 놀았다."""
    dev = _tex_dev()
    th, tw_ = dev.shape
    x0 = 0 if w >= tw_ else int(np.random.randint(0, tw_ - w + 1))
    y0 = (th - h) // 2 if h >= H else int(np.random.randint(0, th - h + 1))
    d = dev[y0:y0 + h, x0:x0 + w] * 1.3 * strength
    img = np.zeros((h, w, 3), np.float32)
    for i in range(3):
        img[..., i] = np.clip(base[i] + d, 0, 255)
    return Image.fromarray(img.astype(np.uint8), 'RGB')


def rough_mask(mask, blur=5, erode=0.55, holes=0.015):
    """인주 질감: 도장 면 마스크의 가장자리를 노이즈로 침식하고 안쪽에 미세한 빈틈을 낸다 (판독/09_낙관.md 규칙 3)."""
    m = np.array(mask.filter(ImageFilter.GaussianBlur(blur))).astype(np.float32) / 255
    n = np.random.rand(*m.shape).astype(np.float32)
    n = np.array(Image.fromarray((n * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))) / 255
    keep = m > (erode * 0.6 + n * erode * 0.8)
    hole = np.random.rand(*m.shape) < holes
    keep &= ~hole
    out = (keep * 255).astype(np.uint8)
    return Image.fromarray(out, 'L').filter(ImageFilter.GaussianBlur(0.4))


def seal(canvas, cx, cy, text, color=RED, w=110, h=110, font=None, fg=HANJI2, tilt=-4, cols=None, alpha=235):
    """낙관(음각): 색 면 + 흰 글자. 비정형 라운드 사각, 살짝 기울임. cols=2 면 글자를 2×2 로 배치."""
    pad = 40
    tile = Image.new('L', (w + pad * 2, h + pad * 2), 0)
    d = ImageDraw.Draw(tile)
    # 비정형: 모서리 반지름을 조금씩 다르게 (레퍼런스 08 손그림 도장)
    r = int(min(w, h) * 0.18)
    d.rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=255)
    # 한 변을 살짝 볼록하게
    d.ellipse((pad - 6, pad + h * 0.25, pad + 8, pad + h * 0.75), fill=255)
    d.ellipse((pad + w - 8, pad + h * 0.2, pad + w + 6, pad + h * 0.8), fill=255)
    tile = rough_mask(tile, blur=4, erode=0.5, holes=0.02)
    face = Image.new('RGBA', tile.size, color + (0,))
    face.putalpha(tile.point(lambda v: v * alpha // 255))
    # 글자 (흰 = 종이색이 비치는 음각)
    txt = Image.new('L', tile.size, 0)
    dt = ImageDraw.Draw(txt)
    f = font or gung(int(h * 0.48))
    if cols == 2 and len(text) == 4:
        g = int(h * 0.40); f = gung(int(h * 0.38))
        for i, ch in enumerate(text):
            px = pad + w / 2 + (-g / 2 if i % 2 == 0 else g / 2)
            py = pad + h / 2 + (-g / 2 if i < 2 else g / 2)
            dt.text((px, py), ch, font=f, fill=255, anchor='mm')
    else:
        dt.text((pad + w / 2, pad + h / 2 + 2), text, font=f, fill=255, anchor='mm')
    txt = txt.filter(ImageFilter.GaussianBlur(0.5))   # 글자는 침식하지 않는다 — 읽혀야 한다
    face_np = np.array(face)
    t = np.array(txt).astype(np.float32) / 255
    for i in range(3):
        face_np[..., i] = (face_np[..., i] * (1 - t) + fg[i] * t).astype(np.uint8)
    face = Image.fromarray(face_np, 'RGBA').rotate(tilt, resample=Image.BICUBIC, expand=True)
    canvas.alpha_composite(face, (int(cx - face.width / 2), int(cy - face.height / 2)))
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def seal_round(canvas, cx, cy, ch, r=30, color=RED):
    """원형 낙관(양각): 붉은 링 + 붉은 궁서 글자 — ①②③ 단계 표시"""
    pad = 20
    tile = Image.new('L', (2 * r + 2 * pad, 2 * r + 2 * pad), 0)
    d = ImageDraw.Draw(tile)
    d.ellipse((pad, pad, pad + 2 * r, pad + 2 * r), outline=255, width=max(4, r // 6))
    d.text((pad + r, pad + r + 1), ch, font=gung(int(r * 1.15)), fill=255, anchor='mm')
    tile = rough_mask(tile, blur=1.5, erode=0.5, holes=0.01)
    face = Image.new('RGBA', tile.size, color + (0,)); face.putalpha(tile.point(lambda v: v * 230 // 255))
    canvas.alpha_composite(face, (int(cx - face.width / 2), int(cy - face.height / 2)))


def wash(canvas, box, color, alpha=30, radius=8):
    """오방색 담채(淡彩) 존 — 가장자리를 살짝 번지게"""
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle(box, fill=color + (alpha,))
    ov = ov.filter(ImageFilter.GaussianBlur(radius))
    canvas.alpha_composite(ov)


def ink_line(d, x0, x1, y, width=3, color=INK, dash=None):
    if dash:
        x = x0
        while x < x1:
            d.line((x, y, min(x + dash[0], x1), y), fill=color, width=width); x += dash[0] + dash[1]
    else:
        d.line((x0, y, x1, y), fill=color, width=width)


def brush_ellipse(canvas, cx, cy, rx, ry, color=INK, wmin=3, wmax=11, start=-100):
    """붓 원: 획 두께가 한 바퀴 돌며 변하고, 끝이 시작보다 조금 넘치게 (손으로 그린 강조 원)"""
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    n = 160
    pts = []
    for i in range(n + 12):
        t = math.radians(start + 360 * i / n)
        jitter = 1 + 0.025 * math.sin(3 * t + 0.7) + 0.02 * math.cos(5 * t)
        pts.append((cx + rx * jitter * math.cos(t), cy + ry * jitter * math.sin(t)))
    for i in range(len(pts) - 1):
        u = i / len(pts)
        wdt = wmin + (wmax - wmin) * (0.5 + 0.5 * math.sin(u * 2 * math.pi * 1.5))
        if i > n: wdt *= max(0.2, 1 - (i - n) / 12)
        d.line((pts[i], pts[i + 1]), fill=color + (225,), width=int(wdt))
        d.ellipse((pts[i][0] - wdt / 2, pts[i][1] - wdt / 2, pts[i][0] + wdt / 2, pts[i][1] + wdt / 2), fill=color + (225,))
    canvas.alpha_composite(ov.filter(ImageFilter.GaussianBlur(0.5)))


def vtext(d, x, y, text, font, fill=INK, gap=4):
    """세로 먹글씨"""
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill, anchor='mt')
        b = font.getbbox(ch); y += (b[3] - b[1]) + gap + 6


# ---------- 틀 ----------
def changho_strip(width, height):
    """창호 실물 띠 — 레퍼런스 12(창호 사진) 워터마크 없는 영역을 크롭해 가로로 늘린다 (상단 '창')"""
    im = Image.open(os.path.join(REF, '12_창호지.jpg')).convert('RGB')
    crop = im.crop((30, 40, 990, 40 + int(960 * height / width)))
    a = np.array(crop).astype(np.float32)
    lum = a.mean(axis=2)
    paper = a[lum > 150].mean(axis=0)                        # 사진 속 종이 평균 (실측 213,198,177)
    gain = np.array(HANJI, np.float32) / paper
    wgt = np.clip((lum - 90) / 80.0, 0, 1)
    wgt = (wgt * wgt * (3 - 2 * wgt))[..., None]             # 밝은 종이만 바탕 톤으로, 어두운 나무살은 그대로
    a = a * (1 + (gain - 1) * wgt)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((width, height), Image.LANCZOS)
    return out.filter(ImageFilter.UnsharpMask(radius=1.2, percent=50, threshold=2))


def byeongpung_frame(canvas, box, silk=JJOK, band=14):
    """병풍 한 폭 테두리: 쪽빛 비단 띠 + 안쪽 한지 틈 + 가는 쪽선 (책가도 병풍 실측 비율 1:15~20 → 화면 1080 의 1/70 로 얇게)"""
    d = ImageDraw.Draw(canvas)
    x0, y0, x1, y1 = box
    d.rectangle((x0, y0, x1, y1), outline=silk, width=band)
    g = band + 5
    d.rectangle((x0 + g, y0 + g, x1 - g, y1 - g), outline=silk, width=2)
    # 비단 결 — 띠 위에 아주 옅은 가로 결
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for y in range(y0, y1, 3):
        od.line((x0, y, x1, y), fill=(255, 255, 255, 10))
    m = Image.new('L', (W, H), 0); md = ImageDraw.Draw(m)
    md.rectangle((x0, y0, x1, y1), fill=255); md.rectangle((x0 + band, y0 + band, x1 - band, y1 - band), fill=0)
    ov.putalpha(ImageChops.multiply(ov.getchannel('A'), m))
    canvas.alpha_composite(ov)


def hyeonpan(canvas, x, y, title, size=40):
    """현판: 옻칠 판 + 금테 + 흰 궁서. 병풍 위 테두리에 걸친다."""
    d = ImageDraw.Draw(canvas)
    f = gung(size)
    w, h = tw(f, title) + 64, size + 40
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((x + 4, y + 6, x + w + 4, y + h + 6), fill=(0, 0, 0, 70))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(canvas)
    d.rectangle((x, y, x + w, y + h), fill=LACQ)
    d.rectangle((x + 5, y + 5, x + w - 5, y + h - 5), outline=GOLD, width=2)
    btext(canvas, (x + w / 2, y + h / 2 + 1), title, f, HANJI2, anchor='mm', bold=1)
    return (x, y, x + w, y + h)


def jokja(canvas, text, y=1012, size=44):
    """족자 자막: 한지 띠 + 쪽빛 끝단 + 작은 축(軸). 먹 궁서."""
    d = ImageDraw.Draw(canvas)
    f = gung(size)
    w = max(tw(f, text) + 120, 700); h = size + 30
    x0 = 960 - w // 2
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((x0, y - h // 2 + 4, x0 + w, y + h // 2 + 6), fill=(0, 0, 0, 55))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    strip = hanji(w, h, HANJI2, 0.8).convert('RGBA')
    canvas.alpha_composite(strip, (x0, y - h // 2))
    d = ImageDraw.Draw(canvas)
    d.rectangle((x0, y - h // 2, x0 + 26, y + h // 2), fill=JJOK)
    d.rectangle((x0 + w - 26, y - h // 2, x0 + w, y + h // 2), fill=JJOK)
    d.rectangle((x0 - 8, y - h // 2 - 5, x0 + 4, y + h // 2 + 5), fill=WOOD)
    d.rectangle((x0 + w - 4, y - h // 2 - 5, x0 + w + 8, y + h // 2 + 5), fill=WOOD)
    btext(canvas, (960, y + 1), text, f, INK, anchor='mm', bold=1)


def logo_seal(canvas, cx, cy, size=150, color=RED):
    """기존 원형 로고(기와지붕+막대)를 인주색 '도장'으로 변주 — 선을 굵히고 가장자리를 침식 (QA_로고.md ①②)"""
    lg = Image.open(LOGO).convert('RGBA').resize((size, size), Image.LANCZOS)
    m = lg.getchannel('A').filter(ImageFilter.MaxFilter(3))          # 획 굵히기
    m = rough_mask(m, blur=1.0, erode=0.45, holes=0.02)
    face = Image.new('RGBA', lg.size, color + (0,)); face.putalpha(m.point(lambda v: v * 235 // 255))
    canvas.alpha_composite(face, (int(cx - size / 2), int(cy - size / 2)))


def channel_seal(canvas, x, y, size=104):
    seal(canvas, x, y, '차트명가', RED, size, size, cols=2, tilt=-3)


# ---------- 차트 위 어휘 ----------
def ma_ends(chart, colors, x_from=1380, x_to=1430):
    """차트 PNG 에서 이평선 끝 y 를 색으로 찾는다 (렌더러 내부값 대신 픽셀로)"""
    a = np.array(chart.convert('RGB')).astype(int)
    res = {}
    for name, c in colors.items():
        best = None
        for x in range(x_to, x_from, -1):
            col = a[:, x, :]
            dist = np.abs(col - np.array(c)).sum(axis=1)
            ys = np.where(dist < 60)[0]
            if len(ys):
                best = float(np.median(ys)); break
        res[name] = best
    return res


# ---------- 레이어 기록기 ----------
class Layers:
    """스틸 하나를 레이어 목록으로 짓는다. 합성본(PNG)과 쪼갠 레이어(PNG+목록)를 **같은 그리기 함수**로 낸다.

    add(이름, 그리기함수, blend)  — 그리기 함수는 투명한 전체 크기 RGBA 캔버스에 그린다.
    쪼갤 때는 알파 상자로 잘라 저장하고 (x, y, w, h) 를 목록에 적는다 → AE 가 그 자리에 놓는다.
    blend='multiply' 는 흰 바탕 차트처럼 곱하기로 얹는 층 (AE 블렌딩 모드 Multiply 와 같다)."""

    def __init__(self, comp, split_dir=None, footage_prefix=''):
        self.comp = comp
        self.split_dir = split_dir
        self.prefix = footage_prefix
        self.canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        self.items = []
        if split_dir:
            os.makedirs(split_dir, exist_ok=True)

    def add(self, name, draw, blend='normal', slug=None, full=False, anim=None):
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw(layer)
        if blend == 'multiply':
            rgb = ImageChops.multiply(self.canvas.convert('RGB'), layer.convert('RGB'))
            a = self.canvas.getchannel('A')
            self.canvas = rgb.convert('RGBA'); self.canvas.putalpha(a)
        else:
            self.canvas.alpha_composite(layer)
        n = len(self.items) + 1
        box = (0, 0, W, H) if (full or blend == 'multiply') else layer.getbbox()
        if box is None:
            return
        x0, y0, x1, y1 = box
        if not full and blend != 'multiply':
            x0, y0, x1, y1 = max(0, x0 - 2), max(0, y0 - 2), min(W, x1 + 2), min(H, y1 + 2)
        rec = {'n': n, 'name': '%02d %s' % (n, name), 'x': x0, 'y': y0, 'w': x1 - x0, 'h': y1 - y0, 'blend': blend}
        if anim:
            rec['anim'] = anim     # AE 모션 컴포지션용 (tools/ae/trad_motion_pack.py → c3_trad_motion.jsx)
        if self.split_dir:
            fn = '%s%02d_%s.png' % (self.prefix, n, slug or ('L%02d' % n))
            layer.crop((x0, y0, x1, y1)).save(os.path.join(self.split_dir, fn))
            rec['file'] = fn
        self.items.append(rec)

    def save_flat(self, path):
        self.canvas.convert('RGB').save(path)

    def manifest(self, fps=30, dur=10):
        return {'comp': self.comp, 'w': W, 'h': H, 'fps': fps, 'dur': dur, 'layers': self.items}


def draw_fn(fn, *args, **kw):
    """ImageDraw 를 받는 함수를 레이어 그리기 함수로 감싼다"""
    return lambda c: fn(ImageDraw.Draw(c), *args, **kw)


def hanji_layer(c):
    c.alpha_composite(hanji().convert('RGBA'))


# ---------- 스틸 ----------
PANEL = (60, 118, 1860, 962)


def frame_layers(L, chart, a):
    """틀 — 총집합과 틀만 스틸이 공유하는 층"""
    L.add('한지 바탕', hanji_layer, slug='hanji', full=True)
    L.add('차트 바닥 (캔들·이평 3선, 곱하기)', lambda c: c.alpha_composite(chart.convert('RGBA')), blend='multiply', slug='chart')
    L.add('병풍 테두리 (쪽)', lambda c: byeongpung_frame(c, PANEL), slug='byeongpung')
    L.add('창호 띠 (실물 크롭)', lambda c: c.alpha_composite(changho_strip(W, 92).convert('RGBA'), (0, 0)), slug='changho')


def deco_layers(L, a):
    L.add('현판 타이틀', lambda c: hyeonpan(c, 96, 68, a.title), slug='hyeonpan')
    L.add('세로 종목 (나스닥 일봉)', draw_fn(vtext, PANEL[2] - 60, 168, a.ticker, gung(34)), slug='ticker')
    L.add('채널 낙관 (차트명가)', lambda c: channel_seal(c, PANEL[2] - 100, PANEL[3] - 100), slug='chseal', anim={'type': 'stamp', 'title': '낙관 차트명가'})
    L.add('족자 자막', lambda c: jokja(c, a.subtitle), slug='jokja',
          anim={'type': 'scroll', 'title': '족자 자막 (본편)', 'text': a.subtitle, 'size': 44, 'y': 1012})


def toolkit_layers(L, cam, chart):
    """차트 위 매매 어휘 — 한 요소가 한 층"""
    xr = cam.x(63) + cam.BW * 0.8
    xs = xr + 132   # 존 라벨 낙관 자리 — 이평 끝 라벨(xr~xr+100) 오른쪽
    x44 = cam.x(44) - cam.BW / 2
    L.add('익절 존 (적 담채)', lambda c: wash(c, (x44, cam.y(LV_TARGET), xr, cam.y(LV_ENTRY)), RED, 34), slug='zone_tp')
    L.add('손절 존 (쪽 담채)', lambda c: wash(c, (x44, cam.y(LV_ENTRY), xr, cam.y(LV_STOP)), JJOK, 30), slug='zone_sl')
    L.add('진입 먹선', draw_fn(ink_line, x44, xs - 50, cam.y(LV_ENTRY), 3), slug='line_entry')
    L.add('익절 점선', draw_fn(ink_line, x44, xs - 50, cam.y(LV_TARGET), 2, RED, dash=(10, 8)), slug='line_tp')
    L.add('손절 점선', draw_fn(ink_line, x44, xs - 50, cam.y(LV_STOP), 2, JJOK, dash=(10, 8)), slug='line_sl')
    L.add('익절 낙관', lambda c: seal(c, xs, cam.y(LV_TARGET), '익절', RED, 96, 50, gung(32), tilt=0), slug='seal_tp', anim={'type': 'stamp', 'title': '낙관 익절'})
    L.add('손절 낙관', lambda c: seal(c, xs, cam.y(LV_STOP), '손절', JJOK, 96, 50, gung(32), tilt=0), slug='seal_sl', anim={'type': 'stamp', 'title': '낙관 손절'})
    L.add('진입 낙관', lambda c: seal(c, xs, cam.y(LV_ENTRY), '진입', INK, 96, 50, gung(32), tilt=0, alpha=210), slug='seal_entry', anim={'type': 'stamp', 'title': '낙관 진입'})
    # 지지·저항 먹 점선 + 작은 낙관
    ys, yr = cam.y(23700), cam.y(23905)
    xin = PANEL[0] + 40
    L.add('지지 점선', draw_fn(ink_line, xin, cam.x(43), ys, 2, INK, dash=(12, 9)), slug='line_support')
    L.add('저항 점선', draw_fn(ink_line, xin, cam.x(43), yr, 2, INK, dash=(12, 9)), slug='line_resist')
    L.add('지지 낙관', lambda c: seal(c, xin + 66, ys + 30, '지지', GRN, 90, 48, gung(30), tilt=0), slug='seal_support', anim={'type': 'stamp', 'title': '낙관 지지'})
    L.add('저항 낙관', lambda c: seal(c, xin + 66, yr - 30, '저항', RED, 90, 48, gung(30), tilt=0), slug='seal_resist', anim={'type': 'stamp', 'title': '낙관 저항'})
    # 이평선 끝 궁서 라벨 (오방색)
    ends = ma_ends(chart, {'10일선': RED, '20일선': YEL, '50일선': GRN})
    used = []
    for name, col, slug in (('10일선', RED, 'ma10'), ('20일선', YEL, 'ma20'), ('50일선', GRN, 'ma50')):
        y = ends.get(name)
        if y is None: continue
        for u in used:
            if abs(y - u) < 30: y = u + 30
        used.append(y)
        L.add('이평 라벨 ' + name, (lambda yy, nm, cc: lambda c: btext(c, (cam.x(63) + cam.BW * 1.2, yy), nm, gung(32), YEL_TXT if cc == YEL else cc, halo=HANJI))(y, name, col), slug='label_' + slug)
    # 매수/매도 낙관
    L.add('매수 낙관', lambda c: seal(c, cam.x(43), cam.y(LV_STOP) + 108, '매수', RED, 104, 104, tilt=-5), slug='seal_buy', anim={'type': 'stamp', 'title': '낙관 매수'})
    L.add('매도 낙관', lambda c: seal(c, cam.x(36), cam.y(24085), '매도', JJOK, 104, 104, tilt=4), slug='seal_sell', anim={'type': 'stamp', 'title': '낙관 매도'})
    # 붓 원 — 재지지
    bcx, bcy = cam.x(52), cam.y(LV_ENTRY + 130)
    L.add('붓 원 (강조)', lambda c: brush_ellipse(c, bcx, bcy, 68, 76, wmin=2.5, wmax=8), slug='brush_circle',
          anim={'type': 'drawon', 'title': '붓 원', 'cx': bcx, 'cy': bcy, 'rx': 68, 'ry': 76, 'start': -100, 'n': 160, 'over': 12, 'wmax': 8})
    # 一二三 원형 낙관 + 먹 궁서
    for ch, bar, price, body, side, slug in (('一', 16, 24140, '정배열 확인', 'r', 'step1'), ('二', 27, 23585, '20일선 눌림목', 'l', 'step2'), ('三', 50, 23540, '반등 양봉에 매수', 'r', 'step3')):
        cx, cy = cam.x(bar), cam.y(price)
        L.add('단계 %s 원형 낙관' % ch, (lambda cx, cy, ch: lambda c: seal_round(c, cx, cy, ch, 28))(cx, cy, ch), slug=slug + '_ring', anim={'type': 'stamp', 'title': '원형 낙관 ' + ch})
        if side == 'r':
            L.add('단계 %s 문구 (%s)' % (ch, body), (lambda cx, cy, body: lambda c: btext(c, (cx + 40, cy + 1), body, gung(32), INK, halo=HANJI))(cx, cy, body), slug=slug + '_text')
        else:   # 원 아래 — 오른쪽은 50일선, 왼쪽은 캔들이 지나간다
            L.add('단계 %s 문구 (%s)' % (ch, body), (lambda cx, cy, body: lambda c: btext(c, (cx, cy + 100), body, gung(32), INK, anchor='mm', halo=HANJI))(cx, cy, body), slug=slug + '_text')
    # 물음표 — 횡보 가짜 신호 (붓글씨)
    L.add('붓 물음표', draw_fn(lambda d: d.text((cam.x(13), cam.y(23470)), '?', font=brush(120), fill=RED, anchor='mm')), slug='question')


def build_sources(chart, cam, a, split=None):
    L = Layers('전통_총집합', split and os.path.join(split, 'sources'), 's')
    frame_layers(L, chart, a)
    toolkit_layers(L, cam, chart)
    deco_layers(L, a)
    return L


def build_frame(chart, cam, a, split=None):
    L = Layers('전통_틀', split and os.path.join(split, 'frame'), 'f')
    frame_layers(L, chart, a)
    deco_layers(L, a)
    return L


def build_logo(a, split=None):
    L = Layers('전통_로고', split and os.path.join(split, 'logo'), 'l')
    L.add('한지 바탕', hanji_layer, slug='hanji', full=True)
    L.add('이름 (궁서 차트명가)', draw_fn(lambda d: d.text((960 - 60, 470), '차트명가', font=gung(180), fill=INK, anchor='mm')), slug='name')
    L.add('名家 낙관', lambda c: seal(c, 960 + 400, 470, '名家', RED, 150, 150, gung(64), tilt=-4), slug='seal_myeongga', anim={'type': 'stamp', 'title': '낙관 名家 (로고)'})
    L.add('부제 (해외선물 매매기법)', draw_fn(lambda d: d.text((960, 640), '해외선물 매매기법', font=gung(44), fill=JJOK, anchor='mm')), slug='sub')
    L.add('먹 밑줄', draw_fn(ink_line, 560, 1360, 700, 3, INK), slug='rule')
    L.add('두인 (기존 로고 인주색 변주)', lambda c: logo_seal(c, 960 - 560, 470, 150), slug='logo_seal', anim={'type': 'stamp', 'title': '두인 (로고)'})
    if not split:   # 비교용 원본 로고는 합성본에만
        def cmp_(c):
            logo = Image.open(LOGO).convert('RGBA').resize((90, 90), Image.LANCZOS)
            c.alpha_composite(logo, (1700, 900))
            btext(c, (1745, 1020), '원본 로고 (분홍) → 두인으로 변주', gung(22), JJOK, anchor='mm')
        L.add('원본 로고 비교', cmp_, slug='compare')
    return L


def build_outro(a, split=None):
    L = Layers('전통_아웃트로', split and os.path.join(split, 'outro'), 'o')
    L.add('한지 바탕', hanji_layer, slug='hanji', full=True)

    def pattern(c):
        # 전통문양(레퍼런스 21 수복문) 을 아주 옅게 깔기
        pat = Image.open(os.path.join(REF, '21_전통패턴_플랫.jpg')).convert('L').resize((740, 740))
        tile = Image.new('L', (W, H), 255)
        for y in range(0, H, 740):
            for x in range(0, W, 740):
                tile.paste(pat, (x, y))
        pat_np = 255 - np.array(tile)
        ov = Image.new('RGBA', (W, H), JJOK + (0,)); ov.putalpha(Image.fromarray((pat_np * 0.10).astype(np.uint8)))
        c.alpha_composite(ov)
    L.add('수복문 바탕 문양 (10%)', pattern, slug='pattern', full=True)
    panels = [(80, 120, 640, 960), (680, 120, 1240, 960), (1280, 120, 1840, 960)]
    for i, p in enumerate(panels):
        L.add('병풍 %d폭 테두리' % (i + 1), (lambda p: lambda c: byeongpung_frame(c, p, band=12))(p), slug='panel%d' % (i + 1))
    # 왼폭: 다음 영상
    L.add('현판 (다음 영상)', lambda c: hyeonpan(c, 150, 80, '다음 영상', 34), slug='hyeonpan_next')
    for i, (y0, y1) in enumerate(((240, 488), (540, 788))):
        def slot(c, y0=y0, y1=y1):
            d = ImageDraw.Draw(c)
            d.rectangle((140, y0, 580, y1), fill=HANJI2, outline=JJOK, width=3)
            d.text((360, (y0 + y1) // 2), '영상 자리', font=gung(30), fill=(0x8A, 0x80, 0x74), anchor='mm')
        L.add('영상 자리 %d' % (i + 1), slot, slug='slot%d' % (i + 1))
    # 가운데: 이름 + 낙관
    L.add('두인 (기존 로고 인주색 변주)', lambda c: logo_seal(c, 960, 190, 110), slug='logo_seal', anim={'type': 'stamp', 'title': '두인 (아웃트로)'})
    L.add('이름 (궁서 차트명가)', lambda c: btext(c, (960, 440), '차트명가', gung(120), INK, anchor='mm', bold=1), slug='name')
    L.add('名家 낙관', lambda c: seal(c, 960, 630, '名家', RED, 130, 130, gung(56), tilt=-4), slug='seal_myeongga', anim={'type': 'stamp', 'title': '낙관 名家 (아웃트로)'})
    L.add('부제 (해외선물 매매기법)', lambda c: btext(c, (960, 770), '해외선물 매매기법', gung(40), JJOK, anchor='mm'), slug='sub')

    def candles(c):
        d = ImageDraw.Draw(c)
        ohlc = [(0.18, 0.36, 0.40, 0.14), (0.36, 0.26, 0.39, 0.22), (0.26, 0.50, 0.54, 0.24), (0.50, 0.40, 0.53, 0.36), (0.40, 0.66, 0.70, 0.38), (0.66, 0.56, 0.69, 0.52), (0.56, 0.86, 0.90, 0.54)]
        for i, (o, cl, hi, lo) in enumerate(ohlc):
            x = 780 + i * 60; base_y, hgt = 950, 150
            up = cl > o; col = RED if up else JJOK
            d.line((x, base_y - hi * hgt, x, base_y - lo * hgt), fill=col, width=3)
            d.rectangle((x - 13, base_y - max(o, cl) * hgt, x + 13, base_y - min(o, cl) * hgt), fill=col if up else HANJI2, outline=col, width=3)
    L.add('먹 캔들 소묘', candles, slug='candles')
    # 오른폭: 구독·좋아요 낙관 버튼
    L.add('현판 (구독 · 알림)', lambda c: hyeonpan(c, 1350, 80, '구독 · 알림', 34), slug='hyeonpan_sub')
    L.add('구독 낙관', lambda c: seal(c, 1560, 400, '구독', RED, 220, 110, gung(56), tilt=-3), slug='seal_subscribe', anim={'type': 'stamp', 'title': '낙관 구독'})
    L.add('좋아요 낙관', lambda c: seal(c, 1560, 600, '좋아요', JJOK, 220, 110, gung(52), tilt=2), slug='seal_like', anim={'type': 'stamp', 'title': '낙관 좋아요'})
    L.add('세로 문구 (매주 새 매매기법)', draw_fn(vtext, 1770, 300, '매주 새 매매기법', gung(34), JJOK), slug='vtext')
    L.add('족자 자막 (다음 영상에서 뵙겠습니다)', lambda c: jokja(c, '다음 영상에서 뵙겠습니다', 1010, 40), slug='jokja',
          anim={'type': 'scroll', 'title': '족자 자막 (아웃트로)', 'text': '다음 영상에서 뵙겠습니다', 'size': 40, 'y': 1010})
    return L


def still_palette(out):
    c = hanji().convert('RGBA'); d = ImageDraw.Draw(c)
    d.text((960, 90), '팔레트 — 오방색 · 한지 · 먹 (레퍼런스 실측: 판독/색실측.md)', font=gung(40), fill=INK, anchor='mm')
    items = [('한지', HANJI, '#ECE3D3  창호 띠 종이(실측 D5C6B1)와 같은 톤 · 닥종이 사진 결'), ('먹', INK, '#1C1A17  글자·진입선'),
             ('인주 적', RED, '#D42A26  매수·익절·10일선 (도장 실측 D71E22)'), ('쪽', JJOK, '#2C3358  매도·손절·병풍 테두리'),
             ('단청 황', YEL, '#C9A227  20일선 (단청 실측 B89E2C)'), ('단청 녹', GRN, '#0B8A4C  50일선·지지 (실측 069853)'),
             ('창호 나무', WOOD, '#5A4029  자막 축·창호 띠'), ('금테', GOLD, '#B08D3C  현판 테두리')]
    y = 170
    for name, col, desc in items:
        d.rectangle((160, y, 420, y + 92), fill=col, outline=INK, width=2)
        d.text((460, y + 46), name, font=gung(40), fill=INK, anchor='lm')
        d.text((720, y + 46), desc, font=gung(28), fill=JJOK, anchor='lm')
        y += 108
    c.convert('RGB').save(os.path.join(out, '전통_5_컬러팔레트.png'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chart', required=True)
    ap.add_argument('--cam', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--title', default='20일선 눌림목에서 추세를 끝까지 끌고 가는 법')
    ap.add_argument('--ticker', default='나스닥 일봉')
    ap.add_argument('--subtitle', default='눌림목에서 잡았으면 추세가 끝날 때까지 들고 갑니다')
    ap.add_argument('--only', default='')
    ap.add_argument('--split', default='', help='레이어를 쪼개 저장할 폴더 (footage). 목록은 <split>/manifest.json · .jsx')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cam = Cam(json.load(io.open(a.cam, encoding='utf-8'))['cuts'][0]['cam'])
    chart = Image.open(a.chart).convert('RGBA')
    which = set(a.only.split(',')) if a.only else {'sources', 'frame', 'logo', 'outro', 'palette'}
    split = a.split or None
    comps = []
    for key, fn, flat in (('sources', lambda s: build_sources(chart, cam, a, s), '전통_2_고정소스_총집합.png'),
                          ('frame', lambda s: build_frame(chart, cam, a, s), '전통_3_틀만.png'),
                          ('logo', lambda s: build_logo(a, s), '전통_1_로고.png'),
                          ('outro', lambda s: build_outro(a, s), '전통_4_아웃트로.png')):
        if key not in which: continue
        random.seed(7); np.random.seed(7)          # 층을 따로 그려도 합성본과 같은 질감이 나오게
        L = fn(split)
        L.save_flat(os.path.join(split, key, '_flat.png') if split else os.path.join(a.out, flat))
        if split: comps.append(L.manifest())
    if 'palette' in which and not split: still_palette(a.out)
    if split:
        np.random.seed(11)
        hanji(1860, 160, HANJI2, 0.8).save(os.path.join(split, 'jokja_paper.png'))
        man = {'pack': os.path.basename(os.path.normpath(split)), 'comps': comps}
        io.open(os.path.join(split, 'manifest.json'), 'w', encoding='utf-8').write(json.dumps(man, ensure_ascii=False, indent=1))
        # ExtendScript 에는 JSON 이 없다 — 객체 리터럴로. 한글은 \\u 이스케이프로 넣어 파일 인코딩에 안 걸리게.
        io.open(os.path.join(split, 'manifest.jsx'), 'w', encoding='ascii').write('var MANIFEST = ' + json.dumps(man, ensure_ascii=True) + ';\n')
        print('split', [(c['comp'], len(c['layers'])) for c in comps])
    print('ok', sorted(which))


if __name__ == '__main__':
    main()
