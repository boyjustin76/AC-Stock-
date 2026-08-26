/**
 * 차트명가 — "20일선 눌림목은 잡는데, 추세를 못 끌고 간다" 4컷
 *
 * 대본 타임코드(29.97 드롭프레임)를 프레임 단위로 환산해 컷 길이를 맞췄다.
 *   ① 00;05;26;27 ~ 00;05;31;02  125f  다수의 트레이더는 20일선 눌림목에서 진입하는 것까지는 성공합니다
 *   ② 00;05;31;02 ~ 00;05;34;29  117f  하지만 막상 수익이 발생하면 추세를 끝까지 끌고 가지 못합니다
 *   ③ 00;05;34;29 ~ 00;05;37;15   76f  확보한 수익을 다시 잃을까 두려운 나머지,
 *   ④ 00;05;37;15 ~ 00;05;42;25  160f  짧은 저항선이나 1:2 정도의 얕은 구간에서 기계적으로 이익을 실현해 버립니다
 *                                 ────
 *                                 478f = 15.949초
 *
 * 59.94fps(= 29.97 × 2)로 렌더하므로 컷마다 프레임 수가 정확히 2배가 되고,
 * 프리미어 29.97 시퀀스에 그대로 얹으면 프레임 단위로 맞는다.
 *
 * 자막은 넣지 않는다 — 캡션은 프리미어에서 따로 얹는다.
 * 차트 위 라벨(매수/익절/손절/놓친 구간)만 시각자료로 넣는다.
 */

const FPS = 60000 / 1001; // 59.94005994
const f = (n) => (n * 1001) / 60000; // 프레임 → 초

/* 이 시나리오의 매매 수치 */
const LV = {
  entry: 23795, // 42번 캔들, 20일선 눌림목 반등 확인 후 진입
  stop: 23665, // 눌림목 저점(23,677.75) 아래
  get risk() { return this.entry - this.stop; }, // 130pt
  get target() { return this.entry + this.risk * 2; }, // 24,055 = 1:2
  runHigh: 24977.5, // 이후 추세가 실제로 도달한 고점 (93번 캔들)
};

/** 네 컷이 하나의 차트를 이어서 보여준다 */
const chartBase = {
  visibleBars: 40,
  pricePad: 0.14,
  showGrid: false,
  showAxes: false,
  showLast: false,
  include: [LV.stop],
  layout: { padLeft: 0, padRight: 0, padTop: 0, padBottom: 0, rightGap: 6 },
  ma: [{ type: 'ema', period: 20, width: 5 }], // 색은 테마의 주황(#F38808)
};

const buyArrowBase = {
  type: 'cmgArrow',
  bar: 42,
  price: LV.entry,
  dir: 'buy',
  label: '매수',
  size: 36,
  gap: 18,
};
/** ① 컷에서 처음 등장할 때만 튀어나오는 연출을 준다 */
const buyArrowIntro = { ...buyArrowBase, in: [2.9, 0.35] };
/**
 * ②~④ 컷에서는 이미 떠 있는 상태로 시작한다.
 * in 을 주지 않고 popDur 을 0 으로 둬야 컷이 바뀔 때마다 다시 튀어나오지 않는다.
 */
const buyArrowHeld = { ...buyArrowBase, popDur: 0 };

/** 평가손익 영역도 ②~③ 컷에 걸쳐 이어진다 */
const profitZoneBase = { type: 'cmgProfit', entry: LV.entry, fromBar: 42 };

