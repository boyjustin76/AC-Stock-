"""새 채널 스타일 스틸 5장 — 틀(베젤)·상단 띠·하단 띠를 그리고 렌더 스틸과 합성한다.

    python tools/style/frame.py --chart out/newch/stills/sources_t0.00s.png --out "<신규안 폴더>"

값은 전부 신규안_v1/스펙.md 에서 온다. 글꼴은 brand/fonts/ 의 파일을 직접 쓴다.
비전 모델이 아니라 이 스크립트가 그리므로 같은 입력이면 같은 그림이 나온다.
"""
import argparse, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
FONTS = os.path.join(ROOT, 'brand', 'fonts')
W, H = 1920, 1080
WIN = (40, 150, 1880, 980)          # 차트 창 (스펙 §1)
BEZEL = (0xF4, 0xF1, 0xEC)
ROSE = (0xEF, 0x27, 0x67)
ROSE_SUB = (0xED, 0x7F, 0x89)
INK = (0x1E, 0x29, 0x3B)
INK2 = (0x33, 0x41, 0x55)
TEAL = (0x0D, 0x94, 0x88)
PINK_CHIP = (0xE9, 0x00, 0x54)
GRAY_CHIP = (0x88, 0x88, 0x88)


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
}


def paper_bezel():
    """웜 오프화이트 + 종이 질감 35%"""
    base = Image.new('RGB', (W, H), BEZEL)
    paper = Image.open(os.path.join(ROOT, 'brand', 'texture', '차트명가_배경(종이).jpg')).convert('RGB')
    pw, ph = paper.size
    s = max(W / pw, H / ph)
    paper = paper.resize((int(pw * s) + 1, int(ph * s) + 1)).crop((0, 0, W, H))
    return Image.blend(base, paper, 0.35)


def rounded(draw, box, r, **kw):
    draw.rounded_rectangle(box, radius=r, **kw)


def text_w(fnt, s):
    b = fnt.getbbox(s)
    return b[2] - b[0]


def draw_text(draw, xy, s, fnt, fill, anchor='la', spacing=0):
    if spacing:
        x, y = xy
        for ch in s:
            draw.text((x, y), ch, font=fnt, fill=fill, anchor=anchor)
            x += text_w(fnt, ch) + spacing
    else:
        draw.text(xy, s, font=fnt, fill=fill, anchor=anchor)


def logo_crop(path, height):
    im = Image.open(path).convert('RGBA')
    bb = im.getbbox()
    im = im.crop(bb)
    s = height / im.height
    return im.resize((int(im.width * s), height), Image.LANCZOS)


