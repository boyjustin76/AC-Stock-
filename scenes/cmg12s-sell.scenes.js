/**
 * 차트명가 #12 r13 — 매도 관점 3컷 (정적·실데이터)
 *
 * 배치 (컷리스트_본편_정확판.txt 그대로):
 *   컷21 sell-array 319.600~334.533 (14.9333s)  5분 차트 · 역배열 → 매도 관점만
 *   컷22 sell-rsi   334.533~349.300 (14.7667s)  반등 무시 · RSI 45선 재이탈
 *   컷23 sell-entry 349.300~369.300 (20.0000s)  음봉 확인 → 매도 → 손익 1:2 → 분할
 *
 * 시장 실측 (SLICE.sellM5 = 실제 NQ 5분봉, 2026-09-01 11:45 진입):
 *   역배열: L165~200 (s10 < s34) · 반등 L184~197 (RSI 57~59) · 45 재이탈 = L199 (RSI 44.1, 음봉)
 *   진입 L200 시가 29208.50 · 손절 = 신호봉 고점 29228.50 (R=20) · 익절 1:2 = 29168.50
 *   1:2 도달 L205 (저가 29146.25) · 이후 L215 저가 29087 (+6R)
 *
 * 컷21·22 는 reveal 205 정지. 컷23 은 phases 로 진행 스틸(214) 교체.
 */
import { FPS, SLICE, COLOR, IN, mkMarket, mt5ChartBase, rsiChip, projectHead } from './cmg12s-base.js';

const S = SLICE.sellM5;
const stillSell = { ...mt5ChartBase, reveal: 205 };

const LV = {
  entry: 29208.5,
  stop: 29228.5,
  get target() { return this.entry - (this.stop - this.entry) * 2; }, // 29168.5
};

