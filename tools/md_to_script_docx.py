# -*- coding: utf-8 -*-
"""초안 `.md` 를 **촬영용 스크립트 `.docx`** 로 바꾼다 — 더원트레이더 양식 그대로.

    python md_to_script_docx.py <초안.md> <양식.docx> <나올 파일.docx>

양식(.docx)을 **틀로 쓴다.** 글꼴·문단 스타일·머리글 테두리·여백이 들어 있는
`styles.xml`·`theme1.xml`·`settings.xml` 을 그대로 물려받고, 본문(`document.xml`)과
머리글 글귀, 문서 속성만 새로 쓴다. 그래서 서식이 원본과 어긋나지 않는다.

**빼는 것** — 내가 붙인 메모(`>` 로 시작하는 줄)와 `사전 질문지` 구역.
팀장 보고용 깔끔한 판이라 작업 메모는 넣지 않는다 (이정찬 2026-09-21).

**남기는 것** — `[… · 읽지 않음]` 지시문. 원본 양식에도 노랑 형광으로 들어 있다.
빼려면 `--no-지시문`.

양식에서 읽어 온 서식 값 (L07 실측, 2026-09-21)
  회차 줄    9.5pt 굵게 · 색 2E74B5      제목      24pt 굵게 · 색 0B2545
  부제       12pt 색 5A626C · 아래 실선   구간 제목  스타일 `1` · 맑은 고딕
  지시문     10pt · 노랑 형광 · 줄간격 1.2   머리글    8.5pt 굵게 · 색 5A626C
"""
import io
import os
import re
import shutil
import sys
import zipfile

# 낭독 속도 — 우리 실측 (차12 뼈대 §1)
SLOW, FAST = 5.4, 7.1          # 자/초
CHART_EXTRA = 2                # 차트 얹으면 늘어나는 분 (양식 원본의 8-10 → 10-12 에서)

LANG = '<w:lang w:eastAsia="ko-KR"/>'


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def runs(text):
    """`**굵게**` 를 굵은 run 으로 나눈다."""
    out = []
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if not part:
            continue
        b = "<w:b/>" if i % 2 else ""
        out.append("<w:r><w:rPr>%s%s</w:rPr><w:t xml:space=\"preserve\">%s</w:t></w:r>"
                   % (b, LANG, esc(part)))
    return "".join(out)


def para(text, ppr="", rpr=""):
    body = []
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if not part:
            continue
        b = "<w:b/>" if i % 2 else ""
        body.append("<w:r><w:rPr>%s%s%s</w:rPr><w:t xml:space=\"preserve\">%s</w:t></w:r>"
                    % (b, rpr, LANG, esc(part)))
    return "<w:p><w:pPr>%s<w:rPr>%s%s</w:rPr></w:pPr>%s</w:p>" % (ppr, rpr, LANG, "".join(body))


