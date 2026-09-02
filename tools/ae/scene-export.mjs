#!/usr/bin/env node
/**
 * 렌더러 → AE 좌표 내보내기.
 *
 *   node tools/ae/scene-export.mjs scenes/sl-11-4.scenes.js --out C:/aelab/ae
 *
 * 파일럿(anchors.mjs)은 컷② 의 reveal 63 한 시점만 쟀다. 카메라가 멈춰 있었으니까.
 * 실제 컷은 11개 중 10개가 움직이므로 **프레임마다** 좌표계를 내보낸다.
 *
 * 좌표계는 완전한 아핀이다(chart.js makeScale) —
 *     x = X0 + 봉   × BW
 *     y = Y0 - 가격 × K
 * 그래서 프레임당 네 숫자면 어떤 (봉,가격)이든 픽셀이 나온다. AE 쪽에서는 이 넷을
 * 널 하나에 키프레임으로 박고, 주석은 표현식으로 자기 위치를 계산한다 — 주석마다
 * 수백 개 키프레임을 굽지 않아도 되고, 사람이 열어 봐도 읽힌다.
 *
 * 좌표는 사람 눈이 아니라 렌더러가 정한다. 이 파일이 그 약속을 지키는 곳이다.
 *
 * 내보내는 것 둘:
 *   <out>/<슬러그>.json   사람과 도구가 읽는 형태
 *   <out>/<슬러그>.jsx    AE 가 $.evalFile 로 읽는 형태 (ExtendScript 에 JSON 이 없다)
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import { makeCandles } from '../../src/market/candles.js';
import { Chart } from '../../src/render/chart.js';
import { makeTheme } from '../../src/render/theme.js';
import { clamp } from '../../src/render/anim.js';
import { keyframe } from '../../src/render/engine.js';

const args = process.argv.slice(2);
const file = args.find((a) => !a.startsWith('--')) ?? 'scenes/sl-11-4.scenes.js';
const outDir = (args[args.indexOf('--out') + 1] && args.includes('--out')) ? args[args.indexOf('--out') + 1] : 'C:/aelab/ae';

const project = (await import(pathToFileURL(path.resolve(file)).href)).default;
const fps = project.fps;
const slug = path.basename(file).replace('.scenes.js', '');
const r2 = (n) => Math.round(n * 100) / 100;

/** 함수·undefined 를 걷어낸 순수 데이터 (씬 파일이 진실이지만 AE 로는 데이터만 넘긴다) */
function plain(v) {
  if (typeof v === 'function' || v === undefined) return undefined;
  if (Array.isArray(v)) return v.map(plain).filter((x) => x !== undefined);
  if (v && typeof v === 'object') {
    const o = {};
    for (const k of Object.keys(v)) { const p = plain(v[k]); if (p !== undefined) o[k] = p; }
    return o;
  }
  return v;
}

const cuts = [];
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
  const p = chart.plot;

  const X0 = [], BW = [], Y0 = [], K = [];
  for (let f = 0; f < frames; f++) {
    const t = f / fps;
    const vp = chart.viewport(
      clamp(keyframe(c.reveal, t, bars.length), 0.001, bars.length),
      keyframe(c.zoom, t, 1),
      keyframe(c.priceOffset, t, 0),
    );
    const bw = p.w / (vp.right - vp.left);
    const k = p.h / (vp.hi - vp.lo);
    X0.push(r2(p.x - vp.left * bw));
    BW.push(r2(bw));
    Y0.push(r2(p.bottom + vp.lo * k));
    K.push(Math.round(k * 1e6) / 1e6);   /* 가격 1단위당 픽셀 — 작은 수라 자리를 더 준다 */
  }
  const rng = (a) => Math.max(...a) - Math.min(...a);
  const still = rng(X0) < 0.5 && rng(BW) < 0.01 && rng(Y0) < 0.5;

  cuts.push({
    id: scene.id,
    name: scene.name,
    frames,
    duration: r2(scene.duration),
    still,
    fadeIn: scene.fadeIn ?? 0,
    fadeOut: scene.fadeOut ?? 0,
    plot: { x: r2(p.x), y: r2(p.y), w: r2(p.w), h: r2(p.h), right: r2(p.right), bottom: r2(p.bottom) },
    /* 캔들 몸통 폭 = 봉 간격 × 0.66 (chart.js makeScale) */
    bodyRatio: 0.66,
    cam: { X0, BW, Y0, K },
    layers: (scene.layers ?? []).map((L, i) => ({ i, ...plain(L) })),
  });
}

const out = {
  _설명: 'tools/ae/scene-export.mjs 가 만든 좌표. x = X0 + 봉*BW, y = Y0 - 가격*K (프레임별). AE 는 좌상단 원점 — 캔버스와 같다.',
  slug,
  title: project.title,
  w: project.width,
  h: project.height,
  fps,
  cuts,
};

mkdirSync(outDir, { recursive: true });
const j = path.join(outDir, slug + '.json');
const x = path.join(outDir, slug + '.jsx');
const body = JSON.stringify(out);
writeFileSync(j, JSON.stringify(out, null, 1), 'utf8');
/* ExtendScript 에는 JSON 이 없다 — 객체 리터럴로 넘긴다 (JSON 은 유효한 JS 다) */
writeFileSync(x, 'var SCENE = ' + body + ';\n', 'utf8');

console.log(`\n  ${project.title}`);
for (const c of cuts) {
  console.log(`    ${c.id.padEnd(22)} ${String(c.frames).padStart(4)}f · 레이어 ${String(c.layers.length).padStart(2)} · 카메라 ${c.still ? '멈춤' : '움직임'}`);
}
console.log(`\n  → ${j}`);
console.log(`  → ${x}  (${(body.length / 1024).toFixed(0)}KB)\n`);
