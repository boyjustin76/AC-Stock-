# -*- coding: utf-8 -*-
"""NAVER API HUB 검색 — 블로그·뉴스·카페·웹문서를 한 번에 훑는다.

    python nsearch.py "검색어" ["검색어2" ...]
헤더는 NCP API Gateway 규격(X-NCP-APIGW-API-KEY-ID / X-NCP-APIGW-API-KEY).
"""
import html
import io
import json
import re
import sys
import urllib.parse
import urllib.request

ENV = dict(l.strip().split("=", 1) for l in io.open(r"C:\Users\user\.secrets\ac_keys.env", encoding="utf-8")
           if "=" in l and not l.startswith("#"))
BASE = "https://naverapihub.apigw.ntruss.com/search/v1/"
KINDS = ("blog", "news", "cafearticle", "webkr")


def call(kind, query, display=20, start=1, sort="sim"):
    url = BASE + kind + "?" + urllib.parse.urlencode(
        {"query": query, "display": display, "start": start, "sort": sort})
    req = urllib.request.Request(url, headers={
        "X-NCP-APIGW-API-KEY-ID": ENV["NCP_APIGW_KEY_ID"],
        "X-NCP-APIGW-API-KEY": ENV["NCP_APIGW_KEY"]})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode("utf-8", "replace")[:300]}
    except Exception as e:
        return {"error": type(e).__name__, "body": str(e)[:200]}


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


for q in sys.argv[1:]:
    print(f"\n{'=' * 70}\n■ '{q}'")
    for kind in KINDS:
        d = call(kind, q)
        if "error" in d:
            print(f"  {kind:12} {d['error']} {d['body'][:160]}")
            continue
        n = d.get("total", 0)
        print(f"  {kind:12} 전체 {n:,}건")
        for it in (d.get("items") or [])[:4]:
            t = clean(it.get("title"))
            desc = clean(it.get("description"))[:80]
            src = it.get("bloggername") or it.get("cafename") or it.get("originallink") or ""
            print(f"      - {t[:52]}  [{clean(src)[:18]}]")
            print(f"        {desc}")
