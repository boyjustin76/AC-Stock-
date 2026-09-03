#!/usr/bin/env node
// 실제 시세 수급 — 야후 파이낸스 v8 chart API.
// 차12 재작(r13)부터 배경 차트는 합성이 아니라 실데이터다. 이 스크립트가 그 원본을 만든다.
//
//   node src/tools/fetch-yahoo.mjs --symbol "NQ=F" --interval 1m --range 5d --out data/nq/NQ_1m.json
//   node src/tools/fetch-yahoo.mjs --symbol "NQ=F" --interval 1m --range 5d --out data/nq/NQ_1m.json --merge
//
// * UA 헤더가 없으면 429 를 준다.
// * 야후 1m 은 최근 ~5일만 준다(소멸 데이터). --merge 로 기존 파일에 t 기준 중복 제거 병합해
//   풀을 누적할 수 있다. 받은 JSON 은 저장소에 커밋한다 — 파일이 곧 원본이다.
// * o/h/l/c 중 하나라도 null 인 봉(휴장 틱)은 버린다.
// * 세션 경계·프리마켓 갭(Δt > barMinutes×3)은 지우지 않고 리포트만 한다 —
//   차트 x 축은 인덱스 기반이라 갭이 그림을 깨지 않는다.

import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

const arg = (name, dflt) => {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--')
    ? process.argv[i + 1] : dflt;
};
const symbol = arg('symbol', 'NQ=F');
const interval = arg('interval', '1m');
const range = arg('range', '5d');
const out = arg('out', null);
const merge = process.argv.includes('--merge');
if (!out) { console.error('--out <파일> 이 필요하다'); process.exit(1); }

const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=${interval}&range=${range}`;
// Node fetch 는 프록시 env 를 기본으로 안 읽는다(NODE_USE_ENV_PROXY 필요). curl 이 확실하다.
const raw = execFileSync('curl', ['-sS', '-m', '60', '-H', 'User-Agent: Mozilla/5.0', url],
  { maxBuffer: 64 * 1024 * 1024 }).toString('utf8');
const json = JSON.parse(raw);
const res = json?.chart?.result?.[0];
if (!res) { console.error('응답에 result 가 없다:', raw.slice(0, 300)); process.exit(1); }

const ts = res.timestamp ?? [];
const q = res.indicators?.quote?.[0] ?? {};
let dropped = 0;
let bars = [];
for (let k = 0; k < ts.length; k++) {
  const o = q.open?.[k], h = q.high?.[k], l = q.low?.[k], c = q.close?.[k];
  if (o == null || h == null || l == null || c == null) { dropped++; continue; }
  bars.push({ t: ts[k] * 1000, o, h, l, c, v: q.volume?.[k] ?? 0 });
}

if (merge) {
  try {
    const prev = JSON.parse(readFileSync(out, 'utf8'));
    const seen = new Map(prev.bars.map((b) => [b.t, b]));
    for (const b of bars) seen.set(b.t, b);
    bars = [...seen.values()].sort((a, b) => a.t - b.t);
    console.log(`병합: 기존 ${prev.bars.length}봉 + 신규 → ${bars.length}봉`);
  } catch { console.log('병합 대상 없음 — 새로 만든다'); }
}

const barMinutes = { '1m': 1, '2m': 2, '5m': 5, '15m': 15, '30m': 30, '60m': 60, '1h': 60, '1d': 1440 }[interval] ?? 1;
const gaps = [];
for (let k = 1; k < bars.length; k++) {
  const dtMin = (bars[k].t - bars[k - 1].t) / 60000;
  if (dtMin > barMinutes * 3) gaps.push({ i: k, at: new Date(bars[k - 1].t).toISOString(), min: dtMin });
}

mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify({
  symbol, interval, barMinutes,
  exchange: res.meta?.exchangeName, currency: res.meta?.currency,
  fetchedAt: new Date().toISOString(), range,
  bars,
}, null, 0) + '\n');
console.log(`${out}: ${bars.length}봉 (null 드랍 ${dropped}) ` +
  `${new Date(bars[0]?.t).toISOString()} ~ ${new Date(bars.at(-1)?.t).toISOString()}`);
console.log(`갭(>${barMinutes * 3}분) ${gaps.length}곳` +
  (gaps.length ? ' — ' + gaps.slice(0, 8).map((g) => `#${g.i}(${Math.round(g.min)}분)`).join(' ') + (gaps.length > 8 ? ' …' : '') : ''));
