/**
 * 실데이터 로더 (차12 r13~).
 * data/nq/*.json (src/tools/fetch-yahoo.mjs 산출물)을 씬 파일에서 동기 로드해
 * makeCandles() 의 spec.bars 로 넣을 슬라이스를 만든다.
 *
 *   import { loadBars, sliceBars } from '../src/market/loadBars.js';
 *   const m1 = loadBars('data/nq/NQ_1m.json');
 *   const slice = sliceBars(m1.bars, { start: 3200, count: 260 });
 *   // 씬: market: { bars: slice, tick: 0.25, barMinutes: 1 }
 *
 * 규칙: 표시 시작 바 앞에 워밍업 봉을 넉넉히(기본 120+) 포함해야
 * SMA34·Wilder RSI(10) 가 슬라이스 안에서 수렴한다. 화면에는 reveal/visibleBars 가
 * 워밍업 뒤쪽만 보여 주므로 워밍업은 보이지 않는다.
 */
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');

/** 저장소 루트 기준 상대경로로 실데이터 JSON 을 읽는다. */
export function loadBars(relPath) {
  const j = JSON.parse(readFileSync(resolve(ROOT, relPath), 'utf8'));
  if (!Array.isArray(j.bars)) throw new Error(`${relPath}: bars 배열이 없다`);
  return j; // { symbol, interval, barMinutes, bars: [{t,o,h,l,c,v}] }
}

/**
 * 구간을 잘라 i 를 0부터 재부여한다. t/o/h/l/c/v 는 그대로.
 * warmup 만큼 start 앞을 추가로 포함한다 (기본 0 — 호출부가 start 로 직접 관리).
 */
export function sliceBars(bars, { start, count, warmup = 0 }) {
  const s = Math.max(0, start - warmup);
  const e = Math.min(bars.length, start + count);
  if (e - s < 2) throw new Error(`sliceBars: 구간이 비었다 (start ${start}, count ${count})`);
  return bars.slice(s, e).map((b, i) => ({ ...b, i }));
}
