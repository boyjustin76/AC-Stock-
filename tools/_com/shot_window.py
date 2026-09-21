"""앱 창 한 장을 그대로 찍는다 — 실패 원자료용.

화면을 통째로 찍으면 **가려진 창**이 안 나온다. 모달이 다른 창 뒤에 있으면 원자료가 쓸모없다.
`PrintWindow(PW_RENDERFULLCONTENT)` 는 가려져 있어도 창 내용을 그려 준다.

프로세스 이름만 주면 그 프로세스가 가진 **보이는 최상위 창 중 가장 큰 것**을 고른다.
`MainWindowHandle` 은 못 믿는다 — 일러스트레이터는 160x28 짜리 엉뚱한 창을 돌려줬다(실측 09-21).

쓰기: python shot_window.py --proc AfterFX --out C:/…/a1_fail.png
      python shot_window.py --title HedgeHood --out C:/…/mt5.png
못 찾으면 종료코드 2 로 빠진다 — 부르는 쪽이 화면 전체로 물러서면 된다.
"""
import argparse
import ctypes
import ctypes.wintypes as w
import sys

from PIL import Image

u = ctypes.windll.user32
g = ctypes.windll.gdi32
k = ctypes.windll.kernel32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass


class BMIH(ctypes.Structure):
    _fields_ = [('biSize', ctypes.c_uint32), ('biWidth', ctypes.c_int32), ('biHeight', ctypes.c_int32),
                ('biPlanes', ctypes.c_uint16), ('biBitCount', ctypes.c_uint16),
                ('biCompression', ctypes.c_uint32), ('biSizeImage', ctypes.c_uint32),
                ('biXPelsPerMeter', ctypes.c_int32), ('biYPelsPerMeter', ctypes.c_int32),
                ('biClrUsed', ctypes.c_uint32), ('biClrImportant', ctypes.c_uint32)]


def _pid_name(pid):
    """PID → 실행 파일 이름 (확장자 없이). 권한이 없으면 빈 문자열."""
    h = k.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ''
    try:
        buf = ctypes.create_unicode_buffer(512)
        size = w.DWORD(512)
        if ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value.rsplit('\\', 1)[-1].rsplit('.', 1)[0]
        return ''
    finally:
        k.CloseHandle(h)


def find_window(proc=None, title=None):
    """조건에 맞는 보이는 최상위 창 중 **가장 큰 것**."""
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, w.HWND, w.LPARAM)
    def cb(h, _):
        if not u.IsWindowVisible(h):
            return True
        r = w.RECT()
        u.GetClientRect(h, ctypes.byref(r))
        area = (r.right - r.left) * (r.bottom - r.top)
        if area < 40000:                            # 200x200 미만은 도구창·팔레트다
            return True
        if title:
            n = u.GetWindowTextLengthW(h)
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, b, n + 1)
            if title.lower() not in b.value.lower():
                return True
        if proc:
            pid = w.DWORD()
            u.GetWindowThreadProcessId(h, ctypes.byref(pid))
            if _pid_name(pid.value).lower() != proc.lower():
                return True
        found.append((area, h, r.right - r.left, r.bottom - r.top))
        return True

    u.EnumWindows(cb, 0)
    if not found:
        return None
    found.sort(reverse=True)
    return found[0][1:]


def shoot(hwnd, cw, ch, out):
    hdc = u.GetWindowDC(hwnd)
    mdc = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, cw, ch)
    g.SelectObject(mdc, bmp)
    ok = u.PrintWindow(hwnd, mdc, 2)                # 2 = PW_RENDERFULLCONTENT
    bi = BMIH()
    bi.biSize = ctypes.sizeof(BMIH)
    bi.biWidth, bi.biHeight = cw, -ch
    bi.biPlanes, bi.biBitCount, bi.biCompression = 1, 32, 0
    buf = ctypes.create_string_buffer(cw * ch * 4)
    g.GetDIBits(mdc, bmp, 0, ch, buf, ctypes.byref(bi), 0)
    Image.frombuffer('RGB', (cw, ch), buf, 'raw', 'BGRX', 0, 1).save(out)
    g.DeleteObject(bmp)
    g.DeleteDC(mdc)
    u.ReleaseDC(hwnd, hdc)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--proc', help='프로세스 이름 (확장자 없이). 예 AfterFX')
    ap.add_argument('--title', help='창 제목에 든 글자')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if not a.proc and not a.title:
        ap.error('--proc 이나 --title 중 하나는 있어야 한다')
    got = find_window(a.proc, a.title)
    if not got:
        print('창을 못 찾았다', file=sys.stderr)
        return 2
    hwnd, cw, ch = got
    ok = shoot(hwnd, cw, ch, a.out)
    print(f'PrintWindow={ok} {cw}x{ch} → {a.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
