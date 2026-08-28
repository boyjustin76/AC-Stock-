/**
 * 차트명가 숏폼 — [SL_차11-5] 20일선 박스권 매매법 (6컷) · v2
 *
 * 프리미어 숏츠 시퀀스(1080x1920/30fps) 가운데 1:1 박스용. 자막·타이틀·로고 없음.
 * v2 반영 (2026-08-28 사용자·팀장 피드백):
 *   - 박스권 수평선은 검은 선 (팀장 지시)
 *   - '20일선' 라벨은 처음부터
 *   - 휩쏘 손절은 '손절' 텍스트 + 화면 전체 손그림 ✕ (차10·차12 최종본 스타일)
 *   - 상단·하단 선의 등장 모션은 처음 그릴 때 한 번만 — 이후 컷에서는 정지 상태
 *     (growDur 0 + labelDelay -1 이 깜빡임을 없앤다)
 *   - 수익 실현은 초록 '익절' 태그 ('매도'는 숏 전용)
 *
 * 타이밍: 컷편집 내레이션 v3 (out_차11-5_내레이션.wav, 46.03초 — 헛출발·침묵 제거판)
 *   ① 0.00~ 6.87  훅 "박스권 대응법"                     206f
 *   ② 6.87~16.83  휩쏘 — 매수 손절 / 매도 손절 + 큰 ✕      299f
 *   ③ 16.83~26.80 검은 수평선 두 줄 — 새 기준              299f
 *   ④ 26.80~32.13 하단 반등 양봉 → 매수, 손절은 지지 아래    160f
 *   ⑤ 32.13~38.90 상단 노리다 장대 음봉 → 익절              203f
 *   ⑥ 38.90~46.07 CTA "추세장인지 박스권인지"              215f
 *                                                  합계 1382f = 46.067s
 *
 * 마켓(seed 71) 실측:
 *   박스 상단(직전 고점 윗꼬리) 24,238.25 (44번) · 하단(직전 저점 아랫꼬리) 23,960.75 (49번)
 *   가짜 상향 돌파 41~44번 / 가짜 하향 돌파 48~50번 · 하단 재테스트 66번(23,918)
 *   회복 양봉 70번(종가 23,992.25) → 랠리 고점 78번 24,103 → 79번 장대 음봉(직전 양봉을 덮음)
 */

const FPS = 30;
const f = (n) => n / FPS;

const BOX = {
  top: 24238.25,
  bottom: 23960.75,
  buyBar: 70,
  buyPrice: 23992.25,
  stop: 23895, // 지지 라인 아래 (재테스트 꼬리 23,918 밑)
  redBar: 79,
  sellPrice: 24027.75,
};

const LINE = '#111111'; // 박스권 수평선 — 검은 선 (팀장 지시)

const chartBase = {
  visibleBars: 34,
  pricePad: 0.12,
  showGrid: false,
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 0, padBottom: 0, rightGap: 6 },
  ma: [{ type: 'ema', period: 20, width: 5 }],
};

/* 상단·하단 검은 선 — 등장 이후 컷에서는 정지 상태 (깜빡임 방지) */
const topHeld = {
  type: 'cmgLevel', price: BOX.top, fromBar: 41, color: LINE, thickness: 12,
  label: '상단', labelSize: 40, growDur: 0, labelDelay: -1,
};
const bottomHeld = {
  type: 'cmgLevel', price: BOX.bottom, fromBar: 46, color: LINE, thickness: 12,
  label: '하단', labelSize: 40, growDur: 0, labelDelay: -1,
};

