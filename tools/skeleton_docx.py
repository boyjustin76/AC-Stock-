# -*- coding: utf-8 -*-
"""뼈대 .md → **회사 기본폼 .docx** (`[차XX_기본폼]_롱폼 기획서+스크립트(차트명가).docx`).

    python tools/skeleton_docx.py log/차13_..._뼈대_회사양식.md -o "…/[차13_…].docx"

## 왜 회사 양식으로 뽑나

팀장이 뼈대를 검사할 때 보는 것은 **회사 기본폼**이다(이정찬 2026-09-21).
우리끼리 쓰는 `.md` 뼈대는 조각 출처·분량을 적기엔 좋지만 그 꼴로는 검사를 받을 수 없다.
그래서 **같은 내용을 두 꼴로** 낸다 — 작업용 `.md` 와 보고용 `.docx`.

## 회사 기본폼이 요구하는 것 — 6단계 퍼널

`[참고용 가이드]롱폼 기획서+스크립트 기획서.docx` 를 그대로 옮기면 이렇다.

    타이틀(포장지) : 대중이 검색할 메인 키워드 — 사람을 끌어오는 미끼
    메인(진짜 제품) : 들어온 사람에게 최종적으로 어필할 회사의 핵심 DB/제품

    1. 후킹      타이틀이 필요한 이유          (5초 안에 끄지 않게)
    2. 소개      타이틀의 쉬운 개념 설명
    3. 본론#1    타이틀의 활용법                (기대하고 들어온 정보)
    4. 문제 제시 **타이틀의 치명적 한계**        ← 제품이 등장할 무대
    5. 본론#2    **제품 공개**                  ← 진짜 목적
    6. 아웃트로  행동 유도 (CTA)

**4·5 가 이 양식의 핵심이다.** 기본폼 표는 그 둘을 `4+5. 본론#2(메인)` 한 칸으로 묶어 두었으므로
이 도구도 한 칸에 함께 적는다.

## 틀을 그대로 쓴다

원본 `.docx` 를 열어 `word/document.xml` 의 **글자만** 갈아 끼운다.
서식(styles·theme·settings)·고정 아웃트로 문구·표 테두리는 손대지 않으므로 회사 문서와 같은 꼴이 나온다.
`tools/md_to_script_docx.py` 가 촬영용 대본에 쓰는 것과 같은 수법이다.

## 들어가는 .md 의 꼴

    타이틀: 테스타 칼만 이동평균선
    메인: 칼만 + HH/LL + ATR 세팅

    ## 1. 후킹(현황&썰)
    본문. 빈 줄 없이 여러 줄을 쓰면 칸 안에서 줄이 바뀐다.

    ## 2. 소개
    ...

    ## 본문 1
    제목: 이평선을 여러 개 켜 두고도 수익이 쌓이지 않는 이유
    (빈 줄로 나눈 문단들이 줄글 란에 들어간다)

    ## 매매법 정리
    매매법 이름 : ...
    (실제)지표 및 설정값 : ...

`##` 제목은 기본폼 표의 첫 칸 글자와 **앞 숫자로** 맞춘다(`1.`·`2.`·`3.`·`4`·`6.`).

**표 칸은 한 줄로 짧게, 대본은 `## 본문 N` 으로.** 회사 문서 09~12 가 그렇게 쓴다.
`## 본문 N` 의 첫 줄 `제목:` 은 섹션 머리글 뒤에 붙는 회차 소제목이다.
"""
import argparse
import io
import os
import re
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
틀 = os.path.join(os.path.dirname(os.path.dirname(REPO)), "05_대본자료", "양식",
                  "[차XX_기본폼]_롱폼 기획서+스크립트(차트명가).docx")

# `<w:t[^>]*>` 로 쓰면 **`<w:tcPr>`·`<w:tcW>` 까지 잡는다** — `<w:t` 뒤에 아무 글자나 와도 되기 때문이다.
# 표 첫 칸의 라벨이 XML 조각으로 나와 6단계 칸이 통째로 안 채워졌다(2026-09-21).
# 태그 이름이 거기서 끝나거나 공백이 와야 한다고 못박는다.
WT = r"<w:t(?:\s[^>]*)?>(.*?)</w:t>"

정리칸 = ["매매법 이름", "해당 매매법의 특징", "(실제)지표 및 설정값",
          "매수(진입) 조건", "매도(청산) 조건", "필수 주의사항(리스크 관리)"]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


굵게 = "<w:b/><w:bCs/>"
# 회사 문서 차명09~12 는 줄글 란의 섹션 머리글을 **초록 강조**로 칠한다(차명12 에 34곳).
# 기본폼에는 없다 — 09 부터 덧칠한 것이다. 요소 순서는 스키마가 정한다: b · bCs 가 highlight 보다 앞.
머리글서식 = 굵게 + '<w:highlight w:val="green"/>'


