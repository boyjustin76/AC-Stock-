/**
 * 차트명가 #12 — 후킹 나머지 2컷 (컷5·컷6) · 인트로 4컷의 시장을 그대로 잇는다
 *
 * 자막 원본: 차명12롱폼 음성자막-한국어.srt (컷 경계는 30.0 격자 반올림 — 인트로와 동일 규칙)
 *   [정확.srt 재동기 2026-08-31] 컷5 17.700~20.600 (2.9000s)  ⑩⑪ "곧바로 하락하는 가짜 신호에 속아 손실을 보거나"
 *   컷6 20.600~28.667 (8.0667s)  ⑫~⑯ "추세가 이어지다가 지표가 꺾이는 순간 어디서
 *                                 익절해야 할지 몰라 손실 전환으로 마감 … 경험이 더 많으셨을 것"
 *
 * 시장: cmg12-cross.build.js 의 seed 12 를 그대로 쓰고 뒤에 세그먼트 3개를 이어붙였다.
 * 이어붙이기는 앞 캔들을 바꾸지 않는다(실측 검증: 0~55번 봉 o/c 동일). 인트로 4컷 재렌더 불필요.
 * 이어붙인 구간 실측 (find-events + 덤프):
 *   골든크로스2 bar=65 → 진입(66번 시가) 60084 → 고점 bar72(60533, +449 미실현)
 *   → e5 꺾임 bar72~73 → 데드크로스 bar=76 (고점 4봉 뒤 — 후행성)
 *   → 청산(77번 시가) 59966 = 진입 대비 -119, 손실 전환
 *
 * 숏폼 업그레이드 적용: 컷 경계 이어받기(popDur 0·growDur 0), 컷 안 줌 전환,
 * 수익 실현이 아닌 손실 청산은 '손절' 태그(#9F0000 — 팀장 규칙 ③), 마무리 cmgCross.
 */

import { INTRO_CARRY, still } from './cmg12-cross.build.js';

/* 인트로에서 이어받은 손실 밴드·진입선은 하락이 끝난 47번 봉에서 멈춘다.
   컷5 초반엔 47번이 화면 밖이라 인트로와 픽셀 동일 — 컷6에서 카메라가 앞으로
   나아가도 옛 밴드가 새 랠리 위까지 덮지 않는다. */
const CARRY = INTRO_CARRY.map((L) => ({
  ...L,
  ...(L.type === 'cmgLevel' ? { toBar: 47 } : {}),
  ...(L.type === 'cmgNote' ? { clamp: false } : {}), // 컷6에서 카메라와 함께 위로 흘러 나간다
}));

const FPS = 60000 / 1001;

/* 인트로와 같은 교차 실측값 */
const X = { golden: 26, goldenPrice: 61221.4, dead: 33, deadPrice: 61250.9, entry: 61361.0, exit: 61013.0 };
/* 이어붙인 구간 실측값 */
const Y = { golden2: 65, entry2: 60084, peakBar: 72, peakHigh: 60533, bend: 72, dead2: 76, exit2: 59966 };

const chartBase = {
  visibleBars: 46,
  pricePad: 0.16,
  showGrid: false,
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 0, padBottom: 0, rightGap: 5 },
  ma: [
    { type: 'ema', period: 5, width: 5, color: '#0D9488' },
    { type: 'ema', period: 20, width: 5, color: '#F38808' },
  ],
};

