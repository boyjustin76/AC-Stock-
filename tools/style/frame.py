"""새 채널 스타일 스틸 v2 — 브라우저 창(점 3·탭·주소창·상태 칩·푸터) 안에 차트를 넣고,
채널이 쓰는 도구 전부를 한 화면에 늘어놓는다.

    python tools/style/frame.py --chart out/newch/stills/sources_t0.00s.png \
        --cam C:/aelab/ae/newch-style.json --out "<신규안 폴더>"

렌더러는 캔들·이평·밴드·태그·손그림 원·문구만 그린다(브랜드 정확도). 나머지 도구 견본은
여기서 같은 카메라(X0·BW·Y0·K)로 그린다 — px(봉) = X0 + 봉·BW, py(가격) = Y0 − 가격·K.
값은 전부 신규안_v1/스펙.md. 글꼴은 brand/fonts/.
"""
import argparse, json, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
FONTS = os.path.join(ROOT, 'brand', 'fonts')
W, H = 1920, 1080

# ── 브라우저 창 기하 ─────────────────────────────────────────
DEV = (20, 20, 1900, 1060)        # 기기 테두리 (남색)
TAB = (34, 34, 1886, 92)          # 탭 줄
ADDR = (34, 92, 1886, 150)        # 주소창 줄
WIN = (34, 150, 1886, 1010)       # 콘텐츠 창 (차트)
FOOT = (34, 1010, 1886, 1046)     # 푸터 띠

# ── 팔레트 (프리셋 blob 문자열로 확정된 5색 + 크롬용 회색) ──
ROSE = (0xEF, 0x27, 0x67)
ROSE_SUB = (0xED, 0x7F, 0x89)
INK = (0x1E, 0x29, 0x3B)
INK2 = (0x33, 0x41, 0x55)
TEAL = (0x0D, 0x94, 0x88)
PINK_CHIP = (0xE9, 0x00, 0x54)
GRAY_CHIP = (0x88, 0x88, 0x88)
CHROME = (0xE6, 0xE9, 0xEE)
CHROME_LINE = (0xD5, 0xDA, 0xE1)
URL_BG = (0xF1, 0xF3, 0xF6)
SLATE = (0x94, 0xA3, 0xB8)
STOP = (0x9F, 0x00, 0x00)
LV_ENTRY, LV_STOP, LV_TARGET = 23795, 23665, 24055
ORANGE = (0xF3, 0x88, 0x08)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


F = {
    'title': lambda s: font('GmarketSansBold.otf', s),
    'chip': lambda s: font('GmarketSansMedium.otf', s),
    'nanum': lambda s: font('NanumGothicBold.otf', s),
    'gyeonggi': lambda s: font('경기천년제목_Bold.ttf', s),
    'gyeonggiM': lambda s: font('경기천년제목_Medium.ttf', s),
    'batang': lambda s: font('경기천년바탕_Bold.ttf', s),
    'body': lambda s: font('SCDream6.otf', s),
    'label': lambda s: font('SCDream5.otf', s),
}


def text_w(fnt, s):
    b = fnt.getbbox(s); return b[2] - b[0]


def spaced(d, xy, s, fnt, fill, spacing, anchor='mm'):
    total = sum(text_w(fnt, c) for c in s) + spacing * (len(s) - 1)
    x = xy[0] - total / 2 if anchor[0] == 'm' else xy[0]
    for c in s:
        d.text((x, xy[1]), c, font=fnt, fill=fill, anchor='l' + anchor[1])
        x += text_w(fnt, c) + spacing


def paper():
    base = Image.new('RGB', (W, H), (0xF4, 0xF1, 0xEC))
    p = Image.open(os.path.join(ROOT, 'brand', 'texture', '차트명가_배경(종이).jpg')).convert('RGB')
    s = max(W / p.width, H / p.height)
    p = p.resize((int(p.width * s) + 1, int(p.height * s) + 1)).crop((0, 0, W, H))
    return Image.blend(base, p, 0.35)


