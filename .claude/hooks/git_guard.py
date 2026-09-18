#!/usr/bin/env python3
"""Claude Code PreToolUse 훅 — 위험한 git·이동 명령을 실행 전에 막는다.

D 가 로컬(~/.claude/hooks/hookify_reason.py)에서 쓰던 규칙 3개를 저장소로 옮긴 것이다.
저장소에 있어야 총괄·B·D·E 가 같은 규칙을 받는다 (공식 hooks 문서: 프로젝트 .claude/settings.json).
아직 **연결돼 있지 않다** — 켜는 법은 log/inbox 의 작업체계 제안서 §3. 켜면 아래 JSON 을
.claude/settings.json 의 "hooks" 에 넣는다 (Windows 는 python 이름이 다르니 exec form).

규칙
  4. heredoc-backslash  본문에 역슬래시가 든 heredoc — 따옴표 없는 <<EOF 는 어디서나, <<'EOF' 는 Windows 에서 막는다.
                       Write/Edit 도구로 파일을 쓰고 명령은 그 파일을 부른다 (constraint_note 38).
  1. mainline-push     본류(claude/futures-…, main, master)로 push 금지.
                       **브랜치 이름 없는 push(`git push`, `git push origin HEAD`)도 금지** — 어디로 가는지
                       명령에서 안 보이면 막고 이름을 쓰게 한다 (D 제안 09-17, 단순한 쪽).
                       총괄 clone 만 예외: `git config ac.role 총괄` 이 있으면 통과.
  2. whole-tree-stage  `git add -A` · `git add .` · `git commit -a` 금지 — 같은 작업트리를 나눠 쓰면
                       남의 파일이 딸려 간다(issue 24). `python3 log/save.py "…" --only <경로>` 를 쓴다.
                       (D 의 '커밋 전 git status' 규칙을 상태 없이 검사할 수 있는 형태로 바꿨다.)
  3. move-without-prlinks  **작업 폴더 이름이 든 경로**(PATH_HINTS: 이정찬·차트명가·aelab·cmgwork·pprolab·납품·더원)
                       를 mv / Move-Item / Rename-Item / robocopy /MOV 로 옮기거나
                       rm -r / Remove-Item -Recurse / rmdir / DeleteDirectory 로 지울 때는 60분 안에 prlinks find 를
                       돌린 표식(<저장소>/.claude/prlinks_find.ok)이 있어야 통과. 표식은
                       `python3 tools/cutedit/prlinks.py find …` 가 끝날 때 스스로 남긴다(E, ea36a4a). 경로 한정은 오탐(`mv scratch/a.png b.png`)을 막기 위한 것 —
                       D 로컬 규칙과 같다. 이름을 더 보태려면 환경변수 AC_GUARD_PATHS="이름1 이름2".
                       git mv 와 저장소 안 이동은 대상이 아니다. 지우기도 막는 이유: 09-16 에 지운 C:\aelab 등도
                       누가 무는지 봐야 했다 (D 회신 §2-B ④).

입력은 stdin JSON (tool_name · tool_input.command · cwd). 막을 때는 permissionDecision deny 와
이유를 같이 돌려준다 — 이유가 없으면 Claude 는 'denied' 만 보고 헤맨다 (issue 36).
판단 못 할 상황(입력 깨짐 등)은 **허용**한다 — 훅이 죽어서 일을 막는 쪽이 더 나쁘다.

시험:  python3 -m pytest tests/test_git_guard.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

MAINLINE = ("claude/futures-youtube-video-edit-fhio4s", "main", "master")
# 명령 머리(줄 시작 · ; & | ( 뒤)의 git 만 본다 — 따옴표 안 'git push' 를 grep 하는 명령은 대상이 아니다
GIT = r"(?:^|[;&|(]\s*)git(?:\s+-[cC]\s+\S+|\s+-C\s+\S+|\s+--git-dir=\S+|\s+--work-tree=\S+)*\s+"
RE_PUSH = re.compile(GIT + r"push\b(?P<rest>[^\n;&|]*)", re.M)
RE_STAGE_ALL = re.compile(GIT + r"add\b[^\n;&|]*?(?:\s-A\b|\s--all\b|\s\.(?:\s|$))", re.M)
RE_COMMIT_ALL = re.compile(GIT + r"commit\b[^\n;&|]*?\s(?:-a\b|--all\b|-am\b)", re.M)
# 줄 머리(^, MULTILINE)도 명령 시작으로 본다 — PowerShell 여러 줄 스크립트의 셋째 줄 Move-Item 을 놓쳤다 (D 시험 09-17)
RE_MOVE = re.compile(r"(?:^|[;&|]\s*)(?:mv|Move-Item|Rename-Item|mv\.exe)\s|robocopy\b[^\n]*\s/MOV\b", re.I | re.M)
RE_DELETE = re.compile(r"(?:^|[;&|]\s*)(?:rm\s+-[a-zA-Z]*r|rmdir\b|Remove-Item\b[^\n;&|]*-Recurse|rd\s+/s)|DeleteDirectory\s*\(", re.I | re.M)
PATH_HINTS = ("이정찬", "차트명가", "aelab", "cmgwork", "pprolab", "납품", "더원")   # 작업 폴더 이름 — 이게 든 경로만 본다
RE_GIT_MV = re.compile(GIT + r"mv\b", re.M)
# 4. heredoc 에 역슬래시가 들어가면 깨진다(constraint_note 38 — 세 세션이 다 밟았다). 따옴표 없는 <<EOF 는
#    bash 가 \\ 를 \ 로 줄이고, Windows 의 Bash 도구는 <<'EOF' 도 못 믿는다(E 실측). 막고 Write/Edit 로 보낸다.
RE_HEREDOC = re.compile(r"<<-?\s*(?P<q>['\"]?)(?P<d>[A-Za-z_][A-Za-z0-9_]*)(?P=q)[^\n]*\n(?P<body>.*?)\n\s*(?P=d)\s*(?:\n|$)", re.S)
MARK = ".claude/prlinks_find.ok"
MARK_TTL = 60 * 60


def _role(cwd: str) -> str:
    try:
        r = subprocess.run(["git", "-C", cwd, "config", "--get", "ac.role"],
                           capture_output=True, text=True, encoding="utf-8", timeout=5)
        return r.stdout.strip()
    except Exception:
        return ""


def _branch(cwd: str) -> str:
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, encoding="utf-8", timeout=5)
        return r.stdout.strip()
    except Exception:
        return ""


def _repo_root(cwd: str) -> str:
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, encoding="utf-8", timeout=5)
        return r.stdout.strip() or cwd
    except Exception:
        return cwd


def check(command: str, cwd: str = ".", *, now: float | None = None,
          role: str | None = None, branch: str | None = None, mark_mtime: float | None = None) -> str | None:
    """막아야 하면 이유(문자열), 아니면 None. 키워드 인자는 시험용 주입."""
    cmd = command or ""

    m = RE_PUSH.search(cmd)
    if m:
        role = _role(cwd) if role is None else role
        if role != "총괄":
            rest = m.group("rest")
            target = next((b for b in MAINLINE if re.search(re.escape(b) + r"(?:\s|$|:)", rest)), None)
            no_branch_arg = not re.search(r"\s[^\s-][^\s]*\s+[^\s-]", rest)
            if target:
                return (f"본류 '{target}' 로의 push 는 총괄만 한다. 옆가지(worktree-…)로 올리고 총괄에게 병합을 요청한다. "
                        f"(총괄 clone 은 `git config ac.role 총괄`)")
            if no_branch_arg or re.search(r"\bHEAD\b", rest):
                return ("어디로 가는지 명령에 안 보이는 push 는 막는다 — 브랜치 이름을 적는다: "
                        "`git push origin worktree-<이름>`. (인자 없는 push 는 upstream 이 본류면 본류로 간다)")

    if RE_STAGE_ALL.search(cmd) or RE_COMMIT_ALL.search(cmd):
        return ("작업트리 전체 스테이징(git add -A / add . / commit -a)은 남의 파일을 휩쓴다(issue 24). "
                "`python3 log/save.py \"한 줄\" --only <내 경로…>` 또는 `git add -- <경로>` 로 범위를 정한다.")

    for m in RE_HEREDOC.finditer(cmd):
        body = m.group("body")
        if "\\" in body and (not m.group("q") or os.name == "nt"):
            why = "따옴표 없는 <<EOF 는 bash 가 역슬래시를 줄인다" if not m.group("q") else "Windows 의 Bash 도구는 <<'EOF' 도 역슬래시를 못 지킨다(E 실측 09-18)"
            return (f"heredoc 본문에 역슬래시가 있다 — {why}. 파일은 Write/Edit 도구로 쓰고, 명령은 파일을 부른다 "
                    "(constraint_note 38: D·B·E 세 세션이 같은 자리에서 깨졌다).")

    hints = PATH_HINTS + tuple(os.environ.get("AC_GUARD_PATHS", "").split())
    touches_work = any(h.lower() in cmd.lower() for h in hints)
    if touches_work and (RE_MOVE.search(cmd) or RE_DELETE.search(cmd)) and not RE_GIT_MV.search(cmd):
        t = time.time() if now is None else now
        if mark_mtime is None:
            p = Path(_repo_root(cwd)) / MARK
            mark_mtime = p.stat().st_mtime if p.exists() else 0.0
        if t - mark_mtime > MARK_TTL:
            return ("작업 폴더를 옮기거나 지우기 전에 누가 그 경로를 무는지 본다 — "
                    "`python3 tools/cutedit/prlinks.py find \"<경로조각>\" \"<검색 루트>\"` 를 먼저 돌린다 — "
                    f"find 가 표식 {MARK} 를 남긴다(60분 유효). 2026-09-16 L08 소스 끊김 두 번(issue 20)의 재발 방지. 옮긴 뒤 `prlinks.py check`.")
    return None


def main() -> int:
    try:
        # 바이트로 받아 UTF-8 로 푼다 — 콘솔 코드페이지(cp949)로 읽으면 한글 명령에서 깨질 수 있다 (D B7)
        data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception:
        return 0
    tool = data.get("tool_name", "")
    if tool not in ("Bash", "PowerShell"):
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    cwd = data.get("cwd") or os.getcwd()
    reason = check(command, cwd)
    if not reason:
        return 0
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                  "permissionDecision": "deny",
                                  "permissionDecisionReason": reason}}
    # ASCII(\uXXXX)로 쓴다 — PYTHONUTF8 가 없는 환경에서 한글·대시를 cp949 로 쓰다 죽으면 훅이 실패하고
    # 명령이 **그대로 통과**한다 (D 시험 09-17: 한글 경로 mv 차단이 UnicodeEncodeError 로 풀렸다).
    sys.stdout.write(json.dumps(out, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
