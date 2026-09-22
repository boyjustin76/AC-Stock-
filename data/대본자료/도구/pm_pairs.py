# -*- coding: utf-8 -*-
"""**버린 것 ↔ 고른 것** 쌍을 모은다 — 팀장·이정찬이 실제로 내린 결정의 기록.

    python pm_pairs.py --걷기 <피드백.docx> --회차 차12 --누가 팀장
    python pm_pairs.py --걷기 <원본.md> <고친판.md> --회차 차12 --누가 이정찬
    python pm_pairs.py                      # 쌓인 것 보기

## 왜 쌓나

총괄(2026-09-21): "**팀장 선택 기록** — 회차마다 팀장이 고른 문구와 버린 문구를 쌍으로 쌓는다.
수십 쌍이 되면 그때 선호 학습. **병목은 모델이 아니라 이 표본이다.**"

Jev 판정관 시험도 같은 자리에서 막혔다 — 표본이 적어 순위를 못 배운다.
그래서 결정이 내려질 때마다 **자동으로 걷어** 둔다. 나중에 몰아서 만들 수 없는 자료다.

## 어디서 걷나

- **색 표시된 `.docx`** — 팀장 범례(이정찬 2026-09-22 정정):
  - `#EE0000`·`#FF0000` = **같은 빨강**이다. `FF0000` 은 색을 잘못 고른 것일 뿐이다.
  - 빨강 옆에 **괄호 글**(`(*…)`, `[*…]`, `(=>…)`, `[…]`)이 있으면 **삭제가 아니라 대체**다.
    괄호가 없을 때만 삭제다.
  - `#00B050` = 추가(더원 L07 참고).
  - **예전에는 `FF0000` 을 '고칠 대목'으로 읽어 `고름` 칸에 넣었다 — 정반대였다.**
    팀장이 지우거나 바꾸라고 한 문장이 '고른 문장'으로 쌓여 있었다(2026-09-22 바로잡음).
  - 괄호 글이 **이웃 문단**에 있을 때(예: 28문단 ↔ 30~33문단)는 도구가 못 잇는다.
    같은 문단 안에서만 대체로 잡고, 나머지는 `삭제(확인)` 로 남겨 사람이 짝짓는다.
- **두 판의 `.md`** — 원본과 고친 판을 줄 단위로 맞대어 바뀐 자리를 쌍으로 뽑는다.

## 저장 자리

`05_대본자료/팀장쌍/pairs.jsonl` — **저장소 밖이다.** `AC-Stock-` 는 public 이고
이 쌍은 회사 대본 문장이라 Pool 과 같은 취급을 한다. 도구만 저장소에 둘 수 있다.
"""
import argparse
import difflib
import io
import json
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(os.path.dirname(HERE), "팀장쌍", "pairs.jsonl")
MARK = {"EE0000": "버림", "FF0000": "버림", "00B050": "고름"}
괄호글 = re.compile(r"\([^()]*\)|\[[^\[\]]*\]")


def _unesc(s):
    return s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")


def docx_marks(path):
    """색 표시된 docx → [(문단번호, 앞뒤 맥락, [(표시, 글)…])]"""
    x = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    body = x.split("<w:body>", 1)[1]
    out = []
    for i, p in enumerate(re.findall(r"<w:p[ >].*?</w:p>|<w:p/>", body, re.S)):
        segs = []
        for r in re.findall(r"<w:r[ >](?:(?!</w:r>).)*</w:r>", p, re.S):
            t = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", r, re.S))
            if not t:
                continue
            m = re.search(r'<w:color w:val="([0-9A-Fa-f]{6})"', r)
            c = (m.group(1).upper() if m else "")
            if segs and segs[-1][0] == c:
                segs[-1][1] += _unesc(t)
            else:
                segs.append([c, _unesc(t)])
        if any(c in MARK for c, _ in segs):
            plain = "".join(t for c, t in segs if c not in MARK).strip()
            out.append((i, plain, [(MARK[c], t.strip()) for c, t in segs if c in MARK]))
    return out


