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
    from PIL import Image
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

    # ── 로고 ────────────────────────────────────────────────────
    # 사용자가 준 원본을 **그대로** 쓴다 (2026-09-16: "기준이 아니라 그냥 그걸 써").
    # 색도 안 바꾼다. 하는 일은 캔버스의 빈 투명 여백을 잘라내는 것뿐이다 —
    # 원본은 1280x720 판에 로고가 742x185 로 얹혀 있어서, 그대로 놓으면 자리를 못 잡는다.
    for src_name, out_name in (('차트명가_로고(최종+핑크).png', '로고_가로.png'),
                               ('차트명가_로고(투명).png', '로고_심볼.png')):
        sp = out / src_name
        if not sp.exists():
            print(f'  (없음, 건너뜀) {src_name}')
            continue
        lg = Image.open(sp).convert('RGBA')
        lg = lg.crop(lg.getbbox())
        lg.save(out / out_name)
        print(f'  {out_name}  {lg.size}  (원본 색 그대로 · 빈 여백만 제거)')

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
