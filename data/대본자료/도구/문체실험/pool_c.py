# -*- coding: utf-8 -*-
"""C판 — Pool 조각 조립 (차13 방식). A판 한 줄마다 뜻이 가장 가까운 회사 Pool 문장을 찾아,
그 문장을 최대한 그대로 쓰고 우리 내용만 끼워 넣게 한다. 줄마다 출처(원고 파일)를 남긴다.
Pool 은 통째로 쓴다(이정찬 2026-09-22 — 제 판단으로 줄이지 말 것). 검사는 B판과 같다."""
import io, os, re, glob, json, sys, difflib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kapi, kj_retrieve as R, gen_b4 as G
from kiwipiepy import Kiwi

HERE = os.path.dirname(os.path.abspath(__file__))
POOL = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\05_대본자료\Pool"
CT, CV = os.path.join(HERE, "pool_sents_all.json"), os.path.join(HERE, "pool_vecs_masked.npy")
BAN = ["무조건", "보장", "100%", "떼돈", "대박", "하루 10만", "월 300", "일 300", "억대", "비법", "필승", "승률 9", "마법", "치트키", "꿀팁"]
kiwi = Kiwi()


def 가리기(s):
    """주제어(명사·숫자·외국어)를 ○○로 — 말투(문장 틀·어미)로만 비교하려고."""
    out, last = [], 0
    for t in kiwi.tokenize(s):
        if t.tag.startswith(("NNG", "NNP", "SN", "SL", "NR")):
            out.append(s[last:t.start] + "○○"); last = t.start + t.len
    return "".join(out) + s[last:]


def Pool문장():
    if os.path.exists(CT) and os.path.exists(CV):
        return json.load(io.open(CT, encoding="utf-8")), np.load(CV)
    본, out = set(), []
    for f in sorted(glob.glob(os.path.join(POOL, "*.txt"))):
        name = os.path.basename(f)
        t = re.sub(r"\s+", " ", io.open(f, encoding="utf-8", errors="ignore").read())
        for 조각 in re.findall(r".{1,600}(?:\s|$)", t):
            for s in kiwi.split_into_sents(조각):
                x = s.text.strip()
                if 10 <= len(x) <= 110 and x not in 본 and not any(b in x for b in BAN):
                    본.add(x); out.append({"문장": x, "원고": name})
    v = R.임베딩([가리기(d["문장"]) for d in out], "embedding-passage")
    json.dump(out, io.open(CT, "w", encoding="utf-8"), ensure_ascii=False); np.save(CV, v)
    return out, v


문장들, V = Pool문장()
원, 고정 = G.원, G.고정
바꿀 = [i for i in range(len(원)) if i not in 고정]
Q = R.임베딩([가리기(원[i]) for i in 바꿀], "embedding-query")
S = Q @ V.T
참고 = {i: [(문장들[j]["문장"], 문장들[j]["원고"], float(S[k, j])) for j in np.argsort(-S[k])[:3]] for k, i in enumerate(바꿀)}

지시 = """[원래 대본]의 번호 붙은 줄을 다시 씁니다. 줄마다 붙인 [회사 원고 틀]은 우리 회사가 방송에 쓴 대본 문장에서 낱말(○○)을 가린 것입니다.
그 **틀(어미·연결 방식·말투)을 가져오고, ○○ 자리에는 우리 원래 줄의 낱말을 채웁니다.** 회사 문장의 원래 내용(다른 주제)을 가져오면 안 됩니다.

규칙
1. 번호 붙은 줄만, 같은 개수(%d줄)로, 같은 번호끼리 대응시킵니다. 줄 앞에 번호를 붙이지 않습니다.
2. 내용은 원래 줄 그대로입니다. 숫자·색·규칙·순서를 바꾸지 않고, 새 사실을 더하지 않습니다.
3. 원래 줄을 그대로 옮기지 말고, 회사 원고 틀의 말투로 실제로 바꿉니다.
4. 존댓말, 반말 금지, 과장된 수익 표현 금지. 강사 본인의 경험담·수익 이야기 금지. 맞춤법을 지킵니다.
5. 문자열만 담은 JSON 배열 하나만 출력합니다."""


