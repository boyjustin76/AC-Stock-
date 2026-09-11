/**
 * 새 채널 스타일 스틸 v3 — 브라우저 창 안, r13 실데이터 차트 + 화이트리스트 §4 어휘 (2026-09-11).
 *
 * v2 반려 뒤 brand/FX-WHITELIST.md 를 읽고 다시 짰다 — "여기 없는 효과·연출·기법은 쓰지 않는다".
 * 차트·좌표·봉 번호는 scenes/cmg12s-buy.scenes.js(r13, 총괄 검증본)에서 그대로 가져왔다:
 *   실제 NQ 1분봉(SLICE.pullbackM1) · 10일선 빨강 / 34일선 주황 · RSI 파랑 + 55/45 점선 ·
 *   눌림 L197(RSI 52.5) · 55 재돌파 L199 · 진입 L200 시가 29436.50 · 손절 29430.50 · 익절 1:2 29448.50.
 * 렌더러가 그리는 것: 캔들 · 이평 · RSI 패널 · 색박스 라벨(§4-1) · 손그림 원(§4-10) · 선 덧칠 ·
 *   문구 · 매수/익절 태그(§4-3) · 손절1/익절2 존(§4-5, inzone 라벨 = 차명#2 문법).
 * frame.py 가 얹는 것: 브라우저 창 · 타이틀 블록 · ①②③ 핑크 알약(§4-2, 두 줄) · 소프트 원 글로우(§4-8) ·
 *   저항선/지지선 + 박스 라벨(§4-7) · 검은 채널(§4-7) · 빨간 ? · ✓(§4-12) · 궁서 자막 · 워터마크.
 *
 * cmg12s-base.js 를 import 하지 않는 이유: 그 파일은 NQ_5m.json 까지 로드하는데 이 PC 에 없다.
 * 필요한 값만 아래에 그대로 옮겼다 (출처 주석).
 */
import { loadBars, sliceBars } from '../src/market/loadBars.js';

const m1 = await loadBars('data/nq/NQ_1m.json');
const slice = sliceBars(m1.bars, { start: 1083, count: 300 });   // cmg12s-base SLICE.pullbackM1

/* cmg12s-base COLOR (차명#2 픽셀 실측) */
const COLOR = {
  ma10: '#D8181B', ma34: '#F09C0C', rsi: '#1E78C8', rsiFrame: '#2743C9', badge: '#F50C54',
  pencil: '#C0272D', line: '#111111', tp: '#14FF36', tpFill: '#BAFDC0', sl: '#9F0000', slFill: '#FEBABA',
  buy: '#E80001', sell: '#0200F3',
};
const LV = { entry: 29436.5, stop: 29430.5, target: 29448.5 };

