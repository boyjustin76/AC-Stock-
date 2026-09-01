/**
 * 차트명가 #12 — 요약 3컷 (컷24~26) · 매수 시장(seed 161) 재사용
 *
 * 자막 원본: 차명12롱폼 음성자막-한국어.srt (30.0 격자 반올림)
 *   [정확.srt 재동기 2026-08-31]
 *   컷24 recap-1 369.300~379.400 (10.1000s)  194~199 정리 3단계 · 첫째 — 배열로 방향 하나
 *   컷25 recap-2 379.400~389.567 (10.1667s)  200~203 둘째 — 55선 재돌파(양봉)/45선 재이탈(음봉)
 *   컷26 recap-3 389.567~408.833 (19.2667s)  204~214 셋째 — 짧은 손절, 1:2 기계적 청산 · 절제된 매매
 *
 * 수치는 cmg12-buy 와 동일 (진입 15553.25 · 손절 15515.50 · 익절 15628.75).
 * 아웃트로(393.4~)는 프리셋 아웃트로 영상 몫 — 클립을 만들지 않는다.
 */

import { market, COLOR } from './cmg12-guide.scenes.js';

const FPS = 60000 / 1001;

const LV = {
  entry: 15553.25,
  stop: 15515.5,
  get target() { return this.entry + (this.entry - this.stop) * 2; },
};

