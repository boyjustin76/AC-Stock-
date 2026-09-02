/**
 * 차트명가 #12 — 매도 관점 3컷 (컷21~23) · 5분 차트
 *
 * 자막 원본: 차명12롱폼 음성자막-한국어.srt (30.0 격자 반올림)
 *   [정확.srt 재동기 2026-08-31]
 *   컷21 sell-array 319.600~334.533 (14.9333s)  174~182 5분 차트 · 역배열 · 매도 관점으로만
 *   컷22 sell-rsi   334.533~349.300 (14.7667s)  183~190 반등 무시 · RSI 45선 재이탈
 *   컷23 sell-entry 349.300~369.300 (20.0000s)  191~201 음봉 확인 → 매도 진입 → 손절·익절 1:2 → 분할
 *
 * 시장 실측 (seed 68 · find-events):
 *   역배열 유지 전 구간 (s10 < s34)
 *   반등: bar 43~48 (RSI 29 → 61.2) → 45선 하향 재이탈 bar 49 (43.2 · 음봉 o15748→c15687)
 *   진입 = 50번 시가 15687.25 (매도) · 손절 = 48번 고점 15757.25 (R=70) · 익절 1:2 = 15547.25
 *   1:2 도달 bar 65 (저가 15496.3) · 이후 15381.75 까지 하락 지속
 */

import { COLOR } from './cmg12-guide.scenes.js';

const FPS = 60000 / 1001;

const SV = {
  signal: 49,
  entry: 15687.25, // 50번 시가
  stop: 15757.25, // 48번 고점
  get target() { return this.entry - (this.stop - this.entry) * 2; }, // 15,547.25
};

const chartBase = {
  visibleBars: 46,
  pricePad: 0.16,
  showGrid: false,
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 216, padBottom: 162, rightGap: 5 },
  ma: [
    { type: 'sma', period: 10, width: 5, color: COLOR.ma10 },
    { type: 'sma', period: 34, width: 5, color: COLOR.ma34 },
  ],
  rsi: {
    period: 10,
    height: 0.26,
    gap: 26,
    baseline: 50,
    levels: [
      { v: 55, label: '55', color: 'rgba(17,17,17,0.62)', width: 2.5 },
      { v: 45, label: '45', color: 'rgba(17,17,17,0.62)', width: 2.5 },
    ],
    color: COLOR.rsi,
    width: 5,
  },
};

