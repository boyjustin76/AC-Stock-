#!/usr/bin/env python3
"""숏폼 대본 — 롱폼에서 뽑아내는 규칙을 코드로 옮긴 것.

숏폼 대본을 만드는 방식은 팀장님 머릿속에만 있었다.  숏폼 25편과 그 원본 롱폼
13편을 문장 단위로 맞춰 보고 역으로 뽑아낸 규칙이 여기 들어 있다.  근거 수치는
log/worklog.db 의 shortform_rule 테이블에 회차별로 남아 있다.

    python3 tools/shortform.py brief 11 --chapter "전략 1" --no 4
        롱폼 11회차의 '전략 1' 챕터로 숏폼 #4 를 쓰기 위한 작성 지시서를 만든다.
        챕터 원문, 목표 분량, 반드시 들어갈 문구, 다음 편으로 넘기는 질문까지.

    python3 tools/shortform.py chapters 11
        그 회차 롱폼이 어떤 챕터로 나뉘어 있는지 본다.

    python3 tools/shortform.py check draft.txt
        써 놓은 초안이 규칙에 맞는지 검사한다.  분량·훅·CTA·질문 마감·파일 이름.
        파일 이름에 '[포인트' 가 있으면 포인트 갈래로 검사한다 (--kind 로 지정 가능).
        포인트는 SL 과 세는 법도 속도도 이름 규칙도 다르다 — log/SCRIPT-LAB.md §4~5.

    python3 tools/shortform.py check draft.txt --kind point --genre 복제
        트팩 원본을 근접 복제한 편은 대본만 봐서는 못 짚으니 직접 준다.

    python3 tools/shortform.py name 11 --no 4 --title "20일선 추세추종 매매법"
        회사 규칙대로 폴더·파일 이름을 만든다.  작업중이면 앞에 (중간) 이 붙는다.

    python3 tools/shortform.py name --kind point --title "손절 기준 잡는 법"
        포인트 편 이름.  YYMMDD_[포인트_차]제목 / [포인트_차]제목.txt
        트팩이면 --channel 트팩 → [포인트].

쓰지 않는 것: 일정표에서 '숏폼(포)' 로 표시된 편.  그건 롱폼 추출이 아니라
외부 레퍼런스를 보고 따로 기획한 것이라 규칙이 다르다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LONG = json.loads((ROOT / "log/data/scripts.json").read_text(encoding="utf-8"))
SHORT = json.loads((ROOT / "log/data/shortform.json").read_text(encoding="utf-8"))

CPS = SHORT["cps"]                      # 6.82 — 자막 13편 실측 중앙값
IDEAL = SHORT["ideal_seconds"]          # 45초 — 팀장님이 정한 이상적인 길이
norm = lambda s: re.sub(r"[^가-힣A-Za-z0-9]", "", s)

# ── 목표 분량 ──────────────────────────────────────────────────────
# 목표는 45초다. 팀장님이 정한 값이고, 나간 편들의 실태(중앙값 55.9초)와는 다르다.
#
# 자막(.srt) 13편을 뜯어 잰 값 — 각 숏폼 폴더의 '소스+원본' 안에 있다.
#   자/초        중앙값 6.82 (범위 6.2~7.7)
#   영상 길이     중앙값 55.9초 (범위 39.3~83.4)  ← 목표보다 24% 길다
#   자수         중앙값 401자
#   훅           3.6초 / 26자   ← 길이와 무관하게 거의 고정
#   본문         49.0초 / 341자 ← 길이는 여기서만 늘고 준다
#   CTA          2.7초 / 26자   ← 고정 문구라 거의 일정
#
# 45초 × 6.82 = 307자.  훅·CTA 는 고정이므로 본문만 255자로 줄인다.
# 밴드는 40~50초(273~341자).
IDEAL_CHARS = 307
TARGET = {
    "총 분량":  (273, 341),      # 40~50초. 한가운데가 45초 = 307자
    "① 훅":    (20, 35),        # 실측 21~63, 중앙값 26
    "②③ 본문": (225, 285),      # 307 - 훅 26 - CTA 26 = 255 가 한가운데
    "④ CTA":   (20, 35),        # 실측 11~39, 중앙값 26
}

# ── 포인트 갈래 ────────────────────────────────────────────────────
# SL 과 다른 물건이다. SL 값(6.82자/초 · 45초 = 307자)을 포인트에 쓰면 안 된다.
# 근거는 log/SCRIPT-LAB.md §4 — 차명 포인트_차 43편 전수, 자막 36편 실측.
#
# Old/New 를 섞으면 안 된다. 260725_포지션 중독 부터가 New 다(팀장 지시).  7월에
# 첫 줄 형식이 갈아탔고 발화 속도도 달라져서, 전수 중앙값을 쓰면 Old 가 분포를
# 끌어당긴다.  New 10편(260725~261001) 실측:
#   영상 길이   중앙값 53.9초 (43.1~63.1)
#   발화 글자   중앙값 362자  (267~495)
#   발화 속도   중앙값 6.70자/초       ← SL 은 6.82
#
# 갈래마다 또 다르다. 토크편은 말이 빨라 같은 초에 글자가 더 들어간다.
# 아래 값은 차명 자기 자막(.srt)만 써서 다시 쟀다.  '발화 글자수 ÷ 실제 영상 길이'.
#   260725 토크  415자 / 60.0초 = 6.91      260806 기법  330자 / 47.6초 = 6.93
#   260730 토크  495자 / 53.9초 = 9.19      260808 기법  482자 / 71.7초 = 6.72
#                                            260810 기법  345자 / 53.1초 = 6.49
POINT_CPS = {
    "토크": 6.91,   # 6.91 과 9.19 중 낮은 쪽. 길게 잡아 두는 편이 안전하다
    "기법": 6.72,   # 6.49·6.72·6.93 의 중앙값
    "복제": 6.72,   # 기법과 같은 값을 쓴다 — 아래 주석 참고
}
# '복제'(모드 A)편은 차명 자기 자막이 없다. 260903·260910 폴더에 있는 .srt 는
# TF(참고) 원본의 것이라 트팩 목소리의 길이다.  같은 사람이 읽는데 갈래만 다르다고
# 속도를 따로 잡을 근거가 없어서 기법 값을 그대로 쓴다.  글자수 밴드만 따로 둔다.
POINT_SEC = (43, 63)            # New 10편 실측 길이 범위 43.1~63.1 을 그대로 밴드로 쓴다
POINT_CHARS = {                 # 갈래별 실측 발화 글자수
    "토크": (415, 495),         # 260725 415자 · 260730 495자
    "기법": (319, 482),
    "복제": (267, 352),
}

# 발화가 아닌 줄. 세면 안 된다 — 촬영 때 읽지 않는다.
DROP_LINE = re.compile(r"^\s*(제목\s*:|레퍼런스|\*\*)|https?://")
LABEL = re.compile(r"^\s*[①②③④]\s*[^:\n]{0,30}:\s*")    # '① 훅 (Hook) : '
STAGE = re.compile(r"\([^)\n]*\)")                        # (차트보며) 같은 지문


def spoken(raw: str) -> str:
    """실제로 입에서 나가는 말만 남긴다.

    norm() 은 파일 전문을 센다.  SL 대본은 그래도 됐지만 포인트 대본은 제목 줄·
    톤 지시 줄·원본 URL·「① 훅 (Hook) : 」 라벨·「(차트보며)」 지문이 파일 안에
    같이 있어서, 그대로 세면 실제보다 11~14% 길게 나온다.

    나간 편으로 확인했다 — 260810 후행스팬은 실제 53.1초인데 59초로, 260910
    캔들 꼬리는 실제 43.1초인데 49초로 읽었다.
    """
    out = []
    for line in raw.replace("\r\n", "\n").split("\n"):
        if DROP_LINE.search(line):
            continue
        out.append(STAGE.sub("", LABEL.sub("", line)))
    return "\n".join(out)


def point_genre(raw: str) -> str:
    """대본만 보고 갈래를 짚는다. '복제'는 원본을 봐야 알아서 못 짚는다."""
    return "토크" if "라이브 방송 중" in raw else "기법"


# 포인트 이름 규칙 — 차명 43편이 43/43 으로 지켰다. naming_rule 테이블에는 없다.
#   폴더  YYMMDD_[포인트_차]제목      파일  [포인트_차]제목.txt
#   트팩  YYMMDD_[포인트]제목         파일  [포인트]제목.txt
P_FOLDER_RE = re.compile(r"^(?:\(중간\))?(\d{6})_\[포인트(?:_차)?\](.+)$")
P_FILE_RE = re.compile(r"^(?:\(중간\))?\[포인트(?:_차)?\](.+)\.txt$")


def check_point_name(path: Path) -> list[str]:
    bad = []
    if not P_FILE_RE.match(path.name):
        bad.append(f"파일 이름 — [포인트_차]제목.txt 형태여야 합니다 (지금: {path.name})")
    if not P_FOLDER_RE.match(path.parent.name):
        bad.append(f"폴더 이름 — YYMMDD_[포인트_차]제목 형태여야 합니다 (지금: {path.parent.name})")
    return bad


# New 10편 중 몇 편이 지켰나. SL 의 CHECKS 와 모집단이 달라 따로 둔다.
# 훅 「오늘은 ~ 알려드릴게요」는 여기서 3/10 뿐이라 선택이다. SL 에서는 필수다.
POINT_CHECKS = [
    ("라벨", r"[①②③④]\s*[^:\n]{0,30}:\s",
     "「① 훅 (Hook) : 」 라벨 — 콜론 뒤 공백 하나", 7, 10),
    ("구독", r"(구독|팔로우)", "CTA 는 구독 유도", 10, 10),
    ("훅", r"오늘은[\s\S]{0,80}?(알려드릴게요|알려드리겠습니다|소개해\s?드릴게요)",
     "훅이 「오늘은 …를 알려드릴게요」", 3, 10),
    ("톤 지시", r"\*\*라이브 방송 중", "2행 톤 지시 (토크편만 붙는다)", 2, 10),
]


# 거의 모든 편에 나오는 고정 문구. 괄호 안은 25편 중 몇 편에 나왔는지.
PHRASES = {
    "훅": ["오늘은 {주제}를 알려드릴게요"],                       # 22/24
    "역접": ["하지만", "그런데", "반대로"],                        # 19/24
    "전환": ["그렇다면"],                                         # 13/24
    "CTA 질문": ["그렇다면 {다음 주제}는 무엇일까요?"],            # 10/24
    "CTA 유도": ["더 자세한 내용이 궁금하시다면",
                 "저를 팔로우하고",
                 "아래 영상을 주목해주세요"],                      # 19/24, 17/24
}

SKELETON = """[제목]
{title}