def title_bar(canvas, x, y, text, size=38):
    """로즈 그라데이션 + 종이 질감 + 흰 글자 (차트명가 타이틀 바)"""
    fnt = F['title'](size)
    tw = text_w(fnt, text)
    w, h = tw + 44, size + 18
    grad = Image.new('RGB', (w, h))
    gd = ImageDraw.Draw(grad)
    c0, c1 = (0x8C, 0x53, 0x5D), (0xD7, 0x6D, 0x83)
    for i in range(w):
        t = i / max(1, w - 1)
        gd.line([(i, 0), (i, h)], fill=tuple(int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3)))
    paper = paper_bezel().crop((x, y, x + w, y + h))
    bar = Image.blend(grad, paper, 0.18)
    canvas.paste(bar, (x, y))
    d = ImageDraw.Draw(canvas)
    d.text((x + 22 + 2, y + h // 2 + 2), text, font=fnt, fill=(60, 20, 30), anchor='lm')
    d.text((x + 22, y + h // 2), text, font=fnt, fill='white', anchor='lm')
    return x + w, y + h


def chip(canvas, x, y, text, color, fnt, h=44, pad=20):
    d = ImageDraw.Draw(canvas)
    tw = text_w(fnt, text)
    rounded(d, (x, y, x + tw + pad * 2, y + h), h // 2, fill=color)
    d.text((x + pad, y + h // 2), text, font=fnt, fill='white', anchor='lm')
    return x + tw + pad * 2


def overlay(title, sub, ticker, with_window=True, footer=True):
    """베젤 + 상단 띠 + 하단 띠. 창 자리는 투명."""
    bez = paper_bezel().convert('RGBA')
    if with_window:
        mask = Image.new('L', (W, H), 255)
        md = ImageDraw.Draw(mask)
        rounded(md, WIN, 16, fill=0)
        bez.putalpha(mask)
        d = ImageDraw.Draw(bez)
        rounded(d, WIN, 16, outline=(0xDD, 0xD6, 0xCC, 255), width=2)
        # 안쪽 그림자 — 창 가장자리 8px 를 살짝 어둡게
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        rounded(sd, (WIN[0] - 6, WIN[1] - 6, WIN[2] + 6, WIN[3] + 6), 20, outline=(0, 0, 0, 40), width=10)
        sh = sh.filter(ImageFilter.GaussianBlur(8))
        sh.putalpha(ImageChops.multiply(sh.getchannel('A'), mask))
        bez = Image.alpha_composite(bez, sh)
    d = ImageDraw.Draw(bez)
    if title:
        title_bar(bez, 60, 28, title)
        x = 60
        x = chip(bez, x, 96, sub, GRAY_CHIP, F['chip'](24)) + 16
        chip(bez, x, 96, ticker, PINK_CHIP, F['nanum'](24))
    # '우측 로고 타이틀.png' 은 알파 상자를 재 보니 원형 심볼만(85×90) 들어 있다 — 글자까지 있는 가로 로고를 쓴다
    logo = logo_crop(os.path.join(ROOT, 'brand', 'logo', '차트명가_가로.png'), 96)
    bez.alpha_composite(logo, (1880 - logo.width, 75 - logo.height // 2))
    if footer:
        d = ImageDraw.Draw(bez)
        d.rectangle((WIN[0], 1000, WIN[2], 1004), fill=ROSE)
        draw_text(d, (960, 1044), '차트명가  ·  해외선물 매매기법', F['gyeonggiM'](24), INK2, anchor='mm', spacing=2)
    return bez


def subtitle_box(canvas, text, y=930, size=40):
    """차트명가 자막 — 검정 박스 + 흰 굵은 글자, 창 하단 중앙 (더원 자막바와 같은 자리)"""
    d = ImageDraw.Draw(canvas)
    fnt = F['title'](size)
    tw = text_w(fnt, text)
    x0, x1 = 960 - tw // 2 - 26, 960 + tw // 2 + 26
    d.rectangle((x0, y - size // 2 - 14, x1, y + size // 2 + 14), fill=(0x11, 0x11, 0x11))
    d.text((960, y), text, font=fnt, fill='white', anchor='mm')


def still_sources(chart_png, title, sub, ticker, subtitle):
    base = Image.open(chart_png).convert('RGBA')
    if subtitle:
        subtitle_box(base, subtitle)
    return Image.alpha_composite(base, overlay(title, sub, ticker)).convert('RGB')


def still_frame_only():
    base = Image.new('RGBA', (W, H), (255, 255, 255, 255))
    return Image.alpha_composite(base, overlay('(타이틀 : 고정)', '(소제목 : 파트마다 교체)', '(종목 : 타임프레임)')).convert('RGB')


def still_logo():
    im = paper_bezel().convert('RGBA')
    # 브랜드 원본은 로즈(ED7F89 계열) — 그대로 쓴다. 상단 띠의 남색본은 베젤 위 대비용 변형이다
    logo = logo_crop(os.path.join(ROOT, 'brand', 'logo', '차트명가_로고(최종+핑크).png'), 330)
    im.alpha_composite(logo, ((W - logo.width) // 2, 290))
    d = ImageDraw.Draw(im)
    draw_text(d, (960, 680), '해외선물 매매기법의 명가', F['gyeonggi'](44), INK2, anchor='mm', spacing=6)
    d.rectangle((760, 740, 1160, 744), fill=ROSE)
    draw_text(d, (960, 790), 'CHART MYEONGGA', F['gyeonggiM'](26), ROSE_SUB, anchor='mm', spacing=8)
    return im.convert('RGB')


def still_palette():
    im = paper_bezel().convert('RGB')
    d = ImageDraw.Draw(im)
    rows = [(ROSE, 'EF2767', '메인 타이틀 · 카드 · 아웃트로'), (ROSE_SUB, 'ED7F89', '서브 타이틀 · 로고'),
            (INK, '1E293B', '전체 배경 또는 일반 본문 텍스트'), (TEAL, '0D9488', '반대되는 개념의 서브 강조'),
            (INK2, '334155', '부가 설명 자막 · 테두리 · 차트 UI'), (BEZEL, 'F4F1EC', '틀(베젤) — 신규')]
    y = 120
    for c, hx, role in rows:
        rounded(d, (140, y, 340, y + 110), 12, fill=c, outline=(0xDD, 0xD6, 0xCC), width=2)
        d.text((390, y + 55), hx, font=F['body'](44), fill=c if hx != 'F4F1EC' else INK2, anchor='lm')
        d.text((640, y + 55), role, font=F['body'](40), fill=INK, anchor='lm')
        y += 140
    d.text((1240, 150), '글꼴', font=F['title'](34), fill=INK, anchor='lm')
    samples = [('타이틀 · 문구  GmarketSans Bold', F['title'](32)), ('칩  GmarketSans Medium', F['chip'](30)),
               ('종목 칩  NanumGothic Bold', F['nanum'](30)), ('라벨  S-CoreDream 5 Medium', font('SCDream5.otf', 30)),
               ('로고 · 푸터  경기천년제목', F['gyeonggi'](32)), ('댓글 유도  경기천년바탕', F['batang'](32))]
    y = 210
    for s, fnt in samples:
        d.text((1240, y), s, font=fnt, fill=INK2, anchor='lm'); y += 62
    return im


def still_outro():
    """차트명가 아웃트로 구조를 창 안에 (동심원 · 로즈 원 · 카드 2 · 구독하기)"""
    inner = Image.new('RGB', (W, H), (0xFA, 0xFA, 0xFA))
    d = ImageDraw.Draw(inner)
    cx, cy = 960, 540
    for i, r in enumerate((1180, 980, 780, 580)):
        g = 0xF4 - i * 3
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(g, g, g))
    d.ellipse((848, 54, 1072, 278), fill=ROSE)
    d.text((960, 310), '차트명가', font=F['gyeonggi'](44), fill=INK, anchor='mm')
    d.text((136, 232), '영상 시청해주셔서', font=F['body'](30), fill=INK2, anchor='lm')
    d.text((136, 278), '감사합니다', font=F['body'](30), fill=INK2, anchor='lm')
    d.text((1784, 240), '구독', font=F['body'](30), fill=INK2, anchor='rm')
    for i in range(3):
        d.ellipse((1660 + i * 52, 278, 1690 + i * 52, 308), outline=INK2, width=3)
    for (x0, x1, label) in ((123, 835, '다음 영상'), (1083, 1795, '추천 영상')):
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((x0 + 6, 350, x1 + 6, 870), 16, fill=(0, 0, 0, 22))
        inner.paste(Image.alpha_composite(inner.convert('RGBA'), sh.filter(ImageFilter.GaussianBlur(10))).convert('RGB'))
        d = ImageDraw.Draw(inner)
        rounded(d, (x0,343, x1, 862), 16, fill=ROSE)
        mx = (x0 + x1) // 2
        d.polygon([(mx - 150, 790), (mx - 150, 820), (mx - 124, 805)], fill='white')
        d.text((mx + 20, 805), label, font=F['gyeonggi'](40), fill='white', anchor='mm')
    rounded(d, (750, 946, 1170, 1024), 12, fill=ROSE)
    d.text((960, 985), '구독하기', font=F['gyeonggi'](44), fill='white', anchor='mm')
    # 창 안으로 축소해 베젤 위에 올린다
    ww, wh = WIN[2] - WIN[0], WIN[3] - WIN[1]
    scaled = inner.resize((ww, wh), Image.LANCZOS)
    base = Image.new('RGBA', (W, H), (255, 255, 255, 255))
    base.paste(scaled, (WIN[0], WIN[1]))
    return Image.alpha_composite(base, overlay(None, None, None)).convert('RGB')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chart', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--title', default='20일선 눌림목에서 추세를 끝까지 끌고 가는 법')
    ap.add_argument('--sub', default='#1 눌림목 + 손익비')
    ap.add_argument('--ticker', default='나스닥 : 1일 차트')
    ap.add_argument('--subtitle', default='눌림목에서 잡았으면 추세가 끝날 때까지 들고 갑니다')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    outs = {
        '신규_1_로고.png': still_logo(),
        '신규_2_고정소스_총집합.png': still_sources(a.chart, a.title, a.sub, a.ticker, a.subtitle),
        '신규_3_틀만.png': still_frame_only(),
        '신규_4_아웃트로.png': still_outro(),
        '신규_5_컬러팔레트.png': still_palette(),
    }
    for name, im in outs.items():
        p = os.path.join(a.out, name)
        im.save(p)
        print('  →', p, im.size)


if __name__ == '__main__':
    main()
