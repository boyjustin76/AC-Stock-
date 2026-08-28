/**
 * 차트명가 숏폼 — [SL_차11-5] 20일선 박스권 매매법 (6컷) · v3
 *
 * 프리미어 숏츠 시퀀스(1080x1920/30fps) 가운데 1:1 박스용. 자막·타이틀·로고 없음.
 * v3 반영 (2026-08-29 피드백):
 *   - 마켓 재튜닝(seed 73, 박스 22봉): 휩쏘 대사 때 화면이 추세가 아니라
 *     '박스권 + 눕는 이평선'으로 보이게. 가짜 상향(+44pt)·가짜 하향(-86pt) 모두
 *     박스를 실제로 뚫고, 장대 음봉(87번, 몸통 114pt)은 상단을 윗꼬리로 찍고 무너진다
 *   - 두 번째 '손절' 등장을 낭독 싱크에 타이트하게 (12.3초 어절에 맞춤)
 *   - '손절' 라인(지지 아래)을 다음 컷(⑤)까지 유지
 *   - 컷 경계 줌 끊김 제거: visibleBars 34 통일, 경계 (reveal,줌폭) 일치,
 *     컷⑥ 줌아웃은 컷 안에서 애니메이션
 *
 * 타이밍: 컷편집 내레이션 v3 (46.03초)
 *   ① 0.00~ 6.87  훅                                    206f  (r22→46)
 *   ② 6.87~16.83  휩쏘 — 매수 손절 / 매도 손절 + 큰 ✕      299f  (r46→63)
 *   ③ 16.83~26.80 검은 수평선 두 줄 — 새 기준              299f  (r63→68)
 *   ④ 26.80~32.13 하단 반등 양봉 → 매수, 손절 라인          160f  (r68→78.4)
 *   ⑤ 32.13~38.90 상단 노리다 장대 음봉 → 익절              203f  (r78.4→88.2)
 *   ⑥ 38.90~46.07 CTA (줌아웃)                           215f  (r88.2→97, z→0.74)
 *                                                  합계 1382f = 46.067s
 *
 * 마켓(seed 73) 실측:
 *   박스(26~47) 24,014.5 / 23,836.5 · 상단 꼬리 24,058 (50번) · 하단 꼬리 23,751 (58번)
 *   재테스트 저점 23,710.75 (76번) → 회복 양봉 77·78번 (78번 종가 23,802.5 매수)
 *   랠리 고점 24,044.75 (85번, 상단 13pt 앞) → 87번 장대 음봉 o24,029 c23,915 (h24,058.75 로 상단 터치)
 */

const FPS = 30;
const f = (n) => n / FPS;

const BOX = {
  top: 24058, // 직전 고점의 윗꼬리 (50번)
  bottom: 23751, // 직전 저점의 아랫꼬리 (58번)
  buyBar: 78,
  buyPrice: 23802.5,
  stop: 23690, // 지지 라인 아래 (재테스트 꼬리 23,710.75 밑)
  redBar: 87,
  sellPrice: 23915.25,
};

const LINE = '#111111'; // 박스권 수평선 — 검은 선 (팀장 지시)

const chartBase = {
  visibleBars: 34,
  pricePad: 0.12,
  showGrid: false,
  showAxes: false,
  showLast: false,
  include: [BOX.top + 130, BOX.stop - 60],
  layout: { padLeft: 0, padRight: 0, padTop: 0, padBottom: 0, rightGap: 6 },
  ma: [{ type: 'ema', period: 20, width: 5 }],
};

/* 상단·하단 검은 선 — 등장 이후 컷에서는 정지 상태 */
const topHeld = {
  type: 'cmgLevel', price: BOX.top, fromBar: 42, color: LINE, thickness: 12,
  label: '상단', labelSize: 40, growDur: 0, labelDelay: -1,
};
const bottomHeld = {
  type: 'cmgLevel', price: BOX.bottom, fromBar: 52, color: LINE, thickness: 12,
  label: '하단', labelSize: 40, growDur: 0, labelDelay: -1,
};
/* 손절 라인 — ④에서 그어지고 ⑤까지 유지 (피드백) */
const stopHeld = {
  type: 'cmgLevel', price: BOX.stop, fromBar: 72, color: '#9F0000', thickness: 14,
  label: '손절', labelSize: 40, growDur: 0, labelDelay: -1,
};

