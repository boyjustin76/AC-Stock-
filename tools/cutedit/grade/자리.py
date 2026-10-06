# -*- coding: utf-8 -*-
"""채점대가 쓰는 자리들 — **절대경로를 코드에 박지 않는다** (issue 20·23·39, tests/test_no_path_literals.py).

  회차 폴더는 환경변수 `AC_CUT_DIR` 또는 첫 인자로 받는다.
  저장소는 이 파일 자리에서 거슬러 찾는다.
"""
import os
import sys

레포 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
도구 = os.path.join(레포, "tools", "cutedit")
채점 = os.path.dirname(os.path.abspath(__file__))
정답자막 = os.path.join(채점, "정답_자막")


def 회차폴더(인자=None):
    """컷편집 회차 폴더 (마01 같은 것). 없으면 알려 주고 멈춘다."""
    길 = 인자 or os.environ.get("AC_CUT_DIR")
    if not 길:
        sys.exit("회차 폴더를 주세요 — 첫 인자로 또는 AC_CUT_DIR 환경변수로\n"
                 "  예) AC_CUT_DIR=<...>/마01 python3 tools/cutedit/grade/가름대조.py")
    if not os.path.isdir(길):
        sys.exit("그런 폴더가 없습니다: %s" % 길)
    return 길


def 작업(인자=None):
    return os.path.join(회차폴더(인자), "_작업")
