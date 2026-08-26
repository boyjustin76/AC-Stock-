/**
 * 컷씬 오버레이 레이어.
 *
 * 씬 정의(scenes/*.js)에 선언된 { type: 'titleCard', ... } 객체를 받아서 그린다.
 * 새 연출이 필요하면 여기에 타입을 하나 추가하면 된다.
 */
import { cue, clamp, lerp, Ease, span, fmtNum, fmtSigned } from './anim.js';
import { roundRect } from './chart.js';

/* ------------------------------------------------------------------ */
/* 공통 헬퍼                                                            */
/* ------------------------------------------------------------------ */

function withAlpha(ctx, a, fn) {
  ctx.save();
  ctx.globalAlpha *= a;
  fn();
  ctx.restore();
}

function hexA(hex, a) {
  const h = hex.replace('#', '');
  const n = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const r = parseInt(n.slice(0, 2), 16);
  const g = parseInt(n.slice(2, 4), 16);
  const b = parseInt(n.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

/** 가격 지정 방식: 숫자면 절대가, {bar:i} 면 해당 캔들 종가, {pct:0.3} 이면 화면 비율 */
function resolvePrice(v, env) {
  if (typeof v === 'number') return v;
  if (v && typeof v === 'object') {
    if (v.bar != null) {
      const b = env.chart.bars[v.bar];
      const base = b ? b[v.field ?? 'c'] : env.viewport.lo;
      return base + (v.offset ?? 0);
    }
    if (v.pct != null) return lerp(env.viewport.lo, env.viewport.hi, v.pct);
    if (v.last != null) return (env.last?.price ?? env.viewport.lo) + (v.offset ?? 0);
  }
  return env.viewport.lo;
}

function textBox(ctx, text, x, y, opt = {}) {
  const padX = opt.padX ?? 16;
  const padY = opt.padY ?? 9;
  const w = ctx.measureText(text).width + padX * 2;
  const h = (opt.h ?? 38) + padY * 0;
  ctx.fillStyle = opt.bg;
  const bx = opt.align === 'right' ? x - w : opt.align === 'center' ? x - w / 2 : x;
  roundRect(ctx, bx, y - h / 2, w, h, opt.radius ?? 7);
  ctx.fill();
  if (opt.stroke) {
    ctx.strokeStyle = opt.stroke;
    ctx.lineWidth = opt.strokeWidth ?? 2;
    ctx.stroke();
  }
  ctx.fillStyle = opt.color;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, bx + w / 2, y + 1);
  return { x: bx, y: y - h / 2, w, h };
}

/** 글자가 아래에서 밀려 올라오며 나타나는 연출 */
function riseText(ctx, text, x, y, p, opt = {}) {
  const dy = (1 - p) * (opt.rise ?? 26);
  ctx.save();
  ctx.globalAlpha *= clamp(p * 1.2);
  ctx.translate(0, dy);
  if (opt.blur) ctx.filter = `blur(${(1 - p) * opt.blur}px)`;
  ctx.fillText(text, x, y);
  ctx.restore();
}

/* ------------------------------------------------------------------ */
/* 레이어 구현                                                          */
/* ------------------------------------------------------------------ */

const LAYERS = {
  /** 화면 전체 타이틀 카드 (인트로/챕터 전환) */
  titleCard(ctx, L, env) {
    const { v } = cue(env.t, L, { inEase: Ease.outQuart });
    if (v <= 0.001) return;
    const { w, h, theme } = env;
    const cx = L.x ?? w / 2;
    const baseY = L.y ?? h * 0.46;
    const align = L.align ?? 'center';

    withAlpha(ctx, v, () => {
      if (L.scrim !== false) {
        const g = ctx.createLinearGradient(0, 0, 0, h);
        g.addColorStop(0, `rgba(4,7,12,${0.86 * (L.scrimStrength ?? 1)})`);
        g.addColorStop(0.55, `rgba(4,7,12,${0.72 * (L.scrimStrength ?? 1)})`);
        g.addColorStop(1, `rgba(4,7,12,${0.9 * (L.scrimStrength ?? 1)})`);
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);
      }
      ctx.textAlign = align;
      ctx.textBaseline = 'alphabetic';

      let y = baseY;
      if (L.kicker) {
        ctx.font = `700 30px ${theme.font}`;
        ctx.letterSpacing = '7px';
        ctx.fillStyle = L.kickerColor ?? theme.accent;
        riseText(ctx, L.kicker, cx, y - 108, span(env.t, L.in[0], L.in[0] + 0.5, Ease.outCubic));
        ctx.letterSpacing = '0px';
      }
      ctx.font = `800 ${L.size ?? 108}px ${theme.font}`;
      ctx.fillStyle = L.color ?? theme.text;
      const lines = Array.isArray(L.title) ? L.title : [L.title];
      lines.forEach((line, i) => {
        const p = span(env.t, L.in[0] + 0.12 + i * 0.14, L.in[0] + 0.12 + i * 0.14 + 0.7, Ease.outQuart);
        riseText(ctx, line, cx, y + i * (L.lineHeight ?? 124), p, { rise: 46, blur: 10 });
      });
      y += (lines.length - 1) * (L.lineHeight ?? 124);

      if (L.subtitle) {
        ctx.font = `500 ${L.subSize ?? 38}px ${theme.font}`;
        ctx.fillStyle = L.subColor ?? theme.textDim;
        const p = span(env.t, L.in[0] + 0.4, L.in[0] + 1.1, Ease.outCubic);
        riseText(ctx, L.subtitle, cx, y + (L.subGap ?? 74), p, { rise: 22 });
      }
      if (L.rule !== false) {
        const p = span(env.t, L.in[0] + 0.25, L.in[0] + 0.95, Ease.outExpo);
        const rw = (L.ruleWidth ?? 200) * p;
        ctx.fillStyle = L.kickerColor ?? theme.accent;
        ctx.fillRect(cx - rw / 2, y + (L.ruleGap ?? 120), rw, 5);
      }
    });
  },

  /** 하단 자막 / 로어서드 */
  caption(ctx, L, env) {
    const { v } = cue(env.t, L);
    if (v <= 0.001) return;
    const { w, h, theme } = env;
    const x = L.x ?? 96;
    const y = L.y ?? h - 132;
    withAlpha(ctx, v, () => {
      ctx.textAlign = 'left';
      ctx.textBaseline = 'alphabetic';
      const barH = L.title ? 96 : 58;
      ctx.fillStyle = L.accent ?? theme.accent;
      ctx.fillRect(x, y - barH + 14, 6, barH * clamp(v * 1.4));
      if (L.title) {
        ctx.font = `700 30px ${theme.font}`;
        ctx.fillStyle = L.accent ?? theme.accent;
        riseText(ctx, L.title, x + 24, y - 52, clamp(v * 1.3), { rise: 14 });
      }
      ctx.font = `600 ${L.size ?? 44}px ${theme.font}`;
      ctx.fillStyle = L.color ?? theme.text;
      riseText(ctx, L.text, x + 24, y, clamp(v * 1.1), { rise: 20 });
    });
  },

  /** 좌상단 종목 HUD (심볼 / 현재가 / 등락) */
  hud(ctx, L, env) {
    const { v } = cue(env.t, L);
    if (v <= 0.001 || !env.last) return;
    const { theme } = env;
    const x = L.x ?? 64;
    const y = L.y ?? 52;
    const base = L.basePrice ?? env.chart.bars[0].o;
    const price = env.last.price;
    const diff = price - base;
    const pct = (diff / base) * 100;
    const col = diff >= 0 ? theme.up : theme.down;

    withAlpha(ctx, v, () => {
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.font = `800 34px ${theme.font}`;
      ctx.fillStyle = theme.text;
      ctx.fillText(L.symbol ?? 'NQ', x, y);
      const sw = ctx.measureText(L.symbol ?? 'NQ').width;

      ctx.font = `500 24px ${theme.font}`;
      ctx.fillStyle = theme.textDim;
      ctx.fillText(L.name ?? '나스닥 100 선물', x + sw + 16, y + 2);

      ctx.font = `600 22px ${theme.mono}`;
      ctx.fillStyle = 'rgba(233,240,255,0.34)';
      ctx.fillText(L.tf ?? '5m', x + sw + 16 + ctx.measureText(L.name ?? '나스닥 100 선물').width + 20, y + 2);

      ctx.font = `700 46px ${theme.mono}`;
      ctx.fillStyle = col;
      ctx.fillText(fmtNum(price, 2), x, y + 54);
      const pw = ctx.measureText(fmtNum(price, 2)).width;
      ctx.font = `600 26px ${theme.mono}`;
      ctx.fillText(`${fmtSigned(diff, 2)}  (${fmtSigned(pct, 2)}%)`, x + pw + 20, y + 56);
    });
  },

  /** 수평 가격선 + 라벨 (지지 / 저항 / 진입가) */
  hline(ctx, L, env) {
    const { v } = cue(env.t, L);
    if (v <= 0.001) return;
    const { theme, scale, chart } = env;
    const price = resolvePrice(L.price, env);
    const y = scale.y(price);
    const p = chart.plot;
    const grow = span(env.t, L.in[0], L.in[0] + (L.growDur ?? 0.6), Ease.outExpo);
    const color = L.color ?? theme.accent;

    withAlpha(ctx, v, () => {
      ctx.strokeStyle = color;
      ctx.lineWidth = L.width ?? 3;
      if (L.dash !== false) ctx.setLineDash(L.dash ?? [14, 10]);
      ctx.beginPath();
      const x0 = L.fromRight ? p.right : p.x;
      const x1 = L.fromRight ? p.right - p.w * grow : p.x + p.w * grow;
      ctx.moveTo(x0, Math.round(y) + 0.5);
      ctx.lineTo(x1, Math.round(y) + 0.5);
      ctx.stroke();
      ctx.setLineDash([]);

      if (L.label) {
        const lp = span(env.t, L.in[0] + (L.labelDelay ?? 0.35), L.in[0] + (L.labelDelay ?? 0.35) + 0.4, Ease.outBack);
        ctx.save();
        ctx.globalAlpha *= clamp(lp);
        ctx.font = `700 27px ${theme.font}`;
        const lx = L.labelX ?? p.x + 22;
        textBox(ctx, L.label, lx, y, {
          bg: L.labelBg ?? 'rgba(9,14,22,0.94)',
          stroke: hexA(color, 0.9),
          color,
          h: 46,
          padX: 20,
          align: L.labelAlign ?? 'left',
        });
        ctx.restore();
      }
      if (L.priceTag) {
        ctx.font = `600 25px ${theme.mono}`;
        textBox(ctx, price.toFixed(2), p.right + 8, y, {
          bg: color, color: '#08101A', h: 40, padX: 15, align: 'left',
        });
      }
    });
  },

  /** 가격 밴드 (매물대 / 박스권 / 목표 구간) */
  zone(ctx, L, env) {
    const { v } = cue(env.t, L);
    if (v <= 0.001) return;
    const { theme, scale, chart } = env;
    const a = scale.y(resolvePrice(L.from, env));
    const b = scale.y(resolvePrice(L.to, env));
    const top = Math.min(a, b);
    const hgt = Math.abs(b - a);
    const p = chart.plot;
    const grow = span(env.t, L.in[0], L.in[0] + (L.growDur ?? 0.7), Ease.outExpo);
    const color = L.color ?? theme.warn;

    withAlpha(ctx, v, () => {
      const w = p.w * grow;
      ctx.save();
      env.chart.clipPlot(ctx);
      ctx.fillStyle = hexA(color, L.opacity ?? 0.13);
      ctx.fillRect(p.x, top, w, hgt);
      ctx.strokeStyle = hexA(color, 0.6);
      ctx.lineWidth = 2;
      ctx.setLineDash([10, 8]);
      ctx.strokeRect(p.x, Math.round(top) + 0.5, w, Math.round(hgt));
      ctx.setLineDash([]);
      ctx.restore();
      if (L.label) {
        const lp = span(env.t, L.in[0] + 0.35, L.in[0] + 0.8, Ease.outBack);
        ctx.save();
        ctx.globalAlpha *= clamp(lp);
        ctx.font = `700 27px ${theme.font}`;
        textBox(ctx, L.label, L.labelX ?? p.x + 22, top + hgt / 2, {
          bg: 'rgba(9,14,22,0.94)', stroke: hexA(color, 0.85), color, h: 46, padX: 20,
          align: L.labelAlign ?? 'left',
        });
        ctx.restore();
      }
    });
  },

  /** 진입 마커 (화살표 + 라벨) */
  marker(ctx, L, env) {
    const { v } = cue(env.t, L);
    if (v <= 0.001) return;
    const { theme, scale } = env;
    const bar = env.chart.bars[L.bar];
    if (!bar) return;
    const long = (L.dir ?? 'long') === 'long';
    const price = L.price ?? (long ? bar.l : bar.h);
    const x = scale.x(L.bar);
    const gap = L.gap ?? 46;
    const y = scale.y(price) + (long ? gap : -gap);
    const color = L.color ?? (long ? theme.long : theme.short);
    const pop = span(env.t, L.in[0], L.in[0] + 0.45, Ease.outBack);
    const size = (L.size ?? 26) * pop;

    withAlpha(ctx, v, () => {
      // 진입 시점 강조 세로선
      ctx.strokeStyle = hexA(color, 0.35);
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 8]);
      ctx.beginPath();
      ctx.moveTo(Math.round(x) + 0.5, env.chart.plot.y);
      ctx.lineTo(Math.round(x) + 0.5, env.chart.plot.bottom);
      ctx.stroke();
      ctx.setLineDash([]);

      // 펄스 링
      const ring = (env.t - L.in[0]) % 1.4 / 1.4;
      if (env.t > L.in[0] && L.pulse !== false) {
        ctx.strokeStyle = hexA(color, 0.5 * (1 - ring));
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(x, y, size * (0.9 + ring * 2.4), 0, Math.PI * 2);
        ctx.stroke();
      }

      // 삼각형 화살표
      ctx.fillStyle = color;
      ctx.shadowColor = color;
      ctx.shadowBlur = 24;
      ctx.beginPath();
      const d = long ? -1 : 1;
      ctx.moveTo(x, y + d * size);
      ctx.lineTo(x - size * 0.86, y - d * size * 0.72);
      ctx.lineTo(x + size * 0.86, y - d * size * 0.72);
      ctx.closePath();
      ctx.fill();
      ctx.shadowBlur = 0;

      if (L.label) {
        const lp = span(env.t, L.in[0] + 0.2, L.in[0] + 0.65, Ease.outBack);
        ctx.save();
        ctx.globalAlpha *= clamp(lp);
        ctx.font = `800 28px ${theme.font}`;
        textBox(ctx, L.label, x, y + (long ? 62 : -62), {
          bg: color, color: '#08101A', h: 46, padX: 20, align: 'center',
        });
        ctx.restore();
      }
    });
  },

  /**
   * 손절 / 익절 박스.
   * 진입가 기준으로 위/아래 박스가 좌→우로 펼쳐진다.
   */
  tradeBox(ctx, L, env) {
    const { v } = cue(env.t, L);
    if (v <= 0.001) return;
    const { theme, scale, chart } = env;
    const entry = resolvePrice(L.entry, env);
    const tp = resolvePrice(L.tp, env);
    const sl = resolvePrice(L.sl, env);
    const x0 = scale.x(L.fromBar ?? 0);
    const x1 = L.toBar != null ? scale.x(L.toBar) : chart.plot.right;
    const grow = span(env.t, L.in[0], L.in[0] + (L.growDur ?? 0.75), Ease.outExpo);
    const w = (x1 - x0) * grow;
    const yE = scale.y(entry);
    const yT = scale.y(tp);
    const yS = scale.y(sl);

    withAlpha(ctx, v, () => {
      ctx.save();
      chart.clipPlot(ctx);
      // 익절 영역
      ctx.fillStyle = hexA(theme.tp, 0.16);
      ctx.fillRect(x0, Math.min(yE, yT), w, Math.abs(yE - yT));
      // 손절 영역
      ctx.fillStyle = hexA(theme.sl, 0.16);
      ctx.fillRect(x0, Math.min(yE, yS), w, Math.abs(yE - yS));

      ctx.lineWidth = 2.5;
      for (const [y, c] of [[yT, theme.tp], [yS, theme.sl]]) {
        ctx.strokeStyle = hexA(c, 0.9);
        ctx.beginPath();
        ctx.moveTo(x0, Math.round(y) + 0.5);
        ctx.lineTo(x0 + w, Math.round(y) + 0.5);
        ctx.stroke();
      }
      ctx.strokeStyle = hexA(theme.text, 0.75);
      ctx.setLineDash([12, 8]);
      ctx.beginPath();
      ctx.moveTo(x0, Math.round(yE) + 0.5);
      ctx.lineTo(x0 + w, Math.round(yE) + 0.5);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();

      if (grow > 0.55) {
        const lp = span(env.t, L.in[0] + 0.5, L.in[0] + 0.95, Ease.outCubic);
        ctx.save();
        ctx.globalAlpha *= clamp(lp);
        ctx.font = `700 26px ${theme.font}`;
        const lx = x0 + w - 18;
        const rr = L.rr ?? Math.abs(tp - entry) / Math.max(0.01, Math.abs(entry - sl));
        textBox(ctx, L.tpLabel ?? `익절 ${tp.toFixed(2)}`, lx, yT, {
          bg: theme.tp, color: '#08101A', h: 42, padX: 16, align: 'right',
        });
        textBox(ctx, L.slLabel ?? `손절 ${sl.toFixed(2)}`, lx, yS, {
          bg: theme.sl, color: '#08101A', h: 42, padX: 16, align: 'right',
        });
        ctx.font = `700 25px ${theme.font}`;
        textBox(ctx, L.entryLabel ?? `진입 ${entry.toFixed(2)}`, lx, yE, {
          bg: 'rgba(233,240,255,0.92)', color: '#08101A', h: 40, padX: 16, align: 'right',
        });
        if (L.showRR !== false) {
          ctx.font = `800 30px ${theme.font}`;
          // 진입선과 겹치지 않게 익절 영역 한가운데에 놓는다
          const yRR = L.rrY ?? (yE + yT) / 2;
          textBox(ctx, `손익비 1 : ${rr.toFixed(1)}`, L.rrX ?? x0 + 20, yRR, {
            bg: 'rgba(9,14,23,0.94)', stroke: hexA(theme.accent, 0.8), color: theme.accent,
            h: 54, padX: 24, align: 'left',
          });
        }
        ctx.restore();
      }
    });
  },

  /** 숫자 카운터 패널 (수익금 / 수익률 / 포인트) */
  counter(ctx, L, env) {
    const { v } = cue(env.t, L);
    if (v <= 0.001) return;
    const { theme } = env;
    const dur = L.dur ?? 1.6;
    const t0 = L.countFrom ?? L.in[0];
    const p = span(env.t, t0, t0 + dur, Ease.outExpo);
    let value = lerp(L.from ?? 0, L.to ?? 0, p);
    if (L.track === 'last' && env.last) value = env.last.price;

    const dec = L.decimals ?? 2;
    const sign = L.signed ? (value < 0 ? '-' : '+') : '';
    const text = sign + (L.prefix ?? '') + fmtNum(Math.abs(value), dec) + (L.suffix ?? '');

    const size = L.size ?? 88;
    const labelSize = L.labelSize ?? 26;
    const color = L.color ?? (value >= 0 ? theme.up : theme.down);

    // 패널 크기는 내용에 맞춰 잡는다
    ctx.font = `800 ${size}px ${theme.mono}`;
    const numW = ctx.measureText(text).width;
    ctx.font = `700 ${labelSize}px ${theme.font}`;
    ctx.letterSpacing = '3px';
    const labW = L.label ? ctx.measureText(L.label).width : 0;
    ctx.letterSpacing = '0px';

    const padX = L.padX ?? 36;
    const padTop = 26;
    const gap = 12;
    const padBottom = 28;
    const boxW = Math.max(numW, labW) + padX * 2;
    const boxH = padTop + (L.label ? labelSize + gap : 0) + size * 0.8 + padBottom;
    // x, y 는 패널의 좌상단. align:'right' 이면 x 를 우측 끝으로 본다.
    const x = (L.align ?? 'left') === 'right' ? (L.x ?? env.w - 96) - boxW : (L.x ?? 96);
    const y = L.y ?? 210;

    withAlpha(ctx, v, () => {
      ctx.translate(0, (1 - v) * 18);
      if (L.panel !== false) {
        ctx.fillStyle = L.panelBg ?? 'rgba(9,14,23,0.95)';
        roundRect(ctx, x, y, boxW, boxH, 18);
        ctx.fill();
        ctx.strokeStyle = hexA(color, 0.35);
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = color;
        roundRect(ctx, x, y + 10, 6, boxH - 20, 3);
        ctx.fill();
      }
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      let ty = y + padTop;
      if (L.label) {
        ctx.font = `700 ${labelSize}px ${theme.font}`;
        ctx.letterSpacing = '3px';
        ctx.fillStyle = theme.textDim;
        ctx.fillText(L.label, x + padX, ty);
        ctx.letterSpacing = '0px';
        ty += labelSize + gap;
      }
      ctx.font = `800 ${size}px ${theme.mono}`;
      ctx.fillStyle = color;
      ctx.shadowColor = hexA(color, 0.45);
      ctx.shadowBlur = 28;
      ctx.fillText(text, x + padX, ty);
    });
  },

  /** 결과 요약 카드 (아웃트로) */
  statCard(ctx, L, env) {
    const { v } = cue(env.t, L);
    if (v <= 0.001) return;
    const { theme, w, h } = env;
    const cw = L.width ?? 720;
    const rows = L.rows ?? [];
    const rowH = L.rowH ?? 76;
    const headH = L.title ? 108 : 34;
    const ch = headH + rows.length * rowH + 34;
    const x = L.x ?? (w - cw) / 2;
    const y = L.y ?? (h - ch) / 2;

    withAlpha(ctx, v, () => {
      if (L.scrim !== false) {
        ctx.fillStyle = 'rgba(4,7,12,0.72)';
        ctx.fillRect(0, 0, w, h);
      }
      const rise = (1 - v) * 40;
      ctx.translate(0, rise);
      ctx.fillStyle = 'rgba(13,19,30,0.96)';
      roundRect(ctx, x, y, cw, ch, 22);
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.1)';
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillStyle = L.accent ?? theme.accent;
      roundRect(ctx, x, y, cw, 8, 4);
      ctx.fill();

      ctx.textBaseline = 'middle';
      if (L.title) {
        ctx.textAlign = 'left';
        ctx.font = `800 42px ${theme.font}`;
        ctx.fillStyle = theme.text;
        ctx.fillText(L.title, x + 40, y + 66);
        if (L.badge) {
          ctx.font = `700 26px ${theme.font}`;
          textBox(ctx, L.badge, x + cw - 40, y + 66, {
            bg: hexA(L.badgeColor ?? theme.up, 0.18),
            stroke: hexA(L.badgeColor ?? theme.up, 0.9),
            color: L.badgeColor ?? theme.up,
            h: 46, padX: 20, align: 'right',
          });
        }
      }
      rows.forEach((r, i) => {
        const ry = y + headH + rowH * i + rowH / 2;
        const rp = span(env.t, L.in[0] + 0.25 + i * 0.12, L.in[0] + 0.25 + i * 0.12 + 0.5, Ease.outCubic);
        ctx.save();
        ctx.globalAlpha *= clamp(rp);
        ctx.translate((1 - rp) * 24, 0);
        ctx.strokeStyle = 'rgba(255,255,255,0.06)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x + 40, Math.round(ry + rowH / 2) + 0.5);
        ctx.lineTo(x + cw - 40, Math.round(ry + rowH / 2) + 0.5);
        ctx.stroke();
        ctx.textAlign = 'left';
        ctx.font = `500 32px ${theme.font}`;
        ctx.fillStyle = theme.textDim;
        ctx.fillText(r.k, x + 40, ry);
        ctx.textAlign = 'right';
        ctx.font = `700 36px ${theme.mono}`;
        ctx.fillStyle = r.tone === 'up' ? theme.up : r.tone === 'down' ? theme.down : theme.text;
        ctx.fillText(r.v, x + cw - 40, ry);
        ctx.restore();
      });
    });
  },

  /** 캔들 위에 붙는 자유 라벨 (화살표 지시선 포함) */
  label(ctx, L, env) {
    const { v } = cue(env.t, L);
    if (v <= 0.001) return;
    const { theme, scale } = env;
    const price = resolvePrice(L.price, env);
    const px = scale.x(L.bar ?? 0);
    const py = scale.y(price);
    const dx = L.dx ?? 0;
    const dy = L.dy ?? -110;
    const color = L.color ?? theme.accent;
    const grow = span(env.t, L.in[0], L.in[0] + 0.45, Ease.outCubic);

    withAlpha(ctx, v, () => {
      ctx.strokeStyle = hexA(color, 0.8);
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(px + dx * grow, py + dy * grow);
      ctx.stroke();
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(px, py, 6, 0, Math.PI * 2);
      ctx.fill();
      const lp = span(env.t, L.in[0] + 0.25, L.in[0] + 0.7, Ease.outBack);
      ctx.save();
      ctx.globalAlpha *= clamp(lp);
      ctx.font = `700 30px ${theme.font}`;
      textBox(ctx, L.text, px + dx, py + dy, {
        bg: 'rgba(8,14,22,0.92)', stroke: hexA(color, 0.85), color: theme.text,
        h: 52, padX: 22, align: L.align ?? 'center',
      });
      ctx.restore();
    });
  },

  /** 컷 전환용 플래시 / 와이프 */
  flash(ctx, L, env) {
    const p = span(env.t, L.at, L.at + (L.dur ?? 0.3), Ease.linear);
    if (p <= 0 || p >= 1) return;
    const a = Math.sin(p * Math.PI) * (L.strength ?? 0.85);
    ctx.save();
    ctx.globalAlpha = a;
    ctx.fillStyle = L.color ?? '#FFFFFF';
    ctx.fillRect(0, 0, env.w, env.h);
    ctx.restore();
  },

  /** 워터마크 / 채널명 */
  watermark(ctx, L, env) {
    const { v } = cue(env.t, L);
    if (v <= 0.001) return;
    const { theme, w, h } = env;
    withAlpha(ctx, v * (L.opacity ?? 0.5), () => {
      ctx.textAlign = L.align ?? 'right';
      ctx.textBaseline = 'middle';
      ctx.font = `700 26px ${theme.font}`;
      ctx.letterSpacing = '4px';
      ctx.fillStyle = theme.text;
      ctx.fillText(L.text ?? '', L.x ?? w - 64, L.y ?? 62);
      ctx.letterSpacing = '0px';
    });
  },

  /** 상/하단 시네마 레터박스 */
  letterbox(ctx, L, env) {
    const { v } = cue(env.t, L);
    if (v <= 0.001) return;
    const bh = (L.height ?? 96) * v;
    ctx.save();
    ctx.fillStyle = L.color ?? '#000';
    ctx.fillRect(0, 0, env.w, bh);
    ctx.fillRect(0, env.h - bh, env.w, bh);
    ctx.restore();
  },
};

export function drawLayer(ctx, layer, env) {
  const fn = LAYERS[layer.type];
  if (!fn) {
    console.warn('[layers] 알 수 없는 레이어 타입:', layer.type);
    return;
  }
  ctx.save();
  fn(ctx, layer, env);
  ctx.restore();
}

export const layerTypes = Object.keys(LAYERS);
