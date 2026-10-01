# -*- coding: utf-8 -*-
"""촬영 대본(.pdf) → 구간별 낭독 **문장** (align 과 테이크 찾기에 쓴다).

마이노 대본 꼴 (마01 기준, 2026-10-01 실측)
  머리말            `차트명가 | 롱폼 12 촬영용 스크립트`, `L12 · SHOOTING SCRIPT` — **쪽마다 반복된다**
  구간 머리글       `INTRO. …`, `1. …`, `2. …`, `OUTRO`
  `[차트 진행 · 읽지 않음]`  아래 문단은 읽지 않는다 — 빈 줄 둘 또는 쪽 머리말까지
  낭독분            **프롬프터라 줄마다 빈 줄이 하나씩 끼어 있다**

여기가 함정이다 (2026-10-01, 자막 오탈자·경계로 드러남)
  ① **빈 줄 하나는 문단의 끝이 아니다.** 프롬프터가 한 줄씩 띄워 놓은 것이다.
     실측 — 빈 줄 1개 97곳(줄바꿈) · 2개 이상 26곳(문단 바뀜) · 0개 25곳(쪽 머리말 앞뒤).
     빈 줄 하나를 문단 끝으로 보면 `… 겹쳐 사용하는 '더블` / `볼린저 밴드' 매매법을` 처럼
     **말 중간에서 끊긴 토막**이 문장이 되고, 그게 그대로 자막 큐가 된다.
  ② **쪽이 바뀌면 문장 중간에 머리말이 끼고 빈 줄이 4개 들어간다.** 그걸 문단 끝으로 보면
     `… 보조 밴드를 겹치면` 과 `작은 흔들림에는 닿지 않습니다.` 가 갈린다 — 한 문장인데.
  ③ **4장 글머리 문단은 양끝 맞추기(justify)라 낱말 중간에서 줄이 바뀐다.**
     `… 절대` / `적인 기준으로` → 그냥 이으면 `절대 적인` 이 된다. 실제로 자막에 12곳 있었다.
     들여쓴 이어짐 줄(들여쓰기 ≥3)이 그 후보다. **붙일지 띄울지는 받아쓰기로 가린다** —
     `--받아쓰기 cam_transcript.json` 을 주면 실제 발화에서 두 꼴의 빈도를 세어 고른다.
     (마01 실측: 12곳 중 11곳은 붙이고 `청산하여 수익을` 만 띄운다. 자동 규칙으로는 못 가른다.)
  ④ **지시문은 괄호 안에 숨어서도 온다** — `맞습니다. (차트를 보며 횡보장 매매 설명)`.
     읽는 말과 한 줄에 붙어 있으니 줄 단위로는 못 걸러낸다.

내놓는 것 (json)
  [{"구간": "INTRO", "제목": "밴드 하단에 샀는데 …", "문장": ["…", …]}, …]

    python3 tools/cutedit/pdf_script.py <대본.pdf> <결과.json> [--받아쓰기 <cam_transcript.json>]
"""
import io, os, re, sys, json, subprocess, glob

머리글 = re.compile(r"^(INTRO|OUTRO|\d+)\.?\s*(.*)$")
버릴줄 = re.compile(r"^(차트명가\s*\||L\d+\s*·|촬영용 프롬프터|· 차트 포함|더블 볼린저밴드 매매법$)")
지시문 = re.compile(r"^\[.*읽지 않음\]")
# 괄호 안 연출 지시 — 읽는 말과 한 줄에 붙어 온다. `(가짜 신호)`·`(반등/반락)`·`(1)` 은 읽는 말이니 건드리지 않는다
괄호지시 = re.compile(r"\s*\([^()]*(설명|언급|보여주며|보여줍니다|표시합니다|진행)[^()]*\)")
글머리 = re.compile(r"^([•·]|\(\d+\)|\d+\))\s*")
# PDF 가 숫자와 조사·단위를 떼어 놓는다 — `표준편차 2 의`, `20 에서`, `4 로`, `20 일 중심선`, `2 가지`.
# 그대로 두면 자막에 `2 의` 로 나가고, 구·절 가름도 `20 | 에서` 에서 헷갈린다 (2026-10-01 실측).
숫자조사 = re.compile(r"(?<=\d)\s+(의|이|가|은|는|을|를|에|에서|로|으로|과|와|도|만|까지|부터"
                      r"|일|개|가지|번|차|초|분|배|회|명|원|년|월|주|배수|퍼센트|%)(?=\s|[,.)\]]|$)")
