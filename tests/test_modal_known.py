# -*- coding: utf-8 -*-
"""아는 모달 문구 표 — 원문 여섯 개를 넣어 보고 답이 같은지 잰다.

공용 실행기(tools/_com/run.ps1)는 실패를 적을 때 모달 문구를 분류한다. 순서는 **표 먼저, Jev 나중**이다
(total 총괄 2026-09-21, 문 0.8). 표가 맞아야 값도 안 들고 흔들리지도 않으므로 여기서 잰다.

원문은 시험 자료(log/data/jev/B1_모달문구.json)에 있고, 알아볼 조각은 tools/_com/modal_known.json 에 있다.
둘이 어긋나면 이 시험이 깨진다 — 한쪽만 고치는 일을 막으려고 일부러 갈라 두고 여기서 묶는다.
Jev 는 부르지 않는다(망도 키도 안 탄다).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "_com"))

import modal_class as mc  # noqa: E402

VERBATIM = ROOT / "log" / "data" / "jev" / "B1_모달문구.json"


def _items():
    return json.loads(VERBATIM.read_text(encoding="utf-8"))["문항"]


def test_table_matches_verbatim_wordings():
    table = mc.load_table()
    틀린 = []
    for q in _items():
        got = mc.classify(q["문구"], use_jev=False, table=table)["처리"]
        if got != q["정답"]:
            틀린.append(f"{q['id']}: 표는 '{got}' · 정답은 '{q['정답']}'")
    assert not 틀린, "표와 원문이 어긋난다 — " + " / ".join(틀린)


def test_unknown_wording_stays_unknown_without_jev():
    """모르는 문구에 함부로 처리를 붙이지 않는다 — 모르면 '모름' 이고, 실행기는 죽이고 기록한다."""
    r = mc.classify("이런 창은 본 적이 없습니다. 무엇이든 하나 고르세요.", use_jev=False)
    assert r["처리"] == mc.UNKNOWN


def test_cancelled_message_carries_the_constraint56_hint():
    """'the operation was cancelled' 는 원인이 안 가려진다 — 힌트로 끝 공백을 가리킨다(constraint 56)."""
    r = mc.classify("오류: the operation was cancelled", use_jev=False)
    assert r["처리"] == mc.UNKNOWN
    assert any("공백" in h for h in r["힌트"])


def test_gate_is_zero_point_eight():
    """자동으로 움직이는 자리라 문이 0.7 이 아니라 0.8 이다 (총괄 2026-09-21 · constraint 65)."""
    assert mc.GATE == 0.8
