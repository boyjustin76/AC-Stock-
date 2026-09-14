# -*- coding: utf-8 -*-
"""
C4 가 AE 에서 찍은 프레임으로 ① 움직임 미리보기 GIF ② 등장 끝난 프레임 대조를 만든다.

  python tools/ae/trad_motion_preview.py [--cap C:/aelab/trad_motion_check] [--pack C:/aelab/pack/trad_motion]

AE 의 saveFrameToPng 는 **알파가 미리 곱해진 PNG** 다 (11-4 풀버전 때 잡은 함정).
그래서 바탕에 얹을 때 C + 바탕·(1−a) 로 합친다 — 보통 알파 합성을 하면 반투명이 어두워진다.

대조 기준
  stamp/drawon  원본 PNG 를 같은 자리에 얹은 그림 (f40 이면 등장이 끝나 원본과 같아야 한다)
  scroll        합성기(trad.jokja) 스틸 — AE 는 글자를 AE 궁서로 새로 짜므로 글자 가장자리 차이는 남는다
"""
import argparse, io, json, os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'style'))
import trad as T

W, H = 1920, 1080


def load_premult(path, bg):
    a = np.array(Image.open(path).convert('RGBA')).astype(np.float32) / 255
    b = np.array(bg.convert('RGB')).astype(np.float32) / 255
    out = a[..., :3] + b * (1 - a[..., 3:4])
    return Image.fromarray((np.clip(out, 0, 1) * 255).round().astype(np.uint8))


def paste_straight(bg, png, x, y):
    c = bg.convert('RGBA')
    c.alpha_composite(Image.open(png).convert('RGBA'), (x, y))
    return c.convert('RGB')


def diff_pct(a, b, box):
    A = np.array(a.crop(box)).astype(int); B = np.array(b.crop(box)).astype(int)
    d = np.abs(A - B).max(axis=2)
    return (d > 8).mean() * 100, int(d.max())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cap', default='C:/aelab/trad_motion_check')
    ap.add_argument('--pack', default='C:/aelab/pack/trad_motion')
    a = ap.parse_args()
    np.random.seed(7)
    bg = T.hanji()
    motion = json.load(io.open(os.path.join(a.pack, 'footage', 'motion.json'), encoding='utf-8'))
    by_title = {i['title']: i for i in motion['items']}
    cmap = {}
    for line in io.open(os.path.join(a.cap, '_map.txt'), encoding='utf-8'):
        if '\t' in line:
            k, v = line.rstrip('\n').split('\t', 1)
            cmap[int(k)] = v
    prev = os.path.join(a.cap, 'preview'); os.makedirs(prev, exist_ok=True)
    rows = []
    for idx, name in sorted(cmap.items()):
        it = by_title.get(name)
        fin = os.path.join(a.cap, 'final_%d.png' % idx)
        if not it or not os.path.exists(fin):
            rows.append((name, None, None, '캡처 없음')); continue
        got = load_premult(fin, bg)
        if it['kind'] == 'scroll':
            ref = bg.convert('RGBA'); np.random.seed(7)
            T.jokja(ref, it['text'], it['y'], it['size']); ref = ref.convert('RGB')
            box = (300, it['y'] - 70, 1620, min(H, it['y'] + 68))
        else:
            ref = paste_straight(bg, os.path.join(a.pack, 'footage', it['file']), it['x'], it['y0'])
            box = (max(0, it['x'] - 10), max(0, it['y0'] - 10), min(W, it['x'] + it['w'] + 10), min(H, it['y0'] + it['h'] + 10))
        pct, mx = diff_pct(got, ref, box)
        rows.append((name, pct, mx, it['kind']))
        if it['kind'] == 'scroll':
            sb = Image.new('RGB', (box[2] - box[0], (box[3] - box[1]) * 2 + 6), (255, 0, 0))
            sb.paste(ref.crop(box), (0, 0)); sb.paste(got.crop(box), (0, box[3] - box[1] + 6))
            sb.save(os.path.join(prev, '대조_%s.png' % name))
        # 움직임 GIF — 캡처가 있는 대표 셋
        frames = sorted(f for f in os.listdir(a.cap) if f.startswith('anim_%d_' % idx))
        if frames:
            if it['kind'] == 'scroll':
                crop = (240, it['y'] - 80, 1680, min(H, it['y'] + 68))
            else:
                cx, cy = it['x'] + it['w'] // 2, it['y0'] + it['h'] // 2
                r = max(it['w'], it['h']) // 2 + 90
                crop = (max(0, cx - r), max(0, cy - r), min(W, cx + r), min(H, cy + r))
            ims = [load_premult(os.path.join(a.cap, f), bg).crop(crop) for f in frames]
            hold = [ims[-1]] * 20                                   # 끝에서 잠깐 멈춘다
            ims[0].save(os.path.join(prev, '움직임_%s.gif' % name), save_all=True, append_images=ims[1:] + hold,
                        duration=33, loop=0)
            # 한 장짜리 연속 사진 (프레임 번호 표시)
            step = [0, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 21, 26]
            pick = [(n, ims[n]) for n in step if n < len(ims)]
            tw_, th_ = ims[0].size
            s = 360 / tw_ if it['kind'] != 'scroll' else 720 / tw_
            cw, chh = int(tw_ * s), int(th_ * s)
            cols = 7 if it['kind'] != 'scroll' else 2
            sheet = Image.new('RGB', (cols * cw, ((len(pick) + cols - 1) // cols) * (chh + 22)), (40, 40, 40))
            d = ImageDraw.Draw(sheet)
            for k, (n, im) in enumerate(pick):
                x0, y0 = (k % cols) * cw, (k // cols) * (chh + 22)
                sheet.paste(im.resize((cw, chh)), (x0, y0 + 22))
                d.text((x0 + 6, y0 + 4), 'f%d' % n, fill=(255, 255, 255))
            sheet.save(os.path.join(prev, '연속_%s.png' % name))
    for name, pct, mx, kind in rows:
        if pct is None:
            print('%-22s %s' % (name, kind))
        else:
            print('%-22s %-6s f40 vs 원본: 8/255 초과 %.2f%%  최대차 %d' % (name, kind, pct, mx))


if __name__ == '__main__':
    main()