export default {
  ...projectHead('차트명가 #12 r13 — 매도 관점 3컷'),
  market: mkMarket(S),

  scenes: [
    /* ── 컷21 5분 차트 — 역배열 (14.9333s) ── */
    {
      id: 'sell-array',
      name: '컷21 역배열 확인 (14.9333s)',
      duration: 14.933333,
      chart: stillSell,
      layers: [
        rsiChip(),
        { type: 'cmgBadge', text: '5분 차트', x: 96, y: 300, size: 42, color: COLOR.badge, border: false, in: [1.6, 0.3] },
        { type: 'cmgTrace', overlay: 0, fromBar: 170, toBar: 202, flatten: 0, width: 14, color: COLOR.ma10, drawDur: IN.draw, in: [4.2, 0.2], out: [9.8, 0.35] },
        { type: 'cmgTrace', overlay: 1, fromBar: 170, toBar: 202, flatten: 0, width: 14, color: COLOR.ma34, drawDur: IN.draw, in: [4.9, 0.2], out: [9.8, 0.35] },
        { type: 'cmgNote', bar: 182, price: 29300, text: '역배열 — 10일선이 34일선 아래', size: 46, color: COLOR.line, in: [6.0, IN.fade] },
        { type: 'cmgNote', x: 960, y: 300, text: '하락 추세 → 매도 관점만', size: 54, color: COLOR.sell, in: [10.6, IN.fade] },
      ],
    },

    /* ── 컷22 반등 무시 · 45선 재이탈 (14.7667s) ── */
    {
      id: 'sell-rsi',
      name: '컷22 매도 신호 (14.7667s)',
      duration: 14.766667,
      chart: stillSell,
      layers: [
        rsiChip(),
        /* 이월 (⑧) */
        { type: 'cmgBadge', text: '5분 차트', x: 96, y: 300, size: 42, color: COLOR.badge, border: false, popDur: 0 },
        { type: 'cmgNote', x: 960, y: 300, text: '하락 추세 → 매도 관점만', size: 54, color: COLOR.sell, in: [0, 0], out: [2.6, 0.4] },
        /* 반등이 와도 매수 아님 */
        { type: 'cmgCircle', bar: 190, price: 29252, rx: 82, ry: 58, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [2.2, 0.2] },
        { type: 'cmgNote', bar: 176, price: 29320, text: '반등 — 매수 아니다', size: 46, color: COLOR.pencil, in: [3.2, IN.fade] },
        /* RSI 45 위로 갔다가 재이탈 */
        { type: 'cmgCircle', bar: 197, rsi: 59.0, rx: 58, ry: 46, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [7.2, 0.2] },
        { type: 'cmgCircle', bar: 199, rsi: 44.1, rx: 56, ry: 44, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [9.6, 0.2] },
        { type: 'cmgNote', bar: 172, rsi: 12, text: '45선 재이탈', size: 46, color: COLOR.sell, in: [10.4, IN.fade] },
      ],
    },

    /* ── 컷23 음봉 확인 → 매도 → 손익 1:2 → 분할 (20.0000s) ── */
    {
      id: 'sell-entry',
      name: '컷23 매도 진입과 청산 (20.0000s)',
      duration: 20.0,
      chart: {
        ...stillSell,
        include: [LV.stop + 4],
        phases: [{ reveal: 214, in: [12.6, 0.5] }],
      },
      layers: [
        rsiChip(),
        { type: 'cmgBadge', text: '5분 차트', x: 96, y: 300, size: 42, color: COLOR.badge, border: false, popDur: 0, out: [8.3, 0.4] },
        /* 이월 (⑧) — 신호 원 둘. 국면 전환(12.6)과 함께 퇴장 — 앵커가 국면0 좌표라서 */
        { type: 'cmgCircle', bar: 199, rsi: 44.1, rx: 56, ry: 44, width: 9, color: COLOR.pencil, drawDur: 0, in: [0, 0], out: [12.6, 0.5] },
        { type: 'cmgNote', bar: 172, rsi: 12, text: '45선 재이탈', size: 46, color: COLOR.sell, in: [0, 0], out: [12.6, 0.5] },
        /* 음봉 마감 확인 */
        { type: 'cmgCircle', bar: 199, price: 29218, rx: 40, ry: 56, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [1.6, 0.2], out: [12.6, 0.5] },
        { type: 'cmgNote', bar: 199, price: 29246, text: '음봉 마감', size: 46, color: COLOR.line, in: [2.4, IN.fade], out: [12.6, 0.5] },
        /* 국면0 — 진입과 손익 구조 */
        { type: 'cmgArrow', bar: 200, price: LV.entry, dir: 'sell', label: '매도', size: 34, gap: 16, popDur: IN.pop, in: [4.6, 0.2], out: [12.6, 0.5] },
        { type: 'cmgLevel', price: LV.entry, fromBar: 198, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0.35, in: [6.4, 0.2], out: [12.6, 0.5] },
        { type: 'cmgLevel', price: LV.stop, fromBar: 198, fillTo: LV.entry, fill: COLOR.slFill, color: COLOR.sl, label: '손절', labelSize: 36, thickness: 11, growDur: 0.4, in: [6.8, 0.2], out: [12.6, 0.5] },
        { type: 'cmgLevel', price: LV.target, fromBar: 198, fillTo: LV.entry, fill: COLOR.tpFill, color: COLOR.tp, label: '익절', labelSize: 36, thickness: 11, growDur: 0.4, in: [8.6, 0.2], out: [12.6, 0.5] },
        { type: 'cmgBadge', text: '손익비  1 : 2', x: 96, y: 300, size: 44, color: COLOR.badge, border: false, in: [8.5, 0.3] },
        /* 국면1 — 진행 스틸: 1:2 도달·분할 */
        { type: 'cmgArrow', phase: 1, bar: 200, price: LV.entry, dir: 'sell', label: '매도', size: 30, gap: 14, popDur: 0, in: [12.6, 0.5] },
        { type: 'cmgLevel', phase: 1, price: LV.entry, fromBar: 198, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0, in: [12.6, 0.5] },
        { type: 'cmgArrow', phase: 1, bar: 205, price: 29146.25, dir: 'buy', label: '익절 1/2', color: '#0DA82A', size: 30, gap: 14, popDur: IN.pop, in: [14.2, 0.2] },
        { type: 'cmgNote', x: 1200, y: 470, text: '남은 절반은 추세 끝까지', size: 44, color: '#0DA82A', in: [16.2, IN.fade] },
      ],
    },
  ],
};
