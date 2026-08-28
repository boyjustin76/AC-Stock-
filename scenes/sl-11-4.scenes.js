/**
 * 차트명가 숏폼 — [SL_차11-4] 20일선 추세추종 매매법 (5컷)
 *
 * 숏폼 3단계 첫 납품. 프리미어 숏츠 시퀀스(1080x1920/30fps)의 가운데 1:1 박스에
 * 들어가는 차트 모션그래픽이다. 자막·타이틀·로고는 프리셋이 얹으므로 넣지 않고,
 * 차트 위 라벨(매수/매도/손절/20일선)만 넣는다.
 *
 * 타이밍은 컷편집 내레이션(out_차11-4_내레이션.wav, 46.77초)의 문장 타임코드에 맞췄다.
 *   ① 0.00~ 8.92  훅 + "눌림목 진입까지는 성공"          268f
 *   ② 8.92~13.98  "수익 나면 1:2 구간에서 팔아버립니다"   152f
 *   ③ 13.98~24.80 "진입 조건 두 가지" (기울기·회복 양봉)   324f
 *   ④ 24.80~40.17 "손절은 아래꼬리 밑 / 익절은 이격 음봉"  461f
 *   ⑤ 40.17~46.83 CTA "박스권에서는?" (다음 편 예고)       200f
 *                                                    합계 1405f = 46.833s
 *   (내레이션 46.77초 — 무음 보정판 out_차11-4_내레이션.wav 기준)
 *
 * 마켓은 롱폼 러너(cmg-20ma-runner)와 같은 seed 11 — 앞 90봉이 완전히 같고,
 * 뒤에 청산 신호(20일선 하방 이탈 이격 음봉, 103번)와 CTA용 박스권 꼬리를 이었다.
 */

const FPS = 30;
const f = (n) => n / FPS;

/* 매매 수치 — 러너와 동일한 시나리오 */
const LV = {
  entry: 23795, // 42번 캔들, 눌림목 반등 확인 후 진입
  stop: 23665, // 직전 눌림목 캔들(41번)의 아래꼬리(23,677.75) 밑
  runHigh: 24977.5, // 추세 고점 (93번 캔들)
  exitBar: 103, // 청산 신호 — 종가가 20일선 아래, 고가조차 안 닿는 이격 음봉
  exitClose: 24831.75,
};