이어짐들여 = 3        # 이만큼 들여썼으면 양끝맞추기로 줄이 바뀐 것 (마01 실측: 글머리 2 · 이어짐 6)


def pdf글(경로):
    도구 = glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages",
                                  "*oppler*", "*", "Library", "bin", "pdftotext.exe"))
    if not 도구: 도구 = ["pdftotext"]
    out = subprocess.run([도구[0], "-layout", 경로, "-"], capture_output=True)
    return out.stdout.decode("utf-8", "ignore")


def 받아쓰기글(경로):
    """받아쓴 말 한 덩어리 — 띄어쓰기를 살려 둔다(붙일지 띄울지 가리는 데 쓴다)."""
    d = json.load(io.open(경로, encoding="utf-8"))
    조각 = d if isinstance(d, list) else d.get("segments", d.get("words", []))
    return re.sub(r"\s+", " ", " ".join(s.get("text", s.get("word", "")) for s in 조각))


def 붙일까(왼, 오른, 말=None):
    """양끝맞추기로 끊긴 자리를 붙일지(`절대`+`적인`→`절대적인`) 띄울지(`청산하여`+`수익을`) 가린다.

    받아쓴 말이 있으면 **실제 발화의 띄어쓰기**를 따른다 — 규칙으로는 못 가른다.
    없으면 띄운다(안전한 쪽: 붙여서 틀리면 없는 낱말이 생긴다).
    """
    앞말 = (왼.split() or [""])[-1]
    뒷말 = (오른.split() or [""])[0]
    if not re.search(r"[가-힣0-9]$", 앞말) or not re.match(r"[가-힣0-9]", 뒷말):
        return False
    if re.search(r"[.?!,:;)\]]$", 앞말):
        return False
    if 말:
        붙, 띄 = 말.count(앞말 + 뒷말), 말.count(앞말 + " " + 뒷말)
        if 붙 or 띄: return 붙 > 띄
        return None                                    # 받아쓰기에 둘 다 없다 — 사람이 봐야 한다
    return None


줄바꿈표 = "\x00"      # 원본에서 줄이 바뀐 자리 표시 — 여기서만 문장을 끊을 수 있다
맺음 = re.compile(r"(니다|니까|세요|십시오|죠|예요|어요|아요|한다|된다|이다)$")


def 문장쪼개기(문단):
    """마침표로 끊고, **마침표가 없어도 맺는 말로 끝난 줄**이면 그 자리에서 끊는다.

    마01 대본은 마침표를 빠뜨린 줄이 꽤 있다 — `… 골드 1 시간입니다`(마침표 없음) 다음 줄에
    새 문장이 온다. 마침표만 보면 두 문장이 한 큐로 붙어 자막이 길어진다.
    원본에서 줄이 바뀐 자리(줄바꿈표)에서만 끊는다 — 문장 중간을 쪼개지 않기 위해서다.
    """
    조각, 나올것 = re.split(r"(?<=[.?!])[%s\s]+" % 줄바꿈표, 문단.strip()), []
    for 조 in 조각:
        덩이 = ""
        for 토막 in 조.split(줄바꿈표):
            덩이 = (덩이 + " " + 토막).strip() if 덩이 else 토막
            if 맺음.search(덩이.rstrip()):
                나올것.append(덩이); 덩이 = ""
        if 덩이: 나올것.append(덩이)
    return [숫자조사.sub(r"\1", re.sub(r"\s+", " ", s)).strip() for s in 나올것 if len(s.strip()) >= 2]


