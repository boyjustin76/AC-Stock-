# -*- coding: utf-8 -*-
"""B판 2차 — 줄 단위 대응. 한국 모델이 쓰고, Claude 는 규칙(줄 수·고정줄·숫자·베끼기)만 기계로 검사한다."""
import io, os, re, sys, json, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kapi, gen_b

HERE = os.path.dirname(os.path.abspath(__file__))
원 = [l for l in io.open(os.path.join(HERE, "A_판.txt"), encoding="utf-8").read().split("\n") if l.strip()]
고정 = [i for i, l in enumerate(원) if l.startswith(("[차트", "INTRO.", "3."))]

지시 = """아래 [원래 대본]은 해외선물 유튜브 강의의 촬영용 대본입니다. 줄마다 번호가 붙어 있습니다.
각 줄을 [김직선 자막 예시]의 말투로 옮겨 써 주세요. (예시는 자동 자막이라 문장부호가 없습니다.)

규칙
1. 줄 수를 똑같이 %d줄로 맞추고, 같은 번호끼리 대응시킵니다. 줄을 합치거나 나누지 않습니다.
2. 번호 %s 줄은 한 글자도 바꾸지 않습니다.
3. 내용은 그대로입니다. 숫자·색·규칙·순서를 바꾸거나, 없는 내용·인사·마무리를 더하지 않습니다.
4. 화자는 이 채널의 강사입니다. '김직선'이라는 이름을 쓰거나 김직선 본인처럼 말하지 않습니다. 말투만 빌립니다.
5. 존댓말을 유지합니다. 반말, 과장된 수익 표현은 쓰지 않습니다.
6. 고정 줄이 아닌 줄은 표현을 김직선식으로 실제로 바꿉니다. 원문을 그대로 옮기지 않습니다.
7. JSON 배열 하나만 출력합니다. 예: ["1번 줄", "2번 줄", ...]"""


def 요청(모델, 추가=""):
    ex = "\n\n".join("[김직선 자막 예시 %d]\n%s" % (i + 1, e) for i, e in enumerate(gen_b.예시(5, 800)))
    본 = "\n".join("%d. %s" % (i + 1, l) for i, l in enumerate(원))
    msgs = [{"role": "system", "content": "당신은 한국어 유튜브 강의 대본의 말투를 바꾸는 작가입니다. JSON 배열만 출력합니다."},
            {"role": "user", "content": (지시 % (len(원), ", ".join(str(i + 1) for i in 고정))) + 추가 + "\n\n" + ex + "\n\n[원래 대본]\n" + 본}]
    if 모델 == "HCX-007":
        r = kapi._post("https://clovastudio.stream.ntruss.com/v3/chat-completions/HCX-007",
                       {"messages": msgs, "maxCompletionTokens": 8000, "thinking": {"effort": "medium"}},
                       {"Authorization": "Bearer " + kapi.K["CLOVA_STUDIO_API_KEY"],
                        "X-NCP-CLOVASTUDIO-REQUEST-ID": os.urandom(8).hex(), "Content-Type": "application/json"}, timeout=300)
        return r["result"]["message"]["content"]
    if 모델.startswith("HCX"):
        return kapi.clova(msgs, 모델, 0.6, 4000)
    return kapi.upstage(msgs, 모델, 0.6, 4000)


def 검사(줄):
    문제 = []
    if len(줄) != len(원):
        return ["줄 수 %d (원래 %d)" % (len(줄), len(원))], 1.0
    for i in 고정:
        if 줄[i].strip() != 원[i].strip():
            문제.append("고정줄 %d 바뀜" % (i + 1))
    for i, (a, b) in enumerate(zip(원, 줄)):
        if sorted(re.findall(r"\d+", a)) != sorted(re.findall(r"\d+", b)):
            문제.append("%d번 숫자 바뀜" % (i + 1))
        for w in ("빨간", "검정", "보조밴드", "메인밴드"):
            if w in a and w not in b.replace(" ", ""):
                문제.append("%d번 '%s' 빠짐" % (i + 1, w))
        if "김직선" in b:
            문제.append("%d번 김직선 이름" % (i + 1))
    바뀐 = [i for i in range(len(원)) if i not in 고정]
    같음 = sum(1 for i in 바뀐 if difflib.SequenceMatcher(None, 원[i], 줄[i]).ratio() > 0.9) / len(바뀐)
    if 같음 > 0.5:
        문제.append("베낌 %.0f%% (원문과 90%% 넘게 같은 줄)" % (같음 * 100))
    return 문제, 같음


if __name__ == "__main__":
    for m in sys.argv[1:]:
        추가 = ""
        for 시도 in range(3):
            t = 요청(m, 추가)
            j = re.search(r"\[.*\]", t, re.S)
            try:
                줄 = [str(x).strip() for x in json.loads(j.group(0))] if j else []
            except Exception:
                줄 = []
            문제, 같음 = 검사(줄)
            print("== %s 시도%d  문제 %d개  원문과 같은 줄 %.0f%%  %s" % (m, 시도 + 1, len(문제), 같음 * 100, "; ".join(문제[:6])), flush=True)
            if not 문제:
                io.open(os.path.join(HERE, "B2_%s.txt" % m), "w", encoding="utf-8").write("\n".join(줄))
                break
            추가 = "\n\n[이전 시도의 문제 — 꼭 고치세요] " + "; ".join(문제[:10])
