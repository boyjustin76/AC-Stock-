/** 컷씬 공통 룩앤필. 씬별로 theme 를 덮어써서 변주할 수 있다. */

export const DARK = {
  name: 'dark',
  bg: '#080B11',
  bgGradient: ['#0C111A', '#06080D'],
  grid: 'rgba(255,255,255,0.045)',
  gridStrong: 'rgba(255,255,255,0.09)',
  axisText: 'rgba(233,240,255,0.42)',
  text: '#E9F0FF',
  textDim: 'rgba(233,240,255,0.55)',

  // 해외 플랫폼 표준(상승 초록 / 하락 빨강).
  // 국내식(상승 빨강 / 하락 파랑)은 candleScheme: 'korea' 로 바꾼다.
  candleScheme: 'global',

  up: '#22C55E',
  upFill: '#22C55E',
  down: '#F2405D',
  downFill: '#F2405D',

  accent: '#4DA3FF',
  warn: '#FFB020',
  long: '#22C55E',
  short: '#F2405D',
  tp: '#22C55E',
  sl: '#F2405D',

  font: "Pretendard, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif",
  mono: "'JetBrains Mono', 'SF Mono', Menlo, monospace",
};

export const KOREA_SCHEME = {
  candleScheme: 'korea',
  up: '#FF3B4E',
  upFill: '#FF3B4E',
  down: '#2E7BFF',
  downFill: '#2E7BFF',
  long: '#FF3B4E',
  short: '#2E7BFF',
  tp: '#FF3B4E',
  sl: '#2E7BFF',
};


/**
 * 차트명가 채널 테마.
 * 레퍼런스 영상에서 실측한 값 — 자세한 근거는 brand/STYLE.md 참고.
 */
export const CHARTMYEONGGA = {
  name: 'chartmyeongga',
  light: true,
  flat: true, // 그라데이션·비네트 없이 단색 배경

  bg: '#FFFFFF',
  bgGradient: null,
  grid: 'rgba(0,0,0,0.05)',
  gridStrong: 'rgba(0,0,0,0.12)',
  axisText: 'rgba(0,0,0,0.38)',
  text: '#111111',
  textDim: 'rgba(0,0,0,0.5)',

  candleScheme: 'chartmyeongga',
  up: '#0B8C7F', // 딥 틸
  upFill: '#0B8C7F',
  down: '#E80001', // 선명한 빨강
  downFill: '#E80001',

  ma: '#F38808', // 이동평균선 주황

  accent: '#E90054', // 종목·타임프레임 배지 핑크레드
  warn: '#F38808',
  muted: '#8E8E8E', // 소제목 배지 회색

  buy: '#E80001', // 매수 라벨 (국내식 — 매수 빨강)
  sell: '#0200F3', // 매도 라벨 파랑
  long: '#E80001',
  short: '#0200F3',

  tp: '#14FF36', // 익절 형광 초록
  tpFill: '#C5FFC4',
  sl: '#9F0000', // 손절 진한 빨강
  slFill: '#F9BAC1',

  // 라벨 글씨는 흰색 + 검정 외곽선이 이 채널의 특징
  labelText: '#FFFFFF',
  labelStroke: '#000000',

  font: "'Gmarket Sans', 'S-Core Dream', Pretendard, sans-serif",
  fontBody: "'S-Core Dream', Pretendard, sans-serif",
  // 매수·매도·익절·손절 버튼과 배지의 글씨.
  // 브랜드 버튼 원본(brand/ui/*.png)과 #7 썸네일의 '익절' 텍스트 레이어가
  // 둘 다 에스코어 드림 5 Medium 이다. 타이틀(Gmarket Sans Bold)과 다른 폰트다.
  fontTag: "'S-Core Dream', Pretendard, sans-serif",
  fontTagWeight: 500,
  mono: "'JetBrains Mono', 'SF Mono', Menlo, monospace",
};

const PRESETS = { dark: DARK, chartmyeongga: CHARTMYEONGGA };

export function usePreset(name) {
  return PRESETS[name] ?? DARK;
}

export function makeTheme(override = {}) {
  const base = { ...usePreset(override.preset) };
  if (override.candleScheme === 'korea') Object.assign(base, KOREA_SCHEME);
  return { ...base, ...override };
}
