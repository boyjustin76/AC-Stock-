"""MT5 가 직접 그린 차트 PNG 를 받는다 (창 캡처보다 깨끗하다).

MQL5 `ChartScreenShot()` 은 **요청한 크기로 차트를 다시 그린다.** 창을 찍어 늘리는 것과 달라
글자·선이 뭉개지지 않는다. 다만 MQL5 를 돌려야 하므로 이렇게 한다:

  1. `Indicators\\CMG_Shot.mq5` 를 MetaEditor 로 컴파일해 둔다 (한 번만)
       "<MT5설치폴더>\\metaeditor64.exe" /compile:"<...>\\MQL5\\Indicators\\CMG_Shot.mq5" /log
  2. **새 차트**를 열고 템플릿을 입혀 사람 차트와 같은 모습으로 만든다 (사람 차트는 안 건드린다)
  3. 그 차트에 CMG_Shot 을 붙이면 지표가 PNG 를 쓰고 **스스로 빠진다**
  4. 새 차트를 닫는다

쓰기: python shot.py <출력.png> [가로 세로] [심볼 주기 템플릿]
"""
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import MT5  # noqa: E402

MQL5 = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'MetaQuotes', 'Terminal',
                    os.environ.get('MT5_TERMINAL_ID', '061BAFBAE5645A1204F350EE84A4B55F'), 'MQL5')
IND = os.path.join(MQL5, 'Indicators', 'CMG_Shot.ex5')
FILES = os.path.join(MQL5, 'Files')


def shot(out, width=1920, height=1080, symbol=None, period=None,
         template=None, end_time='', scale=-1, inds='', wait=30.0):
    """차트를 PNG 로 받는다.

    symbol 을 안 주면 **지금 열려 있는 차트**를 쓴다 — 사람이 맞춰 둔 모습과 자리 그대로다.
    지표는 찍고 스스로 빠지고, 설정은 건드리지 않는다(end_time·scale 을 줄 때만 만진다).
    symbol 을 주면 새 차트를 열어 템플릿을 입히고, 끝나면 닫는다.
    """
    if not os.path.exists(IND):
        raise SystemExit(f'{IND} 가 없다 — CMG_Shot.mq5 를 먼저 컴파일해라 (위 설명 1번)')
    name = 'cmg_shot_%d.png' % int(time.time())
    made = os.path.join(FILES, name)
    if os.path.exists(made):
        os.remove(made)

    m = MT5()
    opened = symbol is not None
    if opened:
        chart_id = str(m.call('chart_open', {'symbol': symbol, 'period': period or 'M2'})['chart_id'])
    else:
        charts = m.open_charts()
        if not charts:
            raise SystemExit('열린 차트가 없다')
        chart_id = str(charts[0]['chart_id'])
    try:
        if opened and template:
            m.call('chart_apply_template', {'chart_id': chart_id, 'template_filename': template})
            # 템플릿은 지표를 통째로 갈아 끼운다. 다 붙기 전에 우리 지표를 올리면 같이 지워진다.
            time.sleep(3.0)
        m.call('chart_add_indicator', {
            'chart_id': chart_id, 'indicator_name': 'CMG_Shot', 'custom_indicator_path': IND,
            'indicator_parameters': f'ShotFile={name},ShotW={width},ShotH={height},'
                                   f'ShotEndTime={end_time},ShotScale={scale},'
                                   f'ShotInds={inds},SelfRemove=true'})
        t0 = time.time()
        while time.time() - t0 < wait:
            if os.path.exists(made) and os.path.getsize(made) > 0:
                time.sleep(0.6)          # 다 쓸 때까지
                break
            time.sleep(0.4)
        else:
            raise SystemExit(f'{wait}초 안에 {made} 가 안 생겼다 — 터미널 로그를 봐라')
    finally:
        if opened:
            m.call('chart_close', {'chart_id': chart_id})

    os.makedirs(os.path.dirname(os.path.abspath(out)) or '.', exist_ok=True)
    shutil.move(made, out)
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    out = a[0] if a else 'chart_shot.png'
    wh = (int(a[1]), int(a[2])) if len(a) > 2 else (1920, 1080)
    rest = a[3:6] if len(a) > 5 else (None, None, None)   # 안 주면 열려 있는 차트
    p = shot(out, wh[0], wh[1], *rest)
    from PIL import Image
    print(f'{Image.open(p).size} → {p}')