export default {
  title: '차트명가 #12 — 후킹 나머지 (컷5·6)',
  width: 1920,
  height: 1080,
  fps: FPS,
  fpsExpr: '60000/1001',
  theme: { preset: 'chartmyeongga' },

  market: {
    seed: 12,
    base: 61200,
    tick: 0.5,
    vol: 160,
    barMinutes: 1440,
    startTime: Date.UTC(2026, 3, 6, 0, 0),
    segments: [
      { type: 'range', dir: 1, bars: 16, strength: 0.3 },
      { type: 'trend', dir: -1, bars: 6, strength: 0.75 },
      { type: 'trend', dir: 1, bars: 6, strength: 0.95 },
      { type: 'trend', dir: -1, bars: 20, strength: 1.5 },
      { type: 'range', dir: 1, bars: 8, strength: 0.3 },
      /* ── 여기부터 컷6용 이어붙임 (앞 캔들 불변 — 실측) ── */
      { type: 'trend', dir: 1, bars: 16, strength: 1.3 },
      { type: 'trend', dir: -1, bars: 10, strength: 1.3 },
      { type: 'range', bars: 5, width: 0.5 },
    ],
  },

  scenes: [
    /* ── 컷5 "곧바로 하락하는 가짜 신호에 속아 손실을 보거나" (2.9000s) ── */
    {
      id: 'cut5-fake-drop',
      name: '컷5 가짜 신호 하락 (2.9000s)',
      duration: 2.9,
      chart: {
        ...chartBase,
        /* 컷4 끝(r34, z1.5 부근)에서 이어받아 줌아웃하며 하락을 드러낸다 */
        reveal: [
          { t: 0, v: 34 },
          { t: 2.4, v: 46, ease: 'inOutCubic' },
          { t: 2.9, v: 46.5, ease: 'linear' },
        ],
        zoom: [
          { t: 0, v: 1.5 },
          { t: 1.2, v: 1.0, ease: 'inOutCubic' },
        ],
      },
      layers: [
        /* 컷4 끝 화면의 요소 전부를 정지 상태로 이어받는다 — 지우는 건 없고 더할 뿐
           (밴드도 컷3부터 있던 그대로 — 다시 자라지 않는다) */
        ...CARRY,
        { type: 'cmgCircle', bar: 39, price: 60600, rx: 210, ry: 270, width: 12, color: '#E90054', drawDur: 0.55, in: [0.9, 0.2] },
        { type: 'cmgNote', text: '가짜 신호', bar: 39, price: 61350, size: 56, color: '#E90054', in: [0.45, 0.3] },
      ],
    },

    /* ── 컷6 "추세가 이어지다가 … 손실 전환으로 마감" (7.9333s) ── */
    {
      id: 'cut6-late-cross',
      name: '컷6 지표가 늦어 손실 전환 (7.9333s)',
      duration: 8.066667,
      chart: {
        ...chartBase,
        reveal: [
          /* [v3] 연쇄 inOutCubic 이 펄스처럼 가속-감속을 반복해 정신없다는 피드백 —
             중간 구간을 linear 로 펴서 속도가 계단식으로만 줄게 한다 */
          { t: 0, v: 46.5 },
          { t: 1.0, v: 66, ease: 'inOutQuad' }, // 추세가 이어지다가 — 랠리 진입
          { t: 2.2, v: 74, ease: 'linear' }, // 지표가 꺾이는 순간
          { t: 3.8, v: 77.5, ease: 'linear' }, // 데드크로스가 그제야
          { t: 5.2, v: 82, ease: 'linear' },
          { t: 8.066667, v: 86, ease: 'linear' },
        ],
        zoom: [{ t: 0, v: 1 }],
      },
      layers: [
        /* 컷5 화면의 요소를 이어받는다 — 카메라가 오른쪽으로 흐르며 자연스럽게 프레임 밖으로 나간다 */
        ...CARRY,
        still({ type: 'cmgCircle', bar: 39, price: 60600, rx: 210, ry: 270, width: 12, color: '#E90054' }),
        still({ type: 'cmgNote', text: '가짜 신호', bar: 39, price: 61350, size: 56, color: '#E90054', clamp: false }),
        /* 랠리 진입 — 골든크로스2 에서 공식대로 또 매수 */
        { type: 'cmgArrow', bar: Y.golden2 + 1, price: 59880, dir: 'buy', label: '매수', size: 36, gap: 18, in: [0.75, 0.35] },
        {
          type: 'cmgLevel',
          price: Y.entry2,
          fromBar: Y.golden2 + 1,
          color: 'rgba(0,0,0,0.72)',
          thickness: 4,
          growDur: 0.35,
          in: [0.95, 0.2],
        },
        /* 지표가 꺾이는 순간 — 5 이평선이 고점 4봉 뒤에야 눕는다 */
        { type: 'cmgCircle', bar: Y.bend, price: 60286, rx: 120, ry: 90, width: 12, drawDur: 0.5, in: [1.5, 0.2] },
        { type: 'cmgNote', text: '익절 기준이 없다', bar: 69, price: 60640, size: 52, color: '#111111', in: [2.7, 0.3] },
        /* 데드크로스 — 청산 신호가 왔을 때는 이미 늦었다 */
        { type: 'cmgCircle', bar: Y.dead2, price: 60070, rx: 96, ry: 80, width: 12, drawDur: 0.5, in: [3.7, 0.2] },
        { type: 'cmgArrow', bar: 79, price: 60000, dir: 'sell', label: '손절', color: '#9F0000', size: 36, gap: 18, in: [4.15, 0.35] },
        {
          // 진입가~청산가 — 수익이었다가 손실로 뒤집힌 구간 (컷3 밴드와 같은 두께·같은 속도감)
          type: 'cmgLevel',
          price: Y.exit2,
          fromBar: Y.golden2 + 1,
          fillTo: Y.entry2,
          fill: '#FEBABA',
          color: '#9F0000',
          thickness: 23,
          growDur: 1.0,
          growEase: 'outCubic',
          in: [4.55, 0.25],
        },
        { type: 'cmgNote', text: '또 손실 전환', bar: 71, price: 59520, size: 56, color: '#E90054', in: [5.25, 0.3] },
        { type: 'cmgUnderline', bar: 71, price: 59520, dy: 50, width: 340, align: 'center', drawDur: 0.35, in: [5.65, 0.15] },
        /* "손실의 경험이 더 많으셨을 것" — 실패 공식 위에 큰 ✕ */
        { type: 'cmgCross', in: [6.35, 0.2] },
      ],
    },
  ],
};
