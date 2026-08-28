/* ── 검토 ──
 * 검토내용: 이징·cue 로직 순수 함수라 결정성 문제 없음. 성능 무관. 수정 없음.
 * 타임코드: 2026-08-27 19:42 KST
 * 검토자: Fable 5 Max
 */
/** 타임라인 / 이징 유틸. 모든 애니메이션은 초(second) 단위 절대시각으로 계산한다. */

export const clamp = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v);
export const lerp = (a, b, p) => a + (b - a) * p;

export const Ease = {
  linear: (p) => p,
  inQuad: (p) => p * p,
  outQuad: (p) => 1 - (1 - p) * (1 - p),
  inOutQuad: (p) => (p < 0.5 ? 2 * p * p : 1 - (-2 * p + 2) ** 2 / 2),
  outCubic: (p) => 1 - (1 - p) ** 3,
  inOutCubic: (p) => (p < 0.5 ? 4 * p * p * p : 1 - (-2 * p + 2) ** 3 / 2),
  outQuart: (p) => 1 - (1 - p) ** 4,
  outExpo: (p) => (p >= 1 ? 1 : 1 - 2 ** (-10 * p)),
  inOutExpo: (p) =>
    p <= 0 ? 0 : p >= 1 ? 1 : p < 0.5 ? 2 ** (20 * p - 10) / 2 : (2 - 2 ** (-20 * p + 10)) / 2,
  outBack: (p) => 1 + 2.2 * (p - 1) ** 3 + 1.2 * (p - 1) ** 2,
  outElastic: (p) =>
    p === 0 || p === 1 ? p : 2 ** (-9 * p) * Math.sin((p * 10 - 0.75) * ((2 * Math.PI) / 3)) + 1,
};

/** [from,to] 구간을 0..1 로 정규화하고 이징 적용 */
export function span(t, from, to, ease = Ease.outCubic) {
  if (to <= from) return t >= to ? 1 : 0;
  return ease(clamp((t - from) / (to - from)));
}

/**
 * 등장/퇴장을 한 번에 처리한다.
 * @param {number} t   현재 시각(초)
 * @param {object} cue { in:[start,dur], out:[start,dur] }
 * @returns {{v:number, phase:'before'|'in'|'hold'|'out'|'after'}}
 *   v = 0(안 보임) ~ 1(완전히 보임)
 */
export function cue(t, c = {}, opts = {}) {
  const inEase = opts.inEase ?? Ease.outCubic;
  const outEase = opts.outEase ?? Ease.inOutQuad;
  // in 을 생략하면 "처음부터 이미 떠 있는 것"으로 본다.
  // 컷을 나눠 렌더할 때 이어지는 요소가 컷 경계에서 한 프레임 사라지는 걸 막는다.
  if (!c.in) {
    if (!c.out) return { v: 1, phase: 'hold' };
    const [os0, od0] = c.out;
    const exit0 = 1 - span(t, os0, os0 + od0, outEase);
    return { v: exit0, phase: t >= os0 + od0 ? 'after' : t >= os0 ? 'out' : 'hold' };
  }
  const [is, id] = c.in;
  const enter = span(t, is, is + id, inEase);
  if (!c.out) return { v: enter, phase: enter >= 1 ? 'hold' : t < is ? 'before' : 'in' };
  const [os, od] = c.out;
  const exit = 1 - span(t, os, os + od, outEase);
  const v = Math.min(enter, exit);
  let phase = 'hold';
  if (t < is) phase = 'before';
  else if (t < is + id) phase = 'in';
  else if (t >= os + od) phase = 'after';
  else if (t >= os) phase = 'out';
  return { v, phase };
}

/** 숫자 카운트업. 옵션으로 소수점/천단위 구분 */
export function fmtNum(v, decimals = 2, thousands = true) {
  const fixed = Number(v).toFixed(decimals);
  if (!thousands) return fixed;
  const [a, b] = fixed.split('.');
  return a.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (b ? '.' + b : '');
}

export function fmtSigned(v, decimals = 2) {
  const s = v > 0 ? '+' : v < 0 ? '-' : '';
  return s + fmtNum(Math.abs(v), decimals);
}
