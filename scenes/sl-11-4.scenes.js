/**
 * 차트명가 숏폼 — [SL_차11-4] 20일선 추세추종 매매법 (5컷) · v2
 *
 * 프리미어 숏츠 시퀀스(1080x1920/30fps) 가운데 1:1 박스용. 자막·타이틀·로고 없음.
 * v2 반영 (2026-08-28 사용자·팀장 피드백):
 *   - '매도' 태그는 숏 전용 → 수익 실현은 초록 '익절' 태그로
 *   - 손익비는 색 박스로 직관화: 익절 초록 박스(진입→1:2)와 손절 갈색 박스(진입→손절)를
 *     같이 그린다. 선과 박스 테두리는 cmgLevel(fillTo)이라 정확히 포개진다
 *   - 최종본 pool(차10·차12) 스타일: 손그림 X·원·라벨은 유지, 등장 모션은 첫 컷만
 *
 * 타이밍: 컷편집 내레이션 v3 (out_차11-4_내레이션.wav, 43.37초 — 침묵 압축판)
 *   ① 0.00~ 8.17  훅 + "눌림목 진입까지는 성공"          245f
 *   ② 8.17~12.63  "1:2 구간에서 팔아버립니다"            134f
 *   ③ 12.63~22.93 "진입 조건 두 가지" (기울기·회복 양봉)   309f
 *   ④ 22.93~36.83 "손절은 아래꼬리 밑 / 이격 음봉 익절"    417f
 *   ⑤ 36.83~43.40 CTA "박스권에서는?"                    197f
 *                                                  합계 1302f = 43.4s
 *
 * 마켓은 롱폼 러너(cmg-20ma-runner)와 같은 seed 11 — 앞 90봉이 같고,
 * 뒤에 청산 신호(20일선 하방 이탈 이격 음봉, 103번)와 CTA용 박스권 꼬리.
 */

const FPS = 30;
const f = (n) => n / FPS;

/* 매매 수치 — 러너와 동일 (실측: brand 프리셋 색) */
const LV = {
  entry: 23795, // 42번 캔들, 눌림목 반등 확인 후 진입
  stop: 23665, // 직전 눌림목 캔들(41번)의 아래꼬리(23,677.75) 밑
  get target() { return this.entry + (this.entry - this.stop) * 2; }, // 24,055 = 1:2
  runHigh: 24977.5,
  exitBar: 103, // 종가가 20일선 아래, 고가조차 안 닿는 이격 음봉
  exitClose: 24831.75,
};

