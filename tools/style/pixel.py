"""그림의 지정 상자 안에서 '지배색'을 잰다 — 비전 모델이 말한 색을 숫자로 확정하는 용도.

    python tools/style/pixel.py <그림> "이름:x0,y0,x1,y1" ["이름:..." ...]

각 상자에서 흰 배경(밝기 245 이상)과 검정 획(밝기 40 이하)을 뺀 뒤 가장 흔한 색을 낸다.
글자·테두리가 섞인 상자면 두 번째로 흔한 색도 같이 낸다. 좌표는 원본 픽셀.
"""
import sys
from collections import Counter
from PIL import Image

path = sys.argv[1]
im = Image.open(path).convert('RGB')
W, H = im.size
print(f'  {path.split(chr(92))[-1].split("/")[-1]}  {W}x{H}')

for spec in sys.argv[2:]:
    name, box = spec.split(':')
    x0, y0, x1, y1 = [int(v) for v in box.split(',')]
    px = list(im.crop((x0, y0, x1, y1)).getdata())
    c = Counter()
    for r, g, b in px:
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        # 흰 배경은 버리고, '검정 획'은 채도까지 낮을 때만 버린다 — 순수 파랑(#0200F3)·
        # 암적색(#9F0000)은 밝기가 낮아도 채도가 높아 여기 안 걸린다 (09-10 에 걸려서 고침)
        sat = max(r, g, b) - min(r, g, b)
        if lum >= 245 or (lum <= 40 and sat < 60):
            continue
        # 8단계로 뭉쳐서 안티에일리어싱 흔들림을 흡수한다
        c[(r >> 3 << 3, g >> 3 << 3, b >> 3 << 3)] += 1
    n = sum(c.values())
    tops = c.most_common(3)
    parts = [f'#{r:02X}{g:02X}{b:02X} {cnt / n * 100:.0f}%' for (r, g, b), cnt in tops] if n else ['(배경뿐)']
    print(f'  {name:<12} {x0},{y0}~{x1},{y1}  ' + ' · '.join(parts))
