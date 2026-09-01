#!/usr/bin/env node
/**
 * 실측: **클립을 시간축에서 밀면 그림이 몇 픽셀 어긋나는가.**
 *
 *   node src/tools/exp-drift.mjs
 *
 * 레이어를 알파 클립으로 갈라 프리미어 트랙에 쌓으면 싱크를 손으로 밀 수 있다.
 * 그런데 주석은 봉·가격에 붙어 있고 차트는 컷 안에서 움직인다(reveal·zoom 키프레임).
 * 클립을 밀면 주석은 **밀기 전 시각의 위치**로 그려진 픽셀인 채 옮겨지므로,
 * 그 사이 차트가 움직인 만큼 어긋난다. 그 양을 잰다.
 *
 * 기준점은 컷② 주석이 실제로 붙어 있는 곳 — 익절선(bar 53, target)과 진입선(bar 42, entry).
 */
import { makeCandles } from '../market/candles.js';
import { Chart } from '../render/chart.js';
import { makeTheme } from '../render/theme.js';
import { Ease, lerp, clamp } from '../render/anim.js';
import project from '../../scenes/sl-11-4.scenes.js';

/* engine.js 의 keyframe() 과 같은 식 — 그쪽은 export 하지 않는다 */
function keyframe(list, t, fallback) {
  if (list == null) return fallback;
  if (typeof list === 'number') return list;
  if (!list.length) return fallback;
  if (t <= list[0].t) return list[0].v;
  for (let i = 1; i < list.length; i++) {
    if (t <= list[i].t) {
      const a = list[i - 1]; const b = list[i];
      const p = b.t === a.t ? 1 : (t - a.t) / (b.t - a.t);
      const e = typeof b.ease === 'function' ? b.ease : (Ease[b.ease ?? 'inOutCubic'] ?? Ease.inOutCubic);
      return lerp(a.v, b.v, e(clamp(p)));
    }
  }
  return list[list.length - 1].v;
}

const scene = project.scenes.find((s) => s.id === 'cut2-early-exit');
const c = scene.chart;
const { bars } = makeCandles({ ...(project.market ?? {}), ...(scene.market ?? {}) });
const chart = new Chart({
  ctx: null, width: project.width, height: project.height, bars,
  theme: makeTheme({ ...(project.theme ?? {}), ...(scene.theme ?? {}) }),
  layout: c.layout,
  view: { visibleBars: c.visibleBars ?? 62, pricePad: c.pricePad ?? 0.16, include: c.include ?? null, ma: c.ma, rsi: c.rsi },
});

const LV = { entry: 23795, target: 23795 + (23795 - 23665) * 2 };
/** t 초에서 기준점들의 픽셀 좌표 */
function at(t) {
  const s = chart.makeScale(chart.viewport(
    clamp(keyframe(c.reveal, t, bars.length), 0.001, bars.length),
    keyframe(c.zoom, t, 1),
    keyframe(c.priceOffset, t, 0),
  ));
  return { ik: [s.x(53), s.y(LV.target)], jin: [s.x(42), s.y(LV.entry)] };
}
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const fps = project.fps;

console.log('\n  컷② — 클립을 미뤘을 때 그림이 어긋나는 양 (px)\n');
console.log('   시각      1프레임    3프레임(0.1s)   15프레임(0.5s)   구간');
const marks = [
  [0.5, '정지 (reveal 43 고정)'], [1.5, '느린 전진 43→50'], [2.5, '느린 전진'],
  [3.3, '익절 화살표 등장'], [4.0, '빠른 전진 50→63'], [4.8, '전진 끝'],
  [5.0, '정지 (reveal 63)'], [5.4, '스우프 시작'], [5.6, '스우프 한복판'],
];
for (const [t, note] of marks) {
  const a = at(t);
  const d = (n) => {
    const b = at(t + n / fps);
    return Math.max(dist(a.ik, b.ik), dist(a.jin, b.jin));
  };
  const f = (v) => v.toFixed(1).padStart(6);
  console.log(`   ${t.toFixed(1)}s   ${f(d(1))}     ${f(d(3))}        ${f(d(15))}        ${note}`);
}
console.log('\n  * 두 기준점(익절선 bar53·진입선 bar42) 중 더 많이 움직인 쪽을 적었다.');
console.log('  * 어긋남이 3px 안쪽이면 눈에 안 띈다. 10px 넘으면 확실히 보인다.\n');