export default {
  title: '차트명가 — 20일선 눌림목 / 조기 익절 4컷',
  width: 1920,
  height: 1080,
  fps: FPS,
  fpsExpr: '60000/1001',

  theme: { preset: 'chartmyeongga' },

  market: {
    seed: 11,
    base: 23400,
    tick: 0.25,
    vol: 58,
    barMinutes: 1440, // 일봉
    startTime: Date.UTC(2026, 0, 5, 0, 0),
    segments: [
      { type: 'trend', dir: 1, bars: 34, strength: 0.52 }, // 상승 추세
      { type: 'pullback', dir: 1, bars: 9, strength: 1.15 }, // 20일선까지 눌림
      { type: 'trend', dir: 1, bars: 52, strength: 0.82 }, // 추세 재개, 끝까지 감
    ],
  },

  scenes: [
    /* ── ① 20일선 눌림목에서 진입까지는 성공 ────────────────────── */
    {
      id: 'cut1-pullback-entry',
      name: '① 20일선 눌림목 진입 (125f)',
      duration: f(250),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 34 },
          { t: f(160), v: 42.2, ease: 'inOutCubic' },
          { t: f(250), v: 43, ease: 'linear' },
        ],
      },
      layers: [
        {
          type: 'cmgNote',
          bar: 26,
          price: 23532.8, // 26번 캔들의 20일선 값
          dy: 62,
          text: '20일선',
          size: 50,
          color: '#F38808',
          in: [0.35, 0.35],
        },
        {
          // 눌림목 구간을 색연필 원으로 감싼다
          type: 'cmgCircle',
          bar: 41,
          price: 23706,
          rx: 148,
          ry: 118,
          width: 12,
          drawDur: 0.65,
          in: [1.75, 0.2],
          // 컷2 로 넘어갈 때 뚝 끊기지 않게 컷 안에서 먼저 지워 준다
          out: [3.45, 0.5],
        },
        buyArrowIntro,
      ],
    },

    /* ── ② 수익은 나는데 끝까지 못 끌고 간다 ──────────────────── */
    {
      id: 'cut2-profit-runs',
      name: '② 수익 발생 (117f)',
      duration: f(234),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 43 },
          { t: f(234), v: 50, ease: 'linear' },
        ],
      },
      layers: [
        { ...profitZoneBase, in: [0, 0.2] },
        buyArrowHeld,
      ],
    },

    /* ── ③ 확보한 수익을 잃을까 두렵다 ────────────────────────── */
    {
      id: 'cut3-fear',
      name: '③ 수익을 잃을까 두려움 (76f)',
      duration: f(152),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 50 },
          { t: f(152), v: 52, ease: 'linear' },
        ],
      },
      // 미세한 손떨림. 난수를 안 쓰므로 다시 렌더해도 같은 흔들림이 나온다.
      camera: {
        shake: [
          { t: 0, v: 0 },
          { t: 0.3, v: 1 },
          { t: f(120), v: 1 },
          { t: f(152), v: 0.4 },
        ],
      },
      layers: [
        {
          // ② 컷에서 이어진다 — in 을 주지 않아 컷 경계에서 끊기지 않는다
          ...profitZoneBase,
          pulse: true,
          pulseFrom: 0.25,
          pulseSpeed: 8.2,
          pulseAmount: 0.5,
        },
        buyArrowHeld,
      ],
    },

    /* ── ④ 1:2 얕은 구간에서 기계적 익절, 그리고 놓친 추세 ────── */
    {
      id: 'cut4-early-exit',
      name: '④ 1:2 조기 익절 + 놓친 구간 (160f)',
      duration: f(320),
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 52 },
          { t: f(40), v: 53.4, ease: 'inOutCubic' },
          { t: f(96), v: 55, ease: 'linear' },
          { t: f(320), v: 95, ease: 'inOutCubic' },
        ],
        // 추세가 다 보이도록 뒤로 갈수록 화면을 넓게 뺀다
        zoom: [
          { t: 0, v: 1 },
          { t: f(96), v: 1 },
          { t: f(300), v: 0.5, ease: 'inOutCubic' },
        ],
      },
      layers: [
        {
          type: 'cmgLevel',
          price: LV.stop,
          fromBar: 42,
          fillTo: LV.entry,
          fill: '#FEBABA',
          color: '#9F0000',
          label: '손절',
          labelSize: 62,
          thickness: 23,
          in: [0.05, 0.2],
          growDur: 0.4,
        },
        {
          type: 'cmgLevel',
          price: LV.target,
          fromBar: 42,
          fillTo: LV.entry,
          fill: '#BAFDC0',
          color: '#14FF36',
          label: '익절',
          labelSize: 62,
          thickness: 23,
          in: [0.3, 0.2],
          growDur: 0.4,
        },
        {
          // 진입가 — 얇은 검은 선
          type: 'cmgLevel',
          price: LV.entry,
          fromBar: 42,
          color: 'rgba(0,0,0,0.72)',
          thickness: 4,
          in: [0.05, 0.2],
          growDur: 0.4,
        },
        buyArrowHeld,
        {
          type: 'cmgBadge',
          text: '손익비  1 : 2',
          x: 96,
          y: 986,
          size: 52,
          color: '#E90054',
          border: false,
          in: [0.75, 0.3],
          out: [f(300), 0.3],
        },
        // 익절 체결
        { type: 'flash', at: 1.28, dur: 0.24, strength: 0.42, color: '#14FF36' },
        {
          type: 'cmgArrow',
          bar: 53,
          price: LV.target,
          dir: 'sell',
          label: '매도',
          size: 36,
          gap: 18,
          in: [1.3, 0.35],
        },
        // 그 뒤로 추세가 간 만큼 = 놓친 구간
        {
          type: 'cmgMissed',
          from: LV.target,
          to: LV.runHigh,
          fromBar: 53,
          color: '#E90054',
          arrow: false,
          growDur: 1.5,
          in: [2.55, 0.5],
        },
        {
          type: 'cmgNote',
          text: '놓친 구간',
          bar: 66,
          price: 24800,
          size: 74,
          in: [3.85, 0.4],
        },
        {
          // 최종본에서 강조할 때 쓰는 손그림 빨간 밑줄
          type: 'cmgUnderline',
          bar: 66,
          price: 24800,
          dy: 58,
          width: 282,
          align: 'center',
          in: [4.15, 0.2],
          drawDur: 0.38,
        },
      ],
    },
  ],
};
