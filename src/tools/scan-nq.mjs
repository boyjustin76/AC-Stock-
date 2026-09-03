#!/usr/bin/env node
// 실데이터 시나리오 스캐너 (차12 r13).
// data/nq/*.json 에서 대본이 요구하는 국면(가짜 골든크로스, 횡보 연속 교차, RSI 과열 지속,
// 정배열 눌림목 재돌파, 역배열 반등 재이탈)을 찾아 슬라이스 후보를 나열한다.
// 결과 구간은 scenes/cmg12s-base.js 에 상수로 박제한다 — 렌더는 스캐너를 다시 돌리지 않는다.
//
//   node src/tools/scan-nq.mjs data/nq/NQ_1d.json --pattern fakeGolden
//   node src/tools/scan-nq.mjs data/nq/NQ_1m.json --pattern pullback --top 8
//
// 지표는 렌더러와 같은 구현(sma/wilderRsi, RSI 기간 10 · 55/45)을 쓴다.

import { readFileSync } from 'node:fs';
import { sma, wilderRsi } from '../market/candles.js';

const file = process.argv[2];
const arg = (name, dflt) => {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : dflt;
};
const pattern = arg('pattern', null);
const top = Number(arg('top', 6));
if (!file || !pattern) { console.error('사용법: scan-nq.mjs <data.json> --pattern <이름>'); process.exit(1); }

const data = JSON.parse(readFileSync(file, 'utf8'));
const bars = data.bars.map((b, i) => ({ ...b, i }));
const bm = data.barMinutes ?? 1;
const s10 = sma(bars, 10); // 배열 반환 (candles.js)
const s34 = sma(bars, 34);
const rsi = wilderRsi(bars, 10).values;

// 갭 지도: bars[i] 와 이전 봉 사이가 봉 간격의 3배 초과면 갭
const gapAt = new Array(bars.length).fill(false);
for (let i = 1; i < bars.length; i++) {
  if ((bars[i].t - bars[i - 1].t) / 60000 > bm * 3) gapAt[i] = true;
}
const hasGap = (a, b) => { for (let i = Math.max(1, a); i <= Math.min(b, bars.length - 1); i++) if (gapAt[i]) return true; return false; };

const crossUp = (i) => s10[i - 1] != null && s34[i - 1] != null && s10[i - 1] <= s34[i - 1] && s10[i] > s34[i];
const crossDn = (i) => s10[i - 1] != null && s34[i - 1] != null && s10[i - 1] >= s34[i - 1] && s10[i] < s34[i];

const found = [];
const push = (o) => found.push(o);

if (pattern === 'fakeGolden' || pattern === 'fakeDead') {
  const up = pattern === 'fakeGolden';
  for (let i = 40; i < bars.length - 20; i++) {
    if (!(up ? crossUp(i) : crossDn(i))) continue;
    const c0 = bars[i].c;
    let ext = c0; let extIdx = i;
    for (let j = i + 1; j <= Math.min(i + 15, bars.length - 1); j++) {
      const v = bars[j].c;
      if (up ? v < ext : v > ext) { ext = v; extIdx = j; }
    }
    const move = (ext - c0) / c0 * 100; // 골든 뒤 하락이면 음수
    const bad = up ? -move : move;      // "가짜" 정도 (%)
    if (bad > 0.5) push({ pattern, crossIdx: i, extIdx, movePct: +move.toFixed(2), gap: hasGap(i - 40, extIdx), score: bad });
  }
}

if (pattern === 'chop') {
  const W = Math.round(120 / bm) * bm === 120 ? 120 : 120; // 창 크기(봉)
  for (let a = 40; a < bars.length - W; a += 10) {
    const b = a + W;
    let crosses = 0;
    const xs = [];
    for (let i = a + 1; i < b; i++) if (crossUp(i) || crossDn(i)) { crosses++; xs.push(i); }
    if (crosses < 5) continue;
    const hi = Math.max(...bars.slice(a, b).map((x) => x.h));
    const lo = Math.min(...bars.slice(a, b).map((x) => x.l));
    const avgRange = bars.slice(a, b).reduce((s2, x) => s2 + (x.h - x.l), 0) / W;
    const tight = (hi - lo) / avgRange; // 작을수록 횡보
    if (tight < 14) push({ pattern, start: a, end: b, crosses, crossIdxs: xs.slice(0, 12), tight: +tight.toFixed(1), gap: hasGap(a, b), score: crosses / tight });
  }
}

