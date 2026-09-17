"""컷편집 도구 — 자막 나누기·타임코드·시퀀스 XML·컷 경계의 뼈대를 시험한다.

값을 고르는 채점(정답 자료에 대고 평균 오차를 재는 것)은 tools/cutedit/grade/ 에 있다.
여기는 '고치다가 깨뜨리지 않았나' 만 본다 — 전부 저장소 안 자료로 돌고, 영상·네트워크는 안 쓴다.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUTEDIT = ROOT / "tools" / "cutedit"
WORK = CUTEDIT / "grade" / "work"
sys.path.insert(0, str(CUTEDIT))

import cut_and_srt  # noqa: E402
import make_xml  # noqa: E402
import srt_rules  # noqa: E402
from textnorm import norm  # noqa: E402


def _sentences(ep):
    rows = json.load(open(WORK / ep / "aligned.json", encoding="utf-8"))
    return [r["text"] for r in rows if r["s"] is not None]


def test_split_cue_keeps_14_chars_and_no_dependent_noun_start():
    sents = _sentences("s015") + _sentences("s016")
    assert len(sents) >= 40
    for s in sents:
        parts = srt_rules.split_cue(s)
        assert parts, s
        for k, p in enumerate(parts):
            assert len(p) <= srt_rules.MAX_LEN or " " not in p, (s, p)   # 넘는 건 어절 하나짜리만
            if k:
                assert not srt_rules._bad_break(p.split()[0]), (s, parts)
        assert norm("".join(parts)) == norm(s)                          # 글자를 잃거나 만들지 않는다


def test_split_cue_long_uses_21():
    s = "볼린저밴드 두 개를 겹쳐 놓으면 추세가 살아 있는 구간과 힘이 빠지는 구간이 갈립니다"
    parts = srt_rules.split_cue(s, srt_rules.LONG_MAX_LEN, srt_rules.LONG_MIN_LEN)
    assert all(len(p) <= 21 for p in parts)
    assert max(len(p) for p in parts) > 14


def test_rate_ntsc():
    assert make_xml.rate(29.97) == (30, "TRUE")
    assert make_xml.rate(30) == (30, "FALSE")
    assert make_xml.rate(59.94) == (60, "TRUE")


def test_pathurl_percent_encodes_korean_and_spaces():
    u = make_xml.pathurl(r"C:\Users\user\Desktop\이정찬\L08_PD에게 설명.mp4")
    assert u.startswith("file://localhost/C:/Users/user/Desktop/")
    assert "%EC%9D%B4%EC%A0%95%EC%B0%AC" in u and "%20" in u
    assert "\\" not in u and "이" not in u


def test_fmt_and_sec_round_trip():
    assert cut_and_srt.fmt(3661.5) == "01:01:01,500"
    assert cut_and_srt.fmt(0.0) == "00:00:00,000"
    assert srt_rules.sec("01:01:01,500") == 3661.5
    assert srt_rules.sec("00:00:02.250") == 2.25
    assert srt_rules.sec("00:00:02") == 2.0
    for t in (0.04, 59.999, 3599.5, 7384.123):
        assert abs(srt_rules.sec(cut_and_srt.fmt(t)) - t) < 5e-4


def test_read_srt_tolerates_missing_index_and_multiline(tmp_path):
    p = tmp_path / "a.srt"
    p.write_text("\ufeff1\n00:00:01,000 --> 00:00:02,500\n첫 줄\n둘째 줄\n\n"
                 "00:00:03.000 --> 00:00:04.000\n번호 없음\n\n"
                 "3\n깨진 타임코드\n글\n", encoding="utf-8")
    cues = srt_rules.read_srt(p)
    assert [(c["s"], c["e"], c["t"]) for c in cues] == [(1.0, 2.5, "첫 줄 둘째 줄"), (3.0, 4.0, "번호 없음")]


def test_check_flags_overlap(tmp_path, capsys):
    p = tmp_path / "b.srt"
    p.write_text("1\n00:00:01,000 --> 00:00:03,000\n가나다\n\n2\n00:00:02,000 --> 00:00:04,000\n라마바\n",
                 encoding="utf-8")
    assert srt_rules.check(str(p)) is False
    assert "겹침" in capsys.readouterr().out


def test_s015_cut_count():
    d = WORK / "s015"
    rows = [r for r in json.load(open(d / "aligned.json", encoding="utf-8")) if r["s"] is not None]
    tr = json.load(open(d / "cam_transcript.json", encoding="utf-8"))
    cuts = cut_and_srt.build_cuts(rows, tr, cut_and_srt.read_silences(str(d / "silences.txt")),
                                  cut_and_srt.read_silences(str(d / "silences_fine.txt")))
    assert len(cuts) == 12
    assert all(c["in"] < c["out"] for c in cuts)
    assert all(a["out"] <= b["in"] for a, b in zip(cuts, cuts[1:], strict=False))
