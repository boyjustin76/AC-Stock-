# -*- coding: utf-8 -*-
"""**더원트레이더 - 숏폼** 자막(.srt) 대본 인덱스.

⚠ 차트명가와 섞지 말 것. 다른 시리즈다.
   차트명가(숏폼)  회차 이름 `SL_차XX_#N` · 폴더 `03_영상_소스_숏츠/차트명가(숏)`
                   대본·규칙은 tools/shortform.py, 자막 실측은 log/SCRIPT-LAB.md
   더원트레이더(숏) 회차 이름 `SNNN_제목_YYMMDD` · 폴더 `더원트레이더_JG/숏폼_프로젝트모음`
                   이 파일이 그 시리즈 전용이다. 두 시리즈는 대본 뼈대도 길이도 다르다.

하는 일 —
  · .srt 를 읽어 회차별 요약(길이·글자수·초당 글자수·훅·마무리)을 만든다
  · 자막 큐를 **말 덩어리**로 다시 묶는다 (0.45초 이상 벌어지면 새 덩어리)
  · 본 나레이션 뒤에 붙은 라이브·설명 구간을 따로 표시한다
  · 낱말을 세어 회차별 주제어를 뽑고, 회차끼리 겹치는 주제를 이어 준다

    python3 tools/theone/srt_index.py <폴더> --out <인덱스.md> --json <인덱스.json>
    python3 tools/theone/srt_index.py <폴더> --ref S012      # 특정 편의 레퍼런스 찾기
"""
import argparse
import io
import json
import os
import re
from collections import Counter

GAP = 0.45          # 이보다 벌어지면 다른 말 덩어리
TAIL_GAP = 20.0     # 본편이 끝나고 이만큼 비면 뒤는 딴 구간(라이브·설명)으로 본다
EP = re.compile(r"^[Ss](\d{3})[_ ](.+?)_(\d{6})\.srt$")

# 세지 않을 흔한 말 — 주제어를 뽑을 때 걸러낸다
STOP = set("""그리고 하지만 그래서 또는 이런 저런 그런 이렇게 저렇게 그렇게 여러분 여러분들
있습니다 없습니다 합니다 됩니다 입니다 것을 것이 것은 수가 수는 때문 때문에 경우 정도 다시
바로 보고 보면 보는 하는 하면 되는 되면 우리 우리가 저는 제가 많이 아주 매우 조금 가장
확인 활용 사용 관점 기준 신호 구간 자리 방법 매매 가격 차트 위로 아래 위에 아래로 아래에
첫 번째 두 세 이상 이하 만약 만약에 이번 오늘 지금 여기 여기서 어떤 무슨 왜 다 더""".split())
# 이 시리즈에서 실제로 주제를 가르는 말들 — 세는 대상
TOPIC = ("이동평균선 이평선 20일 60일 120일 단기 중기 장기 기울기 눌림목 지지 저항 "
         "골든크로스 데드크로스 추세추종 역추세 추세 볼린저밴드 밴드 표준편차 리테스트 "
         "이탈 안착 돌파 RSI 과매수 과매도 다이버전스 50선 원칙 손절 익절 진입 관망 "
         "양봉 음봉 꼬리 반등 고점 저점 종가 몸통").split()


def parse(path):
    s = io.open(path, encoding="utf-8-sig", errors="replace").read().replace("\r\n", "\n")
    out = []
    for blk in re.split(r"\n\s*\n", s.strip()):
        L = [x for x in blk.split("\n") if x.strip()]
        if not L:
            continue
        i = 1 if re.match(r"^\d+$", L[0]) else 0
        if i >= len(L) or "-->" not in L[i]:
            continue
        m = re.search(r"([\d:,]+)\s*-->\s*([\d:,]+)", L[i])
        out.append({"s": sec(m.group(1)), "e": sec(m.group(2)),
                    "t": " ".join(L[i + 1:]).strip()})
    return out


def sec(t):
    h, m, r = t.split(":")
    s, ms = (r.split(",") + ["0"])[:2]
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def tc(x):
    return f"{int(x // 60):02d}:{x % 60:05.2f}"


def chunks(cues, gap=GAP):
    """자막 큐 → 말 덩어리."""
    out = []
    for c in cues:
        if out and c["s"] - out[-1]["e"] <= gap:
            out[-1]["e"] = c["e"]
            out[-1]["t"] += " " + c["t"]
        else:
            out.append(dict(c))
    return out


def topics(text, n=8):
    c = Counter(w for w in TOPIC if w in text)
    for w in TOPIC:
        c[w] = text.count(w)
    return [w for w, k in c.most_common(n) if k]


