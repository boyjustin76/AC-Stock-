#!/usr/bin/env python3
"""롱폼 썸네일을 템플릿 규격대로 조립해 .psd 로 쓴다.

템플릿: 04_영상_에셋_디자인 작업물 / 01_영상(유튜브) 관련 / 05_썸네일 /
        06_차트명가_주 1회 / 차트명가(롱)_하이라이트 - 복사본.psd

그 템플릿을 psd-tools 로 뜯어 확인한 규격을 그대로 쓴다.

  캔버스   1920x1080
  틀       핑크 #EF2767 테두리 (고정 그룹)
  배경     종이 텍스처 (거의 흰색)
  타이틀   두 줄. GmarketSansBold, 자간 -40, 검정 외곽선
             윗줄(서브)  #FFFFFF  y≈84~111   강조할 때 #FF0000
             아랫줄(메인) #FFFF00  y≈229~268
  로고     좌하단 (49, 977)
  차트     매매법의 핵심을 한 장으로. 우리 렌더러가 그린다.
  인물     [선택] 회차에 유명 인물이 있을 때만

    python3 tools/thumbnail.py --help
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.psdwrite import Layer, write_psd  # noqa: E402

W, H = 1920, 1080
FONT = ROOT / "brand/fonts/GmarketSansBold.otf"

# 템플릿에서 읽은 값
YELLOW = "#FFFF00"      # 메인 타이틀
WHITE = "#FFFFFF"       # 서브 타이틀
RED = "#FF0000"         # 서브 타이틀 강조 (차07·차08·차10 이 이걸 썼다)
PINK = "#EF2767"        # 틀
TRACKING = -0.040       # 자간 -40/1000 em


# 완성본 11장에서 잰 타이틀 레이어 폭.
#   윗줄  979~1189, 중앙값 1120   ← 거의 일정하다
#   아랫줄 981~1476, 중앙값 1185
# 글자 수가 달라도 폭을 맞추는 것이 이 채널의 규칙이라, 폰트 크기를 폭에서 역산한다.
SUB_WIDTH = 1120
MAIN_WIDTH = 1185


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT), size)


def fit_size(text: str, target_width: int, lo: int = 40, hi: int = 400) -> int:
    """글자를 target_width 에 맞추는 폰트 크기를 찾는다."""
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _text_width(probe, text, _load_font(mid), TRACKING) <= target_width:
            lo = mid
        else:
            hi = mid - 1
    return lo


def _text_width(draw, text: str, font, tracking: float) -> int:
    gap = round(font.size * tracking)
    w = sum(draw.textlength(c, font=font) for c in text)
    return round(w + gap * (len(text) - 1))


def draw_title(text: str, size: int, fill: str, stroke: int = 13,
               shadow: int = 7) -> Image.Image:
    """자간과 검정 외곽선을 넣어 한 줄을 그린다. 여백은 알파로 둔다."""
    font = _load_font(size)
    pad = stroke + shadow + 18
    probe = Image.new("RGBA", (10, 10))
    d0 = ImageDraw.Draw(probe)
    w = _text_width(d0, text, font, TRACKING)
    img = Image.new("RGBA", (w + pad * 2, round(size * 1.75) + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    gap = round(size * TRACKING)

    def run(dx, dy, colour, sw):
        x = pad + dx
        for ch in text:
            d.text((x, pad + dy), ch, font=font, fill=colour,
                   stroke_width=sw, stroke_fill=colour if sw else None)
            x += d.textlength(ch, font=font) + gap

    if shadow:
        run(shadow, shadow, (0, 0, 0, 110), stroke)     # 그림자
    run(0, 0, (0, 0, 0, 255), stroke)                   # 검정 외곽선
    run(0, 0, fill, 0)                                  # 글자
    return img.crop(img.getbbox())


def paper_background(asset_dir: Path) -> Image.Image:
    p = asset_dir / "종이 배경.png"
    bg = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    if p.exists():
        tex = Image.open(p).convert("RGBA")
        # 템플릿에서 4,-84 에 놓여 있다
        bg.alpha_composite(tex, (0, 0) if tex.size == (W, H) else (4, 0))
    return bg.crop((0, 0, W, H))


def make_frame(thickness: int = 26) -> Image.Image:
    """핑크 테두리. 완성본 11장에서 잰 값 — 두께 26px, 모서리는 각졌다.

    템플릿의 '틀' 은 도형 레이어라 그대로 뽑으면 안쪽 흰 면까지 딸려 온다.
    테두리만 필요하므로 실측값으로 다시 그린다.
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W - 1, H - 1), outline=PINK, width=thickness)
    return img


