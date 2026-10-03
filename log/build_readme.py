#!/usr/bin/env python3
"""worklog.db → README.md (깃허브 첫 화면).

깃허브 README 는 마크다운만 렌더한다. <style> 과 스크립트는 제거되므로
HTML 대시보드를 그대로 붙일 수 없다. 대신 깃허브가 실제로 그려 주는 것들
— mermaid 다이어그램, 배지, 표, <details> — 로 같은 정보를 담는다.

2026-10-03 개정 둘.
  ① 저장소가 렌더러 하나에서 세션 넷(총괄·B·D·E)의 제작 체계로 바뀐 뒤 첫 화면이 초기 버전 그대로였다.
  ② 이정찬이 이 저장소를 이력서에 첨부한다(AI·자동화·파이프라인 공고). 첫 화면은 '문제 → 해결' 로
     역량이 바로 읽히게 두고, 운영용 정보(열린 일·절차·구조)는 아래로 내려 접는다.
     저자 표기는 사실대로 — 코드는 클로드 세션 넷이 쓰고, 체계 설계·운영·검증·결정은 이정찬.

    python3 log/build_readme.py
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "log" / "worklog.db"
OUT = ROOT / "README.md"
DASHBOARD = "https://claude.ai/code/artifact/cfb762d2-2caf-4a18-8ec2-696b884ac0e1"

MARK = {"진행중": "🟢", "자료만": "🔵", "미착수": "⚪", "해당없음": "➖"}

# 뚫어낸 벽 — constraint_note rowid. 값비쌌던 순이 아니라 '다음 사람이 또 밟을' 순이다.
HARD_WALLS = [74, 70, 71, 56, 60, 73, 80, 75, 76, 77, 65, 67, 38, 39, 44, 43, 61, 31, 33, 66]

# 세션 넷 — CLAUDE.md 의 표와 같다. 바뀌면 둘 다 고친다.
SESSIONS = [
    ("**총괄** (클라우드 컨테이너)", "본류 clone", "`claude/futures-youtube-video-edit-fhio4s`",
     "옆가지 병합 · `log/build_worklog_db.py` 유일 편집자 · 공용 코드 판정 · 렌더러 `src/render` · 이정찬에게도 피드백"),
    ("**B** (사무실 PC)", "`B_Image`", "`worktree-B_Image`",
     "포토샵·일러스트레이터 — 썸네일, 라이브 화면, 김직선 비주얼 규격 실측(next_step 55)"),
    ("**D** (사무실 PC)", "`D_Video`", "`worktree-D_Video`",
     "AE·프리미어·MT5 — 어도비 공용 실행기, 대본→차트 장면 촬영, 리플레이, XML 가져오기 검증"),
    ("**E** (사무실 PC)", "`E_Script`", "`worktree-E_Script`",
     "대본(Pool+김직선 말투 조립)·컷편집·자막·프리미어 XML"),
]

# 문제 → 해결. 숫자는 전부 DB(issue·constraint_note·decision)와 인박스 보고서의 실측값이다. 번호가 출처.
CASES = [
    ("프리미어가 우리가 만든 시퀀스 XML 을 **'프로젝트가 손상'** 으로 거부. 3컷은 되고 9컷부터 깨짐",
     "구조가 아니라 **경로 표기**. `()[]&` 를 퍼센트로 바꾸면 경로를 못 찾고, 클립이 여럿이면 변환이 깨진다",
     "프리미어가 **스스로 내보낸 XML 과 맞댐** (태그 경로별 Counter 로 구조 무죄 확정 → 경로로 좁힘). BridgeTalk 로 **가져오기를 자동 재현** (사람 스샷 8판 → 1판 1분)",
     "캠 17컷·한글 경로 OK. 같은 버그가 총괄 렌더러에도 있어 함께 고침 · issue 56·57, constraint 74"),
    ("어도비 앱이 모달 창에 막히면 자동화가 **조용히 멈춘다**. SendKeys·UI Automation 으로 못 닫음",
     "어도비 자작 창은 UIA 트리에 안 잡힌다. 앱을 죽이면 모달도 사라져 증거가 없다",
     "**공용 실행기** `run.ps1` — 앱 넷을 표 한 줄로. 시간 초과면 Win32 `EnumChildWindows` 로 글자, `PrintWindow` 로 그림을 **먼저 찍고** 죽인다. 성공은 잡이 스스로 쓴 `판정:` 한 줄. AE 충돌 복구 창은 자식 창 뼈대로 알아보고 **0.2초/15.5초**에 멈춤",
     "실패 캡처 100%, 가짜 통과(FAIL TIMEOUT→exit 0) 제거 · issue 42~47·53, constraint 70·71"),
    ("대본 한 편에 맞는 **실제 차트 장면** 수십 장을 사람이 MT5 에서 찾아 찍고 있었다",
     "장면 조건(눌림·박스·톱니…)을 코드로 못 적었고, 적어도 **아무 구간이나 뽑혔다**(남의 계산 빌려 씀, 점수 포화)",
     "장면마다 **전용 함수 + 가짜 차트에 진짜·미끼를 심은 시험** 46개, 1등 몰림 경고. 규칙이 못 잡는 비트만 LLM 판정(문 0.7, 규칙 뒤집기는 0.8). 서브에이전트가 35장을 **눈으로 검수** → 고치기 네 번",
     "차10 12비트 124초 자동 촬영 → 콘티 → AE 프로젝트 20초. 검수 적합 20→31/35 · issue 52, next_step 45"),
    ("**LLM 판정 모델(TypeSafe Jev)** 을 어디에 써도 되나 — 문서만으론 모른다",
     "순위 비교에 **자리 치우침**: 한 방향으로만 재면 92%, 자리 바꿔 두 번 맞아야 하면 69%. 수를 견주는 자리에선 confidence 0.91 로 **자신 있게 틀림**",
     "세션 셋이 각자 **합격선을 먼저 정한 시험** 9종(한국어·순위·분류·모달 문구·로그 판정). 결과로 **조건부 채택**: 분류·거르기만, 자리 바꿔 두 번 + confidence 문",
     "분류 11/12·모달 5/5 채택, 순위 판정·로그 판정 기각 · decision 37, constraint 65·67"),
    ("자막이 영상보다 **늦게 뜨고**, 긴 문장에서 **밀린다**",
     "큐 시각을 초 단위로 더하고(프레임 반올림 누적) 글자 수에 **비례 분배**해서 말 속도가 바뀌면 어긋남",
     "프레임으로 셈 + 0.15초 당김(사람 수정본 실측) → **낱말 타임스탬프**로 큐 시각. 재촬영·숨소리는 소리 지도로 떼어냄",
     "안 맞는 큐 6 → **0**, 겹침 중앙값 0.76 · constraint 77, issue 54"),
    ("자막에 **오탈자 12곳·문장 누락 1** — '대본에서 뽑았으니 맞다' 고 넘겼다",
     "프롬프터 PDF 는 줄마다 빈 줄이 하나. 그걸 문단 끝으로 읽어 57문장이 **106토막**",
     "입력 구조를 **세어서** 확인(빈 줄 1개 97곳·2개+ 26곳). 낱말 중간 줄바꿈은 **받아쓰기의 띄어쓰기**로 판별. 산출물을 원본과 글자 단위로 **전수 대조**하는 스크립트",
     "대본 2007자 = 자막 2007자, 닮음 1.0 · issue 55, constraint 75"),
    ("클로드 세션 넷이 **같은 저장소**를 쓰며 서로 파일을 휩쓸고, 본류를 덮어쓸 뻔함",
     "`git add -A`, 본류 직접 push, 세션이 붙잡은 폴더 이동, 역슬래시 heredoc 깨짐 — 세 세션이 같은 함정을 따로 밟았다",
     "**worktree** 로 세션마다 폴더·브랜치 분리, **PreToolUse 훅**(`git_guard.py`)이 네 가지를 막음, `save.py --only` 범위 커밋, 총괄만 병합. 공개 저장소라 원문·자막·docx 는 `.gitignore`",
     "본류 사고 0, 병합 30회+ 겹침 충돌 0 · decision 30·31·38, issue 24·41·48"),
    ("같은 실수가 **세션을 바꿔 가며 되풀이**됨 (일부를 보고 전체를 판단 8건, 환경 함정 반복)",
     "기록이 세션마다 흩어지고, 보고가 '확인했다' 로만 끝남",
     "**SQLite 하나가 원본**(사고·벽·결정·절차·파일 지도) → md·html·README 자동 생성. 완료 보고에 `확인한 것 / 안 본 것` 두 줄 강제. `radar.py`: 오류 문구 → 우리 기록 → SO → GitHub. 막혔을 때 순서 넷(세기→맞대기→성공본 대조→자동 재현)",
     f"사고 {{n_issue}}건 중 고침 {{n_fixed}}, 벽 {{n_wall}}개, 결정 {{n_dec}}개가 번호로 추적됨 · decision 24·33·40"),
    ("차트 렌더가 **93초**, 컷마다 병렬로 돌려도 안 줄어듦",
     "프레임마다 스크린샷 캡처가 병목. 한 프로세스가 4코어를 포화",
     "캡처를 `canvas.toDataURL` 로 교체(출력 md5 동일), 벤치마크 표로 순차·병렬·프리셋 실측",
     "93초 → **26.8초**(같은 출력), 급하면 24.1초 · benchmark 표"),
    ("윈도우 PC 에서 파이썬·PowerShell·ExtendScript 가 **한글·경로**에서 조용히 죽음",
     "cp949 콘솔, 경로 끝 공백·마침표가 떨어짐, `Copy-Item` 의 `[ ]` 와일드카드, MS 스토어 가짜 `python3`, BOM 없는 .ps1",
     "두 사람이 따로 재현해 **실측표**로 확정 → 처방을 코드에(`PYTHONUTF8`, `strip(' .')`, `-LiteralPath`, `sys.executable`), 래칫 시험으로 재발 차단",
     "constraint 38·39·43·44·56·63·78 — 세 세션이 같은 벽을 다시 밟지 않음"),
]

STACK = [
    ("오케스트레이션", "Claude Code 세션 넷(총괄 클라우드 + 로컬 3) · git worktree · PreToolUse 훅 · 스킬 · 인박스 프로토콜 · 서브에이전트 검수"),
    ("판정·언어 모델", "TypeSafe Jev(System One, confidence 게이트) · KURE-v1 임베딩(배너 뜻 거리) · faster-whisper(STT, 낱말 타임스탬프) · 모두의 말뭉치 형태 태그(자막 가름)"),
    ("영상·그래픽", "Node.js · Playwright/Chromium 캔버스 렌더(1920×1080·59.94fps) · ffmpeg · FCP7 XML(xmeml) · After Effects/Premiere/Illustrator/Photoshop ExtendScript · BridgeTalk · COM"),
    ("데이터·검증", "SQLite(FTS5) 원본 → md/html/README 생성 · pytest 래칫 시험 85 · ruff · 벤치마크 표 · md5 회귀"),
    ("시세·차트", "MetaTrader 5 (HedgeHood MCP, MQL5 지표·EA — 자동 촬영·리플레이) · Yahoo v8 시세"),
    ("윈도우 자동화", "PowerShell 5.1(COM, Start-Job 시간 제한, Win32 창 열거·PrintWindow) · PyAV · OpenCV · python-docx/OOXML"),
]


def badge(label: str, value: str, color: str) -> str:
    f = lambda t: quote(t.replace("-", "--").replace("_", "__"), safe="")
    return f"![{label}](https://img.shields.io/badge/{f(label)}-{f(value)}-{color}?style=flat-square)"


def bar(done: int, total: int, width: int = 12) -> str:
    n = round(done / total * width) if total else 0
    return "█" * n + "░" * (width - n)


def short(s: str | None, n: int) -> str:
    s = (s or "").replace("\n", " ").replace("|", "／")
    return s if len(s) <= n else s[: n - 1] + "…"


def n_tests() -> int:
    return sum(len(re.findall(r"^\s*def test_", p.read_text(encoding="utf-8"), re.M))
               for p in (ROOT / "tests").glob("test_*.py"))


def build() -> str:
    con = sqlite3.connect(DB)
    q = lambda s: con.execute(s).fetchall()
    one = lambda s: con.execute(s).fetchone()[0]

    stages = q("SELECT p.format,p.seq,p.name,p.owner,p.in_repo,p.status,p.detail,p.note"
               " FROM pipeline_stage p JOIN format f ON f.name = p.format"
               " ORDER BY f.id, CAST(p.seq AS REAL)")
    fmts = q("SELECT name,aspect,final_spec,source_spec,length,tone,status FROM format ORDER BY id")

    n_issue = one("SELECT COUNT(*) FROM issue")
    n_fixed = one("SELECT COUNT(*) FROM issue WHERE status='fixed'")
    n_wall = one("SELECT COUNT(*) FROM constraint_note")
    n_dec = one("SELECT COUNT(*) FROM decision")
    n_run = one("SELECT COUNT(*) FROM runbook")
    n_req = one("SELECT COUNT(*) FROM request")
    n_commit = one("SELECT COUNT(*) FROM commit_log")
    n_inbox = len(list((ROOT / "log" / "inbox").glob("*.md")))
    n_cut = one("SELECT COUNT(*) FROM scene WHERE config LIKE '%cmg%'")
    n_frames = one("SELECT SUM(frames) FROM scene WHERE config LIKE '%cmg%'")
    n_doc = one("SELECT COUNT(DISTINCT ep) FROM script_doc WHERE status='작성됨'")
    n_empty = one("SELECT COUNT(DISTINCT ep) FROM script_doc WHERE status<>'작성됨'")
    n_prj = one("SELECT COUNT(*) FROM episode_prproj")
    n_tok = one("SELECT COUNT(*) FROM brand_token")
    n_lay = one("SELECT COUNT(*) FROM layer_catalog")
    n_mot = one("SELECT COUNT(*) FROM motion_preset")
    ser = one("SELECT wall_seconds FROM benchmark WHERE mode='serial-v2'")
    med = one("SELECT wall_seconds FROM benchmark WHERE mode='serial-v2-medium'")
    secs = one("SELECT seconds_video FROM benchmark LIMIT 1")
    last_kst = one("SELECT kst FROM checkpoint ORDER BY id DESC LIMIT 1") or ""
    first_day = one("SELECT started_on FROM session") or "2026-08-26"
    today = date.today().isoformat()
    tests = n_tests()

    L = []
    a = L.append

    # ── 머리 ───────────────────────────────────────────────
    a("# 차트명가 제작 자동화")
    a("")
    a("해외선물 유튜브 채널 **차트명가**(파가드AC)의 영상 제작 — 대본 → 컷편집·자막 → 차트 촬영·렌더 → 어도비 자동화 → 납품 — 을 "
      "**클로드 코드 세션 넷(클라우드 총괄 1 + 사무실 PC 3)이 한 저장소에서** 자동화한 기록입니다. "
      f"{first_day} 렌더러 하나로 시작해 2026-09-17 부터 세션 넷 체계입니다.")
    a("")
    a(" ".join([
        badge("세션", "총괄 + B·D·E", "0B8C7F"),
        badge("뚫은 벽", f"{n_wall}", "555"),
        badge("사고", f"{n_issue} (고침 {n_fixed})", "555"),
        badge("결정", f"{n_dec}", "555"),
        badge("시험", f"{tests}", "555"),
        badge("커밋", f"{n_commit}", "555"),
    ]))
    a("")
    a(f"📊 **[작업 로그 대시보드]({DASHBOARD})** · "
      f"[전체 기록 (WORKLOG)](log/WORKLOG.md) · [새 세션 안내 (CLAUDE.md)](CLAUDE.md) · "
      f"[뚫은 벽 전부](log/WORKLOG.md#환경이-거는-제약) · [사고 전부](log/WORKLOG.md#문제와-해결) · [세션 간 보고서](log/inbox/)")
    a("")
    a(f"<sub>마지막 세이브 {last_kst} KST · 이 문서는 `log/worklog.db` 에서 자동 생성 (`python3 log/build_readme.py`)</sub>")
    a("")
    a("---")
    a("")

    # ── 누가 무엇을 ───────────────────────────────────────
    a("## 누가 무엇을 했나")
    a("")
    a("| | |")
    a("|---|---|")
    a("| **이정찬** (팀원·컷편집) | 체계 **설계·운영·검증·결정**. 세션 넷의 역할 분담과 git 운영 규칙을 정하고, 세션 사이에서 보고서를 나르고, "
      "산출물을 프리미어·자막 원본에 대고 직접 검사해 반려하고(\"자막 .pdf 와 비교했어?\" → 오탈자 12곳 발견), 팀장 결정을 전달하고, "
      "에이전트의 피드백(작업 지시 방식·파일 판본 규칙 등)을 받아 고쳤다. **방법론을 정한 사람** — 눈대중 금지, 정답 자료에 대고 채점, 남이 검증한 방법 우선 |")
    a("| **클로드 세션 넷** | 코드·시험·문서 작성. 총괄(클라우드)이 병합·기록·판정, B(이미지)·D(영상·MT5)·E(대본·컷편집)가 각자 PC 의 앱을 직접 돌리며 실측 |")
    a("| **팀장** | 결과물 승인·반려, 방향 결정(차트명가New = 김직선 카피캣, 대본 B판 채택) |")
    a("")
    a("| 기간 | 세션 | 요청·대응 | 세션 간 보고서 | 사고 → 고침 | 뚫은 벽 | 결정 | 절차 | 시험 | 커밋 |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    a(f"| {first_day} ~ | 4 | {n_req} | {n_inbox} | {n_issue} → {n_fixed} | {n_wall} | {n_dec} | {n_run} | {tests} | {n_commit} |")
    a("")
    a("**납품된 것** — 차트명가 롱폼 차12 차트 컷씬 23컷(실데이터 렌더, 팀장 반려 r13 뒤 재작) · 숏폼 1:1 소스 차11-4·5 · "
      "더원트레이더 L08 롱폼 컷편집 합본(49컷·자막 233큐) · 마이노 마01 캠 롱폼(69컷·자막 161큐) · 차10/차11 차트 장면 자동 촬영(12장·35장) + 콘티 + AE 프로젝트 · "
      "차12·차13 대본(Pool 정보 + 김직선 말투 조립) · 썸네일·라이브 화면(포토샵·일러 자동 생성).")
    a("")
    a("---")
    a("")

    # ── 문제 → 해결 ───────────────────────────────────────
    a("## 문제 → 해결")
    a("")
    a("전부 실측이고, 번호(issue·constraint·decision)가 출처입니다. 짐작으로 적은 건 없습니다.")
    a("")
    a("| 문제 | 원인 | 해결 | 결과 · 출처 |")
    a("|---|---|---|---|")
    for p_, c_, s_, r_ in CASES:
        r_ = r_.replace("{n_issue}", str(n_issue)).replace("{n_fixed}", str(n_fixed)).replace("{n_wall}", str(n_wall)).replace("{n_dec}", str(n_dec))
        a(f"| {p_} | {c_} | {s_} | {r_} |")
    a("")
    a("**방법론 (이정찬이 정한 것, 세션 넷이 지키는 것)**")
    a("")
    a("- **측정이 먼저** — 브랜드 색·크기·모션·자막 속도·규격 전부 레퍼런스에서 픽셀·프레임 단위 실측. 짐작으로 바꾸지 않는다. 실태를 표준으로 착각하지 않는다(나간 숏폼 중앙값 55.9초 vs 목표 45초)")
    a("- **합격선을 먼저 정하고 시험** — 새 모델·도구는 정답 자료와 합격선을 적은 뒤 돌린다. 한 방향으로만 재면 92%, 자리를 바꿔 재면 69%(Jev)")
    a("- **래칫** — 절대 경로 리터럴·판정 줄 없는 잡·장면 미끼·모달 표는 시험이 상한을 쥔다. 늘어나면 깨지고, 줄이면 상한을 내린다")
    a("- **완료 보고 = 확인한 것 / 안 본 것 / 원본과 맞댔나** — '일부를 보고 전체를 판단' 사고 8건에서 나온 양식")
    a("- **막혔을 때 순서** — ① 입력 구조를 세어서 확인 ② 산출물은 원본과 맞대야 완료 ③ 성공본과 실패본을 맞댄다 ④ 재현은 자동화 (짐작으로 하나씩 고치는 건 그 뒤)")
    a("- **주류 먼저** — 맨땅에 헤딩하지 않는다. 남이 검증한 방법(공식 문서·채택도)을 먼저 찾고, 판단이면 판단이라고 적는다")
    a("")
    a("---")
    a("")

    # ── 어떻게 돌아가나 ───────────────────────────────────
    a("## 어떻게 돌아가나")
    a("")
    a("```mermaid")
    a("flowchart LR")
    a('  S["<b>대본</b> · E<br/><small>Pool 정보 + 김직선 말투 조립<br/>관문 12 (pipeline.py)</small>"]')
    a('  R["<b>촬영</b> · 사람<br/><small>캠 · PD 설명 · OBS</small>"]')
    a('  C["<b>컷편집·자막</b> · E + D<br/><small>whisper → 대본 정렬 → 무음 경계 컷<br/>→ 낱말 타임스탬프 자막 → 프리미어 XML</small>"]')
    a('  M["<b>차트 장면</b> · D<br/><small>비트 → 장면 탐색 → MT5 촬영<br/>→ 콘티 → AE 프로젝트 · 리플레이</small>"]')
    a('  V["<b>렌더러</b> · 총괄<br/><small>scenes/*.js → 1920×1080 · 59.94fps</small>"]')
    a('  T["<b>썸네일·화면</b> · B<br/><small>포토샵 · 일러 COM</small>"]')
    a('  A["<b>어도비 공용 실행기</b> · D<br/><small>run.ps1 — AE · 프리미어 · 일러 · 포토샵<br/>모달 읽기 · 판정 줄 · XML 가져오기 검증</small>"]')
    a('  P[["프리미어 타임라인 · 납품"]]')
    a("  S --> R --> C --> P")
    a("  S --> M --> A --> P")
    a("  S -.-> V --> P")
    a("  T --> A")
    a("  C --> A")
    a('  subgraph G ["공용 장치"]')
    a("    direction LR")
    a('    G1["worklog.db<br/><small>사고·벽·결정·절차</small>"]')
    a('    G2["save.py<br/><small>세이브 = 재빌드+커밋+푸시</small>"]')
    a('    G3["git_guard<br/><small>본류 push · add -A · 폴더 이동 · heredoc 차단</small>"]')
    a('    G4["radar<br/><small>벽에 두 번째 부딪히면 기록부터</small>"]')
    a('    G5["Jev<br/><small>뜻으로만 갈리는 판정 · 문 0.7/0.8</small>"]')
    a("  end")
    a("  classDef e fill:#0B8C7F,stroke:#0B8C7F,color:#fff")
    a("  classDef g fill:#F2F2F2,stroke:#C9C9C9,color:#444")
    a("  class S,C,M,V,T,A e")
    a("  class R,P,G1,G2,G3,G4,G5 g")
    a("```")
    a("")
    a("```mermaid")
    a("flowchart TB")
    a('  J["<b>이정찬</b><br/><small>설계 · 운영 · 검증 · 결정 · 보고서 전달</small>"]')
    a('  O["<b>총괄</b> (클라우드)<br/><small>병합 · 기록 DB · 공용 코드 판정 · 렌더러</small>"]')
    a('  B["<b>B</b> 이미지<br/><small>포토샵 · 일러</small>"]')
    a('  D["<b>D</b> 영상<br/><small>AE · 프리미어 · MT5</small>"]')
    a('  E["<b>E</b> 대본<br/><small>대본 · 컷편집 · 자막</small>"]')
    a('  TL["팀장<br/><small>승인 · 반려 · 방향</small>"]')
    a("  TL <--> J")
    a("  J <-->|인박스 .md| O")
    a("  J <-->|인박스 .md| B & D & E")
    a("  B & D & E -->|worktree-* push| O")
    a("  O -->|본류 병합 · 번호 등재| B & D & E")
    a("  classDef h fill:#F2F2F2,stroke:#C9C9C9,color:#444")
    a("  classDef s fill:#0B8C7F,stroke:#0B8C7F,color:#fff")
    a("  class J,TL h")
    a("  class O,B,D,E s")
    a("```")
    a("")
    a("| 묶음 | 어디 | 한 줄 |")
    a("|---|---|---|")
    a("| 대본 | `data/대본자료/도구` · `tools/theone` · `log/SCRIPT-LAB.md` | 뼈대의 조각 출처를 Pool 원문에 대고 기계로 대조(`pool_pieces`), 회사 기본폼 .docx(`skeleton_docx`), 관문 12개(`pipeline.py`) |")
    a("| 컷편집·자막 | `tools/cutedit` · runbook 18·26 | L08(09-11)·마01(10-01) 롱폼 합본. 자막 큐는 형태소 태그로 가름(`ko_clause`), XML 은 프리미어 표기(`make_xml`) |")
    a("| 차트 장면 | `tools/mt5` · `tools/ae/jobs/d1_conti_build.jsx` | 대본 한 편 → 12~35장 자동 촬영(`batch_capture`) → 콘티 → AE. 장면마다 전용 함수 + 심은 시험. 리플레이 도구로 전문가가 직접 진행 |")
    a("| 렌더러 | `src/render` · `scenes/` · `brand/` | 차12 계열(`cmg12-*`)이 최신 문법. `--stills` 로 구도 먼저 |")
    a("| 어도비 자동화 | `tools/_com/run.ps1` · `tools/{ae,premiere,illustrator,photoshop}` | 앱 넷을 표 한 줄로. 시간 초과면 모달 글자+그림을 먼저 찍고 죽인다. 성공은 잡이 쓴 `판정:` 줄 |")
    a("| 판정 모델 | `tools/jev` · `tools/radar.py --jev` | TypeSafe Jev — 거르기·분류에 조건부 채택(decision 37). 셈·순위엔 안 쓴다 |")
    a("")
    a("## 기술 스택")
    a("")
    a("| 영역 | 무엇 |")
    a("|---|---|")
    for k, v in STACK:
        a(f"| {k} | {v} |")
    a("")
    a("---")
    a("")

    # ── 뚫어낸 벽 ─────────────────────────────────────────
    a("## 뚫어낸 벽")
    a("")
    a(f"{n_wall}개 전부는 `SELECT * FROM constraint_note;` 와 [WORKLOG](log/WORKLOG.md#환경이-거는-제약). "
      "아래는 **다음 사람이 또 밟을** 것들입니다.")
    a("")
    a("| # | 벽 | 뚫은 법 |")
    a("|---|---|---|")
    rows = {r[0]: r for r in q("SELECT rowid,topic,limit_value,workaround FROM constraint_note")}
    for rid in HARD_WALLS:
        if rid in rows:
            _, topic, lim, work = rows[rid]
            a(f"| {rid} | {short(topic, 70)} | {short(work, 110)} |")
    a("")
    a("---")
    a("")

    # ── 운영 정보 (접음) ──────────────────────────────────
    a("## 운영 정보")
    a("")
    a(f"<details><summary><b>지금 ({today})</b> — 방향 · 세션 넷 · 열린 일</summary>")
    a("")
    a("**차트명가New 는 김직선 카피캣입니다** (decision 39, 2026-09-28). 비주얼·디자인은 B 가 김직선 영상에서 규격을 재고, "
      "대본은 E 가 회사 원고(Pool)에서 정보를·김직선에서 말투를 가져와 조립하고, 차트 장면은 D 가 MT5 에서 찍습니다. "
      "`brand/STYLE.md`·룰북·`thumbnail_rule` 은 **옛 차트명가** 실측이라 New 의 기준이 아닙니다.")
    a("")
    a("| 세션 | 어디서 | 브랜치 | 맡은 것 |")
    a("|---|---|---|---|")
    for s in SESSIONS:
        a(f"| {s[0]} | {s[1]} | {s[2]} | {s[3]} |")
    a("")
    a("옆가지는 본류에 push 하지 않고 총괄이 병합합니다(runbook 23). 자격증명은 이정찬 터미널에서만 다룹니다(decision 32). "
      "저장소는 public — 대본 원문·타 채널 자막·docx 는 저장소 밖입니다(decision 38).")
    a("")
    a("| # | 열린 일 | 누가 |")
    a("|---|---|---|")
    for seq, item, who in q("SELECT seq,item,blocked_by FROM next_step"
                            " WHERE seq >= 45 AND blocked_by NOT LIKE '완료%' ORDER BY seq"):
        a(f"| {seq} | {short(item, 90)} | {short(who, 40)} |")
    a("")
    a("</details>")
    a("")
    a("<details><summary><b>공용 장치</b> — 세이브 · 가드 · 레이더 · 래칫 · 인박스</summary>")
    a("")
    a("| 장치 | 무엇 | 어디 |")
    a("|---|---|---|")
    a("| 세이브 | `python3 log/save.py \"한 줄\"` — DB·WORKLOG·README 재빌드 + 커밋 + 현재 브랜치 푸시. 옆가지는 `--only <경로>` 범위 필수 | `log/save.py` · runbook 23 |")
    a("| 가드 | 본류 push(총괄만)·브랜치 없는 push·`git add -A`·작업 폴더 이동(`prlinks` 검사 뒤에만)·역슬래시 heredoc 을 막는다 | `.claude/hooks/git_guard.py` · `.claude/settings.json` |")
    a("| 레이더 | 오류 문구 → 우리 기록(issue·constraint·TRAPS) → Stack Overflow → GitHub. `--jev` 면 우리 벽 중 상위 3 | `tools/radar.py` · `.claude/skills/radar` |")
    a("| 래칫 시험 | 절대 경로 리터럴·판정 줄 없는 잡·장면 탐색 미끼·모달 표 — 늘어나면 깨진다 | `tests/` |")
    a("| 인박스 | 세션 간 제안·회신·보고는 `log/inbox/YYYY-MM-DD_<누가>_<제목>.md`. 총괄이 등재하고 번호를 준다 | decision 24 |")
    a(f"| 절차 | runbook {n_run}개 — `SELECT * FROM runbook;` | DB |")
    a("")
    a("```bash")
    a("git config ac.role 총괄            # 총괄 컨테이너 첫 명령 (옆가지는 안 함)")
    a('python3 log/save.py "어디까지 했는지 한 줄"   # 세이브')
    a("python3 log/save.py --list                    # 되돌릴 수 있는 시점")
    a('python3 tools/radar.py "<오류 붙여넣기>" --jev  # 벽에 두 번째 부딪혔을 때')
    a("python3 -m pytest -q && ruff check --select F,E9 .   # 병합 전 검사")
    a("```")
    a("")
    a("</details>")
    a("")
    a("<details><summary><b>네 단계 중 어디를 코드가 하나</b> — 롱폼·숏폼 규격</summary>")
    a("")
    a("| 포맷 | 단계 | 담당 | 상태 | 무엇 |")
    a("|---|---|---|---|---|")
    for fmt, seq, name, owner, in_repo, status, detail, note in stages:
        num = seq if "." in seq else f"{seq}."
        a(f"| {fmt} | {num} {name} | {owner} | {MARK[status]} {status} | {short(detail, 110)} |")
    a("")
    a("> 🟢 진행중 · 🔵 결과물만 저장소에 있음 · ⚪ 미착수 · ➖ 저장소가 관여 안 함")
    a("")
    a("| | 화면비 | 채널 최종본 | 우리가 납품 | 길이 | 톤앤매너 |")
    a("|---|---|---|---|---|---|")
    for name, aspect, final, src, length, tone, status in fmts:
        a(f"| **{name}** | {aspect} | {final} | {src} | {length} | {tone} |")
    a("")
    a("</details>")
    a("")
    ready = sum(1 for r in q("SELECT status FROM workflow_step WHERE format='롱폼'") if r[0] == "ready")
    total = one("SELECT COUNT(*) FROM workflow_step WHERE format='롱폼'")
    a("<details><summary><b>렌더러 (롱폼 3단계 · 총괄)</b> — "
      f"절차 {ready}/{total} 자동화 · {secs:.2f}초 클립 = 순차 {ser:.1f}초</summary>")
    a("")
    a(f"최근 납품 20일선 눌림목 / 조기 익절 {n_cut}컷 {n_frames}프레임 · "
      f"렌더 실측 {secs:.2f}초 클립 = 순차 {ser:.1f}초 (`--preset medium` {med:.1f}초)")
    a("")
    a("```bash")
    a("npm install && npm run setup:fonts       # 리눅스만 폰트 등록")
    a("npm run render -- --config scenes/cmg12-bridge.scenes.js --all --stills 5   # 구도 먼저")
    a("npm run render -- --config scenes/cmg12-bridge.scenes.js --all              # 렌더. 순차면 충분")
    a("```")
    a("")
    a("| 단계 | 방법 | 담당 |")
    a("|---|---|---|")
    for seq, step, how, who, st in q(
            "SELECT seq,step,how,who,status FROM workflow_step WHERE format='롱폼' ORDER BY seq"):
        mk = "✅" if st == "ready" else ("🟡" if st == "partial" else "⬜")
        a(f"| {mk} {seq}. {step} | {short(how, 80)} | {who} |")
    a("")
    a("| 갖춰 놓은 것 | 수 | 쓰임 |")
    a("|---|---:|---|")
    a(f"| 대본 인덱스 | {n_doc}편 | 새 대본과 겹치는 회차를 전문 검색으로 (차명14·15 {n_empty}편은 빈 템플릿) |")
    a(f"| 회차 프리미어 파일 | {n_prj}건 | 레퍼런스 확인 (`.prproj` 를 gunzip 해 직접 읽는다) |")
    a(f"| 브랜드 실측값 | {n_tok}건 | 옛 차트명가 색·크기 — New 기준은 next_step 55 에서 다시 잰다 |")
    a(f"| 레이어 | {n_lay}종 | 컷을 짤 때 쓰는 재료 (`layer_catalog`) |")
    a(f"| 회사 모션 문법 | {n_mot}종 | 최종본 키프레임에서 뽑은 프레임 수·이징 |")
    a("")
    a("</details>")
    a("")
    a("<details><summary><b>숏폼 대본을 뽑는 규칙</b> (E · tools/shortform.py)</summary>")
    a("")
    a("나간 숏폼 25편과 원본 롱폼 13편을 맞춰 보고 역으로 구한 것입니다. "
      "핵심은 **복붙이 아니라 다시 쓴다** — 10자 n-gram 겹침이 중앙값 2.2%뿐입니다.")
    a("")
    a("```")
    a("롱폼 한 편 (약 4,000자)")
    a("   ├─ 챕터 하나를 고른다     ← #1 은 앞쪽, #2 는 뒤쪽 (12쌍 중 11쌍)")
    a("   └─ 45초 = 307자로 다시 쓴다  ← 초당 6.82자, 자막 13편 실측")
    a("")
    a("        ① 훅    오늘은 …를 알려드릴게요       26자 / 3.6초   고정")
    a("        ② 근거  통념 → 하지만 → 손실")
    a("        ③ 본론  기준·설정값·순서를 숫자로      255자 / 39초   여기서 조절")
    a("        ④ CTA   질문으로 넘김 + 고정 3줄      26자 / 2.7초   고정")
    a("                → 이 질문이 다음 편의 주제가 된다")
    a("```")
    a("")
    a("| 등급 | 규칙 | 기존 |")
    a("|---|---|---|")
    for grp, rule, hits, tot, tier in q(
            "SELECT grp,rule,hits,total,tier FROM shortform_rule"
            " WHERE tier IN ('필수','권장') AND grp<>'포인트' ORDER BY id"):
        cnt = f"{hits}/{tot}편" if hits else "—"
        a(f"| {tier} | {rule} | {cnt} |")
    a("")
    n_pt = one("SELECT COUNT(*) FROM shortform_rule WHERE grp='포인트'")
    a(f"5개를 모두 지킨 편은 2편뿐이라 **경향에 가깝습니다 — 권장은 어겨도 됩니다.** "
      f"`포인트_차` 갈래는 별도(규칙 {n_pt}개, `WHERE grp='포인트'`). 상세는 [log/SCRIPT-LAB.md](log/SCRIPT-LAB.md).")
    a("")
    a("```bash")
    a("python3 tools/shortform.py chapters 11                      # 롱폼 챕터 보기")
    a("python3 tools/shortform.py brief 11 --chapter '전략 1' --no 4  # 작성 지시서")
    a("python3 tools/shortform.py name 11 --no 4 --title '제목'      # 이름 짓기")
    a("python3 tools/shortform.py check 초안.txt                    # 규칙 + 이름 검사")
    a("```")
    a("")
    a("</details>")
    a("")
    a("<details><summary><b>되돌리기</b> — 최근 세이브 슬롯</summary>")
    a("")
    a("작업 한 덩어리마다 세이브 슬롯을 만듭니다. 태그 푸시는 403 이라 슬롯·해시 짝을 `log/data/checkpoints.json` 에 적습니다.")
    a("")
    a("```bash")
    a("python3 log/save.py --list                    # 슬롯 목록")
    a("git restore --source=<해시> -- .              # 되돌리기 (그 뒤 다시 save)")
    a("```")
    a("")
    a("| 시각 (KST) | 슬롯 | 커밋 | 어디까지 |")
    a("|---|---|---|---|")
    for kst, tag, sha, sm in q("SELECT kst,tag,sha,summary FROM checkpoint ORDER BY id DESC LIMIT 8"):
        a(f"| {kst} | `{tag}` | `{sha or '-'}` | {short(sm, 100)} |")
    a("")
    a("</details>")
    a("")
    n_rf = one("SELECT COUNT(*) FROM repo_file WHERE role NOT IN ('기타')")
    a(f"<details><summary><b>어디에 무엇이 있나</b> — {n_rf}개 (`SELECT * FROM repo_file;`)</summary>")
    a("")
    a("| 경로 | 역할 |")
    a("|---|---|")
    for path, role, note in q(
            "SELECT path,role,note FROM repo_file WHERE role NOT IN ('기타') ORDER BY path"):
        a(f"| `{path}` | {note or role} |")
    a("")
    a("</details>")
    a("")
    a("## 컨텍스트가 날아갔을 때")
    a("")
    a("`log/worklog.db` 한 파일에 전부 들어 있습니다. `CLAUDE.md` 를 먼저 읽고, 그다음 이 순서입니다.")
    a("")
    a("```sql")
    for ord_, step, detail in q("SELECT ord,step,detail FROM v_start_here"):
        a(f"-- {ord_}. {step}")
    a("SELECT * FROM v_start_here;   -- 이 순서대로")
    a("SELECT * FROM v_scope;        -- 파이프라인 어디를 맡는가")
    a("SELECT * FROM next_step WHERE seq >= 45;   -- 지금 열린 일")
    a("SELECT * FROM runbook;        -- 명령어")
    a("SELECT * FROM constraint_note;-- 이미 부딪혀 본 벽")
    a("SELECT * FROM issue ORDER BY seq DESC;     -- 사고와 고친 법")
    a("```")
    a("")
    a("<sub>이 문서는 `log/worklog.db` 에서 자동 생성됩니다 — `python3 log/build_readme.py`. "
      "직접 고치지 말고 `log/build_worklog_db.py` 를 고치세요.</sub>")
    a("")
    return "\n".join(L)


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"README.md 생성 완료 ({OUT.stat().st_size / 1024:.0f} KB)")
