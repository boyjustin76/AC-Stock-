"""Jev(TypeSafe System One) 판정관 시험 — B 세션 몫 셋을 돌린다.

총괄 설계: log/inbox/2026-09-21_총괄_Jev_시험_D·B.md
정답 자료: log/data/jev/B1_모달문구.json · B2_썸네일_빨강.json · B3_오류분류_정답.json

E 가 찾은 것을 그대로 반영한다 — **자리 치우침**(같은 질문도 선택지 자리를 바꾸면 답이 뒤집힌다,
26번 중 16번 앞자리, E 2026-09-21). 그래서 문항마다 **선택지 순서를 뒤집어 두 번 묻고,
둘 다 같은 답일 때만 인정**한다. 한 방향만 재면 점수가 부풀려진다.

키는 ~/.secrets/ac_keys.env 에서 읽는다 (decision 32). 화면에 찍지 않는다.

    python tools/jev_b_test.py b1 b2 b3          # 전부
    python tools/jev_b_test.py b1                # 하나만
    python tools/jev_b_test.py b1 --dry          # 호출 없이 질문만 찍어 본다
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "log" / "data" / "jev"
OUT = DATA / "_결과"


def load_key() -> str:
    """키 파일에서 TYPESAFE_API_KEY 만 꺼낸다. 값은 돌려주기만 하고 찍지 않는다."""
    env = os.environ.get("TYPESAFE_API_KEY")
    if env:
        return env
    p = Path.home() / ".secrets" / "ac_keys.env"
    if not p.exists():
        raise SystemExit(f"키 파일이 없습니다: {p}")
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith("TYPESAFE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("TYPESAFE_API_KEY 줄을 못 찾았습니다")


def jload(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


# ── 문항 만들기 ──────────────────────────────────────────────────────
# 각 시험은 (문항 id, state, 지시문, 선택지 목록, 정답 판정 함수) 를 내놓는다.


def build_b1() -> list[dict]:
    d = jload("B1_모달문구.json")
    opts = list(d["선택지"])
    out = []
    for q in d["문항"]:
        ok = {q["정답"]}
        out.append({
            "id": q["id"],
            "state": {"모달 문구": q["문구"]},
            "지시": "일러스트레이터 자동화 도중 이 창이 떴다. 어떻게 다루어야 하는가?",
            "선택지": opts,
            "정답": ok,
            "정답표시": q["정답"],
        })
    return out


def build_b2() -> list[dict]:
    d = jload("B2_썸네일_빨강.json")
    out = []
    for q in d["문항"]:
        out.append({
            "id": q["id"],
            "state": {"문장": q["윗줄"]},
            "지시": "이 문장에서 부정당하는 대상은 무엇인가? 부정당하는 대상이 없으면 '없음'.",
            "선택지": list(q["선택지"]),
            "정답": {q["정답"]},
            "정답표시": q["정답"],
        })
    return out


def build_b3(cn: dict[int, str]) -> list[dict]:
    d = jload("B3_오류분류_정답.json")
    NONE = "해당 없음"
    opts = [f"{i}. {t}" for i, t in sorted(cn.items())] + [NONE]
    by_id = {i: f"{i}. {t}" for i, t in cn.items()}
    out = []
    for q in d["문항"]:
        allow = q.get("허용") or []
        ok = {by_id[i] for i in allow if i in by_id} or {NONE}
        out.append({
            "id": q["id"],
            "state": {"겪은 일": q["요지"]},
            "지시": "이 일은 우리가 이미 적어 둔 제약(constraint_note) 중 어느 것인가? 맞는 것이 없으면 '해당 없음'.",
            "선택지": opts,
            "정답": ok,
            "정답표시": " 또는 ".join(sorted(ok)) if ok else "(없음)",
        })
    return out


def load_cn() -> dict[int, str]:
    import sqlite3
    c = sqlite3.connect(REPO / "log" / "worklog.db")
    return {r[0]: r[1] for r in c.execute("select id, topic from constraint_note order by id")}


# ── 돌리기 ───────────────────────────────────────────────────────────

def ask(client, Choice, item, options) -> dict:
    """선택지를 준 순서대로 한 번 묻는다."""
    res = client.system_one(
        state=item["state"],
        questions={"q": Choice(instructions=item["지시"],
                               criteria={o: None for o in options})},
    )
    a = res.choices["q"]
    top = sorted(a.probabilities.items(), key=lambda kv: -kv[1])[:3]
    return {
        "choice": a.choice,
        "confidence": round(a.confidence, 3),
        "top3": [(k, round(v, 3)) for k, v in top],
        "입력토큰": res.usage.input_tokens,
    }


def run(name: str, items: list[dict], client, Choice, dry: bool) -> dict:
    print(f"\n=== {name} · {len(items)}문항 · 문항마다 선택지 순서를 뒤집어 두 번 ===")
    rows, tok = [], 0
    for it in items:
        fwd_opts = it["선택지"]
        rev_opts = list(reversed(fwd_opts))
        if dry:
            print(f"  {it['id']}: {it['지시'][:40]}… 선택지 {len(fwd_opts)}개 · 정답 {it['정답표시'][:40]}")
            continue
        a = ask(client, Choice, it, fwd_opts)
        b = ask(client, Choice, it, rev_opts)
        tok += a["입력토큰"] + b["입력토큰"]
        같음 = a["choice"] == b["choice"]
        맞음 = 같음 and a["choice"] in it["정답"]
        rows.append({
            "id": it["id"], "정답": it["정답표시"],
            "앞순서": a["choice"], "conf_앞": a["confidence"],
            "뒤집음": b["choice"], "conf_뒤": b["confidence"],
            "자리무관": 같음, "맞음": 맞음,
            "top3_앞": a["top3"],
        })
        mark = "O" if 맞음 else ("~" if 같음 else "X")
        print(f"  {mark} {it['id']:<6} 앞[{a['choice'][:28]}] {a['confidence']:.2f} "
              f"/ 뒤[{b['choice'][:28]}] {b['confidence']:.2f}  정답[{it['정답표시'][:28]}]")
        time.sleep(0.2)
    if dry:
        return {}
    n = len(rows)
    맞은수 = sum(r["맞음"] for r in rows)
    자리무관 = sum(r["자리무관"] for r in rows)
    # 한 방향만 쟀으면 몇 점이었을지 — E 가 92% -> 69% 로 떨어진 그 차이를 같이 본다
    앞만맞 = sum(1 for r in rows if r["앞순서"] in _ans(items, r["id"]))
    print(f"  → 둘 다 같고 맞음 {맞은수}/{n} · 자리 바꿔도 같은 답 {자리무관}/{n} · 앞순서만 보면 {앞만맞}/{n}")
    return {"이름": name, "문항수": n, "맞음": 맞은수, "자리무관": 자리무관,
            "앞순서만": 앞만맞, "입력토큰": tok, "행": rows}


def _ans(items, qid):
    for it in items:
        if it["id"] == qid:
            return it["정답"]
    return set()


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    which = args or ["b1", "b2", "b3"]

    import typesafe_sdk as ts

    client = None if dry else ts.TypeSafeClient(api_key=load_key())
    cn = load_cn()
    builders = {"b1": build_b1, "b2": build_b2, "b3": lambda: build_b3(cn)}

    OUT.mkdir(parents=True, exist_ok=True)
    summary = []
    try:
        for w in which:
            items = builders[w]()
            r = run(w.upper(), items, client, ts.Choice, dry)
            if r:
                summary.append(r)
                (OUT / f"{w}_결과.json").write_text(
                    json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        if client:
            client.close()

    if summary:
        print("\n=== 모두 ===")
        tot = 0
        for s in summary:
            print(f"  {s['이름']}: {s['맞음']}/{s['문항수']} "
                  f"(자리무관 {s['자리무관']}/{s['문항수']} · 앞순서만 보면 {s['앞순서만']}/{s['문항수']})")
            tot += s["입력토큰"]
        print(f"  입력토큰 합계 {tot:,} = 약 ${tot / 1_000_000 * 0.042:.4f}")


if __name__ == "__main__":
    main()
