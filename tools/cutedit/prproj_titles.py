# -*- coding: utf-8 -*-
"""프리미어 프로젝트에서 [대제목·소제목] 카드와 [챕터 범퍼] 문구를 뽑는다.

문구는 기획서에 없다. 프로젝트 안에만 있어서 .prproj 를 직접 읽는다.
(.prproj 는 gzip 으로 눌린 XML 이다. 표준 라이브러리로 연다.)

화면과 프로젝트 패널에서 확인한 구조:

  카드      대제목 폴더 [ T(대제목) · 모양 01 · 모양 01 ] + T(소제목)
            소제목은 **폴더 밖** 텍스트다. 폴더 안 텍스트가 대제목.
  챕터 범퍼  검은 화면에 흰 글씨 두 줄. 줄바꿈은 레이어 이름에 그대로 들어 있다.

레이어 이름(InstanceName)이 곧 화면 글자다 — 프리미어가 텍스트 레이어를
내용으로 이름 짓는다. 줄바꿈까지 남아서 base64(소스 텍스트)를 풀 필요가 없다.

**판정은 이름이 아니라 자리로 한다.**

  소제목  대제목 폴더 **밖**의 텍스트. 차명07 실측 y 0.139 · 비율 45 (전 회차 동일).
  범퍼    '09_필_단순 커지기' 프리셋 **두 개 밑**의 텍스트. 팀장 확인 사항이고,
          프로젝트마다 이 짝이 늘 있다. 결과적으로 비율 180 · 화면 중앙이 된다.

크기만으로 거르면 인용구·강조 숫자(비율 150~280)가 섞인다. 구조로 잡는다.

    python3 tools/cutedit/prproj_titles.py 프로젝트.prproj [...]
    python3 tools/cutedit/prproj_titles.py --json out.json 프로젝트.prproj [...]
"""
import gzip
import html
import io
import json
import re
import sys

RE_COMP = re.compile(r'<VideoFilterComponent ObjectID="(\d+)"[^>]*>')
END = "</VideoFilterComponent>"
RE_NAME = re.compile(r"<InstanceName>([^<]*)</InstanceName>")
RE_MATCH = re.compile(r"<MatchName>([^<]*)</MatchName>")
RE_REF = re.compile(r'<Param Index="\d+" ObjectRef="(\d+)"/>')
RE_POINT = re.compile(
    r'<PointComponentParam ObjectID="(\d+)"[^>]*>(.{0,900}?)</PointComponentParam>', re.S)
RE_VCP = re.compile(
    r'<VideoComponentParam ObjectID="(\d+)"[^>]*>(.{0,900}?)</VideoComponentParam>', re.S)
RE_XY = re.compile(r"<StartKeyframe>-?\d+,([\d.]+):([\d.]+)")
RE_V = re.compile(r"<StartKeyframe>-?\d+,([\d.]+)")

SUB_Y = (0.12, 0.16)          # 소제목 세로 자리
SUB_SCALE = (40.0, 55.0)      # 소제목 크기
GROW_FX = "커지기"             # 09_필_단순 커지기 — 범퍼 위에 늘 두 개 붙는다
CARD_GROUP = "대제목"


def read_proj(path):
    with open(path, "rb") as fh:
        head = fh.read(2)
    if head == b"\x1f\x8b":
        return gzip.open(path, "rb").read().decode("utf-8", "replace")
    return io.open(path, encoding="utf-8", errors="replace").read()


def _params(xml):
    pos, scale = {}, {}
    for m in RE_POINT.finditer(xml):
        if "<Name>위치</Name>" in m.group(2):
            xy = RE_XY.search(m.group(2))
            if xy:
                pos[int(m.group(1))] = (float(xy.group(1)), float(xy.group(2)))
    for m in RE_VCP.finditer(xml):
        if "<Name>비율 조정</Name>" in m.group(2):
            v = RE_V.search(m.group(2))
            if v:
                scale[int(m.group(1))] = float(v.group(1))
    return pos, scale


def layers(xml):
    """텍스트 레이어를 문서 순서대로 — (글자, x, y, 비율). 그룹은 이름만."""
    pos, scale = _params(xml)
    out = []
    for m in RE_COMP.finditer(xml):
        end = xml.find(END, m.end())
        blob = xml[m.end():end]
        mt = RE_MATCH.search(blob)
        nm = RE_NAME.search(blob)
        kind = (mt.group(1) if mt else "").replace("AE.ADBE ", "")
        text = html.unescape(nm.group(1) if nm else "").strip()
        x = y = s = None
        for r in (int(v) for v in RE_REF.findall(blob)):
            if r in pos and y is None:
                x, y = pos[r]
            if r in scale and s is None:
                s = scale[r]
        out.append({"kind": kind, "text": text, "x": x, "y": y, "scale": s})
    return out


