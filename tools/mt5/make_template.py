"""촬영용 MT5 차트 템플릿(.tpl)을 만든다.

    python tools/mt5/make_template.py [--name CMG_촬영] [--install] [--show]

왜 손으로 안 만드는가: 템플릿은 UTF-16 텍스트라 색·굵기를 코드로 정확히 넣을 수 있다.
눈으로 맞추면 회차마다 달라진다(브랜드 값은 실측으로 고정한다 — CLAUDE.md).

색은 MT5 규칙대로 **BGR 정수**로 넣는다. 아래 표는 `#RRGGBB` 로 적고 변환은 코드가 한다.
기준은 김직선 화면(흰 바탕·밝은 테마·트레이딩뷰 기본색)이다 — 06_실험실/김직선_레퍼런스/판독_1차.md
"""
import argparse
import io
import os

TERMINAL_ID = os.environ.get('MT5_TERMINAL_ID', '061BAFBAE5645A1204F350EE84A4B55F')

# ── 색 (#RRGGBB) ────────────────────────────────────────────────────────────
#  김직선 화면 픽셀 실측 (2026-09-30, 프레임 34장). 그는 MT5 가 아니라 TradingView 를 쓴다 —
#  값만 가져와 MT5 로 흉내 낸다. 근거: 06_실험실/김직선_레퍼런스 프레임 Tj8DYiNS0LQ·ZV7i5VVfIAU
BG = '#FFFFFF'          # 바탕 — 순백 (플롯 영역의 94~96%)
FG = '#101114'          # 글자·축 — 거의 검정
GRID = '#E6E9EF'        # 격자 (그는 격자를 안 쓴다 — grid=0 이라 보이지 않는다)
UP = '#12A87F'          # 양봉 — 꽉 찬 캔들, 테두리·꼬리도 같은 색
DOWN = '#E01F45'        # 음봉 — 같음
LINE = '#2962FF'        # 선차트 (안 씀)
LAST = '#969696'        # 현재가 선 — 회색 점선

# ── 이동평균선 (기간, 색, 굵기) ─────────────────────────────────────────────
#  굵기 2px 는 실측값이다(그의 화면도 2px). 색은 실측이 아니다 —
#  그의 선은 2px 라 유튜브 압축에 흐려져 흰 바탕과 섞였다(녹색 ≈ #84BD86 는 역산값).
#  흐린 값을 그대로 쓰면 우리 화면에서 안 보인다. 그래서 **또렷한 색**을 우리가 정한다.
MAS = [
    (5,   '#FF9800', 2),   # 주황
    (20,  '#2962FF', 2),   # 파랑  — 기준선
    (60,  '#9C27B0', 2),   # 보라
    (120, '#607D8B', 2),   # 회청
]

HEAD = """<chart>
id=0
symbol={symbol}
period_type=0
period_size={period}
digits=2
tick_size=0.000000
position_time=0
scale_fix=0
scale_fixed_min=0.000000
scale_fixed_max=0.000000
scale_fix11=0
scale_bar=0
scale_bar_val=1.000000
scale={scale}
mode=1
fore=0
grid={grid_on}
volume=0
scroll=0
shift=1
shift_size={shift}
fixed_pos=0.000000
ticker=0
ohlc=0
one_click=0
one_click_btn=0
bidline=0
askline=0
lastline=1
days=0
descriptions=0
tradelines=0
tradehistory=0
window_left=0
window_top=0
window_right=0
window_bottom=0
window_type=1
floating=0
floating_left=0
floating_top=0
floating_right=0
floating_bottom=0
floating_type=1
floating_toolbar=1
floating_tbstate=
background_color={bg}
foreground_color={fg}
barup_color={up}
bardown_color={down}
bullcandle_color={up}
bearcandle_color={down}
chartline_color={line}
volumes_color={fg}
grid_color={grid}
bidline_color={up}
askline_color={down}
lastline_color={last}
stops_color={down}
windows_total=1

<window>
height=100.000000
objects=0

<indicator>
name=Main
path=
apply=1
show_data=1
scale_inherit=0
scale_line=0
scale_line_percent=50
scale_line_value=0.000000
scale_fix_min=0
scale_fix_min_val=0.000000
scale_fix_max=0
scale_fix_max_val=0.000000
expertmode=0
fixed_height=-1
</indicator>
"""

MA_BLOCK = """
<indicator>
name=Moving Average
path=
apply=1
show_data=1
scale_inherit=0
scale_line=0
scale_line_percent=50
scale_line_value=0.000000
scale_fix_min=0
scale_fix_min_val=0.000000
scale_fix_max=0
scale_fix_max_val=0.000000
expertmode=0
fixed_height=-1

<graph>
name=
draw=129
style=0
width={width}
color={color}
</graph>
period={period}
method=0
</indicator>
"""

TAIL = """</window>
</chart>
"""


def bgr(hex_color):
    """'#RRGGBB' → MT5 가 쓰는 BGR 정수."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b << 16) | (g << 8) | r


def build(symbol='US100._REPLAY', period=2, scale=4, shift=50.0, grid=False, mas=None):
    mas = MAS if mas is None else mas
    out = HEAD.format(symbol=symbol, period=period, scale=scale, shift='%.6f' % shift,
                      grid_on=1 if grid else 0,
                      bg=bgr(BG), fg=bgr(FG), up=bgr(UP), down=bgr(DOWN),
                      line=bgr(LINE), grid=bgr(GRID), last=bgr(LAST))
    for period_, color, width in mas:
        out += MA_BLOCK.format(width=width, color=bgr(color), period=period_)
    return out + TAIL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='CMG_촬영')
    ap.add_argument('--symbol', default='US100._REPLAY')
    ap.add_argument('--period', type=int, default=2, help='분 단위 (2 = M2)')
    ap.add_argument('--scale', type=int, default=4, help='0~5, 클수록 봉이 굵다')
    ap.add_argument('--shift', type=float, default=50.0, help='오른쪽 여백 %% (10~50)')
    ap.add_argument('--grid', action='store_true', help='격자를 켠다')
    ap.add_argument('--mas', default=None,
                    help="이동평균선을 직접 정한다. 보기: '20:#2962FF:2,60:#9C27B0:2' (빈 문자열이면 없음)")
    ap.add_argument('--out', default=None, help='저장 위치 (기본: MQL5\\Profiles\\Templates)')
    ap.add_argument('--show', action='store_true', help='만든 내용을 화면에도 찍는다')
    a = ap.parse_args()

    mas = MAS
    if a.mas is not None:
        mas = []
        for part in [p for p in a.mas.split(',') if p.strip()]:
            period_, color, width = part.split(':')
            mas.append((int(period_), color, int(width)))

    text = build(a.symbol, a.period, a.scale, a.shift, a.grid, mas)
    dst = a.out or os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'MetaQuotes',
                                'Terminal', TERMINAL_ID, 'MQL5', 'Profiles', 'Templates',
                                a.name + '.tpl')
    io.open(dst, 'w', encoding='utf-16', newline='\r\n').write(text)
    print('템플릿 →', dst)
    print('이동평균선 %d개: %s' % (len(mas), ', '.join('%d(%s,%dpx)' % m for m in mas)))
    if a.show:
        print(text)


if __name__ == '__main__':
    main()