def logo(path, height):
    im = Image.open(os.path.join(ROOT, 'brand', 'logo', path)).convert('RGBA')
    im = im.crop(im.getbbox())
    return im.resize((int(im.width * height / im.height), height), Image.LANCZOS)


def shadow(canvas, box, r, blur=14, alpha=40, dy=8):
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((box[0], box[1] + dy, box[2], box[3] + dy), r, fill=(0, 0, 0, alpha))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


# ── 브라우저 크롬 ────────────────────────────────────────────
def chrome(canvas, tab_title, url='youtube.com/@chartmyeongga', live=True):
    shadow(canvas, DEV, 26, blur=18, alpha=70, dy=12)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle(DEV, 26, fill=INK)
    d.rounded_rectangle((TAB[0], TAB[1], TAB[2], TAB[3] + 2), 14, fill=CHROME)
    d.rectangle((TAB[0], TAB[1] + 20, TAB[2], TAB[3] + 2), fill=CHROME)
    # 창 컨트롤 점 셋 (맥 크롬 관례)
    for i, c in enumerate(((0xFF, 0x5F, 0x57), (0xFE, 0xBC, 0x2E), (0x28, 0xC8, 0x40))):
        d.ellipse((58 + i * 28 - 9, 63 - 9, 58 + i * 28 + 9, 63 + 9), fill=c)
    # 활성 탭: 파비콘(로고 심볼) + 제목
    d.rounded_rectangle((150, 44, 600, 96), 12, fill='white')
    fav = logo('차트명가_로고(투명).png', 26)
    canvas.alpha_composite(fav, (170, 57))
    d = ImageDraw.Draw(canvas)
    d.text((208, 70), tab_title, font=F['chip'](22), fill=INK, anchor='lm')
    d.text((628, 70), '+', font=F['chip'](30), fill=SLATE, anchor='mm')
    # 주소창 줄
    d.rectangle(ADDR, fill='white')
    d.line((ADDR[0], ADDR[3], ADDR[2], ADDR[3]), fill=CHROME_LINE, width=2)
    for x, s in ((72, '<'), (112, '>'), (156, 'C')):
        d.text((x, 121), s, font=F['chip'](30), fill=SLATE, anchor='mm')
    d.rounded_rectangle((196, 104, 1240, 138), 17, fill=URL_BG)
    d.ellipse((222, 114, 236, 128), outline=SLATE, width=2)
    d.text((252, 121), url, font=F['chip'](22), fill=INK2, anchor='lm')
    if live:
        d.rounded_rectangle((1284, 104, 1416, 138), 17, fill=ROSE)
        d.ellipse((1302, 115, 1314, 127), fill='white')
        d.text((1326, 121), 'LIVE', font=F['title'](20), fill='white', anchor='lm')
        spaced(d, (1436, 121), '실시간 분석', F['chip'](20), INK2, 2, anchor='lm')
    for i in range(3):
        d.ellipse((1843, 110 + i * 9, 1849, 116 + i * 9), fill=SLATE)
    # 콘텐츠 창 · 푸터
    d.rectangle(WIN, fill='white')
    d.rectangle(FOOT, fill=INK)
    spaced(d, (960, 1028), 'CHART MYEONGGA  ·  해외선물 매매기법', F['gyeonggiM'](20), ROSE_SUB, 5)


