# -*- coding: utf-8 -*-
"""B판 4차 — A판 한 줄마다 뜻이 가까운 김직선 '실제 문장' 3개를 붙여, 그 문장 틀에 우리 내용을 끼우게 한다.
허용(이정찬 2026-09-22): 부연 한 문장 · '~는 거예요' 15%까지 · 1인칭 의견. 금지: 경험담·수익 이야기·새 사실."""
import io, os, re, sys, json, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kapi, kj_retrieve as R

HERE = os.path.dirname(os.path.abspath(__file__))
원 = [l for l in io.open(os.path.join(HERE, "A_판.txt"), encoding="utf-8").read().split("\n") if l.strip()]
고정 = {i for i, l in enumerate(원) if l.startswith(("[차트", "INTRO.", "3."))}
# 팀장 F2-4 를 반영한 묻고 답하는 줄 · 이정찬이 '하지만'을 넣은 줄은 손대지 않는다
고정 |= {i for i, l in enumerate(원) if l.startswith(("자, 화면에서 20일선", "여기서 진입", "아니요, 아직", "그럼 이제 들어갈까요", "아직이에요", "하지만 상단 하단"))}
바꿀 = [i for i in range(len(원)) if i not in 고정]
참고 = dict(zip(바꿀, R.찾기([원[i] for i in 바꿀], k=3)))

지시 = """[원래 대본]의 번호 붙은 줄을, 줄마다 붙인 [김직선 실제 문장]의 말투와 문장 틀을 빌려 다시 써 주세요.
[김직선 실제 문장]은 유튜버 김직선이 실제로 한 말(자동 자막)입니다. 그 말의 어미·말버릇·호흡을 가져오고, 내용은 우리 원래 줄의 것을 넣습니다.

규칙
1. 번호 붙은 줄만, 같은 개수(%d줄)로, 같은 번호끼리 대응시킵니다. 줄을 합치거나 빼지 않습니다.
2. 내용은 그대로입니다. 숫자·색·규칙·순서를 바꾸지 않고, 새 사실·인사를 더하지 않습니다.
3. 한 줄에 같은 뜻을 한 번 더 풀어 말하는 부연 문장 하나까지는 괜찮습니다. 새 정보는 안 됩니다.
4. '저는 ~라고 봅니다' 같은 1인칭 의견은 괜찮습니다. 강사 본인의 경험담('저도 예전에', '저는 ~했어요')이나 수익 이야기는 쓰지 않습니다.
5. '~는 거예요/거죠'로 끝나는 줄은 이번 묶음에서 1줄까지. 끝맺음을 골고루 섞습니다.
6. 화자는 이 채널의 강사입니다. '김직선' 이름을 쓰지 않습니다. 존댓말, 반말 금지, 과장된 수익 표현 금지. 맞춤법을 지킵니다.
7. 원문을 그대로 옮기지 말고 말투를 실제로 바꿉니다.
8. 문자열만 담은 JSON 배열 하나만 출력합니다. 예: ["첫 줄", "둘째 줄"]"""


def 요청(모델, 번호들, 추가):
    몸 = []
    for k, i in enumerate(번호들):
        몸.append("%d. %s" % (k + 1, 원[i]))
        몸 += ["   [김직선 실제 문장] %s" % s for s, _, _ in 참고[i]]
    msgs = [{"role": "system", "content": "당신은 한국어 유튜브 강의 대본의 말투를 바꾸는 작가입니다. JSON 배열만 출력합니다."},
            {"role": "user", "content": (지시 % len(번호들)) + 추가 + "\n\n[원래 대본]\n" + "\n".join(몸)}]
    if 모델.startswith("HCX"):
        return kapi.clova(msgs, 모델, 0.6, 1500)
    return kapi.upstage(msgs, 모델, 0.6, 1500)


def 풀기(t):
    j = re.search(r"\[.*\]", t, re.S)
    try:
        arr = json.loads(j.group(0)) if j else []
    except Exception:
        return []
    out = []
    for x in arr:
        if isinstance(x, dict):                        # {'text': ...} 꼴로 주는 모델이 있다
            x = x.get("text") or next(iter(x.values()), "")
        out.append(re.sub(r"^\s*\d+\s*[.)]\s*", "", str(x)).strip())   # 모델이 붙인 "1. " 번호를 뗀다
    return out


def 문장수(t):
    return len([x for x in re.split(r"(?<=[.?!])\s+", t.strip()) if x])


