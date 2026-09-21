#!/usr/bin/env python3
"""오류 레이더 — 에러가 나면 혼자 끙끙대지 말고, 이미 겪은 사람의 답부터 찾는다.

    python3 tools/radar.py "UnicodeEncodeError: 'cp949' codec can't encode character"
    python3 tools/radar.py --file err.txt --repo anthropics/claude-code --save
    python3 tools/radar.py "…" --no-web            # 우리 기록만 (오프라인)
    python3 tools/radar.py "…" --jev               # + Jev 가 우리 벽 63개 중 상위 3 을 고른다 (키 필요)

찾는 순서 (가까운 곳부터)
  1. 우리 기록 — log/worklog.db 의 issue·constraint_note, brand/EXTENDSCRIPT-TRAPS.md, log/inbox/*.md
     (같은 벽을 이미 넘었으면 여기서 끝난다)
  2. Stack Overflow — Stack Exchange API, 키 없이 하루 300회 / IP. 채택 답 있는 것 우선
  3. GitHub Issues — 검색 API, 비인증 분당 10회. --repo 로 좁히면 정확하다
     (총괄 클라우드 컨테이너는 이 API 가 막혀 있다 — 건너뛰고 GitHub MCP search_issues 를 쓰라고 알린다)

의존성 없음(표준 라이브러리). 출력은 markdown. --save 면 log/inbox/radar/ 에 남겨 총괄이 issue 로 등재한다.
질의는 오류 문장에서 경로·숫자·해시를 걷어낸 '서명'이다 — 붙여넣기 그대로 넣어도 된다.
찾은 답을 그대로 믿지 않는다: 우리 환경(Windows·cp949·ExtendScript·COM)에 맞는지 한 번 재고 적용한다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "log" / "worklog.db"
TRAPS = ROOT / "brand" / "EXTENDSCRIPT-TRAPS.md"
INBOX = ROOT / "log" / "inbox"
UA = "ac-stock-radar/1 (+https://github.com/boyjustin76/AC-Stock-)"
TIMEOUT = 20

ERR_LINE = re.compile(r"\b(\w+(?:Error|Exception|Warning)|error|failed|denied|cannot|not found|timeout|timed out|refused|No such)\b", re.I)
STOP = set("the a an of to in on for and or is are was be with at by from this that it as not no".split())


def signature(text: str) -> str:
    """붙여넣은 오류에서 검색용 한 줄을 뽑는다 — 마지막 '오류 같은 줄', 경로·숫자·해시 제거."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return ""
    cands = [ln for ln in lines if ERR_LINE.search(ln)]
    line = cands[-1] if cands else lines[-1]
    line = re.sub(r"(?:[A-Za-z]:)?[\\/](?:[^\s'\"\\/:]+[\\/])+[^\s'\"\\/]*", " ", line)   # 경로
    line = re.sub(r"\b0x[0-9a-fA-F]+\b|\b[0-9a-f]{7,40}\b", " ", line)                 # 주소·해시
    line = re.sub(r"\\[ux][0-9a-fA-F]{2,6}|'.'|\"\.\"", " ", line)                          # \u2014 · 따옴표 한 글자
    line = re.sub(r"\b(?:in|at) (?:position|line|column|offset)\b", " ", line)
    line = re.sub(r"\b\d+(?:\.\d+)?\b", " ", line)                                      # 숫자
    line = re.sub(r"[\[\]{}()<>|`]", " ", line)
    line = re.sub(r"\s+", " ", line).strip(" :-")
    words = line.split()
    return " ".join(words[:14])


def web_query(sig: str) -> str:
    """검색엔진용 짧은 질의 — 토큰 8개까지. 긴 문장은 Stack Overflow 가 0건을 돌려준다."""
    return " ".join(tokens(sig)[:8])


def tokens(sig: str) -> list[str]:
    out = []
    for w in re.findall(r"[A-Za-z_][A-Za-z0-9_.-]{2,}|[가-힣]{2,}", sig):
        w = w.strip(".-").lower()
        if w and w not in STOP and w not in out:
            out.append(w)
    return out