def load(folder):
    eps = []
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".srt"):
            continue
        m = EP.match(fn)
        no, title, date = (m.group(1), m.group(2), m.group(3)) if m else ("???", fn[:-4], "")
        cues = parse(os.path.join(folder, fn))
        if not cues:
            continue
        ch = chunks(cues)
        # 본편 / 뒤에 붙은 구간 가르기
        main, tail = ch, []
        for k in range(1, len(ch)):
            if ch[k]["s"] - ch[k - 1]["e"] >= TAIL_GAP:
                main, tail = ch[:k], ch[k:]
                break
        body = " ".join(c["t"] for c in main)
        eps.append({
            "no": no, "title": title, "date": date, "file": fn,
            "cues": len(cues), "len": round(cues[-1]["e"], 1),
            "main_len": round(main[-1]["e"] - main[0]["s"], 1),
            "chars": len(re.sub(r"\s", "", body)),
            "cps": round(len(re.sub(r"\s", "", body)) / max(1, main[-1]["e"] - main[0]["s"]), 2),
            "hook": " ".join(c["t"] for c in main[:1])[:60],
            "topics": topics(body),
            "main": main, "tail": tail,
        })
    return eps


def write_md(eps, path):
    L = ["# 더원트레이더 — 숏폼 대본 인덱스", "",
         "> ⚠ **차트명가와 다른 시리즈다.** 차트명가 숏폼(`SL_차XX_#N`)의 규칙·분량·"
         "뼈대를 여기에 적용하지 말 것.",
         f"> 원본: `더원트레이더_JG/숏폼_프로젝트모음` · 자막 {len(eps)}편", "",
         "## 회차", "",
         "| 회차 | 제목 | 날짜 | 본편 | 글자 | 초당 | 큐 | 주제어 |",
         "|---|---|---|---|---|---|---|---|"]
    for e in eps:
        L.append(f"| S{e['no']} | {e['title']} | {e['date']} | {e['main_len']:.0f}초 | "
                 f"{e['chars']}자 | {e['cps']:.2f} | {e['cues']} | "
                 f"{' · '.join(e['topics'][:5])} |")
    L += ["", "## 회차별 내용 (타임코드는 그 편 자막 기준)", ""]
    for e in eps:
        L += [f"### S{e['no']} {e['title']} ({e['date']})", "",
              f"`{e['file']}` · 본편 {e['main_len']:.1f}초 · {e['chars']}자 · "
              f"초당 {e['cps']:.2f}자", ""]
        for c in e["main"]:
            L.append(f"- `{tc(c['s'])}–{tc(c['e'])}` {c['t']}")
        if e["tail"]:
            L += ["", "**본편 뒤에 붙은 구간** (라이브·현장 설명 — 그대로 쓰는 문구가 아니다)", ""]
            for c in e["tail"]:
                L.append(f"- `{tc(c['s'])}–{tc(c['e'])}` {c['t'][:110]}")
        L.append("")
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(L))


def find(folder, keys, pad=2):
    """낱말이 나오는 자리를 회차별로 — 앞뒤 큐를 붙여 문맥째 돌려준다."""
    out = []
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".srt"):
            continue
        m = EP.match(fn)
        no = m.group(1) if m else "???"
        cues = parse(os.path.join(folder, fn))
        hits = [i for i, c in enumerate(cues) if any(k in c["t"] for k in keys)]
        runs = []
        for i in hits:
            if runs and i - runs[-1][-1] <= 4:
                runs[-1].append(i)
            else:
                runs.append([i])
        for r in runs:
            a, b = max(0, r[0] - pad), min(len(cues), r[-1] + pad + 1)
            out.append({"no": no, "file": fn, "s": cues[a]["s"], "e": cues[b - 1]["e"],
                        "t": " ".join(c["t"] for c in cues[a:b])})
    return out


def refs(folder, eps, no):
    """어떤 회차의 주제어로 다른 회차를 훑어 레퍼런스 후보를 뽑는다."""
    me = next((e for e in eps if e["no"].lstrip("0") == no.lstrip("0S").lstrip("0")), None)
    if me is None:
        return []
    keys = [k for k in me["topics"] if len(k) >= 2]
    out = [h for h in find(folder, keys) if h["no"] != me["no"]]
    for h in out:
        h["keys"] = [k for k in keys if k in h["t"]]
    out.sort(key=lambda h: (-len(h["keys"]), h["no"], h["s"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out")
    ap.add_argument("--json")
    ap.add_argument("--ref", help="이 회차(예: S012)의 레퍼런스 후보를 다른 편에서 찾는다")
    ap.add_argument("--find", nargs="+", help="낱말이 나오는 자리를 타임코드로 찾는다")
    a = ap.parse_args()
    eps = load(a.folder)
    if a.find:
        for h in find(a.folder, a.find):
            print(f"S{h['no']}  {tc(h['s'])}-{tc(h['e'])}  {h['t'][:100]}")
        return
    if a.ref:
        for h in refs(a.folder, eps, a.ref)[:30]:
            print(f"S{h['no']}  {tc(h['s'])}-{tc(h['e'])}  [{'·'.join(h['keys'])}]"
                  f"  {h['t'][:88]}")
        return
    for e in eps:
        print(f"S{e['no']} {e['title'][:34]:<36} {e['main_len']:6.1f}초 "
              f"{e['chars']:4d}자 {e['cps']:.2f}자/초  {' · '.join(e['topics'][:4])}")
    if a.out:
        write_md(eps, a.out)
        print(f"\n→ {a.out}")
    if a.json:
        json.dump(eps, io.open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"→ {a.json}")


if __name__ == "__main__":
    main()
