# -*- coding: utf-8 -*-
"""
C6 가 AE 에서 찍은 프레임으로 ① 합성기 기준과 픽셀 대조 ② 움직임 미리보기(GIF · 연속 사진)를 만든다.

  python tools/ae/trad_rr_preview.py --chart out/newch-trad/stills/trad_t0.00s.png [--cap C:/aelab/trad_rr_check] [--pack C:/aelab/pack/trad_rr]

AE 의 saveFrameToPng 는 알파가 미리 곱해진 PNG 다 → 바탕에 C + 바탕·(1−a) 로 얹는다 (trad_motion_preview 와 같다).
대조 기준은 trad_rr.py 가 그린 _ref.png (글자까지 합성기). AE 는 글자를 AE 궁서로 새로 짜므로 글자 가장자리 차이는 남는다.
미리보기만 v2 차트(한지 × 차트)를 바닥에 깐다 — 납품 컴포지션에는 바닥이 없다.
"""
import argparse, io, json, os, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'style'))
import trad as T


def load_premult(path, bg):
    a = np.array(Image.open(path).convert('RGBA')).astype(np.float32) / 255
    b = np.array(bg.convert('RGB')).astype(np.float32) / 255
    out = a[..., :3] + b * (1 - a[..., 3:4])
    return Image.fromarray((np.clip(out, 0, 1) * 255).round().astype(np.uint8))


def over(bg, ref):
    c = bg.convert('RGBA'); c.alpha_composite(ref); return c.convert('RGB')


def diff(a, b, box):
    A = np.array(a.crop(box)).astype(int); B = np.array(b.crop(box)).astype(int)
    d = np.abs(A - B).max(axis=2)
    return (d > 8).mean() * 100, int(d.max())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chart', required=True)
    ap.add_argument('--cap', default='C:/aelab/trad_rr_check')
    ap.add_argument('--pack', default='C:/aelab/pack/trad_rr')
    a = ap.parse_args()
    rr = json.load(io.open(os.path.join(a.pack, 'footage', 'rr.json'), encoding='utf-8'))
    ref = Image.open(os.path.join(a.pack, '_ref.png')).convert('RGBA')
    np.random.seed(7)
    bg = T.hanji().convert('RGB')
    base = ImageChops.multiply(bg, Image.open(a.chart).convert('RGB'))
    prev = os.path.join(a.cap, 'preview'); os.makedirs(prev, exist_ok=True)

    want = over(bg, ref)
    got = load_premult(os.path.join(a.cap, 'main_150.png'), bg)
    rows = []
    for it in rr['items']:
        box = tuple(int(round(v)) for v in it['box'])
        box = (max(0, box[0]), max(0, box[1]), min(1920, box[2]), min(1080, box[3]))
        if it.get('main', True):
            p_main, m_main = diff(got, want, box)
        else:                                   # 지지선·저항선은 전체 컴포지션에 없다 — 소스 대조만
            p_main, m_main = None, None
        src = os.path.join(a.cap, 'src_%s.png' % it['id'])
        one = os.path.join(a.pack, 'refs', '%s.png' % it['id'])       # 그 요소 하나만 그린 기준
        if os.path.exists(src) and os.path.exists(one):
            p_src, _ = diff(load_premult(src, bg), over(bg, Image.open(one).convert('RGBA')), box)
        else:
            p_src = None
        rows.append((it['title'], it['kind'], p_main, m_main, p_src))
    full_pct, _ = diff(got, want, (0, 0, 1920, 1080))

    # 대조 한 장: 위 합성기 · 아래 AE
    crop = (0, 270, 1920, 810)      # 선·박스가 화면 전체 폭이다 (2026-09-14 2차)
    w, h = crop[2] - crop[0], crop[3] - crop[1]
    sb = Image.new('RGB', (w, h * 2 + 8), (200, 0, 0))
    sb.paste(want.crop(crop), (0, 0)); sb.paste(got.crop(crop), (0, h + 8))
    sb.save(os.path.join(prev, '대조_합성기(위)_AE(아래).png'))
    load_premult(os.path.join(a.cap, 'main_150.png'), base).save(os.path.join(prev, 'AE_f150_차트위.png'))

    # 움직임 — 차트 위에 얹어 GIF + 연속 사진
    frames = sorted(f for f in os.listdir(a.cap) if f.startswith('anim_'))
    s = 0.7
    ims = []
    for fn in frames:
        im = load_premult(os.path.join(a.cap, fn), base).crop(crop)
        ims.append(im.resize((int(w * s), int(h * s)), Image.LANCZOS))
    if ims:
        pal = [im.convert('P', palette=Image.ADAPTIVE, colors=200) for im in ims]
        pal[0].save(os.path.join(prev, '움직임_손익비.gif'), save_all=True, append_images=pal[1:] + [pal[-1]] * 10,
                    duration=66, loop=0, optimize=True)
        pick = [0, 6, 10, 16, 22, 34, 44, 100, 112, 124, 134, 150, 160, 174]
        byf = {int(fn[5:8]): i for i, fn in enumerate(frames)}
        cw, chh = ims[0].size
        cw2, ch2 = cw // 2, chh // 2
        cols = 4
        sel = [(f_, ims[byf[f_]]) for f_ in pick if f_ in byf]
        sheet = Image.new('RGB', (cols * cw2, ((len(sel) + cols - 1) // cols) * (ch2 + 22)), (40, 40, 40))
        d = ImageDraw.Draw(sheet)
        for k, (f_, im) in enumerate(sel):
            x0, y0 = (k % cols) * cw2, (k // cols) * (ch2 + 22)
            sheet.paste(im.resize((cw2, ch2), Image.LANCZOS), (x0, y0 + 22))
            d.text((x0 + 6, y0 + 4), 'f%d (%.2fs)' % (f_, f_ / 30.0), fill=(255, 255, 255))
        sheet.save(os.path.join(prev, '연속_손익비.png'))

    print('%-14s %-6s %s' % ('소스', '종류', 'f150 AE vs 합성기 (8/255 초과 · 최대차) | 소스 컴포 f30 vs 전체 f150'))
    for t, k, p, m, ps in rows:
        head = '   (전체에 없음)   ' if p is None else '%6.2f%%  %3d   ' % (p, m)
        print('%-14s %-6s %s| %s' % (t, k, head, '-' if ps is None else '%.2f%%' % ps))
    print('화면 전체 %.2f%%' % full_pct)


if __name__ == '__main__':
    main()
