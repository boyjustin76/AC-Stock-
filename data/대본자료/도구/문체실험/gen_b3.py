# -*- coding: utf-8 -*-
"""B판 3차 — 5줄씩 끊어서, 통계로 뽑은 '김직선 표현 목록'을 붙여 한국 모델이 옮겨 쓴다.
고른 판은 '김직선다움'(김직선 글자 3-gram 대 배경 12채널 로그가능도비)으로 기계가 정한다."""
import io, os, re, sys, json, math, difflib, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kapi, gen_b2, kj_profile as P
from kiwipiepy import Kiwi

HERE = os.path.dirname(os.path.abspath(__file__))
kiwi = Kiwi()
원, 고정 = gen_b2.원, set(gen_b2.고정)
prof = json.load(io.open(os.path.join(HERE, "kj_profile.json"), encoding="utf-8"))


def 겉모양(g):
    ms = [(t.rsplit("/", 1)[0], t.rsplit("/", 1)[1]) for t in g.split()]
    try:
        return kiwi.join([(f, {"EF": "EF", "EC": "EC", "JK": "JKS", "JX": "JX", "XS": "XSV", "EP": "EP", "ET": "ETM", "VC": "VCP", "VV": "VV", "VA": "VA", "VX": "VX", "MA": "MAG", "MM": "MM", "IC": "IC", "NN": "NNG", "NP": "NP", "XP": "XPN", "XR": "XR", "NR": "NR", "JC": "JC"}.get(t, t)) for f, t in ms])
    except Exception:
        return "".join(f for f, _ in ms)


def 쓰임(s, t, w=26):
    i = t.find(s)
    return t[max(0, i - w): i + len(s) + w].strip() if i >= 0 else ""


표현들, 본 = [], set()
# 말버릇만 — 대명사·어미·부사·감탄·서술격, 그리고 '거/것/생각' 같은 설명 틀. 돈·주제어는 내용이라 뺀다.
말투태그 = {"NP", "EF", "EC", "MA", "VC", "ET", "JX", "JK", "IC", "EP", "XS"}
말투명사 = {"거", "것", "생각"}
def 말버릇(g):
    for t in g.split():
        f, tag = t.rsplit("/", 1)
        if tag not in 말투태그 and not (tag == "NN" and f in 말투명사):
            return False
    return True
for p in prof:
    if not 말버릇(p["표현"]):
        continue
    s = 겉모양(p["표현"]).strip()
    if len(s) < 2 or s in 본 or s in ("매일", "거이", "는 거이"):   # 매일=수익 과장 예시 · 거이=자동자막 오타
        continue
    본.add(s)
    ctx = 쓰임(s, P.kj_t)
    if ctx:
        표현들.append("- %s  (예: …%s…)" % (s, ctx))
    if len(표현들) >= 30:
        break
목록 = "\n".join(표현들)

지시 = """[원래 대본]의 번호 붙은 줄을 유튜버 '김직선'의 말투로 옮겨 써 주세요.
[김직선이 다른 유튜버보다 유독 자주 쓰는 표현]은 김직선 자막 %d편을 다른 트레이딩 유튜버 12명과 비교해 통계로 뽑은 목록입니다. 어울리는 자리에 이런 표현과 말버릇을 써서 말투를 바꾸세요.

규칙
1. 번호 붙은 줄만, 같은 개수(%d줄)로, 같은 번호끼리 대응시켜 씁니다. 줄을 합치거나 나누지 않습니다.
2. 내용은 그대로입니다. 숫자·색·규칙·순서를 바꾸거나 없는 내용·인사를 더하지 않습니다. 강사 본인의 경험담이나 수익 이야기를 새로 지어내지 않습니다.
3. 화자는 이 채널의 강사입니다. '김직선'이라는 이름을 쓰지 않습니다.
4. 존댓말, 반말 금지, 과장된 수익 표현 금지.
5. 원문을 그대로 옮기지 말고 말투를 실제로 바꿉니다. 다만 원문 한 줄은 한 문장으로 옮기고, 문장을 덧붙이지 않습니다.
6. '~는 거예요/거죠'로 끝나는 줄은 이번 묶음에서 1줄까지만 씁니다. 김직선 실제 자막에서도 이 끝맺음은 10%% 안팎입니다. 끝맺음을 골고루 섞습니다.
7. JSON 배열 하나만 출력합니다."""


