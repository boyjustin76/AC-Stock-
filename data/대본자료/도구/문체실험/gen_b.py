# -*- coding: utf-8 -*-
"""B판 — 김직선 말투로. 쓰는 것은 한국 모델(Solar Pro 4 · HCX-005), Claude 는 사실만 확인한다."""
import io, os, re, glob, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kapi

HERE = os.path.dirname(os.path.abspath(__file__))
KJ = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\05_대본자료\메이저자막\김직선 - 나스닥 트레이더"


def srt(p):
    out = [re.sub(r"<[^>]+>", "", l.strip()) for l in io.open(p, encoding="utf-8", errors="ignore")
           if l.strip() and not l.strip().isdigit() and "-->" not in l]
    return " ".join(x for i, x in enumerate(out) if i == 0 or x != out[i - 1])


def 예시(n=4, 길이=900):
    fs = sorted(glob.glob(os.path.join(KJ, "*.srt")), key=os.path.getsize, reverse=True)[:n]
    out = []
    for f in fs:
        t = srt(f)
        mid = len(t) // 3                       # 인사·광고를 피해 앞 1/3 지점부터
        out.append(t[mid:mid + 길이])
    return out


A = io.open(os.path.join(HERE, "A_판.txt"), encoding="utf-8").read()

지시 = """아래는 해외선물 유튜브 강의의 촬영용 대본(프롬프터로 읽음) 일부입니다.
이 대본을 [김직선] 유튜버가 말하는 말투로 다시 써 주세요. [김직선 자막 예시]를 참고하세요(자동 자막이라 문장부호가 없습니다).

반드시 지킬 것
1. 내용은 바꾸지 않습니다. 숫자(20, 4), 색(빨간색 보조밴드, 검정색 메인밴드), 규칙과 순서(중심선 방향 확인 → 보조밴드 하단에 먼저 닿음 → 기다림 → 메인밴드 하단까지 같이 이탈 → 밴드 안쪽으로 돌아오는 반응 확인 → 진입)를 그대로 둡니다. 없는 내용을 더하지 않습니다.
2. 존댓말을 유지합니다. 문장 끝은 '-습니다/-ㅂ니다'를 기본으로 두고 '-요', '-죠'를 섞습니다. 반말, 과장된 수익 표현은 쓰지 않습니다.
3. '[차트 진행 · 읽지 않음]'으로 시작하는 줄과 'INTRO.', '3.'으로 시작하는 제목 줄은 한 글자도 바꾸지 말고 같은 자리에 둡니다.
4. 한 줄에 한 문장씩, 문장부호를 넣어 씁니다. 설명이나 머리말 없이 대본만 출력합니다."""


def 요청(모델):
    ex = "\n\n".join("[김직선 자막 예시 %d]\n%s" % (i + 1, e) for i, e in enumerate(예시()))
    msgs = [{"role": "system", "content": "당신은 한국어 유튜브 강의 대본을 특정 유튜버의 말투로 옮겨 쓰는 작가입니다."},
            {"role": "user", "content": "%s\n\n%s\n\n[원래 대본]\n%s" % (지시, ex, A)}]
    if 모델.startswith("HCX"):
        return kapi.clova(msgs, 모델, 0.5, 3000)
    return kapi.upstage(msgs, 모델, 0.5, 3000)


if __name__ == "__main__":
    for m in sys.argv[1:]:
        t = 요청(m)
        io.open(os.path.join(HERE, "B_%s.txt" % m), "w", encoding="utf-8").write(t.strip())
        print("==== %s (%d자)\n%s\n" % (m, len(t), t.strip()))
