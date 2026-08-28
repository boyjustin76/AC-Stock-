/* ── 검토 ──
 * 검토내용: 드로잉 전체가 2.2ms/f(engine 경유 실측)로 병목이 아니어서 상세 최적화 검토 제외. 수정 없음.
 * 타임코드: 2026-08-27 19:42 KST
 * 검토자: Fable 5 Max
 */
/**
 * 캔들차트 캔버스 렌더러.
 *
 * 프레임마다 상태를 남기지 않는다(stateless). 같은 t 를 넣으면 항상 같은 그림이 나오므로,
 * 프리뷰에서 아무 지점이나 스크럽해도 최종 렌더 결과와 어긋나지 않는다.
 */
import { clamp, lerp, Ease, span } from './anim.js';
import { formingBar, sma, ema } from '../market/candles.js';

const DEFAULT_LAYOUT = {
  padLeft: 84,
  padRight: 176, // 가격축 라벨 자리
  padTop: 152, // 좌상단 HUD 자리를 비워 둔다
  padBottom: 82,
  rightGap: 6, // 마지막 캔들 오른쪽으로 비워 둘 바 개수
};

export class Chart {
  constructor({ ctx, width, height, bars, theme, layout = {}, view = {} }) {
    this.ctx = ctx;
    this.w = width;
    this.h = height;
    this.bars = bars;
    this.theme = theme;
    this.layout = { ...DEFAULT_LAYOUT, ...layout };
    this.view = {
      visibleBars: 62,
      pricePad: 0.16, // 위아래 여백 비율
      include: null, // 화면에 반드시 포함할 가격들
      ...view,
    };
    this.overlays = (view.ma ?? []).map((m) => ({
      ...m,
      values: m.type === 'ema' ? ema(bars, m.period) : sma(bars, m.period),
    }));
    this._plot();
  }

  _plot() {
    const L = this.layout;
    this.plot = {
      x: L.padLeft,
      y: L.padTop,
      w: this.w - L.padLeft - L.padRight,
      h: this.h - L.padTop - L.padBottom,
    };
    this.plot.right = this.plot.x + this.plot.w;
    this.plot.bottom = this.plot.y + this.plot.h;
  }

  /* ---------------- 좌표계 ---------------- */

  /** 현재 프레임의 뷰포트(바 인덱스 범위 + 가격 범위)를 계산 */
  viewport(reveal, zoom = 1, priceOffset = 0) {
    const visible = this.view.visibleBars / zoom;
    const right = reveal + this.layout.rightGap;
    const left = right - visible;
    const range = this._priceRange(left, right, reveal);
    let lo = range.lo + priceOffset;
    let hi = range.hi + priceOffset;

    // 손절·익절선처럼 화면에 반드시 들어와야 하는 가격을 강제로 포함시킨다
    const inc = this.view.include;
    if (inc && inc.length) {
      const pad = (hi - lo) * 0.06;
      for (const p of inc) {
        if (p - pad < lo) lo = p - pad;
        if (p + pad > hi) hi = p + pad;
      }
    }
    return { left, right, visible, lo, hi };
  }

  _priceRangeRaw(left, right, reveal) {
    let lo = Infinity;
    let hi = -Infinity;
    const a = Math.max(0, Math.floor(left));
    const b = Math.min(this.bars.length - 1, Math.ceil(Math.min(right, reveal)));
    for (let i = a; i <= b; i++) {
      const bar = this.bars[i];
      if (!bar) continue;
      if (i > reveal - 1) {
        const f = formingBar(bar, reveal - i);
        if (f.h > hi) hi = f.h;
        if (f.l < lo) lo = f.l;
      } else {
        if (bar.h > hi) hi = bar.h;
        if (bar.l < lo) lo = bar.l;
      }
    }
    if (!isFinite(lo) || !isFinite(hi)) {
      const c = this.bars[0]?.c ?? 100;
      lo = c * 0.995;
      hi = c * 1.005;
    }
    const pad = (hi - lo) * this.view.pricePad + 1e-6;
    // 아래쪽 여백을 조금 더 줘서 거래량/시간축과 붙지 않게 한다
    return { lo: lo - pad * 1.15, hi: hi + pad };
  }

