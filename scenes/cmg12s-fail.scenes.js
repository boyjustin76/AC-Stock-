/**
 * 차트명가 #12 r13 — 대중의 오해·한계 5컷 (정적·실데이터)
 *
 * 배치 (컷리스트_본편_정확판.txt 그대로):
 *   컷11 fail-common 144.267~161.733 (17.4667s)  대중: 교차=반전 신호, RSI 70/30 역추세
 *   컷12 fail-combo  161.733~171.100 ( 9.3667s)  "교차 + RSI 30 = 매수" 조합
 *   컷13 fail-chop   173.100~200.767 (27.6667s)  첫째 한계 — 횡보 가짜 교차 반복
 *   컷14 fail-blind  200.767~230.000 (29.2333s)  둘째 한계 — RSI 70 위 유지 상승
 *   컷15 fail-loss   230.000~253.167 (23.1667s)  역추세 큰 손실 + 구조적 모순
 *
 * 시장: 컷11·12 = SLICE.pullbackM1 (소개 화면 이월, 룰북 ⑧) /
 *       컷13 = SLICE.chopM1 (실측 횡보: L188~241 교차 반복, 폭 29475~29521.75) /
 *       컷14·15 = SLICE.blindM1 (실측 강추세: RSI 70+ 29봉, 29496→29566).
 * 전 컷 차트 정지. 오버레이 크로스페이드 누적만 (FX-WHITELIST).
 */
import { FPS, SLICE, COLOR, IN, mkMarket, mt5ChartBase, rsiChip, projectHead } from './cmg12s-base.js';
import { chartStill, REVEAL } from './cmg12s-guide.scenes.js';

const CHOP = SLICE.chopM1;
const BLIND = SLICE.blindM1;

