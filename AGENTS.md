# AGENTS.md — Claude Code 가 아닌 에이전트(Codex 등)가 이 저장소에서 일할 때

**먼저 `CLAUDE.md` 를 읽는다.** 그 파일이 이 저장소의 본문이다(범위·기록 원본·세이브·기억할 것).
이 파일은 Claude Code 바깥 도구를 위한 **차이점**만 적는다.

## 1. 자동으로 안 걸리는 것 — 그러니 지켜야 한다

Claude Code 는 `.claude/settings.json` 의 훅(`.claude/hooks/git_guard.py`)이 아래를 **막아 준다**. 다른 에이전트에는 훅이 없다. 스스로 지킨다.

| 규칙 | 왜 |
|---|---|
| **본류 `claude/futures-youtube-video-edit-fhio4s` 에 push 하지 않는다.** 자기 가지 `worktree-<이름>` 에만 올린다. 병합은 총괄(클라우드 세션)이 한다 | 세션 넷이 한 저장소를 쓴다 (runbook 23) |
| **브랜치 이름 없는 `git push` 를 치지 않는다.** 항상 `git push origin worktree-<이름>` | upstream 이 본류면 본류로 간다 |
| **`git add -A` · `git add .` · `git commit -a` 를 치지 않는다.** `python log/save.py "한 줄" --only <내 경로…>` 또는 `git add -- <경로>` | 남의 작업이 딸려 간다 (issue 24) |
| **작업 폴더(이정찬·차트명가·aelab·cmgwork·pprolab·납품·더원)를 옮기거나 지우기 전에** `python tools/cutedit/prlinks.py find "<경로조각>" "<검색 루트>"` | 프리미어 프로젝트가 경로를 문다 (issue 20·26) |
| `log/build_worklog_db.py` · `log/worklog.db` 는 **총괄만** 고친다. 기록할 것은 `log/inbox/YYYY-MM-DD_<세션>_<주제>.md` 에 원자료로 | decision 24 |
| 키·토큰은 `C:\Users\user\.secrets\ac_keys.env` 에서 읽는다. 저장소(public)·꾸러미 zip 에 넣지 않는다 | decision 32 |

`log/save.py` 는 현재 브랜치로만 민다(본류는 `git config ac.role 총괄` 인 clone 만). 그래서 옆가지에서는 그냥 돌려도 안전하다.

## 2. 환경 — 세션 폴더와 UTF-8

- 로컬 세션은 자기 worktree 폴더에서 띄운다: D `…\03_저장소\worktrees\D_Video` · B `…\worktrees\B_Image` · E `…\01_저장소\E_Script` (runbook 24·25).
- Claude Code 는 `.claude/settings.json` 의 `env` 로 `PYTHONUTF8=1 · PYTHONIOENCODING=utf-8` 을 받는다. 다른 도구는 **셸에서 직접** 건다 — 안 걸면 한글·특수문자 출력에서 cp949 로 죽는다 (constraint_note 39).
- `.claude/skills/radar/SKILL.md` 는 Claude 전용 지침이다. 내용은 도구 하나 — 같은 오류 두 번째면 `python tools/radar.py "<오류 붙여넣기>"` 로 우리 기록·Stack Overflow·GitHub 를 먼저 본다.

## 3. 어디부터 읽나

1. `CLAUDE.md` → `log/WORKLOG.md`(또는 `sqlite3 log/worklog.db` 로 `SELECT * FROM v_start_here;`)
2. 자기 파트 인수인계: D 영상 `log/inbox/2026-09-18_D_아스트라_인수인계.md` (이 PC 경로 지도·남은 일·함정 11) · E 대본 `tools/theone/README.md` · `log/SCRIPT-AGENT-MANUAL.md` · B 이미지 `tools/photoshop/README.md` · `log/LIVE-SCREEN-MANUAL.md`
3. 벽에 부딪히면 `SELECT * FROM constraint_note;` — 이미 넘은 벽 60개 남짓.

## 4. 검사

```bash
python -m pytest              # 단위 시험
python -m ruff check tools log tests --select F,E9    # 진짜 버그급만 (pyproject.toml)
```
커밋 메시지 끝의 `Co-Authored-By:` 줄은 각 도구의 관행대로. 세션 링크가 있으면 붙인다.
