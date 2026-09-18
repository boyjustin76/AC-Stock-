# -*- coding: utf-8 -*-
"""
틀만(조립 완성본) — 가운데를 뚫은 투명 PNG. 레퍼런스 '트레이딩팩토리_2_틀만.png' 와 같은 형식
(1920×1080 RGBA, 콘텐츠 자리 알파 0). 제목·자막·배지·낙관 같은 회차 요소는 넣지 않는다.

  python tools/style/frames_clean.py --out <폴더> [--chart-v1 PNG] [--chart-v2 PNG] [--variant all|clean]

  A 브라우저 창 (신규안 v1 계열)  — 기기 테두리 · 점 셋 · + · 주소창(뒤로/앞으로/새로고침 · URL · 메뉴)
  B 병풍 (신규안 v2 전통)          — 한지 여백 · 창호 실물 띠 · 쪽빛 병풍 테두리
  --variant clean (2026-09-15 팀장 요청) — B 병풍에서 위 창호(기와) 띠를 빼고 한지만, 한지는 살짝 더 하얗게.
      B_병풍_한지만          뚫린 자리가 기존 B 와 **똑같다** (그대로 바꿔 끼우는 용)
      B_병풍_한지만_여백균등  띠가 빠진 만큼 위 여백을 좌우·아래(60px)와 맞춤 — 뚫린 자리가 위로 58px 커진다

각 틀마다  <이름>_틀만.png (투명)  ·  <이름>_적용예시.png (차트를 밑에 깐 미리보기)  를 낸다.
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frame as V1          # 브라우저 크롬 기하·팔레트·글꼴
import trad as V2           # 한지·창호·병풍

W, H = 1920, 1080
# 한지를 살짝 더 하얗게 (2026-09-15 팀장) — 기존 V2.HANJI #ECE3D3 에서 흰색 쪽으로 약 40%. 종이 결(닥종이 사진 편차)은 그대로.
HANJI_WHITE = (0xF3, 0xEE, 0xE3)


def punch(canvas, box, r=0, ss=4, flat_top=False):
    """box 안을 알파 0 으로 뚫는다. 모서리 둥글림은 4배로 그려 줄여서 계단이 안 생기게.
    flat_top — 위 두 모서리는 각지게(주소창 아래에 딱 붙는 창). 레퍼런스 트팩 틀만과 같다."""
    x0, y0, x1, y1 = box
    m = Image.new('L', (W * ss, H * ss), 255)
    md = ImageDraw.Draw(m)
    top = (y0 - r - 2) if flat_top else y0
    md.rounded_rectangle((x0 * ss, top * ss, x1 * ss - 1, y1 * ss - 1), r * ss, fill=0)
    if flat_top:
        md.rectangle((0, 0, W * ss, y0 * ss - 1), fill=255)
    m = m.resize((W, H), Image.LANCZOS)
    a = np.minimum(np.array(canvas.getchannel('A')), np.array(m))
    px = np.array(canvas)
    px[..., 3] = a
    px[a == 0, :3] = 0          # 뚫린 자리 RGB 도 0 — 레퍼런스와 같게. 뷰어가 알파를 무시해도 밑그림이 안 비친다
    return Image.fromarray(px, 'RGBA')


# ── A 브라우저 창 ─────────────────────────────────────────────
def frame_browser(url='youtube.com/@chartmyeongga'):
    c = V1.paper().convert('RGBA')
    V1.shadow(c, V1.DEV, 26, blur=18, alpha=70, dy=12)
    d = ImageDraw.Draw(c)
    d.rounded_rectangle(V1.DEV, 26, fill=V1.INK)
    # 탭 줄 — 점 셋 + '+' 만 (탭 제목 없음)
    T = V1.TAB
    d.rounded_rectangle((T[0], T[1], T[2], T[3] + 2), 14, fill=V1.CHROME)
    d.rectangle((T[0], T[1] + 20, T[2], T[3] + 2), fill=V1.CHROME)
    for i, col in enumerate(((0xFF, 0x5F, 0x57), (0xFE, 0xBC, 0x2E), (0x28, 0xC8, 0x40))):
        d.ellipse((58 + i * 28 - 9, 63 - 9, 58 + i * 28 + 9, 63 + 9), fill=col)
    d.text((1850, 63), '+', font=V1.F['chip'](30), fill=V1.SLATE, anchor='mm')
    # 주소창 줄 — 뒤로·앞으로·새로고침 · URL · 메뉴 (LIVE 칩·문구 없음)
    A = V1.ADDR
    d.rectangle(A, fill='white')
    d.line((A[0], A[3], A[2], A[3]), fill=V1.CHROME_LINE, width=2)
    for x, s in ((72, '<'), (112, '>'), (156, 'C')):
        d.text((x, 121), s, font=V1.F['chip'](30), fill=V1.SLATE, anchor='mm')
    d.rounded_rectangle((196, 104, 1800, 138), 17, fill=V1.URL_BG)
    d.ellipse((222, 114, 236, 128), outline=V1.SLATE, width=2)
    d.text((252, 121), url, font=V1.F['chip'](22), fill=V1.INK2, anchor='lm')
    for i in range(3):
        d.ellipse((1843, 110 + i * 9, 1849, 116 + i * 9), fill=V1.SLATE)
    # 콘텐츠 자리 — 푸터 글자 띠를 없애고 창을 기기 안쪽 끝까지 내린다
    hole = (V1.WIN[0], A[3] + 2, V1.WIN[2], V1.DEV[3] - 14)
    return punch(c, hole, r=14, flat_top=True), hole


# ── B 병풍 ────────────────────────────────────────────────────
def frame_byeongpung():
    V2.random.seed(7); np.random.seed(7)
    c = V2.hanji().convert('RGBA')
    panel = (60, 118, 1860, 1020)                     # 자막 자리가 빠져 아래 여백을 위·좌우와 맞춤
    V2.byeongpung_frame(c, panel)
    c.alpha_composite(V2.changho_strip(W, 92).convert('RGBA'), (0, 0))
    g = 14 + 5 + 2                                    # 비단 띠 14 + 한지 틈 5 + 가는 쪽선 2 — 안쪽 선까지 틀로 남긴다
    hole = (panel[0] + g, panel[1] + g, panel[2] - g, panel[3] - g)
    return punch(c, hole, r=0), hole


def frame_byeongpung_clean(panel=(60, 118, 1860, 1020), base=HANJI_WHITE):
    """B 병풍 한지만 — 위 창호(기와) 띠 없이 한지 + 쪽빛 병풍 테두리만 (2026-09-15 팀장 요청).
    바탕은 살짝 더 하얀 한지. 결은 기존과 같은 닥종이 사진(같은 씨앗)이라 톤만 바뀐다."""
    V2.random.seed(7); np.random.seed(7)
    c = V2.hanji(base=base).convert('RGBA')
    V2.byeongpung_frame(c, panel)
    g = 14 + 5 + 2
    hole = (panel[0] + g, panel[1] + g, panel[2] - g, panel[3] - g)
    return punch(c, hole, r=0), hole


def preview(frame, hole, chart_path, under='white', hanji_base=None):
    """적용 예시 — 차트를 뚫린 자리에 맞춰 깔고 틀을 얹는다. 차트는 흰 바탕 렌더를 자리에 맞게 줄인다."""
    x0, y0, x1, y1 = hole
    base = Image.new('RGBA', (W, H), (255, 255, 255, 255))
    if under == 'hanji':
        np.random.seed(7)
        base = (V2.hanji(base=hanji_base) if hanji_base else V2.hanji()).convert('RGBA')
    if chart_path and os.path.exists(chart_path):
        ch = Image.open(chart_path).convert('RGB')
        bb = Image.eval(ch.convert('L'), lambda v: 255 if v < 245 else 0).getbbox()  # 그림이 있는 영역
        if bb:
            pad = 40
            bb = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(W, bb[2] + pad), min(H, bb[3] + pad))
            ch = ch.crop(bb)
        s = min((x1 - x0) * 0.92 / ch.width, (y1 - y0) * 0.86 / ch.height)
        ch = ch.resize((int(ch.width * s), int(ch.height * s)), Image.LANCZOS)
        px, py = x0 + ((x1 - x0) - ch.width) // 2, y0 + ((y1 - y0) - ch.height) // 2
        layer = Image.new('RGB', (W, H), (255, 255, 255)); layer.paste(ch, (px, py))
        if under == 'hanji':
            from PIL import ImageChops
            base = ImageChops.multiply(base.convert('RGB'), layer).convert('RGBA')
        else:
            base = layer.convert('RGBA')
    base.alpha_composite(frame)
    return base.convert('RGB')


def report(name, fr, hole):
    al = np.array(fr.getchannel('A'))
    tb = Image.fromarray((al < 10).astype(np.uint8) * 255).getbbox()
    top = np.array(fr.convert('RGB'))[4:40, 200:1720].reshape(-1, 3).mean(axis=0)   # 위 여백 한지 평균색
    print(name, 'hole', hole, '투명 상자', tb, '투명 비율 %.3f' % (al < 10).mean(),
          '위 여백 평균색 #%02X%02X%02X' % tuple(int(round(v)) for v in top))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--chart-v1', default='out/newch-trad/stills/trad_t0.00s.png')
    ap.add_argument('--chart-v2', default='out/newch-trad/stills/trad_t0.00s.png')
    ap.add_argument('--variant', choices=['all', 'clean'], default='all',
                    help="all = A 브라우저창 · B 병풍 (기존) / clean = B 병풍 한지만 2종만 (기존 파일은 안 건드린다)")
    a = ap.parse_args()
    # 윈도우는 경로 끝의 공백·마침표를 조용히 떼어 낸다 — 만들 때 떼지 않으면
    # 끝 공백은 그 뒤 파일 쓰기가 FileNotFoundError 로 터지고, 끝 마침표는
    # 아무 소리 없이 다른 이름의 폴더에 쌓인다 (B·E 실측 + D 재현 2026-09-18).
    a.out = a.out.rstrip(' .')
    os.makedirs(a.out, exist_ok=True)
    if a.variant == 'all':
        jobs = (('A_브라우저창', frame_browser, a.chart_v1, 'white', None),
                ('B_병풍', frame_byeongpung, a.chart_v2, 'hanji', None))
    else:
        jobs = (('B_병풍_한지만', lambda: frame_byeongpung_clean((60, 118, 1860, 1020)), a.chart_v2, 'hanji', HANJI_WHITE),
                ('B_병풍_한지만_여백균등', lambda: frame_byeongpung_clean((60, 60, 1860, 1020)), a.chart_v2, 'hanji', HANJI_WHITE))
    for name, make, chart, under, hb in jobs:
        fr, hole = make()
        fr.save(os.path.join(a.out, name + '_틀만.png'))
        preview(fr, hole, chart, under, hb).save(os.path.join(a.out, name + '_적용예시.png'))
        report(name, fr, hole)


if __name__ == '__main__':
    main()
