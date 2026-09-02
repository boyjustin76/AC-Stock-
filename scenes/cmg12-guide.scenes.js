/**
 * 차트명가 #12 — 소개·설정 4컷 (컷7~10) · 1080p/59.94 · RSI 서브패널 첫 등장
 *
 * 자막 원본: 차명12롱폼 음성자막-한국어.srt (30.0 격자 반올림)
 *   [정확.srt 재동기 2026-08-31]
 *   컷7  guide-intro  60.600~ 70.333 ( 9.7333s)  ㉛~㊱ 오늘 지표: 10일선·34일선·RSI
 *   컷8  guide-ma     70.333~ 81.200 (10.8667s)  ㊲~㊷ 이평선 = 추세 방향, 但 후행성
 *   컷9  guide-rsi    81.200~ 97.967 (16.7667s)  ㊸~㊿ RSI = 힘의 세기, 방향→타이밍 결합 원리
 *   컷10 guide-set   116.967~142.267 (25.3000s)  61~71 설정값: 10/34 이평선, RSI 기간 10, 55/45선
 *   (92.733~111.333 스캘핑 성격 설명은 말 구간 — 차트 지시가 없어 클립을 만들지 않는다)
 *
 * 시장: 매수 관점(cmg12-buy)과 같은 seed 161. 지표 소개를 실전 차트와 같은 화면에서 한다.
 * 색 실측 (차12#1 숏폼 최종본 프레임 픽셀 실측, 2026-08-30):
 *   10일선(단기) 주황 #F38808 · 34일선(중기) 초록 #44B242 · RSI 라인 하늘색 #0FBDF8
 *   RSI 70선 빨강 #FE0000 · 30선 파랑 #002EFE · 지표명 배지 핑크 #ED7E88
 * 55/45 기준선은 최종본에 전례가 없어(그 영상은 70/30 얘기) 검정 #111111 로 그린다
 * — 박스권 검은 선(팀장 규칙 ②)과 같은 '우리 기준선' 문법.
 */

const FPS = 60000 / 1001;

export const market = {
  seed: 161,
  base: 15300,
  tick: 0.25,
  vol: 26,
  barMinutes: 1,
  startTime: Date.UTC(2026, 0, 5, 9, 0),
  segments: [
    { type: 'trend', dir: 1, bars: 42, strength: 0.55 },
    { type: 'pullback', dir: 1, bars: 7, strength: 1.0 },
    { type: 'trend', dir: 1, bars: 34, strength: 0.7 },
    { type: 'trend', dir: 1, bars: 14, strength: 0.5 },
  ],
};

export const COLOR = {
  ma10: '#F38808',
  ma34: '#44B242',
  rsi: '#0FBDF8',
  badge: '#ED7E88',
  line: '#111111',
};

export const chartBase = {
  visibleBars: 46,
  pricePad: 0.16,
  showGrid: false,
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 216, padBottom: 162, rightGap: 5 },
  ma: [
    { type: 'sma', period: 10, width: 5, color: COLOR.ma10 },
    { type: 'sma', period: 34, width: 5, color: COLOR.ma34 },
  ],
  rsi: { period: 10, height: 0.26, gap: 26, baseline: 50, levels: [], color: COLOR.rsi, width: 5 },
};

