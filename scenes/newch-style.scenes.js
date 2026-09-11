/**
 * 새 채널 스타일 스틸 v4 — "차트명가 전편의 결 + 적당한 변형" (2026-09-11).
 *
 * v3 는 r13(차12) 한 회차 문법에 치중했다. lab/finalscan 콘택트시트 10편을 훑어 전편 공통 결로 바꾼다:
 *   흰 풀블리드 차트 · 굵고 매끈한 이평선 여러 개(#1 10/20/50) · 선 끝에 붙는 색 알약(#1·#8) ·
 *   손절/익절 색 블록 · 지지선 초록 띠 / 저항선 빨간 띠 + 알약(#5·#6·#8) · 당일 시가 점선+알약(#6) ·
 *   매수 우위 분홍 면(#3) · 소프트 원 · ①②③ 알약 · 궁서 자막 · 우상단 워터마크 · 서브패널 하나(#2·#7·#8·#9).
 * 렌더러가 그리는 것: 캔들 · 이평 3 · RSI 패널 · 손절/익절 존(라벨은 frame.py 알약) · 태그 · 손그림 원 · 문구.
 * 변형은 frame.py 에서 건다 (타이틀 블록 · 알약 · 라벨 자리·모양). 차트 값·색은 STYLE.md 실측 그대로.
 * 시장은 seed 11(차11 20일선 눌림목 견본) — 특정 회차 데이터에 안 묶이게 합성 캔들을 쓴다.
 */
const LV = { entry: 23795, stop: 23665, target: 24055 };

export default {
  title: '새 채널 스타일 v4 — 전편의 결 + 적당한 변형',
  width: 1920,
  height: 1080,
  fps: 30,
  theme: { preset: 'chartmyeongga' },
  market: {
    seed: 11, base: 23400, tick: 0.25, vol: 58, barMinutes: 1440,
    startTime: Date.UTC(2026, 0, 5, 0, 0),
    segments: [
      { type: 'trend', dir: 1, bars: 34, strength: 0.52 },
      { type: 'pullback', dir: 1, bars: 9, strength: 1.15 },
      { type: 'trend', dir: 1, bars: 52, strength: 0.82 },
    ],
  },
  scenes: [{
    id: 'sources',
    name: '도구 총집합 v4',
    duration: 0.5,
    chart: {
      visibleBars: 58,
      reveal: 64,
      pricePad: 0.12,
      showGrid: false, showAxes: false, showLast: false,
      include: [LV.stop - 110, LV.target + 300],
      layout: { padLeft: 74, padRight: 150, padTop: 300, padBottom: 170, rightGap: 6 },
      /* #1 문법: 10일선 빨강 · 20일선 주황(브랜드) · 50일선 초록. 굵고 매끈하게 */
      ma: [
        { type: 'sma', period: 10, width: 6, color: '#D8181B' },
        { type: 'ema', period: 20, width: 6 },
        { type: 'sma', period: 50, width: 6, color: '#0DA82A' },
      ],
      rsi: {
        period: 14, height: 0.22, gap: 24, baseline: null, width: 3, color: '#1E78C8',
        levels: [
          { v: 70, label: '', dash: [6, 6], color: 'rgba(0,0,0,0.45)', width: 1.5 },
          { v: 30, label: '', dash: [6, 6], color: 'rgba(0,0,0,0.45)', width: 1.5 },
        ],
      },
    },
    layers: [
      /* 손절·익절 존 — 진입 2봉 뒤부터. 라벨은 frame.py 가 오른끝 알약으로 (변형) */
      { type: 'cmgLevel', price: LV.stop, fromBar: 44, fillTo: LV.entry, fill: '#FEBABA', color: '#9F0000', thickness: 14, growDur: 0, in: [-1, 0.2] },
      { type: 'cmgLevel', price: LV.target, fromBar: 44, fillTo: LV.entry, fill: '#BAFDC0', color: '#14FF36', thickness: 14, growDur: 0, in: [-1, 0.2] },
      { type: 'cmgLevel', price: LV.entry, fromBar: 44, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0, in: [-1, 0.2] },
      /* 태그 */
      { type: 'cmgArrow', bar: 42, price: LV.entry + 30, dir: 'buy', label: '매수', size: 34, gap: 18, popDur: 0, in: [-1, 0.2] },
      { type: 'cmgArrow', bar: 28, dir: 'sell', label: '매도', size: 34, gap: 18, popDur: 0, color: '#0200F3', in: [-1, 0.2] },
      /* 손그림 원(색연필) — 재지지 */
      { type: 'cmgCircle', bar: 52, price: LV.entry + 130, rx: 66, ry: 74, width: 9, color: '#C0272D', drawDur: 0, in: [-1, 0.2] },
    ],
  }],
};
