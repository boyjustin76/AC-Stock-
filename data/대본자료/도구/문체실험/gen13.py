# -*- coding: utf-8 -*-
"""차13 = Pool(정보) + 김직선(말투).
정보는 이미 회사 양식 원고에 Pool 조각 49개로 들어가 있다. 여기서는 **말투만** 바꾼다.
문장마다 뜻이 가까운 김직선 실제 문장 3개를 붙여, 그 문장 틀로 다시 쓰게 한다 (차12 B판과 같은 방식).
팀장 수정_3 의 방향(정확성·주어·용어는 건드리지 않음)을 검사로 강제한다."""
import io, os, re, sys, json, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import kapi, kj_retrieve as R
from kiwipiepy import Kiwi

HERE = os.path.dirname(os.path.abspath(__file__))
MD = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\01_저장소\E_Script\log\차13_테스타칼만ATR_뼈대_회사양식.md"
kiwi = Kiwi()

# 지켜야 할 말 — 한 묶음 안의 낱말 중 하나라도 남아 있으면 된다 (같은 뜻으로 바꾼 것은 봐준다)
용어 = [["칼만"], ["이동평균선", "이평선", "이동 평균선"], ["SMA"], ["EMA"], ["HMA"], ["HH"], ["LL"], ["ATR"],
        ["종가"], ["전저점", "직전 저점", "이전 저점"], ["전고점", "직전 고점", "이전 고점"],
        ["초록"], ["빨강", "빨간"], ["메타트레이더"], ["손익비"], ["테스타"], ["마커"],
        ["박스권", "횡보"], ["노이즈", "잡음"], ["골든크로스"], ["데드크로스"],
        ["손절", "손실을 끊", "손실 확정"], ["익절", "이익 실현", "이익을 실현", "청산"],
        ["수평선"], ["고정 댓글"], ["지지"], ["저항"]]
금지 = ["무조건", "보장", "100%", "떼돈", "대박", "하루 10만", "억대", "비법", "필승", "승률 9", "꿀팁"]
# 우리 대본에 없는 남의 지표·자동자막 부스러기 — 원문에 없으면 끌어온 것이다
남의것 = ["볼린저", "RSI", "rsi", "스토캐스틱", "MACD", "일목", "피보나치", "이격도", "과매수", "과매도",
          "원비", "거이", "이거를 보면은", "엘리어트"]


def 문서읽기():
    """(종류, 원문) 목록. 종류: 'skip'=그대로 둘 줄, 'text'=말투를 바꿀 문장"""
    줄들, 블록, 본문 = io.open(MD, encoding="utf-8").read().split("\n"), [], False
    for l in 줄들:
        if l.startswith("## 본문"): 본문 = True
        if l.startswith("## 매매법 정리"): 본문 = False
        if not 본문 or not l.strip() or l.startswith(("#", "제목:", "<!--", "  ", "\t")):
            블록.append(("skip", l)); continue
        # 한 문단을 문장으로 쪼갠다. 문장 앞의 (차트 화면) 같은 표시는 떼어 두고 나중에 붙인다
        조각 = []
        for s in kiwi.split_into_sents(l):
            t = s.text.strip()
            m = re.match(r"^(\([^)]*\)|\[[^\]]*\])\s*", t)          # 앞에 붙은 화면 표시
            머리, 몸 = (m.group(1) + " ", t[m.end():]) if m else ("", t)
            m2 = re.search(r"\s*(\([^)]*\)|\[[^\]]*\])$", 몸)        # 뒤에 붙은 화면 표시 (다음 문장 것)
            꼬리, 몸 = (" " + m2.group(1), 몸[:m2.start()]) if m2 else ("", 몸)
            조각.append(("text", 머리, 몸, 꼬리) if len(몸) >= 10 else ("skip", 머리 + 몸 + 꼬리))
        블록.append(("para", 조각))
    return 블록