def title_block(canvas, title, sub, ticker, x=74, y=172):
    """v4 변형: 종이 질감 그라데이션 바 → 로즈 민짜 라운드 바 + 흰 악센트 + 남색 소제목 칩 + 로즈 테두리 타임프레임 칩.
    자리·크기는 최종본(좌상단 두 줄)과 같고 재질만 바꿨다 — '적당히 변형'."""
    d = ImageDraw.Draw(canvas)
    fnt = F['title'](36)
    w, h = text_w(fnt, title) + 48, 58
    shadow(canvas, (x, y, x + w, y + h), 12, blur=8, alpha=26, dy=4)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((x, y, x + w, y + h), 12, fill=ROSE)
    d.rectangle((x, y + 8, x + 6, y + h - 8), fill='white')
    d.text((x + 26, y + h // 2), title, font=fnt, fill='white', anchor='lm')
    cy = y + h + 14
    f2 = F['chip'](24)
    tw = text_w(f2, sub)
    d.rounded_rectangle((x, cy, x + tw + 40, cy + 44), 10, fill=INK)
    d.text((x + 20, cy + 22), sub, font=f2, fill='white', anchor='lm')
    x2 = x + tw + 40 + 12
    tw2 = text_w(f2, ticker)
    d.rounded_rectangle((x2, cy, x2 + tw2 + 40, cy + 44), 22, fill='white', outline=ROSE, width=3)
    d.text((x2 + 20, cy + 22), ticker, font=f2, fill=ROSE, anchor='lm')


def legend_panel(canvas, x=1640, y=172):
    """더원의 범례 박스를 브랜드 문법으로 — 타임프레임 칩 + 이평선 2줄"""
    box = (x, y, x + 214, y + 140)
    shadow(canvas, box, 12, blur=10, alpha=28, dy=4)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle(box, 12, fill='white', outline=(0xE2, 0xE8, 0xF0), width=2)
    d.rounded_rectangle((x + 14, y + 14, x + 76, y + 46), 8, fill=INK)
    d.text((x + 45, y + 30), 'D1', font=F['title'](20), fill='white', anchor='mm')
    d.text((x + 90, y + 30), '일봉 차트', font=F['chip'](22), fill=INK2, anchor='lm')
    for i, (c, s) in enumerate(((ORANGE, '20일선'), (TEAL, '50일선'))):
        yy = y + 74 + i * 32
        d.rounded_rectangle((x + 16, yy - 6, x + 44, yy + 6), 4, fill=c)
        d.text((x + 58, yy), s, font=F['chip'](22), fill=INK2, anchor='lm')


def subtitle_bar(canvas, text, y=955):
    d = ImageDraw.Draw(canvas)
    fnt = F['batang'](46)   # 최종본 자막 = 경기천년바탕 Bold (참고스틸 16장 공통·룰북 E-2)
    tw = text_w(fnt, text)
    d.rectangle((960 - tw // 2 - 30, y - 36, 960 + tw // 2 + 30, y + 36), fill=(0x11, 0x11, 0x11))
    d.rectangle((960 - tw // 2 - 30, y - 36, 960 - tw // 2 - 22, y + 36), fill=ROSE)   # v4 변형: 로즈 악센트
    d.text((960 + 4, y), text, font=fnt, fill='white', anchor='mm')


def badge(canvas, text, x, y):
    d = ImageDraw.Draw(canvas)
    fnt = F['label'](36)
    tw = text_w(fnt, text)
    d.rounded_rectangle((x - tw - 44, y - 30, x, y + 30), 10, fill=PINK_CHIP, outline='black', width=3)
    d.text((x - 22, y), text, font=fnt, fill='white', anchor='rm', stroke_width=3, stroke_fill='black')


# ── 차트 위 도구 견본 (카메라 좌표) ─────────────────────────
class Cam:
    def __init__(self, path):
        c = json.load(open(path, encoding='utf-8-sig'))['cuts'][0]['cam']
        self.X0, self.BW, self.Y0, self.K = c['X0']['v'][0], c['BW']['v'][0], c['Y0']['v'][0], c['K']['v'][0]
    def x(self, bar): return self.X0 + bar * self.BW
    def y(self, price): return self.Y0 - price * self.K


def ring(d, cam, bar, price, color, label, r=38, below=True):
    cx, cy = cam.x(bar), cam.y(price)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=7)
    ly = cy + r + 26 if below else cy - r - 26
    d.text((cx, ly), label, font=F['title'](28), fill=INK, anchor='mm', stroke_width=5, stroke_fill='white')


def box(canvas, cam, b0, b1, p0, p1, color, label, alpha=46, label_pos='in'):
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    x0, x1 = cam.x(b0) - cam.BW / 2, cam.x(b1) + cam.BW / 2
    y0, y1 = cam.y(max(p0, p1)), cam.y(min(p0, p1))
    od.rounded_rectangle((x0, y0, x1, y1), 8, fill=color + (alpha,), outline=color + (170,), width=3)
    canvas.alpha_composite(ov)
    d = ImageDraw.Draw(canvas)
    ly = (y0 + y1) / 2 if label_pos == 'in' else y0 - 22
    d.text(((x0 + x1) / 2, ly), label, font=F['title'](24), fill=INK, anchor='mm', stroke_width=5, stroke_fill='white')


def pill2(canvas, x, y, num, body, size=32):
    """v4 변형: ①②③ 핑크 알약 두 줄 → 남색 알약 한 줄 + 로즈 번호 원."""
    d = ImageDraw.Draw(canvas)
    fb = F['title'](size)
    r = size // 2 + 6
    w = text_w(fb, body) + 2 * r + 60
    h = size + 30
    shadow(canvas, (x, y, x + w, y + h), h // 2, blur=8, alpha=30, dy=4)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((x, y, x + w, y + h), h // 2, fill=INK)
    d.ellipse((x + 10, y + h // 2 - r, x + 10 + 2 * r, y + h // 2 + r), fill=ROSE)
    d.text((x + 10 + r, y + h // 2 + 1), num, font=F['title'](size - 2), fill='white', anchor='mm')
    d.text((x + 10 + 2 * r + 16, y + h // 2), body, font=fb, fill='white', anchor='lm')
    return (x, y, x + w, y + h)


def glow(canvas, cx, cy, r, color, alpha=90, ring=True):
    """v4 변형: 소프트 원(연한 면)에 같은 색 얇은 링을 하나 더 — 최종본의 부드러운 원을 조금 또렷하게"""
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse((cx - r, cy - r, cx + r, cy + r), fill=color + (alpha,))
    canvas.alpha_composite(ov.filter(ImageFilter.GaussianBlur(5)))
    if ring:
        ImageDraw.Draw(canvas).ellipse((cx - r, cy - r, cx + r, cy + r), outline=color + (235,), width=3)


def pill(d, x, y, text, color, size=22, anchor='lm', fg='white'):
    """색 알약 라벨 — 선 끝(#1 10일선/20일선/50일선) · 띠 라벨(#5 지지선 · #6 당일 시가·저항선)"""
    fnt = F['title'](size)
    tw = text_w(fnt, text)
    h = size + 18
    x0 = x if anchor == 'lm' else x - tw - 28
    d.rounded_rectangle((x0, y - h // 2, x0 + tw + 28, y + h // 2), h // 2, fill=color)
    d.text((x0 + 14, y), text, font=fnt, fill=fg, anchor='lm')
    return (x0, y - h // 2, x0 + tw + 28, y + h // 2)


def band(canvas, x0, x1, y, color, half=9, alpha=70):
    """지지선·저항선 띠 — 최종본은 반투명 초록/빨간 띠(#5·#6·#8)"""
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle((x0, y - half, x1, y + half), fill=color + (alpha,))
    canvas.alpha_composite(ov)


def dashed(d, x0, x1, y, color, width=3, dash=14, gap=10):
    x = x0
    while x < x1:
        d.line((x, y, min(x + dash, x1), y), fill=color, width=width)
        x += dash + gap


def toolkit(canvas, cam, ma, rsi_y=None):
    """전편 공통 어휘를 '적당히 변형'해 얹는다. ma = {10: 값, 20: 값, 50: 값} (마지막 봉 이평값)"""
    d = ImageDraw.Draw(canvas)
    RED = (0xD8, 0x18, 0x1B); GREEN = (0x0D, 0xA8, 0x2A)
    xr = cam.x(63) + cam.BW * 0.9
    # #1 — 이평선 끝 색 알약 (범례 대신 선 끝에)
    # 손절/익절 존 라벨 — 존 안 큰 글자 대신 오른끝 알약 (이평 알약보다 먼저 그려 아래에 깔린다)
    pill(d, cam.x(57), cam.y(24018), '익절 2', (0x14, 0xB8, 0x36), size=24)   # 존 안쪽 — 오른끝 열은 이평 알약 몫
    pill(d, cam.x(57), cam.y(23718), '손절 1', (0x9F, 0x00, 0x00), size=24)
    taken = []
    for period, color in ((10, RED), (20, ORANGE), (50, GREEN)):
        if period in ma:
            yy = cam.y(ma[period])
            for t in taken:
                if abs(yy - t) < 50: yy = t - 52 if yy <= t else t + 52
            taken.append(yy)
            pill(d, xr, yy, str(period) + '일선', color, size=22)
    # #3 — 매수 우위 구간 분홍 면 (진입 뒤, 익절선 위쪽)
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle((cam.x(44) - cam.BW / 2, cam.y(24480), cam.x(63) + cam.BW / 2, cam.y(LV_TARGET)), 10, fill=ROSE + (26,))
    canvas.alpha_composite(ov)
    d = ImageDraw.Draw(canvas)
    pill(d, cam.x(45), cam.y(24455), '매수 우위 구간', ROSE_SUB, size=22)
    # #5·#8 — 지지선 초록 띠 · #6 — 저항선 빨간 띠 (+ 알약)
    band(canvas, cam.x(6) - cam.BW / 2, cam.x(43), cam.y(23703), GREEN, alpha=60)
    band(canvas, cam.x(6) - cam.BW / 2, cam.x(43), cam.y(23852), RED, alpha=50)
    d = ImageDraw.Draw(canvas)
    xL = max(WIN[0] + 40, cam.x(6))            # 창 왼끝 안쪽
    pill(d, xL, cam.y(23703), '지지선', GREEN, size=22)
    pill(d, xL, cam.y(23852), '저항선', RED, size=22)
    # #6 — 당일 시가 점선 + 로즈 알약 (점선은 남색으로)
    y0 = cam.y(23760)
    dashed(d, cam.x(6) - cam.BW / 2, cam.x(43), y0, INK, width=3)
    pill(d, cam.x(31), y0, '당일 시가', ROSE, size=22)
    # 소프트 원 + 링 — 눌림목 저점(로즈) · 재돌파(노랑)
    glow(canvas, cam.x(39), cam.y(23700), 34, (0xFF, 0xB6, 0xC8), 90)   # 매수 태그 아래·왼쪽으로
    glow(canvas, cam.x(46), cam.y(24000), 40, (0xFF, 0xE9, 0x8A), 110)
    d = ImageDraw.Draw(canvas)
    # ①②③ 알약 (남색 + 로즈 번호 원)
    pill2(canvas, cam.x(18), cam.y(24120), '①', '정배열 확인')
    pill2(canvas, cam.x(30), cam.y(23600) + 46, '②', '20일선 눌림목')
    b = pill2(canvas, cam.x(47), cam.y(LV_STOP) + 30, '③', '반등 양봉 → 매수')   # 손절 존 아래 빈자리
    cx, cy = b[2] + 34, (b[1] + b[3]) / 2
    d.line((cx - 16, cy, cx - 4, cy + 14, cx + 20, cy - 16), fill=GREEN, width=8)
    # RSI 패널 칩 (#9 문법, 남색으로)
    pill(d, WIN[0] + 40, 800, 'RSI', INK, size=22)
    # #4·#9 — 빨간 대형 ? (횡보 가짜 신호)
    d.text((cam.x(14), cam.y(23480)), '?', font=F['title'](88), fill=RED, anchor='mm', stroke_width=6, stroke_fill='white')


def watermark(canvas):
    """우측 상단 반투명 로고 (최종본 전 회차 공통 자리) — 크롬의 파비콘과 짝"""
    lg = logo('차트명가_가로.png', 84)
    a = lg.getchannel('A').point(lambda v: int(v * 0.28))
    lg.putalpha(a)
    canvas.alpha_composite(lg, (WIN[2] - 26 - lg.width, WIN[1] + 22))


# ── 스틸 5장 ─────────────────────────────────────────────
def still_sources(chart_png, cam, a):
    base = paper().convert('RGBA')
    chrome(base, a.tab)
    chart = Image.open(chart_png).convert('RGBA').crop(WIN)
    base.alpha_composite(chart, (WIN[0], WIN[1]))
    title_block(base, a.title, a.sub, a.ticker)
    watermark(base)
    ma = {int(k): float(v) for k, v in (kv.split(':') for kv in a.ma.split(','))} if a.ma else {}
    toolkit(base, cam, ma, a.rsi_y)
    subtitle_bar(base, a.subtitle)
    badge(base, '손익비  1 : 2', 344, 340)
    return base.convert('RGB')


def still_frame_only():
    base = paper().convert('RGBA')
    chrome(base, '(탭 제목 : 회차 제목)')
    title_block(base, '(타이틀 : 고정)', '(소제목 : 파트마다 교체)', '(종목 : 타임프레임)')
    watermark(base)
    subtitle_bar(base, '(자막 : 검정 박스 + 흰 글자)')
    badge(base, '(배지)', 1856, 880)
    return base.convert('RGB')


def still_outro():
    inner = Image.new('RGB', (W, H), (0xFA, 0xFA, 0xFA))
    d = ImageDraw.Draw(inner)
    for i, r in enumerate((1180, 980, 780, 580)):
        g = 0xF4 - i * 3
        d.ellipse((960 - r, 540 - r, 960 + r, 540 + r), fill=(g, g, g))
    d.ellipse((848, 54, 1072, 278), fill=ROSE)
    d.text((960, 310), '차트명가', font=F['gyeonggi'](44), fill=INK, anchor='mm')
    d.text((136, 232), '영상 시청해주셔서', font=F['body'](30), fill=INK2, anchor='lm')
    d.text((136, 278), '감사합니다', font=F['body'](30), fill=INK2, anchor='lm')
    d.text((1784, 240), '구독', font=F['body'](30), fill=INK2, anchor='rm')
    for i in range(3):
        d.ellipse((1660 + i * 52, 278, 1690 + i * 52, 308), outline=INK2, width=3)
    for (x0, x1, label) in ((123, 835, '다음 영상'), (1083, 1795, '추천 영상')):
        d.rounded_rectangle((x0, 343, x1, 862), 16, fill=ROSE)
        mx = (x0 + x1) // 2
        d.polygon([(mx - 150, 790), (mx - 150, 820), (mx - 124, 805)], fill='white')
        d.text((mx + 20, 805), label, font=F['gyeonggi'](40), fill='white', anchor='mm')
    d.rounded_rectangle((750, 946, 1170, 1024), 12, fill=ROSE)
    d.text((960, 985), '구독하기', font=F['gyeonggi'](44), fill='white', anchor='mm')
    base = paper().convert('RGBA')
    chrome(base, '차트명가 — 시청해 주셔서 감사합니다', live=False)
    base.alpha_composite(inner.convert('RGBA').resize((WIN[2] - WIN[0], WIN[3] - WIN[1]), Image.LANCZOS), (WIN[0], WIN[1]))
    return base.convert('RGB')


def still_logo():
    im = paper().convert('RGBA')
    lg = logo('차트명가_로고(최종+핑크).png', 330)
    im.alpha_composite(lg, ((W - lg.width) // 2, 290))
    d = ImageDraw.Draw(im)
    spaced(d, (960, 680), '해외선물 매매기법의 명가', F['gyeonggi'](44), INK2, 6)
    d.rectangle((760, 740, 1160, 744), fill=ROSE)
    spaced(d, (960, 790), 'CHART MYEONGGA', F['gyeonggiM'](26), ROSE_SUB, 8)
    # 새 문법 미리보기 — 탭 파비콘 + 주소창 한 줄
    d.rounded_rectangle((640, 860, 1280, 912), 26, fill=URL_BG)
    fav = logo('차트명가_로고(투명).png', 30)
    im.alpha_composite(fav, (664, 871))
    d = ImageDraw.Draw(im)
    d.text((708, 886), 'youtube.com/@chartmyeongga', font=F['chip'](24), fill=INK2, anchor='lm')
    return im.convert('RGB')


def still_palette():
    im = paper().convert('RGB')
    d = ImageDraw.Draw(im)
    rows = [(ROSE, 'EF2767', '메인 타이틀 · 카드 · LIVE 칩'), ((0xF5, 0x0C, 0x54), 'F50C54', '①②③ 핑크 알약 배지 (실측)'),
            ((0xD8, 0x18, 0x1B), 'D8181B', '10일선 (차명#2 실측)'), ((0xF0, 0x9C, 0x0C), 'F09C0C', '34일선 (차명#2 실측)'),
            ((0x1E, 0x78, 0xC8), '1E78C8', 'RSI 라인 · 프레임 2743C9'), ((0xC0, 0x27, 0x2D), 'C0272D', '손그림 색연필 원·밑줄'),
            (INK, '1E293B', '기기 테두리 · 푸터 (신규)'), (CHROME, 'E6E9EE', '브라우저 크롬 탭 줄 (신규)')]
    y = 70
    for c, hx, role in rows:
        d.rounded_rectangle((140, y, 320, y + 96), 12, fill=c, outline=(0xDD, 0xD6, 0xCC), width=2)
        d.text((360, y + 48), hx, font=F['body'](38), fill=c if hx != 'E6E9EE' else INK2, anchor='lm')
        d.text((590, y + 48), role, font=F['body'](32), fill=INK, anchor='lm')
        y += 118
    d.text((1240, 100), '글꼴', font=F['title'](34), fill=INK, anchor='lm')
    d.text((1240, 560), '등장 규약 (FX-WHITELIST §2)', font=F['title'](30), fill=INK, anchor='lm')
    for i, t in enumerate(('텍스트·라벨 등장  4f 팝/페이드', '손그림 드로우온  10~18f', '스틸 교체·존  교차 디졸브 30f', '카메라 줌·팬·리빌  금지')):
        d.text((1240, 612 + i * 46), t, font=F['chip'](26), fill=INK2, anchor='lm')
    samples = [('타이틀 · 문구 · 라벨  GmarketSans Bold', F['title'](30)), ('칩 · 탭 · 주소창  GmarketSans Medium', F['chip'](28)),
               ('종목 칩  NanumGothic Bold', F['nanum'](28)), ('익절/손절 · 배지  S-CoreDream 5', F['label'](28)),
               ('자막 · 카드  경기천년바탕 Bold', F['batang'](30)), ('로고 · 푸터  경기천년제목', F['gyeonggi'](30))]
    y = 160
    for s, fnt in samples:
        d.text((1240, y), s, font=fnt, fill=INK2, anchor='lm'); y += 58
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chart', required=True)
    ap.add_argument('--cam', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--tab', default='차트명가 — 20일선 눌림목 매매법')
    ap.add_argument('--title', default='20일선 눌림목에서 추세를 끝까지 끌고 가는 법')
    ap.add_argument('--sub', default='#1 눌림목 + 손익비')
    ap.add_argument('--ticker', default='나스닥 · 1일 차트')
    ap.add_argument('--subtitle', default='눌림목에서 잡았으면 추세가 끝날 때까지 들고 갑니다')
    ap.add_argument('--rsi-y', type=float, default=800, dest='rsi_y')
    ap.add_argument('--ma', default='', help='10:값,20:값,50:값 — 마지막 봉 이평값(선 끝 알약)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cam = Cam(a.cam)
    outs = {
        '신규_1_로고.png': still_logo(),
        '신규_2_고정소스_총집합.png': still_sources(a.chart, cam, a),
        '신규_3_틀만.png': still_frame_only(),
        '신규_4_아웃트로.png': still_outro(),
        '신규_5_컬러팔레트.png': still_palette(),
    }
    for name, im in outs.items():
        p = os.path.join(a.out, name); im.save(p); print('  →', p)


if __name__ == '__main__':
    main()
