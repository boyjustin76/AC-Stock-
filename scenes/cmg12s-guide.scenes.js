/**
 * 차트명가 #12 r13 — 소개·설정 4컷 (정적·실데이터)
 *
 * 배치 (컷리스트_본편_정확판.txt 그대로):
 *   컷7  guide-intro  60.600~ 70.333 ( 9.7333s)  오늘 지표: 10일선·34일선·RSI
 *   컷8  guide-ma     70.333~ 81.200 (10.8667s)  이평선 = 추세 방향, 但 후행성
 *   컷9  guide-rsi    81.200~ 97.967 (16.7667s)  RSI = 힘의 세기 → 방향은 이평선·타이밍은 RSI
 *   컷10 guide-set   116.967~142.267 (25.3000s)  설정값: 10/34 이평선, RSI 기간 10, 55/45선
 *
 * 시장: 실제 NQ 1분봉 (SLICE.pullbackM1) — 매수 챕터와 같은 차트에서 소개한다 (기존 설계 계승).
 * 차트는 4컷 모두 reveal 205 완전 정지 (컷 경계 심리스, 룰북 ⑧).
 * 지표 '켜짐'은 알파 크로스페이드 0.5s 단발 (FX-WHITELIST §2 — 디졸브 등장 문법).
 */
import { FPS, SLICE, COLOR, IN, mkMarket, mt5ChartBase, rsiChip, projectHead } from './cmg12s-base.js';

const S = SLICE.pullbackM1;
export const REVEAL = 205; // 진입(L200) 직후 시점 — 매수 챕터 시작과 동일 화면
export const chartStill = { ...mt5ChartBase, reveal: REVEAL };

