#!/usr/bin/env python3
"""세이브 / 로드.

한 슬롯 = 되돌릴 수 있는 한 시점.  KST 분 단위로 save/2026-08-27-1004 처럼 이름이 붙고,
그 시점의 저장소 전체(코드·씬·브랜드 애셋·로그 DB)가 통째로 들어간다.

    python3 log/save.py "대본 인덱스까지"     # 지금 상태를 슬롯으로 굳힌다
    python3 log/save.py --list                # 슬롯 목록
    python3 log/save.py --show <슬롯|해시>    # 그 슬롯이 지금과 뭐가 다른가
    python3 log/save.py --load <슬롯|해시>    # 되돌리는 방법을 알려준다

슬롯의 실체는 커밋이다.  이 저장소는 태그 푸시가 막혀 있어서(403) 태그는 로컬 편의용이고,
슬롯 이름과 커밋 해시의 짝은 log/data/checkpoints.json 에 적혀 함께 푸시된다.
새 컨테이너에서 clone 만 해도 --list 가 그대로 나오고, 해시로 되돌릴 수 있다.

되돌리기는 두 가지다.

    git checkout <해시>                       # 통째로 그 시점을 본다 (구경용)
    git restore --source=<해시> -- .          # 지금 브랜치 위로 그 시점 파일을 덮어쓴다

앞의 것은 구경만 하고 돌아올 때, 뒤의 것은 정말 되돌릴 때 쓴다.
뒤의 것은 되돌린 상태가 새 커밋이 되므로 지나온 기록이 사라지지 않는다.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLOTS = ROOT / "log" / "data" / "checkpoints.json"
KST = timezone(timedelta(hours=9))
BRANCH = "claude/futures-youtube-video-edit-fhio4s"


def git(*args: str, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(args)} 실패\n{r.stderr.strip()}")
    return r.stdout.strip()


def load_slots() -> list[dict]:
    if not SLOTS.exists():
        return []
    return json.loads(SLOTS.read_text(encoding="utf-8"))


def save_slots(rows: list[dict]) -> None:
    SLOTS.parent.mkdir(parents=True, exist_ok=True)
    SLOTS.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def slot_name(when: datetime) -> str:
    return "save/" + when.astimezone(KST).strftime("%Y-%m-%d-%H%M")


def rebuild() -> None:
    """DB·MD·HTML 을 현재 저장소 상태로 다시 만든다."""
    for script in ("build_worklog_db.py", "build_worklog_page.py", "build_readme.py"):
        args = [sys.executable, str(ROOT / "log" / script)]
        if script.endswith("db.py"):
            args.append("--md")
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"{script} 실패\n{r.stdout}\n{r.stderr}")
        print("  " + r.stdout.strip().replace("\n", "\n  "))


def cmd_save(summary: str, push: bool) -> None:
    now = datetime.now(timezone.utc)
    tag = slot_name(now)

    if git("tag", "-l", tag):
        raise SystemExit(f"슬롯 {tag} 가 이미 있습니다. 1분 뒤에 다시 하거나 이름을 바꾸세요.")

    print(f"\n  슬롯 {tag}")
    print(f"  {summary}\n")

    # 1) 로그를 지금 상태로 다시 만든다
    print("  로그 다시 만드는 중")
    rebuild()

    # 2) 작업 내용을 먼저 커밋한다. 이 커밋이 곧 슬롯이 가리키는 시점이다.
    git("add", "-A")
    if git("diff", "--cached", "--name-only"):
        git("commit", "-q", "-m", f"세이브 {tag} — {summary}")
    sha = git("rev-parse", "--short", "HEAD")

    # 3) 슬롯 목록에 해시를 그대로 적는다.
    #    이 저장소는 태그 푸시가 막혀 있어(403) 태그는 로컬 편의용이고,
    #    새 컨테이너에서 복구할 때 실제로 쓰이는 것은 여기 적힌 해시다.
    rows = load_slots()
    rows.append({
        "tag": tag,
        "kst": now.astimezone(KST).strftime("%Y-%m-%d %H:%M"),
        "utc": now.strftime("%Y-%m-%d %H:%M"),
        "sha": sha,
        "summary": summary,
    })
    save_slots(rows)
    rebuild()                       # 슬롯 기록이 DB 에도 들어가게
    git("add", "-A")
    if git("diff", "--cached", "--name-only"):
        git("commit", "-q", "-m", f"세이브 기록 {tag}")
    git("tag", "-a", tag, sha, "-m", summary, check=False)
    print(f"\n  커밋 {sha} · 태그 {tag}")

    if push:
        print("  푸시 중")
        git("push", "-u", "origin", BRANCH)
        print("  올렸습니다. 컨테이너가 사라져도 남습니다.")
        print("  (태그는 이 저장소에서 푸시가 막혀 있어 로컬에만 있습니다."
              " 복구는 log/data/checkpoints.json 의 해시로 합니다.)")
    else:
        print(f"  아직 로컬에만 있습니다:  git push -u origin {BRANCH}")


def cmd_list() -> None:
    rows = load_slots()
    if not rows:
        print("  슬롯이 없습니다.")
        return
    print(f"\n  세이브 슬롯 {len(rows)}개\n")
    for r in rows:
        sha = r.get("sha") or git("rev-list", "-n", "1", "--abbrev-commit", r["tag"], check=False) or "-"
        here = "  ← 지금" if sha and sha == git("rev-parse", "--short", "HEAD") else ""
        print(f"    {r['kst']} KST   {r['tag']:26} {sha:9} {r['summary']}{here}")
    print(f"\n  되돌리기:  git restore --source=<해시> -- .   그 다음  python3 log/save.py \"되돌림\"")
    print(f"  구경만:    git checkout <해시>   (돌아올 때 git checkout {BRANCH})\n")


def resolve(ref: str) -> str:
    """슬롯 이름이든 커밋 해시든 받아 해시로 바꾼다."""
    for r in load_slots():
        if ref in (r["tag"], r.get("sha")):
            return r.get("sha") or r["tag"]
    if git("rev-parse", "--verify", "--quiet", ref, check=False):
        return ref
    raise SystemExit(f"{ref} 를 찾을 수 없습니다. --list 로 슬롯을 확인하세요.")


def cmd_show(tag: str) -> None:
    tag = resolve(tag)
    print(f"\n  {tag}")
    print(f"  {git('log', '-1', '--format=%s', tag)}")
    print(f"\n  시각   {git('log', '-1', '--format=%ad', '--date=iso', tag)}")
    files = git("ls-tree", "-r", "--name-only", tag).splitlines()
    print(f"  파일   {len(files)}개")
    print(f"\n  지금과 다른 파일:")
    diff = git("diff", "--stat", tag, "HEAD", check=False)
    print("    " + (diff.replace("\n", "\n    ") if diff else "없음 (같은 상태)"))
    print()


def cmd_load(tag: str) -> None:
    tag = resolve(tag)
    print(f"""
  {tag} 로 되돌리는 방법

  1) 지금 작업 중인 것부터 슬롯으로 남겨 두세요 (안 그러면 사라집니다)
       python3 log/save.py "되돌리기 전"

  2) 되돌립니다 — 파일만 그 시점으로 덮어쓰고 브랜치는 그대로 둡니다
       git restore --source={tag} -- .
       python3 log/save.py "{tag} 로 되돌림"

  구경만 하고 싶다면
       git checkout {tag}
       git checkout {BRANCH}      # 돌아오기
""")


def main() -> None:
    ap = argparse.ArgumentParser(description="날짜 단위 세이브/로드")
    ap.add_argument("summary", nargs="?", help="이 슬롯이 어디까지인지 한 줄")
    ap.add_argument("--list", action="store_true", help="슬롯 목록")
    ap.add_argument("--show", metavar="태그", help="슬롯 내용")
    ap.add_argument("--load", metavar="태그", help="되돌리는 방법")
    ap.add_argument("--no-push", action="store_true", help="푸시하지 않는다")
    a = ap.parse_args()

    if a.list:
        cmd_list()
    elif a.show:
        cmd_show(a.show)
    elif a.load:
        cmd_load(a.load)
    elif a.summary:
        cmd_save(a.summary, push=not a.no_push)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
