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
HANJI = (0xF3, 0xEC, 0xDF)
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


def btext(d, xy, s, font, fill=INK, anchor='lm', bold=0, halo=None):
    """궁서는 획이 얇다 — 같은 색 1px 스트로크로 굵히고, 필요하면 한지색 후광을 먼저 깐다 (중장년 가독성)"""
    if halo:
        d.text(xy, s, font=font, fill=halo, anchor=anchor, stroke_width=bold + 3, stroke_fill=halo)
    d.text(xy, s, font=font, fill=fill, anchor=anchor, stroke_width=bold, stroke_fill=fill)


class Cam:
    def __init__(self, c):
        self.X0, self.BW, self.Y0, self.K = (c[k]['v'][0] for k in ('X0', 'BW', 'Y0', 'K'))
    def x(self, bar): return self.X0 + bar * self.BW
    def y(self, price): return self.Y0 - price * self.K


# ---------- 재질 ----------
def hanji(w=W, h=H, base=HANJI, strength=1.0):
    """한지: 바탕색 + 저주파 얼룩 + 가로로 긴 섬유 노이즈. 화면에서 거의 안 보일 만큼 약하게."""
    a = np.zeros((h, w), np.float32)
    blot = np.random.rand(h // 32 + 1, w // 32 + 1).astype(np.float32)
    blot = np.array(Image.fromarray((blot * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(18))) / 255
    fiber = np.random.rand(h, w).astype(np.float32)
    fiber = np.array(Image.fromarray((fiber * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))) / 255
    fx = np.array(Image.fromarray((fiber * 255).astype(np.uint8)).resize((w // 6, h)).resize((w, h), Image.BILINEAR)) / 255
    a = (blot - 0.5) * 9 + (fiber - 0.5) * 3 + (fx - 0.5) * 4
    a *= strength
    img = np.zeros((h, w, 3), np.float32)
    for i in range(3):
        img[..., i] = np.clip(base[i] + a, 0, 255)
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
    return crop.resize((width, height), Image.LANCZOS)


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
    d.text((x + w / 2, y + h / 2 + 1), title, font=f, fill=HANJI2, anchor='mm', stroke_width=1, stroke_fill=HANJI2)
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
    d.text((960, y + 1), text, font=f, fill=INK, anchor='mm', stroke_width=1, stroke_fill=INK)


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


def toolkit(canvas, cam, chart):
    d = ImageDraw.Draw(canvas)
    xr = cam.x(63) + cam.BW * 0.8
    xl = cam.x(6) - cam.BW * 0.5
    # 익절/손절 담채 존 + 진입 먹선
    wash(canvas, (cam.x(44) - cam.BW / 2, cam.y(LV_TARGET), xr, cam.y(LV_ENTRY)), RED, 34)
    wash(canvas, (cam.x(44) - cam.BW / 2, cam.y(LV_ENTRY), xr, cam.y(LV_STOP)), JJOK, 30)
    d = ImageDraw.Draw(canvas)
    xs = xr + 132   # 존 라벨 낙관 자리 — 이평 끝 라벨(xr~xr+100) 오른쪽
    ink_line(d, cam.x(44) - cam.BW / 2, xs - 50, cam.y(LV_ENTRY), 3)
    ink_line(d, cam.x(44) - cam.BW / 2, xs - 50, cam.y(LV_TARGET), 2, RED, dash=(10, 8))
    ink_line(d, cam.x(44) - cam.BW / 2, xs - 50, cam.y(LV_STOP), 2, JJOK, dash=(10, 8))
    seal(canvas, xs, cam.y(LV_TARGET), '익절', RED, 96, 50, gung(32), tilt=0)
    seal(canvas, xs, cam.y(LV_STOP), '손절', JJOK, 96, 50, gung(32), tilt=0)
    seal(canvas, xs, cam.y(LV_ENTRY), '진입', INK, 96, 50, gung(32), tilt=0, alpha=210)
    # 지지·저항 먹 점선 + 작은 낙관
    ys, yr = cam.y(23700), cam.y(23905)
    xin = PANEL[0] + 40
    ink_line(d, xin, cam.x(43), ys, 2, INK, dash=(12, 9))
    ink_line(d, xin, cam.x(43), yr, 2, INK, dash=(12, 9))
    seal(canvas, xin + 66, ys + 30, '지지', GRN, 90, 48, gung(30), tilt=0)
    seal(canvas, xin + 66, yr - 30, '저항', RED, 90, 48, gung(30), tilt=0)
    # 이평선 끝 궁서 라벨 (오방색)
    ends = ma_ends(chart, {'10일선': RED, '20일선': YEL, '50일선': GRN})
    d = ImageDraw.Draw(canvas)
    used = []
    for name, c in (('10일선', RED), ('20일선', YEL), ('50일선', GRN)):
        y = ends.get(name)
        if y is None: continue
        for u in used:
            if abs(y - u) < 30: y = u + 30
        used.append(y)
        btext(d, (cam.x(63) + cam.BW * 1.2, y), name, gung(32), YEL_TXT if c == YEL else c, halo=HANJI2)
    # 매수/매도 낙관
    seal(canvas, cam.x(43), cam.y(LV_STOP) + 78, '매수', RED, 104, 104, tilt=-5)
    seal(canvas, cam.x(36), cam.y(24085), '매도', JJOK, 104, 104, tilt=4)
    # 붓 원 — 재지지
    brush_ellipse(canvas, cam.x(52), cam.y(LV_ENTRY + 130), 68, 76, wmin=2.5, wmax=8)
    # ①②③ 원형 낙관 + 먹 궁서
    d = ImageDraw.Draw(canvas)
    for ch, bar, price, body in (('一', 16, 24140, '정배열 확인'), ('二', 27, 23585, '20일선 눌림목'), ('三', 50, 23540, '반등 양봉에 매수')):
        cx, cy = cam.x(bar), cam.y(price)
        seal_round(canvas, cx, cy, ch, 28)
        d = ImageDraw.Draw(canvas)
        btext(d, (cx + 40, cy + 1), body, gung(32), INK, halo=HANJI2)
    # 물음표 — 횡보 가짜 신호 (붓글씨)
    d.text((cam.x(13), cam.y(23470)), '?', font=brush(120), fill=RED, anchor='mm')


# ---------- 스틸 ----------
PANEL = (60, 118, 1860, 962)


def base_canvas():
    return hanji().convert('RGBA')


def still_sources(chart, cam, out, a):
    c = base_canvas()
    ch = ImageChops.multiply(c.convert('RGB'), chart.convert('RGB')).convert('RGBA')
    c = ch
    byeongpung_frame(c, PANEL)
    c.alpha_composite(changho_strip(W, 92).convert('RGBA'), (0, 0))
    toolkit(c, cam, chart)
    hyeonpan(c, 96, 68, a.title)
    d = ImageDraw.Draw(c)
    vtext(d, PANEL[2] - 60, 168, a.ticker, gung(34))
    channel_seal(c, PANEL[2] - 100, PANEL[3] - 100)
    jokja(c, a.subtitle)
    c.convert('RGB').save(os.path.join(out, '전통_2_고정소스_총집합.png'))


def still_frame(chart, cam, out, a):
    c = base_canvas()
    c = ImageChops.multiply(c.convert('RGB'), chart.convert('RGB')).convert('RGBA')
    byeongpung_frame(c, PANEL)
    c.alpha_composite(changho_strip(W, 92).convert('RGBA'), (0, 0))
    hyeonpan(c, 96, 68, a.title)
    d = ImageDraw.Draw(c)
    vtext(d, PANEL[2] - 60, 168, a.ticker, gung(34))
    channel_seal(c, PANEL[2] - 100, PANEL[3] - 100)
    jokja(c, a.subtitle)
    c.convert('RGB').save(os.path.join(out, '전통_3_틀만.png'))


def still_logo(out):
    c = base_canvas()
    d = ImageDraw.Draw(c)
    f = gung(180)
    d.text((960 - 60, 470), '차트명가', font=f, fill=INK, anchor='mm')
    seal(c, 960 + 400, 470, '名家', RED, 150, 150, gung(64), tilt=-4)
    d = ImageDraw.Draw(c)
    d.text((960, 640), '해외선물 매매기법', font=gung(44), fill=JJOK, anchor='mm')
    ink_line(d, 560, 1360, 700, 3, INK)
    # 로고 결합 (맨 마지막): 기존 원형 로고를 인주색 도장(두인)으로 변주해 이름 앞에
    logo_seal(c, 960 - 560, 470, 150)
    # 비교용: 원본 분홍 로고 작게
    logo = Image.open(LOGO).convert('RGBA').resize((90, 90), Image.LANCZOS)
    c.alpha_composite(logo, (1700, 900))
    d = ImageDraw.Draw(c)
    btext(d, (1745, 1020), '원본 로고 (분홍) → 두인으로 변주', gung(22), JJOK, anchor='mm')
    c.convert('RGB').save(os.path.join(out, '전통_1_로고.png'))


def still_outro(out):
    c = base_canvas()
    # 전통문양(레퍼런스 21 수복문) 을 아주 옅게 깔기
    pat = Image.open(os.path.join(REF, '21_전통패턴_플랫.jpg')).convert('L')
    pat = pat.resize((740, 740))
    tile = Image.new('L', (W, H), 255)
    for y in range(0, H, 740):
        for x in range(0, W, 740):
            tile.paste(pat, (x, y))
    pat_np = 255 - np.array(tile)
    ov = Image.new('RGBA', (W, H), JJOK + (0,)); ov.putalpha(Image.fromarray((pat_np * 0.10).astype(np.uint8)))
    c.alpha_composite(ov)
    # 병풍 3폭
    panels = [(80, 120, 640, 960), (680, 120, 1240, 960), (1280, 120, 1840, 960)]
    for p in panels:
        byeongpung_frame(c, p, band=12)
    d = ImageDraw.Draw(c)
    # 왼폭: 다음 영상
    hyeonpan(c, 150, 80, '다음 영상', 34)
    d = ImageDraw.Draw(c)
    d.rectangle((140, 240, 580, 488), fill=HANJI2, outline=JJOK, width=3)
    d.text((360, 364), '영상 자리', font=gung(30), fill=(0x8A, 0x80, 0x74), anchor='mm')
    d.rectangle((140, 540, 580, 788), fill=HANJI2, outline=JJOK, width=3)
    d.text((360, 664), '영상 자리', font=gung(30), fill=(0x8A, 0x80, 0x74), anchor='mm')
    # 가운데: 이름 + 낙관
    d.text((960, 440), '차트명가', font=gung(120), fill=INK, anchor='mm', stroke_width=1, stroke_fill=INK)
    seal(c, 960, 630, '名家', RED, 130, 130, gung(56), tilt=-4)
    d = ImageDraw.Draw(c)
    btext(d, (960, 770), '해외선물 매매기법', gung(40), JJOK, anchor='mm')
    # 먹 캔들 소묘 — 이 화면이 '차트' 채널임을 알리는 표식
    for i, (o, cl, hi, lo) in enumerate([(0.55, 0.3, 0.6, 0.25), (0.3, 0.5, 0.55, 0.28), (0.5, 0.42, 0.58, 0.35), (0.42, 0.7, 0.75, 0.4), (0.7, 0.9, 0.95, 0.66)]):
        x = 828 + i * 66; base_y, hgt = 930, 130
        col = RED if cl > o else JJOK
        d.line((x, base_y - hi * hgt, x, base_y - lo * hgt), fill=col, width=4)
        d.rectangle((x - 16, base_y - max(o, cl) * hgt, x + 16, base_y - min(o, cl) * hgt), fill=col if cl > o else HANJI2, outline=col, width=4)
    logo_seal(c, 960, 190, 110)
    # 오른폭: 구독·좋아요 낙관 버튼
    hyeonpan(c, 1350, 80, '구독 · 알림', 34)
    seal(c, 1560, 400, '구독', RED, 220, 110, gung(56), tilt=-3)
    seal(c, 1560, 600, '좋아요', JJOK, 220, 110, gung(52), tilt=2)
    d = ImageDraw.Draw(c)
    vtext(d, 1770, 300, '매주 새 매매기법', gung(34), JJOK)
    jokja(c, '다음 영상에서 뵙겠습니다', 1010, 40)
    c.convert('RGB').save(os.path.join(out, '전통_4_아웃트로.png'))


def still_palette(out):
    c = base_canvas(); d = ImageDraw.Draw(c)
    d.text((960, 90), '팔레트 — 오방색 · 한지 · 먹 (레퍼런스 실측: 판독/색실측.md)', font=gung(40), fill=INK, anchor='mm')
    items = [('한지', HANJI, '#F3ECDF  창호지 실측 E5D6C0 을 밝힘'), ('먹', INK, '#1C1A17  글자·진입선'),
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
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cam = Cam(json.load(io.open(a.cam, encoding='utf-8'))['cuts'][0]['cam'])
    chart = Image.open(a.chart).convert('RGBA')
    which = set(a.only.split(',')) if a.only else {'sources', 'frame', 'logo', 'outro', 'palette'}
    if 'sources' in which: still_sources(chart, cam, a.out, a)
    if 'frame' in which: still_frame(chart, cam, a.out, a)
    if 'logo' in which: still_logo(a.out)
    if 'outro' in which: still_outro(a.out)
    if 'palette' in which: still_palette(a.out)
    print('ok', sorted(which))


if __name__ == '__main__':
    main()
