/**
 * 차12 썸네일 C안 — 70·30선은 버리세요 (과매수 역추세의 함정).
 * 본편 컷14(fail-blind)와 같은 seed 25 강추세장.
 *   RSI 70 돌파 bar35 → 45봉 유지, 이후 +4.2%
 * 빨간 70선·빨간 RSI 구간이 '버릴 것', 회색 55/45 두 줄이 '우리가 쓸 것'.
 */
import { COLOR } from './cmg12-guide.scenes.js';

const W = 1920, H = 1080;

export default {
  name: '차12 C안 — 70·30의 함정', width: W, height: H, fps: 30,
  theme: { preset: 'chartmyeongga' },
  market: {
    seed: 25, base: 15200, tick: 0.25, vol: 30, barMinutes: 1,
    startTime: Date.UTC(2026, 0, 7, 9, 0),
    segments: [
      { type: 'trend', dir: 1, bars: 26, strength: 0.45 },
      { type: 'trend', dir: 1, bars: 26, strength: 1.35 },
      { type: 'trend', dir: 1, bars: 18, strength: 0.9 },
      { type: 'trend', dir: 1, bars: 10, strength: 0.6 },
    ],
  },
  scenes: [{
    id: 'C', name: '70선의 함정', duration: 0.5,
    chart: {
      visibleBars: 52, reveal: 74, pricePad: 0.10,
      /* 타이틀 두 줄이 좌상단을 덮는다 — 위에 없는 값을 끼워 캔들을 아래로 내린다 */
      include: [16330],
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
      // 버릴 것 — 70선 위에서 안 꺾이고 계속 버틴다
      { type: 'rsiZone',  from: 70, to: 100, color: '#FE0000', opacity: 0.16, in: [-1, 0.2] },
      { type: 'rsiLevel', v: 70, label: '70선', color: '#FE0000', width: 5, growDur: 0, in: [-1, 0.2],
        // 기본 labelX(=20)는 틀(26px) 밑에 왼쪽이 잘린다
        labelX: 46 },
      { type: 'rsiTrace', fromBar: 36, toBar: 64, width: 12, color: '#FE0000', drawDur: 0, in: [-1, 0.2] },
      // 과매수라고 매도를 잡았다면 — 추세에 그대로 밀린다
      { type: 'cmgArrow', bar: 36, price: 15408, dir: 'sell', label: '매도', size: 62, gap: 22, popDur: 0, color: '#0000FF' },
      { type: 'cmgArrow', bar: 73, price: 15975, dir: 'sell', label: '손절', size: 62, gap: 22, popDur: 0, color: '#9F0000' },
    ],
  }],
};
