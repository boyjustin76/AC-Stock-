/**
 * 차트 컷씬용 캔들 생성기.
 *
 * 실시세를 쓰지 않고, "대본에 맞는 가격 이야기"를 만들어 내는 것이 목적이다.
 * seed 를 고정하면 몇 번을 렌더해도 같은 캔들이 나오므로,
 * 씬을 나눠 뽑아도 앞뒤 컷의 차트가 어긋나지 않는다.
 */

/** 재현 가능한 난수 (mulberry32) */
export function rng(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** 정규분포 근사 (Box-Muller) */
function gauss(rand) {
  let u = 0;
  let v = 0;
  while (u === 0) u = rand();
  while (v === 0) v = rand();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

/**
 * 구간(segment) 하나가 만들어 내는 "바 1개당 평균 가격 변화(drift)".
 *  - trend    : 한 방향으로 밀어붙이는 추세
 *  - range    : 박스권. 중심선으로 되돌아온다
 *  - breakout : 초반 눌림 후 강하게 이탈
 *  - pullback : 추세 중간 되돌림
 *  - spike    : 한두 개 바에서 급등/급락 (지표 발표 컷용)
 */
function segmentDrift(seg, i, n, rand) {
  const dir = seg.dir ?? 1;
  const p = n <= 1 ? 0 : i / (n - 1);
  switch (seg.type) {
    case 'trend':
      return dir * (seg.strength ?? 1);
    case 'range':
      return 0;
    case 'pullback':
      return -dir * (seg.strength ?? 0.6) * (1 - p * 0.5);
    case 'breakout': {
      const coil = seg.coil ?? 0.45; // 앞쪽 몇 %를 눌림 구간으로 쓸지
      if (p < coil) return -dir * (seg.strength ?? 1) * 0.15;
      const k = (p - coil) / (1 - coil);
      return dir * (seg.strength ?? 1) * (0.6 + k * 1.8);
    }
    case 'spike': {
      const at = seg.at ?? 0.25;
      const w = seg.width ?? 0.08;
      const bell = Math.exp(-((p - at) ** 2) / (2 * w * w));
      return dir * (seg.strength ?? 1) * bell * 8;
    }
    default:
      return dir * (seg.strength ?? 0) + gauss(rand) * 0;
  }
}

/**
 * 캔들 배열 생성.
 * @param {object} spec
 * @param {number} spec.seed
 * @param {number} spec.base     시작가
 * @param {number} spec.tick     최소 호가 (NQ = 0.25)
 * @param {number} spec.vol      바 1개의 기본 변동폭(포인트)
 * @param {Array}  spec.segments 가격 시나리오
 * @returns {{bars:Array, meta:object}}
 */
export function makeCandles(spec) {
  const {
    seed = 1,
    base = 24800,
    tick = 0.25,
    vol = 22,
    segments = [{ type: 'trend', dir: 1, bars: 80, strength: 0.4 }],
    startTime = Date.UTC(2026, 5, 12, 13, 30),
    barMinutes = 5,
  } = spec;

  const rand = rng(seed);
  const bars = [];
  let price = base;
  let center = base;
  let t = startTime;

  for (const seg of segments) {
    const n = seg.bars ?? 20;
    const segVol = (seg.vol ?? 1) * vol;
    center = price;
    for (let i = 0; i < n; i++) {
      const drift = segmentDrift(seg, i, n, rand) * segVol * 0.35;
      let noise = gauss(rand) * segVol * 0.5;

      // 박스권은 중심선으로 되돌리는 힘을 준다
      if (seg.type === 'range') {
        const halfWidth = (seg.width ?? 2.2) * segVol;
        noise += (center - price) * 0.25;
        if (Math.abs(price - center) > halfWidth) {
          noise += (center - price) * 0.45;
        }
      }

      const open = price;
      const close = open + drift + noise;
      const body = Math.abs(close - open);
      const wickUp = Math.abs(gauss(rand)) * segVol * 0.35 + body * 0.12;
      const wickDn = Math.abs(gauss(rand)) * segVol * 0.35 + body * 0.12;
      const high = Math.max(open, close) + wickUp;
      const low = Math.min(open, close) - wickDn;

      bars.push({
        i: bars.length,
        t,
        o: round(open, tick),
        h: round(high, tick),
        l: round(low, tick),
        c: round(close, tick),
        v: Math.round(400 + Math.abs(gauss(rand)) * 900 + body * 18),
      });

      price = close;
      t += barMinutes * 60 * 1000;
    }
  }

  return {
    bars,
    meta: {
      tick,
      barMinutes,
      first: bars[0],
      last: bars[bars.length - 1],
      high: Math.max(...bars.map((b) => b.h)),
      low: Math.min(...bars.map((b) => b.l)),
    },
  };
}

function round(v, tick) {
  return Math.round(v / tick) * tick;
}

/** 단순 이동평균. 값이 없는 구간은 null */
export function sma(bars, period) {
  const out = new Array(bars.length).fill(null);
  let sum = 0;
  for (let i = 0; i < bars.length; i++) {
    sum += bars[i].c;
    if (i >= period) sum -= bars[i - period].c;
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

/** 지수 이동평균 */
export function ema(bars, period) {
  const out = new Array(bars.length).fill(null);
  const k = 2 / (period + 1);
  let prev = null;
  for (let i = 0; i < bars.length; i++) {
    const c = bars[i].c;
    prev = prev === null ? c : c * k + prev * (1 - k);
    if (i >= period - 1) out[i] = prev;
  }
  return out;
}

/**
 * 캔들 하나가 "실시간으로 만들어지는" 모습.
 * p=0 이면 시가만, p=1 이면 완성된 캔들.
 */
export function formingBar(bar, p) {
  const e = Math.max(0, Math.min(1, p));
  const c = bar.o + (bar.c - bar.o) * e;
  // 고가/저가는 몸통이 자라는 것보다 조금 앞서 확장된다
  const w = Math.min(1, e * 1.25);
  const h = Math.max(c, bar.o) + (bar.h - Math.max(bar.o, bar.c)) * w;
  const l = Math.min(c, bar.o) - (Math.min(bar.o, bar.c) - bar.l) * w;
  return { ...bar, c, h: Math.max(h, c), l: Math.min(l, c), forming: e < 1 };
}