  /**
   * 가격축이 툭툭 튀지 않도록, 최근 프레임들의 목표 범위를 가중평균한다.
   * 상태를 저장하지 않고 과거 목표값을 직접 다시 계산하므로 스크럽에도 안전하다.
   */
  _priceRange(left, right, reveal) {
    const N = 20;
    const stepBars = 0.34; // 약 0.5초 분량의 리빌 변화폭
    let wsum = 0;
    let lo = 0;
    let hi = 0;
    for (let k = 0; k < N; k++) {
      const back = k * stepBars;
      const r = Math.max(1, reveal - back);
      const rt = r + this.layout.rightGap;
      const lt = rt - (right - left);
      const raw = this._priceRangeRaw(lt, rt, r);
      const w = Math.exp(-k / 6);
      lo += raw.lo * w;
      hi += raw.hi * w;
      wsum += w;
    }
    return { lo: lo / wsum, hi: hi / wsum };
  }

  makeScale(vp) {
    const p = this.plot;
    const x = (i) => p.x + ((i - vp.left) / (vp.right - vp.left)) * p.w;
    const y = (price) => p.bottom - ((price - vp.lo) / (vp.hi - vp.lo)) * p.h;
    const barW = (p.w / (vp.right - vp.left)) * 0.66;
    return { x, y, barW, vp, plot: p };
  }

  /* ---------------- 그리기 ---------------- */

  drawBackground() {
    const { ctx, theme } = this;
    if (theme.transparent) {
      ctx.clearRect(0, 0, this.w, this.h);
      return;
    }
    if (theme.flat || !theme.bgGradient) {
      ctx.fillStyle = theme.bg;
      ctx.fillRect(0, 0, this.w, this.h);
      return;
    }
    const g = ctx.createLinearGradient(0, 0, this.w * 0.35, this.h);
    g.addColorStop(0, theme.bgGradient[0]);
    g.addColorStop(1, theme.bgGradient[1]);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, this.w, this.h);

