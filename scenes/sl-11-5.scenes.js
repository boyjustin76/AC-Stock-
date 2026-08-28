/**
 * 차트명가 숏폼 — [SL_차11-5] 20일선 박스권 매매법 (6컷)
 *
 * 프리미어 숏츠 시퀀스(1080x1920/30fps) 가운데 1:1 박스용. 자막·타이틀·로고 없음.
 * 타이밍은 컷편집 내레이션(out_차11-5_내레이션.wav, 50.58초) 문장 타임코드 기준.
 *   ① 0.00~ 7.40  훅 "박스권 대응법"                      222f
 *   ② 7.40~19.00 휩쏘 — 돌파 매수 손절 / 돌파 매도 손절     348f
 *   ③ 19.00~29.87 수평선 두 줄 — 새 기준                   326f
 *   ④ 29.87~35.40 하단 반등 양봉 → 매수, 손절은 지지 아래    166f
 *   ⑤ 35.40~43.30 상단 노리다 장대 음봉 → 짧게 실현          237f
 *   ⑥ 43.30~50.63 CTA "추세장인지 박스권인지"               220f
 *                                                    합계 1519f = 50.633s
 *   (내레이션 50.58초 — 무음 보정판. '누워버리면' 뒤 2.8초 침묵을 잘랐다)
 *
 * 마켓(seed 71) 실측:
 *   박스 상단(직전 고점 윗꼬리) 24,238.25 (44번) · 하단(직전 저점 아랫꼬리) 23,960.75 (49번)
 *   가짜 상향 돌파 41~44번 → 되돌림 / 가짜 하향 돌파 48~50번 → 복귀
 *   하단 재테스트 66번(저점 23,918 — 라인 관통 후 회복) → 70번 양봉 종가 23,992.25 매수
 *   랠리 고점 78번 24,103 (상단까지 135pt 남김) → 79번 장대 음봉(직전 양봉 몸통을 덮음)
 */

const FPS = 30;
const f = (n) => n / FPS;

const BOX = {
  top: 24238.25, // 직전 고점의 윗꼬리
  bottom: 23960.75, // 직전 저점의 아랫꼬리
  buyBar: 70,
  buyPrice: 23992.25,
  stop: 23895, // 지지 라인 아래 (재테스트 꼬리 23,918 밑)
  redBar: 79,
  sellPrice: 24027.75, // 장대 음봉 종가 — 짧게 실현
};

const chartBase = {
  visibleBars: 34,
  pricePad: 0.12,
  showGrid: false,
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 0, padBottom: 0, rightGap: 6 },
  ma: [{ type: 'ema', period: 20, width: 5 }],
};

