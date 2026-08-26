/**
 * 기본 컷씬 세트 — 나스닥 100 선물(NQ) / 5분봉
 *
 * 하나의 가격 이야기를 6컷으로 나눈 것이라, 순서대로 붙이면 그대로 한 편이 된다.
 *   ① 하락 추세  ② 박스권 형성  ③ 하단 이탈(스탑 헌팅)
 *   ④ 되돌림 롱 진입  ⑤ 손절·익절 세팅  ⑥ 익절 도달
 *
 * 대본이 나오면 이 파일의 layers 배열만 갈아 끼우면 된다.
 * 시간 단위는 전부 초(second). in:[시작, 길이] / out:[시작, 길이].
 */

/* 이 시나리오에서 실제로 쓰이는 가격대 (캔들 데이터에서 뽑은 값) */
const LV = {
  boxTop: 24750,      // 박스 상단 = 저항
  boxBottom: 24680,   // 박스 하단 = 지지
  stopHunt: 24615.75, // 62번 캔들 저점
  entry: 24688.75,    // 68번 캔들 종가에서 롱 진입
  stop: 24614.75,     // 스윙 저점 아래
  target: 24836.75,   // 손익비 1 : 2
};
const RISK = LV.entry - LV.stop;          // 74.00 pt
const REWARD = LV.target - LV.entry;      // 148.00 pt
const TICK_VALUE = 20;                    // NQ 미니 1계약 = 1포인트당 $20

/** 모든 컷에 공통으로 얹는 요소 */
const hud = { type: 'hud', symbol: 'NQ', name: '나스닥 100 선물', tf: '5분', in: [0.2, 0.6] };
const mark = { type: 'watermark', text: 'CHART CUT', in: [0.5, 0.8], opacity: 0.28 };

