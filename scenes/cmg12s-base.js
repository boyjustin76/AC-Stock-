/**
 * 차트명가 #12 — r13 전면 재작 공통 베이스 (정적·실데이터·화이트리스트 문법)
 *
 * 근거: brand/FX-WHITELIST.md (최종본 #1~#10 전수 실측, 2026-09-03).
 *  - 차트는 컷 안에서 1장 고정(reveal 숫자). 진행은 chart.phases 30f 디졸브.
 *  - 배색: 캔들은 차트명가 프리셋(상승 청록 #0B8C7F/하락 빨강 #E80001 — r13.1 정정,
 *    이정찬: "#2 빨강/파랑은 예외, 기준은 프리셋"). 이평선은 #2 상속(10일선 빨강,
 *    34일선 주황), RSI 파랑 + 파랑 프레임(#9 문법) + 55/45 회색 점선(#2 문법).
 *  - 카메라 모션·줌·팬·리빌 금지 (prproj 전수: 느린 줌·불투명도 kf 부재 증거).
 *  - 등장: 크로스페이드(30f=0.5s@59.94 계열), 팝 4f(0.13s), 손그림 드로우온만.
 *
 * 데이터: data/nq/*.json — 실제 NQ 시세 (src/tools/fetch-yahoo.mjs, 2026-09-03 수급).
 * 슬라이스 근거: src/tools/scan-nq.mjs 실행 결과 (2026-09-03, 커밋 90cb360 시점).
 *  - introD1  : 1d, 전역 640~790. 데드크로스 727(2024-07-26, 이후 +2.25%)과
 *               가짜 골든크로스 747(2024-08-23, 이후 -6.73%)이 한 창에 있다.
 *  - pullbackM1: 1m, 진입신호 전역 1282 (2026-08-31 19:33), 손절 6pt·순행 98pt(1:2 초과).
 *  - chopM1   : 1m, 전역 1440~1560 (2026-08-31 23시대), 교차 17회 횡보.
 *  - blindM1  : 1m, 전역 1813~1841 (2026-09-01 05:34), RSI 70+ 29봉 유지 상승.
 *  - sellM5   : 5m, 진입신호 전역 5794 (2026-09-01 11:45), 순행 124pt.
 */
import { loadBars, sliceBars } from '../src/market/loadBars.js';

export const FPS = 60000 / 1001;

const d1 = await loadBars('data/nq/NQ_1d.json');
const m1 = await loadBars('data/nq/NQ_1m.json');
const m5 = await loadBars('data/nq/NQ_5m.json');

/* 전역 인덱스 → 슬라이스 로컬 인덱스: local = global - start */
export const SLICE = {
  introD1: { bars: sliceBars(d1.bars, { start: 640, count: 150 }), start: 640, barMinutes: 1440 },
  pullbackM1: { bars: sliceBars(m1.bars, { start: 1083, count: 300 }), start: 1083, barMinutes: 1 },
  chopM1: { bars: sliceBars(m1.bars, { start: 1300, count: 300 }), start: 1300, barMinutes: 1 },
  blindM1: { bars: sliceBars(m1.bars, { start: 1653, count: 260 }), start: 1653, barMinutes: 1 },
  sellM5: { bars: sliceBars(m5.bars, { start: 5595, count: 300 }), start: 5595, barMinutes: 5 },
};
export const L = (slice, globalIdx) => globalIdx - slice.start; // 전역→로컬

export const mkMarket = (s) => ({ bars: s.bars, tick: 0.25, barMinutes: s.barMinutes });

/* 실측 배색 (FX-WHITELIST §3·§4, 차명#2 픽셀 실측) */
export const COLOR = {
  ma10: '#D8181B', // 10일선 — 진빨강 (캔들 빨강보다 살짝 깊게)
  ma34: '#F09C0C', // 34일선 — 주황
  rsi: '#1E78C8', // RSI 라인 파랑
  rsiFrame: '#2743C9', // RSI 패널 프레임 (차명#9 파랑 프레임 문법)
  badge: '#F50C54', // 핑크 알약 배지 (실측 #FC0C54 군집)
  pencil: '#C0272D', // 손그림 색연필 빨강
  line: '#111111', // 박스권·기준선 검정 (팀장 규칙 ②)
  tp: '#14FF36', tpFill: '#BAFDC0',
  sl: '#9F0000', slFill: '#FEBABA',
  buy: '#E80001', sell: '#0200F3',
};

/* 등장 규약 — 프레임 실측 (화이트리스트 §2 + 영상 프레임 단위 재실측 2026-09-03):
   최종본에서 텍스트·라벨 등장은 1~4f 즉시/팝이 지배(YDIF 런 분석: 1-2f 최다, 3-5f 차다).
   30f(1.0s) 디졸브는 컷 전환·차트 스틸 교체·존/밴드용이다. */
export const IN = {
  fade: 0.13, // 텍스트·라벨 등장 = 4f 팝/페이드 (실측 지배 문법)
  pop: 0.13, // 균일 팝 4f (prproj ①③)
  bar: 0.13, // 강조바 펴기 4f (prproj ①)
  draw: 0.5, // 손그림 드로우온 10~18f (YDIF 런 실측)
  dissolve: 1.0, // 교차 디졸브 30f@29.97 (prproj 최빈값) — phases·존 교체용
};

export const mt5ChartBase = {
  visibleBars: 96,
  pricePad: 0.14,
  showGrid: false, // 실영상 문법: 축·그리드 없음 풀블리드 (FX-WHITELIST §3)
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 216, padBottom: 162, rightGap: 3 },
  ma: [
    { type: 'sma', period: 10, width: 7, color: COLOR.ma10 },
    { type: 'sma', period: 34, width: 7, color: COLOR.ma34 },
  ],
  rsi: {
    period: 10, height: 0.24, gap: 24, baseline: null, width: 3, color: COLOR.rsi,
    levels: [
      { v: 55, label: '55', dash: [6, 6], color: 'rgba(0,0,0,0.5)', width: 1.5 },
      { v: 45, label: '45', dash: [6, 6], color: 'rgba(0,0,0,0.5)', width: 1.5 },
    ],
  },
};

/* RSI 패널 라벨 칩 (차명#9 좌상단 'RSI' 칩).
   패널 y 는 레이아웃에서 상수: 216 + (702-168-24) = 726 부근. */
export const rsiChip = (extra = {}) => ({
  type: 'cmgBadge', text: 'RSI', x: 84, y: 750, size: 32, color: COLOR.rsiFrame, border: false, ...extra,
});

/* 프로젝트 공통 머리 */
export const projectHead = (title) => ({
  title,
  width: 1920,
  height: 1080,
  fps: FPS,
  fpsExpr: '60000/1001',
  theme: { preset: 'cmgMt5', panelBorder: COLOR.rsiFrame },
});
