# -*- coding: utf-8 -*-
"""라이브 롤링 광고 배너 — 차트명가 NEW 전통판 (2026-09-16).

트레이딩팩토리 원본(`Claude/라이브화면 프레임/라이브_롤링 광고/원본()_*`)의
**문구·구성·좌표는 그대로 두고 톤앤매너만** 전통(병풍·낙관)으로 바꾼 것이다.

원본 실측 (색 무리별 바운딩 박스로 잼)
  긴 판 8000x504    글자띠 y127~399(높이 271) · 왼쪽 장식 x0~1029 · 오른쪽 장식 x6970~7999
                    CTA 알약 x6347~7915 y105~398 · 본문 시작 x1060
  짧은 판 8000x750  글자띠 y224~606(높이 338) · 왼쪽 장식 x0~1560 · 오른쪽 장식 x6439~7430
                    CTA 알약 x5970~7835 y200~549 · 본문 시작 x1160

바꾼 것 (무드보드.md 팔레트)
  검정 바탕        → 한지 #F3EEE3 (라이브화면 본체와 같은 톤)
  형광 연두 #01FF17 → 인주 적 #D42A26
  흰 본문          → 먹 #1C1A17
  노랑             → 단청 황(글자용) #9E7B12
  청록·보라 평행사변형 → 쪽 #2C3358 + 옅은 쪽 (같은 실루엣, 우리 색)
  빨강 알약 CTA     → 현판 (옻칠 #221E1B + 금테 #B08D3C + 흰 궁서)
  연두 테두리 박스   → 인주 적 테두리 박스
  글꼴             → 궁서

  python tools/style/roll_ad.py --out "<라이브화면 폴더>/롤링광고"
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trad as V2                      # noqa: E402  한지·궁서·인주 질감을 그대로 쓴다
import frames_clean as FC              # noqa: E402  한지 흰 톤(#F3EEE3)

HANJI_W = FC.HANJI_WHITE
ACCENT = V2.RED          # 강조 = 인주 적
BODY = V2.INK            # 본문 = 먹
YEL = V2.YEL_TXT         # 노랑 = 단청 황(한지 위 대비용)
SILK = V2.JJOK           # 장식 = 쪽
LACQ = V2.LACQ
GOLD = V2.GOLD
PAPER = V2.HANJI2        # 현판 위 글자

# 원본에서 잰 규격
SPEC = {
    'long':  dict(size=(8000, 504), cy=263, fs=272, gap=44,
                  deco_l=1030, deco_r=1030, x0=1060,
                  pill=(6347, 105, 7915, 398), box_h=414, box_y=45),
    'short': dict(size=(8000, 750), cy=395, fs=338, gap=52,
                  deco_l=1560, deco_r=1560, x0=1160,
                  pill=(5970, 200, 7835, 549), box_h=520, box_y=115),
}


def paper(w, h):
    """한지 바탕 — 결은 trad.py 의 닥종이 사진 그대로.

    trad.hanji() 의 결 텍스처는 1920 폭으로 고정돼 있어 8000 을 한 번에 못 만든다.
    종이 결은 방향성이 없으니 1920 조각을 **좌우로 뒤집어 가며 이어 붙인다** — 이음매가 안 보인다."""
    tile = V2.hanji(1920, h, base=HANJI_W).convert('RGBA')
    if w <= 1920:
        return tile.crop((0, 0, w, h))
    c = Image.new('RGBA', (w, h))
    flip = tile.transpose(Image.FLIP_LEFT_RIGHT)
    x = 0
    i = 0
    while x < w:
        c.alpha_composite(tile if i % 2 == 0 else flip, (x, 0))
        x += 1920
        i += 1
    return c.crop((0, 0, w, h))


# 로고에서 실측한 막대 다섯의 높이비 (brand/logo/차트명가_로고(투명).png, 2026-09-16)
BARS = [0.38, 0.48, 0.77, 0.60, 1.00]
MOTIF = 'bars'          # bars · eave · rings — --motif 로 고른다


def _bars(d, x0, y0, x1, y1, color, alpha, flip, gap=0.30):
    """안1 막대 계단 — 로고 막대 다섯. 로고처럼 **막대 사이에 틈**을 둬 표가 아니라 그래프로 읽히게."""
    n = len(BARS)
    slot = (x1 - x0) / float(n)
    bw = slot * (1 - gap)
    hs = BARS[::-1] if flip else BARS
    for i, h in enumerate(hs):
        bx = x0 + slot * i + (slot - bw) / 2
        by = y1 - (y1 - y0) * h
        d.rectangle((bx, by, bx + bw, y1), fill=color + (alpha,))


def _eave(d, x0, x1, y, h, color, alpha, up):
    """안2 처마 — 로고 지붕의 치켜올린 선. 면이 아니라 **띠**로 그린다.
    가운데는 낮고 양끝이 올라가는 곡선(처마)을 두께 있는 밴드로."""
    import math
    n = 64
    top, bot = [], []
    for i in range(n + 1):
        t = i / float(n)
        # 0~1 을 지나며 양끝이 올라가는 곡선
        k = (2 * t - 1) ** 2
        yy = y - (h * k if up else -h * k)
        x = x0 + (x1 - x0) * t
        top.append((x, yy))
        bot.append((x, yy + (h * 0.42 if up else -h * 0.42)))
    d.polygon(top + bot[::-1], fill=color + (alpha,))


def _ring(d, cx, cy, r, w, color, alpha):
    """안3 원 — 로고의 테두리 원. 채우지 않고 **선**으로 두어 가볍게."""
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color + (alpha,), width=w)


def deco(canvas, spec):
    """양끝 모서리 문양 — 차트명가 로고에서 뽑았다.

    트팩 원본의 기울어진 평행사변형은 **트팩 로고에서 나온 모양**이라 그대로 쓰지 않는다
    (2026-09-16 이정찬 지시). 우리 로고의 요소로 바꾼다 — 막대 다섯 · 처마 · 원.
    """
    W, H = canvas.size
    d = ImageDraw.Draw(canvas, 'RGBA')
    dl, dr = spec['deco_l'], spec['deco_r']

    if MOTIF == 'bars':
        # 옅은 한 겹을 뒤로 깔고 진한 막대를 앞에 — 원본의 겹침을 우리 모양으로
        _bars(d, -int(dl * 0.10), int(H * 0.30), int(dl * 0.92), H, SILK, 70, False)
        _bars(d, 0, int(H * 0.52), int(dl * 0.78), H, SILK, 235, False)
        _bars(d, W - int(dr * 0.92), int(H * 0.30), W + int(dr * 0.10), H, SILK, 70, True)
        _bars(d, W - int(dr * 0.78), int(H * 0.52), W, H, SILK, 235, True)

    elif MOTIF == 'eave':
        _eave(d, -int(dl * 0.15), int(dl * 1.02), int(H * 0.30), int(H * 0.42), SILK, 235, True)
        _eave(d, -int(dl * 0.15), int(dl * 0.80), int(H * 0.16), int(H * 0.30), SILK, 90, True)
        _eave(d, W - int(dr * 1.02), W + int(dr * 0.15), int(H * 0.70), int(H * 0.42), SILK, 235, False)
        _eave(d, W - int(dr * 0.80), W + int(dr * 0.15), int(H * 0.84), int(H * 0.30), SILK, 90, False)

    else:   # rings
        _ring(d, int(dl * 0.10), int(H * 0.16), int(H * 0.62), max(8, H // 26), SILK, 235)
        _ring(d, int(dl * 0.62), int(H * 0.52), int(H * 0.42), max(6, H // 34), SILK, 110)
        _ring(d, W - int(dr * 0.10), int(H * 0.84), int(H * 0.62), max(8, H // 26), SILK, 235)
        _ring(d, W - int(dr * 0.62), int(H * 0.48), int(H * 0.42), max(6, H // 34), SILK, 110)


def runs_width(runs, f, gap):
    w = 0
    for i, (s, _) in enumerate(runs):
        w += V2.tw(f, s) + (gap if i else 0)
    return w


def fit(runs, gap, avail, fs, floor=0.55):
    """남은 폭에 들어갈 때까지 글자 크기를 줄인다. 원본처럼 한 줄에 다 넣어야 한다."""
    s = fs
    while s > fs * floor:
        f = V2.gung(int(s))
        if runs_width(runs, f, gap) <= avail:
            return V2.gung(int(s)), int(s)
        s -= 4
    return V2.gung(int(fs * floor)), int(fs * floor)


def draw_runs(canvas, x, cy, runs, f, gap):
    """[(글자, 색)] 을 왼쪽부터 잇는다. 세로는 글자 가운데 기준."""
    for s, col in runs:
        V2.btext(canvas, (x, cy), s, f, col, anchor='lm', bold=1)
        x += V2.tw(f, s) + gap
    return x


def plaque(canvas, box, text, fs):
    """CTA — 원본 빨강 알약 자리에 현판(옻칠 + 금테 + 흰 궁서)."""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(canvas, 'RGBA')
    sh = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((x0 + 8, y0 + 12, x1 + 8, y1 + 12), fill=(0, 0, 0, 70))
    canvas.alpha_composite(sh.filter(V2.ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(canvas, 'RGBA')
    d.rectangle((x0, y0, x1, y1), fill=LACQ)
    d.rectangle((x0 + 12, y0 + 12, x1 - 12, y1 - 12), outline=GOLD, width=5)
    inner = (x1 - x0) - 2 * (12 + 5) - 40
    s = fs
    while s > 10 and V2.tw(V2.gung(int(s)), text) > inner:
        s -= 2
    V2.btext(canvas, ((x0 + x1) / 2, (y0 + y1) / 2 + 2), text, V2.gung(int(s)), PAPER,
             anchor='mm', bold=1)


def keybox(canvas, x, y0, y1, text, fs, gap=48):
    """원본의 연두 테두리 박스 → 인주 적 테두리 박스. 오른쪽 끝 x 를 돌려준다."""
    f = V2.gung(fs)
    w = V2.tw(f, text) + gap * 2
    d = ImageDraw.Draw(canvas, 'RGBA')
    d.rectangle((x, y0, x + w, y1), outline=ACCENT, width=9)
    V2.btext(canvas, (x + w / 2, (y0 + y1) / 2 + 2), text, f, ACCENT, anchor='mm', bold=1)
    return x + w


# ---------------------------------------------------------------- 문구
# 트레이딩팩토리 원본 문구를 **그대로** 옮겼다 (2026-09-16 이정찬 지시 — 톤앤매너만 바꾼다).
# 팀장 문구가 정해지면 여기만 고치고 다시 뽑으면 된다.
# '영트모' · 'TF 시그널' · '셀퍼럴' 은 트팩 쪽 이름이라 차트명가 문구가 나오면 바뀔 자리다.
COPY = {
    'a1_accent': '해외선물 필수 혜택!',
    'a1_body':   '거래 수수료를 돌려받는 방법은?',
    'b1_body':   '흔들리는 시장,',
    'b1_accent': '이제 TF 시그널로 매매 기준 잡으세요!',
    'a2_key':    '영트모 셀퍼럴 환급',
    'a2_body':   '으로 지금 바로 수익 극대화! (+프리미엄 보조지표 공유)',
    'b2_key':    '영트모 VIP 서비스',
    'b2_body':   '실시간 관점 공유 및',
    'b2_yel':    '셀퍼럴 환급!',
    'sa2_accent': '영트모에서 셀퍼럴',
    'sa2_body':   '환급으로 돌려받자!',
    'sb2_key':   '영트모',
    'sb2_body1': '매매관점 /',
    'sb2_yel':   '셀퍼럴 환급',
    'sb2_body2': '까지',
    'cta':       '고정댓글 확인',
    'arrow':     '》',
}


def tri(canvas, cx, cy, s, color):
    """▼ — 궁서에 없을 수 있어 직접 그린다."""
    ImageDraw.Draw(canvas, 'RGBA').polygon(
        [(cx - s, cy - s * 0.62), (cx + s, cy - s * 0.62), (cx, cy + s * 0.78)], fill=color)


def cta(canvas, box, fs):
    """▼ 고정댓글 확인 ▼ — 현판 안에 삼각형 둘과 글자.

    글자+삼각형을 한 덩어리로 보고 **금테 안쪽 폭에 들어갈 때까지 줄인다.**
    (2026-09-16: 삼각형이 테두리에 걸치는 것을 사용자가 잡아 줬다.)"""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    inner = (x1 - x0) - 2 * (12 + 5) - 56        # 금테(12+5) 양쪽 + 안쪽 여백

    s = fs
    while s > 10:
        f = V2.gung(int(s))
        t = V2.tw(f, COPY['cta'])
        tri_s = s * 0.20
        block = t + 2 * (tri_s * 2.4 + tri_s)     # 글자 + 양옆 삼각형 자리
        if block <= inner:
            break
        s -= 2

    plaque(canvas, box, COPY['cta'], int(s))
    f = V2.gung(int(s))
    t = V2.tw(f, COPY['cta'])
    tri_s = s * 0.20
    tri(canvas, cx - t / 2 - tri_s * 2.4, cy, tri_s, PAPER)
    tri(canvas, cx + t / 2 + tri_s * 2.4, cy, tri_s, PAPER)


def rule(canvas, x0, x1, y, color=ACCENT, w=7):
    ImageDraw.Draw(canvas, 'RGBA').rectangle((x0, y, x1, y + w), fill=color)


def build(kind, name, fn, with_deco=True):
    """원본 실측: 왼쪽에 박스나 로고가 오는 판에는 모서리 장식 면이 **없다**.
    글자만 있는 판(a_1 · B_1 · A_1 · B_1)과 배경 판에만 있다."""
    sp = SPEC[kind]
    W, H = sp['size']
    c = paper(W, H)
    if with_deco:
        deco(c, sp)
    if fn:
        fn(c, sp)
    return name, c


def b_a1(c, sp):
    runs = [(COPY['a1_accent'], ACCENT), (COPY['a1_body'], BODY)]
    avail = c.size[0] - sp['deco_r'] - sp['x0'] - 80
    f, _ = fit(runs, sp['gap'], avail, sp['fs'])
    draw_runs(c, sp['x0'], sp['cy'], runs, f, sp['gap'])


def b_b1(c, sp):
    runs = [(COPY['b1_body'], BODY), (COPY['b1_accent'], ACCENT)]
    avail = c.size[0] - sp['deco_r'] - sp['x0'] - 80
    f, _ = fit(runs, sp['gap'], avail, sp['fs'])
    draw_runs(c, sp['x0'], sp['cy'], runs, f, sp['gap'])


def b_a2(c, sp):
    f = V2.gung(sp['fs'])
    end = keybox(c, 57, sp['box_y'], sp['box_y'] + sp['box_h'], COPY['a2_key'], sp['fs'])
    runs = [(COPY['a2_body'], BODY)]
    x = end + 90
    f, _ = fit(runs, sp['gap'], sp['pill'][0] - x - 120, sp['fs'])
    draw_runs(c, x, sp['cy'], runs, f, sp['gap'])
    cta(c, sp['pill'], int(sp['fs'] * 0.74))


def b_b2(c, sp):
    f = V2.gung(sp['fs'])
    end = keybox(c, 57, sp['box_y'], sp['box_y'] + sp['box_h'], COPY['b2_key'], sp['fs'])
    x0, y0, x1, y1 = sp['pill']
    gg = (x1 - x0)
    plaque(c, (end + 90, y0, end + 90 + int(gg * 0.60), y1), COPY['arrow'], int(sp['fs'] * 0.8))
    x = end + 90 + int(gg * 0.60) + 110
    runs = [(COPY['b2_body'], BODY), (COPY['b2_yel'], YEL)]
    f, _ = fit(runs, sp['gap'], sp['pill'][0] - x - 120, sp['fs'])
    draw_runs(c, x, sp['cy'], runs, f, sp['gap'])
    cta(c, sp['pill'], int(sp['fs'] * 0.74))


LOGO_WIDE = os.path.join(HERE, '..', '..', 'brand', 'logo', '차트명가_로고(최종+핑크).png')


def s_a2(c, sp):
    """짧은 판 A_2 — 왼쪽에 차트명가 로고를 **그대로** 얹는다 (다시 그리지 않는다).
    원본 트팩도 이 자리에 심볼+워드마크를 두었다(x186~1054 · 높이 약 330)."""
    lg = Image.open(LOGO_WIDE).convert('RGBA')
    lg = lg.crop(lg.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
    lw = 870
    lg = lg.resize((lw, int(lg.height * lw / lg.width)), Image.LANCZOS)
    c.alpha_composite(lg, (186, int(sp['cy'] - lg.height / 2)))
    x = 186 + lw + 170
    runs = [(COPY['sa2_accent'], ACCENT), (COPY['sa2_body'], BODY)]
    f, _ = fit(runs, sp['gap'], sp['pill'][0] - x - 120, sp['fs'])
    draw_runs(c, x, sp['cy'], runs, f, sp['gap'])
    cta(c, sp['pill'], int(sp['fs'] * 0.74))


def s_b2(c, sp):
    f = V2.gung(sp['fs'])
    key = COPY['sb2_key']
    kw = V2.tw(f, key)
    V2.btext(c, (sp['x0'], sp['cy']), key, f, ACCENT, anchor='lm', bold=1)
    rule(c, sp['x0'], sp['x0'] + kw, sp['cy'] - sp['fs'] * 0.72)
    rule(c, sp['x0'], sp['x0'] + kw, sp['cy'] + sp['fs'] * 0.60)
    x0, y0, x1, y1 = sp['pill']
    x = sp['x0'] + kw + 130
    plaque(c, (x, y0, x + 380, y1), COPY['arrow'], int(sp['fs'] * 0.8))
    x += 380 + 120
    runs = [(COPY['sb2_body1'], BODY), (COPY['sb2_yel'], YEL), (COPY['sb2_body2'], BODY)]
    f, _ = fit(runs, sp['gap'], sp['pill'][0] - x - 120, sp['fs'])
    draw_runs(c, x, sp['cy'], runs, f, sp['gap'])
    cta(c, sp['pill'], int(sp['fs'] * 0.74))


#            (파일 이름, 그리는 함수, 모서리 장식 여부)
LONG = [('라이브_a_1', b_a1, True), ('라이브_a_2', b_a2, False),
        ('라이브_B_1', b_b1, True), ('라이브_B_2', b_b2, False),
        ('라이브_배경', None, True)]
SHORT = [('하이라이트_A_1', b_a1, True), ('하이라이트_A_2', s_a2, False),
         ('하이라이트_B_1', b_b1, True), ('하이라이트_B_2', s_b2, False),
         ('하이라이트_배경', None, True)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--motif', default='bars', choices=('bars', 'eave', 'rings'),
                    help='모서리 문양 — 차트명가 로고에서 뽑은 것 중 고른다')
    a = ap.parse_args()
    global MOTIF
    MOTIF = a.motif
    dl = os.path.join(a.out, '원본(방송 라이브 버전)_long')
    ds = os.path.join(a.out, '원본(하이라이트 버전)_short')
    os.makedirs(dl, exist_ok=True)
    os.makedirs(ds, exist_ok=True)

    for name, fn, dk in LONG:
        n, c = build('long', name, fn, dk)
        p = os.path.join(dl, n + ('.png' if '배경' in n else '.jpg'))
        (c.convert('RGB') if p.endswith('.jpg') else c).save(p, quality=95)
        print('  ', os.path.basename(p), c.size)
    for name, fn, dk in SHORT:
        n, c = build('short', name, fn, dk)
        p = os.path.join(ds, n + ('.png' if '배경' in n else '.jpg'))
        (c.convert('RGB') if p.endswith('.jpg') else c).save(p, quality=95)
        print('  ', os.path.basename(p), c.size)

    # 고정댓글 — 377x71 짜리 작은 현판
    c = Image.new('RGBA', (377, 71), (0, 0, 0, 0))
    cta(c, (0, 0, 376, 70), 26)
    c.save(os.path.join(dl, '고정댓글.png'))
    print('   고정댓글.png (377, 71)')


if __name__ == '__main__':
    main()
