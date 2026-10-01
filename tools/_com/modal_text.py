"""떠 있는 모달 창을 찾아 **글자와 그림**을 뜬다 — 실패 원자료용 (TRAPS ⑨-5).

공용 실행기가 시간 제한을 넘기면 거의 모달이다. 그런데 모달을 닫는 길은 없고(SendKeys·UIA 가 안 먹는다),
앱을 죽이면 창이 사라져 원인이 같이 사라진다. 그래서 **죽이기 전에** 여기서 한 번 뜬다.

  · 모달 판별 — 대상 프로세스의 최상위 창 중 클래스가 `#32770`(윈도 표준 대화상자)인 것.
    보조로 **가장 큰 창이 IsWindowEnabled=False** 면 무언가가 입력을 막고 있다는 뜻이다.
  · 글자 — 대화상자 제목 + 자식 창(Static·Button)의 글자. 어도비가 직접 그린 대화상자는
    자식 창이 없어 빈손으로 나온다. 그때는 `--out` 그림만 남는다(사람이 본다).
  · 그림 — `PrintWindow(PW_RENDERFULLCONTENT)`. 가려져 있어도 그려진다. 구현은 shot_window.py 한 벌.

    python modal_text.py --proc Illustrator --out C:/…/build_live_modal.png --json C:/…/modal.json

종료코드 0 = 모달을 찾았다 · 2 = 못 찾았다(부르는 쪽이 앱 창 전체로 물러서면 된다).
stdout 에는 ASCII 만 찍는다 — PowerShell 5.1 이 cp949 로 받아 한글이 깨지기 때문(constraint 63 과 같은 뿌리).
"""
import argparse
import ctypes
import ctypes.wintypes as w
import json
import sys

from shot_window import _pid_name, shoot

u = ctypes.windll.user32

DIALOG_CLASS = "#32770"


def _class_of(h):
    b = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(h, b, 256)
    return b.value


def _text_of(h):
    n = u.GetWindowTextLengthW(h)
    if not n:
        return ""
    b = ctypes.create_unicode_buffer(n + 1)
    u.GetWindowTextW(h, b, n + 1)
    return b.value


def _rect(h):
    r = w.RECT()
    u.GetWindowRect(h, ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def top_windows(proc):
    """그 프로세스가 가진 보이는 최상위 창 전부 — (hwnd, 클래스, 제목, 넓이, 폭, 높이)."""
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, w.HWND, w.LPARAM)
    def cb(h, _):
        if not u.IsWindowVisible(h):
            return True
        pid = w.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if _pid_name(pid.value).lower() != proc.lower():
            return True
        _, _, cw, ch = _rect(h)
        out.append({"hwnd": h, "class": _class_of(h), "title": _text_of(h),
                    "w": cw, "h": ch, "area": cw * ch,
                    "enabled": bool(u.IsWindowEnabled(h))})
        return True

    u.EnumWindows(cb, 0)
    return out


def child_texts(hwnd):
    """대화상자 안 자식 창의 글자. 어도비가 직접 그린 창은 여기가 빈다."""
    got = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, w.HWND, w.LPARAM)
    def cb(h, _):
        t = _text_of(h).strip()
        if t:
            got.append(t)
        return True

    u.EnumChildWindows(hwnd, cb, 0)
    return got


def find_modal(proc):
    """(모달 창, 주창) — 모달이 없으면 (None, 주창)."""
    wins = top_windows(proc)
    if not wins:
        return None, None
    wins.sort(key=lambda d: -d["area"])
    main = wins[0]
    for d in wins:
        if d["class"] == DIALOG_CLASS:
            return d, main
    # 클래스가 #32770 이 아니어도 주창이 잠겨 있으면 무언가가 막고 있는 것이다.
    # 그럴 때는 두 번째로 큰 창을 후보로 본다 (어도비가 직접 그린 대화상자).
    if not main["enabled"] and len(wins) > 1:
        return wins[1], main
    return None, main


def ae_recovery():
    """AE 의 '충돌 복구 옵션' 창이 떠 있나 (constraint 71 · next_step 53).

    강제 종료된 AE 를 다시 띄우면 뜬다. 어도비가 그린 창이라 문구는 안 읽히지만 **뼈대**는 읽힌다 (09-22 D 실측):
      · 복구 창   #32770 · 자식 OS_ViewContainer ×2 + **OS_EditTextContainer** · AE 주창 없음 (534x365)
      · 시작 화면 #32770 · 자식 OS_ViewContainer 하나뿐 (766x516) — 이것과 헷갈리면 안 된다
    크기는 화면 배율마다 달라질 수 있어 조건에 안 넣는다.
    """
    wins = top_windows("AfterFX")
    if any(d["class"].startswith("AE_CApplication") for d in wins):
        return None
    for d in wins:
        if d["class"] == DIALOG_CLASS and "OS_EditTextContainer" in child_texts(d["hwnd"]):
            return d
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proc", help="프로세스 이름 (확장자 없이). 예 Illustrator")
    ap.add_argument("--out", help="모달 그림을 쓸 자리 (.png)")
    ap.add_argument("--json", help="찾은 것을 쓸 자리 (.json, UTF-8)")
    ap.add_argument("--ae-recovery", action="store_true",
                    help="AE 충돌 복구 창만 본다. 종료코드 0 = 떠 있다 · 2 = 없다")
    a = ap.parse_args()
    if a.ae_recovery:
        d = ae_recovery()
        print(f"ae_recovery={int(d is not None)}" + (f" size={d['w']}x{d['h']}" if d else ""))
        return 0 if d else 2
    if not a.proc:
        ap.error("--proc 가 있어야 한다")

    modal, main_win = find_modal(a.proc)
    res = {
        "프로세스": a.proc,
        "모달": modal is not None,
        "주창_잠김": (main_win is not None and not main_win["enabled"]),
        "제목": modal["title"] if modal else "",
        "클래스": modal["class"] if modal else "",
        "크기": f"{modal['w']}x{modal['h']}" if modal else "",
        "글자": child_texts(modal["hwnd"]) if modal else [],
        "그림": "",
    }
    res["문구"] = " ".join([res["제목"]] + res["글자"]).strip()

    if a.out and modal:
        try:
            ok = shoot(modal["hwnd"], modal["w"], modal["h"], a.out)
            res["그림"] = a.out
            res["PrintWindow"] = int(ok)
        except Exception as e:                       # 그림은 덤이다 — 실패해도 글자는 남긴다
            res["그림오류"] = str(e)

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

    # 한글을 찍으면 PS 5.1 이 깨뜨린다 — 숫자와 ASCII 만
    print(f"modal={int(res['모달'])} locked={int(res['주창_잠김'])} "
          f"class={res['클래스'] or '-'} size={res['크기'] or '-'} "
          f"chars={len(res['문구'])} kids={len(res['글자'])}")
    return 0 if modal else 2


if __name__ == "__main__":
    sys.exit(main())
