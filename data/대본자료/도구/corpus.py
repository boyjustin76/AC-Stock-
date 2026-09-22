# -*- coding: utf-8 -*-
"""메이저 채널의 '많이 본 롱폼' 자막을 모아 레퍼런스 코퍼스를 만든다.

① Data API 로 채널별 업로드 목록 + 조회수·좋아요·길이 (유닛: 채널당 ~9)
② 조회수 상위 롱폼만 골라 yt-dlp 로 한국어 자막(ko-orig→ko) 받기

    python corpus.py [채널수] [채널당영상수]
산출: corpus/<채널>/<영상id>.srt · corpus/index.json
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from paths import CORP  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = CORP
NCH = int(sys.argv[1]) if len(sys.argv) > 1 else 12
NVID = int(sys.argv[2]) if len(sys.argv) > 2 else 4
MIN_SEC = 480                      # 8분 이상 = 롱폼
ENV = dict(l.strip().split("=", 1) for l in io.open(r"C:\Users\user\.secrets\ac_keys.env", encoding="utf-8")
           if "=" in l and not l.startswith("#"))
API = "https://www.googleapis.com/youtube/v3/"


def api(path, **params):
    params["key"] = ENV["YOUTUBE_API_KEY"]
    with urllib.request.urlopen(API + path + "?" + urllib.parse.urlencode(params), timeout=30) as r:
        return json.load(r)


def iso_sec(s):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    h, mi, se = (int(x or 0) for x in m.groups()) if m else (0, 0, 0)
    return h * 3600 + mi * 60 + se


def uploads(cid):
    it = api("channels", part="contentDetails", id=cid)["items"]
    return it[0]["contentDetails"]["relatedPlaylists"]["uploads"] if it else None


def videos_of(pl, cap=200):
    ids, tok = [], None
    while len(ids) < cap:
        d = api("playlistItems", part="contentDetails", playlistId=pl, maxResults=50,
                **({"pageToken": tok} if tok else {}))
        ids += [x["contentDetails"]["videoId"] for x in d.get("items", [])]
        tok = d.get("nextPageToken")
        if not tok:
            break
    return ids[:cap]


def stats_of(ids):
    out = []
    for i in range(0, len(ids), 50):
        d = api("videos", part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50]), maxResults=50)
        for it in d.get("items", []):
            s, sn = it["statistics"], it["snippet"]
            out.append({"id": it["id"], "title": sn["title"], "date": sn["publishedAt"][:10],
                        "sec": iso_sec(it["contentDetails"]["duration"]),
                        "views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                        "comments": int(s.get("commentCount", 0))})
    return out


def subs(vid, folder):
    os.makedirs(folder, exist_ok=True)
    for lang in ("ko-orig", "ko"):
        subprocess.run([sys.executable, "-m", "yt_dlp", "--js-runtimes", "node", "--no-warnings", "--quiet",
                        "--skip-download", "--write-auto-subs", "--write-subs", "--sub-langs", lang,
                        "--sub-format", "srt/vtt", "--sleep-requests", "1",
                        "-o", os.path.join(folder, "%(id)s.%(ext)s"),
                        f"https://www.youtube.com/watch?v={vid}"],
                       capture_output=True, text=True, timeout=300)
        got = [f for f in os.listdir(folder) if f.startswith(vid) and f.endswith((".srt", ".vtt"))]
        if got:
            return got[0]
    return None


def srt_text(p):
    t = io.open(p, encoding="utf-8-sig", errors="replace").read()
    t = re.sub(r"^\d+\s*$|^\d\d:\d\d:\d\d[,.]\d+ -->.*$|^WEBVTT.*$|^Kind:.*$|^Language:.*$", "", t, flags=re.M)
    lines, seen = [], None
    for ln in (x.strip() for x in t.split("\n")):
        if ln and ln != seen:                      # vtt 롤링 중복 제거
            lines.append(ln)
            seen = ln
    return " ".join(lines)


majors = json.load(io.open(os.path.join(CORP, "majors.json"), encoding="utf-8"))["rows"]
picked = [m for m in majors if m["subs"] >= 3000 and m["kw_hits"] >= 2][:NCH]
os.makedirs(OUT, exist_ok=True)
index = []
for m in picked:
    pl = uploads(m["cid"])
    if not pl:
        continue
    vs = stats_of(videos_of(pl))
    long_ = [v for v in vs if v["sec"] >= MIN_SEC]
    top = sorted(long_, key=lambda v: -v["views"])[:NVID]
    # 윈도우는 이름 끝의 공백·마침표를 못 쓴다 — 그대로 두면 다른 이름으로 만들어져 못 찾는다
    folder = os.path.join(OUT, re.sub(r'[\\/:*?"<>|#]', "_", m["name"])[:30].strip(" ._"))
    print(f"{m['name'][:20]:22} 구독 {m['subs']:>9,} · 영상 {len(vs):3d}개(롱폼 {len(long_):3d}) → 상위 {len(top)}편", flush=True)
    for v in top:
        t0 = time.time()
        f = subs(v["id"], folder)
        txt = srt_text(os.path.join(folder, f)) if f else ""
        index.append({**v, "channel": m["name"], "cid": m["cid"], "subs": m["subs"],
                      "file": os.path.join(os.path.basename(folder), f) if f else None, "chars": len(txt),
                      "cps": round(len(txt) / max(1, v["sec"]), 2)})
        print(f"   {v['views']:>9,}회 ♥{v['likes']:>6,} {v['sec'] // 60:>3}분  {v['title'][:34]:36} "
              f"{'자막 ' + str(len(txt)) + '자' if txt else '자막 없음'} ({time.time() - t0:.0f}초)", flush=True)

io.open(os.path.join(OUT, "index.json"), "w", encoding="utf-8").write(
    json.dumps(index, ensure_ascii=False, indent=1))
ok = [x for x in index if x["chars"] > 500]
print(f"\n영상 {len(index)}편 중 자막 확보 {len(ok)}편 · 총 {sum(x['chars'] for x in ok):,}자 → corpus/index.json")
