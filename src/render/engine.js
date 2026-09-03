/* ── 검토 ──
 * 검토내용: 결정적 렌더(프레임 번호→그림) 구조 건전. 드로잉은 2.2ms/f 로 병목 아님이 실측돼 최적화 불필요. 난수 없는 카메라 셰이크·키프레임 보간 모두 재현성 유지. 수정 없음.
 * 타임코드: 2026-08-27 19:42 KST
 * 검토자: Fable 5 Max
 */
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
import { Ease, lerp, clamp, span } from './anim.js';

function easeByName(name) {
  if (typeof name === 'function') return name;
  return Ease[name] ?? Ease.inOutCubic;
}

/** 키프레임 보간: [{t, v, ease}] — 좌표를 재계산하는 바깥 도구들도 이걸 쓴다 */
export function keyframe(list, t, fallback) {
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

/**
 * 등장·퇴장을 걷어내고 **컷 내내 켜진** 레이어로 바꾼다.
 *
 * 왜 —
 *   주석을 알파 클립으로 갈라 프리미어에 얹으면 싱크를 손으로 만질 수 있는데,
 *   클립을 **밀면** 주석은 밀기 전 시각의 픽셀인 채 옮겨져 차트와 어긋난다
 *   (차트가 컷 안에서 움직이므로 — src/tools/exp-drift.mjs 로 실측).
 *   그런데 컷 내내 켜 두면 어느 프레임이든 그 시각의 올바른 위치에 그려져 있어,
 *   **자르기(트림)** 로 등장 시점을 정하면 어긋남이 0 이다. 미는 대신 자르는 것이다.
 *
 * in 을 아주 이른 시각으로 밀어 두면 cue() 는 계속 1 을 주고, growDur·drawDur 로
 * 도는 자라남·손그림도 컷이 시작하기 전에 이미 끝나 있다.
 * `in` 이 없는 레이어(flash 처럼 at/dur 로 도는 것)는 건드리지 않는다 — 순간 효과라
 * 켜 두는 게 뜻이 없다.
 */
function holdOn(layer) {
  if (!layer.in) return layer;
  return { ...layer, in: [-10, 0.001], out: null };
}

/** 씬에서 쓰는 이미지를 모두 미리 로드한다 (첫 프레임에 빠지지 않게) */
async function preloadImages(scene) {
  const srcs = [...new Set((scene.layers ?? []).filter((l) => l.type === 'image' && l.src).map((l) => l.src))];
  const out = {};
  await Promise.all(
    srcs.map(async (src) => {
      const img = new Image();
      img.src = encodeURI(src);
      await img.decode();
      out[src] = img;
    }),
  );
  return out;
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
        rsi: c.rsi,
      },
    });
    this.totalFrames = Math.round(scene.duration * this.fps);
    this.images = {};
    /*  패스 = '이번 렌더에 무엇을 그릴지'. null 이면 전부 그린다(기존 동작).
        {chart:false, layers:[3,4]} 처럼 주면 그 조각만 그린다 — 프리미어에
        트랙으로 쌓을 알파 클립을 뽑는 용도다. 좌표계는 무엇을 끄든 그대로
        계산되므로(chart.frame 주석 참고) 조각들을 겹치면 원본과 같은 그림이 된다.  */
    this.pass = null;

    /*  팀장 규칙 ⑭ (2026-09-01, 이정찬 전달): 매수/매도/익절/손절 버튼은 무조건 레이어
        맨 앞 — 배열 순서와 무관하게 cmgArrow 를 마지막에 그린다(같은 층 안에서는 배열
        순서 유지, sort 는 안정 정렬). 버튼 위에 무언가를 얹어야 하면 순서를 바꾸지 말고
        버튼을 잠깐 투명화한다. 반려 사례: 차12 병합 인트로에서 손절 태그가 뒤에 선언된
        손실 밴드에 덮임. brand/EDIT-RULEBOOK.md ⑭
        패스로 조각을 뽑을 때도 골라내려면 **원래 배열 번호**가 필요해 함께 싣는다.  */
    /*  z 를 직접 적어 그 층만 예외로 둘 수 있다 (2026-09-03). ⑭ 의 기본 층은
        영역·글자 0 < 동그라미·배지 10 < 버튼 20 이고, 사이 값을 적으면 그 자리에
        낀다. 만든 이유: 동그라미가 **영역** 위여야 한다는 ⑭ 의 뜻과 달리 글자가
        영역과 같은 0 층이라 손그림 원이 문구를 갈라 놓는 자리가 있었다
        (차11-4 컷③ '기울기 상방'). 규칙 자체를 뒤집으면 이미 컨펌된 36개 씬의
        순서가 흔들려 그 자리에서만 z 로 올린다 — ⑭ 이 버튼 충돌에 '순서를 바꾸지
        말고 잠깐 투명화하라'고 한 것과 같은 결의 국소 해법이다.
        z 를 안 적으면 예전과 완전히 같은 순서다(전 씬 대조로 확인).  */
    const zOf = (L) => (L.z != null ? L.z
      : L.type === 'cmgArrow' ? 20
      : (L.type === 'cmgCircle' || L.type === 'cmgBadge') ? 10 : 0);
    this.drawOrder = (scene.layers ?? [])
      .map((L, i) => ({ L, i }))
      .sort((a, b) => zOf(a.L) - zOf(b.L));
  }

  /** 프레임 하나 그리기. frame 은 0-based */
  renderFrame(frame) {
    const t = frame / this.fps;
    const ctx = this.ctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, this.w, this.h);
    ctx.globalAlpha = 1;

    // 카메라 흔들림. 난수를 쓰지 않아 같은 프레임은 항상 같은 결과가 나온다.
    const shake = keyframe(this.scene.camera?.shake, t, 0);
    if (shake > 0) {
      const a = Math.sin(t * 47.3) * shake * 14;
      const b = Math.cos(t * 61.7) * shake * 10;
      const cx = this.w / 2;
      const cy = this.h / 2;
      const z = 1 + shake * 0.02;
      ctx.translate(cx, cy);
      ctx.scale(z, z);
      ctx.translate(-cx, -cy);
      ctx.translate(a, b);
    }

    const c = this.chartCfg;
    const reveal = clamp(
      keyframe(c.reveal, t, this.bars.length),
      0.001,
      this.bars.length,
    );
    const zoom = keyframe(c.zoom, t, 1);
    const priceOffset = keyframe(c.priceOffset, t, 0);
    const chartAlpha = keyframe(c.alpha, t, 1);

    // 이평선별 등장 알파 (c.ma[i].alpha 키프레임) · RSI 패널 등장 알파 (c.rsiAlpha)
    const maAlphas = (c.ma ?? []).map((m) => keyframe(m.alpha, t, 1));
    const rsiAlpha = keyframe(c.rsiAlpha, t, 1);

    const pass = this.pass;
    const floor = !pass || pass.chart !== false;

    /* 카드 씬용: 차트를 흐려서 배경으로 깐다 (팀장 최종본의 워시 문법 — c.alpha 와 조합).
       ctx.filter 를 켠 채 chart.frame() 을 부르면 캔들·꼬리·이평선 드로우콜 하나하나에
       블러 패스가 돌아 프레임당 수 초가 걸린다(r10 실측 — 인트로 1794f 에 80분).
       오프스크린에 차트를 완성한 뒤 그 한 장에만 블러를 건다. */
    const blurPx = keyframe(c.blurPx, t, 0);
    let chartTargetCtx = null;
    if (blurPx > 0) {
      if (!this._blurLayer) {
        this._blurLayer = document.createElement('canvas');
        this._blurLayer.width = this.w;
        this._blurLayer.height = this.h;
        this._blurLayerCtx = this._blurLayer.getContext('2d', { alpha: true });
      }
      const octx = this._blurLayerCtx;
      octx.setTransform(1, 0, 0, 1, 0, 0);
      octx.clearRect(0, 0, this.w, this.h);
      chartTargetCtx = this.chart.ctx;
      this.chart.ctx = octx;
    }
    const info = this.chart.frame({
      reveal,
      zoom,
      priceOffset,
      alpha: chartAlpha,
      showGrid: floor && c.showGrid !== false,
      showAxes: floor && c.showAxes !== false,
      showLast: floor && c.showLast !== false,
      showCandles: floor && c.showCandles !== false,
      showMAs: floor && c.showMAs !== false,
      maAlphas,
      rsiAlpha: floor ? rsiAlpha : 0,
    });
    if (blurPx > 0) {
      this.chart.ctx = chartTargetCtx;
      ctx.save();
      ctx.filter = `blur(${blurPx}px)`;
      ctx.drawImage(this._blurLayer, 0, 0);
      ctx.restore();
      ctx.filter = 'none';
    }

    /*  chart.phases (차12 r13 실사 문법): 같은 bars 에서 reveal(·zoom·priceOffset)만
        다른 정지 차트를 크로스디졸브로 교체한다 — 실제 최종본이 "나중 시점 스크린샷"으로
        디졸브하던 컷 안 진행의 엔진 등가물. 배경이 불투명이라 위에 그리면 곧 디졸브다.
          chart: { reveal: 92, phases: [{ reveal: 128, in: [9.0, 0.5] }] }
        - 좌표계는 등장 전에도 항상 계산해 env.phases[k] 로 노출한다. 레이어에
          phase: 1 을 적으면 그 국면의 scale/viewport 로 앵커된다 (0 = 기본 차트).
        - env 의 최상위 scale/viewport/last 는 언제나 기본 차트(phase 0)다.
        - blurPx 와의 조합은 지원하지 않는다(카드 씬은 phases 를 쓸 일이 없다).
        - phases 미선언 씬은 이 블록을 스치지도 않는다 — 기존 경로 그대로.  */
    const phaseInfos = [info];
    const phasesCfg = Array.isArray(c.phases) ? c.phases : null;
    if (phasesCfg && floor && blurPx <= 0) {
      const showFlags = {
        alpha: chartAlpha,
        showGrid: c.showGrid !== false,
        showAxes: c.showAxes !== false,
        showLast: c.showLast !== false,
        showCandles: c.showCandles !== false,
        showMAs: c.showMAs !== false,
        maAlphas,
        rsiAlpha,
      };
      for (const ph of phasesCfg) {
        const pReveal = clamp(ph.reveal ?? reveal, 0.001, this.bars.length);
        const pZoom = ph.zoom ?? zoom;
        const pOff = ph.priceOffset ?? priceOffset;
        const [ps = 0, pd = 0] = ph.in ?? [];
        const a = ph.in ? span(t, ps, ps + Math.max(pd, 1e-4), Ease.inOutQuad) : 1;
        if (a <= 0) {
          // 아직 안 나옴 — 레이어 앵커용 좌표만 계산
          const vp = this.chart.viewport(pReveal, pZoom, pOff);
          const s = this.chart.makeScale(vp);
          phaseInfos.push({ scale: s, viewport: vp, last: this.chart.lastInfo(s, pReveal) });
        } else if (a >= 1) {
          // 완전 교체 — 본 캔버스에 그대로 덮어 그린다
          phaseInfos.push(this.chart.frame({ reveal: pReveal, zoom: pZoom, priceOffset: pOff, ...showFlags }));
        } else {
          // 디졸브 중 — 오프스크린 한 장에 완성해 알파로 얹는다
          if (!this._phaseLayer) {
            this._phaseLayer = document.createElement('canvas');
            this._phaseLayer.width = this.w;
            this._phaseLayer.height = this.h;
            this._phaseLayerCtx = this._phaseLayer.getContext('2d', { alpha: true });
          }
          const pctx = this._phaseLayerCtx;
          pctx.setTransform(1, 0, 0, 1, 0, 0);
          pctx.clearRect(0, 0, this.w, this.h);
          const prev = this.chart.ctx;
          this.chart.ctx = pctx;
          const pi = this.chart.frame({ reveal: pReveal, zoom: pZoom, priceOffset: pOff, ...showFlags });
          this.chart.ctx = prev;
          ctx.save();
          ctx.globalAlpha = a;
          ctx.drawImage(this._phaseLayer, 0, 0);
          ctx.restore();
          phaseInfos.push(pi);
        }
      }
    }

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
      images: this.images,
      phases: phaseInfos, // [0] = 기본 차트, [k] = chart.phases[k-1] 의 좌표계
    };

    const pick = pass?.layers ?? null;   // null = 전부
    for (const entry of this.drawOrder) {
      if (pick && !pick.includes(entry.i)) continue;
      let layer = entry.L;
      if (layer.enabled === false) continue;
      if (pass?.hold) layer = holdOn(layer);
      // layer.phase: k — 그 국면의 좌표계로 앵커 (chart.phases 참고)
      let envL = env;
      if (layer.phase != null && phaseInfos[layer.phase]) {
        const pi = phaseInfos[layer.phase];
        envL = { ...env, scale: pi.scale, viewport: pi.viewport, last: pi.last };
      }
      drawLayer(ctx, layer, envL);
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
  runtime.images = await preloadImages(scene);

  window.__scene = {
    id: scene.id,
    name: scene.name,
    duration: scene.duration,
    fps: project.fps,
    fpsExpr: project.fpsExpr ?? null,
    totalFrames: runtime.totalFrames,
    width: project.width,
    height: project.height,
    transparent: !!runtime.theme.transparent,
  };
  window.__renderFrame = (n) => runtime.renderFrame(n);
  /** 패스 지정. {chart, layers, transparent} — 캡처 쪽에서 호출한다 */
  window.__setPass = (p) => {
    runtime.pass = p ?? null;
    if (p && p.transparent) runtime.theme.transparent = true;
    return true;
  };
  window.__runtime = runtime;
  await document.fonts.ready;
  runtime.renderFrame(0);
  window.__ready = true;
  return runtime;
}
