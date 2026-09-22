# -*- coding: utf-8 -*-
"""블로그 goldrivertrader(월가노트) 글 본문을 받아 사람 이름을 찾는다.

내부 검색(PostSearchList)은 대조군('금')도 0건이라 죽어 있다 — 그래서 본문을 직접 받아 센다.
"""
import html
import io
import re
import time
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
KW = ["강민호", "마이노", "Myno", "myno", "골드리버", "goldriver", "전문가", "대표", "트레이더님",
      "리딩", "실장", "팀장", "본부장", "파가드", "차트명가", "더원", "트레이딩팩토리"]
BLOG = "goldrivertrader"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": f"https://blog.naver.com/{BLOG}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def body(logno):
    s = get(f"https://blog.naver.com/PostView.naver?blogId={BLOG}&logNo={logno}"
            f"&redirect=Dlog&widgetTypeCall=true&directAccess=false")
    m = (re.search(r'<div class="se-main-container">(.*?)<!-- // se-main-container', s, re.S)
         or re.search(r'id="postViewArea"(.*?)<!--', s, re.S))
    t = m.group(1) if m else s
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    title = re.search(r'og:title" content="([^"]*)"', s)
    return (title.group(1) if title else ""), re.sub(r"\s+", " ", t).strip()


rss = io.open("rss.xml", encoding="utf-8", errors="replace").read()
logs = re.findall(r"logNo=(\d+)", rss) or re.findall(r"/(\d{12})", rss)
logs = list(dict.fromkeys(logs))
logs.append("223261968127")            # 본부장이 준 2023년 글
print(f"검사할 글 {len(logs)}편")
hits = {k: [] for k in KW}
total_chars = 0
for i, lg in enumerate(logs, 1):
    try:
        t, txt = body(lg)
    except Exception as e:
        print(f"  {lg} 실패 {type(e).__name__}")
        continue
    total_chars += len(txt)
    for k in KW:
        if k in txt or k in t:
            hits[k].append((lg, t[:40]))
    if i % 10 == 0:
        print(f"   {i}편 · 누적 {total_chars:,}자", flush=True)
    time.sleep(0.4)
print(f"\n본문 {total_chars:,}자에서 찾은 것")
for k, v in hits.items():
    if v:
        print(f"  '{k}' {len(v)}편 — 예: {v[0][1]} (logNo {v[0][0]})")
none = [k for k, v in hits.items() if not v]
print("  전혀 없음:", ", ".join(none))
