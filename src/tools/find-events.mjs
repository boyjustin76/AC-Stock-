#!/usr/bin/env node
/**
 * 씬 설정의 캔들에서 차12 본편에 필요한 이벤트를 전부 찾아 준다.
 * find-cross(교차 전용)의 확장판 — RSI 기준선 교차까지 본다.
 *
 *   node src/tools/find-events.mjs <scenes 파일> [--scene id] [--levels 55,45] [--bars 12,34]
 *
 * 출력:
 *   - MA 골든/데드크로스 (find-cross 와 동일)
 *   - MA 배열 전환 (fast>slow ↔ fast<slow 구간)
 *   - RSI 가 지정 레벨을 위/아래로 지나는 바 + 그 캔들이 양봉인지 음봉인지
 *   - --bars: 바별 o/h/l/c · ma · rsi 덤프
 */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { makeCandles, sma, ema, wilderRsi } from '../market/candles.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

const rel = process.argv[2];
if (!rel) {
  console.error('사용법: node src/tools/find-events.mjs <scenes 파일> [--scene id] [--levels 55,45] [--bars 1,2]');
  process.exit(2);
}
const arg = (name) => {
  const i = process.argv.indexOf(name);
  return i > 0 ? process.argv[i + 1] : null;
};
const sceneId = arg('--scene');
const levels = (arg('--levels') ?? '55,45').split(',').map(Number);
const showBars = (arg('--bars') ?? '').split(',').filter(Boolean).map(Number);

const project = (await import(pathToFileURL(path.join(ROOT, rel)).href)).default;
const scene = sceneId ? project.scenes.find((s) => s.id === sceneId) : project.scenes[0];
if (!scene) throw new Error(`씬 없음: ${sceneId}`);
const market = { ...(project.market ?? {}), ...(scene.market ?? {}) };
const { bars } = makeCandles(market);

const maSpec = scene.chart?.ma ?? [];
const series = maSpec.map((m) => ({ ...m, v: m.type === 'ema' ? ema(bars, m.period) : sma(bars, m.period) }));
const rsiPeriod = scene.chart?.rsi?.period ?? 10;
const rsi = wilderRsi(bars, rsiPeriod).values;

console.log(`캔들 ${bars.length}개 · ${series.map((s) => s.type + s.period).join(' / ') || 'MA 없음'} · RSI(${rsiPeriod})`);
const lo = Math.min(...bars.map((b) => b.l));
const hi = Math.max(...bars.map((b) => b.h));
console.log(`가격 ${lo.toFixed(1)} ~ ${hi.toFixed(1)}\n`);

if (series.length >= 2) {
  const [fast, slow] = series;
  let state = null;
  console.log('── MA 교차·배열');
  for (let i = 1; i < bars.length; i++) {
    const a = fast.v[i];
    const b = slow.v[i];
    if (a == null || b == null) continue;
    const now = a > b ? '정배열' : '역배열';
    if (state === null) {
      console.log(`  bar=${i} 부터 ${now}`);
    } else if (state !== now) {
      const kind = now === '정배열' ? '골든' : '데드';
      console.log(`  ${kind}크로스 bar=${i}  교차가≈${b.toFixed(1)}  종가=${bars[i].c.toFixed(1)}  → ${now}`);
    }
    state = now;
  }
}

console.log('\n── RSI 레벨 교차');
for (const L of levels) {
  for (let i = 1; i < bars.length; i++) {
    const p = rsi[i - 1];
    const c = rsi[i];
    if (p == null || c == null) continue;
    if (p < L && c >= L) {
      const bull = bars[i].c >= bars[i].o;
      console.log(`  RSI ${L} 상향돌파 bar=${i}  rsi=${c.toFixed(1)}  캔들=${bull ? '양봉' : '음봉'}  종가=${bars[i].c.toFixed(1)}`);
    }
    if (p > L && c <= L) {
      const bull = bars[i].c >= bars[i].o;
      console.log(`  RSI ${L} 하향이탈 bar=${i}  rsi=${c.toFixed(1)}  캔들=${bull ? '양봉' : '음봉'}  종가=${bars[i].c.toFixed(1)}`);
    }
  }
}

// RSI 70 위 유지 구간 (문제제시 ② 용)
console.log('\n── RSI 70+ 유지 구간');
let runStart = null;
for (let i = 1; i <= bars.length; i++) {
  const v = rsi[i];
  if (v != null && v >= 70) {
    if (runStart === null) runStart = i;
  } else if (runStart !== null) {
    if (i - runStart >= 3) console.log(`  bar ${runStart}~${i - 1} (${i - runStart}봉)  최대 rsi=${Math.max(...rsi.slice(runStart, i)).toFixed(1)}`);
    runStart = null;
  }
}

if (showBars.length) {
  console.log('\n── 지정한 바');
  for (const i of showBars) {
    const b = bars[i];
    if (!b) { console.log(`  bar=${i} 없음`); continue; }
    console.log(
      `  bar=${i}  o=${b.o.toFixed(1)} h=${b.h.toFixed(1)} l=${b.l.toFixed(1)} c=${b.c.toFixed(1)}` +
        series.map((s) => `  ${s.type}${s.period}=${s.v[i]?.toFixed(1) ?? '-'}`).join('') +
        `  rsi=${rsi[i]?.toFixed(1) ?? '-'}`
    );
  }
}
