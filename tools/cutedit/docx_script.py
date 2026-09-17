# -*- coding: utf-8 -*-
"""롱폼 촬영 대본(.docx) → align_take.py 가 읽는 대본(.txt).

더원트레이더 롱폼 대본 모양 (L07 더블 볼린저밴드 초안 기준) —
  머리말·사전 질문지        첫 구간 머리글 전까지. 낭독분이 아니다.
  INTRO. 제목 / 1. 제목 / OUTRO   구간 머리글. 제목은 낭독되기도 해서 후보 줄로 넣는다
                             (낭독 안 됐으면 정렬에서 후보가 안 잡혀 저절로 빠진다).
  [차트 진행 · 읽지 않음] …   문단 하나짜리 지시문. 대괄호가 줄 끝까지 안 가서
                             align_take 의 한 줄 지시문 규칙에 안 걸린다 → 여기서 뺀다.

문단 하나에 문장이 여럿이면 문장으로 쪼갠다. 롱폼 낭독은 틀리면 문단 머리가 아니라
문장 중간에서 다시 읽기도 해서, 문단째로 두면 마지막 테이크가 한 덩어리로 안 잡힌다.
워드에서 띄어쓰기가 빠진 곳('합니다.이후', '매매법!지금부터')도 여기서 가른다.

    python3 tools/cutedit/docx_script.py <대본.docx> <결과.txt>
"""
import io
import re
import sys
import zipfile

HEAD = re.compile(r"^(INTRO|OUTRO)\b\.?\s*(.*)$|^(\d{1,2})\.\s+(.+)$")
NOTE = re.compile(r"^\[[^\]]*읽지\s*않음[^\]]*\]")
# 문장 끝 — 마침표·물음표·느낌표 뒤에 글자가 오면 가른다 (띄어쓰기 유무 무관).
# 숫자 사이 점(2.0)은 뒤가 숫자라 안 걸린다.
SENT = re.compile(r"(?<=[.!?])\s*(?=[가-힣A-Za-z‘“\"'])")


def paragraphs(path):
    x = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    for p in re.findall(r"<w:p[ >].*?</w:p>", x, flags=re.S):
        t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
        t = (t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
              .replace("&quot;", '"').replace("&apos;", "'"))
        yield re.sub(r"\s+", " ", t).strip()


def convert(path):
    out, started = [], False
    for t in paragraphs(path):
        if not t:
            continue
        m = HEAD.match(t)
        if m:
            started = True
            if m.group(1):
                name, title = m.group(1), m.group(2)
            else:
                name, title = f"{m.group(3)}장", m.group(4)
            out += ["", f"[{name}]"]
            if title.strip():
                out.append(title.strip())
            continue
        if not started or NOTE.match(t):
            continue
        out += [s.strip() for s in SENT.split(t) if s.strip()]
    return "\n".join(out).strip() + "\n"


def main():
    if len(sys.argv) < 3:
        sys.exit("사용법: docx_script.py <대본.docx> <결과.txt>")
    txt = convert(sys.argv[1])
    io.open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(txt)
    lines = [l for l in txt.splitlines() if l and not l.startswith("[")]
    print(f"{sys.argv[2]} — 구간 {txt.count(chr(10) + '[') + txt.startswith('[')}개 · 줄 {len(lines)}개")


if __name__ == "__main__":
    main()
