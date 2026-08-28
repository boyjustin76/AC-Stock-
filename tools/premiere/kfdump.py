#!/usr/bin/env python3
"""저장된 .prproj 의 <Keyframes> 평문을 파싱한다.

프리미어 API 에는 `getInterpolationTypeAtKey` 가 **없다** (setter 만 있다).
보간 타입을 확인할 방법은 파일을 읽는 것뿐이라 이 도구가 필요하다 (§3-5).

평문 형식 (실측):
    스칼라  틱,값,보간,0,0,베지어X,베지어Y,베지어Z;            8필드
    2D     틱,x:y,보간,0,0,b,b,b,보간2,4,0,0,b,b;            14필드
    불리언  틱,true,4,0,0,0,0,0.3333;                        8필드
  * 값이 여러 차원이면 `:` 로 이어진다.
  * 필드 2가 보간 타입. 2D 는 8번째 필드에 둘째 차원의 보간이 또 있다.

    python tools/premiere/kfdump.py <파일.prproj>
    python tools/premiere/kfdump.py <파일.prproj> --value 10       # 값으로 블록 찾기
    python tools/premiere/kfdump.py <파일.prproj> --near 914456685542400
"""
import argparse
import gzip
import re
import sys

TICKS_PER_SEC = 254_016_000_000
FRAME_2997 = 8_475_667_200      # 틱/프레임 @29.97 드롭프레임
FRAME_30 = 8_467_200_000        # 틱/프레임 @30.0

# setInterpolationTypeAtKey 의 API 상수 → 파일에 박히는 코드는 **0~7 그대로 1:1** 이다
# (m3_interp 실험에서 8개를 각각 걸어 확인). 이름은 확인된 것만 단다 —
# 0·5 는 prproj_fact 14 + 프리셋 실물(motion_preset #1 은 0->5, #3 은 5,5,5,5)로 확인됐다.
INTERP_NAME = {
    0: "선형",
    5: "이즈",
}


def interp_label(code):
    try:
        return INTERP_NAME.get(int(code), "미확인")
    except (TypeError, ValueError):
        return "?"

KF_RE = re.compile(r"<Keyframes>(.*?)</Keyframes>", re.S)


def parse_block(text):
    pts = []
    for chunk in text.strip().split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        f = chunk.split(",")
        if len(f) < 3:
            continue
        try:
            ticks = int(f[0])
        except ValueError:
            continue
        pts.append({"ticks": ticks, "value": f[1], "interp": f[2],
                    "interp2": f[8] if len(f) > 8 else None, "nfields": len(f)})
    return pts


def blocks(path):
    with gzip.open(path, "rb") as fh:
        xml = fh.read().decode("utf-8")
    return [parse_block(b) for b in KF_RE.findall(xml)]


def show(pts, idx):
    print(f"[블록 {idx}]  {len(pts)}키 · {pts[0]['nfields']}필드")
    prev = None
    for p in pts:
        gap = ""
        if prev is not None:
            d = p["ticks"] - prev
            gap = (f"  Δ{d:,} = {d / FRAME_2997:.4f}f@29.97 / {d / FRAME_30:.4f}f@30.0")
        code = p["interp"]
        nm = interp_label(code)
        extra = f" interp2={p['interp2']}" if p["interp2"] is not None else ""
        print(f"   t={p['ticks']:>16}  ({p['ticks'] / TICKS_PER_SEC:>10.4f}s)  "
              f"v={p['value']:<38} interp={code}({nm}){extra}{gap}")
        prev = p["ticks"]
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--value", help="이 값을 가진 키가 있는 블록만")
    ap.add_argument("--near", type=int, help="이 틱 근처(±10초)에 키가 있는 블록만")
    ap.add_argument("--min-keys", type=int, default=1)
    args = ap.parse_args()

    bs = blocks(args.path)
    print(f"{args.path} — <Keyframes> 블록 {len(bs)}개, 점 {sum(len(b) for b in bs)}개\n")
    shown = 0
    for i, pts in enumerate(bs):
        if len(pts) < args.min_keys:
            continue
        if args.value and not any(p["value"].startswith(args.value) for p in pts):
            continue
        if args.near and not any(abs(p["ticks"] - args.near) < 10 * TICKS_PER_SEC for p in pts):
            continue
        show(pts, i)
        shown += 1
    if not shown:
        print("(조건에 맞는 블록 없음)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
