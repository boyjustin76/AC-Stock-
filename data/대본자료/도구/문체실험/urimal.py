# -*- coding: utf-8 -*-
import json, ssl, urllib.request, urllib.parse, certifi, sys
sys.path.insert(0, ".")
import kapi
CTX = ssl.create_default_context(cafile=certifi.where())
def 용례수(q):
    u = "https://opendict.korean.go.kr/api/search?" + urllib.parse.urlencode(
        {"key": kapi.K["URIMALSAEM_API_KEY"], "q": q, "req_type": "json", "part": "exam", "method": "include", "num": 10, "advanced": "y"})
    with urllib.request.urlopen(u, context=CTX, timeout=30) as r:
        t = r.read().decode("utf-8")
    try:
        d = json.loads(t)
    except Exception:
        return None, t[:150]
    ch = d.get("channel", {})
    ex = [i.get("example") or i.get("word") for i in (ch.get("item") or [])][:1]
    return ch.get("total", 0), ex
if __name__ == "__main__":
    for a, b in [("손익비가 나빠", "손익비가 낮아"), ("비율이 나빠", "비율이 낮아"), ("규칙이 짧", "조건이 적"),
                 ("알아보기 어려", "복잡해"), ("정답처럼 느껴", "정답으로 착각"), ("진입합니까", "진입하면 될까요")]:
        ra, rb = 용례수(a), 용례수(b)
        print("%-12s %6s  ↔  %-12s %6s   예) %s" % (a, ra[0], b, rb[0], (rb[1] or ra[1] or [""])[0] if isinstance(rb[1], list) else rb[1]))
