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

export function makeTheme(override = {}) {
  const base = { ...DARK };
  if (override.candleScheme === 'korea') Object.assign(base, KOREA_SCHEME);
  return { ...base, ...override };
}