def _lines(t):
    return [l.strip() for l in re.split(r"[\r\n]+", t) if l.strip()]


def cards(ls):
    """대제목 폴더 뒤에 오는 텍스트 두 개 = (대제목, 소제목).

    소제목은 자리(y 0.139)와 크기(45)로 한 번 더 확인한다.
    """
    out = []
    for i, l in enumerate(ls):
        if l["text"] != CARD_GROUP or "SubGroup" not in l["kind"]:
            continue
        texts = []
        for j in range(i + 1, min(i + 8, len(ls))):
            n = ls[j]
            if n["text"] == CARD_GROUP:
                break
            if n["kind"] == "Text" and n["text"]:
                texts.append(n)
                if len(texts) == 2:
                    break
            elif "SubGroup" in n["kind"]:
                break
        if not texts:
            continue
        sub = texts[1] if len(texts) > 1 else None
        ok = bool(sub) and sub["y"] is not None and SUB_Y[0] <= sub["y"] <= SUB_Y[1] \
            and sub["scale"] is not None and SUB_SCALE[0] <= sub["scale"] <= SUB_SCALE[1]
        out.append({"대제목": texts[0]["text"],
                    "소제목": sub["text"] if sub else None,
                    "자리확인": ok, "at": i})
    return out


def bumpers(ls):
    """챕터 범퍼 = '필_단순 커지기' 두 개 밑의 텍스트.

    팀장 확인: 프로젝트마다 이 프리셋 짝이 늘 있고, 그 밑 T 가 범퍼다.
    차명07 실측 —
        Geometry2 '09_필_단순 커지기'
        Geometry2 '09_필_단순 커지기'
        Text      'MACD 기본 개념 / 차트 설정 방법'   (비율 180.17)

    다만 한 범퍼 클립 안에 텍스트가 둘 들어 있는 경우가 있다(앞 범퍼에서 이어진
    레이어). 그것도 화면에 뜨는 범퍼라 놓치면 안 된다. 그래서 두 걸음으로 잡는다 —

      ① 커지기 짝 밑의 텍스트를 먼저 찾는다 (확실한 것)
      ② ①의 비율을 그 프로젝트의 '범퍼 크기'로 삼고, 같은 크기의 텍스트를 더 줍는다

    크기만으로 거르면 인용구·강조 숫자(비율 150~280)가 섞이므로 ①이 먼저다.
    """
    def _add(out, seen, j, l, how):
        if l["text"] in seen:
            return
        seen.add(l["text"])
        out.append({"문구": l["text"], "줄": _lines(l["text"]),
                    "비율": l["scale"], "y": l["y"], "at": j, "판정": how})

    out, seen = [], set()
    for j, l in enumerate(ls):
        if l["kind"] != "Text" or not l["text"]:
            continue
        if sum(1 for k in range(max(0, j - 3), j) if GROW_FX in ls[k]["text"]) >= 2:
            _add(out, seen, j, l, "커지기 짝")

    sizes = [b["비율"] for b in out if b["비율"]]
    if sizes:
        base = max(set(sizes), key=sizes.count)      # 그 편의 범퍼 크기
        for j, l in enumerate(ls):
            if l["kind"] != "Text" or not l["text"] or l["scale"] is None:
                continue
            if abs(l["scale"] - base) < 0.5:
                _add(out, seen, j, l, "같은 크기")
    out.sort(key=lambda b: b["at"])
    return out


def scan(path):
    ls = layers(read_proj(path))
    return {"proj": path, "layers": len(ls), "cards": cards(ls), "bumpers": bumpers(ls)}


def main():
    args = sys.argv[1:]
    out_json = None
    if args and args[0] == "--json":
        out_json, args = args[1], args[2:]
    res = []
    for p in args:
        try:
            r = scan(p)
        except Exception as e:
            print(f"! {p}: {e}", flush=True)
            continue
        res.append(r)
        print(f"\n== {p.split('/')[-1]}  (레이어 {r['layers']})", flush=True)
        for c in r["cards"]:
            if c["소제목"] and c["자리확인"]:
                print(f"   카드   대={c['대제목'][:34]}  소={c['소제목'][:38]}", flush=True)
        for b in r["bumpers"]:
            sc = f"{b['비율']:.0f}" if b["비율"] is not None else "?"
            print(f"   범퍼   {' | '.join(b['줄'])}   (비율 {sc})", flush=True)
    if out_json:
        io.open(out_json, "w", encoding="utf-8").write(
            json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
