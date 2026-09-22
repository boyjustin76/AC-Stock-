# -*- coding: utf-8 -*-
"""자료가 어디 있는지 한 곳에서 정한다.

도구는 `05_대본자료/도구/` 에 있고 자료는 그 **윗칸**에 있다.
스크래치 폴더에서 옮겨 오면서 이름이 바뀌었다 — pool→Pool · docs→레퍼런스 · corpus→메이저자막.
"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 05_대본자료
POOL = os.path.join(BASE, "Pool")           # 회사 원고 173편
DOCS = os.path.join(BASE, "레퍼런스")        # 레퍼런스 자막·더원 원고
CORP = os.path.join(BASE, "메이저자막")      # 타채널 자막 45편
YT = os.path.join(DOCS, "원본자막")          # 내려받은 자막 원본(json3·srt)
AIRED = os.path.join(BASE, "방송본")        # 실제로 나간 영상의 자막 (ASR)