def 요청(모델, 번호들, 추가):
    몸 = []
    for k, i in enumerate(번호들):
        몸.append("%d. %s" % (k + 1, 원[i]))
        몸 += ["   [회사 원고 틀] %s" % 가리기(s) for s, _, _ in 참고[i]]
    msgs = [{"role": "system", "content": "당신은 회사가 쓰던 대본 문장을 재활용해 새 대본을 조립하는 작가입니다. JSON 배열만 출력합니다."},
            {"role": "user", "content": (지시 % len(번호들)) + 추가 + "\n\n[원래 대본]\n" + "\n".join(몸)}]
    return kapi.clova(msgs, 모델, 0.4, 1500) if 모델.startswith("HCX") else kapi.upstage(msgs, 모델, 0.4, 1500)


def 검사(번호들, 줄):
    G.참고.update({i: 참고[i] for i in 번호들})       # 베껴 붙이기 검사 대상은 김직선이 아니라 Pool — 여기선 오히려 권장이므로 끈다
    문제 = [p for p in G.검사.__wrapped__(번호들, 줄)] if hasattr(G.검사, "__wrapped__") else G.검사(번호들, 줄)
    # 김직선 베끼기 검사는 끈다(여기선 Pool 을 가져다 쓰는 게 목적). A판 베끼기는 켠다.
    문제 = [p for p in 문제 if not p.startswith(("김직선 문장 베껴 붙임", "'~거예요"))]
    # Pool 을 실제로 가져다 썼나 — 조각의 절반 이상이 Pool 문장과 40% 이상 겹쳐야 한다
    쓴 = sum(1 for i, b in zip(번호들, 줄) if max(difflib.SequenceMatcher(None, 가리기(t[0]), 가리기(b)).ratio() for t in 참고[i]) >= 0.45)
    if 쓴 < (len(번호들) + 1) // 2: 문제.append("Pool 문장을 거의 안 씀 (%d/%d줄)" % (쓴, len(번호들)))
    for b in 줄:
        if any(x in b for x in BAN): 문제.append("과장 표현: " + b[:20])
    return 문제


def 출처(i, b):
    best = max(참고[i], key=lambda t: difflib.SequenceMatcher(None, 가리기(t[0]), 가리기(b)).ratio())
    return best[1] + " — " + best[0], round(difflib.SequenceMatcher(None, 가리기(best[0]), 가리기(b)).ratio(), 2)


if __name__ == "__main__":
    print("Pool 문장 %d개 (Pool 통째) · 예) %s → %s" % (len(문장들), 원[바꿀[0]], 가리기(원[바꿀[0]])))
    모델들 = sys.argv[1].split("+")
    새, 유지 = list(원), []
    for s in range(0, len(바꿀), 5):
        번호들, 추가, 됨 = 바꿀[s:s + 5], "", False
        for 시도 in range(4 * len(모델들)):
            줄 = G.풀기(요청(모델들[시도 // 4], 번호들, 추가))
            문제 = 검사(번호들, 줄)
            if not 문제:
                for i, b in zip(번호들, 줄): 새[i] = b
                됨 = True; break
            추가 = "\n\n[이전 시도의 문제 — 꼭 고치세요] " + "; ".join(문제[:8])
        if not 됨:
            유지.append("%d~%d줄" % (번호들[0] + 1, 번호들[-1] + 1))
    기록 = []
    for i in range(len(원)):
        if i in 고정 or 새[i] == 원[i]:
            기록.append({"줄": i + 1, "C": 새[i], "출처": "(A판 그대로)", "Pool과 겹침": None})
        else:
            f, r = 출처(i, 새[i]); 기록.append({"줄": i + 1, "C": 새[i], "출처": f, "Pool과 겹침": r})
    io.open(os.path.join(HERE, "C_판.txt"), "w", encoding="utf-8").write("\n".join(새))
    json.dump(기록, io.open(os.path.join(HERE, "C_출처.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    바뀐 = [r for r in 기록 if r["Pool과 겹침"] is not None]
    print("C판 완료 · 바뀐 줄 %d · Pool 틀과 평균 겹침 %.2f · 원문 유지 %s" %
          (len(바뀐), (sum(r["Pool과 겹침"] for r in 바뀐) / len(바뀐)) if 바뀐 else 0, ", ".join(유지) or "없음"))
