/**
 * 차트명가 #12 r13 — 인트로+후킹 병합 1컷 (정적·실데이터)
 *
 * 배치: 컷리스트_본편_정확판.txt 그대로 — 시작 5.533s / 길이 23.1333s (레거시 intro-hook 대체).
 * 대본: "골든크로스에 사고 데드크로스에 팔아라" 공식 → ①골든 가짜 신호 손실
 *       ②데드크로스 매도 후 상승 — 손실 전환. (두 사례가 별개 — 총괄 해석, 이정찬 컨펌)
 *
 * 시장: 실제 NQ 일봉 (data/nq/NQ_1d.json 전역 640~790 슬라이스, cmg12s-base SLICE.introD1)
 *   - 데드크로스 L87 (2024-07-26) 이후 반등 — 매도했으면 손실 전환
 *   - 골든크로스 L107 (2024-08-23) 이후 -6.7% — 가짜 신호
 * 차트는 reveal 137 로 컷 내내 완전 정지. 오버레이만 크로스페이드로 누적 (FX-WHITELIST §0·§5).
 */
import { FPS, SLICE, COLOR, IN, mkMarket, mt5ChartBase, rsiChip, projectHead } from './cmg12s-base.js';

const S = SLICE.introD1;

export default {
  ...projectHead('차트명가 #12 r13 — 인트로 병합 1컷'),
  market: mkMarket(S),

  scenes: [
    {
      id: 'intro-hook',
      name: '인트로+후킹 병합 (23.1333s)',
      duration: 23.133333,
      chart: {
        ...mt5ChartBase,
        visibleBars: 96,
        reveal: 137, // 정지 — 두 사례가 모두 화면 안
        rsi: undefined, // 인트로는 이평선 이야기 — RSI 패널 없음 (대본에 RSI 없음)
        layout: { ...mt5ChartBase.layout },
      },
      layers: [
        /* 공식 소개 */
        { type: 'cmgNote', x: 960, y: 300, text: '"골든크로스에 사고, 데드크로스에 팔아라"', size: 56, color: COLOR.line, in: [0.6, IN.fade], out: [5.2, 0.4] },

        /* 사례① — 골든크로스 가짜 신호 (L107 교차 → L116 저점 -6.7%) */
        { type: 'cmgCircle', bar: 107, price: 19487, rx: 64, ry: 52, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [5.6, 0.2] },
        { type: 'cmgNote', bar: 111, price: 20350, text: '골든크로스', size: 48, color: COLOR.pencil, in: [6.2, IN.fade] },
        { type: 'cmgArrow', bar: 108, price: 19560, dir: 'buy', label: '매수', size: 34, gap: 16, popDur: IN.pop, in: [7.4, 0.2] },
        {
          type: 'cmgLevel', price: 18339.75, fromBar: 108, fillTo: 19790.75,
          fill: COLOR.slFill, color: COLOR.sl, label: '손실', labelSize: 38, thickness: 13,
          growDur: 0.4, in: [9.2, 0.25],
        },
        { type: 'cmgNote', bar: 116, price: 17900, text: '가짜 신호', size: 50, color: COLOR.sl, in: [10.8, IN.fade] },

        /* 사례② — 데드크로스 매도 후 상승 (L87 교차 → L102 반등) */
        { type: 'cmgCircle', bar: 85, price: 19870, rx: 64, ry: 52, width: 9, color: COLOR.pencil, drawDur: IN.draw, in: [12.6, 0.2] },
        { type: 'cmgNote', bar: 72, price: 19050, text: '데드크로스', size: 48, color: COLOR.pencil, in: [13.2, IN.fade] },
        { type: 'cmgArrow', bar: 88, price: 18865, dir: 'sell', label: '매도', size: 34, gap: 16, popDur: IN.pop, in: [14.4, 0.2] },
        {
          type: 'cmgLevel', price: 19605.75, fromBar: 92, fillTo: 19174.5,
          fill: COLOR.slFill, color: COLOR.sl, label: '손실 전환', labelSize: 36, thickness: 13,
          growDur: 0.4, in: [16.2, 0.25],
        },

        /* 정리 */
        { type: 'cmgNote', x: 960, y: 300, text: '공식만 믿으면 — 두 번 다 손실', size: 56, color: COLOR.line, in: [19.4, IN.fade] },
      ],
    },
  ],
};
