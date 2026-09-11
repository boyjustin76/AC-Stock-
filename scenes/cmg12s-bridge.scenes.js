/**
 * 차트명가 #12 r13 — 말 구간 설명 카드 2클립 (정적 배경판)
 *
 * 문안·타이포는 r12 확정본(cmg12-bridge.scenes.js, 이정찬 "확인했어. 완벽해")을 그대로 계승.
 * r13 변경점 둘뿐:
 *   ① 배경 워시 차트의 리빌 흐름 제거 — reveal 숫자 고정 (팀장: 움직이는 것 금지)
 *   ② 배경 캔들을 실데이터로 교체 (인트로/매수 챕터와 같은 슬라이스 이월)
 *
 * 배치 (컷리스트_본편_정확판.txt 그대로):
 *   브리지1 bridge-intro 28.667~58.600 (29.9333s)
 *   브리지2 bridge-scalp 97.967~116.967 (19.0000s)
 */
import { FPS, SLICE, COLOR, mkMarket, projectHead } from './cmg12s-base.js';

const washBase = {
  visibleBars: 96,
  pricePad: 0.16,
  showGrid: false,
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 216, padBottom: 162, rightGap: 0 },
  blurPx: [{ t: 0, v: 16 }],
  alpha: [{ t: 0, v: 0.55 }],
};

/* 차명10 카드 타이포 (r12 실측 그대로 — cmg12-bridge.scenes.js 참조) */
const T10 = {
  font: "'GyeonggiBatang', '경기천년바탕', Pretendard, sans-serif",
  fontWeight: 700,
  italic: true,
  color: '#FFFFFF',
  strokeWidth: 0,
  shadowPrem: { opacity: 0.95, angle: 135, distance: 7.0, size: 12.8, blur: 40 },
  hlStyle: 'band',
  hlColor: '#EF2767',
  hlTextColor: '#FFFFFF',
  preColor: 'rgba(255,255,255,0.5)',
};
const T10H = { ...T10, size: 117 };
const title10 = (text) => ({ parts: [{ text, hl: true }] });
const GROUND10 = { type: 'fill', color: '#C4C6C5', opacity: 0.82, in: [0, 0] };

