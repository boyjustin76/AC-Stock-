"""radar — 네트워크 없이 서명 추출·우리 기록 검색·응답 파싱만 시험한다."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import radar  # noqa: E402


def test_signature_picks_last_error_line_and_strips_paths():
    tb = """Traceback (most recent call last):
  File "C:\\Users\\user\\Desktop\\x.py", line 12, in <module>
    main()
UnicodeEncodeError: 'cp949' codec can't encode character '\\u2014' in position 40: illegal multibyte sequence"""
    sig = radar.signature(tb)
    assert sig.startswith("UnicodeEncodeError: 'cp949' codec can't encode character")
    assert "Users" not in sig and "40" not in sig


def test_signature_single_line_keeps_words():
    assert radar.signature("Move-Item : Cannot move item because the item at 'C:\\a\\b' is in use.") \
        .startswith("Move-Item : Cannot move item because the item at")


def test_local_finds_cp949_wall():
    hits = radar.search_local("UnicodeEncodeError: 'cp949' codec can't encode character", 3)
    assert hits and any("cp949" in h["title"] for h in hits)


def test_parse_stackoverflow_prefers_accepted():
    data = {"items": [
        {"title": "a &amp; b", "link": "u1", "score": 9, "answer_count": 2},
        {"title": "c", "link": "u2", "score": 1, "answer_count": 1, "accepted_answer_id": 5},
    ]}
    out = radar.parse_se(data, 5)
    assert out[0]["url"] == "u2" and out[0]["answered"]
    assert out[1]["title"] == "a & b"


def test_parse_github():
    data = {"items": [{"title": "t", "html_url": "h", "state": "open", "comments": 3,
                       "repository_url": "https://api.github.com/repos/o/r"}]}
    assert radar.parse_gh(data, 5) == [{"title": "t", "url": "h", "state": "open", "comments": 3, "repo": "o/r"}]


def test_jev_classify_top3_offline():
    """망 없이 — ask 를 주입해 상위 3 추출과 '해당 없음' 처리만 본다."""
    def fake_ask(state, q):
        opts = q["c"]["criteria"]
        keys = list(opts)
        probs = {k: 0.0 for k in keys}
        probs[keys[1]] = 0.6; probs[keys[2]] = 0.3; probs["0"] = 0.1
        return {"answers": {"c": {"type": "choice", "choice": keys[1], "confidence": 0.6, "probabilities": probs}}}
    hits, note = radar.jev_classify("x", "x", 3, ask=fake_ask)
    assert [h["p"] for h in hits] == [0.6, 0.3, 0.1] and hits[-1]["id"] == 0 and "0.60" in note


def test_jev_classify_without_key_is_silent():
    """키가 없으면 jev.py 가 SystemExit 를 낸다 — 레이더는 죽지 않고 빈 결과 + 한 줄. (망을 안 타게 주입)"""
    def no_key(state, q):
        raise SystemExit("TYPESAFE_API_KEY 가 없다")
    hits, note = radar.jev_classify("x", "x", 3, ask=no_key)
    assert hits == [] and "Jev 안 씀" in note
