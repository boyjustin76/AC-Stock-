/**
 * 차11 「20일선의 비밀」 썸네일용 차트.
 *
 * 썸네일 규칙: 한 차트로 대본 전체를 설명할 수 있어야 한다.
 * 그래서 대본의 두 전략이 한 화면에 다 들어가도록 만들었다.
 *
 *   앞쪽  20일선이 옆으로 누운 박스권          → 전략 2 (횡보장 스위칭)
 *   중간  기울기가 상방으로 서고 눌림목 진입      → 전략 1 진입 조건
 *   뒤쪽  추세를 끝까지 끌고 가다가 완전 이격 음봉 → 전략 1 청산 조건
 *
 * 렌더는 정지 컷 한 장만 쓴다.
 *   npm run render -- --config scenes/thumb-ch11.scenes.js --all --stills 1
 */
const W = 1920;
const H = 1080;

// 실제 생성된 캔들에서 읽은 값 (seed 41, 96봉)
//   박스권 0~29   23,078 ~ 23,284
//   눌림목 53번   저가 23,231 → 진입 23,258
//   추세 고점 86번 23,770
//   이격 음봉 87~89 → 청산 23,699
const LV = { boxHi: 23284, boxLo: 23078, entry: 23258, exit: 23699 };

const chartBase = {
  visibleBars: 96,
  reveal: 96,
  pricePad: 0.10,
  showGrid: false,
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 0, padBottom: 0, rightGap: 2 },
  ma: [{ type: 'ema', period: 20, width: 7 }],
};

const market = {
  seed: 41,
  base: 23200,
  tick: 0.25,
  vol: 62,
  barMinutes: 1440,
  segments: [
    { type: 'range', bars: 30, strength: 0.9 },     // 20일선이 눕는 박스권 (전략 2)
    { type: 'trend', dir: 1, bars: 16, strength: 0.72 },
    { type: 'pullback', dir: 1, bars: 7, strength: 1.1 },  // 눌림목 (전략 1 진입)
    { type: 'trend', dir: 1, bars: 34, strength: 0.86 },   // 끝까지 홀딩
    { type: 'spike', dir: -1, bars: 9, strength: 1.25 },   // 완전 이격 음봉 = 청산
  ],
};

export default {
  name: '차11 20일선의 비밀 — 썸네일 차트',
  width: W,
  height: H,
  fps: 30,
  // 배경을 비워 두면 종이 텍스처 위에 그대로 얹을 수 있다
  theme: { preset: 'chartmyeongga', transparent: true },
  market,
  scenes: [
    {
      id: 'thumb-a',
      name: 'A안 — 추세를 끝까지 (매수 → 익절)',
      duration: 0.5,
      chart: { ...chartBase },
      // 태그는 여기서 그리지 않는다. 템플릿 .psd 에서 뜯어낸 진짜 버튼 픽셀을
      // tools/thumbnail_png.py 가 이 차트 위에 얹는다. 직접 그리면 회사 것과 달라진다.
      layers: [],
    },
    {
      id: 'thumb-b',
      name: 'B안 — 두 얼굴 (박스권 상하단 + 추세 진입)',
      duration: 0.5,
      chart: { ...chartBase },
      layers: [
        { type: 'hline', price: LV.boxHi, color: '#8E8E8E', dash: [22, 14], growDur: 0 },
        { type: 'hline', price: LV.boxLo, color: '#8E8E8E', dash: [22, 14], growDur: 0 },
      ],
    },
    {
      // 버튼을 얹을 좌표를 알아내려고 찍는 컷. 자홍/청록은 차트에 없는 색이라
      // 렌더된 PNG 에서 그 색만 찾으면 (bar, price) 의 화면 좌표가 나온다.
      // gap:0 이라 태그 꼭짓점이 정확히 그 캔들의 x 다.
      id: 'probe',
      name: '좌표 찍기 (버튼 위치용, 납품물 아님)',
      duration: 0.5,
      chart: { ...chartBase },
      layers: [
        { type: 'cmgArrow', bar: 53, price: LV.entry, dir: 'buy', label: '·',
          size: 24, gap: 0, popDur: 0, color: '#FF00FF', halo: false },
        { type: 'cmgArrow', bar: 87, price: LV.exit, dir: 'buy', label: '·',
          size: 24, gap: 0, popDur: 0, color: '#00FFFF', halo: false },
      ],
    },
  ],
};