### ① 훅 (Hook)
오늘은 {topic}를 알려드릴게요

### ② 근거 (Evidence)
{evidence}

### ③ 본론 (Body)
{body}

### ④ 아웃트로 (CTA)
{tease}
더 자세한 내용이 궁금하시다면
저를 팔로우하고
아래 영상을 주목해주세요
"""


# 트팩 편을 차명으로 가져오는 방식은 둘뿐이다. 원본이 얼마나 오래됐는지로 갈린다.
#   모드 A  원본이 6개월 이상 묵었다 → 거의 그대로 옮긴다
#           260808 1.13 · 260903 0.94 · 260910 0.87 · 260924 1.01  (간격 6~9개월)
#   모드 B  원본이 최근이다 → 뼈대만 가져오고 문장은 새로 쓴다
#           260828 진화한 세력들 0.59  (간격 0개월)
# 겹침이 드러나면 안 되는 쪽이 모드 B 다. 같은 달에 나간 편을 그대로 옮기면 티가 난다.
COPY_MODE_MONTHS = 6
COPY_RATIO = {"A": (0.87, 1.13), "B": (0.50, 0.70)}

POINT_SKELETON = """제목 : {title}
{tone}
① 훅 (Hook) :
{hook}

② 근거 (Evidence) :
{evidence}

