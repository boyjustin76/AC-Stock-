"""라이브화면에 깔 한지 바탕을 굽는다.

왜 파이썬인가 — 한지는 '바탕색 + 닥종이 사진의 밝기 편차'다 (tools/style/trad.py hanji()).
곱하기·오버레이 같은 블렌드모드로는 그 값이 안 나온다. 일러스트레이터에서 흉내 내는 대신
D 가 쓰는 함수를 그대로 불러 굽는다 — 같은 공식이 두 벌 생기지 않게.

    python tools/illustrator/make_bg.py --out "<납품 폴더>"

바탕색은 frames_clean.HANJI_WHITE (#F3EEE3). 2026-09-15 팀장 '한지를 더 하얗게' 반영분이고,
틀만_완성 의 B_병풍 한지 버전과 같은 값이다.
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.style import trad as V2                     # noqa: E402
from tools.style.frames_clean import HANJI_WHITE       # noqa: E402

W, H = 1920, 1080


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, help='결과를 넣을 폴더')
    ap.add_argument('--name', default='한지바탕_1920x1080.png')
    ap.add_argument('--seal', type=int, default=56, help='채널 낙관 한 변(px)')
    ap.add_argument('--band', type=int, nargs=4, default=(17, 140, 1519, 218),
                    help='정보 띠 자리 x0 y0 x1 y1 — 여기만 잘라 따로 저장한다')
    ap.add_argument('--band-name', default='한지띠_정보.png')
    ap.add_argument('--seal-name', default='낙관_차트명가.png')
    ap.add_argument('--seed', type=int, default=11,
                    help='결을 자르는 자리가 난수다. 같은 그림을 다시 얻으려면 고정한다')
    a = ap.parse_args()

    import numpy as np
    np.random.seed(a.seed)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    img = V2.hanji(W, H, base=HANJI_WHITE)
    p = out / a.name
    img.save(p)
    arr = np.asarray(img).reshape(-1, 3)
    print(f'{p}  {img.size}')
    print(f'  평균 #{int(arr[:,0].mean()):02X}{int(arr[:,1].mean()):02X}{int(arr[:,2].mean()):02X}'
          f'  편차 {arr.std():.1f}  (바탕 #{HANJI_WHITE[0]:02X}{HANJI_WHITE[1]:02X}{HANJI_WHITE[2]:02X})')

    # ── 채널 낙관 (알파 포함) ──────────────────────────────────
    # 벡터로 바꾸지 않는다: 인주 질감(노이즈 침식)이 낙관의 정체성이라 벡터화하면 그게 죽는다.
    # imagetosvg 로 시험해 보니 단색 한 덩어리로 뭉갰다 (2026-09-16).
    # 필요한 치수로 '다시 그린다' — 확대가 아니다. seal() 이 잉크폭·거친 가장자리를 치수에 맞춰 다시 잡는다.
    from PIL import Image
    side = a.seal
    canvas = Image.new('RGBA', (side * 2, side * 2), (0, 0, 0, 0))
    V2.seal(canvas, side, side, '차트명가', w=side, h=side, cols=2)
    seal_img = canvas.crop(canvas.getbbox())
    ps = out / a.seal_name
    seal_img.save(ps)
    print(f'{ps}  {seal_img.size}')

    # ── 정보 띠에 깔 한지 띠 ────────────────────────────────────
    # 메인 프레임은 가운데가 뚫려 있어 바탕이 없다. 그런데 정보 띠에는 먹 글씨가 앉으므로
    # 그 자리만 불투명한 한지가 필요하다. 같은 바탕에서 잘라 써야 결이 이어진다.
    bx0, by0, bx1, by1 = a.band
    strip = img.crop((bx0, by0, bx1, by1))
    pb = out / a.band_name
    strip.save(pb)
    print(f'{pb}  {strip.size}')


if __name__ == '__main__':
    main()