# ── 1. 우리 기록 ────────────────────────────────────────────────────────────
def _score(text: str, toks: list[str]) -> int:
    t = text.lower()
    return sum(1 for w in toks if w in t)


def search_local(sig: str, n: int = 3) -> list[dict]:
    toks = tokens(sig)
    if not toks:
        return []
    hits: list[dict] = []
    if DB.exists():
        con = sqlite3.connect(str(DB))
        for seq, title, symptom, root, fix, status in con.execute(
                "SELECT seq,title,symptom,root_cause,fix,status FROM issue"):
            s = _score(" ".join([title, symptom, root, fix]), toks)
            if s:
                hits.append({"src": f"issue {seq} [{status}]", "title": title, "fix": fix, "score": s * 3})
        for rid, topic, limit, work in con.execute("SELECT id,topic,limit_value,workaround FROM constraint_note"):
            s = _score(" ".join([topic, limit, work]), toks)
            if s:
                hits.append({"src": f"constraint_note {rid}", "title": topic, "fix": work, "score": s * 3})
        con.close()
    if TRAPS.exists():
        for block in re.split(r"\n(?=#{2,4} )", TRAPS.read_text(encoding="utf-8")):
            head = block.splitlines()[0].lstrip("# ").strip()
            s = _score(block, toks)
            if s and head:
                hits.append({"src": "EXTENDSCRIPT-TRAPS.md", "title": head, "fix": "원문 참조 (번호로 가리킨다)", "score": s * 2})
    if INBOX.exists():
        for f in sorted(INBOX.glob("*.md")):
            for block in re.split(r"\n(?=#{2,4} )", f.read_text(encoding="utf-8", errors="replace")):
                head = block.splitlines()[0].lstrip("# ").strip()
                s = _score(block, toks)
                if s >= 2 and head:
                    hits.append({"src": f"inbox {f.name}", "title": head, "fix": "원문 참조", "score": s})
    hits.sort(key=lambda h: -h["score"])
    out, inbox_n = [], 0
    for h in hits:                       # 인박스 원문(부록 로그)은 한 건만 — DB 문장이 먼저다
        if h["src"].startswith("inbox"):
            if inbox_n:
                continue
            inbox_n += 1
        out.append(h)
        if len(out) >= n:
            break
    return out


# ── 1b. Jev 분류 — 우리 벽(constraint_note) 중 어느 것인가, 상위 3 ─────────────
def jev_classify(sig: str, raw: str, n: int = 3, ask=None) -> tuple[list[dict], str]:
    """D 시험 D-3(11/12, 2026-09-21)로 채택 — 1등 하나가 아니라 확률 상위 n 개를 보여 준다(24/25 처럼 둘 다 맞는 경우).
    키(TYPESAFE_API_KEY)나 망이 없으면 조용히 비운다 — 레이더가 죽어서 일을 막지 않는다. ask 는 시험용 주입."""
    if not DB.exists():
        return [], ""
    con = sqlite3.connect(str(DB))
    rows = con.execute("SELECT id, topic FROM constraint_note ORDER BY id").fetchall()
    con.close()
    options = {str(i): t for i, t in rows}
    options["0"] = "해당 없음 — 기록에 없는 새 벽"
    try:
        if ask is None:
            sys.path.insert(0, str(ROOT / "tools" / "jev"))
            import jev  # noqa: PLC0415
            ask = lambda state, q: jev.ask(state, q)  # noqa: E731
            q = {"c": jev.choice("이 오류는 아래 기록 중 어느 것인가", options)}
        else:
            q = {"c": {"type": "choice", "instructions": "이 오류는 아래 기록 중 어느 것인가", "criteria": options}}
        state = (raw.strip()[:1500] or sig)
        ans = ask(state, q)
    except SystemExit as e:                       # 키 없음 등 — jev.py 가 SystemExit 로 알린다
        return [], f"Jev 안 씀 ({e})"
    except Exception as e:
        return [], f"Jev 못 씀 ({type(e).__name__}: {e})"
    a = ans.get("answers", {}).get("c", {})
    probs = a.get("probabilities") or {}
    top = sorted(probs.items(), key=lambda kv: -kv[1])[:n]
    out = [{"id": int(k) if k.isdigit() else 0, "topic": options.get(k, k), "p": round(v, 2)} for k, v in top]
    return out, f"confidence {a.get('confidence', 0):.2f}"


