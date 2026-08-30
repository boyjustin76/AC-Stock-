/* RSI 패널 스모크 테스트 — 구도·기준선·라인·레이어 앵커 확인용 */
const FPS = 60000 / 1001;
export default {
  title: 'RSI smoke',
  width: 1920, height: 1080, fps: FPS, fpsExpr: '60000/1001',
  theme: { preset: 'chartmyeongga' },
  market: {
    seed: 21, base: 23400, tick: 0.25, vol: 58, barMinutes: 1,
    startTime: Date.UTC(2026, 0, 5, 9, 0),
    segments: [
      { type: 'trend', dir: 1, bars: 40, strength: 0.6 },
      { type: 'pullback', dir: 1, bars: 6, strength: 1.0 },
      { type: 'trend', dir: 1, bars: 30, strength: 0.7 },
    ],
  },
  scenes: [
    {
      id: 'smoke',
      name: 'RSI smoke',
      duration: 2,
      chart: {
        visibleBars: 56, pricePad: 0.14, showGrid: false, showAxes: false, showLast: false,
        layout: { padLeft: 60, padRight: 150, padTop: 90, padBottom: 60, rightGap: 5 },
        ma: [
          { type: 'sma', period: 10, width: 5, color: '#F38808' },
          { type: 'sma', period: 34, width: 5, color: '#0D9488' },
        ],
        rsi: {
          period: 10, height: 0.27, range: [15, 95],
          levels: [
            { v: 55, label: '55', color: 'rgba(17,17,17,0.6)' },
            { v: 45, label: '45', color: 'rgba(17,17,17,0.6)' },
          ],
        },
        reveal: [{ t: 0, v: 70 }],
      },
      layers: [
        { type: 'rsiLevel', v: 70, label: '70', color: '#E90054', in: [0.1, 0.2] },
        { type: 'rsiZone', from: 70, to: 100, color: '#E90054', in: [0.2, 0.2] },
        { type: 'cmgCircle', bar: 62, rsi: 62, rx: 60, ry: 44, width: 9, in: [0.1, 0.1], drawDur: 0.3 },
        { type: 'cmgNote', bar: 20, rsi: 20, text: 'RSI 앵커', size: 36, color: '#111111', stroke: '#FFFFFF', in: [0, 0.1] },
      ],
    },
  ],
};
