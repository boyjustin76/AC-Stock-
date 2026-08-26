/**
 * 오버레이 세트 — 배경이 투명한 컷.
 *
 * 실제 촬영본이나 다른 화면 위에 차트만 얹을 때 씁니다.
 *   npm run render -- --config scenes/nq-overlay.scenes.js --all --format alpha
 * 결과는 알파 채널이 살아 있는 .mov (QuickTime RLE) 라, 프리미어·파컷·다빈치에
 * 그냥 끌어다 놓으면 배경이 비칩니다.
 */
const LV = {
  boxBottom: 24680,
  entry: 24688.75,
  stop: 24614.75,
  target: 24836.75,
};

const market = {
  seed: 42,
  base: 24780,
  tick: 0.25,
  vol: 20,
  barMinutes: 5,
  startTime: Date.UTC(2026, 5, 12, 13, 30),
  segments: [
    { type: 'trend', dir: -1, bars: 24, strength: 0.55 },
    { type: 'range', bars: 24, width: 1.6 },
    { type: 'breakout', dir: 1, bars: 34, strength: 1.15 },
  ],
};

export default {
  title: '해외선물 차트 컷씬 — 투명 배경 오버레이 세트',
  width: 1920,
  height: 1080,
  fps: 60,
  market,
  theme: { transparent: true },

  scenes: [
    {
      id: 'ov-chart',
      name: '오버레이 — 캔들만 그려지기',
      duration: 5,
      fadeIn: 0.3,
      fadeOut: 0.4,
      chart: {
        visibleBars: 58,
        showGrid: false,
        ma: [{ type: 'ema', period: 20, color: 'rgba(150,190,255,0.75)', width: 3 }],
        reveal: [
          { t: 0, v: 20 },
          { t: 4.4, v: 68, ease: 'outCubic' },
        ],
      },
      layers: [{ type: 'hud', symbol: 'NQ', name: '나스닥 100 선물', tf: '5분', in: [0.2, 0.5] }],
    },
    {
      id: 'ov-tpsl',
      name: '오버레이 — 손절·익절 박스',
      duration: 5,
      fadeIn: 0.3,
      fadeOut: 0.4,
      chart: {
        visibleBars: 58,
        showGrid: false,
        showAxes: false,
        include: [LV.target, LV.stop],
        layout: { rightGap: 22 },
        reveal: [{ t: 0, v: 71.5 }, { t: 5, v: 72.5, ease: 'linear' }],
      },
      layers: [
        { type: 'marker', bar: 68, dir: 'long', price: 24668.75, in: [0.2, 0.35], pulse: false, size: 22 },
        {
          type: 'tradeBox',
          entry: LV.entry,
          tp: LV.target,
          sl: LV.stop,
          fromBar: 68,
          in: [0.5, 0.4],
          growDur: 0.8,
        },
      ],
    },
    {
      id: 'ov-pnl',
      name: '오버레이 — 손익 카운터만',
      duration: 5,
      fadeIn: 0.3,
      fadeOut: 0.4,
      chart: {
        visibleBars: 58,
        alpha: 0, // 차트는 그리지 않고 숫자 패널만 남긴다
        showGrid: false,
        showAxes: false,
        showLast: false,
        reveal: [{ t: 0, v: 82 }],
      },
      layers: [
        {
          type: 'counter',
          label: '평가 손익',
          from: 0,
          to: 2960,
          countFrom: 0.4,
          dur: 2.6,
          prefix: '$',
          signed: true,
          decimals: 0,
          size: 84,
          x: 96,
          y: 200,
          in: [0.2, 0.5],
        },
        {
          type: 'counter',
          label: '포인트',
          from: 0,
          to: 148,
          countFrom: 0.4,
          dur: 2.6,
          suffix: ' pt',
          signed: true,
          decimals: 2,
          size: 54,
          x: 96,
          y: 376,
          in: [0.4, 0.5],
        },
      ],
    },
  ],
};
