# -*- coding: utf-8 -*-
"""로컬 맞춤법 교정 모델(j5ng/et5-typos-corrector) 자가점검 — CPU, 키 없음."""
import time

from transformers import T5ForConditionalGeneration, T5TokenizerFast

t0 = time.time()
M = "j5ng/et5-typos-corrector"
tok = T5TokenizerFast.from_pretrained(M)
model = T5ForConditionalGeneration.from_pretrained(M)
model.eval()
print(f"모델 로드 {time.time() - t0:.1f}초 · 파라미터 {sum(p.numel() for p in model.parameters()) / 1e6:.0f}M")

TESTS = [
    "초보자도 쉽고 간단하게 적용하여 사용할 수 있는단순하면서 강력한 매매법!지금부터 소개해 드리겠습니다.",
    "이 밴드는 시장의 기본 범위와 중심 방향을 확인하는 역할을 합니다.이후 설명에서는 메인밴드라고 부르겠습니다.",
    "메인밴드의21기간 중심선이 우하향하고 가격이 중심선 아래에서 하락 구조를 만들고 있다면 매도 방향만 봅니다.",
    "수수료 황급부터 자체 개발 지표까지 자세한 내용은 아래 댓글을 확인해 주세요.",   # 자동자막 오인식
    "오늘은 초보자도 하루 최소 10만 원 이상을 목표로 할 수 있다고 검중된 전략입니다.",   # 자동자막 오인식
]
for s in TESTS:
    t = time.time()
    ids = tok("맞춤법을 고쳐주세요: " + s, return_tensors="pt", max_length=128, truncation=True)
    out = model.generate(**ids, max_length=128, num_beams=5, early_stopping=True)
    print(f"\n원문: {s}")
    print(f"교정: {tok.decode(out[0], skip_special_tokens=True)}   ({time.time() - t:.1f}초)")
