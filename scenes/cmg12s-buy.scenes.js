/**
 * 차트명가 #12 r13 — 핵심 개념 + 매수 관점 5컷 (정적·실데이터)
 *
 * 배치 (컷리스트_본편_정확판.txt 그대로):
 *   컷16 buy-core   255.167~265.433 (10.2667s)  핵심: 추세 필터 + 진짜 눌림목
 *   컷17 buy-array  265.433~280.667 (15.2333s)  1분 차트 · 크로스가 아니라 배열
 *   컷18 buy-trend  280.667~293.533 (12.8667s)  정배열 = 상승 추세 → 매수 관점만
 *   컷19 buy-entry  293.533~305.733 (12.2000s)  RSI 55 재돌파 + 양봉 → 다음 캔들 시가 매수
 *   컷20 buy-exit   305.733~319.600 (13.8667s)  손절·익절 1:2 → 절반 분할 → 러너
 *
 * 시장 실측 (SLICE.pullbackM1 = 실제 NQ 1분봉, 2026-08-31 19:33 진입):
 *   정배열: L187~ (s10 > s34) · 눌림 L197 (RSI 52.5) · 55 재돌파 = L199 (RSI 55.1, 양봉)
 *   진입 L200 시가 29436.50 · 손절 = 신호봉 저점 29430.50 (R=6.0) · 익절 1:2 = 29448.50
 *   1:2 도달 L207 (고가 29457.5) · 러너 L216 고가 29528.25 (+15R)
 *
 * 컷16~19 는 reveal 205 완전 정지 (guide 4컷과 같은 화면 — 룰북 ⑧ 심리스).
 * 컷20 은 chart.phases 로 "진행된 시점 스틸" 을 30f 디졸브 교체 — 실영상의
 * 스크린샷 교체 문법 (FX-WHITELIST §0). 가격 앵커 요소는 국면별 복제를
 * 같은 창에서 크로스페이드해 앵커를 갈아탄다 (layer.phase).
 */
import { FPS, SLICE, COLOR, IN, mkMarket, mt5ChartBase, rsiChip, projectHead } from './cmg12s-base.js';
import { chartStill, REVEAL } from './cmg12s-guide.scenes.js';

const LV = {
  signal: 199,
  entry: 29436.5,
  stop: 29430.5,
  get target() { return this.entry + (this.entry - this.stop) * 2; }, // 29448.5
};

