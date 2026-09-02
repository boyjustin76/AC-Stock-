#!/usr/bin/env node
/**
 * 컷 전수 조사 — AE 컴포지션으로 옮기기 전에 무엇을 상대하는지 잰다.
 *
 *   node src/tools/exp-survey.mjs scenes/sl-11-4.scenes.js
 *
 * 컷마다: 길이 · 레이어 종류 · **카메라가 움직이는 양**.
 * 카메라가 멈춰 있으면 바닥을 스틸 한 장으로 깔고 주석 좌표를 고정하면 된다(파일럿 방식).
 * 움직이면 주석이 차트를 따라가야 하므로 추적이 필요하다.
 */
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import { makeCandles } from '../market/candles.js';
import { Chart } from '../render/chart.js';
import { makeTheme } from '../render/theme.js';
import { clamp } from '../render/anim.js';
import { keyframe } from '../render/engine.js';


const file = process.argv[2] ?? 'scenes/sl-11-4.scenes.js';
const project = (await import(pathToFileURL(path.resolve(file)).href)).default;
const fps = project.fps;

console.log(`\n  ${project.title}   ${project.width}x${project.height} @ ${fps}fps\n`);

const allTypes = new Map();
let totalLayers = 0;

for (const scene of project.scenes) {
  const c = scene.chart ?? {};
  const { bars } = makeCandles({ ...(project.market ?? {}), ...(scene.market ?? {}) });
  const chart = new Chart({
    ctx: null, width: project.width, height: project.height, bars,
    theme: makeTheme({ ...(project.theme ?? {}), ...(scene.theme ?? {}) }),
    layout: c.layout,
    view: { visibleBars: c.visibleBars ?? 62, pricePad: c.pricePad ?? 0.16, include: c.include ?? null, ma: c.ma, rsi: c.rsi },
  });
  const frames = Math.round(scene.duration * fps);

  /*  카메라 = (x 원점, barW, y 원점, y 배율). 이 넷이 정해지면 어떤 (봉,가격)이든 픽셀이 나온다.
      프레임마다 재서 최댓값-최솟값을 본다.  */
  const xs = [], ws = [], ys = [], hs = [];
  for (let f = 0; f < frames; f++) {
    const t = f / fps;
    const vp = chart.viewport(
      clamp(keyframe(c.reveal, t, bars.length), 0.001, bars.length),
      keyframe(c.zoom, t, 1), keyframe(c.priceOffset, t, 0));
    const s = chart.makeScale(vp);
    xs.push(s.x(0)); ws.push(s.barW); ys.push(s.y(0)); hs.push(s.y(1000) - s.y(0));
  }
  const rng = (a) => Math.max(...a) - Math.min(...a);
  const still = rng(xs) < 0.5 && rng(ws) < 0.01 && rng(ys) < 0.5;

  const types = (scene.layers ?? []).map((l) => l.type);
  types.forEach((t) => allTypes.set(t, (allTypes.get(t) ?? 0) + 1));
  totalLayers += types.length;

  const uniq = [...new Set(types)];
  console.log(`  ${scene.id}`);
  console.log(`    ${frames}f (${scene.duration.toFixed(2)}s) · 레이어 ${types.length}개 · ${uniq.join(' ')}`);
  console.log(`    카메라 ${still ? '멈춤 — 스틸 바닥 가능'
    : `움직임 · x폭 ${rng(xs).toFixed(0)}px · barW ${Math.min(...ws).toFixed(1)}~${Math.max(...ws).toFixed(1)} · y폭 ${rng(ys).toFixed(0)}px`}`);
}

console.log(`\n  합계 ${project.scenes.length}컷 · 레이어 ${totalLayers}개`);
console.log('  종류별: ' + [...allTypes.entries()].sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}×${v}`).join(' · ') + '\n');
