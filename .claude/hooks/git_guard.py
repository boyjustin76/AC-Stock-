#!/usr/bin/env python3
"""Claude Code PreToolUse 훅 — 위험한 git·이동 명령을 실행 전에 막는다.

D 가 로컬(~/.claude/hooks/hookify_reason.py)에서 쓰던 규칙 3개를 저장소로 옮긴 것이다.
저장소에 있어야 총괄·B·D·E 가 같은 규칙을 받는다 (공식 hooks 문서: 프로젝트 .claude/settings.json).
아직 **연결돼 있지 않다** — 켜는 법은 log/inbox 의 작업체계 제안서 §3. 켜면 아래 JSON 을
.claude/settings.json 의 "hooks" 에 넣는다 (Windows 는 python 이름이 다르니 exec form).

규칙
  1. mainline-push     본류(claude/futures-…, main, master)로 push 금지.
                       총괄 clone 만 예외: `git config ac.role 총괄` 이 있으면 통과.
  2. whole-tree-stage  `git add -A` · `git add .` · `git commit -a` 금지 — 같은 작업트리를 나눠 쓰면
                       남의 파일이 딸려 간다(issue 24). `python3 log/save.py "…" --only <경로>` 를 쓴다.
                       (D 의 '커밋 전 git status' 규칙을 상태 없이 검사할 수 있는 형태로 바꿨다.)
  3. move-without-prlinks  mv / Move-Item / Rename-Item / robocopy /MOV 는 60분 안에 prlinks find 를
                       돌린 표식(<저장소>/.claude/prlinks_find.ok)이 있어야 통과. 표식은
                       `python3 tools/cutedit/prlinks.py find …` 뒤에 `touch .claude/prlinks_find.ok` (E 가
                       prlinks.py 에 넣어 주면 자동). git mv 와 저장소 안 이동은 대상이 아니다.

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
GIT = r"\bgit(?:\s+-[cC]\s+\S+|\s+-C\s+\S+|\s+--git-dir=\S+|\s+--work-tree=\S+)*\s+"
RE_PUSH = re.compile(GIT + r"push\b(?P<rest>[^\n;&|]*)")
RE_STAGE_ALL = re.compile(GIT + r"add\b[^\n;&|]*?(?:\s-A\b|\s--all\b|\s\.(?:\s|$))")
RE_COMMIT_ALL = re.compile(GIT + r"commit\b[^\n;&|]*?\s(?:-a\b|--all\b|-am\b)")
# 줄 머리(^, MULTILINE)도 명령 시작으로 본다 — PowerShell 여러 줄 스크립트의 셋째 줄 Move-Item 을 놓쳤다 (D 시험 09-17)
RE_MOVE = re.compile(r"(?:^|[;&|]\s*)(?:mv|Move-Item|Rename-Item|mv\.exe)\s|robocopy\b[^\n]*\s/MOV\b", re.I | re.M)
RE_GIT_MV = re.compile(GIT + r"mv\b")
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
            if target is None and (no_branch_arg or re.search(r"\bHEAD\b", rest)):   # 인자 없음·HEAD → 현재 브랜치
                cur = _branch(cwd) if branch is None else branch
                target = cur if cur in MAINLINE else None
            if target:
                return (f"본류 '{target}' 로의 push 는 총괄만 한다. 옆가지(local/…)로 올리고 총괄에게 병합을 요청한다. "
                        f"(총괄 clone 은 `git config ac.role 총괄`)")

    if RE_STAGE_ALL.search(cmd) or RE_COMMIT_ALL.search(cmd):
        return ("작업트리 전체 스테이징(git add -A / add . / commit -a)은 남의 파일을 휩쓴다(issue 24). "
                "`python3 log/save.py \"한 줄\" --only <내 경로…>` 또는 `git add -- <경로>` 로 범위를 정한다.")

    if RE_MOVE.search(cmd) and not RE_GIT_MV.search(cmd):
        t = time.time() if now is None else now
        if mark_mtime is None:
            p = Path(_repo_root(cwd)) / MARK
            mark_mtime = p.stat().st_mtime if p.exists() else 0.0
        if t - mark_mtime > MARK_TTL:
            return ("폴더·파일을 옮기기 전에 누가 그 경로를 무는지 본다 — "
                    "`python3 tools/cutedit/prlinks.py find \"<경로조각>\" \"<검색 루트>\"` 를 먼저 돌리고 "
                    f"`touch {MARK}` (60분 유효). 2026-09-16 L08 소스 끊김 두 번(issue 20)의 재발 방지. 옮긴 뒤 `prlinks.py check`.")
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
