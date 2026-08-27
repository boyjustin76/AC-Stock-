#!/usr/bin/env python3
"""worklog.db → README.md (깃허브 첫 화면 대시보드).

깃허브 README 는 마크다운만 렌더한다. <style> 과 스크립트는 제거되므로
HTML 대시보드를 그대로 붙일 수 없다. 대신 깃허브가 실제로 그려 주는 것들
— mermaid 다이어그램, 배지, 표 — 로 같은 정보를 담는다.

    python3 log/build_readme.py
"""
from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "log" / "worklog.db"
OUT = ROOT / "README.md"
DASHBOARD = "https://claude.ai/code/artifact/cfb762d2-2caf-4a18-8ec2-696b884ac0e1"

MARK = {"진행중": "🟢", "자료만": "🔵", "미착수": "⚪", "해당없음": "➖"}


def badge(label: str, value: str, color: str) -> str:
    f = lambda t: quote(t.replace("-", "--").replace("_", "__"), safe="")
    return f"![{label}](https://img.shields.io/badge/{f(label)}-{f(value)}-{color}?style=flat-square)"


def bar(done: int, total: int, width: int = 12) -> str:
    n = round(done / total * width) if total else 0
    return "█" * n + "░" * (width - n)


def build() -> str:
    con = sqlite3.connect(DB)
    q = lambda s: con.execute(s).fetchall()
    one = lambda s: con.execute(s).fetchone()[0]

    stages = q("SELECT p.format,p.seq,p.name,p.owner,p.in_repo,p.status,p.detail,p.note"
               " FROM pipeline_stage p JOIN format f ON f.name = p.format"
               " ORDER BY f.id, p.id")
    fmts = q("SELECT name,aspect,final_spec,source_spec,length,tone,status FROM format ORDER BY id")

    n_cut = one("SELECT COUNT(*) FROM scene WHERE config LIKE '%cmg%'")
    n_frames = one("SELECT SUM(frames) FROM scene WHERE config LIKE '%cmg%'")
    n_doc = one("SELECT COUNT(DISTINCT ep) FROM script_doc WHERE status='작성됨'")
    n_empty = one("SELECT COUNT(DISTINCT ep) FROM script_doc WHERE status<>'작성됨'")
    n_prj = one("SELECT COUNT(*) FROM episode_prproj")
    n_tok = one("SELECT COUNT(*) FROM brand_token")
    n_lay = one("SELECT COUNT(*) FROM layer_catalog")
    n_mot = one("SELECT COUNT(*) FROM motion_preset")
    ser, par = q("SELECT wall_seconds FROM benchmark ORDER BY id")[0][0], \
        q("SELECT wall_seconds FROM benchmark ORDER BY id")[1][0]
    secs = one("SELECT seconds_video FROM benchmark LIMIT 1")

    L = []
    a = L.append

    a("# 차트 컷씬 렌더러")
    a("")
    a("해외선물 유튜브 채널 **차트명가** 영상에 쓸 차트 모션그래픽 소스 영상을 코드로 렌더합니다.")
    a("")
    a(" ".join([
        badge("범위", "롱폼 3단계", "0B8C7F"),
        badge("규격", "1920x1080 · 59.94fps", "555"),
        badge("렌더", f"{secs:.0f}초 클립 = {par:.0f}초", "555"),
        badge("대본 인덱스", f"{n_doc}편", "555"),
        badge("레이어", f"{n_lay}종", "555"),
    ]))
    a("")
    a(f"📊 **[작업 로그 대시보드]({DASHBOARD})** · "
      f"[전체 기록](log/WORKLOG.md) · [새 세션 안내](CLAUDE.md)")
    a("")
    a("---")
    a("")

    # ── 범위 ───────────────────────────────────────────────
    a("## 이 저장소가 맡는 곳")
    a("")
    a("영상 한 편은 네 단계를 거칩니다. **이 저장소는 그중 3단계 하나만** 합니다.")
    a("나머지는 사람이 프리미어에서 합니다.")
    a("")
    a("```mermaid")
    a("flowchart LR")
    a('  subgraph L ["롱폼 — 작업중"]')
    a("    direction LR")
    a('    L1["1. 대본 만들기<br/><small>사람</small>"]')
    a('    L15["1.5 성우 녹음<br/><small>외부</small>"]')
    a('    L2["2. 컷편집 · 자막<br/><small>사람 · 프리미어</small>"]')
    a('    L3["<b>3. 모션그래픽 · 소스</b><br/><small>이 저장소</small>"]')
    a("    L1 --> L15 --> L2 --> L3")
    a("  end")
    a('  subgraph S ["숏폼 — 미착수"]')
    a("    direction LR")
    a('    S1["1. 대본"] --> S15["1.5 녹음"] --> S2["2. 컷편집 · 자막"] --> S3["3. 모션그래픽 · 소스"]')
    a("  end")
    a("  L3 -.->|납품| P[[프리미어 타임라인]]")
    a("  classDef here fill:#0B8C7F,stroke:#0B8C7F,color:#fff,font-weight:bold")
    a("  classDef human fill:#F2F2F2,stroke:#C9C9C9,color:#444")
    a("  classDef idle fill:#FAFAFA,stroke:#E2E2E2,color:#9A9A9A,stroke-dasharray:3 3")
    a("  class L3 here")
    a("  class L1,L15,L2,P human")
    a("  class S1,S15,S2,S3 idle")
    a("```")
    a("")
    a("| 포맷 | 단계 | 담당 | 상태 | |")
    a("|---|---|---|---|---|")
    for fmt, seq, name, owner, in_repo, status, detail, note in stages:
        here = "**← 여기**" if in_repo and status == "진행중" else ""
        num = seq if "." in seq else f"{seq}."
        a(f"| {fmt} | {num} {name} | {owner} | {MARK[status]} {status} | {here} |")
    a("")
    a("> 🟢 진행중 · 🔵 결과물만 저장소에 있음 · ⚪ 미착수 · ➖ 저장소가 관여 안 함")
    a("")
    a("**3단계가 받는 것**은 타임코드가 붙은 대본(2단계 산출물), "
      "**내놓는 것**은 차트만 있는 영상 클립입니다. "
      "자막·타이틀·로고는 2단계에서 이미 들어가므로 렌더에 넣지 않습니다.")
    a("")

    # ── 포맷 ───────────────────────────────────────────────
    a("## 롱폼과 숏폼")
    a("")
    a("| | 화면비 | 채널 최종본 | 우리가 납품 | 길이 | 톤앤매너 |")
    a("|---|---|---|---|---|---|")
    for name, aspect, final, src, length, tone, status in fmts:
        a(f"| **{name}** | {aspect} | {final} | {src} | {length} | {tone} |")
    a("")
    a("숏폼은 세로 프레임이라 차트 레이아웃을 다시 잡아야 합니다. "
      "렌더러는 그대로 쓰되 `layout`·`visibleBars` 부터 새로 정해야 하고, "
      "그 전에 최종본 숏츠를 실측해 톤앤매너를 잡는 것이 먼저입니다.")
    a("")
    a("---")
    a("")

    # ── 현황 ───────────────────────────────────────────────
    a("## 현황")
    a("")
    ready = sum(1 for r in q("SELECT status FROM workflow_step WHERE format='롱폼'") if r[0] == "ready")
    total = one("SELECT COUNT(*) FROM workflow_step WHERE format='롱폼'")
    a(f"**롱폼 3단계 내부 절차** `{bar(ready, total)}` {ready}/{total} 자동화")
    a("")
    a("| 단계 | 방법 | 담당 |")
    a("|---|---|---|")
    for seq, step, how, who, st in q(
            "SELECT seq,step,how,who,status FROM workflow_step WHERE format='롱폼' ORDER BY seq"):
        mk = "✅" if st == "ready" else ("🟡" if st == "partial" else "⬜")
        a(f"| {mk} {seq}. {step} | {how[:70]}{'…' if len(how) > 70 else ''} | {who} |")
    a("")
    a("| 갖춰 놓은 것 | 수 | 쓰임 |")
    a("|---|---:|---|")
    a(f"| 대본 인덱스 | {n_doc}편 | 새 대본과 겹치는 회차를 전문 검색으로 찾는다"
      f" (차명14·15 {n_empty}편은 아직 빈 템플릿) |")
    a(f"| 회차 프리미어 파일 | {n_prj}건 | 레퍼런스 확인 (`.prproj` 를 직접 읽는다) |")
    a(f"| 브랜드 실측값 | {n_tok}건 | 색·크기. 레퍼런스 프레임에서 픽셀 단위로 잰 값 |")
    a(f"| 레이어 | {n_lay}종 | 컷을 짤 때 쓰는 재료 |")
    a(f"| 회사 모션 문법 | {n_mot}종 | 최종본 키프레임에서 뽑은 프레임 수·이징 |")
    a("")
    a(f"**최근 납품** — 20일선 눌림목 / 조기 익절 {n_cut}컷, "
      f"{n_frames}프레임 · 1920×1080 · 59.94fps  \n"
      f"**렌더 실측** — {secs:.2f}초 클립 기준 순차 {ser:.0f}초, 컷별 병렬 {par:.0f}초 (4코어)")
    a("")
    a("---")
    a("")

    # ── 명령 ───────────────────────────────────────────────
    a("## 빠른 시작")
    a("")
    a("```bash")
    a("npm install")
    a("npm run setup:fonts                        # 리눅스만. 폰트 등록")
    a("npm run render -- --config scenes/cmg-20ma-runner.scenes.js --all --stills 5")
    a("npm run render -- --config scenes/cmg-20ma-runner.scenes.js --all")
    a("```")
    a("")
    a("컷별로 쪼개 동시에 돌리면 절반 시간에 끝납니다. 결과물은 순차 렌더와 md5 까지 같습니다.")
    a("")
    a("```bash")
    a("for c in cut1-pullback-entry cut2-profit-runs cut3-fear cut4-early-exit; do")
    a("  node src/cli.mjs --config scenes/cmg-20ma-runner.scenes.js --scene $c --out out/cmg &")
    a("done; wait")
    a("```")
    a("")
    a("## 되돌리기")
    a("")
    a("작업 한 덩어리마다 세이브 슬롯을 만듭니다. 슬롯 하나가 그 시점의 저장소 전체입니다.")
    a("")
    a("```bash")
    a('python3 log/save.py "어디까지 했는지 한 줄"   # 세이브')
    a("python3 log/save.py --list                    # 슬롯 목록")
    a("git restore --source=<해시> -- .              # 되돌리기")
    a("```")
    a("")
    a("| 시각 (KST) | 슬롯 | 커밋 | 어디까지 |")
    a("|---|---|---|---|")
    for kst, tag, sha, sm in q("SELECT kst,tag,sha,summary FROM checkpoint ORDER BY id DESC LIMIT 6"):
        a(f"| {kst} | `{tag}` | `{sha or '-'}` | {sm} |")
    a("")
    a("---")
    a("")

    # ── 구조 ───────────────────────────────────────────────
    a("## 어디에 무엇이 있나")
    a("")
    a("| 경로 | 역할 |")
    a("|---|---|")
    for path, role, note in q(
            "SELECT path,role,note FROM repo_file WHERE role NOT IN ('기타') ORDER BY path"):
        a(f"| `{path}` | {note or role} |")
    a("")
    a("## 컨텍스트가 날아갔을 때")
    a("")
    a("`log/worklog.db` 한 파일에 전부 들어 있습니다. 순서대로 읽으면 됩니다.")
    a("")
    a("```sql")
    for ord_, step, detail in q("SELECT ord,step,detail FROM v_start_here"):
        a(f"-- {ord_}. {step}")
    a("SELECT * FROM v_start_here;   -- 이 순서대로")
    a("SELECT * FROM v_scope;        -- 파이프라인 어디를 맡는가")
    a("SELECT * FROM runbook;        -- 명령어")
    a("SELECT * FROM constraint_note;-- 이미 부딪혀 본 벽")
    a("```")
    a("")
    a("<sub>이 문서는 `log/worklog.db` 에서 자동 생성됩니다 — `python3 log/build_readme.py`. "
      "직접 고치지 말고 DB 를 고치세요.</sub>")
    a("")
    return "\n".join(L)


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"README.md 생성 완료 ({OUT.stat().st_size / 1024:.0f} KB)")
