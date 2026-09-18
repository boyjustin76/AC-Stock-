"""이름 규칙 왕복 시험 — 만든 이름이 실제 디스크에서 그대로 살아남는가.

윈도우는 경로 마지막 조각의 끝 공백·마침표를 조용히 뗀다. 폴더면 그 안을 못 찾아 터지고,
파일이면 적힌 이름이 달라져 이름 검사가 어긋난다. 그래서 '만들어 보고 다시 읽는' 시험을 둔다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import shortform  # noqa: E402

DIRTY = ["제목 끝에 마침표.", "제목 끝에 공백 ", "정상 제목"]


def test_folder_name_survives_disk(tmp_path):
    for title in DIRTY:
        name = shortform.folder_name(11, 4, title, "260918")
        d = tmp_path / name
        d.mkdir()
        assert d.name in [x.name for x in tmp_path.iterdir()], (title, name)   # 이름 그대로 남았나
        (d / "a.txt").write_text("x", encoding="utf-8")                        # 폴더로 실제로 쓸 수 있나
        assert (d / "a.txt").read_text(encoding="utf-8") == "x"


def test_file_name_survives_disk(tmp_path):
    for title in DIRTY:
        name = shortform.file_name(11, 4, title)
        p = tmp_path / name
        p.write_text("x", encoding="utf-8")
        assert name in [x.name for x in tmp_path.iterdir()], (title, name)     # 적힌 이름이 같은가


def test_names_round_trip_check_name(tmp_path):
    for title in DIRTY:
        d = tmp_path / shortform.folder_name(11, 4, title, "260918")
        d.mkdir()
        p = d / shortform.file_name(11, 4, title)
        p.write_text("x", encoding="utf-8")
        assert shortform.check_name(p) == [], (title, p.name, d.name)          # 규칙 검사를 통과하는가
