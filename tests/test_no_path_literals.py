# -*- coding: utf-8 -*-
"""새 코드에 절대경로 리터럴이 박히는 것을 막는 래칫(ratchet) 시험 — 킴 지적 2026-09-18.

경로를 박은 코드가 폴더 통합 때 셋 터졌다(issue 20·23·39). labdir 패턴이 정답이고, 새 리터럴은 여기서 걸린다.
지금 남은 것은 BASELINE 에 적어 두고, 고치면 지운다. **BASELINE 은 늘어나면 안 된다.**
파이썬은 ast 로 문자열 상수만 본다(docstring·주석 제외). jsx/mjs/ps1 은 주석 줄을 뺀 정규식.
"""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAT = re.compile(r"^(?:[A-Za-z]:[\\/]|/c/Users)")
SKIP_DIRS = ("tools/legacy", "node_modules", "lab", "deliver", "out")
SKIP_FILES = ("labdir", "_labdir")          # 폴백으로 옛 자리를 적는 파일
BASELINE = {                                 # 파일: 허용 개수 (고치면 줄인다)
    "tools/theone/pairs.py": 2,              # EXTRA_SRT — E (검토 ⑦)
    "tools/style/trad.py": 1,                # C:\Windows\Fonts\batang.ttc — 시스템 폰트, 이 PC 전용 (D)
}


def _py_literals(p: Path):
    tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue                          # docstring
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and PAT.match(node.value):
            yield node.lineno


def _other_literals(p: Path):
    in_block = False                          # /* … */ 블록 주석 안은 건너뛴다
    for i, ln in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        s = ln.strip()
        if in_block:
            if "*/" in s:
                in_block = False
            continue
        if s.startswith("/*") or s.startswith("<#"):
            if "*/" not in s and "#>" not in s:
                in_block = True
            continue
        if s.startswith(("//", "*", "#")):
            continue
        for _ in re.finditer(r"[\"'`]([A-Za-z]:[\\/][^\"'`]*|/c/Users[^\"'`]*)[\"'`]", ln):
            yield i


def test_no_new_absolute_path_literals():
    found = {}
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in (".py", ".mjs", ".js", ".jsx", ".ps1"):
            continue
        rel = p.relative_to(ROOT).as_posix()
        if not rel.startswith(("tools/", "src/", "scenes/", "log/")) or rel.endswith("build_worklog_db.py"):
            continue
        if any(rel.startswith(d) for d in SKIP_DIRS) or any(k in p.name for k in SKIP_FILES):
            continue
        lines = list(_py_literals(p) if p.suffix == ".py" else _other_literals(p))
        if lines:
            found[rel] = lines
    over = {f: v for f, v in found.items() if len(v) > BASELINE.get(f, 0)}
    assert not over, f"새 절대경로 리터럴 — labdir/환경변수/설정으로 바꾼다: {over}"
