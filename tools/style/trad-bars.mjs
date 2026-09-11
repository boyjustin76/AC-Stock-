/**
 * newch-trad 씬용 봉 데이터: seed 11 합성 시장 앞에 워밍업 60봉을 붙여 이평선이 첫 봉부터 그려지게 한다.
 * 워밍업은 bar0 시가에서 거꾸로 걷는 완만한 흐름 — 화면에 보이는 봉(60~)의 모양은 원래 seed 11 과 동일하다.
 *   node tools/style/trad-bars.mjs  → data/synth/newch-trad.json
 */
import { makeCandles, rng } from '../../src/market/candles.js';
import { writeFileSync } from 'node:fs';

const spec = {
  seed: 11, base: 23400, tick: 0.25, vol: 58, barMinutes: 1440,
  startTime: Date.UTC(2026, 0, 5, 0, 0),
  segments: [
    { type: 'trend', dir: 1, bars: 34, strength: 0.52 },
    { type: 'pullback', dir: 1, bars: 9, strength: 1.15 },
    { type: 'trend', dir: 1, bars: 52, strength: 0.82 },
  ],
};
const WARM = 60;
const { bars } = makeCandles(spec);
const rand = rng(1103);
const gauss = () => { let u = 0, v = 0; while (!u) u = rand(); while (!v) v = rand(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
const r = (v) => Math.round(v / spec.tick) * spec.tick;
const day = 1440 * 60 * 1000;
const warm = [];
let close = bars[0].o;                // bar0 시가로 끝나게 거꾸로 걷는다
for (let k = 0; k < WARM; k++) {
  const drift = -0.18 * spec.vol * 0.35;                 // 과거로 갈수록 조금 낮게 (완만한 상승 추세 위에 놓인 시작점)
  const open = close - (drift + gauss() * spec.vol * 0.32);
  const body = Math.abs(close - open);
  const h = Math.max(open, close) + Math.abs(gauss()) * spec.vol * 0.3 + body * 0.1;
  const l = Math.min(open, close) - Math.abs(gauss()) * spec.vol * 0.3 + body * 0.1;
  warm.unshift({ o: r(open), h: r(h), l: r(l), c: r(close), v: 600 + Math.round(Math.abs(gauss()) * 500) });
  close = open;
}
const out = [];
warm.forEach((b, i) => out.push({ i, t: bars[0].t - (WARM - i) * day, ...b }));
bars.forEach((b) => out.push({ ...b, i: out.length }));
writeFileSync('data/synth/newch-trad.json', JSON.stringify({ symbol: 'SYNTH-seed11+warm60', interval: '1d', barMinutes: 1440, warm: WARM, bars: out }));
console.log('bars', out.length, 'warm', WARM, 'first visible idx', WARM + 6, 'entry-bar(44)→', WARM + 44);