const chartBase = {
  visibleBars: 46,
  pricePad: 0.16,
  showGrid: false,
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 0, padBottom: 0, rightGap: 5 },
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
  title: '차트명가 #12 — 요약 3컷',
  width: 1920,
  height: 1080,
  fps: FPS,
  fpsExpr: '60000/1001',
  theme: { preset: 'chartmyeongga' },
  market,

  scenes: [
    /* ── 컷24 첫째 — 배열을 보고 방향을 하나로 (11.5667s) ── */
    {
      id: 'recap-1',
      name: '컷24 요약① 배열 (11.5667s)',
      duration: 10.1,
      chart: {
        ...chartBase,
        reveal: [{ t: 0, v: 58 }, { t: 10.1, v: 60, ease: 'linear' }],
      },
      layers: [
        { type: 'cmgBadge', text: '정리 — 3단계', x: 84, y: 96, size: 44, color: '#E90054', in: [0.6, 0.3] },
        { type: 'cmgTrace', overlay: 0, fromBar: 44, toBar: 57, flatten: 0, width: 14, color: COLOR.ma10, in: [4.0, 0.5] },
        { type: 'cmgTrace', overlay: 1, fromBar: 44, toBar: 57, flatten: 0, width: 14, color: COLOR.ma34, in: [4.5, 0.5] },
        { type: 'cmgNote', text: '① 배열 → 오늘의 방향 하나', bar: 43, price: 15617, size: 52, color: '#111111', in: [5.1, 0.3] },
      ],
    },

    /* ── 컷25 둘째 — 진짜 눌림목 포착 (7.9000s) ── */
    {
      id: 'recap-2',
      name: '컷25 요약② RSI 신호 (7.9000s)',
      duration: 10.166667,
      chart: {
        ...chartBase,
        reveal: [{ t: 0, v: 60 }, { t: 10.166667, v: 60.6, ease: 'linear' }],
      },
      layers: [
        { type: 'cmgBadge', text: '정리 — 3단계', x: 84, y: 96, size: 44, color: '#E90054', popDur: 0 },
        /* 컷24 끝 화면 이월(⑧) — ①은 ②(1.6)가 역할을 이어받을 때 크로스페이드(⑨) */
        { type: 'cmgTrace', overlay: 0, fromBar: 44, toBar: 57, flatten: 0, width: 14, color: COLOR.ma10, in: [0, 0], out: [1.4, 0.4] },
        { type: 'cmgTrace', overlay: 1, fromBar: 44, toBar: 57, flatten: 0, width: 14, color: COLOR.ma34, in: [0, 0], out: [1.4, 0.4] },
        { type: 'cmgNote', text: '① 배열 → 오늘의 방향 하나', bar: 43, price: 15617, size: 52, color: '#111111', in: [0, 0], out: [1.4, 0.4] },
        { type: 'cmgCircle', bar: 52, rsi: 60.5, rx: 58, ry: 48, width: 10, color: '#E90054', drawDur: 0.5, in: [0.9, 0.2] },
        { type: 'cmgNote', text: '② 상승장 — 55선 재돌파 + 양봉', bar: 44, rsi: 74, size: 44, color: '#E90054', in: [1.6, 0.3] },
        { type: 'cmgNote', text: '하락장 — 45선 재이탈 + 음봉', bar: 44, rsi: 16, size: 44, color: '#111111', in: [4.6, 0.3] },
      ],
    },

    /* ── 컷26 셋째 — 짧은 손절 · 1:2 청산 · 절제된 매매 (19.9000s) ── */
    {
      id: 'recap-3',
      name: '컷26 요약③ 손익비와 절제 (19.9000s)',
      duration: 19.266667,
      chart: {
        ...chartBase,
        include: [LV.stop - 12],
        reveal: [{ t: 0, v: 60.6 }, { t: 19.266667, v: 64, ease: 'linear' }],
      },
      layers: [
        { type: 'cmgBadge', text: '정리 — 3단계', x: 84, y: 96, size: 44, color: '#E90054', popDur: 0 },
        /* 컷25 끝 화면 이월(⑧) — ②는 ③(2.2)이 역할을 이어받을 때 크로스페이드(⑨) */
        { type: 'cmgCircle', bar: 52, rsi: 60.5, rx: 58, ry: 48, width: 10, color: '#E90054', drawDur: 0, in: [0, 0], out: [2.0, 0.4] },
        { type: 'cmgNote', text: '② 상승장 — 55선 재돌파 + 양봉', bar: 44, rsi: 74, size: 44, color: '#E90054', in: [0, 0], out: [2.0, 0.4] },
        { type: 'cmgNote', text: '하락장 — 45선 재이탈 + 음봉', bar: 44, rsi: 16, size: 44, color: '#111111', in: [0, 0], out: [2.0, 0.4] },
        { type: 'cmgLevel', price: LV.entry, fromBar: 51, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0.35, in: [0.6, 0.2] },
        {
          type: 'cmgLevel',
          price: LV.stop,
          fromBar: 51,
          fillTo: LV.entry,
          fill: '#FEBABA',
          color: '#9F0000',
          label: '손절',
          labelSize: 38,
          thickness: 13,
          growDur: 0.4,
          in: [0.9, 0.2],
        },
        { type: 'cmgNote', text: '③ 신호 캔들 저점·고점 = 짧은 손절', bar: 40, price: 15448, size: 44, color: '#9F0000', in: [2.2, 0.3] },
        {
          type: 'cmgLevel',
          price: LV.target,
          fromBar: 51,
          fillTo: LV.entry,
          fill: '#BAFDC0',
          color: '#14FF36',
          label: '익절',
          labelSize: 38,
          thickness: 13,
          growDur: 0.4,
          in: [5.8, 0.2],
        },
        { type: 'cmgNote', text: '1 : 2 이상에서 기계적으로', bar: 42, price: 15648, size: 46, color: '#0DA82A', in: [6.7, 0.3] },
        /* 모든 신호가 아니라 세 조건이 겹칠 때만 */
        { type: 'cmgNote', text: '세 조건이 전부 겹칠 때만 진입', bar: 52, rsi: 26, size: 46, color: '#111111', in: [10.4, 0.3] },
        { type: 'cmgNote', text: "'절제된 매매'", bar: 42, price: 15395, size: 64, color: '#E90054', in: [16.2, 0.35] },
        { type: 'cmgUnderline', bar: 42, price: 15395, dy: 58, width: 400, align: 'center', drawDur: 0.35, in: [16.9, 0.15] },
      ],
    },
  ],
};