def runs(text, 바탕=""):
    """여러 줄 → <w:r> 묶음. 줄바꿈은 <w:br/>, `**굵게**` 는 <w:b/> 로 살린다.

    `바탕` 은 모든 run 에 깔 서식(<w:rPr> 속)이다. 머리글처럼 원래 굵던 문단을 고쳐 쓸 때
    이걸 안 주면 **서식이 지워진다** — 소제목을 붙인 머리글이 보통 글씨로 나왔다(2026-09-22).

    별표를 그대로 두면 워드 문서에 `**방향**` 이 글자로 찍힌다 — 회사 문서는 마크다운이 아니다.
    """
    out = []
    for i, line in enumerate(text.split("\n")):
        if i:
            out.append("<w:r><w:br/></w:r>")
        for j, 조각 in enumerate(re.split(r"\*\*(.+?)\*\*", line)):
            if not 조각:
                continue
            속 = 바탕
            if j % 2 and 굵게 not in 속:
                속 = 굵게 + 속
            rpr = "<w:rPr>%s</w:rPr>" % 속 if 속 else ""
            out.append('<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, esc(조각)))
    return "".join(out)


def 문단채우기(p, text, 바탕=""):
    """문단 하나의 글자를 갈아 끼운다. <w:pPr>(서식)는 남긴다."""
    m = re.match(r"(<w:p\b[^>]*?)(/>|>)", p)
    if not m:
        return p
    여는태그 = m.group(1) + ">"
    속 = "" if m.group(2) == "/>" else p[m.end():p.rindex("</w:p>")]
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", 속, re.S)
    return 여는태그 + (ppr.group(0) if ppr else "") + runs(text, 바탕) + "</w:p>"


def 칸채우기(tc, text):
    """표 칸 하나를 갈아 끼운다. <w:tcPr>(테두리·여백)는 남긴다."""
    m = re.search(r"</w:tcPr>", tc)
    머리 = tc[:m.end()] if m else "<w:tc>"
    문단들 = re.findall(r"<w:p\b(?:(?!</w:p>).)*</w:p>|<w:p\b[^>]*/>", tc, re.S)
    본 = 문단들[0] if 문단들 else '<w:p/>'
    return 머리 + 문단채우기(본, text) + "</w:tc>"


def 읽기(path):
    """.md → {'타이틀':…, '메인':…, '구간':{'1':글…}, '본문':{'1':[문단…]}, '정리':{…}}"""
    글 = io.open(path, encoding="utf-8").read()
    out = {"타이틀": "", "메인": "", "구간": {}, "본문": {}, "소제목": {}, "정리": {}}
    이름, 쌓기 = None, []

    def 닫기():
        if 이름 is None:
            return
        몸 = "\n".join(쌓기).strip()
        if 이름 == "매매법 정리":
            for line in 몸.split("\n"):
                for k in 정리칸:
                    if line.strip().startswith(k):
                        out["정리"][k] = line.split(":", 1)[1].strip() if ":" in line else ""
        elif 이름.startswith("본문"):
            # 줄글 란. 빈 줄로 문단을 나눈다.
            # 첫 줄이 `제목: …` 이면 섹션 머리글 뒤에 덧붙일 **회차 소제목**이다.
            # 회사 문서 차명12 가 그렇게 쓴다 — `1. 후킹 (Hook) : 타이틀이 필요한 이유:크로스 매매가…`
            n = re.search(r"(\d+)", 이름)
            if not n:
                return
            문단들 = [p.strip() for p in re.split(r"\n\s*\n", 몸) if p.strip()]
            if 문단들 and 문단들[0].startswith("제목:"):
                out["소제목"][n.group(1)] = 문단들.pop(0).split(":", 1)[1].strip()
            if 문단들:
                out["본문"][n.group(1)] = 문단들
        else:
            n = re.match(r"\s*(\d+)", 이름)
            if n:
                out["구간"][n.group(1)] = 몸

    for line in 글.split("\n"):
        if line.startswith("## "):
            닫기()
            이름, 쌓기 = line[3:].strip(), []
            continue
        if 이름 is None:
            for k in ("타이틀", "메인"):
                if line.startswith(k + ":"):
                    out[k] = line.split(":", 1)[1].strip()
            continue
        쌓기.append(line)
    닫기()
    return out


def 만들기(자료, 틀경로, 낼곳):
    src = zipfile.ZipFile(틀경로)
    xml = src.read("word/document.xml").decode("utf-8")
    앞, 몸 = xml.split("<w:body>", 1)

    # ① 타이틀 / 메인 — 맨 앞 두 문단
    def 머리글(m):
        p = m.group(0)
        t = "".join(re.findall(WT, p, re.S))
        for k in ("타이틀", "메인"):
            if t.strip().startswith(k + ":") and 자료[k]:
                return 문단채우기(p, "%s: %s" % (k, 자료[k]))
        for k in 정리칸:                                    # ③ 매매법 정리 빈칸
            if t.strip().startswith(k) and 자료["정리"].get(k):
                return 문단채우기(p, "%s : %s" % (k, 자료["정리"][k]))
        return p

    # ② 6단계 표 — 첫 칸의 앞 숫자로 맞춘다
    def 표(m):
        tbl = m.group(0)

        def 줄(mr):
            tr = mr.group(0)
            칸들 = re.findall(r"<w:tc>.*?</w:tc>", tr, re.S)
            if len(칸들) < 2:
                return tr
            라벨 = "".join(re.findall(WT, 칸들[0], re.S)).strip()
            n = re.match(r"(\d+)", 라벨)
            if not n or n.group(1) not in 자료["구간"]:
                return tr
            새칸 = 칸채우기(칸들[1], 자료["구간"][n.group(1)])
            return tr.replace(칸들[1], 새칸, 1)

        return re.sub(r"<w:tr\b.*?</w:tr>", 줄, tbl, flags=re.S)

    # ④ 줄글 란 — 섹션 머리글(`1. 후킹 (Hook) : …`) **뒤에** 대본 문단을 끼워 넣는다.
    #
    # 표와 줄글 란은 하는 일이 다르다(회사 문서 실측, 2026-09-21).
    #   표    = 빈칸 채우기 결과. **한 줄 요약** — 차10 38~81자 · 차11 11~48자 · 차12 0~65자.
    #   줄글  = 실제 대본 — 차12 는 후킹 483 · 소개 477 · 본론#1 247 · 문제제시 743 ·
    #           본론#2 1,612 · 아웃트로 281자.
    # **표에 대본을 통째로 넣으면 양식을 잘못 쓴 것이다.**
    # (차명03 은 표 칸이 94~221자였으나 **09 부터 꼴이 바뀌었다** — 09 이후만 본다. 이정찬 지정.)
    def 본문붙이기(p):
        t = "".join(re.findall(WT, p, re.S)).strip()
        n = re.match(r"(\d+)", t)
        if not n:
            return p
        키 = n.group(1)
        if 키 not in 자료["본문"] and 키 not in 자료["소제목"]:
            return p
        # 소제목은 붙여 쓴다 — 차명12 가 `타이틀이 필요한 이유:크로스 매매가…` 로 썼다.
        머리 = 문단채우기(p, t + ":" + 자료["소제목"][키], 머리글서식) if 키 in 자료["소제목"] else p
        # 대본 문단은 **서식 없는 보통 문단**으로 찍는다. 머리글 문단을 본뜨면 문단 기호의 굵게까지 따라온다.
        return 머리 + "".join("<w:p>%s</w:p>" % runs(문단) for 문단 in 자료["본문"].get(키, []))

    # **맨 위 층 덩이만** 훑는다. 한 번에 표와 문단을 갈라 다뤄야 한다 —
    # 문단만 따로 훑으면 표 **안**의 `1. 후킹(현황&썰)` 칸까지 머리글로 잡아
    # 거기에 대본이 끼어들어 표가 깨진다.
    덩이 = re.compile(r"<w:tbl>.*?</w:tbl>|<w:p\b(?:(?!</w:p>).)*</w:p>|<w:p\b[^>]*/>", re.S)
    표쓴적 = []

    def 갈라서(m):
        blk = m.group(0)
        if blk.startswith("<w:tbl>"):
            if 표쓴적:                       # 6단계 표는 맨 앞 하나뿐이다
                return blk
            표쓴적.append(True)
            return 표(m)
        return 본문붙이기(머리글(m))

    몸 = 덩이.sub(갈라서, 몸)

    if os.path.dirname(낼곳):
        try:
            os.makedirs(os.path.dirname(낼곳))
        except OSError:
            pass
    tmp = 낼곳 + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for item in src.infolist():
            if item.filename == "word/document.xml":
                out.writestr(item, (앞 + "<w:body>" + 몸).encode("utf-8"))
            else:
                out.writestr(item, src.read(item.filename))
    shutil.move(tmp, 낼곳)
    return 낼곳


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="뼈대 .md 를 회사 기본폼 .docx 로 뽑는다")
    ap.add_argument("md")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--틀", default=틀)
    a = ap.parse_args()

    자료 = 읽기(a.md)
    if not os.path.exists(a.틀):
        raise SystemExit("틀이 없다: %s\n  회사 드라이브의 [차XX_기본폼] 을 그 자리에 복사해 둔다." % a.틀)
    p = 만들기(자료, a.틀, a.out)
    print("냈다: %s (%,d바이트)".replace("%,d", "%d") % (p, os.path.getsize(p)))
    print("  타이틀 %s · 메인 %s" % (자료["타이틀"] or "(빈칸)", 자료["메인"] or "(빈칸)"))
    print("  채운 구간 %s · 매매법 정리 %d/6"
          % (",".join(sorted(자료["구간"])), len(자료["정리"])))
