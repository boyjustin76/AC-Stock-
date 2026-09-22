# -*- coding: utf-8 -*-
"""국내 해외선물·트레이딩 유튜브 '메이저 채널' 추리기.

① yt-dlp 검색으로 키워드마다 상위 N개를 모아 **채널별 등장 횟수·조회수**를 센다 (키 불필요)
② 후보 채널을 YouTube Data API channels.list 로 **구독자·총조회수·영상수** 를 정확히 채운다 (1유닛/50개)

    python majors.py [검색개수]
산출: majors.json · majors.md
"""
import collections
import io
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from paths import CORP  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
HERE = os.path.dirname(os.path.abspath(__file__))
ENV = dict(l.strip().split("=", 1) for l in io.open(r"C:\Users\user\.secrets\ac_keys.env", encoding="utf-8")
           if "=" in l and not l.startswith("#"))

KEYWORDS = [
    "해외선물 매매법", "해외선물 실전 매매", "해선 매매 전략", "나스닥 선물 매매",
    "해외선물 진입 타점", "해외선물 손절 기준", "크루드오일 선물 매매", "금 선물 매매",
    "항셍 선물 매매", "해외선물 스캘핑", "해외선물 추세매매", "해외선물 눌림목",
    "해외선물 볼린저밴드", "해외선물 이동평균선", "해외선물 보조지표", "해외선물 초보",
]


def search(kw):
    p = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--js-runtimes", "node", "--no-warnings", "--flat-playlist",
         "--print", "%(channel)s\t%(channel_id)s\t%(view_count)s\t%(duration)s\t%(title)s",
         f"ytsearch{N}:{kw}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    out = []
    for ln in p.stdout.splitlines():
        f = ln.split("\t")
        if len(f) == 5 and f[1].startswith("UC"):
            out.append({"channel": f[0], "cid": f[1], "views": int(f[2]) if f[2].isdigit() else 0,
                        "dur": int(f[3]) if f[3].isdigit() else 0, "title": f[4], "kw": kw})
    return out


rows = []
for kw in KEYWORDS:
    r = search(kw)
    rows += r
    print(f"  {kw:22} {len(r):3d}건", flush=True)

by = collections.defaultdict(list)
for r in rows:
    by[r["cid"]].append(r)
cand = sorted(by.items(), key=lambda x: (-len({v["kw"] for v in x[1]}), -sum(v["views"] for v in x[1])))[:40]

# ── API 로 정확한 채널 지표
stats = {}
for i in range(0, len(cand), 50):
    ids = ",".join(c for c, _ in cand[i:i + 50])
    u = "https://www.googleapis.com/youtube/v3/channels?" + urllib.parse.urlencode(
        {"part": "snippet,statistics", "id": ids, "key": ENV["YOUTUBE_API_KEY"]})
    for it in json.load(urllib.request.urlopen(u, timeout=30)).get("items", []):
        s = it["statistics"]
        stats[it["id"]] = {"title": it["snippet"]["title"],
                           "subs": int(s.get("subscriberCount", 0)), "views": int(s.get("viewCount", 0)),
                           "videos": int(s.get("videoCount", 0)),
                           "desc": (it["snippet"].get("description") or "").replace("\n", " ")[:120],
                           "published": it["snippet"].get("publishedAt", "")[:10]}

res = []
for cid, vs in cand:
    st = stats.get(cid, {})
    vw = sorted(v["views"] for v in vs)
    res.append({"cid": cid, "name": st.get("title") or vs[0]["channel"], "kw_hits": len({v["kw"] for v in vs}),
                "hits": len(vs), "subs": st.get("subs", 0), "ch_views": st.get("views", 0),
                "videos": st.get("videos", 0), "published": st.get("published", ""),
                "med_view": vw[len(vw) // 2], "max_view": vw[-1],
                "desc": st.get("desc", ""), "top": max(vs, key=lambda v: v["views"])["title"][:50]})
res.sort(key=lambda r: (-r["kw_hits"], -r["subs"]))

io.open(os.path.join(CORP, "majors.json"), "w", encoding="utf-8").write(
    json.dumps({"keywords": KEYWORDS, "n": N, "rows": res}, ensure_ascii=False, indent=1))
L = [f"# 해외선물·트레이딩 채널 후보 — 검색 {len(KEYWORDS)}키워드 × 상위 {N}개 집계", "",
     "| 채널 | 구독자 | 채널 총조회 | 영상수 | 걸린 키워드 | 검색노출 | 중앙조회 | 대표 영상 |",
     "|---|---|---|---|---|---|---|---|"]
for r in res:
    L.append(f"| {r['name'][:22]} | {r['subs']:,} | {r['ch_views']:,} | {r['videos']:,} | "
             f"{r['kw_hits']}/{len(KEYWORDS)} | {r['hits']} | {r['med_view']:,} | {r['top'][:40]} |")
io.open(os.path.join(CORP, "majors.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print(f"\n검색 {len(rows)}건 · 후보 채널 {len(res)}개 → majors.md")
