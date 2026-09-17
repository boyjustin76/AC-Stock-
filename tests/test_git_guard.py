"""git_guard 규칙 시험 — 실제 git 을 부르지 않도록 role/branch/mark 를 주입한다."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("git_guard", ROOT / ".claude" / "hooks" / "git_guard.py")
gg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gg)

NOW = 1_000_000.0
FRESH = NOW - 60          # 1분 전 표식
STALE = NOW - 2 * 3600    # 2시간 전 표식


def chk(cmd, **kw):
    kw.setdefault("role", "")
    kw.setdefault("branch", "local/newch-style")
    kw.setdefault("now", NOW)
    kw.setdefault("mark_mtime", FRESH)
    return gg.check(cmd, ".", **kw)


# 1. 본류 push
def test_push_mainline_explicit_blocked():
    assert chk("git push -u origin claude/futures-youtube-video-edit-fhio4s")
    assert chk("git -C C:/x/AC-Stock- push origin main")


def test_push_sidebranch_allowed():
    assert chk("git push -u origin local/newch-style") is None


def test_push_no_arg_uses_current_branch():
    assert chk("git push", branch="claude/futures-youtube-video-edit-fhio4s")
    assert chk("git push", branch="local/script-lab") is None


def test_push_allowed_for_master_role():
    assert chk("git push -u origin claude/futures-youtube-video-edit-fhio4s", role="총괄") is None


def test_grep_or_log_mentioning_push_not_blocked():
    assert chk("git log --grep push") is None
    assert chk("grep -n 'git push' log/save.py") is None


# 2. 전체 스테이징
def test_stage_all_blocked():
    assert chk("git add -A")
    assert chk("git add . && git commit -m x")
    assert chk("git commit -am 'x'")
    assert chk("git commit -a -m 'x'")


def test_scoped_stage_allowed():
    assert chk("git add -- tools/illustrator") is None
    assert chk("git add tools/ae/labdir.mjs") is None
    assert chk('python3 log/save.py "x" --only tools/ae') is None


# 3. 이동
def test_move_without_fresh_mark_blocked():
    assert chk('mv "C:/a/폴더" "C:/b/"', mark_mtime=STALE)
    assert chk('Move-Item -Path C:\\a -Destination C:\\b', mark_mtime=0.0)


def test_move_with_fresh_mark_allowed():
    assert chk('mv "C:/a/폴더" "C:/b/"', mark_mtime=FRESH) is None


def test_git_mv_and_non_move_allowed():
    assert chk("git mv tools/cutedit/build_cuts.py tools/legacy/", mark_mtime=STALE) is None
    assert chk("ls -la; echo mv", mark_mtime=STALE) is None


def test_push_head_uses_current_branch():
    assert chk("git push origin HEAD", branch="claude/futures-youtube-video-edit-fhio4s")
    assert chk("git push origin HEAD", branch="local/ae-lab") is None


# D 시험 (2026-09-17) — 실제 입력 모양에서 놓친 것
def test_move_on_later_line_of_multiline_script_blocked():
    script = '$src = "C:/a"\n$dst = "C:/b"\nMove-Item -LiteralPath $src -Destination $dst'
    assert chk(script, mark_mtime=STALE)


def test_hook_main_survives_cp949_console():
    """PYTHONUTF8 없이 돌려도 한글 명령을 막고 이유를 ASCII JSON 으로 낸다 — 죽으면 명령이 통과한다."""
    import json
    import os
    import subprocess
    import sys
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    cmd = "git push origin claude/futures-youtube-video-edit-fhio4s  # 한글 경로 — 대시"
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": "."}, ensure_ascii=False).encode("utf-8")
    r = subprocess.run([sys.executable, str(ROOT / ".claude" / "hooks" / "git_guard.py")],
                       input=payload, capture_output=True, env=env, timeout=30)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.decode("ascii"))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
