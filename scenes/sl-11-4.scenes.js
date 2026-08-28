/**
 * 차트명가 숏폼 — [SL_차11-4] 20일선 추세추종 매매법 (5컷) · v3
 *
 * 프리미어 숏츠 시퀀스(1080x1920/30fps) 가운데 1:1 박스용. 자막·타이틀·로고 없음.
 * v3 반영 (2026-08-29 피드백):
 *   - 손익비 컷에 '놓친 구간' 빨간 빗금(cmgMissed) 추가 — 익절 후 추세가 24,418 까지
 *     내달리는 것을 같은 클립에서 보여준다 (팀장: "이만큼 더 먹을 수 있었는데")
 *   - 줌인/줌아웃이 컷 경계에서 뚝 끊기지 않게: 전 컷 visibleBars 32 로 통일하고
 *     경계에서 (reveal, 줌폭)을 일치시킨 뒤, 줌 전환은 컷 안에서 애니메이션한다.
 *     · 컷1끝(r43,z1) = 컷2첫 프레임
 *     · 컷2 꼬리에서 스우프(z1→1.4545, r63→45.5) = 컷3첫 프레임
 *     · 컷3끝(r45.5,z1.4545) = 컷4첫 프레임, 컷4 안에서 z→0.55 줌아웃
 *     · 컷4끝(r104.5,z0.55) = 컷5첫 프레임, 컷5 안에서 z→0.8
 *
 * 타이밍: 컷편집 내레이션 v3 (43.37초)
 *   ① 0.00~ 8.17  훅 + "눌림목 진입까지는 성공"          245f  (r30→43)
 *   ② 8.17~14.05  "1:2 팔아버림" + 놓친 구간 + 스우프     176f  (r43→63→45.5)
 *   ③ 14.05~22.93 "진입 조건 두 가지" (줌인 유지)         266f  (r45.5, z1.4545)
 *   ④ 22.93~36.83 "손절 / 이격 음봉 익절" (줌아웃)        417f  (r45.5→104.2, z→0.55)
 *   ⑤ 36.83~43.40 CTA "박스권에서는?"                    197f  (r104.5→121, z→0.8)
 *                                                  합계 1301f = 43.367s
 */

const FPS = 30;
const f = (n) => n / FPS;

/* 매매 수치 — 러너와 동일 seed 11 실측 */
const LV = {
  entry: 23795, // 42번 캔들
  stop: 23665, // 41번 아래꼬리(23,677.75) 밑
  get target() { return this.entry + (this.entry - this.stop) * 2; }, // 24,055
  missedHigh: 24418.25, // 익절 후 추세 고점 (62번)
  exitBar: 103,
  exitClose: 24831.75,
};

const COLOR = {
  tp: '#14FF36',
  tpFill: '#BAFDC0',
  sl: '#9F0000',
  slFill: '#FEBABA',
};

const ZOOM_IN = 32 / 22; // 컷3 의 줌인 배율 (22봉 폭)

const chartBase = {
  visibleBars: 32,
  pricePad: 0.14,
  showGrid: false,
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 0, padBottom: 0, rightGap: 6 },
  ma: [{ type: 'ema', period: 20, width: 5 }],
};

const buyArrowBase = {
  type: 'cmgArrow',
  bar: 42,
  price: LV.entry,
  dir: 'buy',
  label: '매수',
  size: 32,
  gap: 16,
};
const buyArrowHeld = { ...buyArrowBase, popDur: 0 };

