#!/usr/bin/env python3
"""worklog.db → README.md (깃허브 첫 화면).

깃허브 README 는 마크다운만 렌더한다. <style> 과 스크립트는 제거되므로
HTML 대시보드를 그대로 붙일 수 없다. 대신 깃허브가 실제로 그려 주는 것들
— mermaid 다이어그램, 배지, 표, <details> — 로 같은 정보를 담는다.

2026-10-03 전면 개정: 저장소가 렌더러 하나에서 세션 넷(총괄·B·D·E)의 제작 체계로 바뀐 뒤
첫 화면이 초기 버전 그대로였다(이정찬). 위부터 '지금 → 누가 무엇을 → 어떻게 돌아가나 →
뚫어낸 벽 → 장치' 순으로 두고, 렌더러 전용 절은 아래로 내려 접는다.

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
    n_commit = one("SELECT COUNT(*) FROM commit_log")
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
    today = date.today().isoformat()

    L = []
    a = L.append

    # ── 머리 ───────────────────────────────────────────────
    a("# 차트명가 제작 자동화")
    a("")
    a("해외선물 유튜브 채널 **차트명가**(파가드AC) 영상 제작을 코드로 돕습니다. "
      "대본 → 컷편집·자막 → 차트 촬영·렌더 → 어도비 자동화 → 납품까지, "
      "**클로드 세션 넷이 한 저장소에서 일합니다.** 2026-08-26 렌더러 하나로 시작해 09-17 부터 세션 넷 체계입니다.")
    a("")
    a(" ".join([
        badge("세션", "총괄 + B·D·E", "0B8C7F"),
        badge("뚫은 벽", f"{n_wall}", "555"),
        badge("사고", f"{n_issue} (고침 {n_fixed})", "555"),
        badge("결정", f"{n_dec}", "555"),
        badge("시험", f"{n_tests()}", "555"),
        badge("커밋", f"{n_commit}", "555"),
    ]))
    a("")
    a(f"📊 **[작업 로그 대시보드]({DASHBOARD})** · "
      f"[전체 기록](log/WORKLOG.md) · [새 세션 안내](CLAUDE.md) · "
      f"[뚫은 벽 전부](log/WORKLOG.md#환경이-거는-제약) · [사고 전부](log/WORKLOG.md#문제와-해결)")
    a("")
    a(f"<sub>마지막 세이브 {last_kst} KST · 이 문서는 `log/worklog.db` 에서 자동 생성 (`python3 log/build_readme.py`) · "
      f"직접 고치지 말고 `log/build_worklog_db.py` 를 고치세요</sub>")
    a("")
    a("---")
    a("")

    # ── 지금 ───────────────────────────────────────────────
    a(f"## 지금 ({today})")
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
    a("**이정찬**(팀원·컷편집)이 세션 사이에서 인박스 파일(`log/inbox/`)을 나릅니다. 옆가지는 본류에 push 하지 않고 총괄이 병합합니다(runbook 23). "
      "자격증명은 이정찬 터미널에서만 다룹니다(decision 32). 저장소는 public — 대본 원문·타 채널 자막·docx 는 저장소 밖입니다(decision 38).")
    a("")
    a("**열린 일** (`SELECT * FROM next_step WHERE seq >= 45;`)")
    a("")
    a("| # | 무엇 | 누가 |")
    a("|---|---|---|")
    for seq, item, who in q("SELECT seq,item,blocked_by FROM next_step"
                            " WHERE seq >= 45 AND blocked_by NOT LIKE '완료%' ORDER BY seq"):
        a(f"| {seq} | {short(item, 90)} | {short(who, 40)} |")
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
    a("| 묶음 | 어디 | 한 줄 |")
    a("|---|---|---|")
    a("| 대본 | `data/대본자료/도구` · `tools/theone` · `log/SCRIPT-LAB.md` | 뼈대의 조각 출처를 Pool 원문에 대고 기계로 대조(`pool_pieces`), 회사 기본폼 .docx(`skeleton_docx`), 관문 12개(`pipeline.py`) |")
    a("| 컷편집·자막 | `tools/cutedit` · runbook 18·26 | L08(09-11)·마01(10-01) 롱폼 합본. 자막 큐는 형태소 태그로 가름(`ko_clause`), XML 은 프리미어 표기(`make_xml`) |")
    a("| 차트 장면 | `tools/mt5` · `tools/ae/jobs/d1_conti_build.jsx` | 대본 한 편 → 12~35장 자동 촬영(`batch_capture`) → 콘티 → AE. 장면마다 전용 함수 + 심은 시험. 리플레이 도구로 전문가가 직접 진행 |")
    a("| 렌더러 | `src/render` · `scenes/` · `brand/` | 차12 계열(`cmg12-*`)이 최신 문법. `--stills` 로 구도 먼저 |")
    a("| 어도비 자동화 | `tools/_com/run.ps1` · `tools/{ae,premiere,illustrator,photoshop}` | 앱 넷을 표 한 줄로. 시간 초과면 모달 글자+그림을 먼저 찍고 죽인다. 성공은 잡이 쓴 `판정:` 줄 |")
    a("| 판정 모델 | `tools/jev` · `tools/radar.py --jev` | TypeSafe Jev — 거르기·분류에 조건부 채택(decision 37). 셈·순위엔 안 쓴다 |")
    a("")
    a("---")
    a("")

    # ── 뚫어낸 벽 ─────────────────────────────────────────
    a("## 뚫어낸 벽")
    a("")
    a(f"{n_wall}개 전부는 `SELECT * FROM constraint_note;` 와 [WORKLOG](log/WORKLOG.md#환경이-거는-제약). "
      "아래는 **다음 사람이 또 밟을** 것들입니다. 전부 실측이고, 짐작으로 적은 건 없습니다.")
    a("")
    a("| # | 벽 | 뚫은 법 |")
    a("|---|---|---|")
    rows = {r[0]: r for r in q("SELECT rowid,topic,limit_value,workaround FROM constraint_note")}
    for rid in HARD_WALLS:
        if rid in rows:
            _, topic, lim, work = rows[rid]
            a(f"| {rid} | {short(topic, 70)} | {short(work, 110)} |")
    a("")
    a("**사고에서 배운 절차** (decision 33·40)")
    a("")
    a("- 완료 보고에는 `확인한 것 / 안 본 것` 두 줄 — 사고 여덟 건이 '일부를 보고 전체를 판단' 이었다 (`log/inbox/_완료보고_양식.md`)")
    a("- 막혔을 때: ① 입력 구조를 **세어서** 확인 ② 산출물은 **원본과 맞대야** 완료 ③ 안 되면 **성공본과 실패본을 맞댄다** ④ 재현은 자동화한다")
    a("- 기록에 없는 결정은 추론하지 않고 이정찬에게 묻는다. 번호 없는 '…하지 않는다' 는 지시가 아니라 메모다 (issue 48)")
    a("- 결과를 믿지 말고 다시 읽는다 — 지표 3개를 켜라 했는데 1개만 켜지고 오류가 없었다 (constraint 60 ⑧)")
    a("")
    a("---")
    a("")

    # ── 장치 ───────────────────────────────────────────────
    a("## 공용 장치")
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
    a("---")
    a("")

    # ── 범위 ───────────────────────────────────────────────
    a("## 네 단계 중 어디를 코드가 하나")
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
    a("---")
    a("")

    # ── 렌더러 ─────────────────────────────────────────────
    a("## 렌더러 (롱폼 3단계 · 총괄)")
    a("")
    ready = sum(1 for r in q("SELECT status FROM workflow_step WHERE format='롱폼'") if r[0] == "ready")
    total = one("SELECT COUNT(*) FROM workflow_step WHERE format='롱폼'")
    a(f"내부 절차 `{bar(ready, total)}` {ready}/{total} 자동화 · "
      f"최근 납품 20일선 눌림목 / 조기 익절 {n_cut}컷 {n_frames}프레임 · "
      f"렌더 실측 {secs:.2f}초 클립 = 순차 {ser:.1f}초 (`--preset medium` {med:.1f}초)")
    a("")
    a("```bash")
    a("npm install && npm run setup:fonts       # 리눅스만 폰트 등록")
    a("npm run render -- --config scenes/cmg12-bridge.scenes.js --all --stills 5   # 구도 먼저")
    a("npm run render -- --config scenes/cmg12-bridge.scenes.js --all              # 렌더. 순차면 충분")
    a("```")
    a("")
    a("<details><summary>내부 절차 9단계 · 갖춰 놓은 것</summary>")
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
    a("---")
    a("")

    # ── 숏폼 대본 규칙 ─────────────────────────────────────
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

    # ── 되돌리기 ───────────────────────────────────────────
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

    # ── 구조 ───────────────────────────────────────────────
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