def heading(text):
    return ('<w:p><w:pPr><w:pStyle w:val="1"/><w:rPr>%s</w:rPr></w:pPr>'
            '<w:r><w:rPr><w:rFonts w:ascii="맑은 고딕" w:eastAsia="맑은 고딕" w:hAnsi="맑은 고딕"/>%s</w:rPr>'
            '<w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (LANG, LANG, esc(text)))


def direction(text):
    ppr = ('<w:keepLines/><w:spacing w:before="160" w:after="160" w:line="288" w:lineRule="auto"/>')
    rpr = '<w:sz w:val="20"/><w:highlight w:val="yellow"/>'
    return para(text, ppr, rpr)


def parse(path, keep_dir=True):
    """초안 .md → (회차, 제목, 문단 목록)"""
    raw = io.open(path, encoding="utf-8").read().split("\n")
    ep = title = ""
    out, skip = [], False
    for ln in raw:
        s = ln.rstrip()
        if s.startswith("# "):                       # 문서 제목 줄에서 회차·제목을 뽑는다
            m = re.match(r"#\s*(\S+)\s*·\s*(.+?)\s*—", s)
            if m:
                ep, title = m.group(1), m.group(2)
            continue
        if s.startswith(">") or s.startswith("---") or not s.strip():
            continue
        if s.startswith("## "):
            head = s[3:].strip()
            skip = head.startswith("사전 질문지")      # 이 구역은 통째로 뺀다
            if not skip:
                out.append(("h", head))
            continue
        if skip:
            continue
        if s.startswith("**[") and "읽지 않음" in s:
            if keep_dir:
                out.append(("d", s.replace("**", "")))
            continue
        out.append(("p", s))
    return ep, title, out


def build(md, template, dest, keep_dir=True):
    ep, title, items = parse(md, keep_dir)
    if not ep:
        raise SystemExit("제목 줄에서 회차를 못 읽었다 — `# 차12 · 제목 — …` 꼴이어야 한다")
    spoken = sum(len(t) for k, t in items if k == "p")
    lo, hi = int(spoken / FAST / 60 + 0.5), int(spoken / SLOW / 60 + 0.5)
    sub = ("촬영용 프롬프터 스크립트 초안  ·  대사 예상 RT %d-%d분  ·  차트 포함 최종 예상 RT %d-%d분"
           % (lo, hi, lo + CHART_EXTRA, hi + CHART_EXTRA))
    no = re.sub(r"\D", "", ep)

    ps = [
        para("%s  ·  SHOOTING SCRIPT" % ep, '<w:spacing w:after="40"/>',
             '<w:b/><w:color w:val="2E74B5"/><w:sz w:val="19"/>'),
        para(title, '<w:keepNext/><w:spacing w:after="100"/>',
             '<w:b/><w:color w:val="0B2545"/><w:sz w:val="48"/>'),
        para(sub, '<w:pBdr><w:bottom w:val="single" w:sz="6" w:space="8" w:color="D9E4F0"/></w:pBdr>'
                  '<w:spacing w:after="280"/>', '<w:color w:val="5A626C"/><w:sz w:val="24"/>'),
    ]
    for kind, text in items:
        ps.append({"h": heading, "d": direction}.get(kind, para)(text))

    z = zipfile.ZipFile(template)
    doc = z.read("word/document.xml").decode("utf-8")
    head, tail = doc.split("<w:body>", 1)
    sect = re.search(r"<w:sectPr.*?</w:sectPr>", tail, re.S).group(0)
    doc_new = head + "<w:body>" + "".join(ps) + sect + "</w:body></w:document>"

    hdr = z.read("word/header1.xml").decode("utf-8")
    hdr_new = re.sub(r"(<w:t[^>]*>)[^<]*(</w:t>)",
                     r"\g<1>차트명가  |  롱폼 %s 촬영용 스크립트\g<2>" % no, hdr, count=1)

    core = z.read("docProps/core.xml").decode("utf-8")
    core = re.sub(r"<dc:title>[^<]*</dc:title>",
                  "<dc:title>%s %s 촬영용 스크립트</dc:title>" % (esc(ep), esc(title)), core)
    core = re.sub(r"<dc:subject>[^<]*</dc:subject>",
                  "<dc:subject>차트명가 롱폼 %s 촬영용 스크립트</dc:subject>" % no, core)
    core = re.sub(r"<dc:creator>[^<]*</dc:creator>", "<dc:creator>차트명가</dc:creator>", core)

    swap = {"word/document.xml": doc_new, "word/header1.xml": hdr_new, "docProps/core.xml": core}
    tmp = dest + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for item in z.infolist():
            if item.filename in swap:
                out.writestr(item.filename, swap[item.filename].encode("utf-8"))
            else:
                out.writestr(item, z.read(item.filename))
    z.close()
    shutil.move(tmp, dest)
    n = {k: sum(1 for x, _ in items if x == k) for k in "hpd"}
    print("%s — 구간 %d · 낭독 문단 %d(%d자) · 지시문 %d · 예상 RT %d-%d분"
          % (os.path.basename(dest), n["h"], n["p"], spoken, n["d"], lo, hi))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 3:
        raise SystemExit(__doc__)
    build(args[0], args[1], args[2], keep_dir="--no-지시문" not in sys.argv)
