# -*- coding: utf-8 -*-
"""채점 자료 위치 한 군데.

정답 자료(사람이 고친 것)와 작업폴더를 저장소 안에 같이 둔다 — 임시폴더에만 두면
세션이 끝날 때 같이 사라져서, 규칙을 다시 잴 수가 없다.
환경변수로 딴 데를 가리킬 수 있다: CUTEDIT_GRADE_WORK · CUTEDIT_GRADE_TRUTH.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CUTEDIT = os.path.dirname(HERE)
WORK = os.environ.get("CUTEDIT_GRADE_WORK") or os.path.join(HERE, "work")
TRUTH = os.environ.get("CUTEDIT_GRADE_TRUTH") or os.path.join(HERE, "truth")

# 회차 → (작업폴더, 정답 파일 앞이름). 정답은 <앞이름>_수정.srt · <앞이름>_컷편집_수정.xml
EPISODE = {
    "S015": (os.path.join(WORK, "s015"), "S015_포지션중독극복법_260908"),
    "S016": (os.path.join(WORK, "s016"), "S016_일목균형표 구름대만 남기세요_260910"),
}


def truth_srt(tag):
    return os.path.join(TRUTH, EPISODE[tag][1] + "_수정.srt")


def truth_xml(tag):
    return os.path.join(TRUTH, EPISODE[tag][1] + "_컷편집_수정.xml")


def work(tag):
    return EPISODE[tag][0]
