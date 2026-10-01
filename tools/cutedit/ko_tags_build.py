# -*- coding: utf-8 -*-
"""모두의 말뭉치 **형태 분석(MP)** → 자막 가름에 쓸 태그 모델을 만든다.

왜 필요한가
  자막을 구·절 단위로 가르려면 어절마다 '끝이 무슨 어미/조사인가' 를 알아야 한다.
  글자만 보고는 못 가른다 — `설정은`(명사+보조사)과 `깊은`(용언+관형형 전성어미)이 둘 다 `은` 으로 끝난다.
  말뭉치에는 그 답이 태그로 붙어 있다. 그걸 **끝꼴 → 끝 태그** 모델로 뽑아 둔다.

내놓는 것 (`tools/cutedit/data/ko_tags.json.gz`)
  **어절**  어절 그 자체 → [첫 태그, 끝 태그, 빈도]. 이게 진본이다
  끝꼴   어절 끝 2~5글자 → 가장 흔한 끝 태그 (사전에 없는 꼴에만 쓴다)
  앞꼴   어절 앞 2~4글자 → 가장 흔한 첫 태그
  보조용언 · 의존명사   말뭉치에서 실제로 VX / NNB 로 태그된 형태들

**1글자 꼴은 넣지 않는다.** 너무 모호해서 틀린 답을 준다 — `경고` 를 `고`(연결어미 EC)로,
`객관적인` 을 `인`(명사 NNG)으로 읽었다. 둘 다 자막을 엉뚱한 자리에서 끊게 만들었다 (2026-10-01 실측).

    python3 tools/cutedit/ko_tags_build.py <MP json…> [-o tools/cutedit/data/ko_tags.json.gz]
"""
import io, os, sys, json, gzip
from collections import Counter, defaultdict

최대끝, 최소끝 = 5, 2     # 1글자 꼴은 안 쓴다 — `고`·`인` 처럼 모호해서 틀린다
최대앞, 최소앞 = 4, 2
최소빈도 = 3            # 이보다 드문 꼴은 버린다 (크기·잡음)


def 모으기(경로들):
    낱 = defaultdict(Counter)       # 어절 → (첫태그, 끝태그) 빈도
    끝 = defaultdict(Counter)       # 끝꼴 → 끝 태그 빈도
    앞 = defaultdict(Counter)       # 앞꼴 → 첫 태그 빈도
    보조, 의존 = Counter(), Counter()
    어절수 = 0
    for p in 경로들:
        d = json.load(io.open(p, encoding="utf-8"))
        for 문서 in d.get("document", []):
            for 문장 in 문서.get("sentence", []):
                형태소 = 문장.get("MP") or []
                if not 형태소: continue
                덩이 = defaultdict(list)
                for m in 형태소:
                    덩이[m["word_id"]].append((m.get("position", 0), m["form"], m["label"]))
                for wid, 들 in 덩이.items():
                    들.sort()
                    꼴 = "".join(f for _, f, _ in 들)
                    # 문장부호는 떼고 본다 — 자막에서는 어차피 뗀다
                    알 = [(f, l) for _, f, l in 들 if not l.startswith("S")]
                    if not 알 or not 꼴: continue
                    어절수 += 1
                    글 = "".join(f for f, _ in 알)
                    첫태, 끝태 = 알[0][1], 알[-1][1]
                    낱[글][(첫태, 끝태)] += 1
                    for k in range(최소끝, 최대끝 + 1):
                        if len(글) > k: 끝[글[-k:]][끝태] += 1   # 어절 전체와 같으면 사전 몫이다
                    for k in range(최소앞, 최대앞 + 1):
                        if len(글) > k: 앞[글[:k]][첫태] += 1
                    if 첫태 == "VX": 보조[알[0][0]] += 1
                    if 첫태 == "NNB": 의존[알[0][0]] += 1
    return 낱, 끝, 앞, 보조, 의존, 어절수


def 추리기(표, 최소=최소빈도):
    낼것 = {}
    for 꼴, c in 표.items():
        n = sum(c.values())
        if n < 최소: continue
        태, 수 = c.most_common(1)[0]
        낼것[꼴] = [태, round(수 / n, 3), n]
    return 낼것


def 사전추리기(낱):
    """어절 → [첫태그, 끝태그, 빈도]. 두 번 이상 나온 것만 (한 번짜리는 오타·잡음이 많다)."""
    낼것 = {}
    for 글, c in 낱.items():
        n = sum(c.values())
        if n < 2: continue
        (첫, 끝), 수 = c.most_common(1)[0]
        낼것[글] = [첫, 끝, n]
    return 낼것


if __name__ == "__main__":
    인자 = sys.argv[1:]
    낼곳 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ko_tags.json.gz")
    if "-o" in 인자:
        k = 인자.index("-o"); 낼곳 = 인자[k + 1]; del 인자[k:k + 2]
    낱, 끝, 앞, 보조, 의존, 어절수 = 모으기(인자)
    꾸러미 = {
        "어절수": 어절수,
        "어절": 사전추리기(낱),
        "끝꼴": 추리기(끝),
        "앞꼴": 추리기(앞),
        "보조용언": [w for w, n in 보조.most_common() if n >= 3],
        "의존명사": [w for w, n in 의존.most_common() if n >= 3],
    }
    os.makedirs(os.path.dirname(낼곳), exist_ok=True)
    with gzip.open(낼곳, "wt", encoding="utf-8") as f:
        json.dump(꾸러미, f, ensure_ascii=False)
    print("어절 %d개 → 사전 %d · 끝꼴 %d · 앞꼴 %d · 보조용언 %d · 의존명사 %d"
          % (어절수, len(꾸러미["어절"]), len(꾸러미["끝꼴"]), len(꾸러미["앞꼴"]),
             len(꾸러미["보조용언"]), len(꾸러미["의존명사"])))
    print("%s · %.1fMB" % (낼곳, os.path.getsize(낼곳) / 1e6))
    print("보조용언:", " ".join(꾸러미["보조용언"][:30]))
    print("의존명사:", " ".join(꾸러미["의존명사"][:30]))
