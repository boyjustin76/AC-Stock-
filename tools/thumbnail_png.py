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

회차 스펙(회차 이름·안별 문구)은 여기 박지 않고 tools/photoshop/config.json
에서 읽는다 — 로컬 포토샵 경로와 같은 파일이라 두 경로의 스펙이 한 곳이다.

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

# 회차 스펙은 tools/photoshop/config.json 과 공유한다 (--config 로 바꿀 수 있다).
# group("#11 20일선의 비밀")과 variants(id·main·sub)가 회차마다 바뀌는 전부다.
# scene·tags 는 이 컨테이너 경로만 쓰는 키다 — JSX 는 모르는 키를 무시한다.
# scene 이 없는 안은 로컬 차트(seed 가 다르거나 probe 컷이 없음)라 여기서 못 만들고 건너뛴다.
CONFIG = ROOT / "tools/photoshop/config.json"

# 템플릿에서 복제 기준으로 쓰는 그룹과 그 안의 텍스트 레이어 (컨테이너 경로 고정값.
# config 의 "base"(#6)는 로컬 JSX 용이다 — 여기는 레이어 이름까지 아는 #1 을 쓴다.)
BASE_GROUP = "#1 쿠라마기"
BAKE = (
    ("이동평균선 매매법", "main", 1185, (255, 255, 0)),    # 아랫줄(노랑)
    ("3년만에 100배 수익", "sub", 1120, (255, 255, 255)),  # 윗줄(흰색)
)
FONT = ROOT / "brand/fonts/GmarketSansBold.otf"


def load_spec(path: Path) -> tuple[str, str, list[dict]]:
    """config.json 에서 (출력 이름 머리, 회차 번호, 만들 안 목록) 을 읽는다."""
    import json
    import re

    cfg = json.loads(path.read_text(encoding="utf-8"))
    m = re.fullmatch(r"#(\d+)\s+(.+)", cfg["group"].strip())
    if not m:
        sys.exit(f"config 의 group 이 '#번호 제목' 꼴이 아니다: {cfg['group']!r}")
    skipped = [v["id"] for v in cfg["variants"] if not v.get("scene")]
    if skipped:
        print(f"  scene 없는 안 {'·'.join(skipped)} 은 로컬 포토샵 경로 전용 — 건너뜀")
    variants = [v for v in cfg["variants"] if v.get("scene")]
    if not variants:
        sys.exit("scene 이 달린 안이 하나도 없다 — 컨테이너 경로에서 만들 게 없다")
    return f"차명#{m.group(1)}_{m.group(2)}", m.group(1), variants

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


def title_sig(template: Path, spec: dict, grp: str) -> str:
    """캐시 유효성 열쇠 — 문구·크기·색·템플릿·글꼴이 하나라도 바뀌면 달라진다.

    예전엔 title_*.txt 가 존재하기만 하면 재사용해서, 문구를 고쳐도
    옛 타이틀이 조용히 나왔다. 이제 meta 첫 줄의 spec 해시와 비교한다.
    """
    import hashlib

    parts = [grp, BASE_GROUP]
    for src, key, want, colour in BAKE:
        parts += [src, spec[key], str(want), str(colour)]
    for f in (template, FONT):
        st = f.stat()
        parts += [f.name, str(st.st_size), str(int(st.st_mtime))]
    return hashlib.sha1("\x1f".join(parts).encode()).hexdigest()[:12]


