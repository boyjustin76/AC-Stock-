# -*- coding: utf-8 -*-
"""AE 작업실 폴더가 어디인지 **찾아서** 알려준다.

2026-09-16 이전에는 어디서나 'C:/aelab' 을 박아 썼다. 그날 작업물을 한 폴더로 모으면서
작업실이 <통합 폴더>/02_AE작업실_aelab 으로 들어갔고, C:\aelab 은 없앴다.
경로를 박지 않고 찾게 해두면 꾸러미를 통째로 어디에 풀어도 그대로 돌아간다.

찾는 순서
  1) 환경변수 AELAB_DIR
  2) tools/ae/config.json 의 labDir (비어 있지 않으면. 상대경로면 config.json 기준)
  3) 이 파일에서 위로 올라가며 '02_AE작업실_aelab' 폴더를 찾는다
  4) 옛 자리 C:/aelab (되돌린 경우)
"""
import json
import os

FOLDER = "02_AE작업실_aelab"
LEGACY = "C:/aelab"


def _from_config():
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    try:
        with open(cfg, encoding="utf-8") as f:
            v = json.load(f).get("labDir") or ""
    except Exception:
        return None
    if not v:
        return None
    if not os.path.isabs(v):
        v = os.path.join(os.path.dirname(cfg), v)
    return os.path.normpath(v)


def _by_walking_up():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        c = os.path.join(d, FOLDER)
        if os.path.isdir(c):
            return c
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None


def lab_dir():
    """작업실 폴더를 슬래시(/) 경로로 돌려준다."""
    for v in (os.environ.get("AELAB_DIR"), _from_config(), _by_walking_up(), LEGACY):
        if v and os.path.isdir(v):
            return os.path.abspath(v).replace("\\", "/")
    # 아직 없는 자리라도 만들 수 있게 마지막 후보를 준다
    return (_by_walking_up() or LEGACY).replace("\\", "/")


def lab(*parts):
    """작업실 아래 경로를 만든다.  lab('pack', 'trad_rr')"""
    return "/".join([lab_dir()] + [str(p).strip("/") for p in parts])


if __name__ == "__main__":
    print(lab_dir())