export default {
  title: '새 채널 스타일 v3 — 브라우저 창 안 화이트리스트 도구 총집합',
  width: 1920,
  height: 1080,
  fps: 30,
  theme: { preset: 'cmgMt5', panelBorder: COLOR.rsiFrame },
  market: { bars: slice, tick: 0.25, barMinutes: 1 },
  scenes: [{
    id: 'sources',
    name: '도구 총집합 v3',
    duration: 0.5,
    chart: {
      /* cmg12s-base mt5ChartBase 그대로, 패딩만 브라우저 창 안 자리로 (창 y 150~1010) */
      visibleBars: 96,
      reveal: 224,                // 컷20 국면1 스틸 — 익절 태그까지 보인다
      pricePad: 0.14,
      showGrid: false, showAxes: false, showLast: false,
      include: [LV.stop - 4],
      layout: { padLeft: 74, padRight: 74, padTop: 300, padBottom: 170, rightGap: 3 },
      ma: [
        { type: 'sma', period: 10, width: 7, color: COLOR.ma10 },
        { type: 'sma', period: 34, width: 7, color: COLOR.ma34 },
      ],
      rsi: {
        period: 10, height: 0.24, gap: 24, baseline: null, width: 3, color: COLOR.rsi,
        levels: [
          { v: 55, label: '', dash: [6, 6], color: 'rgba(0,0,0,0.5)', width: 1.5 },
          { v: 45, label: '', dash: [6, 6], color: 'rgba(0,0,0,0.5)', width: 1.5 },
        ],
      },
    },
    layers: [
      /* §4-1 지표 색박스 라벨 — 창 왼쪽, 타이틀 블록 아래 */
      { type: 'cmgBadge', text: '10일선', x: 110, y: 330, size: 36, color: COLOR.ma10, border: false, popDur: 0, in: [-1, 0.2] },
      { type: 'cmgBadge', text: '34일선', x: 110, y: 390, size: 36, color: COLOR.ma34, border: false, popDur: 0, in: [-1, 0.2] },
      /* RSI 패널 좌상단 칩 (차명#9 문법) — y 는 probe 로 맞춘다 */
      { type: 'cmgBadge', text: 'RSI', x: 110, y: 800, size: 30, color: COLOR.rsiFrame, border: false, popDur: 0, in: [-1, 0.2] },
      /* §4-10 선 덧칠 — 정배열 구간의 10일선 */
      { type: 'cmgTrace', overlay: 0, fromBar: 176, toBar: 196, flatten: 0, width: 14, color: COLOR.ma10, drawDur: 0, in: [-1, 0.2] },
      { type: 'cmgNote', bar: 190, price: 29397, text: '정배열', size: 44, color: COLOR.line, in: [-1, 0.2] },
      /* §4-10 손그림 원 — RSI 눌림 · 양봉 마감 */
      { type: 'cmgCircle', bar: 197, rsi: 52.5, rx: 62, ry: 48, width: 9, color: COLOR.pencil, drawDur: 0, in: [-1, 0.2] },
      { type: 'cmgCircle', bar: 199, price: 29434, rx: 40, ry: 56, width: 9, color: COLOR.pencil, drawDur: 0, in: [-1, 0.2] },
      { type: 'cmgNote', bar: 206, price: 29480, text: '양봉 마감', size: 40, color: COLOR.line, in: [-1, 0.2] },
      /* §4-3 태그 · §4-5 존 (inzone 라벨 = 차명#2 '손절 1 / 익절 2' 블록 문법) */
      { type: 'cmgLevel', price: LV.entry, fromBar: 198, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0, in: [-1, 0.2] },
      { type: 'cmgLevel', price: LV.stop, fromBar: 198, fillTo: LV.entry, fill: COLOR.slFill, color: COLOR.sl, label: '손절 1', labelX: 1690, labelSide: 'right', labelSize: 26, labelHeight: 34, labelPadX: 16, thickness: 11, growDur: 0, in: [-1, 0.2] },
      { type: 'cmgLevel', price: LV.target, fromBar: 198, fillTo: LV.entry, fill: COLOR.tpFill, color: COLOR.tp, label: '익절 2', labelX: 1690, labelSide: 'right', labelSize: 26, labelHeight: 34, labelPadX: 16, thickness: 11, growDur: 0, in: [-1, 0.2] },
      { type: 'cmgArrow', bar: 200, price: LV.entry, dir: 'buy', label: '매수', size: 34, gap: 16, popDur: 0, in: [-1, 0.2] },
      { type: 'cmgArrow', bar: 207, price: 29457.5, dir: 'sell', label: '익절 1/2', color: '#0DA82A', size: 30, gap: 14, popDur: 0, in: [-1, 0.2] },
      { type: 'cmgArrow', bar: 216, price: 29528.25, dir: 'sell', label: '익절', color: '#0DA82A', size: 30, gap: 14, popDur: 0, in: [-1, 0.2] },
      { type: 'cmgProfit', entry: LV.entry, fromBar: 200, color: COLOR.tpFill, opacity: 0.3, in: [-1, 0.2] },
      { type: 'cmgNote', x: 1470, y: 322, text: '남은 절반은 추세 끝까지', size: 36, color: '#0DA82A', in: [-1, 0.2] },
    ],
  }],
};
