# -*- coding: utf-8 -*-
"""**더원트레이더 숏폼** — (대본 ↔ 화면 문구) 쌍 corpus 를 만든다.

배너 문구를 짐작으로 정하지 않으려고, 팀장이 실제로 쓴 문구와 그때의 대본을
쌍으로 모은다. 이 쌍이 곧 규칙서다 (총괄 Fable 제안, 2026-09-09).

어디서 나오나 —
  · 화면 문구 : `.prproj` 안의 텍스트 레이어(InstanceName). gzip XML 이라 그냥 읽힌다.
                상단 배너 두 줄 + 차트 라벨(지지선·매수 준비·관망…)이 다 들어 있다.
  · 대본     : 같은 회차 `.srt`.
  · 최종본 실측: 배너는 최종본 mp4 프레임에서도 읽어 대조했다 (6/6 일치).

배너는 영상 내내 고정이라 타임코드가 필요 없다 — 회차 전체 대본과 짝지으면 된다.
차트 라벨은 타임코드가 있어야 정확히 짝지을 수 있는데, prproj 의 클립 시각은
아직 안 읽는다. 그래서 라벨은 '그 회차 어딘가'로만 묶어 둔다.

    python3 tools/theone/pairs.py <숏폼_프로젝트모음> --out pairs.jsonl
"""
import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "cutedit"))
from prproj_titles import layers, read_proj          # noqa: E402
from srt_index import parse as parse_srt             # noqa: E402

# 최종본 mp4 에서 눈으로 읽은 배너 (prproj 와 대조용 · 자막/프로젝트 없는 편 포함)
BANNER_SEEN = {
    "S002": ("닿아서 매수했는데??", "20일 이평선의 배신"),
    "S003": ("볼린저밴드 이탈은 손실!?", "잡았다! 밴드타기!"),
    "S006": ("세 가지만 기억하세요!", "이평선 개념정리"),
    "S007": ("아직도 그냥 쓰세요?!", "볼린저밴드의 변신"),
    "S008": ("추세추종? 역추세?", "손실 최소화 매매법"),
    "S009": ("나만의 원칙 만들기", "W.H.W 매매기준"),
    "S010": ("일목균형표 쓰고 있다면", "다 지우고 '이것'만"),
    "S011": ("세 가지만 기억하세요!", "RSI? 쉽다 쉬워"),
    "S012": ("세 가지만 기억하세요!", "20일 이평선"),
    "S013": ("무료로 받아가세요", "프랙탈 매매지표"),
    "S014": ("이것만 바꿔보세요!", "RSI 스캘핑 매매"),
    "S015": ("싹 고쳐드립니다", "포지션 중독? 주목!"),
}
# 배너가 아니라 채널 고정 광고판 — 쌍에서 뺀다
AD = ("시장은 흔들려도", "VIP 회원", "셀퍼럴", "트레이딩룸", "기준있는 매매의 시작",
      "시크릿 지표")


def norm(t):
    return re.sub(r"[^0-9가-힣a-zA-Z]", "", t)


def ep_of(name):
    m = re.search(r"[Ss](\d{3})", name)
    return "S" + m.group(1) if m else None


def collect(folder):
    """회차별로 { prproj 텍스트, srt 큐 } 를 모은다."""
    eps = {}
    for fn in os.listdir(folder):
        p = os.path.join(folder, fn)
        if fn.lower().endswith(".srt"):
            e = ep_of(fn)
            if e:
                eps.setdefault(e, {})["cues"] = [c["t"] for c in parse_srt(p)]
        elif os.path.isdir(p) and fn.startswith("X_"):
            e = ep_of(fn)
            pr = [f for f in os.listdir(p) if f.endswith(".prproj")]
            if e and pr:
                ls = layers(read_proj(os.path.join(p, pr[0])))
                seen, txt = set(), []
                for l in ls:
                    t = l["text"].strip()
                    if l["kind"] != "Text" or not t or t in seen:
                        continue
                    if any(a in t for a in AD):
                        continue
                    seen.add(t)
                    txt.append(t)
                eps.setdefault(e, {})["screen"] = txt
    return eps


def build(folder):
    eps = collect(folder)
    rows = []
    for ep in sorted(set(list(eps) + list(BANNER_SEEN))):
        d = eps.get(ep, {})
        cues = d.get("cues") or []
        screen = d.get("screen") or []
        script = " ".join(cues)
        up, low = BANNER_SEEN.get(ep, (None, None))
        # prproj 에도 그 문구가 있나 (배너 실측 교차확인)
        conf = None
        if screen and up:
            ns = {norm(s) for s in screen}
            conf = (norm(up) in ns, norm(low) in ns)
        if up:
            rows.append({"ep": ep, "kind": "배너_윗줄", "text": up,
                         "script": script, "cues": cues,
                         "prproj확인": conf[0] if conf else None})
            rows.append({"ep": ep, "kind": "배너_아랫줄", "text": low,
                         "script": script, "cues": cues,
                         "prproj확인": conf[1] if conf else None})
        for s in screen:
            if up and norm(s) in (norm(up), norm(low)):
                continue
            rows.append({"ep": ep, "kind": "화면라벨", "text": s,
                         "script": script, "cues": cues, "prproj확인": True})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out", default="pairs.jsonl")
    a = ap.parse_args()
    rows = build(a.folder)
    with io.open(a.out, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    c = Counter(r["kind"] for r in rows)
    has = sum(1 for r in rows if r["cues"])
    print(f"쌍 {len(rows)}개 → {a.out}")
    for k, n in c.most_common():
        print(f"   {k:<10} {n}")
    print(f"   이 중 대본(.srt)이 있는 것 {has}개")
    bad = [r for r in rows if r["kind"].startswith("배너") and r["prproj확인"] is False]
    if bad:
        print("\n⚠ 최종본에서 읽은 배너가 prproj 에 없다 — 확인 필요")
        for r in bad:
            print(f"   {r['ep']} {r['kind']} |{r['text']}|")


if __name__ == "__main__":
    main()
