/**
 * 씬 런타임. 브라우저에서 동작한다.
 *
 * 실시간 재생(requestAnimationFrame)이 아니라 프레임 번호를 받아 그리는 방식이다.
 * 렌더 속도와 무관하게 정확히 지정한 fps 로 뽑히고, 아무 프레임이나 다시 그려도 결과가 같다.
 */
import { makeCandles } from '../market/candles.js';
import { Chart } from './chart.js';
import { drawLayer } from './layers.js';
import { makeTheme } from './theme.js';
import { Ease, lerp, clamp } from './anim.js';

function easeByName(name) {
  if (typeof name === 'function') return name;
  return Ease[name] ?? Ease.inOutCubic;
}

/** 키프레임 보간: [{t, v, ease}] */
function keyframe(list, t, fallback) {
  if (list == null) return fallback;
  if (typeof list === 'number') return list;
  if (!list.length) return fallback;
  if (t <= list[0].t) return list[0].v;
  for (let i = 1; i < list.length; i++) {
    if (t <= list[i].t) {
      const a = list[i - 1];
      const b = list[i];
      const p = b.t === a.t ? 1 : (t - a.t) / (b.t - a.t);
      return lerp(a.v, b.v, easeByName(b.ease ?? 'inOutCubic')(clamp(p)));
    }
  }
  return list[list.length - 1].v;
}

export class SceneRuntime {
  constructor(canvas, scene, project) {
    this.canvas = canvas;
    this.scene = scene;
    this.project = project;
    this.fps = project.fps;
    this.w = canvas.width;
    this.h = canvas.height;
    this.ctx = canvas.getContext('2d', { alpha: true });
    this.theme = makeTheme({ ...(project.theme ?? {}), ...(scene.theme ?? {}) });

    const market = { ...(project.market ?? {}), ...(scene.market ?? {}) };
    const { bars, meta } = makeCandles(market);
    this.bars = bars;
    this.marketMeta = meta;

    const c = scene.chart ?? {};
    this.chartCfg = c;
    this.chart = new Chart({
      ctx: this.ctx,
      width: this.w,
      height: this.h,
      bars,
      theme: this.theme,
      layout: c.layout,
      view: {
        visibleBars: c.visibleBars ?? 62,
        pricePad: c.pricePad ?? 0.16,
        include: c.include ?? null,
        ma: c.ma,
      },
    });
    this.totalFrames = Math.round(scene.duration * this.fps);
  }

  /** 프레임 하나 그리기. frame 은 0-based */
  renderFrame(frame) {
    const t = frame / this.fps;
    const ctx = this.ctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, this.w, this.h);
    ctx.globalAlpha = 1;

    const c = this.chartCfg;
    const reveal = clamp(
      keyframe(c.reveal, t, this.bars.length),
      0.001,
      this.bars.length,
    );
    const zoom = keyframe(c.zoom, t, 1);
    const priceOffset = keyframe(c.priceOffset, t, 0);
    const chartAlpha = keyframe(c.alpha, t, 1);

    const info = this.chart.frame({
      reveal,
      zoom,
      priceOffset,
      alpha: chartAlpha,
      showGrid: c.showGrid !== false,
      showAxes: c.showAxes !== false,
      showLast: c.showLast !== false,
    });

    const env = {
      t,
      frame,
      fps: this.fps,
      w: this.w,
      h: this.h,
      theme: this.theme,
      chart: this.chart,
      scale: info.scale,
      viewport: info.viewport,
      last: info.last,
      reveal,
      bars: this.bars,
      scene: this.scene,
    };

    for (const layer of this.scene.layers ?? []) {
      if (layer.enabled === false) continue;
      drawLayer(ctx, layer, env);
    }

    // 씬 전체 페이드 인/아웃
    const fi = this.scene.fadeIn ?? 0;
    const fo = this.scene.fadeOut ?? 0;
    let fade = 1;
    if (fi > 0) fade = Math.min(fade, clamp(t / fi));
    if (fo > 0) fade = Math.min(fade, clamp((this.scene.duration - t) / fo));
    if (fade < 1) {
      ctx.save();
      ctx.globalCompositeOperation = this.theme.transparent ? 'destination-out' : 'source-over';
      ctx.globalAlpha = 1 - fade;
      ctx.fillStyle = this.theme.transparent ? '#000' : (this.scene.fadeColor ?? '#000');
      ctx.fillRect(0, 0, this.w, this.h);
      ctx.restore();
    }
    return t;
  }
}

/** 페이지 부트스트랩: ?scene=<id> 로 씬을 골라 준비하고 window 에 API 를 노출한다 */
export async function boot() {
  const params = new URLSearchParams(location.search);
  const file = params.get('config') ?? 'scenes/nq-basic.scenes.js';
  const sceneId = params.get('scene');
  const mod = await import(`/${file}?v=${Date.now()}`);
  const project = mod.default;
  const scene = sceneId
    ? project.scenes.find((s) => s.id === sceneId)
    : project.scenes[0];
  if (!scene) throw new Error(`씬을 찾을 수 없습니다: ${sceneId}`);

  const canvas = document.getElementById('stage');
  canvas.width = project.width;
  canvas.height = project.height;
  const runtime = new SceneRuntime(canvas, scene, project);

  window.__scene = {
    id: scene.id,
    name: scene.name,
    duration: scene.duration,
    fps: project.fps,
    totalFrames: runtime.totalFrames,
    width: project.width,
    height: project.height,
    transparent: !!runtime.theme.transparent,
  };
  window.__renderFrame = (n) => runtime.renderFrame(n);
  window.__runtime = runtime;
  await document.fonts.ready;
  runtime.renderFrame(0);
  window.__ready = true;
  return runtime;
}
