# -*- coding: utf-8 -*-
"""save.py — 푸시 대상 규칙만 (git 을 부르지 않는다)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("save", ROOT / "log" / "save.py")
save = importlib.util.module_from_spec(spec)
spec.loader.exec_module(save)


def test_sidebranch_pushes_to_itself():
    assert save.push_target("worktree-D_Video", "") == "worktree-D_Video"


def test_mainline_only_for_master_role():
    assert save.push_target(save.BRANCH, "") is None
    assert "총괄만" in save.push_reason(save.BRANCH, "")
    assert save.push_target(save.BRANCH, "총괄") == save.BRANCH


def test_detached_head_not_pushed():
    assert save.push_target("HEAD", "총괄") is None
