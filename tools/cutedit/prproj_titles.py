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

**판정은 이름이 아니라 화면 위치·크기로 한다.** 차명07 실측:

    대제목    y 0.076   비율  71.6
    소제목    y 0.139   비율  45.0     ← 전 회차 동일
    챕터 범퍼  y 0.45~0.52 비율 180.2   ← 화면 한가운데, 압도적으로 크다
    차트 주석  y 0.19~0.58 비율 85~150  ← 범퍼와 섞이기 쉬운 것들

'커지기' 프리셋으로 잡으면 차트 주석(풀백(Pull Back)·과매도·익절)이 섞인다.
비율로 걸러야 범퍼만 남는다.

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
BUMP_Y = (0.35, 0.65)         # 범퍼는 화면 한가운데
BUMP_SCALE = 150.0            # 범퍼는 이보다 크다
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
    """화면 한가운데 크게 뜨는 텍스트 = 챕터 범퍼."""
    out, seen = [], set()
    for j, l in enumerate(ls):
        if l["kind"] != "Text" or not l["text"]:
            continue
        if l["scale"] is None or l["scale"] < BUMP_SCALE:
            continue
        if l["y"] is None or not (BUMP_Y[0] <= l["y"] <= BUMP_Y[1]):
            continue
        if l["text"] in seen:
            continue
        seen.add(l["text"])
        out.append({"문구": l["text"], "줄": _lines(l["text"]),
                    "비율": l["scale"], "y": round(l["y"], 3), "at": j})
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
            print(f"   범퍼   {' | '.join(b['줄'])}   (비율 {b['비율']:.0f})", flush=True)
    if out_json:
        io.open(out_json, "w", encoding="utf-8").write(
            json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
