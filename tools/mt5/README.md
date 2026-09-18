# MT5 차트 화면 가져오기

MetaTrader 5 화면을 **그대로** 영상 배경으로 쓰고, 그 위에 우리 표시를 **정확한 자리**에 얹기 위한 도구다.
이정찬 결정 2026-09-18: 차트는 우리가 그리지 않고 MT5 것을 쓴다.

## 왜 이 구성인가 (전부 이 PC 에서 실측)

- MT5 빌드 5955 부터 터미널에 **MCP 서버가 내장**돼 있다(도구 > 옵션 > MCP). 도구 50종을 확인했는데
  **스크린샷 도구는 없다.** MQL5 `ChartScreenShot()` 은 스크립트를 컴파일해 차트에 올려야 해서 자동화가 안 된다.
  → 화면은 **창 캡처**로 가져오고, 값은 **MCP** 로 가져온다.
- 봉이 어디에 그려졌는지는 MCP 가 알려주지 않는다. 그래서 찍은 그림과 실제 OHLC 를 맞춰 **스스로 보정**한다.

## 쓰는 순서

```bash
# 0) 키 — 저장소에 적지 않는다. MT5 설정 창에서 복사해 여기에 둔다
#    C:\Users\user\.secrets\ac_keys.env  에  MT5_MCP_KEY=...
python tools/mt5/mcp.py                       # 붙는지 · 열린 차트 확인

# 1) 차트 판만 찍는다 (창 크기를 고정한 뒤 찍는다)
python tools/mt5/capture.py out/chart.png

# 2) 봉 격자와 가격축을 맞춘다 → calib.json
python tools/mt5/calibrate.py out/chart.png 410 "US100." M2 2026-08-28T14:00:00 2026-08-28T22:00:00
```

`calib.json` 이 나오면 (시각, 가격) 을 화면 좌표로 바꿀 수 있다.

```python
x = phase + slot * pitch          # slot = 첫 보이는 봉부터 센 번호
y = a * price + b
```

## 실측값 (2026-09-18 · HedgeHood 데모 · US100. M2)

| 것 | 값 |
|---|---|
| 창 크기 | 1936×1056 → 차트 판 **1920×608** · 차트 판 첫 줄 y=85 |
| 보이는 봉 | **117** (MCP `page_bars` 와 그림에서 센 것이 일치) |
| 봉 간격 | **16.00px** · 기준 x 10.0 |
| 가격→y | `y = -1.069944 * price + 31847.928` · **RMS 1.93px** |

## 걸렸던 것

1. **인증** — `Authorization: Bearer <키>` 만 받는다. `X-API-Key` 류는 401.
2. **세션** — `initialize` 응답의 `Mcp-Session-Id` 를 이후 요청에 싣고, `notifications/initialized` 를
   **id 없이** 보내야 열린다. id 를 붙이면 `MCP session is not initialized`.
3. **PrintWindow** — 차트 자식 창 핸들을 줘도 본 창을 그린다. 그래서 본 창을 찍고 잘라낸다.
   자식 창 좌표(`GetWindowRect`)는 MDI·DPI 때문에 어긋나므로 **그림에서** 차트 판을 찾는다.
4. **이동평균선이 봉과 같은 빨강**이라 색만으로 못 가른다. 청록(상승봉)으로 칸 간격을 먼저 구하고,
   칸 중심 열에서 가장 긴 줄기만 봉으로 본다. 이걸 안 하면 봉이 203개로 잡히고 오차가 50px 까지 벌어진다.
5. **창 크기를 고정**해야 한다. 창이 바뀌면 보이는 봉 수와 픽셀 간격이 달라져 지난 보정이 못 쓰게 된다.

## 안 건드리는 것

`trade_*` 도구 7종(주문·청산·손절수정)은 **부르지 않는다.** 읽기만 한다.

## 더 깨끗한 길 — MT5 가 직접 그린 PNG (`shot.py`)

창 캡처는 화면에 보이는 픽셀 그대로라 확대하면 뭉갠다. MQL5 `ChartScreenShot()` 은
**요청한 크기로 차트를 다시 그린다.** 3840×2160 을 달라고 하면 그 해상도로 새로 그려 준다.

MT5 에는 **SVG·HTML 같은 벡터 내보내기가 없다.** 차트는 GDI 로 그린 래스터고, 웹 터미널도 canvas 다.
그래서 '안 깨지는' 방법은 벡터가 아니라 **큰 크기로 다시 그리게 하는 것**이다.

```bash
# 한 번만 — 지표를 컴파일한다
"C:\Program Files\HedgeHood MT5 Terminal\metaeditor64.exe" \
  /compile:"...\MQL5\Indicators\CMG_Shot.mq5" /log

# 그 뒤로는
python tools/mt5/shot.py out/chart4k.png 3840 2160
```

`shot.py` 는 **새 차트를 열고 템플릿을 입혀** 사람 차트와 같은 모습으로 만든 뒤 지표를 붙인다.
지표는 PNG 를 쓰고 스스로 빠지며, 끝나면 새 차트를 닫는다 — **사람이 쓰던 차트는 안 건드린다.**

**걸리는 것 하나**: 터미널은 쓸 수 있는 지표 목록을 캐시해 둔다. 새로 컴파일한 `CMG_Shot` 이
목록에 없으면 `chart_add_indicator` 가 `specified indicator not found in base` 를 낸다.
→ MT5 **탐색기(Navigator) 우클릭 > 새로고침** 한 번(또는 터미널 재시작)이면 잡힌다. 그 뒤론 자동이다.
