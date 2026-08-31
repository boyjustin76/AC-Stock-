/**
 * 라벨 클리핑 감사 도구 — 렌더 없이 씬의 가격/RSI 앵커 라벨이 화면 안에 있는지 수치로 확인한다.
 *
 * 뷰포트는 리빌·줌·가격범위 스무딩(_priceRange)에 따라 매 프레임 움직이므로,
 * 라벨이 "등장 시점엔 반쯤 잘리고 나중에야 들어오는" 문제는 스틸 몇 장으로는 놓치기 쉽다.
 * 여기서는 등장(in)부터 퇴장(out 또는 씬 끝)까지 0.25초 간격으로 y 를 전부 계산해
 * 잘리는 구간을 표로 보고한다.
 *
 *   node src/tools/probe-labels.mjs --config scenes/cmg12-buy.scenes.js [--scene id] [--margin 60]
 */
import { SceneRuntime, keyframe } from '../render/engine.js';
import { clamp } from '../render/anim.js';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
function arg(name, dflt) {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : dflt;
}
const configPath = arg('config');
const onlyScene = arg('scene', null);
const MARGIN = Number(arg('margin', 60));

if (!configPath) {
  console.error('사용법: node src/tools/probe-labels.mjs --config scenes/xxx.scenes.js');
  process.exit(1);
}

/* 그리지 않는 2D 컨텍스트 흉내 — 좌표 계산(viewport/makeScale)만 쓴다 */
function stubCtx() {
  const store = {};
  return new Proxy(store, {
    get(t, p) {
      if (p === 'measureText') return () => ({ width: 100 });
      if (p === 'createLinearGradient' || p === 'createRadialGradient') {
        return () => ({ addColorStop() {} });
      }
      if (p in t) return t[p];
      return () => undefined;
    },
    set(t, p, v) { t[p] = v; return true; },
  });
}

const mod = await import(pathToFileURL(path.resolve(configPath)).href);
const project = mod.default;
const ANCHORED = new Set(['cmgNote', 'cmgUnderline', 'cmgCircle', 'cmgArrow', 'cmgLevel']);

for (const scene of project.scenes) {
  if (onlyScene && scene.id !== onlyScene) continue;
  const canvas = { width: project.width, height: project.height, getContext: () => stubCtx() };
  const rt = new SceneRuntime(canvas, scene, project);
  const c = scene.chart ?? {};
  const H = project.height;

  const scaleAt = (t) => {
    const reveal = clamp(keyframe(c.reveal, t, rt.bars.length), 0.001, rt.bars.length);
    const zoom = keyframe(c.zoom, t, 1);
    const vp = rt.chart.viewport(reveal, zoom, keyframe(c.priceOffset, t, 0));
    return rt.chart.makeScale(vp);
  };

  console.log(`\n■ ${scene.id} (${scene.duration.toFixed(2)}s) — ${scene.name ?? ''}`);
  for (const L of scene.layers ?? []) {
    if (!ANCHORED.has(L.type)) continue;
    if (L.price == null && L.rsi == null) continue;
    const t0 = (L.in?.[0] ?? 0) + (L.in?.[1] ?? 0);
    const t1 = L.out ? L.out[0] : scene.duration;
    let minY = Infinity;
    let maxY = -Infinity;
    let clipSpans = [];
    let cur = null;
    for (let t = t0; t <= t1 + 1e-6; t += 0.25) {
      const s = scaleAt(Math.min(t, scene.duration));
      const y = (L.rsi != null && s.rsiY ? s.rsiY(L.rsi) : s.y(L.price)) + (L.dy ?? 0);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
      const clipped = y < MARGIN || y > H - MARGIN;
      if (clipped && !cur) cur = [t, t];
      else if (clipped && cur) cur[1] = t;
      else if (!clipped && cur) { clipSpans.push(cur); cur = null; }
    }
    if (cur) clipSpans.push(cur);
    const label = L.text ?? L.label ?? L.type;
    const anchor = L.rsi != null ? `rsi ${L.rsi}` : `price ${L.price}`;
    const spanTxt = clipSpans.length
      ? `  ⚠ 잘림 ${clipSpans.map(([a, b]) => `${a.toFixed(2)}~${b.toFixed(2)}s`).join(', ')}`
      : '';
    console.log(
      `  ${clipSpans.length ? '⚠' : '·'} ${L.type} "${label}" (${anchor}${L.dy ? ` dy ${L.dy}` : ''})` +
      ` in ${t0.toFixed(2)}s  y ${minY.toFixed(0)}~${maxY.toFixed(0)}${spanTxt}`,
    );
  }
}