# ── 2·3. 웹 ────────────────────────────────────────────────────────────────
def _get(url: str) -> tuple[int, dict | None, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                import gzip
                raw = gzip.decompress(raw)
            return r.status, json.loads(raw.decode("utf-8", "replace")), ""
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        return e.code, None, body[:300]
    except Exception as e:  # 네트워크 없음 등 — 레이더가 죽어서 일을 막지 않는다
        return 0, None, str(e)


def parse_se(data: dict, n: int) -> list[dict]:
    items = data.get("items", [])
    items.sort(key=lambda i: (not i.get("accepted_answer_id"), -int(i.get("score", 0))))
    return [{"title": _unescape(i.get("title", "")), "url": i.get("link", ""),
             "score": i.get("score", 0), "answered": bool(i.get("accepted_answer_id")),
             "answers": i.get("answer_count", 0)} for i in items[:n]]


def search_stackoverflow(sig: str, n: int) -> tuple[list[dict], str]:
    q = urllib.parse.urlencode({"order": "desc", "sort": "relevance", "q": web_query(sig), "site": "stackoverflow",
                                "pagesize": max(n * 2, 5)})
    code, data, err = _get("https://api.stackexchange.com/2.3/search/advanced?" + q)
    if code != 200 or not data:
        return [], f"Stack Overflow 못 봄 (http {code}) {err}".strip()
    left = data.get("quota_remaining")
    return parse_se(data, n), f"남은 쿼터 {left}/일" if left is not None else ""


def parse_gh(data: dict, n: int) -> list[dict]:
    items = data.get("items", [])
    return [{"title": i.get("title", ""), "url": i.get("html_url", ""), "state": i.get("state", ""),
             "comments": i.get("comments", 0), "repo": "/".join(i.get("repository_url", "").split("/")[-2:])}
            for i in items[:n]]


def search_github(sig: str, repos: list[str], n: int) -> tuple[list[dict], str]:
    q = web_query(sig) + " is:issue" + "".join(f" repo:{r}" for r in repos)
    url = "https://api.github.com/search/issues?" + urllib.parse.urlencode({"q": q, "per_page": n, "sort": "reactions"})
    code, data, err = _get(url)
    if code == 403 and "bound to their configured repositories" in err:
        return [], "GitHub 검색 API 가 이 컨테이너에선 막혀 있다 — mcp__github__search_issues 로 같은 질의를 한다"
    if code in (403, 429):
        return [], f"GitHub 검색 제한 (http {code}) — 비인증은 분당 10회. 잠시 뒤 다시"
    if code != 200 or not data:
        return [], f"GitHub 못 봄 (http {code}) {err}".strip()
    return parse_gh(data, n), ""


def _unescape(s: str) -> str:
    import html
    return html.unescape(s)


# ── 출력 ────────────────────────────────────────────────────────────────────
def report(sig: str, local: list[dict], so: list[dict], so_note: str, gh: list[dict], gh_note: str,
           raw: str, web: bool, jev: list[dict] | None = None, jev_note: str = "") -> str:
    L = [f"# 레이더 · {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}", "", f"**서명:** `{sig}`", ""]
    L.append("## 1. 우리 기록")
    if local:
        for h in local:
            L.append(f"- **{h['src']}** — {h['title']}")
            L.append(f"  - 처방: {h['fix'][:300]}")
    else:
        L.append("- 없음 — 처음 보는 벽이다. 해결하면 log/inbox 에 원문을 남긴다 (decision 24)")
    if jev:
        L += ["", f"## 1b. Jev 가 고른 벽 (상위 {len(jev)}, {jev_note})"]
        for h in jev:
            L.append(f"- constraint_note **{h['id']}** ({h['p']:.0%}) — {h['topic']}" if h["id"] else f"- 해당 없음 ({h['p']:.0%}) — 새 벽일 수 있다")
        L.append("- 확률이 갈리면 둘 다 맞을 수 있다(원인/처방). 자리 치우침이 있으니 확신은 0.7 넘을 때만 (constraint_note 65)")
    elif jev_note:
        L += ["", f"## 1b. Jev — {jev_note}"]
    if web:
        L += ["", "## 2. Stack Overflow" + (f"  ({so_note})" if so_note and so else "")]
        if so:
            for h in so:
                mark = "✔채택" if h["answered"] else f"답 {h['answers']}"
                L.append(f"- [{h['title']}]({h['url']}) · 점수 {h['score']} · {mark}")
        else:
            L.append(f"- {so_note or '없음'}")
        L += ["", "## 3. GitHub Issues"]
        if gh:
            for h in gh:
                L.append(f"- [{h['repo']}] [{h['title']}]({h['url']}) · {h['state']} · 댓글 {h['comments']}")
        else:
            L.append(f"- {gh_note or '없음'}")
    L += ["", "## 다음", "- 답을 적용하기 전에 우리 환경(Windows cp949 · ExtendScript ES3 · COM 모달 · 한글 경로)에 맞는지 한 줄로 확인한다",
          "- 해결되면 원문(오류 로그·고친 줄)을 log/inbox/YYYY-MM-DD_<세션>_<주제>.md 에 남긴다",
          "- 로컬 PC 라면 context7 (라이브러리 문서) · GitHub MCP search_issues 도 같은 서명으로 물어본다", ""]
    if raw and raw.strip() != sig:
        L += ["<details><summary>원문</summary>", "", "```", raw.strip()[:2000], "```", "", "</details>", ""]
    return "\n".join(L)


def slug(sig: str) -> str:
    s = re.sub(r"[^0-9A-Za-z가-힣]+", "-", sig).strip("-")
    return s[:48] or "radar"


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Windows cp949 콘솔
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="오류 레이더 — 우리 기록 → Stack Overflow → GitHub Issues")
    ap.add_argument("text", nargs="?", help="오류 문장 (붙여넣기 그대로)")
    ap.add_argument("--file", help="오류 로그 파일")
    ap.add_argument("--repo", action="append", default=[], help="GitHub owner/name (여러 번)")
    ap.add_argument("-n", type=int, default=5, help="소스당 결과 수")
    ap.add_argument("--no-web", action="store_true", help="우리 기록만")
    ap.add_argument("--save", action="store_true", help="log/inbox/radar/ 에 남긴다")
    ap.add_argument("--jev", action="store_true", help="Jev 로 우리 벽 중 어느 것인지 상위 3 (키 필요, D-3 11/12)")
    a = ap.parse_args(argv)
    raw = Path(a.file).read_text(encoding="utf-8", errors="replace") if a.file else (a.text or "")
    if not raw.strip() and not sys.stdin.isatty():
        raw = sys.stdin.read()
    sig = signature(raw)
    if not sig:
        ap.error("오류 문장을 주세요")
    local = search_local(sig, 3)
    jev_hits, jev_note = ([], "")
    if a.jev:
        jev_hits, jev_note = jev_classify(sig, raw)
    so, so_note, gh, gh_note = [], "", [], ""
    if not a.no_web:
        so, so_note = search_stackoverflow(sig, a.n)
        gh, gh_note = search_github(sig, a.repo, a.n)
    md = report(sig, local, so, so_note, gh, gh_note, raw, web=not a.no_web, jev=jev_hits, jev_note=jev_note)
    print(md)
    if a.save:
        out = INBOX / "radar" / f"{dt.date.today().isoformat()}_{slug(sig)}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"\n저장: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