export default {
  title: '차트명가 숏폼 — 차11-5 20일선 박스권 6컷 (v3)',
  width: 1080,
  height: 1080,
  fps: FPS,

  theme: { preset: 'chartmyeongga' },

  market: {
    seed: 73,
    base: 23600,
    tick: 0.25,
    vol: 55,
    barMinutes: 1440,
    startTime: Date.UTC(2026, 2, 2, 0, 0),
    segments: [
      { type: 'trend', dir: 1, bars: 26, strength: 0.6 }, // 이평선이 살아있던 추세
      { type: 'range', bars: 22, width: 1.0 }, // 26-47 눕는 박스 (길게)
      { type: 'trend', dir: 1, bars: 3, strength: 1.5 }, // 48-50 가짜 상향 돌파
      { type: 'trend', dir: -1, bars: 5, strength: 1.2 }, // 51-55 되돌림
      { type: 'trend', dir: -1, bars: 3, strength: 1.4 }, // 56-58 가짜 하향 돌파
      { type: 'trend', dir: 1, bars: 4, strength: 1.1 }, // 59-62 복귀
      { type: 'range', bars: 10, width: 0.9 }, // 63-72 안정
      { type: 'trend', dir: -1, bars: 4, strength: 1.1 }, // 73-76 하단 재테스트
      { type: 'trend', dir: 1, bars: 2, strength: 1.7 }, // 77-78 회복 양봉
      { type: 'trend', dir: 1, bars: 8, strength: 0.85 }, // 79-86 랠리
      { type: 'trend', dir: -1, bars: 2, strength: 2.4, vol: 1.5 }, // 87-88 장대 음봉
      { type: 'range', bars: 9, width: 0.9 }, // 89-97 CTA
    ],
  },

  scenes: [
    /* ── ① 훅 (0.00~6.87) ──────────────────────────────────────── */
    {
      id: 'cut1-hook',
      name: '① 훅 (206f)',
      duration: f(206),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 22 },
          { t: 4.6, v: 44, ease: 'inOutCubic' },
          { t: f(206), v: 46, ease: 'linear' },
        ],
      },
      layers: [
        {
          type: 'cmgNote',
          bar: 24,
          price: 23680,
          dy: 30,
          text: '20일선',
          size: 44,
          color: '#F38808',
          in: [0.4, 0.35],
        },
      ],
    },

    /* ── ② 휩쏘 — 양쪽으로 계좌만 깎인다 (6.87~16.83) ───────────── */
    {
      id: 'cut2-whipsaw',
      name: '② 매수 손절 / 매도 손절 + 큰 ✕ (299f)',
      duration: f(299),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 46 },
          { t: 2.4, v: 51, ease: 'inOutCubic' }, // 상향 돌파
          { t: 3.4, v: 56, ease: 'inOutCubic' }, // 되돌림
          { t: 4.7, v: 59, ease: 'inOutCubic' }, // 하향 돌파
          { t: 6.3, v: 63, ease: 'inOutCubic' }, // 복귀
          { t: f(299), v: 63, ease: 'linear' },
        ],
      },
      layers: [
        {
          // "이평선이 옆으로 누워버리면" — 누운 구간만 접선처럼 굵게 덧칠 (팀장 기법)
          type: 'cmgTrace',
          fromBar: 39,
          toBar: 50,
          flatten: 0.65,
          width: 16,
          in: [1.55, 0.2],
          drawDur: 0.7,
          out: [7.5, 0.4],
        },
        {
          // "돌파에 매수해서" (내레이션 9.4)
          type: 'cmgArrow',
          bar: 50,
          price: 24015.25,
          dir: 'buy',
          label: '매수',
          size: 32,
          gap: 16,
          in: [2.5, 0.3],
          out: [7.5, 0.4],
        },
        {
          // 첫 번째 "손절" (내레이션 10.19~10.93)
          type: 'cmgNote',
          bar: 53,
          price: 24120,
          text: '손절',
          size: 46,
          color: '#9F0000',
          in: [3.22, 0.15],
          out: [7.5, 0.4],
        },
        {
          // "다시 돌파에 매도해서" — 하향 돌파, 진짜 숏이라 '매도'
          type: 'cmgArrow',
          bar: 58,
          price: 23780.25,
          dir: 'sell',
          label: '매도',
          size: 32,
          gap: 16,
          in: [4.75, 0.3],
          out: [7.5, 0.4],
        },
        {
          // 두 번째 "손절" (내레이션 12.3~12.77 — 어절에 딱 맞춤)
          type: 'cmgNote',
          bar: 61,
          price: 23680,
          text: '손절',
          size: 46,
          color: '#9F0000',
          in: [5.05, 0.15],
          out: [7.5, 0.4],
        },
        {
          // "양쪽으로 계좌만 깎입니다" — 화면 전체 손그림 ✕
          type: 'cmgCross',
          width: 36,
          drawDur: 0.55,
          in: [5.95, 0.2],
          out: [7.6, 0.4],
        },
        {
          // "이평선이 눕는 순간 추세가 없다"
          type: 'cmgCircle',
          bar: 52,
          price: 23915,
          rx: 230,
          ry: 64,
          width: 11,
          drawDur: 0.65,
          in: [7.7, 0.2],
        },
        {
          type: 'cmgNote',
          bar: 58,
          price: 24140,
          text: '추세 없음',
          size: 46,
          color: '#F38808',
          in: [8.5, 0.35],
        },
      ],
    },

    /* ── ③ 검은 수평선 두 줄 — 새 기준 (16.83~26.80) ────────────── */
    {
      id: 'cut3-lines',
      name: '③ 박스 상단·하단 수평선 (299f)',
      duration: f(299),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 63 },
          { t: f(299), v: 68, ease: 'linear' },
        ],
      },
      layers: [
        {
          // "직전 고점의 윗꼬리와" — 여기서 딱 한 번 그어진다
          ...topHeld,
          growDur: 0.5,
          labelDelay: 0.12,
          in: [3.8, 0.2],
        },
        {
          // "직전 저점의 아랫꼬리에"
          ...bottomHeld,
          growDur: 0.5,
          labelDelay: 0.12,
          in: [5.6, 0.2],
        },
        {
          // "이 두 줄 사이가 새 기준"
          type: 'zone',
          from: BOX.top,
          to: BOX.bottom,
          color: '#F38808',
          opacity: 0.09,
          in: [8.0, 0.4],
        },
        {
          type: 'cmgNote',
          bar: 57,
          price: 23935,
          text: '새 기준',
          size: 48,
          color: '#F38808',
          in: [8.5, 0.35],
        },
      ],
    },

    /* ── ④ 하단 반등 양봉 → 매수, 손절 라인 (26.80~32.13) ────────── */
    {
      id: 'cut4-buy',
      name: '④ 하단 터치 후 회복 양봉 매수 (160f)',
      duration: f(160),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 68 },
          { t: 0.5, v: 73, ease: 'inOutCubic' },
          { t: 2.6, v: 78.3, ease: 'inOutCubic' }, // 하단 테스트 → 회복 양봉
          { t: f(160), v: 78.4, ease: 'linear' },
        ],
      },
      layers: [
        topHeld,
        bottomHeld,
        {
          // "다시 올라와 종가를 마감하면" — 회복 양봉 (봉 하나 타점)
          type: 'cmgCircle',
          bar: 77,
          price: 23770,
          rx: 96,
          ry: 100,
          width: 11,
          drawDur: 0.55,
          in: [2.6, 0.2],
        },
        {
          type: 'cmgArrow',
          bar: BOX.buyBar,
          price: BOX.buyPrice,
          dir: 'buy',
          label: '매수',
          size: 32,
          gap: 16,
          in: [3.5, 0.35],
        },
        {
          // "손절은 지지 라인 아래" — ⑤까지 유지된다
          ...stopHeld,
          growDur: 0.4,
          labelDelay: 0.12,
          in: [4.4, 0.2],
        },
      ],
    },

    /* ── ⑤ 상단 노리다 장대 음봉 → 익절 (32.13~38.90) ───────────── */
    {
      id: 'cut5-take',
      name: '⑤ 장대 음봉 익절 (203f)',
      duration: f(203),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 78.4 },
          { t: 1.8, v: 85.4, ease: 'inOutCubic' }, // 상단을 향한 랠리
          { t: 3.2, v: 88, ease: 'inOutCubic' }, // 장대 음봉
          { t: f(203), v: 88.2, ease: 'linear' },
        ],
      },
      layers: [
        topHeld,
        bottomHeld,
        stopHeld, // 손절 라인 유지 (피드백)
        {
          type: 'cmgProfit',
          entry: BOX.buyPrice,
          fromBar: BOX.buyBar,
          in: [0, 0.25],
        },
        {
          type: 'cmgArrow',
          bar: BOX.buyBar,
          price: BOX.buyPrice,
          dir: 'buy',
          label: '매수',
          size: 32,
          gap: 16,
          popDur: 0,
        },
        {
          // "직전 양봉을 덮는 장대 음봉" — 상단을 윗꼬리로 찍고 무너진다
          type: 'cmgCircle',
          bar: BOX.redBar,
          price: 23985,
          rx: 90,
          ry: 130,
          width: 11,
          drawDur: 0.55,
          in: [3.4, 0.2],
        },
        { type: 'flash', at: 5.45, dur: 0.22, strength: 0.4, color: '#14FF36' },
        {
          type: 'cmgArrow',
          bar: BOX.redBar,
          price: BOX.sellPrice,
          dir: 'sell',
          label: '익절',
          color: '#0DA82A',
          size: 32,
          gap: 16,
          in: [5.5, 0.35],
        },
      ],
    },

    /* ── ⑥ CTA — 추세장인지 박스권인지 (38.90~46.07) ────────────── */
    {
      id: 'cut6-cta',
      name: '⑥ CTA (215f)',
      duration: f(215),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 88.2 },
          { t: 4.2, v: 97, ease: 'inOutCubic' },
          { t: f(215), v: 97, ease: 'linear' },
        ],
        zoom: [
          { t: 0, v: 1 },
          { t: 4.2, v: 0.74, ease: 'inOutCubic' }, // 컷 안에서 줌아웃 (끊김 없이)
        ],
      },
      layers: [
        topHeld,
        bottomHeld,
        {
          // 마무리 — 화면이 살짝 어두워지며 정중앙에 크게 (최종본 엔딩 스타일)
          type: 'titleCard',
          title: '추세장? 박스권?',
          size: 104,
          color: '#FFFFFF',
          scrimStrength: 0.85,
          in: [1.4, 0.45],
        },
      ],
    },
  ],
};
