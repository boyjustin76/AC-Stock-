# -*- coding: utf-8 -*-
"""바른(bareun.ai)으로 대본의 **어법**을 본다 — 맞춤법·띄어쓰기 교정.

    python bareun.py <초안.md>            # 고칠 곳과 **물리친 교정**을 같이 보여 준다
    python bareun.py <초안.md> --적용      # `*_어법교정.md` 로 새로 쓴다 (원본은 안 건드린다)

왜 이걸 쓰나 — kiwipiepy 는 형태소를 나눌 뿐 교정은 못 한다. 바른은 국립국어원 47품사 기준이고
교정 근거를 같이 돌려준다.

## 그대로 받아쓰면 안 된다 — 첫 호출에서 바로 확인했다 (2026-09-21)

    오늘은 볼린저 밴드에 대해서 알아 보겠습니다.
    →  오늘은 **볼링저** 밴드에 대해서 알아보겠습니다.

`볼린저` 를 모르는 낱말로 보고 `볼링저` 로 망가뜨렸다. `et5-typos-corrector` 를 반려한 것과
같은 실패다(그때는 `하락 구조`→`상승 구조`). 띄어쓰기(`알아 보겠습니다`→`알아보겠습니다`)는 맞았다.

**그래서 회사 Pool 을 방패로 쓴다.** 교정이 **Pool 173편에 실제로 쓰인 낱말을 건드리면 물리친다.**
회사가 173편에서 써 온 말이면 그게 우리 표기다. Pool 에 없는 낱말만 교정을 받는다.
물리친 것도 전부 찍어서 사람이 볼 수 있게 한다.
"""
import difflib
import io
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

import certifi

from inpool import forms as POOL_FORMS          # Pool 낱말 셈 (캐시)

URL = "https://api.bareun.ai/bareun.RevisionService/CorrectError"
CHUNK = 1200
CTX = ssl.create_default_context(cafile=certifi.where())
WORD = re.compile(r"[0-9가-힣a-zA-Z]+")


def load_keys(path=os.path.expanduser("~/.secrets/ac_keys.env")):
    for line in io.open(path, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def correct(text, key):
    body = json.dumps({"document": {"content": text, "language": "ko-KR"},
                       "encoding_type": "UTF8"}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "api-key": key})
    with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
        return json.loads(r.read().decode("utf-8"))


def 사라진_Pool낱말(before, after):
    """교정 때문에 **없어진** 낱말 중 Pool 이 쓰는 것. 하나라도 있으면 그 줄은 물리친다."""
    a, b = WORD.findall(before), WORD.findall(after)
    gone = [w for w in a if a.count(w) > b.count(w)]
    return [w for w in gone if POOL_FORMS.get(w)]


def 낭독줄(path):
    raw = io.open(path, encoding="utf-8").read()
    head, _, rest = raw.partition("## INTRO")
    out = []
    for ln in ("## INTRO" + rest).split("\n"):
        s = ln.rstrip()
        t = s.strip()
        skip = (not t) or t.startswith(("#", ">", "**[", "---", "|", "- ",
                                        "1)", "2)", "3)", "4)"))
        out.append((s, not skip))
    return head, out


def 검사(path, key, 알림=None):
    """**한 줄씩** 보낸다.

    덩어리로 보내면 바른이 문서를 통째로 다시 흘려서 줄 대응이 깨진다 — 한 줄의 교정 자리에
    뒤따르는 수십 줄이 합쳐져 돌아온다(2026-09-21 실측). 줄 수가 늘어도 한 줄씩이 정확하다.
    """
    head, lines = 낭독줄(path)
    said = [i for i, (_, ok) in enumerate(lines) if ok]
    took, threw = {}, []
    for n, i in enumerate(said, 1):
        a = lines[i][0]
        if not a.strip():
            continue
        try:
            r = correct(a, key)
        except urllib.error.HTTPError as e:
            raise SystemExit("바른 호출 실패 %s — %s" % (e.code, e.read()[:200]))
        b = (r.get("revised") or a).strip()
        if 알림 and n % 20 == 0:
            print("   … %d/%d" % (n, len(said)), file=sys.stderr)
        if b == a.strip():
            continue
        bad = 사라진_Pool낱말(a, b)
        if bad:
            threw.append((i, a, b, bad))
        else:
            took[i] = b
    return head, lines, said, took, threw


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    load_keys()
    key = os.environ.get("BAREUN_API_KEY")
    if not key:
        raise SystemExit("BAREUN_API_KEY 가 없다 — ~/.secrets/ac_keys.env 에 `BAREUN_API_KEY=koba-...`")

    for path in args:
        head, lines, said, took, threw = 검사(path, key)
        print("=" * 78)
        print("%s — 낭독 %d줄 · 받은 교정 **%d줄** · Pool 을 건드려 물리친 것 **%d줄**"
              % (os.path.basename(path), len(said), len(took), len(threw)))

        if took:
            print("\n── 받은 교정 ──")
            for i in sorted(took):
                print("\n  전  %s" % lines[i][0])
                print("  후  %s" % took[i])
                for d in difflib.ndiff(lines[i][0].split(), took[i].split()):
                    if d[0] in "-+":
                        print("      %s" % d)
        if threw:
            print("\n── 물리친 교정 (Pool 이 쓰는 낱말을 건드렸다) ──")
            for i, a, b, bad in threw:
                print("\n  바른 제안  %s" % b)
                print("  없앤 낱말  %s  ← Pool 에 %s" % (
                    ", ".join(bad), " · ".join("%s %d번" % (w, POOL_FORMS[w]) for w in bad)))

        if "--적용" in sys.argv and took:
            out = re.sub(r"\.md$", "_어법교정.md", path)
            new = [took.get(i, s) for i, (s, _) in enumerate(lines)]
            io.open(out, "w", encoding="utf-8", newline="").write(head + "\n".join(new))
            print("\n  → %s (원본은 그대로)" % os.path.basename(out))
