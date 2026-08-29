/* sl-11-4 컷② 무주석 바닥 스틸용 — reveal 63 고정, 레이어 없음 */
const FPS = 30;
const f = (n) => n / FPS;

const chartBase = {
  visibleBars: 32,
  pricePad: 0.14,
  showGrid: false,
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 0, padBottom: 0, rightGap: 6 },
  ma: [{ type: 'ema', period: 20, width: 5 }],
};

export default {
  title: '차11-4 컷2 무주석 바닥',
  width: 1080,
  height: 1080,
  fps: FPS,
  theme: { preset: 'chartmyeongga' },
  market: {
    seed: 11,
    base: 23400,
    tick: 0.25,
    vol: 58,
    barMinutes: 1440,
    startTime: Date.UTC(2026, 0, 5, 0, 0),
    segments: [
      { type: 'trend', dir: 1, bars: 34, strength: 0.52 },
      { type: 'pullback', dir: 1, bars: 9, strength: 1.15 },
      { type: 'trend', dir: 1, bars: 52, strength: 0.82 },
      { type: 'trend', dir: -1, bars: 8, strength: 1.05 },
      { type: 'range', bars: 18, width: 1.1 },
    ],
  },
  scenes: [
    {
      id: 'cut2-base-r63',
      name: '무주석 reveal 63',
      duration: f(4),
      chart: { ...chartBase, reveal: [{ t: 0, v: 63 }], zoom: [{ t: 0, v: 1 }] },
      layers: [],
    },
  ],
};