def load_logo(asset_dir: Path) -> Image.Image | None:
    p = asset_dir / "고정_차트명가_로고(최종+핑크).png"
    return Image.open(p).convert("RGBA") if p.exists() else None


def build(name: str, chart_png: Path, sub: str, main: str, out_dir: Path,
          sub_color: str = WHITE, sub_size: int = 0, main_size: int = 0,
          person_png: Path | None = None, asset_dir: Path | None = None) -> dict:
    asset_dir = asset_dir or (ROOT / "brand/thumbnail")
    layers: list[Layer] = []

    layers.append(Layer("배경(종이)", paper_background(asset_dir), 0, 0))

    chart = Image.open(chart_png).convert("RGBA")
    if chart.size != (W, H):
        chart = chart.resize((W, H), Image.LANCZOS)
    layers.append(Layer("차트", chart, 0, 0))

    if person_png and Path(person_png).exists():
        pi = Image.open(person_png).convert("RGBA")
        layers.append(Layer("인물", pi, W - pi.width - 40, H - pi.height))

    ss = sub_size or fit_size(sub, SUB_WIDTH)
    ms = main_size or fit_size(main, MAIN_WIDTH)
    sub_img = draw_title(sub, ss, sub_color)
    main_img = draw_title(main, ms, YELLOW)
    # 템플릿의 두 줄 위치를 그대로 따른다 (윗줄 y≈84, 아랫줄 y≈260)
    layers.append(Layer("타이틀_윗줄", sub_img, 74, 60))
    layers.append(Layer("타이틀_아랫줄", main_img, 74, 60 + sub_img.height - 22))

    logo = load_logo(asset_dir)
    if logo is not None:
        layers.append(Layer("로고", logo, 49, 977))
    layers.append(Layer("틀", make_frame(), 0, 0))

    out_dir.mkdir(parents=True, exist_ok=True)
    psd = write_psd(out_dir / f"{name}.psd", W, H, layers)

    flat = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    for L in layers:
        flat.alpha_composite(L.image.convert("RGBA"), (L.left, L.top))
    png = out_dir / f"{name}.png"
    flat.convert("RGB").save(png, quality=95)
    return {"psd": psd, "png": png, "layers": [L.name for L in layers],
            "kb": psd.stat().st_size // 1024, "sub_size": ss, "main_size": ms,
            "sub_w": sub_img.width, "main_w": main_img.width}


def main():
    ap = argparse.ArgumentParser(description="롱폼 썸네일 조립 → .psd")
    ap.add_argument("name")
    ap.add_argument("--chart", required=True, type=Path)
    ap.add_argument("--sub", required=True, help="윗줄 (후킹 문구)")
    ap.add_argument("--main", required=True, help="아랫줄 (매매법 이름)")
    ap.add_argument("--sub-color", default=WHITE, choices=[WHITE, RED])
    ap.add_argument("--sub-size", type=int, default=0, help="0 이면 폭 1120 에 맞춰 자동")
    ap.add_argument("--main-size", type=int, default=0, help="0 이면 폭 1185 에 맞춰 자동")
    ap.add_argument("--person", type=Path)
    ap.add_argument("--assets", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "out/thumbnail")
    a = ap.parse_args()
    r = build(a.name, a.chart, a.sub, a.main, a.out, a.sub_color,
              a.sub_size, a.main_size, a.person, a.assets)
    print(f"\n  {r['psd']}  ({r['kb']} KB)")
    print(f"  {r['png']}")
    print(f"  레이어 {len(r['layers'])}개: {' / '.join(r['layers'])}")
    print(f"  윗줄 {r['sub_size']}px (폭 {r['sub_w']}) · "
          f"아랫줄 {r['main_size']}px (폭 {r['main_w']})\n")


if __name__ == "__main__":
    main()