const chartBase = {
  visibleBars: 32,
  pricePad: 0.14,
  showGrid: false,
  showAxes: false,
  showLast: false,
  include: [LV.stop],
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
  title: '차트명가 숏폼 — 차11-4 20일선 추세추종 5컷',
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
      { type: 'trend', dir: -1, bars: 8, strength: 1.05 }, // 청산 신호로 가는 하락
      { type: 'range', bars: 18, width: 1.1 }, // CTA: 20일선이 옆으로 눕는다
    ],
  },

  scenes: [
    /* ── ① 훅 + 눌림목 진입까지는 성공 (0.00~8.92) ───────────────── */
    {
      id: 'cut1-hook-entry',
      name: '① 훅 + 눌림목 진입 (268f)',
      duration: f(268),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 30 },
          { t: 4.4, v: 42.2, ease: 'inOutCubic' },
          { t: f(268), v: 43, ease: 'linear' },
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
          in: [0.9, 0.35],
        },
        {
          // "20일선 눌림목에서" — 눌림 구간 색연필 원
          type: 'cmgCircle',
          bar: 41,
          price: 23706,
          rx: 132,
          ry: 106,
          width: 11,
          drawDur: 0.6,
          in: [4.7, 0.2],
          out: [8.2, 0.4],
        },
        // "진입하는 것까지는 성공합니다"
        { ...buyArrowBase, in: [6.3, 0.35] },
      ],
    },

    /* ── ② 수익이 나면 1:2 에서 팔아버린다 (8.92~13.98) ──────────── */
    {
      id: 'cut2-early-exit',
      name: '② 1:2 조기 익절 (152f)',
      duration: f(152),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 43 },
          { t: f(152), v: 51, ease: 'linear' },
        ],
      },
      layers: [
        { type: 'cmgProfit', entry: LV.entry, fromBar: 42, in: [0, 0.25] },
        buyArrowHeld,
        {
          // 1:2 목표가 — 기계적 익절 자리
          type: 'cmgLevel',
          price: LV.entry + (LV.entry - LV.stop) * 2, // 24,055
          fromBar: 42,
          color: '#14FF36',
          thickness: 14,
          label: '1:2',
          labelSize: 40,
          in: [2.1, 0.25],
          growDur: 0.35,
        },
        { type: 'flash', at: 3.55, dur: 0.22, strength: 0.4, color: '#14FF36' },
        {
          type: 'cmgArrow',
          bar: 53,
          price: 24055,
          dir: 'sell',
          label: '매도',
          size: 32,
          gap: 16,
          in: [3.6, 0.35],
        },
      ],
    },

    /* ── ③ 진입 조건 두 가지 (13.98~25.43) ──────────────────────── */
    {
      id: 'cut3-conditions',
      name: '③ 진입 조건 기울기·회복 양봉 (324f)',
      duration: f(324),
      chart: {
        ...chartBase,
        visibleBars: 22, // 눌림목 구간을 크게
        reveal: [
          { t: 0, v: 45 },
          { t: f(324), v: 45.5, ease: 'linear' },
        ],
      },
      layers: [
        {
          // 조건 ① — 20일선 기울기가 명확한 상방 (16.00~19.24 → 컷 내 2.0~5.3)
          type: 'cmgNote',
          bar: 30,
          dx: 26,
          align: 'left',
          price: 23675,
          text: '기울기 상방',
          size: 46,
          color: '#F38808',
          in: [2.3, 0.35],
          out: [5.4, 0.4],
        },
        {
          // 상방으로 기운 20일선 구간을 감싼다
          type: 'cmgCircle',
          bar: 37,
          price: 23690,
          rx: 180,
          ry: 58,
          width: 11,
          drawDur: 0.6,
          in: [2.8, 0.2],
          out: [5.6, 0.4],
        },
        {
          // 조건 ② — 20일선 아래로 갔다가 종가 회복 양봉 (19.24~25.12 → 컷 내 5.3~11.1)
          type: 'cmgCircle',
          bar: 41,
          price: 23730,
          rx: 92,
          ry: 100,
          width: 11,
          drawDur: 0.6,
          in: [5.9, 0.2],
        },
        {
          type: 'cmgNote',
          bar: 30,
          dx: 26,
          align: 'left',
          price: 23675,
          text: '종가 회복 양봉',
          size: 44,
          in: [7.4, 0.35],
        },
      ],
    },

    /* ── ④ 손절은 아래꼬리 밑 / 청산 신호는 이격 음봉 (25.43~41.23) ─ */
    {
      id: 'cut4-stop-and-signal',
      name: '④ 손절선 + 이격 음봉 청산 (461f)',
      duration: f(461),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 45.5 },
          { t: 7.5, v: 46, ease: 'linear' },
          { t: 9.2, v: 60, ease: 'inOutCubic' },
          { t: 14.6, v: 104.2, ease: 'inOutCubic' }, // 추세 전체 + 이탈 음봉까지
          { t: f(461), v: 104.5, ease: 'linear' },
        ],
        zoom: [
          { t: 0, v: 1 },
          { t: 9.2, v: 1 },
          { t: 14.2, v: 0.55, ease: 'inOutCubic' },
        ],
      },
      layers: [
        {
          // "손절은 직전 눌림목 캔들의 아래꼬리 밑" (25.44~29.30 → 0.0~3.9)
          type: 'cmgLevel',
          price: LV.stop,
          fromBar: 41,
          color: '#9F0000',
          thickness: 16,
          label: '손절',
          labelSize: 44,
          in: [0.15, 0.2],
          out: [8.6, 0.5],
          growDur: 0.4,
        },
        buyArrowHeld,
        {
          // "목표가를 미리 정하지 마세요" (30.82~32.72 → 5.4~7.3) — 떴다가 지워진다
          type: 'cmgNote',
          bar: 38,
          price: 23985,
          text: '목표가 ✕',
          size: 48,
          color: '#9AA3AF',
          in: [5.4, 0.3],
          out: [7.4, 0.45],
        },
        {
          // "종가가 20일선을 하방 이탈… 이격된 음봉" (34.84~41.06 → 9.4~15.6)
          type: 'cmgCircle',
          bar: LV.exitBar,
          price: 24845,
          rx: 96,
          ry: 128,
          width: 11,
          drawDur: 0.6,
          in: [12.6, 0.2],
        },
        {
          type: 'cmgArrow',
          bar: LV.exitBar,
          price: LV.exitClose,
          dir: 'sell',
          label: '청산',
          size: 32,
          gap: 16,
          in: [14.0, 0.35],
        },
        {
          type: 'cmgNote',
          bar: 96,
          price: 25060,
          text: '이격 음봉',
          size: 46,
          color: '#E90054',
          in: [13.3, 0.35],
        },
      ],
    },

    /* ── ⑤ CTA — 20일선이 옆으로 누우면? (41.23~48.63) ──────────── */
    {
      id: 'cut5-cta-box',
      name: '⑤ CTA 박스권 예고 (200f)',
      duration: f(200),
      chart: {
        ...chartBase,
        visibleBars: 40,
        include: [],
        pricePad: 0.18,
        reveal: [
          { t: 0, v: 104.5 },
          { t: 5.4, v: 121, ease: 'inOutCubic' },
          { t: f(200), v: 121, ease: 'linear' },
        ],
      },
      layers: [
        {
          // 눕기 시작한 20일선을 감싼다 — 다음 편 예고
          type: 'cmgCircle',
          bar: 113,
          price: 24880,
          rx: 190,
          ry: 82,
          width: 11,
          drawDur: 0.65,
          in: [1.6, 0.2],
        },
        {
          type: 'cmgNote',
          bar: 113,
          price: 25000,
          text: '옆으로 누우면?',
          size: 48,
          color: '#F38808',
          in: [2.6, 0.35],
        },
      ],
    },
  ],
};
