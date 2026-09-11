/**
 * 실데이터 로더 (차12 r13~).
 * data/nq/*.json (src/tools/fetch-yahoo.mjs 산출물)을 씬 파일에서 로드해
 * makeCandles() 의 spec.bars 로 넣을 슬라이스를 만든다.
 *
 * 씬 파일은 두 곳에서 실행된다는 것을 잊지 말 것:
 *  - 렌더 시: Chromium 페이지 (server.mjs 가 저장소 루트를 서빙) → fetch
 *  - 도구에서: Node (find-events.mjs 등) → node:fs
 * 그래서 loadBars 는 async 다. 씬 파일에서는 톱레벨 await 로 쓴다:
 *
 *   import { loadBars, sliceBars } from '../src/market/loadBars.js';
 *   const m1 = await loadBars('data/nq/NQ_1m.json');
 *   const slice = sliceBars(m1.bars, { start: 3200, count: 260 });
 *   // 씬: market: { bars: slice, tick: 0.25, barMinutes: 1 }
 *
 * 규칙: 표시 시작 바 앞에 워밍업 봉을 넉넉히(120+) 포함해야 SMA34·RSI(10)가
 * 슬라이스 안에서 수렴한다. 화면에는 reveal/visibleBars 가 뒤쪽만 보여 준다.
 */

/** 저장소 루트 기준 상대경로로 실데이터 JSON 을 읽는다 (브라우저/Node 겸용). */
export async function loadBars(relPath) {
  let j;
  if (typeof window !== 'undefined' && typeof fetch === 'function' && typeof process === 'undefined') {
    const r = await fetch('/' + relPath.replace(/^\/+/, ''));
    if (!r.ok) throw new Error(`${relPath}: HTTP ${r.status}`);
    j = await r.json();
  } else {
    const { readFileSync } = await import('node:fs');
    const { resolve, dirname } = await import('node:path');
    const { fileURLToPath } = await import('node:url');
    const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
    j = JSON.parse(readFileSync(resolve(ROOT, relPath), 'utf8'));
  }
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