    // 아주 옅은 비네트
    const v = ctx.createRadialGradient(
      this.w / 2, this.h / 2, this.h * 0.25,
      this.w / 2, this.h / 2, this.h * 0.95,
    );
    v.addColorStop(0, 'rgba(0,0,0,0)');
    v.addColorStop(1, 'rgba(0,0,0,0.38)');
    ctx.fillStyle = v;
    ctx.fillRect(0, 0, this.w, this.h);
  }

  priceTicks(vp, target = 7) {
    const range = vp.hi - vp.lo;
    const rough = range / target;
    const mag = 10 ** Math.floor(Math.log10(rough));
    const norm = rough / mag;
    const step = (norm > 5 ? 10 : norm > 2.5 ? 5 : norm > 1.5 ? 2.5 : norm > 1.2 ? 2 : 1) * mag;
    const out = [];
    for (let v = Math.ceil(vp.lo / step) * step; v <= vp.hi; v += step) out.push(v);
    return { ticks: out, step };
  }

  drawGrid(s, alpha = 1) {
    const { ctx, theme } = this;
    const p = this.plot;
    ctx.save();
    ctx.globalAlpha = alpha;
    const { ticks } = this.priceTicks(s.vp);
    ctx.strokeStyle = theme.grid;
    ctx.lineWidth = 1;
    for (const v of ticks) {
      const yy = Math.round(s.y(v)) + 0.5;
      ctx.beginPath();
      ctx.moveTo(p.x, yy);
      ctx.lineTo(p.right, yy);
      ctx.stroke();
    }
    // 세로 그리드: 12바 간격
    const step = 12;
    const from = Math.ceil(s.vp.left / step) * step;
    for (let i = from; i <= s.vp.right; i += step) {
      const xx = Math.round(s.x(i)) + 0.5;
      ctx.beginPath();
      ctx.moveTo(xx, p.y);
      ctx.lineTo(xx, p.bottom);
      ctx.stroke();
    }
    ctx.restore();
  }

  drawAxes(s, reveal, alpha = 1) {
    const { ctx, theme } = this;
    const p = this.plot;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = theme.axisText;
    ctx.font = `500 24px ${theme.mono}`;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    const { ticks, step } = this.priceTicks(s.vp);
    const dec = step < 1 ? 2 : step < 10 ? 1 : 0;
    for (const v of ticks) {
      ctx.fillText(v.toFixed(dec), p.right + 18, s.y(v));
    }

    // 시간축
    ctx.textAlign = 'center';
    ctx.font = `500 22px ${theme.mono}`;
    const tstep = 12;
    const from = Math.ceil(s.vp.left / tstep) * tstep;
    for (let i = from; i <= Math.min(s.vp.right, this.bars.length - 1); i += tstep) {
      const bar = this.bars[Math.round(i)];
      if (!bar) continue;
      const tx = s.x(i);
      if (tx < p.x + 26 || tx > p.right - 26) continue;
      const d = new Date(bar.t);
      const hh = String(d.getUTCHours()).padStart(2, '0');
      const mm = String(d.getUTCMinutes()).padStart(2, '0');
      ctx.fillText(`${hh}:${mm}`, tx, p.bottom + 36);
    }

    // 축 선
    ctx.strokeStyle = theme.gridStrong;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(p.x, p.bottom + 0.5);
    ctx.lineTo(p.right, p.bottom + 0.5);
    ctx.moveTo(p.right + 0.5, p.y);
    ctx.lineTo(p.right + 0.5, p.bottom);
    ctx.stroke();
    ctx.restore();
  }

  /** 플롯 영역 밖으로 그림이 새지 않게 자른다 */
  clipPlot(ctx = this.ctx) {
    const p = this.plot;
    ctx.beginPath();
    ctx.rect(p.x, p.y, p.w, p.h);
    ctx.clip();
  }

  drawMAs(s, reveal, alpha = 1) {
    if (!this.overlays.length) return;
    const { ctx } = this;
    ctx.save();
    this.clipPlot(ctx);
    ctx.globalAlpha = alpha;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    for (const ov of this.overlays) {
      ctx.strokeStyle = ov.color ?? this.theme.ma ?? 'rgba(120,170,255,0.75)';
      ctx.lineWidth = ov.width ?? 3;
      ctx.beginPath();
      let started = false;
      const end = Math.min(this.bars.length - 1, Math.floor(reveal) - 1);
      for (let i = Math.max(0, Math.floor(s.vp.left)); i <= end; i++) {
        const v = ov.values[i];
        if (v == null) continue;
        const xx = s.x(i);
        const yy = s.y(v);
        if (!started) {
          ctx.moveTo(xx, yy);
          started = true;
        } else ctx.lineTo(xx, yy);
      }
      ctx.stroke();
    }
    ctx.restore();
  }

  drawCandles(s, reveal, alpha = 1) {
    const { ctx, theme } = this;
    ctx.save();
    this.clipPlot(ctx);
    ctx.globalAlpha = alpha;
    const start = Math.max(0, Math.floor(s.vp.left) - 1);
    const end = Math.min(this.bars.length - 1, Math.floor(reveal));
    const w = Math.max(2, s.barW);

    for (let i = start; i <= end; i++) {
      const raw = this.bars[i];
      if (!raw) continue;
      const p = reveal - i;
      if (p <= 0) continue;
      const bar = p < 1 ? formingBar(raw, p) : raw;
      const bull = bar.c >= bar.o;
      const color = bull ? theme.up : theme.down;

      const x = s.x(i);
      const yo = s.y(bar.o);
      const yc = s.y(bar.c);
      const yh = s.y(bar.h);
      const yl = s.y(bar.l);

      // 심지
      ctx.strokeStyle = color;
      ctx.lineWidth = Math.max(1.5, w * 0.13);
      ctx.beginPath();
      ctx.moveTo(Math.round(x) + 0.5, yh);
      ctx.lineTo(Math.round(x) + 0.5, yl);
      ctx.stroke();

      // 몸통
      const top = Math.min(yo, yc);
      const bh = Math.max(2, Math.abs(yc - yo));
      ctx.fillStyle = bull ? theme.upFill : theme.downFill;
      ctx.fillRect(Math.round(x - w / 2), Math.round(top), Math.round(w), Math.round(bh));

      // 형성 중인 캔들은 살짝 발광 (밝은 테마에서는 지저분해지므로 생략)
      if (bar.forming && !theme.flat) {
        ctx.save();
        ctx.shadowColor = color;
        ctx.shadowBlur = 26;
        ctx.fillRect(Math.round(x - w / 2), Math.round(top), Math.round(w), Math.round(bh));
        ctx.restore();
      }
    }
    ctx.restore();
  }

  /** 마지막(형성 중인) 캔들의 현재가 정보. 그리지는 않는다. */
  lastInfo(s, reveal) {
    const idx = Math.min(this.bars.length - 1, Math.floor(reveal));
    const raw = this.bars[idx];
    if (!raw) return null;
    const p = clamp(reveal - idx, 0, 1);
    const bar = p < 1 ? formingBar(raw, p) : raw;
    const bull = bar.c >= bar.o;
    return {
      price: bar.c,
      y: s.y(bar.c),
      x: s.x(idx),
      color: bull ? this.theme.up : this.theme.down,
      bar,
      index: idx,
    };
  }

  /** 현재가 점선 + 오른쪽 가격 태그 */
  drawLastPrice(s, reveal, alpha = 1) {
    const { ctx, theme } = this;
    const idx = Math.min(this.bars.length - 1, Math.floor(reveal));
    const raw = this.bars[idx];
    if (!raw) return null;
    const p = clamp(reveal - idx, 0, 1);
    const bar = p < 1 ? formingBar(raw, p) : raw;
    const bull = bar.c >= bar.o;
    const color = bull ? theme.up : theme.down;
    const y = s.y(bar.c);

    ctx.save();
    ctx.globalAlpha = alpha;
    if (y < this.plot.y - 4 || y > this.plot.bottom + 4) {
      ctx.restore();
      return { price: bar.c, y, x: s.x(idx), color, bar, offscreen: true };
    }
    ctx.setLineDash([8, 8]);
    ctx.strokeStyle = color;
    ctx.globalAlpha = alpha * 0.55;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(this.plot.x, Math.round(y) + 0.5);
    ctx.lineTo(this.plot.right, Math.round(y) + 0.5);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.globalAlpha = alpha;
    const label = bar.c.toFixed(2);
    ctx.font = `600 25px ${theme.mono}`;
    const tw = ctx.measureText(label).width;
    const bw = tw + 30;
    const bx = this.plot.right + 8;
    ctx.fillStyle = color;
    roundRect(ctx, bx, y - 20, bw, 40, 7);
    ctx.fill();
    ctx.fillStyle = '#08101A';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, bx + bw / 2, y + 1);
    ctx.restore();
    return { price: bar.c, y, x: s.x(idx), color, bar };
  }

  /**
   * 한 프레임 전체를 그린다.
   * @returns {{scale, viewport, last}} 오버레이 레이어가 쓸 좌표 정보
   */
  frame({ reveal, zoom = 1, priceOffset = 0, alpha = 1, showGrid = true, showAxes = true, showLast = true,
          showCandles = true, showMAs = true }) {
    const vp = this.viewport(reveal, zoom, priceOffset);
    const s = this.makeScale(vp);
    this.drawBackground();
    if (showGrid) this.drawGrid(s, alpha * 1);
    /*  showMAs / showCandles 는 레이어를 따로 렌더할 때 쓴다.
        프리미어에 층으로 쌓으려면 '캔들만' · '이평선만' 클립이 각각 필요하다.
        좌표계(scale/viewport)는 그리지 않아도 그대로 계산되므로,
        차트를 다 끄고 오버레이 레이어만 렌더해도 위치가 어긋나지 않는다.  */
    if (showMAs) this.drawMAs(s, reveal, alpha);
    if (showCandles) this.drawCandles(s, reveal, alpha);
    let last = this.lastInfo(s, reveal);
    if (showLast) last = this.drawLastPrice(s, reveal, alpha) ?? last;
    if (showAxes) this.drawAxes(s, reveal, alpha);
    return { scale: s, viewport: vp, last };
  }
}

export function roundRect(ctx, x, y, w, h, r) {
  const rr = Math.min(r, Math.abs(w) / 2, Math.abs(h) / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}
