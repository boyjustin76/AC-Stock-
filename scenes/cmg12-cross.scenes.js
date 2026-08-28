/**
 * 차트명가 #12 — RSI+이평선 스캘핑 · 인트로 3컷 (테스트)
 *
 * 자막 원본: 차명12롱폼 음성자막-한국어.srt (회사 드라이브 · 소스 폴더)
 *   ③ 00:00:03,390 ~ 00:00:07,400  4.010s  "골든크로스에 사고 데드크로스에 팔아라."
 *   ⑤ 00:00:07,400 ~ 00:00:13,770  6.370s  우리가 교과서처럼 외우고 있는 이 공식을 차트에
 *                                          대입해보지만, 실제 실전 매매에서는 이 공식대로
 *                                          수익이 나는 경우는 많지 않습니다
 *   ⑨ 00:00:13,770 ~ 00:00:15,520  1.750s  크로스 신호만 보고 진입했다가
 *
 * 컷 길이는 자막의 초를 그대로 쓴다. 프레임 수로 환산해 옮기면 어긋난다 —
 * 프리미어 시퀀스의 컷 경계는 30.0 격자이고 대본 타임코드는 29.97 이라 20분에서
 * 36프레임(1.2초) 차이가 난다. 초로 옮기면 오차가 프레임 하나 안쪽이다.
 * (실측 근거: log/PREMIERE-LAB.md 의 '격자' 항목)
 *
 * 자막·타이틀·로고·배지는 넣지 않는다 — 프리미어 프리셋에 이미 있어 겹친다.
 * 차트 위 라벨만 넣는다.
 *
 * 색
 *   20 이평선  #F38808  brand_token 4 '20일 이동평균선' 실측
 *    5 이평선  #0D9488  메인프리셋 안의 색상 범례가 '반대되는 개념의 서브 강조
 *                       (예: 매수/매도, 상승/하락 등 상반된 지표 비교)' 로 정의한 색.
 *                       프리셋 XML 의 소스 텍스트에서 원문 확인.
 *                       단기 이평선 색은 실측된 것이 없어, 용도 정의가 맞는 이 색을 골랐다.
 *
 * RSI 는 렌더러에 보조지표 창이 없어 그리지 않는다. 이 3컷은 이평선 교차 이야기라
 * 대본에 RSI 가 나오지 않는다 — 뒤 구간에서 필요해지면 그때 만든다.
 */

const FPS = 60000 / 1001; // 59.94005994 = 29.97 × 2

/* 자막에서 그대로 가져온 컷 길이(초) */
const CUT = {
  rule: 7.4 - 3.39, //  4.010
  apply: 13.77 - 7.4, //  6.370
  entry: 15.52 - 13.77, //  1.750
};

/**
 * 아래 market 으로 만든 캔들에서 실측한 값이다 (§3-10 — 눈대중으로 바를 찍지 않는다).
 *   node src/tools/find-cross.mjs scenes/cmg12-cross.scenes.js
 *     골든크로스  bar=26  교차가=61221.4  종가=61361.0
 *     데드크로스  bar=33  교차가=61250.9  종가=61013.0
 *   진입 61361.0(27봉 시가) → 청산 61013.0(34봉 시가) = -348 (-0.57%).
 *   진입 후 고점은 +0.44% 뿐이다 — '곧바로 하락하는 가짜 신호' 그대로다.
 */
const X = {
  golden: 26,
  goldenPrice: 61221.4, // 교차 시점의 20 이평선 값 — 강조원의 중심
  dead: 33,
  deadPrice: 61250.9,
  entry: 61361.0, // 골든크로스 다음 봉(27) 시가 — '공식대로' 진입했을 때의 체결가
  exit: 61013.0, // 데드크로스 다음 봉(34) 시가
  low: 59484.0,
};

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

/* ①~③ 에 걸쳐 이어지는 매수·매도 태그. in 을 안 주면 컷 경계에서 다시 안 튀어나온다 */
const buyTag = {
  type: 'cmgArrow',
  bar: X.golden,
  price: X.goldenPrice - 150,
  dir: 'buy',
  label: '매수',
  size: 36,
  gap: 18,
};
const sellTag = {
  type: 'cmgArrow',
  bar: X.dead,
  price: X.deadPrice + 150,
  dir: 'sell',
  label: '매도',
  size: 36,
  gap: 18,
};