def titles(template: Path, cache: Path, num: str,
           variants: list[dict]) -> dict[str, list[tuple[Image.Image, int, int]]]:
    """타이틀 두 줄을 템플릿 텍스트 레이어 그대로 그린다.

    글자 위에 얹히는 획 6px·그림자는 레이어 효과(lfx2)라 우리가 그리지 않는다.
    psd-tools 가 템플릿에 들어 있는 효과 설정을 그대로 적용해 준다.

    그룹째 합성하지 않고 줄 하나씩 합성한다 — 복제한 그룹은 psd-tools 가
    크기를 0 으로 잡아서 빈 그림이 나온다.
    """
    from psd_tools import PSDImage
    from tools.psdedit import Template

    out = {}
    for spec in variants:
        vid = spec["id"]
        grp = f"#{num} {vid}"
        sig = title_sig(template, spec, grp)
        meta = cache / f"title_{vid}.txt"
        head = meta.read_text().split("\n") if meta.exists() else []
        if head and head[0] == f"spec {sig}":       # 첫 줄이 다르면(옛 형식 포함) 다시 굽는다
            rows = []
            for i, line in enumerate(l for l in head[1:] if l.strip()):
                x, y = (int(v) for v in line.split())
                rows.append((Image.open(cache / f"title_{vid}_{i}.png").convert("RGBA"), x, y))
            out[vid] = rows
            continue

        t = Template(template)
        t.clone_group(BASE_GROUP, grp)
        t.solo(grp)          # 원본 #1 은 꺼져 있어서 복제본도 꺼진 채로 나온다
        for src, key, want, colour in BAKE:
            t.bake_text(grp, src, spec[key], FONT, want, colour)
        for other in t.episode_groups():
            if other != grp:
                t.drop_group(other)
        tmp = cache / f"_{vid}.psd"
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

        rows, lines = [], [f"spec {sig}"]
        for txt in (spec["main"], spec["sub"]):     # 아랫줄 먼저 = 레이어 순서 그대로
            l = find(psd, txt)
            im = l.composite(force=True).convert("RGBA")
            i = len(rows)
            im.save(cache / f"title_{vid}_{i}.png")
            lines.append(f"{l.left} {l.top}")
            rows.append((im, l.left, l.top))
        meta.write_text("\n".join(lines))
        tmp.unlink(missing_ok=True)
        out[vid] = rows
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
    ap.add_argument("--config", type=Path, default=CONFIG,
                    help="회차 스펙 — 로컬 포토샵 경로(tools/photoshop)와 같은 파일을 읽는다")
    a = ap.parse_args()

    stem, num, variants = load_spec(a.config)
    anchors = probe_anchors(a.stills / "probe_t0.00s.png")
    print("  버튼 꼭짓점:", {k: (v[0], round(v[1])) for k, v in anchors.items()})
    ttl = titles(a.template, a.cache, num, variants)
    a.out.mkdir(parents=True, exist_ok=True)

    paper = Image.open(ASSET / "종이배경.png").convert("RGBA")
    logo = Image.open(ASSET / "로고.png").convert("RGBA")
    frame = Image.open(ASSET / "틀.png").convert("RGBA")

    for spec in variants:
        vid = spec["id"]
        chart = build_chart(a.stills / f"{spec['scene']}_t0.00s.png", anchors, spec.get("tags", []))
        cp = a.out / f"{stem}_{vid}_차트.png"
        chart.save(cp)      # 배경은 투명하게 둔다 — 종이 위에 그대로 얹을 수 있게

        # 흰 바탕 → 종이 텍스처 30% → 차트.  완성본에서 흰 부분을 재 보면 250.2 인데
        # 0.3x239(종이) + 0.7x255 = 250.3 이라 이 순서가 맞는다.
        c = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        veil = paper.copy()
        veil.putalpha(veil.getchannel("A").point(lambda v: round(v * PAPER_ALPHA)))
        paste(c, veil, PAPER_AT)
        paste(c, chart, (0, 0))
        for im, x, y in ttl[vid]:
            paste(c, im, (x, y))
        paste(c, logo, LOGO_AT)
        paste(c, frame, FRAME_AT)
        fp = a.out / f"{stem}_{vid}.png"
        c.convert("RGB").save(fp, quality=95)
        print(f"  {vid}  {cp.name} · {fp.name}")


if __name__ == "__main__":
    main()
