/**
 * 차12 썸네일 B안 — 골든크로스에 사지 마세요 (횡보 가짜 신호).
 * 본편 컷13(fail-chop)과 같은 seed 96 횡보장.
 *   10일/34일선 교차 10회 @37,43,44,50,52,65,66,68,69,79 · 박스 15393~15498
 * 교차마다 빨간 원 — 열 번 다 가짜였다는 것이 한눈에 보이게.
 */
import { COLOR } from './cmg12-guide.scenes.js';

const W = 1920, H = 1080;

export default {
  name: '차12 B안 — 골든크로스의 함정', width: W, height: H, fps: 30,
  theme: { preset: 'chartmyeongga' },
  market: {
    seed: 96, base: 15450, tick: 0.25, vol: 26, barMinutes: 1,
    startTime: Date.UTC(2026, 0, 9, 9, 0),
    segments: [
      { type: 'range', bars: 30, width: 0.9 },
      { type: 'range', bars: 30, width: 1.1 },
      { type: 'range', bars: 25, width: 0.9 },
    ],
  },
  scenes: [{
    id: 'B', name: '가짜 신호', duration: 0.5,
    chart: {
      visibleBars: 52, reveal: 80, pricePad: 0.10,
      /* 타이틀 두 줄이 좌상단을 덮는다 — 위에 없는 값을 끼워 캔들을 아래로 내린다 */
      include: [15572],
      showGrid: false, showAxes: false, showLast: false,
      /* padRight 40 — RSI 55/45 라벨은 패널 오른쪽 끝에 붙는데,
         그대로 두면 완성본에서 틀(핑크 26px) 밑에 반쯤 잘린다. 40px 안으로 들인다.
         차트 배경이 흰색이라 오른쪽에 생긴 띠는 종이 배경과 구분되지 않는다 */
      layout: { padLeft: 0, padRight: 40, padTop: 0, padBottom: 0, rightGap: 2 },
      ma: [
        { type: 'sma', period: 10, width: 9, color: COLOR.ma10 },
        { type: 'sma', period: 34, width: 9, color: COLOR.ma34 },
      ],
      rsi: {
        period: 10, height: 0.24, gap: 22, baseline: 50, color: COLOR.rsi, width: 7,
        levels: [
          { v: 55, label: '55', color: 'rgba(17,17,17,0.62)', width: 3 },
          { v: 45, label: '45', color: 'rgba(17,17,17,0.62)', width: 3 },
        ],
      },
    },
    layers: [
      { type: 'cmgBadge', text: 'RSI', x: 1560, y: 1005, size: 52, color: COLOR.badge, in: [-1, 0.2] },
      // 교차마다 빨간 원 — 본편 컷13 실측 좌표 그대로
      { type: 'cmgCircle', bar: 37, price: 15452, rx: 50, ry: 44, width: 11, color: '#E90054', drawDur: 0, in: [-1, 0.2] },
      { type: 'cmgCircle', bar: 43, price: 15452, rx: 50, ry: 44, width: 11, color: '#E90054', drawDur: 0, in: [-1, 0.2] },
      { type: 'cmgCircle', bar: 50, price: 15450, rx: 50, ry: 44, width: 11, color: '#E90054', drawDur: 0, in: [-1, 0.2] },
      { type: 'cmgCircle', bar: 65, price: 15454, rx: 50, ry: 44, width: 11, color: '#E90054', drawDur: 0, in: [-1, 0.2] },
      { type: 'cmgCircle', bar: 72, price: 15458, rx: 50, ry: 44, width: 11, color: '#E90054', drawDur: 0, in: [-1, 0.2] },
      // 그때마다 손절만 남는다
      { type: 'cmgArrow', bar: 44, price: 15398, dir: 'sell', label: '손절', color: '#9F0000', size: 60, gap: 22, popDur: 0 },
      { type: 'cmgArrow', bar: 69, price: 15414, dir: 'sell', label: '손절', color: '#9F0000', size: 60, gap: 22, popDur: 0 },
    ],
  }],
};