def 읽기(경로, 받아쓰기=None):
    말 = 받아쓰기글(받아쓰기) if 받아쓰기 else None
    줄들 = pdf글(경로).split("\n")
    구간, 지금, 덩이, 건너뛰기, 쪽바뀜, 빈, 애매 = [], None, [], False, False, 0, []

    def 덩이닫기():
        """모아 둔 줄들을 한 덩어리로 이어 문장으로 쪼갠다."""
        if not 덩이:
            return
        줄 = 덩이[:]
        덩이.clear()
        글 = 줄[0][1]
        for 들여, 글자 in 줄[1:]:
            붙 = False
            if 들여 >= 이어짐들여 and not 글머리.match(글자):
                판 = 붙일까(글, 글자, 말)
                if 판 is None:
                    애매.append((글.split()[-1] if 글.split() else "", 글자.split()[0] if 글자.split() else ""))
                붙 = bool(판)
            글 += ("" if 붙 else 줄바꿈표) + 글자
        글 = 글머리.sub("", 글).strip()                 # 글머리 기호는 읽지 않는다
        if 글 and 지금 is not None:
            지금["문장"] += 문장쪼개기(글)

    for l in 줄들:
        s = l.strip()
        if not s:
            빈 += 1
            # 쪽이 바뀌는 자리의 빈 줄은 문단을 끊지 않는다 (함정 ②)
            if 빈 >= 2 and not 쪽바뀜:
                덩이닫기()
                건너뛰기 = False
            continue
        앞빈, 빈 = 빈, 0
        들여 = len(l) - len(l.lstrip())
        if 버릴줄.match(s):                             # 쪽 머리말 — 문단은 이어진다
            쪽바뀜, 건너뛰기 = True, False
            continue
        s = 괄호지시.sub("", s).strip()                  # 괄호 안 연출 지시 (함정 ④) — 줄 안에 섞여 온다
        if not s:
            continue
        m = 머리글.match(s)
        if m and (s.startswith(("INTRO", "OUTRO")) or re.match(r"^\d+\.\s*\S", s)):
            덩이닫기()
            지금 = {"구간": m.group(1), "제목": m.group(2).strip(), "문장": []}
            구간.append(지금)
            건너뛰기, 쪽바뀜 = False, False
            continue
        if 지시문.match(s):
            덩이닫기()
            건너뛰기, 쪽바뀜 = True, False
            continue
        쪽넘김, 쪽바뀜 = 쪽바뀜, False
        if 건너뛰기:
            continue
        앞들여 = 덩이[-1][0] if 덩이 else 0
        if 글머리.match(s) and 들여 < 이어짐들여:        # 글머리 항목은 저마다 한 덩어리다
            덩이닫기()
        elif 들여 == 0 and 앞들여 >= 2:                  # 글머리 덩어리에서 본문으로 돌아왔다
            덩이닫기()
        elif 앞빈 >= 2 and not 쪽넘김:                   # 쪽이 바뀌며 생긴 빈 줄은 문단을 끊지 않는다 (함정 ②)
            덩이닫기()
        덩이.append((들여, s))
    덩이닫기()
    return 구간, 애매


if __name__ == "__main__":
    인자 = sys.argv[1:]
    받 = None
    if "--받아쓰기" in 인자:
        i = 인자.index("--받아쓰기")
        받 = 인자[i + 1]
        인자 = 인자[:i] + 인자[i + 2:]
    구간, 애매 = 읽기(인자[0], 받)
    json.dump(구간, io.open(인자[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for g in 구간:
        글자 = sum(len(s) for s in g["문장"])
        print("%-6s %-34s 문장 %3d · %5d자 (낭독 %.1f분)" %
              (g["구간"], g["제목"][:34], len(g["문장"]), 글자, 글자 / 6.8 / 60))
    if 애매:
        print("\n붙일지 띄울지 못 가린 자리 %d곳 — 사람이 봐야 한다 (받아쓰기에 두 꼴이 다 없다)" % len(애매))
        for a, b in 애매: print("   «%s» + «%s»" % (a, b))
    print("냈다:", 인자[1])