export default {
  title: '차트명가 숏폼 — 차11-5 20일선 박스권 6컷',
  width: 1080,
  height: 1080,
  fps: FPS,

  theme: { preset: 'chartmyeongga' },

  market: {
    seed: 71,
    base: 23600,
    tick: 0.25,
    vol: 55,
    barMinutes: 1440,
    startTime: Date.UTC(2026, 2, 2, 0, 0),
    segments: [
      { type: 'trend', dir: 1, bars: 26, strength: 0.6 }, // 이평선이 살아있던 추세
      { type: 'range', bars: 14, width: 1.0 }, // 눕기 시작
      { type: 'trend', dir: 1, bars: 3, strength: 1.5 }, // 가짜 상향 돌파
      { type: 'trend', dir: -1, bars: 5, strength: 1.2 }, // 되돌림 (매수 손절)
      { type: 'trend', dir: -1, bars: 3, strength: 1.4 }, // 가짜 하향 돌파
      { type: 'trend', dir: 1, bars: 4, strength: 1.1 }, // 복귀 (매도 손절)
      { type: 'range', bars: 10, width: 0.9 }, // 안정 — 여기서 수평선을 긋는다
      { type: 'trend', dir: -1, bars: 4, strength: 1.1 }, // 하단 재테스트
      { type: 'trend', dir: 1, bars: 2, strength: 1.7 }, // 회복 양봉 → 매수
      { type: 'trend', dir: 1, bars: 8, strength: 0.85 }, // 상단으로 랠리
      { type: 'trend', dir: -1, bars: 2, strength: 2.4, vol: 1.5 }, // 장대 음봉
      { type: 'range', bars: 9, width: 0.9 }, // CTA
    ],
  },

  scenes: [
    /* ── ① 훅 — 20일선이 통하지 않는 구간 (0.00~7.40) ────────────── */
    {
      id: 'cut1-hook',
      name: '① 훅 (222f)',
      duration: f(222),
      chart: {
        ...chartBase,
        visibleBars: 36,
        reveal: [
          { t: 0, v: 22 },
          { t: 4.6, v: 38, ease: 'inOutCubic' },
          { t: f(222), v: 40, ease: 'linear' },
        ],
      },
      layers: [
        {
          type: 'cmgNote',
          bar: 20,
          price: 23860,
          dy: 56,
          text: '20일선',
          size: 44,
          color: '#F38808',
          in: [3.4, 0.35],
        },
      ],
    },

    /* ── ② 휩쏘 — 양쪽으로 계좌만 깎인다 (7.40~22.70) ───────────── */
    {
      id: 'cut2-whipsaw',
      name: '② 돌파 매수 손절 / 돌파 매도 손절 (348f)',
      duration: f(348),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 40 },
          { t: 2.0, v: 43, ease: 'inOutCubic' }, // 상향 돌파
          { t: 3.9, v: 48, ease: 'inOutCubic' }, // 되돌림
          { t: 5.2, v: 51, ease: 'inOutCubic' }, // 하향 돌파
          { t: 7.2, v: 55, ease: 'inOutCubic' }, // 복귀
          { t: f(348), v: 56, ease: 'linear' },
        ],
      },
      layers: [
        {
          // "돌파에 매수해서" (내레이션 9.9 → 컷 내 2.5)
          type: 'cmgArrow',
          bar: 42,
          price: 24179.25,
          dir: 'buy',
          label: '매수',
          size: 32,
          gap: 16,
          in: [2.0, 0.3],
          out: [8.7, 0.4],
        },
        {
          // "손절" — 매수가 깨진다
          type: 'cmgNote',
          bar: 47,
          price: 24040,
          text: '손절 ✕',
          size: 46,
          color: '#9F0000',
          in: [4.3, 0.3],
          out: [8.7, 0.4],
        },
        {
          // "다시 돌파에 매도해서" (내레이션 13.3 → 컷 내 5.9)
          type: 'cmgArrow',
          bar: 50,
          price: 23969.25,
          dir: 'sell',
          label: '매도',
          size: 32,
          gap: 16,
          in: [5.0, 0.3],
          out: [8.7, 0.4],
        },
        {
          // "손절" — 매도도 깨진다
          type: 'cmgNote',
          bar: 54,
          price: 24110,
          text: '손절 ✕',
          size: 46,
          color: '#9F0000',
          in: [6.3, 0.3],
          out: [8.7, 0.4],
        },
        {
          // "이평선이 눕는 순간 추세가 없다" (내레이션 18.9 → 컷 내 11.5)
          type: 'cmgCircle',
          bar: 48,
          price: 24095,
          rx: 210,
          ry: 66,
          width: 11,
          drawDur: 0.65,
          in: [8.9, 0.2],
        },
        {
          type: 'cmgNote',
          bar: 51,
          price: 24200,
          text: '추세 없음',
          size: 46,
          color: '#F38808',
          in: [9.6, 0.35],
        },
      ],
    },

    /* ── ③ 수평선 두 줄 — 새 기준 (22.70~34.00) ─────────────────── */
    {
      id: 'cut3-lines',
      name: '③ 박스 상단·하단 수평선 (326f)',
      duration: f(326),
      chart: {
        ...chartBase,
        include: [BOX.top + 130, BOX.bottom - 110],
        reveal: [
          { t: 0, v: 56 },
          { t: f(326), v: 62, ease: 'linear' },
        ],
      },
      layers: [
        {
          // "직전 고점의 윗꼬리와" (내레이션 27.1 → 컷 내 4.4)
          type: 'cmgLevel',
          price: BOX.top,
          fromBar: 41,
          color: '#9F0000',
          thickness: 14,
          label: '상단',
          labelSize: 42,
          in: [4.4, 0.2],
          growDur: 0.5,
        },
        {
          // "직전 저점의 아랫꼬리에" (내레이션 29.2 → 컷 내 6.5)
          type: 'cmgLevel',
          price: BOX.bottom,
          fromBar: 46,
          color: '#0B8C7F',
          thickness: 14,
          label: '하단',
          labelSize: 42,
          in: [6.0, 0.2],
          growDur: 0.5,
        },
        {
          // "이 두 줄 사이가 새 기준" (내레이션 31.6 → 컷 내 8.9)
          type: 'zone',
          from: BOX.top,
          to: BOX.bottom,
          color: '#F38808',
          opacity: 0.1,
          in: [8.6, 0.4],
        },
        {
          type: 'cmgNote',
          bar: 55,
          price: 24095,
          text: '새 기준',
          size: 48,
          color: '#F38808',
          in: [9.1, 0.35],
        },
      ],
    },

    /* ── ④ 하단 반등 양봉 → 매수 (34.00~40.37) ─────────────────── */
    {
      id: 'cut4-buy',
      name: '④ 하단 터치 후 회복 양봉 매수 (166f)',
      duration: f(166),
      chart: {
        ...chartBase,
        include: [BOX.top + 130, BOX.stop - 60],
        reveal: [
          { t: 0, v: 62 },
          { t: 3.2, v: 71, ease: 'inOutCubic' }, // 하단 테스트 → 회복 양봉
          { t: f(166), v: 71.4, ease: 'linear' },
        ],
      },
      layers: [
        { type: 'cmgLevel', price: BOX.top, fromBar: 41, color: '#9F0000', thickness: 14, label: '상단', labelSize: 42, popDur: 0 },
        { type: 'cmgLevel', price: BOX.bottom, fromBar: 46, color: '#0B8C7F', thickness: 14, label: '하단', labelSize: 42, popDur: 0 },
        {
          // "다시 올라와 종가를 마감하면" — 회복 양봉
          type: 'cmgCircle',
          bar: BOX.buyBar,
          price: 23995,
          rx: 84,
          ry: 112,
          width: 11,
          drawDur: 0.55,
          in: [2.9, 0.2],
        },
        {
          type: 'cmgArrow',
          bar: BOX.buyBar,
          price: BOX.buyPrice,
          dir: 'buy',
          label: '매수',
          size: 32,
          gap: 16,
          in: [3.6, 0.35],
        },
        {
          // "손절은 지지 라인 아래" (내레이션 38.9 → 컷 내 4.9)
          type: 'cmgLevel',
          price: BOX.stop,
          fromBar: 64,
          color: '#9F0000',
          thickness: 14,
          label: '손절',
          labelSize: 42,
          in: [4.1, 0.2],
          growDur: 0.4,
        },
      ],
    },

    /* ── ⑤ 상단 노리다 장대 음봉 → 짧게 실현 (40.37~48.03) ───────── */
    {
      id: 'cut5-take',
      name: '⑤ 장대 음봉 짧은 실현 (237f)',
      duration: f(237),
      chart: {
        ...chartBase,
        include: [BOX.top + 130, BOX.stop - 60],
        reveal: [
          { t: 0, v: 71.4 },
          { t: 2.2, v: 78.4, ease: 'inOutCubic' }, // 상단을 향한 랠리
          { t: 3.6, v: 80, ease: 'inOutCubic' }, // 장대 음봉 등장
          { t: f(237), v: 80.2, ease: 'linear' },
        ],
      },
      layers: [
        { type: 'cmgLevel', price: BOX.top, fromBar: 41, color: '#9F0000', thickness: 14, label: '상단', labelSize: 42, popDur: 0 },
        { type: 'cmgLevel', price: BOX.bottom, fromBar: 46, color: '#0B8C7F', thickness: 14, label: '하단', labelSize: 42, popDur: 0 },
        { type: 'cmgProfit', entry: BOX.buyPrice, fromBar: BOX.buyBar, in: [0, 0.25] },
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
          // "직전 양봉을 덮는 장대 음봉" (내레이션 43.5 → 컷 내 3.1)
          type: 'cmgCircle',
          bar: BOX.redBar,
          price: 24060,
          rx: 88,
          ry: 122,
          width: 11,
          drawDur: 0.55,
          in: [3.8, 0.2],
        },
        { type: 'flash', at: 6.1, dur: 0.22, strength: 0.4, color: '#14FF36' },
        {
          // "욕심 없이 짧게 수익 실현"
          type: 'cmgArrow',
          bar: BOX.redBar,
          price: BOX.sellPrice,
          dir: 'sell',
          label: '실현',
          size: 32,
          gap: 16,
          in: [6.15, 0.35],
        },
      ],
    },

    /* ── ⑥ CTA — 추세장인지 박스권인지 (48.03~56.20) ────────────── */
    {
      id: 'cut6-cta',
      name: '⑥ CTA (220f)',
      duration: f(220),
      chart: {
        ...chartBase,
        visibleBars: 46,
        include: [BOX.top + 130, BOX.stop - 60],
        reveal: [
          { t: 0, v: 80.2 },
          { t: 4.6, v: 89, ease: 'inOutCubic' },
          { t: f(220), v: 89, ease: 'linear' },
        ],
      },
      layers: [
        { type: 'cmgLevel', price: BOX.top, fromBar: 41, color: '#9F0000', thickness: 14, label: '상단', labelSize: 42, popDur: 0 },
        { type: 'cmgLevel', price: BOX.bottom, fromBar: 46, color: '#0B8C7F', thickness: 14, label: '하단', labelSize: 42, popDur: 0 },
        {
          // "추세장인지 박스권인지 무엇으로 걸러낼까?"
          type: 'cmgNote',
          bar: 74,
          price: 24330,
          text: '추세장? 박스권?',
          size: 48,
          color: '#F38808',
          in: [1.6, 0.35],
        },
      ],
    },
  ],
};