export default {
  title: '차트명가 #12 — 매도 관점 3컷',
  width: 1920,
  height: 1080,
  fps: FPS,
  fpsExpr: '60000/1001',
  theme: { preset: 'chartmyeongga' },

  market: {
    seed: 68,
    base: 15900,
    tick: 0.25,
    vol: 40,
    barMinutes: 5,
    startTime: Date.UTC(2026, 0, 5, 9, 0),
    segments: [
      { type: 'trend', dir: -1, bars: 42, strength: 0.55 },
      { type: 'pullback', dir: -1, bars: 7, strength: 1.0 },
      { type: 'trend', dir: -1, bars: 34, strength: 0.7 },
      { type: 'trend', dir: -1, bars: 14, strength: 0.5 },
    ],
  },

  scenes: [
    /* ── 컷21 5분 차트 — 역배열 확인 (12.5333s) ── */
    {
      id: 'sell-array',
      name: '컷21 역배열 확인 (12.5333s)',
      duration: 14.933333,
      chart: {
        ...chartBase,
        reveal: [{ t: 0, v: 44 }, { t: 14.933333, v: 48, ease: 'linear' }],
      },
      layers: [
        { type: 'cmgBadge', text: '5분 차트', x: 84, y: 262, size: 42, color: COLOR.badge, in: [2.0, 0.3] },
        { type: 'cmgNote', text: '10일선', bar: 40, price: 15628, size: 46, color: COLOR.ma10, in: [4.5, 0.3] },
        { type: 'cmgNote', text: '34일선', bar: 40, price: 15822, size: 46, color: COLOR.ma34, in: [5.7, 0.3] },
        { type: 'cmgTrace', overlay: 0, fromBar: 34, toBar: 46, flatten: 0, width: 14, color: COLOR.ma10, in: [9.5, 0.5] },
        { type: 'cmgTrace', overlay: 1, fromBar: 34, toBar: 46, flatten: 0, width: 14, color: COLOR.ma34, in: [10.0, 0.5] },
        { type: 'cmgNote', text: '역배열 = 하락 추세', bar: 24, price: 15648, size: 52, color: '#111111', in: [10.6, 0.3] },
        { type: 'cmgNote', text: '오직 매도 관점으로만', bar: 30, rsi: 18, size: 44, color: '#E90054', in: [12.9, 0.3] },
      ],
    },

    /* ── 컷22 매도 관점만 — 반등을 기다렸다 45선 재이탈 (17.1333s) ── */
    {
      id: 'sell-rsi',
      name: '컷22 45선 재이탈 (17.1333s)',
      duration: 14.766667,
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 48 },
          { t: 8.5, v: 49.5, ease: 'linear' },
          { t: 12.0, v: 50.2, ease: 'inOutCubic' },
          { t: 14.766667, v: 50.4, ease: 'linear' },
        ],
      },
      layers: [
        /* 컷21 끝 화면 이월(⑧) — 배지·접선·'오직 매도'는 유지, 이름표는 반등
           이야기(1.0~)로 넘어가며 크로스페이드(⑨) */
        { type: 'cmgBadge', text: '5분 차트', x: 84, y: 262, size: 42, color: COLOR.badge, popDur: 0 },
        { type: 'cmgTrace', overlay: 0, fromBar: 34, toBar: 46, flatten: 0, width: 14, color: COLOR.ma10, in: [0, 0] },
        { type: 'cmgTrace', overlay: 1, fromBar: 34, toBar: 46, flatten: 0, width: 14, color: COLOR.ma34, in: [0, 0] },
        { type: 'cmgNote', text: '10일선', bar: 40, price: 15628, size: 46, color: COLOR.ma10, in: [0, 0], out: [0.8, 0.4] },
        { type: 'cmgNote', text: '34일선', bar: 40, price: 15822, size: 46, color: COLOR.ma34, in: [0, 0], out: [0.8, 0.4] },
        { type: 'cmgNote', text: '역배열 = 하락 추세', bar: 24, price: 15648, size: 52, color: '#111111', in: [0, 0], out: [1.5, 0.4] },
        { type: 'cmgNote', text: '오직 매도 관점으로만', bar: 30, rsi: 18, size: 44, color: '#E90054', in: [0, 0] },
        /* 반등이 나와도 매수 고려 X */
        { type: 'cmgCircle', bar: 45.5, price: 15715, rx: 170, ry: 120, width: 10, drawDur: 0.6, in: [1.0, 0.2] },
        { type: 'cmgNote', text: '반등에도 매수 금지', bar: 45, price: 15905, size: 48, color: '#111111', in: [1.7, 0.3] },
        /* RSI — 45선 위로 올라왔다가 다시 하향 이탈 */
        { type: 'cmgCircle', bar: 46, rsi: 58.3, rx: 66, ry: 50, width: 10, color: COLOR.rsi, drawDur: 0.5, in: [9.8, 0.2] },
        { type: 'cmgCircle', bar: 49, rsi: 43.2, rx: 58, ry: 48, width: 10, color: '#E90054', drawDur: 0.5, in: [12.3, 0.2] },
        { type: 'cmgNote', text: '45선 재이탈', bar: 40, rsi: 68, size: 46, color: '#E90054', in: [12.9, 0.3] },
      ],
    },

    /* ── 컷23 음봉 확인 → 매도 진입 → 손절·익절 1:2 → 분할 청산 (20.0333s) ── */
    {
      id: 'sell-entry',
      name: '컷23 매도 진입과 청산 (20.0333s)',
      duration: 20.0,
      chart: {
        ...chartBase,
        include: [SV.stop + 14],
        reveal: [
          /* [v3] 11초 단일 inOutCubic 폭주 완화 — 완만한 가속 후 등속 (1:2 도달 bar 65는 13.8s에 확정, flash 15.7 전 ✓) */
          { t: 0, v: 50.4 },
          { t: 4.0, v: 52, ease: 'linear' },
          { t: 8.0, v: 56, ease: 'inOutQuad' },
          { t: 15.0, v: 68, ease: 'linear' },
          { t: 20.0, v: 74, ease: 'linear' },
        ],
        zoom: [
          { t: 0, v: 1 },
          { t: 3.0, v: 1.28, ease: 'inOutCubic' }, // 음봉 확인 줌인
          { t: 9.5, v: 1.28 },
          { t: 12.5, v: 1.0, ease: 'inOutCubic' }, // 줌아웃 — 하락이 이어진다
        ],
      },
      layers: [
        /* 컷22 끝 화면 이월(⑧) — 접선·문장·원은 줌인(0~3.0)에 실어 보낸다(⑩보충),
           배지는 '손익비'(12.0)와 크로스페이드(⑨) */
        { type: 'cmgBadge', text: '5분 차트', x: 84, y: 262, size: 42, color: COLOR.badge, popDur: 0, out: [11.8, 0.4] },
        { type: 'cmgTrace', overlay: 0, fromBar: 34, toBar: 46, flatten: 0, width: 14, color: COLOR.ma10, in: [0, 0], out: [1.0, 0.5] },
        { type: 'cmgTrace', overlay: 1, fromBar: 34, toBar: 46, flatten: 0, width: 14, color: COLOR.ma34, in: [0, 0], out: [1.0, 0.5] },
        { type: 'cmgNote', text: '오직 매도 관점으로만', bar: 30, rsi: 18, size: 44, color: '#E90054', in: [0, 0], out: [1.0, 0.5] },
        { type: 'cmgCircle', bar: 46, rsi: 58.3, rx: 66, ry: 50, width: 10, color: COLOR.rsi, drawDur: 0, in: [0, 0], out: [1.0, 0.5] },
        { type: 'cmgCircle', bar: 49, rsi: 43.2, rx: 58, ry: 48, width: 10, color: '#E90054', drawDur: 0, in: [0, 0], out: [1.5, 0.4] },
        { type: 'cmgNote', text: '45선 재이탈', bar: 40, rsi: 68, size: 46, color: '#E90054', in: [0, 0], out: [1.5, 0.4] },
        /* 신호 캔들이 음봉으로 확실히 마감 */
        { type: 'cmgCircle', bar: 49, price: 15700, rx: 46, ry: 84, width: 10, drawDur: 0.5, in: [0.8, 0.2], out: [6.6, 0.4] },
        { type: 'cmgNote', text: '음봉 마감', bar: 43, price: 15840, size: 48, color: '#111111', in: [1.7, 0.3], out: [4.2, 0.4] },
        /* 다음 캔들에서 매도 진입 ('매도'는 숏 진입 전용 — 팀장 규칙 ③) */
        { type: 'cmgArrow', bar: 50, price: 15694, dir: 'sell', label: '매도', size: 34, gap: 16, in: [4.7, 0.35] },
        { type: 'cmgLevel', price: SV.entry, fromBar: 48, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0.35, in: [5.2, 0.2] },
        /* 손절 = 직전 캔들 고점 (갈색 박스) */
        {
          type: 'cmgLevel',
          price: SV.stop,
          fromBar: 48,
          fillTo: SV.entry,
          fill: '#FEBABA',
          color: '#9F0000',
          label: '손절',
          labelSize: 38,
          thickness: 13,
          growDur: 0.4,
          in: [7.0, 0.2],
        },
        /* 익절 = 1:2 (초록 박스) */
        {
          type: 'cmgLevel',
          price: SV.target,
          fromBar: 48,
          fillTo: SV.entry,
          fill: '#BAFDC0',
          color: '#14FF36',
          label: '익절',
          labelSize: 38,
          thickness: 13,
          growDur: 0.4,
          in: [11.0, 0.2],
        },
        { type: 'cmgBadge', text: '손익비  1 : 2', x: 84, y: 262, size: 44, color: '#E90054', in: [12.0, 0.3] },
        /* 1:2 도달 — 절반 분할 청산 후 추세를 더 길게 */
        { type: 'flash', at: 15.7, dur: 0.22, strength: 0.4, color: '#14FF36' },
        { type: 'cmgArrow', bar: 65, price: 15500, dir: 'buy', label: '익절 1/2', color: '#0DA82A', size: 32, gap: 16, in: [15.9, 0.35] },
        { type: 'cmgProfit', entry: SV.entry, fromBar: 50, color: '#BAFDC0', opacity: 0.5, in: [17.4, 0.4] },
      ],
    },
  ],
};
