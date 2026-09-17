"""글자 비교용 정규화 — 숫자·한글 음절·영문자만 남긴다.

대본 줄 ↔ STT 낱말 ↔ 자막 큐를 글자로 맞출 때 모두 이 한 벌을 쓴다.
한 곳만 바꾸면 정렬(align_take)과 채점(cuetune)이 서로 다른 글자를 세게 된다.
"""
import re

_DROP = re.compile(r"[^0-9가-힣a-zA-Z]")


def norm(t):
    return _DROP.sub("", t)
