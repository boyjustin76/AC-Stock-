# -*- coding: utf-8 -*-
"""build_rollad 가 .ai 에서 뽑은 png 와 roll_ad.py 가 그린 무손실 png 를 판마다 비교한다.

"똑같이" 를 눈이 아니라 값으로 본다. 차이가 **어디서** 나는지도 나눠 센다 —
글자 가장자리 안티앨리어싱은 두 렌더러가 다를 수밖에 없고, 판·금테 자리가 어긋나는 건 버그다.

  python tools/illustrator/rollad_compare.py [--dir tools/illustrator/_rollad]

보는 값
  평균차     채널 평균 절대차 (0~255)
  큰차 %     한 채널이라도 48 넘게 다른 픽셀 비율 — 눈에 띄는 차이
  구역별     큰차 픽셀이 글자 잉크 상자 안 / 무늬 안 / 그 밖(판·금테·바탕) 중 어디에 있나
diff/<판>.png 에 큰차 픽셀을 빨갛게 찍어 둔다.
"""
import argparse
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BIG = 48


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.join(HERE, '_rollad'))
    a = ap.parse_args()
    lay = json.load(open(os.path.join(a.dir, 'layout.json'), encoding='utf-8'))
    os.makedirs(os.path.join(a.dir, 'diff'), exist_ok=True)

    worst = 0.0
    for b in lay['boards']:
        ref = Image.open(os.path.join(a.dir, 'ref', b['name'] + '.png')).convert('RGBA')
        p = os.path.join(a.dir, 'ai_png', b['name'] + '.png')
        if not os.path.exists(p):
            print('%-14s  .ai 에서 뽑은 png 없음' % b['name'])
            continue
        ai = Image.open(p).convert('RGBA')
        if ai.size != ref.size:
            print('%-14s  크기 다름 %s vs %s' % (b['name'], ai.size, ref.size))
            continue

        # 투명 판(고정댓글)은 검정 위에 얹어 비교 — 알파 차이도 색 차이로 드러난다
        def flat(im):
            bg = Image.new('RGBA', im.size, (0, 0, 0, 255))
            return np.asarray(Image.alpha_composite(bg, im).convert('RGB')).astype(np.int16)
        r, x = flat(ref), flat(ai)
        d = np.abs(r - x)
        mean = d.mean()
        big = d.max(axis=2) > BIG
        H, W = big.shape

        zone = np.zeros((H, W), np.uint8)          # 0 그 밖 · 1 글자 · 2 무늬
        for it in b['items']:
            if it['kind'] == 'image' and it.get('role') == 'mark':
                x0, y0 = max(0, int(it['x'])), max(0, int(it['y']))
                zone[y0:int(it['y'] + it['h']), x0:int(it['x'] + it['w'])] = 2
        for it in b['items']:
            if it['kind'] == 'text':
                x0, y0, x1, y1 = it['ink']
                zone[max(0, y0 - 4):y1 + 4, max(0, x0 - 4):x1 + 4] = 1

        nb = int(big.sum())
        parts = [int((big & (zone == z)).sum()) for z in (1, 2, 0)]
        pct = nb / big.size * 100
        worst = max(worst, parts[2] / big.size * 100)
        print('%-14s 평균차 %5.2f · 큰차 %6.3f%%  (글자 %d · 무늬 %d · 그 밖 %d)'
              % (b['name'], mean, pct, *parts))

        vis = Image.fromarray(np.uint8(r)).convert('RGB')
        red = Image.new('RGB', vis.size, (255, 0, 0))
        vis.paste(red, (0, 0), Image.fromarray(np.uint8(big) * 255))
        vis.save(os.path.join(a.dir, 'diff', b['name'] + '.png'))

    print('판·금테·바탕 자리의 큰차 최대 %.4f%% — 0 에 가까워야 자리가 맞은 것' % worst)


if __name__ == '__main__':
    main()