if (pattern === 'blind') {
  for (let i = 40; i < bars.length; i++) {
    if (rsi[i] == null || rsi[i] < 70) continue;
    let j = i;
    let hiStart = bars[i].h; let hiEnd = bars[i].h;
    while (j < bars.length - 1 && rsi[j + 1] >= 68) { j++; hiEnd = Math.max(hiEnd, bars[j].h); }
    const len = j - i + 1;
    if (len >= Math.round(12 / (bm / 1))) {
      const rise = (hiEnd - hiStart) / hiStart * 100;
      if (rise > 0.15) push({ pattern, start: i, end: j, lenBars: len, risePct: +rise.toFixed(2), gap: hasGap(i - 40, j), score: len * rise });
    }
    i = j + 1;
  }
}

if (pattern === 'pullback' || pattern === 'sellArray') {
  const long = pattern === 'pullback';
  const LV = long ? 55 : 45;
  for (let i = 60; i < bars.length - 25; i++) {
    // 배열 상태가 K봉 이상 지속
    let ok = true;
    for (let k = i - 20; k <= i; k++) {
      if (s10[k] == null || s34[k] == null || (long ? s10[k] <= s34[k] : s10[k] >= s34[k])) { ok = false; break; }
    }
    if (!ok || rsi[i] == null || rsi[i - 1] == null) continue;
    // RSI 가 레벨을 이탈했다가 (양봉/음봉으로) 재돌파하는 지점
    const recross = long
      ? rsi[i - 1] < LV && rsi[i] >= LV && bars[i].c > bars[i].o
      : rsi[i - 1] > LV && rsi[i] <= LV && bars[i].c < bars[i].o;
    if (!recross) continue;
    // 직전 이탈 깊이 (얼마나 눌렸다 왔나)
    let dipIdx = i - 1; let dip = rsi[i - 1];
    for (let k = i - 1; k > i - 15 && k > 0; k--) {
      if (rsi[k] == null) break;
      if (long ? rsi[k] < dip : rsi[k] > dip) { dip = rsi[k]; dipIdx = k; }
      if (long ? rsi[k] >= LV : rsi[k] <= LV) break;
    }
    // 진입 뒤 이익 방향으로 실제로 갔나 (다음 캔들 시가 진입 가정)
    const entry = bars[i + 1]?.o; if (entry == null) continue;
    let fav = 0; let adv = 0;
    for (let j = i + 1; j <= Math.min(i + 20, bars.length - 1); j++) {
      fav = Math.max(fav, long ? bars[j].h - entry : entry - bars[j].l);
      adv = Math.max(adv, long ? entry - bars[j].l : bars[j].h - entry);
    }
    const stop = long ? entry - bars[i].l : bars[i].h - entry; // 신호 캔들 반대끝 손절
    if (stop <= 0) continue;
    const rr = fav / stop;
    if (rr >= 2 && adv < stop) {
      push({ pattern, dipIdx, entrySignalIdx: i, entryIdx: i + 1, dipRsi: +dip.toFixed(1),
        stopPts: +stop.toFixed(2), favPts: +fav.toFixed(2), rr: +rr.toFixed(2),
        gap: hasGap(i - 60, Math.min(i + 20, bars.length - 1)), score: rr });
    }
  }
}

found.sort((a, b) => (a.gap - b.gap) || (b.score - a.score));
console.log(`${file} · ${pattern} · 후보 ${found.length}개 (갭 없는 것 우선, 상위 ${top})`);
for (const f of found.slice(0, top)) {
  const at = f.crossIdx ?? f.start ?? f.entrySignalIdx;
  console.log(JSON.stringify({ ...f, when: new Date(bars[at].t).toISOString() }));
}
