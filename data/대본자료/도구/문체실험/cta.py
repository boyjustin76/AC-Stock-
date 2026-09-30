# -*- coding: utf-8 -*-
"""CTA 문구 짓기 — 어휘는 회사 Pool 아웃트로에서, 말투는 김직선 실제 CTA 문장에서.
지어낸 약속(수익·승률·금액)과 없는 제도(이벤트 등)는 검사로 막는다."""
import io, os, re, sys, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kapi

HERE = os.path.dirname(os.path.abspath(__file__))
B = r"C:\Users\user\Desktop\이정찬\스크립트_컷편집_통합\05_대본자료"
POOL, KJ = os.path.join(B, "Pool"), os.path.join(B, "메이저자막", "김직선 - 나스닥 트레이더")
CTA말 = ["구독", "좋아요", "알림", "고정 댓글", "댓글", "링크", "라이브", "트레이딩룸", "참여", "공유"]
금지 = ["무조건", "보장", "100%", "떼돈", "대박", "하루 10만", "억대", "비법", "필승", "꿀팁", "수익률",
        "승률", "원 벌", "만 원", "수익 인증", "무료 강의", "이벤트", "추첨", "선착순", "리딩", "종목 추천"]


def 문장들(t, 최소=8, 최대=80):
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+|\n", t) if 최소 <= len(s.strip()) <= 최대]


def srt(p):
    ls = [re.sub(r"<[^>]+>", "", l.strip()) for l in io.open(p, encoding="utf-8", errors="ignore")
          if l.strip() and not l.strip().isdigit() and "-->" not in l]
    return " ".join(x for i, x in enumerate(ls) if i == 0 or x != ls[i - 1])


def 재료():
    pool, 본 = [], set()
    for f in glob.glob(os.path.join(POOL, "*.txt")):
        for s in 문장들(io.open(f, encoding="utf-8", errors="ignore").read()[-1800:]):
            if any(w in s for w in CTA말[:8]) and s not in 본 and not s.startswith(("[", "•", "-")):
                본.add(s); pool.append(s)
    kj = []
    for f in glob.glob(os.path.join(KJ, "*.srt")):
        t = srt(f)
        for 부분 in (t[:700], t[-1500:]):
            for s in 문장들(부분):
                if any(w in s for w in CTA말) and s not in 본:
                    본.add(s); kj.append(s)
    return pool, kj


갈래 = [
    ("구독·좋아요", "영상을 끝까지 본 사람에게 구독과 좋아요, 알림 설정을 청하는 마무리"),
    ("지표 배포", "오늘 쓴 지표(칼만 이평선·HH LL)를 고정 댓글 링크에서 받아 가라고 알리는 문구"),
    ("댓글 유도", "댓글로 한 가지를 적고 가게 만드는 문구. 다음 영상 주제와 이어지게"),
    ("라이브·트레이딩룸", "라이브 방송과 트레이딩룸에 들어와 같이 매매해 보자고 청하는 문구"),
]

지시 = """당신은 트레이딩 유튜브 채널의 대본 작가입니다. 영상 끝에 붙일 CTA(행동 유도) 문구를 짓습니다.

[우리 채널이 쓰던 문구]는 우리 회사 대본의 아웃트로입니다. **여기서 낱말과 청하는 내용**을 가져옵니다.
[본보기 말투]는 우리가 본보기로 삼는 유튜버가 실제로 한 말입니다. **여기서 말투와 호흡만** 가져옵니다. 그 사람의 사정(라이브 3년, 댓글 2026개 같은 것)은 가져오지 않습니다.

규칙
1. 목적: %s
2. 2~3문장, 전체 60~140자. 존댓말. 반말·명령조 금지.
2-1. **말투가 핵심입니다.** [본보기 말투]처럼 짧게 끊고, '~요/~죠'로 끝내고, 구어체 부사(지금, 한번, 그냥, 진짜)를 씁니다.
2-2. 다음 표현은 쓰지 않습니다: '부탁드립니다', '바랍니다', '~해 주시면 감사하겠습니다', '마련하고 있습니다'.
3. 수익·승률·금액·기간을 약속하지 않습니다. 없는 제도(이벤트·추첨·선착순·리딩)를 지어내지 않습니다.
4. 우리 채널 이름이나 사람 이름을 쓰지 않습니다.
5. 서로 다른 %d개를 만듭니다. 문장 틀이 겹치지 않게 합니다.
6. 문자열만 담은 JSON 배열 하나만 출력합니다."""


말버릇 = ["요.", "요!", "죠.", "죠?", "요?", "거예요", "니까요", "세요", "볼게요", "할게요", "드릴게요"]
def 검사(s):
    문제 = []
    if not any(w in s for w in 말버릇): 문제.append("김직선 말투 아님")
    for w in ("부탁드립니다", "바랍니다", "감사하겠습니다", "마련하고 있습니다", "뵙겠습니다"):
        if w in s: 문제.append("회사 상투어 '%s'" % w)
    if not (50 <= len(s) <= 160): 문제.append("길이 %d자" % len(s))
    for w in 금지:
        if w in s: 문제.append("금지어 '%s'" % w)
    if re.search(r"\d+\s*(%|퍼센트|배|원|만|억)", s): 문제.append("숫자 약속")
    if not re.search(r"(요|다|죠|까)[.?!]$", s.strip()): 문제.append("끝맺음")
    return 문제


if __name__ == "__main__":
    pool, kj = 재료()
    print("재료 — Pool %d문장 · 김직선 %d문장\n" % (len(pool), len(kj)))
    본, 결과 = set(), []
    for 이름, 목적 in 갈래:
        for 모델 in ("solar-pro4", "HCX-005"):
            msgs = [{"role": "system", "content": "당신은 한국어 유튜브 대본 작가입니다. JSON 배열만 출력합니다."},
                    {"role": "user", "content": (지시 % (목적, 4))
                     + "\n\n[우리 채널이 쓰던 문구]\n" + "\n".join("- " + s for s in pool[:40])
                     + "\n\n[본보기 말투]\n" + "\n".join("- " + s for s in kj[:40])}]
            t = kapi.upstage(msgs, 모델, 0.8, 1200) if 모델.startswith("solar") else kapi.clova(msgs, 모델, 0.8, 1200)
            m = re.search(r"\[.*\]", t, re.S)
            try: arr = json.loads(m.group(0)) if m else []
            except Exception: arr = []
            for x in arr:
                s = re.sub(r"\s+", " ", str(x)).strip()
                문제 = 검사(s)
                if not 문제 and s not in 본:
                    본.add(s); 결과.append({"갈래": 이름, "모델": 모델, "문구": s})
    # 김직선다움 — 김직선 자막 글자 3-gram 대 다른 채널 배경 (gen_b3 와 같은 자)
    import channel_llr as C, kj_profile as P
    Pk, Pb = C.삼그램(C.정리(P.kj_t)), C.삼그램(C.정리(P.bg_t))
    for r in 결과:
        s = r["문구"]
        r["김직선다움"] = round((Pk.lp(s) - Pb.lp(s)) / max(1, len(C.정리(s))), 4)
    결과.sort(key=lambda r: -r["김직선다움"])
    json.dump(결과, io.open(os.path.join(HERE, "cta_후보.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for 이름, _ in 갈래:
        print("== " + 이름)
        for r in [x for x in 결과 if x["갈래"] == 이름]:
            print("  [%+.3f] %s" % (r["김직선다움"], r["문구"]))
        print()