def md_lines(path):
    raw = io.open(path, encoding="utf-8").read().split("## INTRO", 1)[-1]
    return [s.strip() for s in ("## INTRO" + raw).split("\n")
            if s.strip() and not s.strip().startswith((">", "---", "|", "- ", "#"))]


def md_pairs(before, after):
    a, b = md_lines(before), md_lines(after)
    rows = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            for x, y in zip(a[i1:i2], b[j1:j2]):
                rows.append({"버림": x, "고름": y, "꼴": "바꿈"})
        elif tag == "delete":
            for x in a[i1:i2]:
                rows.append({"버림": x, "고름": "", "꼴": "지움"})
        else:
            for y in b[j1:j2]:
                rows.append({"버림": "", "고름": y, "꼴": "더함"})
    return rows


def 쌓기(rows):
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    있던 = set()
    if os.path.exists(STORE):
        for line in io.open(STORE, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                있던.add((r.get("버림", ""), r.get("고름", "")))
    새 = [r for r in rows if (r.get("버림", ""), r.get("고름", "")) not in 있던]
    with io.open(STORE, "a", encoding="utf-8", newline="\n") as f:
        for r in 새:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(새), len(있던) + len(새)


def 보기():
    if not os.path.exists(STORE):
        print("아직 쌓인 것이 없다."); return
    rows = [json.loads(l) for l in io.open(STORE, encoding="utf-8") if l.strip()]
    print("쌓인 쌍 **%d개**  (`%s`)\n" % (len(rows), os.path.relpath(STORE, os.path.dirname(HERE))))
    from collections import Counter
    print("누가:", dict(Counter(r.get("누가") for r in rows)),
          "· 회차:", dict(Counter(r.get("회차") for r in rows)),
          "· 꼴:", dict(Counter(r.get("꼴") for r in rows)))
    for r in rows:
        print("\n  [%s · %s · %s]" % (r.get("회차"), r.get("누가"), r.get("꼴")))
        if r.get("버림"):
            print("   버림  %s" % r["버림"][:96])
        if r.get("고름"):
            print("   고름  %s" % r["고름"][:96])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--걷기", nargs="+")
    ap.add_argument("--회차", default="")
    ap.add_argument("--누가", default="")
    ap.add_argument("--날짜", default="2026-09-21")
    a = ap.parse_args()
    if not a.걷기:
        보기(); raise SystemExit

    rows = []
    if len(a.걷기) == 1 and a.걷기[0].lower().endswith(".docx"):
        for i, 맥락, marks in docx_marks(a.걷기[0]):
            # 괄호 글은 색과 상관없이 팀장 메모(지시·대체안)다 — 빨강으로 적힌 메모도 있다(51문단).
            # 같은 색 run 이 이어지면 문장과 메모가 한 덩이로 붙어 온다(11문단) — 덩이 안에서 괄호만 떼어 낸다.
            지시들, 버림들, 고름들 = [], [], []
            for k, t in marks:
                지시들 += 괄호글.findall(t)
                남은 = 괄호글.sub(" ", t).strip()
                if 남은 and 남은 not in "()[].":
                    (버림들 if k == "버림" else 고름들).append(남은)
            지시, 버림, 고름 = " ".join(지시들), " ".join(버림들), " ".join(고름들)
            if 버림:
                꼴 = "대체" if (고름 or 지시) else "삭제(확인)"
            else:
                꼴 = "추가"
            rows.append({"문단": i, "버림": 버림, "고름": 고름, "지시": 지시,
                         "맥락": 맥락, "꼴": 꼴})
    elif len(a.걷기) == 2:
        rows = md_pairs(a.걷기[0], a.걷기[1])
    else:
        raise SystemExit(__doc__)

    for r in rows:
        r.update({"회차": a.회차, "누가": a.누가, "날짜": a.날짜,
                  "출처": os.path.basename(a.걷기[-1])})
    새, 전체 = 쌓기(rows)
    print("걷은 쌍 %d개 중 **새로 쌓은 것 %d개** · 전체 **%d개**" % (len(rows), 새, 전체))
