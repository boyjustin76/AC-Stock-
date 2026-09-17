# -*- coding: utf-8 -*-
"""프리미어 프로젝트가 무는 미디어 경로 검사 — 프리미어를 열지 않는다.

`.prproj` 는 gzip 으로 압축된 XML 이다. 미디어 자리는 세 태그에 들어 있다.
  <ActualMediaFilePath> · <FilePath>   절대경로. **프리미어가 실제로 여는 자리다**
  <RelativePath>                       프로젝트 파일 기준 상대경로. 절대경로가 빗나갔을 때의 대비책

두 가지로 쓴다.

  check  <폴더>            그 아래 프로젝트가 무는 파일이 실제로 있는지 (오프라인 클립 찾기)
  find   <경로조각> <폴더>  그 경로를 무는 프로젝트가 누구인지 (**폴더를 옮기기 전에** 돌린다)

`find` 가 이 도구의 요점이다. 2026-09-16 에 `차트명가 NEW\` 를 옮겼더니 더원 L08 편집본에서
소스 10개가 오프라인이 됐다. 옮기는 쪽은 '파일이 다 담겼나'만 봤고 **'누가 이 경로를 무는가'**
를 안 봤다. 담는 쪽 말고 쓰는 쪽을 보라는 뜻이다.

    python3 tools/cutedit/prlinks.py check "C:/…/더원트레이더/0910"
    python3 tools/cutedit/prlinks.py find  "차트명가 NEW" "C:/Users/user/Desktop/이정찬"

**`RelativePath` 는 한 번 더 이스케이프돼 있다** (`&` → `&amp;amp;`). 프리미어 관행이지 누가
망가뜨린 게 아니다 — 손대지 않은 프로젝트(차트명가New 프리셋, 2026-09-15)도 `RelativePath` 만
이중이고 `ActualMediaFilePath` 는 정상이었다. 그래서 여기서는 상대경로를 **두 번** 푼다.
이걸 모르고 한 번만 풀면 멀쩡한 클립을 끊겼다고 잘못 읽는다.

판정 — **절대경로가 없고, 같은 이름의 상대경로 후보도 없을 때만** 끊긴 것으로 센다.
자동저장본(`Adobe Premiere Pro Auto-Save`)은 기본으로 건너뛴다. `--all` 이면 같이 본다 —
자동저장으로 되돌렸을 때 다시 끊기는 함정을 막으려면 그쪽도 봐야 한다.

**검사 범위에서 목적지 폴더를 빼지 마라.** 옮긴 뒤 검사할 때 '이미 정리한 곳'이라고 새 폴더를
빼면, 그 안에 있던 프로젝트가 옛 경로를 무는 것을 놓친다 (2026-09-16 차트명가 프리셋이 그랬다).
루트 하나를 통째로 주고 `--all` 을 붙이는 편이 안전하다.
"""
import glob
import gzip
import html
import os
import sys

ABS_TAGS = ("ActualMediaFilePath", "FilePath")
REL_TAG = "RelativePath"
AUTOSAVE = "Auto-Save"


def read_xml(proj):
    try:
        return gzip.open(proj, "rb").read().decode("utf-8", "replace")
    except OSError:                       # 압축을 끈 프로젝트도 있다
        return open(proj, "rb").read().decode("utf-8", "replace")


def tag_values(xml, tag):
    out, k, open_t, close_t = [], 0, "<" + tag + ">", "</" + tag + ">"
    while True:
        a = xml.find(open_t, k)
        if a < 0:
            return out
        b = xml.find(close_t, a)
        if b < 0:
            return out
        out.append(xml[a + len(open_t):b].strip())
        k = b + len(close_t)


def is_abs_path(s):
    return len(s) > 3 and s[1] == ":" and s[0].isalpha() and s[2] in ("\\", "/")


def links(proj, xml=None):
    """(절대경로 모음, 상대경로로 찾아지는 파일 이름 모음)."""
    xml = read_xml(proj) if xml is None else xml
    base = os.path.dirname(os.path.abspath(proj))
    absolute, relative = set(), set()
    for tag in ABS_TAGS:
        for v in tag_values(xml, tag):
            v = html.unescape(v)
            if is_abs_path(v):
                absolute.add(v)
    for v in tag_values(xml, REL_TAG):
        v = html.unescape(html.unescape(v))          # 상대경로는 두 번 이스케이프돼 있다
        if not v:
            continue
        p = os.path.normpath(os.path.join(base, v.replace("\\", os.sep)))
        if os.path.exists(p):
            relative.add(os.path.basename(p).lower())
    return absolute, relative


def missing(proj, xml=None):
    absolute, relative = links(proj, xml)
    return sorted(p for p in absolute
                  if not os.path.exists(p) and os.path.basename(p).lower() not in relative), len(absolute)


def projects(root, include_autosave=False):
    for p in sorted(glob.glob(os.path.join(root, "**", "*.prproj"), recursive=True)):
        if include_autosave or AUTOSAVE not in p:
            yield p


def cmd_check(root, include_autosave):
    bad = tot = 0
    for proj in projects(root, include_autosave):
        miss, n = missing(proj)
        tot += 1
        bad += bool(miss)
        print(f"{os.path.basename(proj)[:54]:56} 미디어 {n:3} · "
              + ("모두 연결됨" if not miss else f"끊김 {len(miss)}"))
        for p in miss:
            print("        ", p)
    print(f"\n프로젝트 {tot}개 · 끊긴 프로젝트 {bad}개"
          + ("" if include_autosave else "  (자동저장본은 뺐다 — --all 로 포함)"))
    return 0 if bad == 0 else 1


def cmd_find(needle, root, include_autosave):
    hits = 0
    for proj in projects(root, include_autosave):
        xml = read_xml(proj)
        n = sum(1 for tag in ABS_TAGS + (REL_TAG,)
                for v in tag_values(xml, tag) if needle in html.unescape(v))
        if n:
            hits += 1
            print(f"{n:5}건  {proj}")
    print(f"\n'{needle}' 을(를) 무는 프로젝트 {hits}개"
          + ("" if include_autosave else "  (자동저장본은 뺐다 — --all 로 포함)"))
    return 0 if hits == 0 else 1


def main():
    args = [a for a in sys.argv[1:] if a != "--all"]
    all_ = "--all" in sys.argv
    if len(args) >= 2 and args[0] == "check":
        sys.exit(cmd_check(args[1], all_))
    if len(args) >= 3 and args[0] == "find":
        sys.exit(cmd_find(args[1], args[2], all_))
    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