def 조각요청(모델, 번호들, 앞줄, 추가):
    본 = "\n".join("%d. %s" % (k + 1, 원[i]) for k, i in enumerate(번호들))
    msgs = [{"role": "system", "content": "당신은 한국어 유튜브 강의 대본의 말투를 바꾸는 작가입니다. JSON 배열만 출력합니다."},
            {"role": "user", "content": (지시 % (len(glob.glob(os.path.join(P.B, P.KJ, "*.srt"))), len(번호들))) + 추가
             + "\n\n[김직선이 다른 유튜버보다 유독 자주 쓰는 표현]\n" + 목록
             + "\n\n[바로 앞 줄 — 참고만, 옮기지 않음]\n" + 앞줄 + "\n\n[원래 대본]\n" + 본}]
    if 모델.startswith("HCX"):
        return kapi.clova(msgs, 모델, 0.7, 1500)
    return kapi.upstage(msgs, 모델, 0.7, 1500)


def 조각검사(번호들, 줄):
    if len(줄) != len(번호들):
        return ["줄 수 %d (원래 %d)" % (len(줄), len(번호들))]
    문제 = []
    for i, b in zip(번호들, 줄):
        a = 원[i]
        if sorted(re.findall(r"\d+", a)) != sorted(re.findall(r"\d+", b)): 문제.append("숫자 바뀜: " + b[:20])
        for w in ("빨간", "검정", "보조밴드", "메인밴드", "중심선", "안쪽"):
            if w in a.replace(" ", "") and w not in b.replace(" ", ""): 문제.append("'%s' 빠짐" % w)
        if "김직선" in b: 문제.append("김직선 이름")
        문장수 = lambda t: len([x for x in re.split(r"(?<=[.?!])\s+", t.strip()) if x])
        if 문장수(b) > 문장수(a): 문제.append("문장 덧붙임: " + b[-24:])
        if re.search(r"(저는|저도|제가)[^.?!]*(했어요|했었|곤 했|그랬|예전에)", b) and not re.search(r"(저는|저도|제가)", a):
            문제.append("지어낸 경험담: " + b[:24])
    거체 = sum(1 for b in 줄 if re.search(r"거(예요|에요|죠|였죠|였어요)[.?!]?$", b.strip()))
    if 거체 > 1: 문제.append("'~거예요/거죠'로 끝나는 줄 %d개 — 1개까지" % 거체)
    # 짧은 줄("아직이에요.")은 이미 대화체라 바꿀 게 없다 — 베낌 계산에서 뺀다
    긴 = [(i, b) for i, b in zip(번호들, 줄) if len(원[i]) >= 12]
    같음 = sum(1 for i, b in 긴 if difflib.SequenceMatcher(None, 원[i], b).ratio() > 0.9) / max(1, len(긴))
    if 같음 > 0.6: 문제.append("베낌 %.0f%%" % (같음 * 100))
    return 문제


def 만들기(모델):
    모델들 = 모델.split("+")                       # 예: solar-pro4+HCX-005 — 조각마다 앞 모델이 실패하면 다음 모델
    바꿀 = [i for i in range(len(원)) if i not in 고정]
    새 = list(원)
    원문유지 = []
    for s in range(0, len(바꿀), 5):
        번호들 = 바꿀[s:s + 5]
        추가 = ""
        for 시도 in range(4 * len(모델들)):
            t = 조각요청(모델들[시도 // 4], 번호들, 원[번호들[0] - 1] if 번호들[0] else "", 추가)
            j = re.search(r"\[.*\]", t, re.S)
            try: 줄 = [str(x).strip() for x in json.loads(j.group(0))] if j else []
            except Exception: 줄 = []
            문제 = 조각검사(번호들, 줄)
            if not 문제:
                for i, b in zip(번호들, 줄): 새[i] = b
                break
            추가 = "\n\n[이전 시도의 문제 — 꼭 고치세요] " + "; ".join(문제[:8])
        else:
            # 끝내 통과 못 한 조각은 A판 원문을 그대로 둔다 — 규칙을 풀지 않는다. 남긴 자리는 기록한다.
            원문유지.append("%d~%d줄" % (번호들[0] + 1, 번호들[-1] + 1))
    return 새, ("원문 유지: " + ", ".join(원문유지)) if 원문유지 else ""


# 김직선다움 — 김직선 글자 3-gram 대 배경
import channel_llr as C
Pk = C.삼그램(C.정리(P.kj_t)); Pb = C.삼그램(C.정리(P.bg_t))
def 다움(줄들):
    s = " ".join(l for i, l in enumerate(줄들) if i not in 고정)
    return (Pk.lp(s) - Pb.lp(s)) / max(1, len(C.정리(s)))


if __name__ == "__main__":
    print("A판(원래) 김직선다움 %.4f" % 다움(원))
    for m in sys.argv[1:]:
        새, 왜 = 만들기(m)
        if 새 is None:
            print("%-12s 실패 — %s" % (m, 왜)); continue
        io.open(os.path.join(HERE, "B3_%s.txt" % m), "w", encoding="utf-8").write("\n".join(새))
        print("%-12s 완료 · 김직선다움 %.4f (A판 대비 %+.4f) %s" % (m, 다움(새), 다움(새) - 다움(원), 왜), flush=True)