export default {
  ...projectHead('차트명가 #12 r13 — 소개·설정 4컷'),
  market: mkMarket(S),

  scenes: [
    /* ── 컷7 지표 소개 — 하나씩 켜짐 (9.7333s) ── */
    {
      id: 'guide-intro',
      name: '컷7 오늘의 지표 (9.7333s)',
      duration: 9.733333,
      chart: {
        ...chartStill,
        ma: [
          { type: 'sma', period: 10, width: 7, color: COLOR.ma10, alpha: [{ t: 1.6, v: 0 }, { t: 2.1, v: 1 }] },
          { type: 'sma', period: 34, width: 7, color: COLOR.ma34, alpha: [{ t: 3.4, v: 0 }, { t: 3.9, v: 1 }] },
        ],
        rsiAlpha: [{ t: 5.6, v: 0 }, { t: 6.1, v: 1 }],
      },
      layers: [
        rsiChip({ in: [5.9, 0.3] }),
        { type: 'cmgBadge', text: '10일선', x: 96, y: 300, size: 40, color: COLOR.ma10, border: false, in: [2.2, 0.3] },
        { type: 'cmgBadge', text: '34일선', x: 96, y: 372, size: 40, color: COLOR.ma34, border: false, in: [4.0, 0.3] },
        { type: 'cmgBadge', text: 'RSI (기간 10)', x: 96, y: 444, size: 40, color: COLOR.rsi, border: false, in: [6.2, 0.3] },
      ],
    },

    /* ── 컷8 이평선 = 추세의 방향, 후행성 (10.8667s) ── */
    {
      id: 'guide-ma',
      name: '컷8 이평선의 역할 (10.8667s)',
      duration: 10.866667,
      chart: chartStill,
      layers: [
        rsiChip(),
        { type: 'cmgBadge', text: '10일선', x: 96, y: 300, size: 40, color: COLOR.ma10, border: false, popDur: 0 },
        { type: 'cmgBadge', text: '34일선', x: 96, y: 372, size: 40, color: COLOR.ma34, border: false, popDur: 0 },
        /* 정배열 구간의 두 선을 접선 덧칠로 강조 — 추세의 방향 */
        { type: 'cmgTrace', overlay: 0, fromBar: 168, toBar: 200, flatten: 0, width: 14, color: COLOR.ma10, drawDur: IN.draw, in: [1.2, 0.2], out: [6.0, 0.4] },
        { type: 'cmgNote', bar: 178, price: 29452, text: '추세의 방향', size: 48, color: COLOR.ma10, in: [2.2, IN.fade], out: [6.0, 0.4] },
        /* 후행성 — 가격이 먼저 꺾이고 이평선이 늦게 따라온 자리 */
        { type: 'cmgCircle', bar: 193, price: 29424, rx: 66, ry: 52, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [6.6, 0.2] },
        { type: 'cmgNote', bar: 178, price: 29396, text: '단, 반응은 한 박자 늦다 — 후행성', size: 44, color: COLOR.line, in: [7.6, IN.fade] },
      ],
    },

    /* ── 컷9 RSI = 힘의 세기 · 방향→타이밍 결합 (16.7667s) ── */
    {
      id: 'guide-rsi',
      name: '컷9 RSI 의 역할 (16.7667s)',
      duration: 16.766667,
      chart: chartStill,
      layers: [
        rsiChip(),
        /* 이월 (⑧): 후행성 원과 문구는 RSI 이야기가 시작되며 교체 (⑨) */
        { type: 'cmgCircle', bar: 193, price: 29424, rx: 66, ry: 52, width: 9, color: COLOR.pencil, drawDur: 0, in: [0, 0], out: [2.2, 0.4] },
        { type: 'cmgNote', bar: 178, price: 29396, text: '단, 반응은 한 박자 늦다 — 후행성', size: 44, color: COLOR.line, in: [0, 0], out: [2.2, 0.4] },
        /* RSI = 상대적 힘의 세기 */
        { type: 'cmgCircle', bar: 97, rsi: 74.3, rx: 72, ry: 50, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [2.8, 0.2] },
        { type: 'cmgNote', bar: 110, rsi: 96, text: '힘이 강할 때', size: 42, color: COLOR.rsi, in: [3.6, IN.fade] },
        { type: 'cmgCircle', bar: 157, rsi: 45.1, rx: 72, ry: 50, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [5.4, 0.2] },
        { type: 'cmgNote', bar: 168, rsi: 12, text: '힘이 빠질 때', size: 42, color: COLOR.rsi, in: [6.2, IN.fade] },
        /* 결합 원리 */
        { type: 'cmgNote', x: 960, y: 320, text: '방향은 이동평균선 · 타이밍은 RSI', size: 56, color: COLOR.line, in: [10.4, IN.fade] },
        { type: 'cmgUnderline', x: 960, y: 368, width: 760, align: 'center', drawDur: IN.bar, in: [11.2, 0.1] },
      ],
    },

    /* ── 컷10 설정값 (25.3000s) ── */
    {
      id: 'guide-set',
      name: '컷10 설정값 (25.3000s)',
      duration: 25.3,
      chart: chartStill,
      layers: [
        rsiChip(),
        /* 이월 (⑧) — 결합 원리 문장은 설정 이야기가 시작되며 퇴장 */
        { type: 'cmgNote', x: 960, y: 320, text: '방향은 이동평균선 · 타이밍은 RSI', size: 56, color: COLOR.line, in: [0, 0], out: [3.2, 0.4] },
        { type: 'cmgUnderline', x: 960, y: 368, width: 760, align: 'center', drawDur: 0, in: [0, 0], out: [3.2, 0.4] },
        /* 설정 3종 — 핑크 알약 누적 (①②③ 문법) */
        { type: 'cmgBadge', text: '① 이동평균선 10 · 34', x: 96, y: 300, size: 44, color: COLOR.badge, border: false, in: [4.0, 0.3] },
        { type: 'cmgBadge', text: '② RSI 기간 14 → 10', x: 96, y: 380, size: 44, color: COLOR.badge, border: false, in: [9.8, 0.3] },
        { type: 'cmgBadge', text: '③ 기준선 70·30 → 55·45', x: 96, y: 460, size: 44, color: COLOR.badge, border: false, in: [15.6, 0.3] },
        /* 55/45 점선을 손그림 원으로 짚는다 */
        { type: 'cmgCircle', bar: 203, rsi: 55, rx: 54, ry: 30, width: 8, color: COLOR.pencil, drawDur: IN.draw, in: [17.4, 0.2] },
        { type: 'cmgCircle', bar: 203, rsi: 45, rx: 54, ry: 30, width: 8, color: COLOR.pencil, drawDur: IN.draw, in: [18.4, 0.2] },
        { type: 'cmgNote', bar: 158, rsi: 16, text: '스캘핑은 더 빠른 기준선', size: 42, color: COLOR.line, in: [19.6, IN.fade] },
      ],
    },
  ],
};