export default {
  ...projectHead('차트명가 #12 r13 — 말 구간 카드 2클립'),

  scenes: [
    /* ── 브리지1: 문제의 원인 → 오늘 배울 것 (29.9333s) ── */
    {
      id: 'bridge-intro',
      name: '브리지1 원인과 예고 (29.9333s)',
      duration: 29.933333,
      market: mkMarket(SLICE.introD1), // 인트로 일봉 이월
      chart: {
        ...washBase,
        ma: [
          { type: 'sma', period: 10, width: 7, color: COLOR.ma10 },
          { type: 'sma', period: 34, width: 7, color: COLOR.ma34 },
        ],
        reveal: 137, // 정지 — 인트로와 같은 화면이 워시 아래 은은히
      },
      layers: [
        GROUND10,
        { type: 'cmgText', ...T10, y: 500, size: 96, text: '매매법 자체의 문제가 아닙니다', in: [0.3, 0.35], out: [4.0, 0.4] },
        { type: 'cmgText', ...T10H, y: 360, ...title10('손실의 진짜 이유'), in: [4.5, 0.35], out: [15.6, 0.4] },
        { type: 'cmgText', ...T10, y: 560, size: 80, text: '명확한 진입 · 청산 기준 없이 운영', in: [5.8, 0.35], out: [15.6, 0.4] },
        { type: 'cmgText', ...T10, y: 720, size: 72, text: '기준에 따라 결과는 완전히 달라진다', in: [11.5, 0.35], out: [15.6, 0.4] },
        { type: 'cmgText', ...T10H, y: 310, ...title10('오늘 알려드릴 것'), in: [16.1, 0.35] },
        { type: 'cmgText', ...T10, y: 470, size: 84, text: '① 어떤 기준으로 매매하는가', align: 'left', x: 430, in: [16.7, 0.3], activeAt: 20.1 },
        { type: 'cmgText', ...T10, y: 610, size: 84, text: '② 몇 분봉을 설정하는가', align: 'left', x: 430, in: [16.9, 0.3], activeAt: 21.9 },
        { type: 'cmgText', ...T10, y: 750, size: 84, text: '③ 어떤 보조지표를 쓰는가', align: 'left', x: 430, in: [17.1, 0.3], activeAt: 23.2 },
        { type: 'cmgText', ...T10, y: 872, size: 88, text: '이동평균선 + RSI 눌림목 매매 전략', in: [25.5, 0.4] },
      ],
    },

    /* ── 브리지2: 스윙이 아니라 초단타·스캘핑 (19.0000s) ── */
    {
      id: 'bridge-scalp',
      name: '브리지2 매매 성격 (19.0000s)',
      duration: 19.0,
      market: mkMarket(SLICE.pullbackM1), // 소개·매수 챕터 1분봉 이월
      chart: {
        ...washBase,
        ma: [
          { type: 'sma', period: 10, width: 7, color: COLOR.ma10 },
          { type: 'sma', period: 34, width: 7, color: COLOR.ma34 },
        ],
        reveal: 205, // 정지 — 소개 4컷과 같은 화면
      },
      layers: [
        GROUND10,
        { type: 'cmgText', ...T10, y: 430, size: 72, text: '며칠씩 포지션을 끌고 가는', in: [0.3, 0.3], out: [3.5, 0.4] },
        {
          type: 'cmgText', ...T10, y: 590, size: 108, in: [0.8, 0.35], out: [3.5, 0.4],
          parts: [{ text: '스윙 매매' }, { text: '  ✗', color: '#EF2767' }],
        },
        { type: 'cmgText', ...T10H, y: 320, ...title10('짧은 시간 · 반복 거래'), in: [3.9, 0.35], out: [11.3, 0.4] },
        { type: 'image', src: '/brand/thumbnail/btn_매수.png', x: 274, y: 455, width: 189, in: [4.4, 0.2], out: [11.3, 0.4] },
        { type: 'image', src: '/brand/thumbnail/btn_익절.png', x: 493, y: 455, width: 185, in: [4.7, 0.2], out: [11.3, 0.4] },
        { type: 'image', src: '/brand/thumbnail/btn_매수.png', x: 758, y: 455, width: 189, in: [5.2, 0.2], out: [11.3, 0.4] },
        { type: 'image', src: '/brand/thumbnail/btn_익절.png', x: 977, y: 455, width: 185, in: [5.5, 0.2], out: [11.3, 0.4] },
        { type: 'image', src: '/brand/thumbnail/btn_매수.png', x: 1242, y: 455, width: 189, in: [6.0, 0.2], out: [11.3, 0.4] },
        { type: 'image', src: '/brand/thumbnail/btn_익절.png', x: 1461, y: 455, width: 185, in: [6.3, 0.2], out: [11.3, 0.4] },
        { type: 'cmgText', ...T10, y: 700, size: 96, text: '1분봉  또는  5분봉', in: [7.0, 0.35], out: [11.3, 0.4] },
        { type: 'cmgText', ...T10, y: 840, size: 100, text: '초단타 · 스캘핑', in: [9.2, 0.35], out: [11.3, 0.4] },
        { type: 'cmgText', ...T10, y: 400, size: 72, text: '한 번에 큰 수익을 노리기보다', in: [11.5, 0.3] },
        { type: 'cmgText', ...T10, y: 560, size: 92, text: '짧고 확실한 지점만', in: [13.4, 0.35] },
        { type: 'cmgText', ...T10, y: 725, size: 92, text: '기계적으로 진입 · 청산', in: [15.4, 0.35] },
      ],
    },
  ],
};