export default {
  ...projectHead('차트명가 #12 r13 — 오해·한계 5컷'),
  market: mkMarket(SLICE.pullbackM1),

  scenes: [
    /* ── 컷11 대중의 통념 (17.4667s) ── */
    {
      id: 'fail-common',
      name: '컷11 대중의 통념 (17.4667s)',
      duration: 17.466667,
      chart: chartStill,
      layers: [
        rsiChip(),
        /* 통념 1 — 교차 = 반전 신호 */
        { type: 'cmgNote', x: 960, y: 300, text: '교차가 나오면 추세가 뒤집힌다?', size: 54, color: COLOR.line, in: [1.0, IN.fade], out: [8.2, 0.4] },
        /* 통념 2 — RSI 70/30 역추세 (기본형 기준선을 잠깐 그어 보인다) */
        { type: 'rsiLevel', v: 70, label: '70', color: 'rgba(159,0,0,0.8)', width: 2.5, growDur: IN.bar, in: [8.8, 0.1] },
        { type: 'rsiLevel', v: 30, label: '30', color: 'rgba(2,0,243,0.7)', width: 2.5, growDur: IN.bar, in: [9.4, 0.1] },
        { type: 'cmgNote', bar: 150, rsi: 96, text: '70 넘으면 과매수 → 매도?', size: 42, color: COLOR.sl, in: [10.2, IN.fade] },
        { type: 'cmgNote', bar: 150, rsi: 8, text: '30 아래면 과매도 → 매수?', size: 42, color: COLOR.sell, in: [12.6, IN.fade] },
      ],
    },

    /* ── 컷12 조합 공식 (9.3667s) ── */
    {
      id: 'fail-combo',
      name: '컷12 조합 공식 (9.3667s)',
      duration: 9.366667,
      chart: chartStill,
      layers: [
        rsiChip(),
        /* 이월 (⑧) — 기본형 기준선과 통념 문구 유지 */
        { type: 'rsiLevel', v: 70, label: '70', color: 'rgba(159,0,0,0.8)', width: 2.5, growDur: 0, in: [0, 0] },
        { type: 'rsiLevel', v: 30, label: '30', color: 'rgba(2,0,243,0.7)', width: 2.5, growDur: 0, in: [0, 0] },
        { type: 'cmgNote', bar: 150, rsi: 96, text: '70 넘으면 과매수 → 매도?', size: 42, color: COLOR.sl, in: [0, 0], out: [2.4, 0.4] },
        { type: 'cmgNote', bar: 150, rsi: 8, text: '30 아래면 과매도 → 매수?', size: 42, color: COLOR.sell, in: [0, 0], out: [2.4, 0.4] },
        /* "조합하면 정답?" — ①②③ 알약 누적 */
        { type: 'cmgBadge', text: '① 골든크로스', x: 96, y: 300, size: 44, color: COLOR.badge, border: false, popDur: 0.13, in: [2.8, 0.3] },
        { type: 'cmgBadge', text: '② RSI 30 과매도', x: 96, y: 380, size: 44, color: COLOR.badge, border: false, popDur: 0.13, in: [4.2, 0.3] },
        { type: 'cmgBadge', text: '= 매수 신호?', x: 96, y: 460, size: 44, color: COLOR.line, border: false, popDur: 0.13, in: [5.8, 0.3] },
      ],
    },

    /* ── 컷13 첫째 한계 — 횡보 가짜 교차 (27.6667s) ── */
    {
      id: 'fail-chop',
      name: '컷13 횡보 가짜 신호 (27.6667s)',
      duration: 27.666667,
      market: mkMarket(CHOP),
      chart: {
        ...mt5ChartBase,
        reveal: 264, // L165~267 — 교차 L188·205·223·241 이 모두 화면 안
        rsi: undefined, // 첫째 한계는 이평선 이야기 (대본: "이평선을 켜보면")
      },
      layers: [
        /* 박스권 검은 선 (팀장 규칙 ②) — 실측 폭 29475~29521.75 */
        { type: 'cmgLevel', price: 29521.75, fromBar: 170, color: COLOR.line, thickness: 4, growDur: 0.35, in: [1.2, 0.2] },
        { type: 'cmgLevel', price: 29475, fromBar: 170, color: COLOR.line, thickness: 4, growDur: 0.35, in: [1.6, 0.2] },
        { type: 'cmgNote', x: 430, y: 300, text: '추세 없는 횡보', size: 48, color: COLOR.line, in: [2.6, IN.fade] },
        /* 교차 반복 — 손그림 원 셋 (연타 금지 — 내레이션 호흡대로) */
        { type: 'cmgCircle', bar: 188, price: 29505, rx: 56, ry: 44, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [7.4, 0.2] },
        { type: 'cmgCircle', bar: 205, price: 29503, rx: 56, ry: 44, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [9.8, 0.2] },
        { type: 'cmgCircle', bar: 223, price: 29502, rx: 56, ry: 44, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [12.2, 0.2] },
        { type: 'cmgNote', x: 720, y: 884, text: '교차가 계속 나온다 = 신호도 계속', size: 46, color: COLOR.pencil, in: [13.6, IN.fade] },
        /* 신호대로 했다면 — 태그 두 개와 좌절 */
        { type: 'cmgArrow', bar: 206, price: 29502, dir: 'buy', label: '매수', size: 30, gap: 14, popDur: IN.pop, in: [17.8, 0.2] },
        { type: 'cmgArrow', bar: 224, price: 29491, dir: 'sell', label: '매도', size: 30, gap: 14, popDur: IN.pop, in: [19.6, 0.2] },
        { type: 'cmgNote', x: 960, y: 258, text: '수수료와 짧은 손절만 쌓인다', size: 52, color: COLOR.sl, in: [22.4, IN.fade] },
      ],
    },

    /* ── 컷14 둘째 한계 — RSI 70 위 유지 (29.2333s) ── */
    {
      id: 'fail-blind',
      name: '컷14 RSI 70 맹신 (29.2333s)',
      duration: 29.233333,
      market: mkMarket(BLIND),
      chart: {
        ...mt5ChartBase,
        reveal: 230, // L131~233 — RSI 70+ 구간(L160~188)과 이후 지속 상승까지
      },
      layers: [
        rsiChip(),
        { type: 'cmgNote', bar: 150, price: 29558, text: '뚜렷한 상승 추세', size: 48, color: COLOR.line, in: [1.4, IN.fade] },
        /* RSI 70 위 유지 — 과열 밴드 + 원 */
        { type: 'rsiZone', from: 70, to: 100, color: 'rgba(254,186,186,0.4)', growDur: IN.bar, in: [5.2, 0.1] },
        { type: 'rsiLevel', v: 70, label: '70', color: 'rgba(159,0,0,0.8)', width: 2.5, growDur: IN.bar, in: [5.6, 0.1] },
        { type: 'cmgCircle', bar: 160, rsi: 70.9, rx: 58, ry: 44, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [8.0, 0.2] },
        { type: 'cmgNote', bar: 150, rsi: 12, text: '70 돌파 — 과매수?', size: 42, color: COLOR.sl, in: [9.0, IN.fade] },
        /* 꺾이지 않고 계속 위 */
        { type: 'cmgTrace', overlay: 0, fromBar: 162, toBar: 196, flatten: 0, width: 14, color: COLOR.ma10, drawDur: 0.7, in: [14.2, 0.2] },
        { type: 'cmgNote', bar: 176, price: 29534, text: '안 꺾이고 계속 위에 머문다', size: 46, color: COLOR.pencil, in: [15.6, IN.fade] },
        { type: 'cmgNote', x: 960, y: 300, text: '강한 추세에서 RSI 는 계속 과매수다', size: 52, color: COLOR.line, in: [22.0, IN.fade] },
      ],
    },

    /* ── 컷15 역추세 큰 손실 + 구조적 모순 (23.1667s) ── */
    {
      id: 'fail-loss',
      name: '컷15 역추세의 대가 (23.1667s)',
      duration: 23.166667,
      market: mkMarket(BLIND),
      chart: {
        ...mt5ChartBase,
        reveal: 230,
      },
      layers: [
        rsiChip(),
        /* 이월 (⑧) — 과열 밴드·70선·원 유지 */
        { type: 'rsiZone', from: 70, to: 100, color: 'rgba(254,186,186,0.4)', growDur: 0, in: [0, 0] },
        { type: 'rsiLevel', v: 70, label: '70', color: 'rgba(159,0,0,0.8)', width: 2.5, growDur: 0, in: [0, 0] },
        { type: 'cmgCircle', bar: 160, rsi: 70.9, rx: 58, ry: 44, width: 9, color: COLOR.pencil, drawDur: 0, in: [0, 0] },
        { type: 'cmgNote', x: 960, y: 300, text: '강한 추세에서 RSI 는 계속 과매수다', size: 52, color: COLOR.line, in: [0, 0], out: [2.6, 0.4] },
        /* 과매수라고 매도 잡았다면 */
        { type: 'cmgArrow', bar: 161, price: 29490, dir: 'sell', label: '매도', size: 32, gap: 16, popDur: IN.pop, in: [3.0, 0.2] },
        {
          type: 'cmgLevel', price: 29566.75, fromBar: 161, fillTo: 29496.5,
          fill: COLOR.slFill, color: COLOR.sl, label: '손실', labelSize: 38, thickness: 13,
          growDur: 0.4, in: [5.0, 0.25],
        },
        { type: 'cmgNote', bar: 196, price: 29470, text: '추세가 이어질수록 손실도 커진다', size: 46, color: COLOR.sl, in: [7.4, IN.fade], out: [13.4, 0.4] },
        /* 구조적 모순 정리 (⑯ 같은 폰트 프리셋) — 존과 겹치지 않는 중앙 하단 빈 면 */
        { type: 'cmgNote', x: 860, y: 600, text: '횡보장 — 신호가 너무 많다', size: 50, color: COLOR.line, in: [14.0, IN.fade] },
        { type: 'cmgNote', x: 860, y: 674, text: '추세장 — 신호가 계속 틀린다', size: 50, color: COLOR.line, in: [16.6, IN.fade] },
        { type: 'cmgNote', x: 860, y: 772, text: '기준을 어떻게 다시 세워야 할까?', size: 54, color: COLOR.badge, in: [20.0, IN.fade] },
      ],
    },
  ],
};