export default {
  title: '차트명가 #12 — 골든/데드크로스 인트로 3컷',
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
    barMinutes: 1440, // 일봉
    startTime: Date.UTC(2026, 3, 6, 0, 0),
    segments: [
      { type: 'range', dir: 1, bars: 16, strength: 0.3 }, //  0~15  지루한 횡보
      { type: 'trend', dir: -1, bars: 6, strength: 0.75 }, // 16~21  눌림
      { type: 'trend', dir: 1, bars: 6, strength: 0.95 }, // 22~27  짧은 반등 → 골든크로스
      { type: 'trend', dir: -1, bars: 20, strength: 1.5 }, // 28~47  곧바로 하락 = 가짜 신호
      { type: 'range', dir: 1, bars: 8, strength: 0.3 }, // 48~55
    ],
  },

  scenes: [
    /* ── ① "골든크로스에 사고 데드크로스에 팔아라." ─────────────────── */
    {
      id: 'cut1-rule',
      name: '① 교과서 공식 (4.010s)',
      duration: CUT.rule,
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 28 }, // 골든크로스(26)는 이미 지나 있다
          { t: 1.0, v: 30, ease: 'linear' },
          { t: 2.2, v: 35, ease: 'inOutCubic' }, // 데드크로스(33)가 여기서 드러난다
          { t: CUT.rule, v: 42, ease: 'linear' },
        ],
      },
      layers: [
        {
          type: 'cmgNote',
          text: '5 이평선',
          bar: 13,
          price: 61302.1 - 190, // bar13 의 ema5 아래. '골든크로스' 라벨과 겹치지 않게 왼쪽으로 뺐다
          size: 44,
          color: '#0D9488',
          in: [0.15, 0.3],
        },
        {
          type: 'cmgNote',
          text: '20 이평선',
          bar: 20,
          price: 61242.4 + 205, // bar20 의 ema20 위
          size: 44,
          color: '#F38808',
          in: [0.35, 0.3],
        },
        // 골든크로스 — 사라
        {
          type: 'cmgCircle',
          bar: X.golden,
          price: X.goldenPrice,
          rx: 88,
          ry: 76,
          width: 12,
          drawDur: 0.6,
          in: [0.95, 0.2],
        },
        {
          type: 'cmgNote',
          text: '골든크로스',
          bar: X.golden,
          price: X.goldenPrice - 330,
          size: 60,
          in: [1.25, 0.3],
        },
        { ...buyTag, in: [1.5, 0.35] },
        // 데드크로스 — 팔아라
        {
          type: 'cmgCircle',
          bar: X.dead,
          price: X.deadPrice,
          rx: 88,
          ry: 76,
          width: 12,
          drawDur: 0.6,
          in: [2.45, 0.2],
        },
        {
          type: 'cmgNote',
          text: '데드크로스',
          bar: X.dead,
          price: X.deadPrice + 390,
          size: 60,
          in: [2.75, 0.3],
        },
        { ...sellTag, in: [3.0, 0.35] },
      ],
    },

    /* ── ② 공식을 대입해보지만 수익이 나지 않는다 ──────────────────── */
    {
      id: 'cut2-apply',
      name: '② 공식대로 하면 수익이 안 난다 (6.370s)',
      duration: CUT.apply,
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 42 },
          { t: CUT.apply, v: 50, ease: 'linear' }, // 청산 뒤로도 흘러내리는 것을 보여 준다
        ],
      },
      layers: [
        { ...buyTag, popDur: 0 },
        {
          /*  진입~청산 사이의 실제 손실 밴드.
              cmgProfit 은 높이가 '현재가'를 따라가서, 청산한 뒤에도 계속 깊어진다 —
              실제 청산 손실(-348)보다 훨씬 커 보여서 그림이 거짓말을 한다.
              cmgLevel 로 진입가~청산가 사이를 고정 밴드로 그린다.
              색은 손절 토큰 실측값(brand_token 7·8)이지만 라벨은 달지 않는다 —
              손절 주문이 아니라 데드크로스 청산이라 '손실 구간' 이라는 뜻만 남긴다.  */
          type: 'cmgLevel',
          price: X.exit,
          fromBar: X.golden,
          fillTo: X.entry,
          fill: '#FEBABA',
          color: '#9F0000',
          thickness: 23,
          growDur: 0.5,
          in: [0.15, 0.25],
        },
        {
          // 진입가 — 얇은 검은 선
          type: 'cmgLevel',
          price: X.entry,
          fromBar: X.golden,
          color: 'rgba(0,0,0,0.72)',
          thickness: 4,
          growDur: 0.4,
          in: [0.1, 0.2],
        },
        {
          type: 'cmgNote',
          text: '공식대로 진입',
          bar: X.golden + 3,
          price: X.entry + 330,
          size: 52,
          in: [0.7, 0.3],
        },
        { ...sellTag, popDur: 0 },
        {
          type: 'cmgNote',
          text: '수익이 아니라 손실',
          bar: X.dead + 4,
          price: X.deadPrice - 900,
          size: 60,
          color: '#E90054',
          in: [4.1, 0.35],
        },
        {
          type: 'cmgUnderline',
          bar: X.dead + 4,
          price: X.deadPrice - 900,
          dy: 54,
          width: 392,
          align: 'center',
          drawDur: 0.4,
          in: [4.5, 0.2],
        },
      ],
    },

    /* ── ③ 크로스 신호만 보고 진입했다가 ───────────────────────────── */
    {
      id: 'cut3-signal-only',
      name: '③ 크로스 신호만 보고 진입 (1.750s)',
      duration: CUT.entry,
      chart: {
        ...chartBase,
        /*  뷰는 오른쪽 끝(reveal + rightGap)에 고정이라 zoom 만 키우면 최신 봉만 커진다.
            교차 지점을 다시 잡으려면 reveal 을 되감아야 한다. 컷이 나뉘어 있어 점프컷으로 읽힌다.  */
        reveal: [
          { t: 0, v: 32 },
          { t: CUT.entry, v: 34, ease: 'linear' },
        ],
        zoom: [
          { t: 0, v: 1.15 },
          { t: CUT.entry, v: 1.5, ease: 'inOutCubic' },
        ],
      },
      layers: [
        { ...buyTag, popDur: 0 },
        {
          type: 'cmgCircle',
          bar: X.golden,
          price: X.goldenPrice,
          // 이 컷은 zoom 1.5 라 화면상 원이 커진다. 매수 태그를 덮지 않게 반지름을 줄였다
          rx: 94,
          ry: 78,
          width: 13,
          drawDur: 0.5,
          in: [0.08, 0.2],
        },
        {
          type: 'cmgNote',
          text: '크로스 신호 하나',
          bar: X.golden,
          price: X.goldenPrice - 330,
          size: 56,
          in: [0.4, 0.3],
        },
      ],
    },
  ],
};
