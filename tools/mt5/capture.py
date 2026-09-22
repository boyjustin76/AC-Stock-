"""MT5 차트 판을 그대로 찍는다 — 도구모음·터미널 패널 없이 차트만.

왜 이렇게 하나 (실측 2026-09-18)
 · MT5 내장 MCP 에는 **스크린샷 도구가 없다**(도구 50종 확인). MQL5 `ChartScreenShot()` 은
   스크립트를 컴파일해 차트에 올려야 해서 사람 손이 필요하다. 그래서 창을 직접 찍는다.
 · `PrintWindow` 는 자식 창 핸들을 줘도 **본 창**을 그린다. 그래서 본 창을 찍고 차트 판을 잘라낸다.
 · 자식 창 좌표는 DPI·MDI 때문에 어긋나므로, 그림에서 직접 찾는다 —
   회색 도구모음(240,240,240) 다음에 오는 검은 테두리 줄 바로 아래가 차트 판이고,
   높이는 MCP `list_open_charts` 의 `rect_bottom` 이다.

**창 크기를 먼저 고정**한다. 창이 커지면 보이는 봉 수와 픽셀 간격이 달라져 재현이 안 된다.

쓰기: python capture.py <출력.png> [창너비 창높이]
"""
import ctypes
import ctypes.wintypes as w
import os
import sys
import time

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import MT5  # noqa: E402

u = ctypes.windll.user32
g = ctypes.windll.gdi32
ctypes.windll.shcore.SetProcessDpiAwareness(2)

TITLE_HINT = os.environ.get('MT5_WINDOW_HINT', 'MetaTrader')
WIN_SIZE = (1936, 1056)          # 기본 창 크기 — 이 값에서 차트 판이 1920x608 이 된다
SW_RESTORE = 9
SWP_NOMOVE, SWP_NOZORDER = 0x0002, 0x0004
TOOLBAR_GRAY = (240, 240, 240)


class BMIH(ctypes.Structure):
    _fields_ = [('biSize', ctypes.c_uint32), ('biWidth', ctypes.c_int32), ('biHeight', ctypes.c_int32),
                ('biPlanes', ctypes.c_uint16), ('biBitCount', ctypes.c_uint16),
                ('biCompression', ctypes.c_uint32), ('biSizeImage', ctypes.c_uint32),
                ('biXPelsPerMeter', ctypes.c_int32), ('biYPelsPerMeter', ctypes.c_int32),
                ('biClrUsed', ctypes.c_uint32), ('biClrImportant', ctypes.c_uint32)]


def find_window(hint=TITLE_HINT):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, w.HWND, w.LPARAM)
    def cb(h, _):
        n = u.GetWindowTextLengthW(h)
        if n:
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, b, n + 1)
            if hint in b.value:
                out.append(h)
        return True

    u.EnumWindows(cb, 0)
    if out:
        return out[0]
    # 제목은 브로커가 정한다 — HedgeHood 터미널은 '935002683 - HedgeHoodMU-1: 데모계좌 - …' 라 'MetaTrader' 가 없다(09-22).
    # 그래서 제목으로 못 찾으면 terminal64 프로세스의 가장 큰 보이는 창을 쓴다.
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '_com'))
    from shot_window import find_window as by_proc
    got = by_proc(proc='terminal64')
    if got:
        return got[0]
    raise SystemExit(f'제목에 {hint!r} 가 든 창도, terminal64 창도 못 찾았다 — MT5 가 떠 있나 보라')


def shoot(hwnd):
    r = w.RECT()
    u.GetClientRect(hwnd, ctypes.byref(r))
    cw, ch = r.right, r.bottom
    hdc = u.GetWindowDC(hwnd)
    mdc = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, cw, ch)
    g.SelectObject(mdc, bmp)
    u.PrintWindow(hwnd, mdc, 2)  # 2 = PW_RENDERFULLCONTENT
    bi = BMIH()
    bi.biSize = ctypes.sizeof(BMIH)
    bi.biWidth, bi.biHeight = cw, -ch
    bi.biPlanes, bi.biBitCount, bi.biCompression = 1, 32, 0
    buf = ctypes.create_string_buffer(cw * ch * 4)
    g.GetDIBits(mdc, bmp, 0, ch, buf, ctypes.byref(bi), 0)
    im = Image.frombuffer('RGB', (cw, ch), buf, 'raw', 'BGRX', 0, 1)
    g.DeleteObject(bmp)
    g.DeleteDC(mdc)
    u.ReleaseDC(hwnd, hdc)
    return im


def chart_top(im):
    """회색 도구모음 아래 첫 검은 테두리 줄을 찾아 차트 판 첫 줄을 돌려준다."""
    px = im.load()
    W = im.size[0]
    xs = range(100, min(W, 1800), 50)
    for y in range(20, 400):
        if sum(1 for x in xs if sum(px[x, y]) < 200) > len(list(xs)) * 0.8:
            return y + 1
    raise SystemExit('차트 판 위 테두리를 못 찾았다 — 색 구성이 바뀌었나 본다')


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'chart.png'
    size = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else WIN_SIZE

    hwnd = find_window()
    if u.IsIconic(hwnd):
        u.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(1.0)
    u.SetWindowPos(hwnd, 0, 0, 0, size[0], size[1], SWP_NOMOVE | SWP_NOZORDER)
    time.sleep(0.8)

    chart = MT5().open_charts()[0]
    full = shoot(hwnd)
    top = chart_top(full)
    im = full.crop((0, top, chart['rect_right'], top + chart['rect_bottom']))
    im.save(out)
    print(f"{chart['symbol']} {chart['period']} · 보이는 봉 {chart['page_bars']} · "
          f"차트 판 {im.size[0]}x{im.size[1]} (본창 {full.size[0]}x{full.size[1]}, 위 {top}) → {out}")


if __name__ == '__main__':
    main()