지시 = """[원래 대본]의 번호 붙은 문장을, 줄마다 붙인 [김직선 실제 문장]의 말투와 문장 틀을 빌려 다시 써 주세요.
[김직선 실제 문장]은 유튜버 김직선이 실제로 한 말(자동 자막)입니다. 그 말의 어미·말버릇·호흡만 가져오고, 내용은 우리 원래 문장의 것을 그대로 둡니다.

규칙
1. 번호 붙은 문장만, 같은 개수(%d개)로, 같은 번호끼리 대응시킵니다. 문장 앞에 번호를 붙이지 않습니다.
2. 내용은 그대로입니다. 숫자·설정값·지표 이름·색·순서를 바꾸지 않고, 새 사실이나 인사를 더하지 않습니다.
3. 지표 이름과 용어(칼만 이동평균선, HH LL, ATR, 종가, 전저점 등)는 줄이거나 풀어 쓰지 말고 그대로 씁니다.
4. 같은 뜻을 한 번 더 풀어 말하거나 문장을 둘로 나누는 것은 괜찮습니다. 새 정보는 안 됩니다.
5. '저는 ~라고 봅니다' 같은 1인칭 의견은 괜찮습니다. 강사 본인의 경험담('저도 예전에', '제가 진입해서')이나 수익 이야기는 쓰지 않습니다.
6. '~는 거예요/거죠'로 끝나는 문장은 이번 묶음에서 1개까지. 끝맺음을 골고루 섞습니다.
7. 화자는 이 채널의 강사입니다. '김직선' 이름을 쓰지 않습니다. 존댓말, 반말 금지, 과장된 수익 표현 금지. 맞춤법을 지킵니다.
8. 원문을 그대로 옮기지 말고 말투를 실제로 바꿉니다.
9. 문자열만 담은 JSON 배열 하나만 출력합니다. 예: ["첫 문장", "둘째 문장"]"""


def 요청(모델, 원문들, 참고들, 추가):
    몸 = []
    for k, (a, hits) in enumerate(zip(원문들, 참고들)):
        몸.append("%d. %s" % (k + 1, a))
        몸 += ["   [김직선 실제 문장] %s" % s for s, _, _ in hits]
    msgs = [{"role": "system", "content": "당신은 한국어 유튜브 강의 대본의 말투를 바꾸는 작가입니다. JSON 배열만 출력합니다."},
            {"role": "user", "content": (지시 % len(원문들)) + 추가 + "\n\n[원래 대본]\n" + "\n".join(몸)}]
    return kapi.clova(msgs, 모델, 0.6, 2000) if 모델.startswith("HCX") else kapi.upstage(msgs, 모델, 0.6, 2000)


def 풀기(t):
    j = re.search(r"\[.*\]", t, re.S)
    try: arr = json.loads(j.group(0)) if j else []
    except Exception: return []
    out = []
    for x in arr:
        if isinstance(x, dict): x = x.get("text") or next(iter(x.values()), "")
        out.append(re.sub(r"^\s*\d+\s*[.)]\s*", "", str(x)).strip())
    return out


def 문장수(t): return len([x for x in re.split(r"(?<=[.?!])\s+", t.strip()) if x])


def 다듬기(원문들, 새줄):
    """모델이 빼먹은 끝 문장부호를 원문 것으로 붙인다."""
    out = []
    for a, b in zip(원문들, 새줄):
        b = b.strip()
        if b and b[-1] not in ".?!…": b += a.strip()[-1] if a.strip()[-1] in ".?!…" else "."
        out.append(b)
    return out


def 검사(원문들, 새줄):
    """문장마다 문제 목록 — 통과한 문장은 살리고 걸린 것만 다시 돌리려고 개별로 돌려준다."""
    if len(새줄) != len(원문들): return None
    표 = []
    A = R.임베딩(원문들, "embedding-query"); B = R.임베딩(새줄, "embedding-query")
    덧붙인 = {k: [x for x in re.split(r"(?<=[.?!])\s+", b.strip()) if x][1:] for k, b in enumerate(새줄)}
    덧목록 = [(k, x) for k, (a, b) in enumerate(zip(원문들, 새줄)) if 문장수(b) > 문장수(a) for x in 덧붙인[k]]
    for k, (a, b) in enumerate(zip(원문들, 새줄)):
        문제 = []
        if sorted(re.findall(r"\d+", a)) != sorted(re.findall(r"\d+", b)): 문제.append("숫자 바뀜: " + b[:24])
        for 묶 in 용어:
            if any(w in a for w in 묶) and not any(w in b for w in 묶):
                문제.append("'%s' 빠짐: %s" % (묶[0], b[:20]))
        if "김직선" in b: 문제.append("김직선 이름")
        if re.search(r"(저도|저는|제가)[^.?!]{0,30}(했어요|했었|곤 했|그랬|예전에|벌었|잃었|진입한|진입했)", b):
            문제.append("경험담: " + b[:26])
        if re.search(r"(구요|이예요|됬)", b): 문제.append("맞춤법: " + b[:20])
        if re.search(r"(합시다|더라고요|같은 뜻|풀어 보면|한 번 더 풀)", b): 문제.append("지시문 새어 나옴: " + b[:20])
        if any(x in b for x in 금지): 문제.append("과장 표현: " + b[:20])
        for w in 남의것:
            if w in b and w not in a: 문제.append("남의 자막에서 끌어옴('%s'): %s" % (w, b[:22]))
        if len(b) > len(a) * 1.8 + 12: 문제.append("너무 길어짐(%d→%d자): %s" % (len(a), len(b), b[:20]))
        c = float(A[k] @ B[k])
        if c < 0.78: 문제.append("뜻이 달라짐(%.2f): %s" % (c, b[:18]))
        # 덧붙이는 건 괜찮지만(이정찬 2026-09-23), 덧붙인 문장이 원문에 없는 내용을 끌어오면 안 된다
        for x in (덧붙인[k] if 문장수(b) > 문장수(a) else []):
            새말 = [w for 묶 in 용어 for w in 묶 if w in x and w not in a]
            새수 = [n for n in re.findall(r"\d+", x) if n not in a]
            if 새말 or 새수:
                문제.append("덧붙인 문장에 원문에 없는 내용(%s): %s" % (", ".join(새말 + 새수), x[:22]))
        표.append(문제)
    # 덧붙인 문장이 원문과 같은 이야기인지 — 부연이면 가깝고, 끌어온 말이면 멀다
    if 덧목록:
        V = R.임베딩([x for _, x in 덧목록], "embedding-query")
        for (k, x), v in zip(덧목록, V):
            c = float(A[k] @ v)
            if c < 0.66: 표[k].append("덧붙인 문장이 딴 이야기(%.2f): %s" % (c, x[:24]))
    return 표


