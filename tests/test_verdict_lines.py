# -*- coding: utf-8 -*-
"""어도비 잡(.jsx)의 '판정' 줄 래칫 — 공용 실행기(tools/_com/run.ps1)는 판정 줄로 성공을 정한다.

D 가 1단계에서 "판정 줄 없으면 실패" 를 "경고 통과" 로 완화했다(잡 대부분이 옛 것이라). 총괄은 그 완화를
받되 **없는 잡의 수가 늘지 않게** 여기서 잰다(decision 36). 새 잡은 판정 줄이 있어야 하고, 옛 잡은 손댈 때 넣는다.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOB_DIRS = ("tools/ae/jobs", "tools/premiere/jobs", "tools/photoshop", "tools/illustrator")
BASELINE = 46          # 2026-09-21 — 줄이기만 한다


def _jobs():
    for d in JOB_DIRS:
        for p in sorted((ROOT / d).glob("*.jsx")):
            if p.name.startswith("_") or "labdir" in p.name:
                continue
            yield p


def test_jobs_without_verdict_line_do_not_increase():
    missing = [p.relative_to(ROOT).as_posix() for p in _jobs()
               if "판정" not in p.read_text(encoding="utf-8", errors="replace")]
    assert len(missing) <= BASELINE, f"판정 줄 없는 잡이 늘었다({len(missing)} > {BASELINE}) — 새 잡은 로그에 '판정: …' 한 줄: {missing}"
