/**
 * 차트명가 #12 r13 — 요약 3컷 (정적·실데이터)
 *
 * 배치 (컷리스트_본편_정확판.txt 그대로):
 *   컷24 recap-1 369.300~379.400 (10.1000s)  요약① 배열 → 방향 하나
 *   컷25 recap-2 379.400~389.567 (10.1667s)  요약② 55선 재돌파 / 45선 재이탈
 *   컷26 recap-3 389.567~408.833 (19.2667s)  요약③ 짧은 손절 · 1:2 기계적 청산 · 절제
 *
 * 시장: 매수 사례의 완결 화면 (SLICE.pullbackM1, reveal 224 — 러너까지 보이는 스틸).
 * 요약 열거는 같은 폰트 프리셋으로 통일 (룰북 ⑯) — 핑크 알약 + 검정 노트.
 */
import { FPS, SLICE, COLOR, IN, mkMarket, mt5ChartBase, rsiChip, projectHead } from './cmg12s-base.js';

const stillDone = { ...mt5ChartBase, reveal: 224 };

export default {
  ...projectHead('차트명가 #12 r13 — 요약 3컷'),
  market: mkMarket(SLICE.pullbackM1),

  scenes: [
    /* ── 컷24 요약① 배열 → 방향 (10.1000s) ── */
    {
      id: 'recap-1',
      name: '컷24 요약① (10.1000s)',
      duration: 10.1,
      chart: stillDone,
      layers: [
        rsiChip(),
        { type: 'cmgBadge', text: '① 배열로 방향을 정한다', x: 96, y: 300, size: 46, color: COLOR.badge, border: false, in: [1.2, 0.3] },
        { type: 'cmgTrace', overlay: 0, fromBar: 176, toBar: 218, flatten: 0, width: 14, color: COLOR.ma10, drawDur: 0.6, in: [3.4, 0.2] },
        { type: 'cmgNote', bar: 196, price: 29396, text: '정배열이면 매수만 · 역배열이면 매도만', size: 44, color: COLOR.line, in: [5.2, IN.fade] },
      ],
    },

    /* ── 컷25 요약② 신호 (10.1667s) ── */
    {
      id: 'recap-2',
      name: '컷25 요약② (10.1667s)',
      duration: 10.166667,
      chart: stillDone,
      layers: [
        rsiChip(),
        /* 이월 (⑧) */
        { type: 'cmgBadge', text: '① 배열로 방향을 정한다', x: 96, y: 300, size: 46, color: COLOR.badge, border: false, popDur: 0 },
        { type: 'cmgBadge', text: '② 55 재돌파 / 45 재이탈', x: 96, y: 380, size: 46, color: COLOR.badge, border: false, in: [1.2, 0.3] },
        { type: 'cmgCircle', bar: 199, rsi: 55.1, rx: 56, ry: 44, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [3.4, 0.2] },
        { type: 'cmgNote', bar: 176, rsi: 90, text: '캔들 색까지 확인하고 진입', size: 42, color: COLOR.line, in: [5.4, IN.fade] },
      ],
    },

    /* ── 컷26 요약③ 청산 규칙 + 마무리 (19.2667s) ── */
    {
      id: 'recap-3',
      name: '컷26 요약③ (19.2667s)',
      duration: 19.266667,
      chart: stillDone,
      layers: [
        rsiChip(),
        /* 이월 (⑧) */
        { type: 'cmgBadge', text: '① 배열로 방향을 정한다', x: 96, y: 300, size: 46, color: COLOR.badge, border: false, popDur: 0 },
        { type: 'cmgBadge', text: '② 55 재돌파 / 45 재이탈', x: 96, y: 380, size: 46, color: COLOR.badge, border: false, popDur: 0 },
        { type: 'cmgCircle', bar: 199, rsi: 55.1, rx: 56, ry: 44, width: 9, color: COLOR.pencil, drawDur: 0, in: [0, 0] },
        { type: 'cmgBadge', text: '③ 손절 짧게 · 익절 1:2', x: 96, y: 460, size: 46, color: COLOR.badge, border: false, in: [1.4, 0.3] },
        { type: 'cmgLevel', price: 29430.5, fromBar: 198, fillTo: 29436.5, fill: COLOR.slFill, color: COLOR.sl, thickness: 8, growDur: 0.4, in: [3.6, 0.2] },
        { type: 'cmgLevel', price: 29448.5, fromBar: 198, fillTo: 29436.5, fill: COLOR.tpFill, color: COLOR.tp, thickness: 8, growDur: 0.4, in: [4.2, 0.2] },
        { type: 'cmgNote', x: 1210, y: 640, text: '이유 없는 진입도, 미련 있는 청산도 없다', size: 44, color: COLOR.line, in: [8.4, IN.fade] },
        { type: 'cmgNote', x: 1260, y: 300, text: '절제된 매매 — 기준이 계좌를 지킨다', size: 52, color: COLOR.badge, in: [14.0, IN.fade] },
      ],
    },
  ],
};