export default {
  title: '차트명가 #12 — 소개·설정 4컷',
  width: 1920,
  height: 1080,
  fps: FPS,
  fpsExpr: '60000/1001',
  theme: { preset: 'chartmyeongga' },
  market,

  scenes: [
    /* ── 컷7 "오늘 우리가 사용할 지표는…" — 지표가 하나씩 켜진다 (9.7333s) ── */
    {
      id: 'guide-intro',
      name: '컷7 지표 소개 (9.7333s)',
      duration: 9.733333,
      chart: {
        ...chartBase,
        ma: [
          { ...chartBase.ma[0], alpha: [{ t: 0, v: 0 }, { t: 1.9, v: 0 }, { t: 2.5, v: 1 }] },
          { ...chartBase.ma[1], alpha: [{ t: 0, v: 0 }, { t: 3.0, v: 0 }, { t: 3.6, v: 1 }] },
        ],
        rsiAlpha: [{ t: 0, v: 0 }, { t: 4.6, v: 0 }, { t: 5.3, v: 1 }],
        reveal: [
          { t: 0, v: 55 },
          { t: 9.733333, v: 60, ease: 'linear' },
        ],
      },
      layers: [
        { type: 'cmgNote', text: '10일선', bar: 44, price: 15602, size: 46, color: COLOR.ma10, in: [2.3, 0.3] },
        { type: 'cmgNote', text: '34일선', bar: 44, price: 15448, size: 46, color: COLOR.ma34, in: [3.4, 0.3] },
        { type: 'cmgBadge', text: 'RSI', x: 84, y: 860, size: 44, color: COLOR.badge, in: [5.0, 0.3] },
      ],
    },

    /* ── 컷8 이평선 = 추세 방향, 하지만 후행성 (10.7000s) ── */
    {
      id: 'guide-ma',
      name: '컷8 이평선의 쓸모와 한계 (10.7000s)',
      duration: 10.866667,
      chart: {
        ...chartBase,
        reveal: [{ t: 0, v: 60 }, { t: 10.866667, v: 61, ease: 'linear' }],
      },
      layers: [
        /* 컷7 끝 화면 이월 (룰북 ⑧ — 경계에서 지우지 않는다). 배지는 컷 내내,
           이름표 두 장은 '추세 방향'이 역할을 이어받는 3.3초에 크로스페이드(⑨) */
        { type: 'cmgBadge', text: 'RSI', x: 84, y: 860, size: 44, color: COLOR.badge, popDur: 0 },
        { type: 'cmgNote', text: '10일선', bar: 44, price: 15602, size: 46, color: COLOR.ma10, in: [0, 0], out: [3.3, 0.4] },
        { type: 'cmgNote', text: '34일선', bar: 44, price: 15448, size: 46, color: COLOR.ma34, in: [0, 0], out: [3.3, 0.4] },
        /* 추세 방향 — 10일선 구간 덧칠 (팀장 접선 기법) */
        { type: 'cmgTrace', overlay: 0, fromBar: 33, toBar: 45, flatten: 0, width: 15, color: COLOR.ma10, in: [3.3, 0.5], out: [6.3, 0.35] },
        { type: 'cmgNote', text: '추세 방향', bar: 38, price: 15625, size: 48, color: COLOR.ma10, in: [3.9, 0.3], out: [6.3, 0.35] },
        /* 후행성 — 가격이 먼저 꺾이고(42) 선은 4봉 늦게(46) 꺾인다 */
        { type: 'cmgCircle', bar: 42, price: 15589, rx: 62, ry: 56, width: 10, drawDur: 0.5, in: [6.7, 0.2] },
        { type: 'cmgCircle', bar: 46, price: 15560, rx: 62, ry: 56, width: 10, color: '#111111', drawDur: 0.5, in: [7.6, 0.2] },
        { type: 'cmgNote', text: '가격 먼저, 선은 늦게', bar: 49, price: 15645, size: 50, color: '#111111', in: [8.2, 0.3] },
        { type: 'cmgUnderline', bar: 49, price: 15645, dy: 46, width: 430, align: 'center', drawDur: 0.35, in: [9.6, 0.15] },
      ],
    },

    /* ── 컷9 RSI = 힘의 세기 → 방향은 이평선, 타이밍은 RSI (16.2333s) ── */
    {
      id: 'guide-rsi',
      name: '컷9 RSI 와 결합 원리 (16.2333s)',
      duration: 16.766667,
      chart: {
        ...chartBase,
        reveal: [{ t: 0, v: 61 }, { t: 16.766667, v: 66, ease: 'linear' }],
      },
      layers: [
        { type: 'cmgBadge', text: 'RSI', x: 84, y: 860, size: 44, color: COLOR.badge, in: [0, 0], popDur: 0 },
        /* 컷8 끝 화면 이월(⑧) — 후행성 원·문장은 RSI 이야기('힘의 세기' 1.4)로
           넘어가는 순간 크로스페이드(⑨)로 역할을 넘긴다 */
        { type: 'cmgCircle', bar: 42, price: 15589, rx: 62, ry: 56, width: 10, drawDur: 0, in: [0, 0], out: [1.2, 0.4] },
        { type: 'cmgCircle', bar: 46, price: 15560, rx: 62, ry: 56, width: 10, color: '#111111', drawDur: 0, in: [0, 0], out: [1.2, 0.4] },
        { type: 'cmgNote', text: '가격 먼저, 선은 늦게', bar: 49, price: 15645, size: 50, color: '#111111', in: [0, 0], out: [1.2, 0.4] },
        { type: 'cmgUnderline', bar: 49, price: 15645, dy: 46, width: 430, align: 'center', drawDur: 0, in: [0, 0], out: [1.2, 0.4] },
        { type: 'cmgNote', text: '힘의 세기', bar: 44, rsi: 82, size: 46, color: COLOR.rsi, stroke: '#083244', in: [1.4, 0.3] },
        /* 세기가 수치로 — 눌림에서 힘이 빠지는 게 그대로 보인다 */
        { type: 'cmgCircle', bar: 48, rsi: 41, rx: 66, ry: 52, width: 10, color: COLOR.rsi, drawDur: 0.5, in: [2.9, 0.2], out: [6.2, 0.3] },
        /* 결합 원리 ① 방향은 이평선으로 — ②와 짝이므로 컷 끝까지 남는다.
           [2026-09-01 반려] 원래 13.6에 지웠는데 후속 요소가 없는 중간 퇴장이라
           룰북 ⑧ 위반(r6 재검토가 컷 경계만 보고 컷 중간을 놓친 것). */
        { type: 'cmgTrace', overlay: 0, fromBar: 50, toBar: 62, flatten: 0, width: 15, color: COLOR.ma10, in: [6.9, 0.5] },
        { type: 'cmgNote', text: '① 방향', bar: 55, price: 15505, size: 48, color: COLOR.ma10, in: [7.5, 0.3] },
        /* 결합 원리 ② 타이밍은 RSI 로 */
        { type: 'cmgCircle', bar: 52, rsi: 60.5, rx: 60, ry: 50, width: 10, color: '#E90054', drawDur: 0.5, in: [11.0, 0.2] },
        { type: 'cmgNote', text: '② 타이밍', bar: 46, rsi: 68, size: 48, color: '#E90054', in: [11.8, 0.3] },
      ],
    },

    /* ── 컷10 설정값 — 10/34 이평선, RSI 기간 10, 50 위아래 55/45선 (21.8667s) ── */
    {
      id: 'guide-set',
      name: '컷10 설정값 (21.8667s)',
      duration: 25.3,
      chart: {
        ...chartBase,
        reveal: [{ t: 0, v: 66 }, { t: 25.3, v: 70, ease: 'linear' }],
      },
      layers: [
        { type: 'cmgNote', text: '10일선', bar: 59, price: 15630, size: 46, color: COLOR.ma10, in: [3.9, 0.3] },
        { type: 'cmgNote', text: '34일선', bar: 59, price: 15505, size: 46, color: COLOR.ma34, in: [6.4, 0.3] },
        { type: 'cmgNote', text: 'RSI 기간 14 → 10', bar: 52, rsi: 85, size: 46, color: '#111111', in: [10.0, 0.3] },
        /* 55선·45선이 자막에 맞춰 그어진다 — 이후 모든 컷의 상시 기준선 */
        { type: 'rsiLevel', v: 55, label: '55선', color: COLOR.line, width: 4, growDur: 0.6, in: [20.5, 0.2] },
        { type: 'rsiLevel', v: 45, label: '45선', labelX: 176, color: COLOR.line, width: 4, growDur: 0.6, in: [21.7, 0.2] },
        { type: 'cmgNote', text: '타점의 기준선', bar: 61, rsi: 30, size: 46, color: '#E90054', in: [23.1, 0.3] },
      ],
    },
  ],
};
