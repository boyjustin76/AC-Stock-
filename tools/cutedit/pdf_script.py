# -*- coding: utf-8 -*-
"""촬영 대본(.pdf) → 구간별 낭독 문장 (align 과 테이크 찾기에 쓴다).

마이노 대본 꼴 (마01 기준, 2026-10-01)
  머리말            `차트명가 | 롱폼 12 촬영용 스크립트`, `L12 · SHOOTING SCRIPT` 같은 줄 — 쪽마다 반복된다
  구간 머리글       `INTRO. …`, `1. …`, `2. …`, `OUTRO`
  `[차트 진행 · 읽지 않음]`  그 아래 문단은 **읽지 않는다** — 다음 빈 줄 둘까지 건너뛴다
  나머지            낭독분. pdf 가 줄을 잘라 놔서 빈 줄을 기준으로 문단을 다시 잇는다

내놓는 것 (json)
  [{"구간": "INTRO", "제목": "밴드 하단에 샀는데 …", "문장": ["…", …]}, …]

    python3 tools/cutedit/pdf_script.py <대본.pdf> <결과.json>
"""
import io, os, re, sys, json, subprocess, glob

머리글 = re.compile(r"^(INTRO|OUTRO|\d+)\.?\s*(.*)$")
버릴줄 = re.compile(r"^(차트명가\s*\||L\d+\s*·|촬영용 프롬프터|· 차트 포함|더블 볼린저밴드 매매법$)")
지시문 = re.compile(r"^\[.*읽지 않음\]")


def pdf글(경로):
    도구 = glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages",
                                  "*oppler*", "*", "Library", "bin", "pdftotext.exe"))
    if not 도구: 도구 = ["pdftotext"]
    out = subprocess.run([도구[0], "-layout", 경로, "-"], capture_output=True)
    return out.stdout.decode("utf-8", "ignore")


def 문장쪼개기(문단):
    조각 = re.split(r"(?<=[.?!])\s+", 문단.strip())
    return [s.strip() for s in 조각 if len(s.strip()) >= 2]


def 읽기(경로):
    줄들 = [l.rstrip() for l in pdf글(경로).split("\n")]
    구간, 지금, 문단, 건너뛰기 = [], None, [], False
    def 문단닫기():
        글 = " ".join(문단).strip()
        문단.clear()
        if 글 and 지금 is not None: 지금["문장"] += 문장쪼개기(글)
    빈줄 = 0
    for l in 줄들:
        s = l.strip()
        if not s:
            빈줄 += 1
            문단닫기()
            if 빈줄 >= 2: 건너뛰기 = False             # 지시문 덩어리는 빈 줄 두 줄로 끝난다 (마01 실측)
            continue
        빈줄 = 0
        # 지시문 덩어리는 **쪽 머리글이나 다음 구간 머리글**까지 이어진다 (마01 실측 2026-10-01)
        if 버릴줄.match(s):
            건너뛰기 = False; continue
        m = 머리글.match(s)
        if m and (s.startswith(("INTRO", "OUTRO")) or re.match(r"^\d+\.\s*\S", s)):
            문단닫기()
            지금 = {"구간": m.group(1), "제목": m.group(2).strip(), "문장": []}
            구간.append(지금); 건너뛰기 = False; continue
        if 지시문.match(s): 건너뛰기 = True; continue
        if 건너뛰기: continue
        문단.append(s)
    문단닫기()
    return 구간


if __name__ == "__main__":
    구간 = 읽기(sys.argv[1])
    json.dump(구간, io.open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for g in 구간:
        글자 = sum(len(s) for s in g["문장"])
        print("%-6s %-34s 문장 %3d · %5d자 (낭독 %.1f분)" %
              (g["구간"], g["제목"][:34], len(g["문장"]), 글자, 글자 / 6.8 / 60))
    print("냈다:", sys.argv[2])