export default {
  title: '차트명가 숏폼 — 차11-5 20일선 박스권 6컷 (v2)',
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
      { type: 'trend', dir: 1, bars: 26, strength: 0.6 },
      { type: 'range', bars: 14, width: 1.0 },
      { type: 'trend', dir: 1, bars: 3, strength: 1.5 },
      { type: 'trend', dir: -1, bars: 5, strength: 1.2 },
      { type: 'trend', dir: -1, bars: 3, strength: 1.4 },
      { type: 'trend', dir: 1, bars: 4, strength: 1.1 },
      { type: 'range', bars: 10, width: 0.9 },
      { type: 'trend', dir: -1, bars: 4, strength: 1.1 },
      { type: 'trend', dir: 1, bars: 2, strength: 1.7 },
      { type: 'trend', dir: 1, bars: 8, strength: 0.85 },
      { type: 'trend', dir: -1, bars: 2, strength: 2.4, vol: 1.5 },
      { type: 'range', bars: 9, width: 0.9 },
    ],
  },

  scenes: [
    /* ── ① 훅 — 20일선이 통하지 않는 구간 (0.00~6.87) ───────────── */
    {
      id: 'cut1-hook',
      name: '① 훅 (206f)',
      duration: f(206),
      chart: {
        ...chartBase,
        visibleBars: 36,
        reveal: [
          { t: 0, v: 22 },
          { t: 4.4, v: 38, ease: 'inOutCubic' },
          { t: f(206), v: 40, ease: 'linear' },
        ],
      },
      layers: [
        {
          // '20일선' 라벨은 처음부터 (피드백 반영)
          type: 'cmgNote',
          bar: 20,
          price: 23860,
          dy: 56,
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
          { t: 0, v: 40 },
          { t: 2.0, v: 43, ease: 'inOutCubic' }, // 상향 돌파
          { t: 3.5, v: 48, ease: 'inOutCubic' }, // 되돌림
          { t: 5.0, v: 51, ease: 'inOutCubic' }, // 하향 돌파
          { t: 6.5, v: 55, ease: 'inOutCubic' }, // 복귀
          { t: f(299), v: 56, ease: 'linear' },
        ],
      },
      layers: [
        {
          // "돌파에 매수해서"
          type: 'cmgArrow',
          bar: 42,
          price: 24179.25,
          dir: 'buy',
          label: '매수',
          size: 32,
          gap: 16,
          in: [1.8, 0.3],
          out: [7.5, 0.4],
        },
        {
          type: 'cmgNote',
          bar: 47,
          price: 24040,
          text: '손절',
          size: 46,
          color: '#9F0000',
          in: [3.2, 0.3],
          out: [7.5, 0.4],
        },
        {
          // "다시 돌파에 매도해서" — 하향 돌파는 진짜 숏이라 '매도' 태그가 맞다
          type: 'cmgArrow',
          bar: 50,
          price: 23969.25,
          dir: 'sell',
          label: '매도',
          size: 32,
          gap: 16,
          in: [4.4, 0.3],
          out: [7.5, 0.4],
        },
        {
          type: 'cmgNote',
          bar: 54,
          price: 24110,
          text: '손절',
          size: 46,
          color: '#9F0000',
          in: [5.3, 0.3],
          out: [7.5, 0.4],
        },
        {
          // "양쪽으로 계좌만 깎입니다" — 화면 전체 손그림 ✕ (최종본 스타일)
          type: 'cmgCross',
          width: 36,
          drawDur: 0.55,
          in: [5.95, 0.2],
          out: [7.6, 0.4],
        },
        {
          // "이평선이 눕는 순간 추세가 없다"
          type: 'cmgCircle',
          bar: 48,
          price: 24095,
          rx: 210,
          ry: 66,
          width: 11,
          drawDur: 0.65,
          in: [7.7, 0.2],
        },
        {
          type: 'cmgNote',
          bar: 51,
          price: 24200,
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
        include: [BOX.top + 130, BOX.bottom - 110],
        reveal: [
          { t: 0, v: 56 },
          { t: f(299), v: 62, ease: 'linear' },
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
          bar: 55,
          price: 24095,
          text: '새 기준',
          size: 48,
          color: '#F38808',
          in: [8.5, 0.35],
        },
      ],
    },

    /* ── ④ 하단 반등 양봉 → 매수 (26.80~32.13) ─────────────────── */
    {
      id: 'cut4-buy',
      name: '④ 하단 터치 후 회복 양봉 매수 (160f)',
      duration: f(160),
      chart: {
        ...chartBase,
        include: [BOX.top + 130, BOX.stop - 60],
        reveal: [
          { t: 0, v: 62 },
          { t: 2.8, v: 71, ease: 'inOutCubic' }, // 하단 테스트 → 회복 양봉
          { t: f(160), v: 71.4, ease: 'linear' },
        ],
      },
      layers: [
        topHeld,
        bottomHeld,
        {
          // "다시 올라와 종가를 마감하면" — 회복 양봉 (봉 하나 타점)
          type: 'cmgCircle',
          bar: BOX.buyBar,
          price: 23995,
          rx: 84,
          ry: 112,
          width: 11,
          drawDur: 0.55,
          in: [2.7, 0.2],
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
          // "손절은 지지 라인 아래" — 손절 갈색 선
          type: 'cmgLevel',
          price: BOX.stop,
          fromBar: 64,
          color: '#9F0000',
          thickness: 14,
          label: '손절',
          labelSize: 40,
          in: [4.4, 0.2],
          growDur: 0.4,
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
        include: [BOX.top + 130, BOX.stop - 60],
        reveal: [
          { t: 0, v: 71.4 },
          { t: 1.8, v: 78.4, ease: 'inOutCubic' }, // 상단을 향한 랠리
          { t: 3.2, v: 80, ease: 'inOutCubic' }, // 장대 음봉 등장
          { t: f(203), v: 80.2, ease: 'linear' },
        ],
      },
      layers: [
        topHeld,
        bottomHeld,
        {
          // 진입 이후 평가수익 — 초록 박스 (내가 얼만큼 먹었는지)
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
          // "직전 양봉을 덮는 장대 음봉"
          type: 'cmgCircle',
          bar: BOX.redBar,
          price: 24060,
          rx: 88,
          ry: 122,
          width: 11,
          drawDur: 0.55,
          in: [3.4, 0.2],
        },
        { type: 'flash', at: 5.45, dur: 0.22, strength: 0.4, color: '#14FF36' },
        {
          // "욕심 없이 짧게 수익 실현" — 초록 '익절' 태그
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
        visibleBars: 46,
        include: [BOX.top + 130, BOX.stop - 60],
        reveal: [
          { t: 0, v: 80.2 },
          { t: 4.2, v: 89, ease: 'inOutCubic' },
          { t: f(215), v: 89, ease: 'linear' },
        ],
      },
      layers: [
        topHeld,
        bottomHeld,
        {
          type: 'cmgNote',
          bar: 74,
          price: 24330,
          text: '추세장? 박스권?',
          size: 48,
          color: '#F38808',
          in: [1.3, 0.35],
        },
      ],
    },
  ],
};
