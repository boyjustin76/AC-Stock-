#!/usr/bin/env python3
"""롱폼 썸네일을 .png 로 뽑는다 — 차트 한 장, 완성본 한 장.

.psd 를 넘기는 방식은 접었다. 포토샵이 열다가 튕기는 위험이 있고, 사람이 보고
따라 만들 수 있으면 그림 파일이면 충분하다.

**태그(매수·익절)는 직접 그리지 않는다.** 회사 템플릿 안에 있는 진짜 버튼
픽셀을 그대로 뜯어 쓴다.  코드로 비슷하게 그리면 모서리 반지름·화살촉 각도·
자간이 미묘하게 달라져서 한눈에 티가 난다.

  매수  #1 쿠라마기 / 매수 버튼(좌우)   189x90, 빨강 #FF0000, 효과 없음, 오른쪽 화살표
  익절  #5 탐드마크 / 그룹 3 / 익절     185x90, 초록 #00FF24 (Color Overlay), 왼쪽 화살표
        → 좌우 반전해서 오른쪽을 가리키게 하고 흰 '익절' 글자를 다시 얹었다

버튼을 놓을 자리는 짐작하지 않는다.  씬 파일의 probe 컷이 차트에 없는 색
(자홍·청록)으로 같은 (봉, 가격) 에 태그를 찍어 두었으니, 그 색만 찾으면
화면 좌표가 나온다.

    python3 tools/thumbnail_png.py --template '차트명가(롱)_하이라이트 - 복사본.psd'
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

W, H = 1920, 1080
ASSET = ROOT / "brand/thumbnail"
GAP = 14          # 태그 꼭짓점과 캔들 사이 여백

# 템플릿에서 잰 배치 (문서 좌표)
PAPER_AT = (4, -84)
PAPER_ALPHA = 0.30   # 템플릿의 '종이 배경' 은 불투명도 77/255
LOGO_AT = (49, 977)
FRAME_AT = (-27, -27)

VERSIONS = {
    "v1": {
        "scene": "thumb-a",
        "sub": "손익비 1:5 만드는",
        "main": "20일선 매매법",
        "tags": ["매수", "익절"],
    },
    "v2": {
        "scene": "thumb-b",
        "sub": "여기서 사면 물립니다",
        "main": "20일선의 두 얼굴",
        "tags": ["매수"],
    },
}

PROBE = {"매수": (255, 0, 255), "익절": (0, 255, 255)}


def probe_anchors(png: Path) -> dict[str, tuple[int, float]]:
    """probe 컷에서 태그 꼭짓점 좌표를 읽는다.

    자홍·청록은 차트 어디에도 없는 색이라 그 색만 골라내면 된다.
    태그는 오른쪽을 가리키므로 꼭짓점은 그 덩어리의 오른쪽 끝, 세로 한가운데다.
    """
    a = np.array(Image.open(png).convert("RGB")).astype(int)
    out = {}
    for name, rgb in PROBE.items():
        m = np.abs(a - np.array(rgb)).sum(axis=2) < 40
        if not m.any():
            continue
        ys, xs = np.where(m)
        out[name] = (int(xs.max()), (int(ys.min()) + int(ys.max())) / 2)
    return out


def tip_of(btn: Image.Image) -> tuple[int, int]:
    """버튼 그림 안에서 화살촉 꼭짓점이 어디인지."""
    al = np.array(btn)[..., 3]
    cols = np.where((al > 128).any(axis=0))[0]
    c = int(cols.max())
    rows = np.where(al[:, c] > 128)[0]
    return c, int(round((rows.min() + rows.max()) / 2))


def build_chart(still: Path, anchors: dict, tags: list[str]) -> Image.Image:
    chart = Image.open(still).convert("RGBA")
    for name in tags:
        if name not in anchors:
            continue
        btn = Image.open(ASSET / f"btn_{name}.png").convert("RGBA")
        tx, ty = tip_of(btn)
        ax, ay = anchors[name]
        chart.alpha_composite(btn, (round(ax - GAP - tx), round(ay - ty)))
    return chart


def titles(template: Path, cache: Path) -> dict[str, list[tuple[Image.Image, int, int]]]:
    """타이틀 두 줄을 템플릿 텍스트 레이어 그대로 그린다.

    글자 위에 얹히는 획 6px·그림자는 레이어 효과(lfx2)라 우리가 그리지 않는다.
    psd-tools 가 템플릿에 들어 있는 효과 설정을 그대로 적용해 준다.

    그룹째 합성하지 않고 줄 하나씩 합성한다 — 복제한 그룹은 psd-tools 가
    크기를 0 으로 잡아서 빈 그림이 나온다.
    """
    from psd_tools import PSDImage
    from tools.psdedit import Template

    out = {}
    for tag, spec in VERSIONS.items():
        meta = cache / f"title_{tag}.txt"
        if meta.exists():
            rows = []
            for i, line in enumerate(meta.read_text().split("\n")):
                if not line.strip():
                    continue
                x, y = (int(v) for v in line.split())
                rows.append((Image.open(cache / f"title_{tag}_{i}.png").convert("RGBA"), x, y))
            out[tag] = rows
            continue

        t = Template(template)
        grp = f"#11 {tag}"
        t.clone_group("#1 쿠라마기", grp)
        t.solo(grp)          # 원본 #1 은 꺼져 있어서 복제본도 꺼진 채로 나온다
        for src, txt, want, colour in (
            ("이동평균선 매매법", spec["main"], 1185, (255, 255, 0)),
            ("3년만에 100배 수익", spec["sub"], 1120, (255, 255, 255)),
        ):
            t.bake_text(grp, src, txt, ROOT / "brand/fonts/GmarketSansBold.otf", want, colour)
        for other in t.episode_groups():
            if other != grp:
                t.drop_group(other)
        tmp = cache / f"_{tag}.psd"
        cache.mkdir(parents=True, exist_ok=True)
        t.save(tmp)

        psd = PSDImage.open(str(tmp))

        def find(g, name):
            for l in g:
                if l.name == name:
                    return l
                if l.is_group():
                    r = find(l, name)
                    if r is not None:
                        return r

        rows, lines = [], []
        for txt in (spec["main"], spec["sub"]):     # 아랫줄 먼저 = 레이어 순서 그대로
            l = find(psd, txt)
            im = l.composite(force=True).convert("RGBA")
            i = len(rows)
            im.save(cache / f"title_{tag}_{i}.png")
            lines.append(f"{l.left} {l.top}")
            rows.append((im, l.left, l.top))
        meta.write_text("\n".join(lines))
        tmp.unlink(missing_ok=True)
        out[tag] = rows
    return out


def paste(canvas: Image.Image, im: Image.Image, at: tuple[int, int]) -> None:
    x, y = at
    if x < 0 or y < 0:
        im = im.crop((max(0, -x), max(0, -y), im.width, im.height))
        x, y = max(0, x), max(0, y)
    canvas.alpha_composite(im, (x, y))


def main() -> None:
    ap = argparse.ArgumentParser(description="롱폼 썸네일 → .png")
    ap.add_argument("--template", type=Path, required=True, help="차트명가(롱)_하이라이트 - 복사본.psd")
    ap.add_argument("--stills", type=Path, required=True, help="렌더된 차트 스틸 폴더")
    ap.add_argument("--out", type=Path, default=ROOT / "out/thumbnail")
    ap.add_argument("--cache", type=Path, default=ROOT / "out/thumbnail/.cache")
    a = ap.parse_args()

    anchors = probe_anchors(a.stills / "probe_t0.00s.png")
    print("  버튼 꼭짓점:", {k: (v[0], round(v[1])) for k, v in anchors.items()})
    ttl = titles(a.template, a.cache)
    a.out.mkdir(parents=True, exist_ok=True)

    paper = Image.open(ASSET / "종이배경.png").convert("RGBA")
    logo = Image.open(ASSET / "로고.png").convert("RGBA")
    frame = Image.open(ASSET / "틀.png").convert("RGBA")

    for tag, spec in VERSIONS.items():
        chart = build_chart(a.stills / f"{spec['scene']}_t0.00s.png", anchors, spec["tags"])
        cp = a.out / f"차명#11_20일선의 비밀_{tag}_차트.png"
        chart.save(cp)      # 배경은 투명하게 둔다 — 종이 위에 그대로 얹을 수 있게

        # 흰 바탕 → 종이 텍스처 30% → 차트.  완성본에서 흰 부분을 재 보면 250.2 인데
        # 0.3x239(종이) + 0.7x255 = 250.3 이라 이 순서가 맞는다.
        c = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        veil = paper.copy()
        veil.putalpha(veil.getchannel("A").point(lambda v: round(v * PAPER_ALPHA)))
        paste(c, veil, PAPER_AT)
        paste(c, chart, (0, 0))
        for im, x, y in ttl[tag]:
            paste(c, im, (x, y))
        paste(c, logo, LOGO_AT)
        paste(c, frame, FRAME_AT)
        fp = a.out / f"차명#11_20일선의 비밀_{tag}.png"
        c.convert("RGB").save(fp, quality=95)
        print(f"  {tag}  {cp.name} · {fp.name}")


if __name__ == "__main__":
    main()
