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
    """차트명가 타이틀 바(로즈 그라데이션+종이) + 칩 2 — 콘텐츠 창 좌상단"""
    fnt = F['title'](36)
    w, h = text_w(fnt, title) + 44, 56
    bar = Image.new('RGB', (w, h))
    bd = ImageDraw.Draw(bar)
    c0, c1 = (0x8C, 0x53, 0x5D), (0xD7, 0x6D, 0x83)
    for i in range(w):
        t = i / max(1, w - 1)
        bd.line([(i, 0), (i, h)], fill=tuple(int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3)))
    bar = Image.blend(bar, paper().crop((x, y, x + w, y + h)), 0.18)
    canvas.paste(bar, (x, y))
    d = ImageDraw.Draw(canvas)
    d.text((x + 24, y + h // 2 + 2), title, font=fnt, fill=(60, 20, 30), anchor='lm')
    d.text((x + 22, y + h // 2), title, font=fnt, fill='white', anchor='lm')
    cy = y + h + 14
    for text, color, fnt2 in ((sub, GRAY_CHIP, F['chip'](24)), (ticker, PINK_CHIP, F['nanum'](24))):
        tw = text_w(fnt2, text)
        d.rounded_rectangle((x, cy, x + tw + 40, cy + 44), 22, fill=color)
        d.text((x + 20, cy + 22), text, font=fnt2, fill='white', anchor='lm')
        x += tw + 40 + 14


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
    fnt = F['title'](38)
    tw = text_w(fnt, text)
    d.rectangle((960 - tw // 2 - 26, y - 33, 960 + tw // 2 + 26, y + 33), fill=(0x11, 0x11, 0x11))
    d.text((960, y), text, font=fnt, fill='white', anchor='mm')


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


def toolkit(canvas, cam):
    """트팩_1 의 도구 견본 전부를 브랜드 문법으로: 링 = 7px 팔레트 색, 라벨 = GmarketSans Bold + 흰 외곽선.
    자리는 세 구역 — 왼쪽(크로스·추세 시작) · 가운데(눌림목·진입) · 오른쪽(청산·돌파·조정)."""
    d = ImageDraw.Draw(canvas)
    # 저항 추세선 — 30번 고점 → 46번 고점, 62번까지 연장 (앵커 사각 셋)
    (ax, ay), (bx, by) = (cam.x(30), cam.y(23852)), (cam.x(46), cam.y(24032))
    ex = cam.x(62); ey = ay + (by - ay) * (ex - ax) / (bx - ax)
    d.line((ax, ay, ex, ey), fill=INK, width=4)
    for px, py in ((ax, ay), (bx, by), (ex, ey)):
        d.rectangle((px - 6, py - 6, px + 6, py + 6), fill='white', outline=INK, width=3)
    d.text((ex - 30, ey + 36), '추세선', font=F['title'](26), fill=INK, anchor='rm', stroke_width=5, stroke_fill='white')
    # 구간 박스 — 라벨은 박스 위쪽에 얹어 안의 캔들·링과 안 겹치게
    box(canvas, cam, 33, 37, 23695, 23815, ROSE, '눌림목 구간', label_pos='top')
    box(canvas, cam, 48, 54, 23945, 24040, (0x60, 0xA5, 0xFA), '횡보 / 조정', label_pos='in')
    d = ImageDraw.Draw(canvas)
    # 링 견본
    ring(d, cam, 20, 23513, INK2, '지지', r=32, below=True)
    ring(d, cam, 30, 23852, INK, '저항', below=False)
    ring(d, cam, 24, 23688, INK, '데드크로스', below=True)
    ring(d, cam, 60, 24363, TEAL, '청산', below=False)
    d.text((cam.x(14), cam.y(23425) + 92), '골든크로스', font=F['title'](28), fill=INK, anchor='mm', stroke_width=5, stroke_fill='white')
    # 추적 손절 — 짧은 암적 선 (익절 밴드 안, 조정 구간 아래)
    # 비전 QA: 익절 밴드 안에 두면 20일선과 겹쳐 안 읽힌다 → 손절 밴드 안(빈 자리)으로. '올린 손절'로 읽힌다
    y = cam.y(23760); x0, x1 = cam.x(48), cam.x(55)
    d.line((x0, y, x1, y), fill=STOP, width=6)
    d.text(((x0 + x1) / 2, y + 24), '추적 손절', font=F['title'](24), fill=STOP, anchor='mm', stroke_width=5, stroke_fill='white')
    # 핑크 지시선 — 저항 돌파 봉
    tx, ty = cam.x(45), cam.y(23960)
    d.line((tx, ty - 120, tx, ty - 14), fill=PINK_CHIP, width=6)
    d.line((tx - 24, ty - 40, tx, ty - 14, tx + 24, ty - 40), fill=PINK_CHIP, width=6)
    d.text((tx, ty - 146), '저항 돌파', font=F['title'](26), fill=PINK_CHIP, anchor='mm', stroke_width=5, stroke_fill='white')


# ── 스틸 5장 ─────────────────────────────────────────────
def still_sources(chart_png, cam, a):
    base = paper().convert('RGBA')
    chrome(base, a.tab)
    chart = Image.open(chart_png).convert('RGBA').crop(WIN)
    base.alpha_composite(chart, (WIN[0], WIN[1]))
    title_block(base, a.title, a.sub, a.ticker)
    legend_panel(base)
    toolkit(base, cam)
    subtitle_bar(base, a.subtitle)
    badge(base, '손익비  1 : 2', 1856, 880)
    return base.convert('RGB')


def still_frame_only():
    base = paper().convert('RGBA')
    chrome(base, '(탭 제목 : 회차 제목)')
    title_block(base, '(타이틀 : 고정)', '(소제목 : 파트마다 교체)', '(종목 : 타임프레임)')
    legend_panel(base)
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
    rows = [(ROSE, 'EF2767', '메인 타이틀 · 카드 · LIVE 칩'), (ROSE_SUB, 'ED7F89', '서브 타이틀 · 로고 · 푸터 글자'),
            (INK, '1E293B', '기기 테두리 · 푸터 · 링 라벨'), (TEAL, '0D9488', '50일선 · 청산 · 반대 개념 강조'),
            (INK2, '334155', '부가 설명 · 지지 링 · 차트 UI'), (CHROME, 'E6E9EE', '브라우저 크롬 (탭 줄) — 신규')]
    y = 110
    for c, hx, role in rows:
        d.rounded_rectangle((140, y, 340, y + 104), 12, fill=c, outline=(0xDD, 0xD6, 0xCC), width=2)
        d.text((390, y + 52), hx, font=F['body'](42), fill=c if hx != 'E6E9EE' else INK2, anchor='lm')
        d.text((640, y + 52), role, font=F['body'](36), fill=INK, anchor='lm')
        y += 132
    d.text((1240, 140), '글꼴', font=F['title'](34), fill=INK, anchor='lm')
    samples = [('타이틀 · 문구 · 링 라벨  GmarketSans Bold', F['title'](30)), ('칩 · 탭 · 주소창  GmarketSans Medium', F['chip'](28)),
               ('종목 칩  NanumGothic Bold', F['nanum'](28)), ('익절/손절 라벨 · 배지  S-CoreDream 5', F['label'](28)),
               ('로고 · 푸터  경기천년제목', F['gyeonggi'](30)), ('댓글 유도  경기천년바탕', F['batang'](30))]
    y = 200
    for s, fnt in samples:
        d.text((1240, y), s, font=fnt, fill=INK2, anchor='lm'); y += 60
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chart', required=True)
    ap.add_argument('--cam', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--tab', default='차트명가 — 20일선 눌림목')
    ap.add_argument('--title', default='20일선 눌림목에서 추세를 끝까지 끌고 가는 법')
    ap.add_argument('--sub', default='#1 눌림목 + 손익비')
    ap.add_argument('--ticker', default='나스닥 : 1일 차트')
    ap.add_argument('--subtitle', default='눌림목에서 잡았으면 추세가 끝날 때까지 들고 갑니다')
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