export default {
  ...projectHead('차트명가 #12 r13 — 핵심·매수 관점 5컷'),
  market: mkMarket(SLICE.pullbackM1),

  scenes: [
    /* ── 컷16 핵심 — 추세 필터 + 진짜 눌림목 (10.2667s) ── */
    {
      id: 'buy-core',
      name: '컷16 매매법의 핵심 (10.2667s)',
      duration: 10.266667,
      chart: chartStill,
      layers: [
        rsiChip(),
        { type: 'cmgTrace', overlay: 0, fromBar: 172, toBar: 200, flatten: 0, width: 14, color: COLOR.ma10, drawDur: IN.draw, in: [0.8, 0.2], out: [4.2, 0.35] },
        { type: 'cmgNote', bar: 182, price: 29455, text: '① 추세 먼저 필터', size: 48, color: COLOR.ma10, in: [1.6, IN.fade], out: [4.2, 0.35] },
        { type: 'cmgCircle', bar: 197, rsi: 52.5, rx: 62, ry: 48, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [4.8, 0.2] },
        { type: 'cmgNote', bar: 170, rsi: 14, text: '② 진짜 눌림목만', size: 46, color: COLOR.pencil, in: [5.8, IN.fade] },
      ],
    },

    /* ── 컷17 1분 차트 — 크로스가 아니라 배열 (15.2333s) ── */
    {
      id: 'buy-array',
      name: '컷17 정배열 확인 (15.2333s)',
      duration: 15.233333,
      chart: chartStill,
      layers: [
        rsiChip(),
        /* 이월 (⑧) */
        { type: 'cmgCircle', bar: 197, rsi: 52.5, rx: 62, ry: 48, width: 9, color: COLOR.pencil, drawDur: 0, in: [0, 0] },
        { type: 'cmgNote', bar: 170, rsi: 14, text: '② 진짜 눌림목만', size: 46, color: COLOR.pencil, in: [0, 0] },
        { type: 'cmgBadge', text: '1분 차트', x: 96, y: 300, size: 42, color: COLOR.badge, border: false, popDur: 0.13, in: [2.2, 0.3] },
        { type: 'cmgBadge', text: '10일선', x: 96, y: 374, size: 40, color: COLOR.ma10, border: false, popDur: 0.13, in: [4.6, 0.3] },
        { type: 'cmgBadge', text: '34일선', x: 96, y: 446, size: 40, color: COLOR.ma34, border: false, popDur: 0.13, in: [5.6, 0.3] },
        { type: 'cmgNote', x: 960, y: 300, text: '크로스가 아니라 배열', size: 54, color: COLOR.line, in: [8.6, IN.fade] },
        { type: 'cmgUnderline', x: 960, y: 348, width: 560, align: 'center', drawDur: IN.bar, in: [9.4, 0.1] },
      ],
    },

    /* ── 컷18 정배열 = 상승 추세 → 매수 관점만 (12.8667s) ── */
    {
      id: 'buy-trend',
      name: '컷18 매수 관점 고정 (12.8667s)',
      duration: 12.866667,
      chart: chartStill,
      layers: [
        rsiChip(),
        /* 이월 (⑧) — 문장은 교체 시점에 크로스페이드 (⑨) */
        { type: 'cmgBadge', text: '1분 차트', x: 96, y: 300, size: 42, color: COLOR.badge, border: false, popDur: 0 },
        { type: 'cmgCircle', bar: 197, rsi: 52.5, rx: 62, ry: 48, width: 9, color: COLOR.pencil, drawDur: 0, in: [0, 0] },
        { type: 'cmgNote', bar: 170, rsi: 14, text: '② 진짜 눌림목만', size: 46, color: COLOR.pencil, in: [0, 0] },
        { type: 'cmgBadge', text: '10일선', x: 96, y: 374, size: 40, color: COLOR.ma10, border: false, popDur: 0, out: [3.0, 0.4] },
        { type: 'cmgBadge', text: '34일선', x: 96, y: 446, size: 40, color: COLOR.ma34, border: false, popDur: 0, out: [3.0, 0.4] },
        { type: 'cmgNote', x: 960, y: 300, text: '크로스가 아니라 배열', size: 54, color: COLOR.line, in: [0, 0], out: [5.4, 0.4] },
        { type: 'cmgUnderline', x: 960, y: 348, width: 560, align: 'center', drawDur: 0, in: [0, 0], out: [5.4, 0.4] },
        /* 10일선이 34일선 위 — 나란한 접선 강조 */
        { type: 'cmgTrace', overlay: 0, fromBar: 176, toBar: 202, flatten: 0, width: 14, color: COLOR.ma10, drawDur: IN.draw, in: [1.0, 0.2], out: [5.4, 0.35] },
        { type: 'cmgTrace', overlay: 1, fromBar: 176, toBar: 202, flatten: 0, width: 14, color: COLOR.ma34, drawDur: IN.draw, in: [1.7, 0.2], out: [5.4, 0.35] },
        { type: 'cmgNote', bar: 190, price: 29408, text: '정배열', size: 52, color: COLOR.line, in: [2.6, IN.fade] },
        { type: 'cmgNote', x: 960, y: 300, text: '상승 추세 → 매수 관점만', size: 54, color: COLOR.buy, in: [5.9, IN.fade] },
        { type: 'cmgCircle', bar: 187, rsi: 51.4, rx: 72, ry: 52, width: 9, color: COLOR.rsi, drawDur: IN.draw, in: [9.4, 0.2] },
        { type: 'cmgNote', bar: 165, rsi: 90, text: '눌림목 타점은 RSI', size: 44, color: COLOR.rsi, in: [10.2, IN.fade] },
      ],
    },

    /* ── 컷19 신호 — 55 재돌파 + 양봉 마감 → 매수 (12.2000s) ── */
    {
      id: 'buy-entry',
      name: '컷19 진입 신호 (12.2000s)',
      duration: 12.2,
      chart: chartStill, // 줌 금지 — 같은 정지 화면에서 신호 자리를 짚는다
      layers: [
        rsiChip(),
        /* 이월 (⑧) */
        { type: 'cmgBadge', text: '1분 차트', x: 96, y: 300, size: 42, color: COLOR.badge, border: false, popDur: 0 },
        { type: 'cmgCircle', bar: 197, rsi: 52.5, rx: 62, ry: 48, width: 9, color: COLOR.pencil, drawDur: 0, in: [0, 0] },
        { type: 'cmgNote', bar: 170, rsi: 14, text: '② 진짜 눌림목만', size: 46, color: COLOR.pencil, in: [0, 0], out: [3.4, 0.4] },
        { type: 'cmgNote', x: 960, y: 300, text: '상승 추세 → 매수 관점만', size: 54, color: COLOR.buy, in: [0, 0], out: [1.8, 0.4] },
        { type: 'cmgCircle', bar: 187, rsi: 51.4, rx: 72, ry: 52, width: 9, color: COLOR.rsi, drawDur: 0, in: [0, 0], out: [3.4, 0.4] },
        { type: 'cmgNote', bar: 165, rsi: 90, text: '눌림목 타점은 RSI', size: 44, color: COLOR.rsi, in: [0, 0], out: [3.4, 0.4] },
        /* 신호 — RSI 55 재돌파 */
        { type: 'cmgCircle', bar: 199, rsi: 55.1, rx: 56, ry: 44, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [3.8, 0.2] },
        { type: 'cmgNote', bar: 176, rsi: 90, text: '55선 재돌파', size: 46, color: COLOR.buy, in: [4.6, IN.fade] },
        /* 돌파 캔들이 양봉 마감 */
        { type: 'cmgCircle', bar: 199, price: 29434, rx: 40, ry: 56, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [6.4, 0.2] },
        { type: 'cmgNote', bar: 199, price: 29466, text: '양봉 마감', size: 46, color: COLOR.line, in: [7.2, IN.fade] },
        /* 다음 캔들 시가 매수 */
        { type: 'cmgArrow', bar: 200, price: 29436.5, dir: 'buy', label: '매수', size: 34, gap: 16, popDur: IN.pop, in: [9.8, 0.2] },
        { type: 'cmgNote', bar: 200, price: 29414, text: '다음 캔들 시가', size: 40, color: COLOR.line, in: [10.5, IN.fade] },
      ],
    },

    /* ── 컷20 손절·익절 1:2 → 분할 → 러너 (13.8667s) ──
       t=8.0 에 "진행된 시점 스틸"(reveal 224)로 30f 디졸브 (phases).
       가격 앵커 요소는 국면 0/1 복제를 같은 창에서 크로스페이드. */
    {
      id: 'buy-exit',
      name: '컷20 손익비와 러너 (13.8667s)',
      duration: 13.866667,
      chart: {
        ...chartStill,
        include: [LV.stop - 4],
        phases: [{ reveal: 224, in: [8.0, 1.0] }],
      },
      layers: [
        rsiChip(),
        { type: 'cmgBadge', text: '1분 차트', x: 96, y: 300, size: 42, color: COLOR.badge, border: false, popDur: 0, out: [4.9, 0.4] },
        /* 국면0 — 진입 직후 화면의 손익 구조 */
        { type: 'cmgArrow', bar: 200, price: LV.entry, dir: 'buy', label: '매수', size: 34, gap: 16, popDur: 0, out: [8.0, 1.0] },
        { type: 'cmgLevel', price: LV.entry, fromBar: 198, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0.35, in: [0.6, 0.2], out: [8.0, 1.0] },
        { type: 'cmgLevel', price: LV.stop, fromBar: 198, fillTo: LV.entry, fill: COLOR.slFill, color: COLOR.sl, label: '손절', labelSize: 36, thickness: 11, growDur: 0.4, in: [1.0, 0.2], out: [8.0, 1.0] },
        { type: 'cmgLevel', price: LV.target, fromBar: 198, fillTo: LV.entry, fill: COLOR.tpFill, color: COLOR.tp, label: '익절', labelSize: 36, thickness: 11, growDur: 0.4, in: [3.2, 0.2], out: [8.0, 1.0] },
        { type: 'cmgBadge', text: '손익비  1 : 2', x: 96, y: 300, size: 44, color: COLOR.badge, border: false, popDur: 0.13, in: [5.1, 0.3] },
        { type: 'cmgArrow', bar: 207, price: 29457.5, dir: 'sell', label: '익절 1/2', color: '#0DA82A', size: 32, gap: 16, popDur: IN.pop, in: [6.2, 0.2], out: [8.0, 1.0] },
        /* 국면1 — 진행된 스틸 위에 같은 구조를 이어받고 러너 수익 */
        { type: 'cmgArrow', phase: 1, bar: 200, price: LV.entry, dir: 'buy', label: '매수', size: 30, gap: 14, popDur: 0, in: [8.0, 1.0] },
        { type: 'cmgLevel', phase: 1, price: LV.entry, fromBar: 198, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0, in: [8.0, 1.0] },
        { type: 'cmgArrow', phase: 1, bar: 207, price: 29457.5, dir: 'sell', label: '익절 1/2', color: '#0DA82A', size: 28, gap: 14, popDur: 0, in: [8.0, 1.0] },
        { type: 'cmgProfit', phase: 1, entry: LV.entry, fromBar: 200, color: COLOR.tpFill, opacity: 0.3, in: [8.6, 0.4] },
        { type: 'cmgNote', x: 1140, y: 252, text: '남은 절반은 추세 끝까지', size: 46, color: '#0DA82A', in: [9.6, IN.fade] },
        { type: 'cmgArrow', phase: 1, bar: 216, price: 29528.25, dir: 'sell', label: '익절', color: '#0DA82A', size: 32, gap: 16, popDur: IN.pop, in: [12.2, 0.2] },
      ],
    },
  ],
};
