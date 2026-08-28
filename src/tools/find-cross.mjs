#!/usr/bin/env node
/**
 * 씬 설정의 캔들에서 이동평균 교차(골든/데드)를 찾아 준다.
 *
 * 라벨을 붙일 바 번호를 눈대중으로 찍으면 렌더할 때마다 어긋난다.
 * seed 가 고정이라 캔들은 재현되므로, 같은 생성기로 미리 계산해서 정확한 바를 쓴다 (§3-10).
 *
 *   node src/tools/find-cross.mjs scenes/cmg12-cross.scenes.js
 *   node src/tools/find-cross.mjs scenes/cmg12-cross.scenes.js --bars 30,42
 */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { makeCandles, sma, ema } from '../market/candles.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

const rel = process.argv[2];
if (!rel) {
  console.error('사용법: node src/tools/find-cross.mjs <scenes 파일> [--bars 12,34]');
  process.exit(2);
}
const showBarsArg = process.argv.indexOf('--bars');
const showBars = showBarsArg > 0 ? process.argv[showBarsArg + 1].split(',').map(Number) : [];

const project = (await import(pathToFileURL(path.join(ROOT, rel)).href)).default;
const { bars, meta } = makeCandles(project.market);   // makeCandles 는 {bars, meta} 를 준다

// 첫 씬의 ma 설정을 기준으로 삼는다 (컷마다 같은 차트를 이어 보여 주는 구성 전제)
const maSpec = project.scenes?.[0]?.chart?.ma ?? [];
if (maSpec.length < 2) {
  console.error('이동평균이 2개 이상이어야 교차를 찾는다. 지금:', maSpec.length);
  process.exit(2);
}
const series = maSpec.map((m) => ({
  ...m,
  v: m.type === 'ema' ? ema(bars, m.period) : sma(bars, m.period),
}));
const [fast, slow] = series;

console.log(`캔들 ${bars.length}개 · ${fast.type}${fast.period} vs ${slow.type}${slow.period}`);
const lo = Math.min(...bars.map((b) => b.l));
const hi = Math.max(...bars.map((b) => b.h));
console.log(`가격 ${lo.toFixed(1)} ~ ${hi.toFixed(1)}\n`);

const crosses = [];
for (let i = 1; i < bars.length; i++) {
  const [a0, b0, a1, b1] = [fast.v[i - 1], slow.v[i - 1], fast.v[i], slow.v[i]];
  if ([a0, b0, a1, b1].some((x) => x == null || Number.isNaN(x))) continue;
  const d0 = a0 - b0;
  const d1 = a1 - b1;
  if (d0 <= 0 && d1 > 0) crosses.push({ i, kind: '골든', price: slow.v[i] });
  if (d0 >= 0 && d1 < 0) crosses.push({ i, kind: '데드', price: slow.v[i] });
}

if (!crosses.length) console.log('교차 없음');
for (const c of crosses) {
  const after = bars.slice(c.i, c.i + 10).map((b) => b.c);
  const move = after.length > 1 ? ((after[after.length - 1] - after[0]) / after[0]) * 100 : 0;
  console.log(
    `${c.kind}크로스  bar=${c.i}  교차가=${c.price.toFixed(1)}  ` +
      `종가=${bars[c.i].c.toFixed(1)}  이후 10봉 ${move >= 0 ? '+' : ''}${move.toFixed(2)}%`
  );
}

if (showBars.length) {
  console.log('\n지정한 바:');
  for (const i of showBars) {
    const b = bars[i];
    if (!b) { console.log(`  bar=${i} 없음`); continue; }
    console.log(
      `  bar=${i}  o=${b.o.toFixed(1)} h=${b.h.toFixed(1)} l=${b.l.toFixed(1)} c=${b.c.toFixed(1)}` +
        series.map((s) => `  ${s.type}${s.period}=${s.v[i]?.toFixed(1) ?? '-'}`).join('')
    );
  }
}