const COLOR = {
  tp: '#14FF36', // 익절 (프리셋 실측)
  tpFill: '#BAFDC0',
  sl: '#9F0000', // 손절
  slFill: '#FEBABA',
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
  title: '차트명가 숏폼 — 차11-4 20일선 추세추종 5컷 (v2)',
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
          // "20일선 눌림목에서" — 눌림 구간 색연필 원
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
        // "진입하는 것까지는 성공합니다"
        { ...buyArrowBase, in: [5.8, 0.35] },
      ],
    },

    /* ── ② 1:2 에서 팔아버린다 — 손익비를 색 박스로 (8.17~12.63) ──── */
    {
      id: 'cut2-early-exit',
      name: '② 1:2 조기 익절 (134f)',
      duration: f(134),
      chart: {
        ...chartBase,
        include: [LV.stop, LV.target + 60],
        reveal: [
          { t: 0, v: 43 },
          { t: f(134), v: 51, ease: 'linear' },
        ],
      },
      layers: [
        buyArrowHeld,
        {
          // 익절 초록 박스 — 선(1:2)과 박스 테두리가 정확히 포개진다
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
          growDur: 0.4,
        },
        {
          // 손절 갈색 박스 — 1:2 비율이 한눈에 보이게
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
          growDur: 0.4,
        },
        {
          // 진입가 — 얇은 검은 선
          type: 'cmgLevel',
          price: LV.entry,
          fromBar: 42,
          color: 'rgba(0,0,0,0.72)',
          thickness: 4,
          in: [0.3, 0.2],
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
        },
        { type: 'flash', at: 3.25, dur: 0.22, strength: 0.4, color: COLOR.tp },
        {
          // "팔아버립니다" — 수익 실현은 '익절' 태그 (매도 태그는 숏 전용)
          type: 'cmgArrow',
          bar: 53,
          price: LV.target,
          dir: 'sell',
          label: '익절',
          color: '#0DA82A',
          size: 32,
          gap: 16,
          in: [3.3, 0.35],
        },
      ],
    },

    /* ── ③ 진입 조건 두 가지 (12.63~22.93) ──────────────────────── */
    {
      id: 'cut3-conditions',
      name: '③ 진입 조건 기울기·회복 양봉 (309f)',
      duration: f(309),
      chart: {
        ...chartBase,
        visibleBars: 22, // 줌인 — 눌림목 타점을 크게
        reveal: [
          { t: 0, v: 45 },
          { t: f(309), v: 45.5, ease: 'linear' },
        ],
      },
      layers: [
        {
          // 조건 ① — 20일선 기울기가 명확한 상방 (내레이션 14.55~17.38)
          type: 'cmgNote',
          bar: 30,
          dx: 26,
          align: 'left',
          price: 23675,
          text: '기울기 상방',
          size: 46,
          color: '#F38808',
          in: [1.9, 0.35],
          out: [4.8, 0.4],
        },
        {
          type: 'cmgCircle',
          bar: 37,
          price: 23690,
          rx: 180,
          ry: 58,
          width: 11,
          drawDur: 0.6,
          in: [2.2, 0.2],
          out: [5.0, 0.4],
        },
        {
          // 조건 ② — 아래로 갔다가 종가 회복 양봉 (내레이션 17.88~22.87)
          type: 'cmgCircle',
          bar: 41,
          price: 23730,
          rx: 92,
          ry: 100,
          width: 11,
          drawDur: 0.6,
          in: [5.3, 0.2],
        },
        {
          type: 'cmgNote',
          bar: 30,
          dx: 26,
          align: 'left',
          price: 23675,
          text: '종가 회복 양봉',
          size: 44,
          in: [6.8, 0.35],
        },
      ],
    },

    /* ── ④ 손절은 아래꼬리 밑 / 이격 음봉에 익절 (22.93~36.83) ────── */
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
          { t: 13.5, v: 104.2, ease: 'inOutCubic' }, // 추세 전체 + 이탈 음봉까지
          { t: f(417), v: 104.5, ease: 'linear' },
        ],
        zoom: [
          { t: 0, v: 1 },
          { t: 8.2, v: 1 },
          { t: 13.2, v: 0.55, ease: 'inOutCubic' },
        ],
      },
      layers: [
        {
          // "손절은 직전 눌림목 캔들의 아래꼬리 밑" (내레이션 22.97~25.97)
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
          // "목표가를 미리 정하지 마세요" (내레이션 27.49~29.11)
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
          // "종가가 20일선을 하방 이탈… 이격된 음봉" (내레이션 31.15~36.75)
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
          bar: 96,
          price: 25060,
          text: '이격 음봉',
          size: 46,
          color: '#E90054',
          in: [12.3, 0.35],
        },
        { type: 'flash', at: 12.85, dur: 0.22, strength: 0.4, color: COLOR.tp },
        {
          // 수익 실현 → 초록 '익절' 태그
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
        visibleBars: 40,
        include: [],
        pricePad: 0.18,
        reveal: [
          { t: 0, v: 104.5 },
          { t: 5.0, v: 121, ease: 'inOutCubic' },
          { t: f(197), v: 121, ease: 'linear' },
        ],
      },
      layers: [
        {
          type: 'cmgCircle',
          bar: 113,
          price: 24880,
          rx: 190,
          ry: 82,
          width: 11,
          drawDur: 0.65,
          in: [1.2, 0.2],
        },
        {
          type: 'cmgNote',
          bar: 113,
          price: 25000,
          text: '옆으로 누우면?',
          size: 48,
          color: '#F38808',
          in: [2.1, 0.35],
        },
      ],
    },
  ],
};