export default {
  title: '해외선물 차트 컷씬 — NQ 기본 세트',
  width: 1920,
  height: 1080,
  fps: 60,

  /* 여섯 컷이 모두 같은 캔들을 공유한다. seed 를 바꾸면 시나리오 전체가 바뀐다. */
  market: {
    seed: 42,
    base: 24780,
    tick: 0.25,
    vol: 20,
    barMinutes: 5,
    startTime: Date.UTC(2026, 5, 12, 13, 30),
    segments: [
      { type: 'trend', dir: -1, bars: 24, strength: 0.55 },
      { type: 'range', bars: 24, width: 1.6 },
      { type: 'breakout', dir: 1, bars: 34, strength: 1.15 },
    ],
  },

  theme: {
    // 국내식(상승 빨강/하락 파랑)으로 바꾸려면: candleScheme: 'korea'
    candleScheme: 'global',
  },

  scenes: [
    /* ------------------------------------------------------------------ */
    {
      id: '01-open',
      name: '오프닝 — 캔들 드로잉 + 타이틀',
      duration: 7,
      fadeIn: 0.4,
      fadeOut: 0.5,
      chart: {
        visibleBars: 58,
        ma: [{ type: 'ema', period: 20, color: 'rgba(120,170,255,0.55)', width: 3 }],
        reveal: [
          { t: 0, v: 6 },
          { t: 5.2, v: 48, ease: 'outCubic' },
          { t: 7, v: 52, ease: 'linear' },
        ],
      },
      layers: [
        hud,
        {
          type: 'titleCard',
          kicker: '해외선물 실전 매매',
          title: ['나스닥은 왜', '이 자리에서 돌았나'],
          subtitle: '박스권 이탈 → 되돌림 롱  ·  NQ 5분봉',
          size: 104,
          lineHeight: 122,
          y: 402,
          in: [1.7, 1.0],
          out: [5.9, 0.7],
          scrimStrength: 0.92,
        },
        mark,
      ],
    },

    /* ------------------------------------------------------------------ */
    {
      id: '02-structure',
      name: '구조 — 지지·저항 박스권',
      duration: 7.5,
      fadeIn: 0.35,
      fadeOut: 0.4,
      chart: {
        visibleBars: 58,
        ma: [{ type: 'ema', period: 20, color: 'rgba(120,170,255,0.45)', width: 3 }],
        reveal: [
          { t: 0, v: 52 },
          { t: 7.5, v: 56, ease: 'linear' },
        ],
      },
      layers: [
        hud,
        {
          type: 'caption',
          title: 'STEP 1',
          text: '먼저 가격이 갇혀 있는 구간부터 잡는다',
          in: [0.5, 0.6],
          out: [3.0, 0.5],
        },
        {
          type: 'hline',
          price: LV.boxTop,
          label: '저항  24,750',
          color: '#F2405D',
          priceTag: true,
          in: [1.3, 0.7],
          growDur: 0.7,
        },
        {
          type: 'hline',
          price: LV.boxBottom,
          label: '지지  24,680',
          color: '#22C55E',
          priceTag: true,
          in: [2.1, 0.7],
          growDur: 0.7,
        },
        {
          type: 'zone',
          from: LV.boxBottom,
          to: LV.boxTop,
          label: '박스권 70pt',
          color: '#4DA3FF',
          opacity: 0.1,
          in: [3.0, 0.7],
        },
        {
          type: 'caption',
          title: 'STEP 2',
          text: '70포인트 박스 — 이탈하는 쪽으로 따라붙는다',
          in: [3.9, 0.6],
          out: [7.0, 0.4],
        },
        mark,
      ],
    },

    /* ------------------------------------------------------------------ */
    {
      id: '03-breakdown',
      name: '이탈 — 하단 붕괴와 스탑 헌팅',
      duration: 7,
      fadeIn: 0.3,
      fadeOut: 0.4,
      chart: {
        visibleBars: 58,
        ma: [{ type: 'ema', period: 20, color: 'rgba(120,170,255,0.4)', width: 3 }],
        reveal: [
          { t: 0, v: 56 },
          { t: 4.4, v: 67, ease: 'inOutCubic' },
          { t: 7, v: 68, ease: 'linear' },
        ],
      },
      layers: [
        hud,
        {
          type: 'zone',
          from: LV.boxBottom,
          to: LV.boxTop,
          color: '#4DA3FF',
          opacity: 0.08,
          in: [0, 0.3],
          growDur: 0.3,
        },
        {
          type: 'hline',
          price: LV.boxBottom,
          label: '지지  24,680',
          color: '#22C55E',
          in: [0, 0.3],
          growDur: 0.3,
        },
        {
          type: 'caption',
          text: '지지선을 아래로 뚫었다',
          title: '이탈',
          accent: '#F2405D',
          in: [1.9, 0.5],
          out: [4.0, 0.4],
        },
        { type: 'flash', at: 2.05, dur: 0.26, strength: 0.4, color: '#F2405D' },
        {
          type: 'label',
          bar: 62,
          price: LV.stopHunt,
          text: '가짜 이탈 · 손절 물량 털기',
          color: '#FFB020',
          dx: -30,
          dy: 150,
          in: [4.5, 0.5],
        },
        {
          type: 'hline',
          price: LV.stopHunt,
          label: '저점  24,615.75',
          color: '#FFB020',
          priceTag: true,
          in: [4.9, 0.5],
          growDur: 0.5,
        },
        mark,
      ],
    },

    /* ------------------------------------------------------------------ */
    {
      id: '04-entry',
      name: '진입 — 되돌림 롱',
      duration: 7,
      fadeIn: 0.3,
      fadeOut: 0.4,
      chart: {
        visibleBars: 56,
        ma: [{ type: 'ema', period: 20, color: 'rgba(120,170,255,0.4)', width: 3 }],
        reveal: [
          { t: 0, v: 68 },
          { t: 3.2, v: 70, ease: 'inOutCubic' },
          { t: 7, v: 71.5, ease: 'linear' },
        ],
      },
      layers: [
        hud,
        {
          type: 'hline',
          price: LV.boxBottom,
          label: '되돌아온 지지선',
          color: '#22C55E',
          in: [0.4, 0.5],
          growDur: 0.5,
        },
        {
          type: 'marker',
          bar: 68,
          dir: 'long',
          price: 24668.75,
          label: '롱 진입  24,688.75',
          in: [1.5, 0.5],
        },
        {
          type: 'caption',
          title: '진입 근거',
          text: '박스 하단을 되찾은 첫 캔들 — 가짜 이탈 확정',
          in: [2.4, 0.6],
          out: [6.2, 0.4],
        },
        mark,
      ],
    },

    /* ------------------------------------------------------------------ */
    {
      id: '05-tpsl',
      name: '세팅 — 손절·익절과 손익비',
      duration: 7.5,
      fadeIn: 0.3,
      fadeOut: 0.4,
      chart: {
        visibleBars: 58,
        pricePad: 0.12,
        // 손절선·익절선이 화면 밖으로 나가지 않게 강제로 포함시킨다
        include: [LV.target, LV.stop],
        // 진입 캔들 오른쪽에 박스가 펼쳐질 공간을 넉넉히 비운다
        layout: { rightGap: 22 },
        ma: [{ type: 'ema', period: 20, color: 'rgba(120,170,255,0.35)', width: 3 }],
        reveal: [
          { t: 0, v: 71.5 },
          { t: 7.5, v: 73, ease: 'linear' },
        ],
      },
      layers: [
        hud,
        {
          type: 'marker',
          bar: 68,
          dir: 'long',
          price: 24668.75,
          in: [0, 0.25],
          pulse: false,
          size: 22,
        },
        {
          type: 'tradeBox',
          entry: LV.entry,
          tp: LV.target,
          sl: LV.stop,
          fromBar: 68,
          in: [0.9, 0.5],
          growDur: 0.85,
          tpLabel: `익절 ${LV.target.toLocaleString('en-US', { minimumFractionDigits: 2 })}  (+${REWARD}pt)`,
          slLabel: `손절 ${LV.stop.toLocaleString('en-US', { minimumFractionDigits: 2 })}  (-${RISK}pt)`,
          entryLabel: `진입 ${LV.entry.toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
        },
        {
          type: 'caption',
          title: '리스크 관리',
          text: '74포인트 걸고 148포인트를 노린다',
          in: [3.4, 0.6],
          out: [7.0, 0.4],
        },
        mark,
      ],
    },

    /* ------------------------------------------------------------------ */
    {
      id: '06-result',
      name: '결과 — 익절 도달 + 요약 카드',
      duration: 9,
      fadeIn: 0.3,
      fadeOut: 0.6,
      chart: {
        visibleBars: 62,
        pricePad: 0.16,
        include: [LV.target],
        ma: [{ type: 'ema', period: 20, color: 'rgba(120,170,255,0.35)', width: 3 }],
        reveal: [
          { t: 0, v: 73 },
          { t: 4.2, v: 82, ease: 'inOutCubic' },
        ],
      },
      layers: [
        hud,
        {
          type: 'hline',
          price: LV.target,
          label: '익절 목표  24,836.75',
          color: '#22C55E',
          labelX: 640,
          in: [0.2, 0.4],
          growDur: 0.4,
        },
        {
          type: 'hline',
          price: LV.entry,
          label: '진입가',
          color: 'rgba(233,240,255,0.8)',
          in: [0.2, 0.4],
          growDur: 0.4,
        },
        {
          type: 'counter',
          label: '평가 손익',
          from: 0,
          to: REWARD * TICK_VALUE,
          countFrom: 1.2,
          dur: 3.2,
          prefix: '$',
          signed: true,
          decimals: 0,
          size: 84,
          align: 'left',
          x: 96,
          y: 200,
          in: [1.0, 0.5],
          out: [4.9, 0.4],
        },
        {
          type: 'counter',
          label: '포인트',
          from: 0,
          to: REWARD,
          countFrom: 1.2,
          dur: 3.2,
          suffix: ' pt',
          signed: true,
          decimals: 2,
          size: 54,
          align: 'left',
          x: 96,
          y: 376,
          in: [1.2, 0.5],
          out: [4.9, 0.4],
        },
        { type: 'flash', at: 4.15, dur: 0.34, strength: 0.5, color: '#22C55E' },
        {
          type: 'statCard',
          title: '매매 결과',
          badge: '익절',
          badgeColor: '#22C55E',
          rows: [
            { k: '종목 / 방향', v: 'NQ  ·  롱' },
            { k: '진입 → 청산', v: '24,688.75 → 24,836.75' },
            { k: '손익비', v: '1 : 2.0' },
            { k: '수익', v: `+148.00 pt  /  +$${(REWARD * TICK_VALUE).toLocaleString('en-US')}`, tone: 'up' },
          ],
          width: 780,
          y: 300,
          in: [5.0, 0.7],
        },
        mark,
      ],
    },
  ],
};
