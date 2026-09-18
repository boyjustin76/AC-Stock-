"""한 장면을 '팀장 방식'으로 찍는다 — 차트를 그 시각으로 옮기고 **창을 그대로** 캡처한다.

왜 이 조합인가 (실측 2026-09-18)
 · `ChartScreenShot` 은 요청한 크기로 다시 그려 화질은 좋은데, **스크롤 자리를 무시하고 늘 최신 구간**을 그린다.
   (지표 로그로 확인: 첫보임=2080 인 상태에서 찍어도 그림은 최신이었다.)
 · 반면 `ChartNavigate` 로 **화면을 옮기는 것은 확실히 된다.**
 · 팀장 그림도 어차피 **MT5 창 캡처**(1920×1032, 도구모음 포함)다.
 → 그래서 지표로 옮겨 놓고, 창을 PrintWindow 로 찍고, 다시 되돌린다.

쓰기: python capture_scene.py <출력.png> "2026.09.15 14:45" [지표] [배율]
      지표 예: EMA20,EMA200,ADX   (빈칸이면 지금 차트 그대로)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capture as CAP  # noqa: E402
from mcp import MT5  # noqa: E402

MQL5 = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'MetaQuotes', 'Terminal',
                    os.environ.get('MT5_TERMINAL_ID', '061BAFBAE5645A1204F350EE84A4B55F'), 'MQL5')
IND = os.path.join(MQL5, 'Indicators', 'CMG_Shot.ex5')


def _attach(m, chart_id, params, settle=3.5):
    m.call('chart_add_indicator', {
        'chart_id': chart_id, 'indicator_name': 'CMG_Shot',
        'custom_indicator_path': IND, 'indicator_parameters': params})
    time.sleep(settle)


def scene(out, end_time, inds='', scale=-1, restore=True):
    m = MT5()
    chart = m.open_charts()[0]
    cid = str(chart['chart_id'])

    # 1) 그 시각으로 옮긴다 (ShotFile 을 비우면 찍지 않고 자리만 잡는다)
    _attach(m, cid, f'ShotFile=,ShotEndTime={end_time},ShotScale={scale},'
                    f'ShotInds={inds},SelfRemove=true')
    # 2) 창을 그대로 찍는다
    hwnd = CAP.find_window()
    full = CAP.shoot(hwnd)
    top = CAP.chart_top(full)
    im = full.crop((0, top, chart['rect_right'], top + chart['rect_bottom']))
    os.makedirs(os.path.dirname(os.path.abspath(out)) or '.', exist_ok=True)
    im.save(out)
    # 3) 보던 자리로 되돌린다
    if restore:
        _attach(m, cid, 'ShotFile=,ShotRestore=true,SelfRemove=true', settle=2.0)
    return out, im.size, chart


if __name__ == '__main__':
    out = sys.argv[1]
    end = sys.argv[2]
    inds = sys.argv[3] if len(sys.argv) > 3 else ''
    scale = int(sys.argv[4]) if len(sys.argv) > 4 else -1
    p, size, ch = scene(out, end, inds, scale)
    print(f"{ch['symbol']} {ch['period']} · {end} · {size[0]}x{size[1]} → {p}")