③ 본론 (Body) :
(차트보며)
{body}

④ 결과 (Conclusion) :
{outro}
"""

POINT_OUTRO = {
    "토크": "정리하자면\n(반말 단정 슬로건 한 줄)\n동의하면 구독과 좋아요\n반박하면 댓글도 환영입니다",
    "기법": "정리하자면\n(무엇이 그대로이고 무엇이 달라졌는지)\n\n(다음 편으로 넘기는 질문)\n저를 구독하고 다음 영상을 기다려주세요",
}


# ── 이름 짓기 ──────────────────────────────────────────────────────
# 폴더  YYMMDD_[SL_차XX_#X]숏폼제목
# 파일  [SL]숏폼제목[롱폼제목#X].txt
# 아직 작업 중이면 둘 다 맨 앞에 (중간) 을 붙인다.
#
# 폴더 규칙은 나간 25편이 25/25 로 지켰다.  파일 규칙은 5/25 인데, 지킨 것이
# 차09·차11 로 최근 편들이라 이쪽이 새로 정해진 표준이다.
WIP = "(중간)"
FOLDER_RE = re.compile(r"^(?:\(중간\))?(\d{6})_\[SL_차(\d{2})_#(\d)\](.+)$")
FILE_RE = re.compile(r"^(?:\(중간\))?\[SL\](.+?)\[(.+?)#(\d)\]\.txt$")


def long_title(ep: int) -> str:
    """롱폼 제목. '차명11_20일선의 비밀' → '20일선의 비밀'."""
    for d in LONG["docs"]:
        if d["ep_no"] == ep:
            return d["ep"].split("_", 1)[-1]
    return f"차{ep:02d}"


def folder_name(ep: int, no: int, title: str, date: str, wip: bool = True) -> str:
    return f"{WIP if wip else ''}{date}_[SL_차{ep:02d}_#{no}]{title}"


def file_name(ep: int, no: int, title: str, wip: bool = True) -> str:
    return f"{WIP if wip else ''}[SL]{title}[{long_title(ep)}#{no}].txt"


def check_point(a, raw):
    """포인트 갈래 검사. SL 과 세는 법도, 속도도, 이름 규칙도 다르다."""
    genre = a.genre or point_genre(raw)
    cps = POINT_CPS[genre]
    lo, hi = POINT_CHARS[genre]
    slo, shi = POINT_SEC
    body = spoken(raw)
    # 세는 것은 발화만, 규칙 검사는 파일 전문으로 한다. 라벨·톤 지시는 발화가
    # 아니라 body 에서 지워졌지만, 있어야 할 자리에 있는지는 봐야 한다.
    flat = re.sub(r"\s+", " ", raw)
    n = len(norm(body))
    n_raw = len(norm(raw))
    est = n / cps

    print(f"\n  {a.file}")
    print(f"  갈래 {genre}{'' if a.genre else ' (대본에서 짚었습니다)'}"
          f" · 초당 {cps}자 — New 10편 실측")
    print(f"  발화 {n}자 → 약 {est:.0f}초"
          f"   (파일 전문은 {n_raw}자 — 제목·라벨·지문·URL 은 읽지 않으므로 뺐다)\n")

    missing = []
    ok_len = slo <= est <= shi
    print(f"    {'○' if ok_len else '△'}  분량   {n}자 / {est:.0f}초"
          f"   (밴드 {slo}~{shi}초 · {genre}편 실측 {lo}~{hi}자)")
    for _, pat, desc, hit, tot in POINT_CHECKS:
        good = bool(re.search(pat, flat))
        t = tier(hit, tot)
        if not good and t == "필수":
            missing.append(desc)
        print(f"    {'○' if good else '·'}  {t}   {desc}   (New {hit}/{tot}편)")

    # 첫 줄은 「제목 : 」 형이거나 원본 URL 형이거나. 섞은 편은 New 10편 중 0편이다.
    mixed = bool(re.search(r"^\s*제목\s*:", raw, re.M)) and "http" in raw
    if mixed:
        missing.append("첫 줄 — 「제목 : 」 형과 URL 형을 섞었다. 섞은 편은 0/10 이다")
    print(f"    {'·' if mixed else '○'}  필수   "
          "「제목 : 」 형과 URL 형을 섞지 않는다   (섞은 편 0/10)")

    if "영트모" in raw:
        missing.append("「영트모로 입장하세요」 — 트팩 CTA 다. 차명은 쓰지 않는다")
        print("    ·  필수   트팩 CTA(영트모)를 쓰지 않는다")

    name_bad = check_point_name(Path(a.file))
    print(f"    {'·' if name_bad else '○'}  필수   폴더·파일 이름이 회사 규칙에 맞는다   (43/43편)")
    missing += name_bad

    print()
    if missing:
        print("  손볼 곳:")
        for m in missing:
            print(f"    · {m}")
    elif not ok_len:
        print("  필수는 다 지켰습니다. 분량만 밴드 밖입니다 — "
              f"{'덜어내세요' if est > shi else '더 쓰세요'}.")
    else:
        print("  필수·분량 모두 맞습니다.")
    print("  · SL 규칙(6.82자/초 · 307자 · [SL_차XX_#X])은 여기에 쓰지 않았습니다."
          " 근거는 log/SCRIPT-LAB.md §4~5.\n")


def cmd_name(a):
    date = a.date or _today()
    wip = not a.final
    if a.kind == "point":
        tag = "포인트_차" if a.channel == "차명" else "포인트"
        fo = f"{WIP if wip else ''}{date}_[{tag}]{a.title}"
        fi = f"{WIP if wip else ''}[{tag}]{a.title}.txt"
    else:
        if a.ep is None or a.no is None:
            sys.exit("SL 은 회차(ep)와 --no 가 있어야 합니다.")
        fo = folder_name(a.ep, a.no, a.title, date, wip)
        fi = file_name(a.ep, a.no, a.title, wip)
    print(f"\n  폴더  {fo}")
    print(f"  파일  {fi}")
    print(f"\n  scripts/shortform/{fo}/{fi}\n")
    if wip:
        print("  아직 작업 중이라 (중간) 이 붙었습니다. 확정되면 --final 로 다시 뽑으세요.")
    print(f"  날짜는 {'지정한 값' if a.date else '오늘'}입니다."
          " 나간 25편의 폴더 날짜는 방영일이니, 확정할 때 방영일로 바꾸세요.\n")


def _today() -> str:
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone(timedelta(hours=9))).strftime("%y%m%d")


def check_name(path: Path) -> list[str]:
    """파일·폴더 이름이 규칙에 맞는지. 어긋난 것만 돌려준다."""
    bad = []
    if not FILE_RE.match(path.name):
        bad.append(f"파일 이름 — [SL]숏폼제목[롱폼제목#N].txt 형태여야 합니다 (지금: {path.name})")
    if not FOLDER_RE.match(path.parent.name):
        bad.append(f"폴더 이름 — YYMMDD_[SL_차XX_#X]숏폼제목 형태여야 합니다 (지금: {path.parent.name})")
    return bad


# ── 롱폼 읽기 ──────────────────────────────────────────────────────
def long_doc(ep: int) -> dict | None:
    for d in LONG["docs"]:
        if d["ep_no"] == ep and d["status"] == "작성됨" and d["file"].endswith(".docx"):
            return d
    return None


def chapters(text: str) -> list[tuple[str, str]]:
    """[제목] 머리와 '전략 N' 줄을 챕터 경계로 본다."""
    marks = []
    for m in re.finditer(r"^\[([^\]\n]{2,70})\]", text, re.M):
        marks.append((m.start(), m.group(1).strip()))
    for m in re.finditer(r"^(전략\s*\d[^\n]{0,60})", text, re.M):
        marks.append((m.start(), m.group(1).strip()))
    marks.sort()
    if not marks:
        return [("(챕터 구분 없음 — 전체)", text)]
    out = []
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        body = text[pos:end]
        body = body.split("\n", 1)[1] if "\n" in body else ""
        out.append((name, body.strip()))
    return out


def pick(ep: int, needle: str) -> tuple[str, str]:
    doc = long_doc(ep)
    if not doc:
        sys.exit(f"롱폼 {ep}회차 대본이 없습니다. (log/data/scripts.json 확인)")
    chs = chapters(doc["text"])
    hits = [(n, b) for n, b in chs if needle.replace(" ", "") in n.replace(" ", "")]
    if not hits:
        print("그런 챕터가 없습니다. 이 회차의 챕터는:", file=sys.stderr)
        for n, b in chs:
            print(f"  · {n}  ({len(norm(b))}자)", file=sys.stderr)
        sys.exit(1)
    return max(hits, key=lambda x: len(x[1]))


# ── 같은 회차에서 이미 만든 숏폼 ───────────────────────────────────
def siblings(ep: int) -> list[dict]:
    return sorted((d for d in SHORT["docs"] if d["ep"] == ep and not d["rerun"]),
                  key=lambda d: d["no"] or 9)


def planned(ep: int) -> list[dict]:
    out = []
    for r in SHORT["schedule_sl"]:
        if re.search(rf"차{ep:02d}[_\]]", r["title"]) or re.search(rf"차{ep:02d}_", r["source"]):
            out.append(r)
    return sorted(out, key=lambda r: r["date"])


# ── 명령 ───────────────────────────────────────────────────────────
def cmd_chapters(a):
    doc = long_doc(a.ep)
    if not doc:
        sys.exit(f"롱폼 {a.ep}회차 대본이 없습니다.")
    print(f"\n  롱폼 차{a.ep:02} — {doc['file']}")
    print(f"  {len(norm(doc['text']))}자\n")
    for n, b in chapters(doc["text"]):
        print(f"    {len(norm(b)):5}자  {n[:70]}")
    made = siblings(a.ep)
    if made:
        print("\n  이미 만든 숏폼")
        for d in made:
            print(f"    #{d['no']}  {d['date']}  {d['chars']:4}자 / 약 {d['est_sec']:.0f}초"
                  f"  · 롱폼 {d['long_window']}~{(d['long_window'] or 0)+10}% 구간에서"
                  f"  · {d['folder'][7:46]}")
    plan = planned(a.ep)
    if plan:
        print("\n  일정표에 잡힌 숏폼")
        for r in plan:
            print(f"    {r['date']}  {r['title'][:56]}")
    print()


def cmd_brief(a):
    if a.kind == "point":
        return brief_point(a)
    if a.ep is None or not a.chapter or a.no is None:
        sys.exit("SL 지시서는 회차(ep)·--chapter·--no 가 있어야 합니다.")
    name, body = pick(a.ep, a.chapter)
    doc = long_doc(a.ep)
    made = siblings(a.ep)
    lo, hi = TARGET["총 분량"]

    print("═" * 74)
    print(f"  숏폼 작성 지시서 — 차{a.ep:02}_#{a.no}")
    print("═" * 74)
    print(f"\n  원본   롱폼 차{a.ep:02} · 챕터 「{name}」 ({len(norm(body))}자)")
    print(f"  목표   {IDEAL}초 = {IDEAL_CHARS}자   (허용 {lo}~{hi}자 = {lo/CPS:.0f}~{hi/CPS:.0f}초)")
    print(f"         초당 {CPS}자 — 자막 13편 실측 중앙값")
    cn = len(norm(body))
    lfn = len(norm(doc["text"]))
    if cn > hi:
        print(f"  압축   챕터 {cn}자 → {hi}자 이하로. 약 {round(hi / cn * 100)}% 로 줄인다")
    else:
        print(f"  압축   챕터 {cn}자 → {lo}~{hi}자. 챕터가 짧으니 줄이기보다 풀어 쓴다")
    print(f"         (숏폼 한 편은 롱폼 전체 {lfn}자의 {round((lo + hi) / 2 / lfn * 100)}% 안팎)")

    print("\n  ─ 뼈대와 목표 분량 (45초 기준) ─")
    for k in ("① 훅", "②③ 본문", "④ CTA"):
        l, h = TARGET[k]
        print(f"    {k:9} {l:3}~{h:3}자  {l/CPS:4.1f}~{h/CPS:4.1f}초   {_part_hint(k)}")
    print("    훅과 CTA 는 길이와 상관없이 거의 고정이다. 줄이고 늘리는 것은 본문이다.")

    print("\n  ─ 반드시 지킬 것 ─")
    print("    · 훅은 «오늘은 …를 알려드릴게요» 한 문장. (25편 중 22편)")
    print("    · 근거에 역접을 한 번 넣는다 — «하지만/그런데». (19편)")
    print("    · CTA 는 답을 주지 않고 «…무엇일까요?» 로 넘긴다. (10편)")
    print("    · 마무리 3줄은 고정: 궁금하시다면 / 저를 팔로우하고 / 아래 영상을 주목해주세요.")
    print("    · 자막·타이틀·로고 문구는 쓰지 않는다. 내레이션만 쓴다.")

    if made:
        print("\n  ─ 같은 회차에서 이미 나간 편 (겹치지 말 것) ─")
        for d in made:
            first = next((l.strip() for l in d["text"].split("\n")
                          if l.strip().startswith("오늘은")), "")
            print(f"    #{d['no']} {d['date']}  {d['folder'][7:44]}")
            if first:
                print(f"         훅: {first[:60]}")

    prev = [d for d in made if (d["no"] or 9) == a.no - 1]
    if prev:
        q = _tease_of(prev[0]["text"])
        print(f"\n  ─ 앞 편(#{a.no-1})이 던진 질문 ─")
        print(f"    「{q}」")
        print("    이 편의 훅이 그 답이 되어야 한다. 숏폼은 사슬처럼 이어진다.")

    print("\n  ─ 챕터 원문 ─")
    for line in body.strip().split("\n"):
        if line.strip():
            print(f"    │ {line.strip()}")

    print("\n  ─ 채워 넣을 틀 ─\n")
    for line in SKELETON.format(
            title="(제목 두 줄)", topic="(주제)",
            evidence="(통념 → 역접 → 문제)",
            body="(구체적 기준·설정값·순서)",
            tease="(다음 편으로 넘기는 질문)").split("\n"):
        print(f"    {line}")
    print("  초안을 쓴 뒤 검사:  python3 tools/shortform.py check <파일>\n")


def _read_any(path: Path) -> str:
    """드라이브 대본은 인코딩이 제각각이다. BOM·CP949·UTF-16 을 다 본다."""
    for enc in ("utf-8-sig", "cp949", "utf-16"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            pass
    return path.read_text(encoding="utf-8", errors="replace")


def _srt_seconds(folder: Path) -> float | None:
    """자막 마지막 타임코드 = 영상 길이."""
    for srt in sorted(folder.glob("소스+원본/*.srt")) + sorted(folder.glob("*.srt")):
        t = _read_any(srt)
        m = re.findall(r"(\d\d):(\d\d):(\d\d)[,.](\d\d\d)", t)
        if m:
            h, mi, se, ms = m[-1]
            return int(h) * 3600 + int(mi) * 60 + int(se) + int(ms) / 1000
    return None


def point_source(arg: str) -> dict:
    """트팩 원본 한 편을 읽는다. 폴더를 줘도 되고 .txt 를 줘도 된다."""
    path = Path(arg)
    if path.is_dir():
        folder = path
        txts = sorted(folder.glob("*.txt"))
        if not txts:
            sys.exit(f"그 폴더에 .txt 가 없습니다: {folder}")
        path = txts[0]
    else:
        folder = path.parent
    if not path.exists():
        sys.exit(f"원본이 없습니다: {path}")
    raw = _read_any(path)
    # 폴더 이름 어디에 있든 첫 YYMMDD_ 를 잡는다.
    # 참고 폴더는 앞에 TF(참고)_ 가 붙는다 — TF(참고)_260322_[포인트]….
    m = re.search(r"(\d{6})_", folder.name)
    return {
        "path": path, "folder": folder, "raw": raw,
        "date": m.group(1) if m else None,
        "chars": len(norm(spoken(raw))),
        "sec": _srt_seconds(folder),
    }


def _months(a: str, b: str) -> int:
    """YYMMDD 두 개 사이의 개월 수."""
    return (int(b[:2]) * 12 + int(b[2:4])) - (int(a[:2]) * 12 + int(a[2:4]))


def brief_point(a):
    src = point_source(a.source)
    genre = a.genre or "기법"
    cps = POINT_CPS[genre]
    clo, chi = POINT_CHARS[genre]
    slo, shi = POINT_SEC
    today = a.date or _today()

    gap = _months(src["date"], today) if src["date"] else None
    mode = None if gap is None else ("A" if gap >= COPY_MODE_MONTHS else "B")
    rlo, rhi = COPY_RATIO[mode] if mode else (None, None)

    print("═" * 74)
    print(f"  포인트 작성 지시서 — [포인트_차]{a.title or '(제목 미정)'}")
    print("═" * 74)
    print(f"\n  원본   {src['folder'].name}")
    print(f"         발화 {src['chars']}자" +
          (f" · {src['sec']:.1f}초" if src["sec"] else " · 자막 없음"))
    print(f"  목표   {clo}~{chi}자 = {clo/cps:.0f}~{chi/cps:.0f}초"
          f"   (밴드 {slo}~{shi}초 · {genre}편 · 초당 {cps}자)")

    print(f"\n  ─ 카피 모드 {mode or '판정 못 함'} ─")
    if mode is None:
        print("    원본 폴더 이름에서 YYMMDD 를 못 읽었습니다. 모드는 직접 판단하세요 —")
        print(f"    원본이 {COPY_MODE_MONTHS}개월 이상 묵었으면 A, 아니면 B 다.")
    elif mode == "A":
        print(f"    원본이 {gap}개월 묵었다. 거의 그대로 옮긴다.")
        print("    나간 편: 260808 1.13 · 260903 0.94 · 260910 0.87 · 260924 1.01")
    else:
        print(f"    원본이 {gap}개월밖에 안 됐다. 뼈대만 가져오고 문장은 새로 쓴다.")
        print("    같은 달에 나간 편을 그대로 옮기면 티가 난다. 260828 편이 0.59 였다.")
    if mode:
        t_lo, t_hi = round(src["chars"] * rlo), round(src["chars"] * rhi)
        print(f"    분량   원본 {src['chars']}자 × {rlo}~{rhi} = {t_lo}~{t_hi}자"
              f"   (갈래 밴드와 겹치는 구간으로 잡는다)")

    print("\n  ─ 반드시 지킬 것 (New 10편 기준) ─")
    print("    · 첫 줄 «제목 : 제목». 원본 URL 을 들고 오는 편이면 URL 형으로 가고"
          " 둘을 섞지 않는다. (섞은 편 0/10)")
    print("    · 라벨 «① 훅 (Hook) : » — 콜론 뒤 공백 하나. (7/10)")
    print("    · 4단 뼈대 훅 → 근거 → 본론 → 결과. 원본이 3단이어도 4단으로 다시 끼운다.")
    print("    · 차트를 짚는 자리에 «(차트보며)» 지문.")
    print("    · CTA 는 구독 유도. (10/10)")
    if genre == "토크":
        print("    · 2행에 «**라이브 방송 중 답변한다는 느낌으로». 이건 연기 지시다 —"
              " 차명이 라이브를 한다는 뜻이 아니다.")
        print("    · 종결을 구어로 — «~거든요» «~잖아요» «~단 말이죠» «그러니깐».")
        print("    · 결론은 «정리하자면» → 반말 단정 → 동의하면 구독과 좋아요 /"
              " 반박하면 댓글도 환영입니다.")
    else:
        print("    · 훅 «오늘은 ~ 알려드릴게요» 는 3/10 뿐이다. 선언형·질문형도 된다.")

    print("\n  ─ 쓰면 안 되는 것 ─")
    print("    · «영트모로 입장하세요» — 트팩 CTA 다. 차명은 절대 안 쓴다.")
    print("    · 차명이 라이브를 한다는 투의 문장. 차명은 라이브를 하지 않는다.")
    print("    · 자막·타이틀·로고 문구. 편집에서 들어간다.")
    print("    · 원본 문장을 통째로. 10자 연속 겹침이 기준선 2.2% 를 넘으면 안 된다.")

    print("\n  ─ 원본 ─")
    for line in src["raw"].replace("\r\n", "\n").strip().split("\n"):
        if line.strip():
            print(f"    │ {line.strip()}")

    print("\n  ─ 채워 넣을 틀 ─\n")
    tone = "**라이브 방송 중 답변한다는 느낌으로\n" if genre == "토크" else ""
    filled = POINT_SKELETON.format(
        title=a.title or "(제목)", tone=tone,
        hook="(무엇을 말할지 · 대화로 던져도 된다)",
        evidence="(통념 → 하지만 → 그래서 안 통한다)",
        body="(구체적 기준·설정값·순서)",
        outro=POINT_OUTRO[genre])
    for line in filled.split("\n"):
        print(f"    {line}")
    print("  초안을 쓴 뒤 검사:  python3 tools/shortform.py check <파일>\n")


def _part_hint(k):
    return {
        "① 훅": "무엇을 알려줄지 한 문장",
        "②③ 본문": "통념 → 하지만 → 문제 → 기준·설정값·순서 → 다음 편으로 넘기는 질문",
        "④ CTA": "궁금하시다면 / 저를 팔로우하고 / 아래 영상을 주목해주세요",
    }[k]


def _tease_of(text):
    flat = [l.strip() for l in text.replace("\r\n", "\n").split("\n") if l.strip()]
    qs = [l for l in flat[-14:] if re.search(r"(을까요|일까요|할까요|무엇을까요|까요)\s*\?*$", l)]
    return qs[-1] if qs else "(없음)"


# 기존 24편에서 몇 편이 지켰나로 등급을 나눈다.
#   필수(≥85%) · 권장(65~85%) · 선택(<65%)
# 24편 중 5개를 모두 지킨 것은 2편뿐이다. 이건 규칙이 아니라 경향이라는 뜻이라,
# 어긋난다고 틀린 게 아니다. 다만 어긋나면 이유가 있어야 한다.
CHECKS = [
    ("훅", r"오늘은[\s\S]{0,80}?(알려드릴게요|알려드리겠습니다|소개해\s?드릴게요)",
     "«오늘은 …를 알려드릴게요» 로 시작", 22, 24),
    ("영상 유도", r"(아래|다음)\s*영상", "«아래/다음 영상» 으로 유도", 20, 24),
    ("역접", r"(하지만|그런데|반대로)", "근거에 역접이 있다", 19, 24),
    ("팔로우", r"(팔로우|구독)", "«팔로우/구독» 유도", 17, 24),
    ("질문 마감", r"(을까요|일까요|할까요|무엇을까요)\s*\?*",
     "CTA 를 미해결 질문으로 넘긴다", 10, 24),
]

def tier(hit, tot):
    r = hit / tot
    return "필수" if r >= 0.85 else ("권장" if r >= 0.65 else "선택")


def cmd_check(a):
    raw = Path(a.file).read_text(encoding="utf-8").replace("\r\n", "\n")
    kind = a.kind or ("point" if "[포인트" in Path(a.file).name else "sl")
    if kind == "point":
        return check_point(a, raw)
    flat = re.sub(r"\s+", " ", raw)
    n = len(norm(raw))
    lo, hi = TARGET["총 분량"]
    est = n / CPS
    print(f"\n  {a.file}")
    print(f"  {n}자 → 약 {est:.0f}초   (목표 {IDEAL}초 = {IDEAL_CHARS}자)\n")

    missing = []
    ok_len = lo <= n <= hi
    over = ""
    if not ok_len:
        over = f"  {'+' if n > hi else '−'}{abs(round(est - IDEAL))}초"
    print(f"    {'○' if ok_len else '△'}  분량   {n}자 / {est:.0f}초{over}"
          f"   (허용 {lo}~{hi}자 = {lo / CPS:.0f}~{hi / CPS:.0f}초)")
    for _, pat, desc, hit, tot in CHECKS:
        good = bool(re.search(pat, flat))
        t = tier(hit, tot)
        if not good and t == "필수":
            missing.append(desc)
        print(f"    {'○' if good else '·'}  {t}   {desc}   (기존 {hit}/{tot}편)")

    if re.search(r"(포인트|\[포\])", raw):
        missing.append("'포인트/포' 표기 — 편집에서 붙는 것이라 대본에 쓰지 않는다")
        print("    ·  필수   '포인트/포' 표기를 쓰지 않는다")

    name_bad = check_name(Path(a.file))
    print(f"    {'·' if name_bad else '○'}  필수   폴더·파일 이름이 회사 규칙에 맞는다   (폴더 25/25편)")
    missing += name_bad

    print()
    if missing:
        print("  손볼 곳:")
        for m in missing:
            print(f"    · {m}")
    elif not ok_len:
        cut = n - IDEAL_CHARS
        print(f"  필수는 다 지켰습니다. 분량만 목표 밖입니다 —"
              f" 45초에 맞추려면 본문에서 {abs(cut)}자 {'덜어내세요' if cut > 0 else '더 쓰세요'}.")
        print("  (나간 편들도 중앙값 55.9초로 목표보다 깁니다. 의도한 것이면 그대로 두세요.)")
    else:
        print("  필수·분량 모두 맞습니다.")
    print("  · 표시된 권장/선택은 어겨도 됩니다. 기존 24편 중 5개를 다 지킨 건 2편뿐입니다.\n")


def main():
    ap = argparse.ArgumentParser(description="숏폼 대본 — 롱폼 추출 규칙")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("chapters", help="롱폼 회차의 챕터와 이미 만든 숏폼을 본다")
    c.add_argument("ep", type=int)
    c.set_defaults(fn=cmd_chapters)

    b = sub.add_parser("brief", help="한 편을 쓰기 위한 작성 지시서")
    b.add_argument("ep", type=int, nargs="?", help="SL 일 때 롱폼 회차")
    b.add_argument("--kind", choices=("sl", "point"), default="sl")
    b.add_argument("--chapter", help="SL — 챕터 이름 일부 (예: '전략 1')")
    b.add_argument("--no", type=int, help="SL — 이 회차의 몇 번째 숏폼인가")
    b.add_argument("--source", help="포인트 — 트팩 원본 폴더 또는 .txt 경로")
    b.add_argument("--title", help="포인트 — 이 편 제목")
    b.add_argument("--genre", choices=tuple(POINT_CPS), help="포인트 — 갈래 (기본 기법)")
    b.add_argument("--date", help="포인트 — 방영 예정일 YYMMDD. 카피 모드 판정에 쓴다")
    b.set_defaults(fn=cmd_brief)

    k = sub.add_parser("check", help="초안이 규칙에 맞는지 검사")
    k.add_argument("file")
    k.add_argument("--kind", choices=("sl", "point"),
                   help="갈래. 없으면 파일 이름의 '[포인트' 로 짚는다")
    k.add_argument("--genre", choices=tuple(POINT_CPS),
                   help="포인트 갈래 세부. 없으면 대본에서 짚는다."
                        " '복제'는 원본을 봐야 알 수 있어 직접 주어야 한다")
    k.set_defaults(fn=cmd_check)

    m = sub.add_parser("name", help="회사 규칙대로 폴더·파일 이름을 만든다")
    m.add_argument("ep", type=int, nargs="?", help="SL 일 때 롱폼 회차")
    m.add_argument("--kind", choices=("sl", "point"), default="sl")
    m.add_argument("--channel", choices=("차명", "트팩"), default="차명",
                   help="포인트일 때. 차명=[포인트_차] · 트팩=[포인트]")
    m.add_argument("--no", type=int, help="SL 일 때 이 회차의 몇 번째 숏폼인가")
    m.add_argument("--title", required=True, help="숏폼 제목")
    m.add_argument("--date", help="YYMMDD. 없으면 오늘(KST)")
    m.add_argument("--final", action="store_true", help="확정본 — (중간) 을 붙이지 않는다")
    m.set_defaults(fn=cmd_name)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