export default {
  title: '차트명가 숏폼 — 차11-4 20일선 추세추종 5컷 (v3)',
  width: 1080,
  height: 1080,
  fps: FPS,

  theme: { preset: 'chartmyeongga' },

  market: {
    seed: 11,
    base: 23400,
    tick: 0.25,
    vol: 58,
    barMinutes: 1440,
    startTime: Date.UTC(2026, 0, 5, 0, 0),
    segments: [
      { type: 'trend', dir: 1, bars: 34, strength: 0.52 },
      { type: 'pullback', dir: 1, bars: 9, strength: 1.15 },
      { type: 'trend', dir: 1, bars: 52, strength: 0.82 },
      { type: 'trend', dir: -1, bars: 8, strength: 1.05 },
      { type: 'range', bars: 18, width: 1.1 },
    ],
  },

  scenes: [
    /* ── ① 훅 + 눌림목 진입까지는 성공 (0.00~8.17) ───────────────── */
    {
      id: 'cut1-hook-entry',
      name: '① 훅 + 눌림목 진입 (245f)',
      duration: f(245),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 30 },
          { t: 4.2, v: 42.2, ease: 'inOutCubic' },
          { t: f(245), v: 43, ease: 'linear' },
        ],
      },
      layers: [
        {
          type: 'cmgNote',
          bar: 26,
          price: 23533,
          dy: 56,
          text: '20일선',
          size: 44,
          color: '#F38808',
          in: [0.5, 0.35],
        },
        {
          type: 'cmgCircle',
          bar: 41,
          price: 23706,
          rx: 132,
          ry: 106,
          width: 11,
          drawDur: 0.6,
          in: [4.3, 0.2],
          out: [7.5, 0.4],
        },
        { ...buyArrowBase, in: [5.8, 0.35] },
      ],
    },

    /* ── ② 1:2 팔아버림 → 놓친 구간 → 스우프 줌인 (8.17~14.05) ───── */
    {
      id: 'cut2-early-exit',
      name: '② 1:2 조기 익절 + 놓친 구간 (176f)',
      duration: f(176),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 43 },
          { t: 3.2, v: 50, ease: 'linear' },
          { t: 4.6, v: 63, ease: 'inOutCubic' }, // 익절 뒤 추세가 내달린다
          { t: 5.15, v: 63 },
          { t: 5.85, v: 45.5, ease: 'inOutCubic' }, // 스우프 — 컷3 프레이밍으로
        ],
        zoom: [
          { t: 0, v: 1 },
          { t: 5.15, v: 1 },
          { t: 5.85, v: ZOOM_IN, ease: 'inOutCubic' },
        ],
      },
      layers: [
        { ...buyArrowHeld, out: [5.0, 0.4] },
        {
          // 익절 초록 박스 — 선과 테두리가 포개진다
          type: 'cmgLevel',
          price: LV.target,
          fillTo: LV.entry,
          fill: COLOR.tpFill,
          color: COLOR.tp,
          label: '익절',
          labelSize: 40,
          thickness: 14,
          fromBar: 42,
          in: [0.3, 0.2],
          out: [5.15, 0.35],
          growDur: 0.4,
        },
        {
          // 손절 갈색 박스 — 1:2 비율이 한눈에
          type: 'cmgLevel',
          price: LV.stop,
          fillTo: LV.entry,
          fill: COLOR.slFill,
          color: COLOR.sl,
          label: '손절',
          labelSize: 40,
          thickness: 14,
          fromBar: 42,
          in: [0.7, 0.2],
          out: [5.15, 0.35],
          growDur: 0.4,
        },
        {
          type: 'cmgLevel',
          price: LV.entry,
          fromBar: 42,
          color: 'rgba(0,0,0,0.72)',
          thickness: 4,
          in: [0.3, 0.2],
          out: [5.15, 0.35],
          growDur: 0.4,
        },
        {
          type: 'cmgBadge',
          text: '손익비  1 : 2',
          x: 64,
          y: 1004,
          size: 46,
          color: '#E90054',
          border: false,
          in: [1.3, 0.3],
          out: [5.15, 0.35],
        },
        { type: 'flash', at: 3.25, dur: 0.22, strength: 0.4, color: COLOR.tp },
        {
          type: 'cmgArrow',
          bar: 53,
          price: LV.target,
          dir: 'sell',
          label: '익절',
          color: '#0DA82A',
          size: 32,
          gap: 16,
          in: [3.3, 0.35],
          out: [5.15, 0.35],
        },
        {
          // "이만큼 더 먹을 수 있었다" — 놓친 구간 빨간 빗금 (팀장 지시)
          type: 'cmgMissed',
          from: LV.target,
          to: LV.missedHigh,
          fromBar: 53,
          color: '#E90054',
          arrow: false,
          growDur: 0.9,
          in: [3.55, 0.3],
          out: [5.15, 0.35],
        },
        {
          // 롱폼 러너 컷4와 같은 기법 — 빗금 안에 크게 + 빨간 손그림 밑줄
          type: 'cmgNote',
          bar: 57,
          price: 24270,
          text: '놓친 구간',
          size: 58,
          in: [4.05, 0.3],
          out: [5.15, 0.35],
        },
        {
          type: 'cmgUnderline',
          bar: 57,
          price: 24270,
          dy: 46,
          width: 300,
          align: 'center',
          in: [4.3, 0.2],
          drawDur: 0.35,
          out: [5.15, 0.35],
        },
      ],
    },

    /* ── ③ 진입 조건 두 가지 — 줌인 유지 (14.05~22.93) ──────────── */
    {
      id: 'cut3-conditions',
      name: '③ 진입 조건 기울기·회복 양봉 (266f)',
      duration: f(266),
      chart: {
        ...chartBase,
        zoom: [{ t: 0, v: ZOOM_IN }],
        reveal: [{ t: 0, v: 45.5 }],
      },
      layers: [
        {
          type: 'cmgNote',
          bar: 30,
          dx: 26,
          align: 'left',
          price: 23675,
          text: '기울기 상방',
          size: 46,
          color: '#F38808',
          in: [0.5, 0.35],
          out: [3.3, 0.4],
        },
        {
          type: 'cmgCircle',
          bar: 37,
          price: 23690,
          rx: 180,
          ry: 58,
          width: 11,
          drawDur: 0.6,
          in: [0.8, 0.2],
          out: [3.5, 0.4],
        },
        {
          type: 'cmgCircle',
          bar: 41,
          price: 23730,
          rx: 92,
          ry: 100,
          width: 11,
          drawDur: 0.6,
          in: [3.85, 0.2],
        },
        {
          type: 'cmgNote',
          bar: 30,
          dx: 26,
          align: 'left',
          price: 23675,
          text: '종가 회복 양봉',
          size: 44,
          in: [5.4, 0.35],
        },
      ],
    },

    /* ── ④ 손절선 / 이격 음봉 익절 — 줌아웃 (22.93~36.83) ────────── */
    {
      id: 'cut4-stop-and-signal',
      name: '④ 손절선 + 이격 음봉 익절 (417f)',
      duration: f(417),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 45.5 },
          { t: 6.4, v: 46, ease: 'linear' },
          { t: 8.2, v: 60, ease: 'inOutCubic' },
          { t: 11.2, v: 104.2, ease: 'inOutCubic' },
          { t: f(417), v: 104.5, ease: 'linear' },
        ],
        zoom: [
          { t: 0, v: ZOOM_IN },
          { t: 8.2, v: ZOOM_IN },
          { t: 11.2, v: 0.55, ease: 'inOutCubic' }, // 추세 전체 줌아웃
          { t: 11.5, v: 0.55 },
          { t: 12.7, v: 1.1, ease: 'inOutCubic' }, // "이격된 음봉" — 봉 하나로 다시 줌인
        ],
      },
      layers: [
        {
          type: 'cmgLevel',
          price: LV.stop,
          fromBar: 41,
          color: COLOR.sl,
          thickness: 16,
          label: '손절',
          labelSize: 44,
          in: [0.15, 0.2],
          out: [3.4, 0.5],
          growDur: 0.4,
        },
        buyArrowHeld,
        {
          type: 'cmgNote',
          bar: 38,
          price: 23985,
          text: '목표가 ✕',
          size: 48,
          color: '#9AA3AF',
          in: [4.6, 0.3],
          out: [6.3, 0.45],
        },
        {
          type: 'cmgCircle',
          bar: LV.exitBar,
          price: 24845,
          rx: 96,
          ry: 128,
          width: 11,
          drawDur: 0.6,
          in: [11.6, 0.2],
        },
        {
          type: 'cmgNote',
          bar: 98,
          price: 25000,
          text: '이격 음봉',
          size: 46,
          color: '#E90054',
          in: [12.3, 0.35],
        },
        { type: 'flash', at: 12.85, dur: 0.22, strength: 0.4, color: COLOR.tp },
        {
          type: 'cmgArrow',
          bar: LV.exitBar,
          price: LV.exitClose,
          dir: 'sell',
          label: '익절',
          color: '#0DA82A',
          size: 32,
          gap: 16,
          in: [12.9, 0.35],
        },
      ],
    },

    /* ── ⑤ CTA — 20일선이 옆으로 누우면? (36.83~43.40) ──────────── */
    {
      id: 'cut5-cta-box',
      name: '⑤ CTA 박스권 예고 (197f)',
      duration: f(197),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 104.5 },
          { t: 5.0, v: 121, ease: 'inOutCubic' },
          { t: f(197), v: 121, ease: 'linear' },
        ],
        zoom: [
          { t: 0, v: 1.1 },
          { t: 5.0, v: 0.8, ease: 'inOutCubic' },
        ],
      },
      layers: [
        // ── 컷4의 이격 음봉 세트를 이어받아 천천히 걷는다 (경계에서 즉사 방지) ──
        {
          type: 'cmgCircle',
          bar: LV.exitBar,
          price: 24845,
          rx: 96,
          ry: 128,
          width: 11,
          drawDur: 0,
          in: [0, 0],
          out: [1.4, 0.5],
        },
        {
          type: 'cmgNote',
          bar: 98,
          price: 25000,
          text: '이격 음봉',
          size: 46,
          color: '#E90054',
          in: [0, 0],
          out: [1.4, 0.5],
        },
        {
          type: 'cmgArrow',
          bar: LV.exitBar,
          price: LV.exitClose,
          dir: 'sell',
          label: '익절',
          color: '#0DA82A',
          size: 32,
          gap: 16,
          popDur: 0,
          out: [1.4, 0.5],
        },
        {
          // 박스권 예고 원 — 캔들이 먼저 그려진 뒤에 친다 (당연한 순서)
          type: 'cmgCircle',
          bar: 113,
          price: 24880,
          rx: 190,
          ry: 82,
          width: 11,
          drawDur: 0.65,
          in: [4.3, 0.2],
        },
        {
          // 마무리 — 화면이 살짝 어두워지며 정중앙에 크게 (최종본 엔딩 스타일)
          type: 'titleCard',
          title: '옆으로 누우면?',
          size: 104,
          color: '#FFFFFF',
          scrimStrength: 0.85,
          in: [1.9, 0.45],
        },
      ],
    },
  ],
};
