# -*- coding: utf-8 -*-
"""판정관 시험 — 사람(이정찬·팀장)이 고른 문장을 모델도 고르는가.
순서를 바꿔 두 번 묻는다. 조건: G(기준 없음) / R(팀장 피드백 원문을 기준으로 줌)."""
import io, os, json, re, sys, time, math
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kapi

HERE = os.path.dirname(os.path.abspath(__file__))
세트 = json.load(io.open(os.path.join(HERE, "testset.json"), encoding="utf-8"))

기준문 = """[팀장 피드백 원문]
- Remix의 핵심은 내용이 아닌 표현이다. '사람이 읽었을 때'를 기준으로, 이음새를 더 부드럽게.
- 리듬감 부족 (종결어미의 단조로움 + 늘어지는 호흡). 불필요한 기초 개념은 간략하게 (하지만 주어는 반드시 넣어줌).
- 대화형 어미와 접속사 생략 (하지만 그런데라는 표현은 좀더 덜어주세요). 기초 설명은 과감히 삭제 / 직접적인 차이와 비교에 집중.
- 행동 유도형 지시어: "매수를 예로 보겠습니다" 대신 "자, 20일선 우상향 확인하셨죠? 여기서 진입합니까? 아니요, 기다립니다"
- 글이 술술 안 읽힌다. 구성보다는 어휘. '입니다' 너무 자주 반복 - 교과서 같다, 딱딱하다.
- 좀 더 시청자랑 대화하는 느낌, 친절함(교육/튜토리얼 스타일). 비교 적극적으로 사용."""


def 질문(a, b, 조건):
    head = "해외선물 매매법을 설명하는 유튜브 강의의 촬영용 대본 한 문장입니다. 같은 자리에 들어갈 두 후보 가운데, 강사가 시청자에게 말할 때 더 자연스럽고 매끄러운 한국어는 어느 쪽입니까?"
    if 조건 == "R":
        head += "\n아래 팀장 기준에 더 맞는 쪽을 고르세요.\n" + 기준문
    return [{"role": "system", "content": "당신은 한국어 유튜브 강의 대본을 다듬는 편집자입니다. 답은 A 또는 B 한 글자로만 합니다."},
            {"role": "user", "content": "%s\n\nA: %s\nB: %s\n\n답(A 또는 B):" % (head, a, b)}]


def 부르기(모델, msgs):
    for 시도 in range(4):
        try:
            if 모델.startswith("HCX-007"):
                r = kapi._post("https://clovastudio.stream.ntruss.com/v3/chat-completions/HCX-007",
                               {"messages": msgs, "maxCompletionTokens": 2048, "thinking": {"effort": "low"}},
                               {"Authorization": "Bearer " + kapi.K["CLOVA_STUDIO_API_KEY"],
                                "X-NCP-CLOVASTUDIO-REQUEST-ID": os.urandom(8).hex(), "Content-Type": "application/json"})
                return r["result"]["message"]["content"]
            if 모델.startswith("HCX"):
                return kapi.clova(msgs, 모델, 0.0, 5)
            return kapi.upstage(msgs, 모델, 0.0, 5)
        except Exception as e:
            if "429" in str(e) or "Too Many" in str(e):
                time.sleep(3 * (시도 + 1)); continue
            if 시도 == 3: return "ERR " + str(e)[:80]
            time.sleep(1)
    return "ERR"


def 뽑기(t):
    m = re.search(r"\b([AB])\b", t.strip().upper()) or re.search(r"([AB])", t.strip().upper())
    return m.group(1) if m else "?"


def 시험(모델, 조건):
    일 = []
    for i, p in enumerate(세트):
        일.append((i, "사람=B", 질문(p["버림"], p["고름"], 조건), "B"))   # 사람이 고른 문장이 B 자리
        일.append((i, "사람=A", 질문(p["고름"], p["버림"], 조건), "A"))   # 사람이 고른 문장이 A 자리
    with ThreadPoolExecutor(max_workers=3) as ex:
        답 = list(ex.map(lambda w: 뽑기(부르기(모델, w[2])), 일))
    맞 = sum(1 for w, a in zip(일, 답) if a == w[3])
    오류 = sum(1 for a in 답 if a == "?")
    b쏠림 = sum(1 for a in 답 if a == "B") / len(답) * 100
    둘다 = sum(1 for i in range(len(세트)) if 답[2 * i] == "B" and 답[2 * i + 1] == "A")
    n = len(일)
    p = sum(math.comb(n, k) for k in range(맞, n + 1)) / 2 ** n
    return 맞 / n * 100, 둘다 / len(세트) * 100, b쏠림, 오류, p, 답


if __name__ == "__main__":
    모델들 = sys.argv[1].split(",")
    조건들 = sys.argv[2].split(",") if len(sys.argv) > 2 else ["G"]
    결과 = {}
    for 조건 in 조건들:
        for m in 모델들:
            acc, both, bb, err, p, 답 = 시험(m, 조건)
            결과["%s|%s" % (m, 조건)] = 답
            print("%-14s 조건%s  사람과 일치 %5.1f%%  (두 순서 모두 맞힘 %5.1f%%)  B쏠림 %4.0f%%  못읽음 %d  p=%.4f" % (m, 조건, acc, both, bb, err, p), flush=True)
    json.dump(결과, io.open(os.path.join(HERE, "judge_%s.json" % "_".join(조건들)), "w", encoding="utf-8"), ensure_ascii=False)