def 검사(번호들, 줄):
    if len(줄) != len(번호들):
        return ["줄 수 %d (원래 %d)" % (len(줄), len(번호들))]
    문제 = []
    for i, b in zip(번호들, 줄):
        a = 원[i]
        if sorted(re.findall(r"\d+", a)) != sorted(re.findall(r"\d+", b)): 문제.append("숫자 바뀜: " + b[:20])
        for w in ("빨간", "검정", "보조밴드", "메인밴드", "중심선", "안쪽", "20일"):
            if w in a.replace(" ", "") and w not in b.replace(" ", ""): 문제.append("'%s' 빠짐" % w)
        if "김직선" in b: 문제.append("김직선 이름")
        if 문장수(b) > 문장수(a) + 1: 문제.append("문장 둘 이상 덧붙임")
        if re.search(r"(저도|저는|제가)[^.?!]{0,30}(했어요|했었|곤 했|그랬|예전에|벌었|잃었|진입한|진입했)", b):
            문제.append("경험담: " + b[:26])
        if re.search(r"(구요|이예요)", b): 문제.append("맞춤법: " + b[:20])
        if re.search(r"제가 (들어간|진입한|잡은|산|판)", b): 문제.append("경험담: " + b[:26])
        for w in ("이탈", "두 번 다"):
            if w in a and w not in b: 문제.append("'%s' 빠짐" % w)
        # 부연으로 김직선 문장을 그대로 붙였는가 — 베껴 붙이기 금지
        for 문 in re.split(r"(?<=[.?!])\s+", b):
            for 김, _, _ in 참고[i]:
                if len(문) > 8 and difflib.SequenceMatcher(None, 문, 김).ratio() > 0.7:
                    문제.append("김직선 문장 베껴 붙임: " + 문[:20])
        if re.search(r"(합시다|더라고요|같은 뜻|풀어 보면|한 번 더 풀)", b): 문제.append("말투·지시문 새어 나옴: " + b[:20])
        for w in ("타고", "따라"):
            if w in a and w not in b: 문제.append("밴드 타기 표현 '%s' 빠짐" % w)
    # 뜻 보존 — A 줄과 B 줄의 뜻 벡터가 0.72 이상 (2026-09-22 실측: 내용 빠진 줄 0.36~0.68, 보존된 줄 0.75~)
    import numpy as _np
    A = R.임베딩([원[i] for i in 번호들], "embedding-query"); Bv = R.임베딩(줄, "embedding-query")
    for k, i in enumerate(번호들):
        c = float(A[k] @ Bv[k])
        if c < 0.72: 문제.append("%d번째 줄 뜻이 달라짐(유사도 %.2f): %s" % (k + 1, c, 줄[k][:18]))
    거체 = sum(1 for b in 줄 if re.search(r"거(예요|에요|죠|였죠|였어요)[.?!]?$", b.strip()))
    if 거체 > 1: 문제.append("'~거예요/거죠' %d줄 — 1줄까지" % 거체)
    긴 = [(i, b) for i, b in zip(번호들, 줄) if len(원[i]) >= 12]
    if 긴 and sum(1 for i, b in 긴 if difflib.SequenceMatcher(None, 원[i], b).ratio() > 0.9) / len(긴) > 0.6:
        문제.append("베낌")
    return 문제


def 만들기(모델들):
    새, 유지 = list(원), []
    for s in range(0, len(바꿀), 5):
        번호들, 추가, 됨 = 바꿀[s:s + 5], "", False
        for 시도 in range(4 * len(모델들)):
            줄 = 풀기(요청(모델들[시도 // 4], 번호들, 추가))
            문제 = 검사(번호들, 줄)
            if not 문제:
                for i, b in zip(번호들, 줄): 새[i] = b
                됨 = True; break
            추가 = "\n\n[이전 시도의 문제 — 꼭 고치세요] " + "; ".join(문제[:8])
        if not 됨:
            유지.append("%d~%d줄" % (번호들[0] + 1, 번호들[-1] + 1))
    return 새, 유지


if __name__ == "__main__":
    import gen_b3
    print("A판 김직선다움 %.4f" % gen_b3.다움(원))
    for spec in sys.argv[1:]:
        새, 유지 = 만들기(spec.split("+"))
        io.open(os.path.join(HERE, "B4_%s.txt" % spec), "w", encoding="utf-8").write("\n".join(새))
        거 = sum(1 for i in 바꿀 if re.search(r"거(예요|에요|죠|였죠|였어요)[.?!]?$", 새[i].strip())) / len(바꿀) * 100
        print("%-32s 김직선다움 %.4f (A판 대비 %+.4f) · '~거예요' %.0f%% · 원문 유지 %s" %
              (spec, gen_b3.다움(새), gen_b3.다움(새) - gen_b3.다움(원), 거, ", ".join(유지) or "없음"), flush=True)