def 만들기(모델들, 묶음=5):
    블록 = 문서읽기()
    대상 = [(bi, si) for bi, b in enumerate(블록) if b[0] == "para" for si, c in enumerate(b[1]) if c[0] == "text"]
    원문들 = [블록[bi][1][si][2] for bi, si in 대상]
    print("바꿀 문장 %d개" % len(원문들), flush=True)
    참고 = R.찾기(원문들, k=3)
    새, 유지, 기록 = dict(), [], []
    for s in range(0, len(대상), 묶음):
        처음 = list(range(s, min(s + 묶음, len(대상))))
        남은, 추가 = list(처음), ""
        for 시도 in range(3 * len(모델들)):
            if not 남은: break
            줄 = 풀기(요청(모델들[시도 // 3], [원문들[i] for i in 남은], [참고[i] for i in 남은], 추가))
            if len(줄) == len(남은): 줄 = 다듬기([원문들[i] for i in 남은], 줄)
            표 = 검사([원문들[i] for i in 남은], 줄) if 줄 else None
            기록.append({"묶음": [i + 1 for i in 남은], "시도": 시도, "모델": 모델들[시도 // 3],
                         "문제": ["문장 수 안 맞음"] if 표 is None else [p for ps in 표 for p in ps]})
            if 표 is None:
                추가 = "\n\n[이전 시도의 문제] 문장 개수를 정확히 맞추세요."
                continue
            실패, 이유, 거체 = [], [], 0
            for i, b, ps in zip(남은, 줄, 표):
                if re.search(r"거(예요|에요|죠|였죠|였어요)[.?!]?$", b.strip()):
                    거체 += 1
                    if 거체 > 1: ps = ps + ["'~거예요/거죠'가 이번 묶음에 이미 있습니다 — 다른 끝맺음으로"]
                if ps: 실패.append(i); 이유 += ps
                else: 새[i] = b          # 통과한 문장은 살린다
            남은 = 실패
            추가 = "\n\n[이전 시도의 문제 — 꼭 고치세요] " + "; ".join(list(dict.fromkeys(이유))[:8])
        print("  %d~%d 됨 %d / %d" % (처음[0] + 1, 처음[-1] + 1, len(처음) - len(남은), len(처음)), flush=True)
        유지 += [i + 1 for i in 남은]
    json.dump(기록, io.open(os.path.join(HERE, "차13_실패기록.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 다시 조립
    out = []
    for bi, b in enumerate(블록):
        if b[0] != "para": out.append(b[1]); continue
        문장 = []
        for si, c in enumerate(b[1]):
            if c[0] == "skip": 문장.append(c[1]); continue
            i = 대상.index((bi, si))
            문장.append(c[1] + 새.get(i, c[2]) + c[3])
        out.append(" ".join(문장))
    return "\n".join(out), 원문들, 새, 유지


if __name__ == "__main__":
    모델들 = (sys.argv[1] if len(sys.argv) > 1 else "solar-pro4+HCX-005").split("+")
    본문, 원문들, 새, 유지 = 만들기(모델들)
    io.open(os.path.join(HERE, "차13_김직선말투.md"), "w", encoding="utf-8").write(본문)
    json.dump([{"원": a, "새": 새.get(i, "")} for i, a in enumerate(원문들)],
              io.open(os.path.join(HERE, "차13_문장대조.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("바꾼 문장 %d / %d · 원문 유지 %s" % (len(새), len(원문들), 유지 or "없음"))
