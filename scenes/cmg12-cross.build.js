/**
 * 차트명가 #12 — RSI+이평선 스캘핑 · 인트로 4컷 (레이어 분리 빌더)
 *
 * 한 벌의 정의에서 **레이어별로 따로 렌더**할 수 있게 만든 것이다.
 * 프리미어에 한 장짜리 영상으로 얹으면 편집자가 아무것도 못 만진다.
 * 포토샵의 레이어 그룹처럼, 층을 나눠서 트랙에 쌓아야 끄고 켜고 옮길 수 있다.
 *
 *   build('all')     한 장에 다 그린다 (미리보기·스틸 확인용)
 *   build('candle')  캔들만 · 흰 배경        ← 불투명. 스택의 바닥
 *   build('ma')      이평선만 · 투명
 *   build('mark')    강조원 · 손실 밴드 · 진입선 · 투명
 *   build('tag')     매수/매도 태그 · 투명
 *   build('text')    글자 라벨 · 밑줄 · 투명
 *
 * 좌표가 어긋나지 않는 이유: 차트를 안 그려도 `frame()` 은 스케일과 뷰포트를 똑같이
 * 계산한다(`showCandles`/`showMAs` 는 그리기만 끈다). 그래서 오버레이 레이어만
 * 렌더해도 캔들 레이어와 픽셀 단위로 겹친다.
 *
 * ── 자막 원본 ─────────────────────────────────────────────────────────
 * 차명12롱폼 음성자막-한국어.srt (회사 드라이브 · 소스 폴더)
 *   ③ 00:00:03,390 ~ 00:00:07,400  "골든크로스에 사고 / 데드크로스에 팔아라."
 *   ⑤ 00:00:07,400 ~ 00:00:13,770  우리가 교과서처럼 외우고 있는 이 공식을 차트에
 *                                  대입해보지만, 실제 실전 매매에서는 이 공식대로
 *                                  수익이 나는 경우는 많지 않습니다
 *   ⑨ 00:00:13,770 ~ 00:00:15,520  크로스 신호만 보고 진입했다가
 *
 * ── 컷을 넷으로 나눈 이유 ────────────────────────────────────────────
 * 프리미어 프리셋 타임라인을 프레임으로 뽑아 보고 나눴다 (jobs/m5_frames.jsx).
 * 프리셋의 0~16초는 빈 자리가 아니라 고정 오프닝이다 — 5.93~12.20 은 인트로
 * 애니메이션(지그재그 + 매수/매도 태그) → 타이틀 카드가 화면의 주인공이라,
 * 거기에 라벨 붙은 차트를 깔면 매수/매도가 두 벌로 겹친다.
 *
 *   컷1  5.533~ 7.833  2.3000s  공식을 짚는다 — 원·라벨·태그 전부 등장
 *   컷2  7.833~12.200  4.3667s  타이틀 구간 — 컷1 요소 유지 (비우지 않는다)
 *   컷3 12.200~15.900  3.7000s  손실이 드러난다 (요소 유지 + 밴드 추가)
 *   컷4 15.900~17.700  1.8000s  크로스 신호 하나로 파고든다 (카메라 재프레이밍)
 *
 * 길이는 자막 초를 시퀀스 timebase(30.0) 프레임으로 반올림한 값이다.
 * 프레임 번호로 옮기면 어긋난다 — 대본은 29.97, 컷 경계는 30.0 격자다
 * (실측 근거: log/PREMIERE-LAB.md 의 '격자' 항목).
 *
 * 카메라 워크(밀고 당기기)는 여기 넣지 않고 프리미어의 모션 키프레임으로 준다.
 * 회사 프리셋이 그렇게 되어 있어서 편집자가 나중에 손볼 수 있어야 한다.
 * 컷4 의 `zoom` 만 남겼다 — 그건 픽셀 확대가 아니라 데이터 재프레이밍이라
 * 프리미어 비율로 흉내 내면 해상도를 잃는다. **레이어 전부에 똑같이 적용해야
 * 층이 어긋나지 않는다** — 그래서 chart 설정은 레이어와 무관하게 공유한다.
 *
 * 자막·타이틀·로고는 넣지 않는다 — 프리미어 프리셋에 이미 있어 겹친다.
 *
 * 색
 *   20 이평선  #F38808  brand_token 4 '20일 이동평균선' 실측
 *    5 이평선  #0D9488  메인프리셋 안의 색상 범례가 '반대되는 개념의 서브 강조
 *                       (예: 매수/매도, 상승/하락 등 상반된 지표 비교)' 로 정의한 색.
 *                       프리셋 XML 의 소스 텍스트에서 원문 확인.
 *
 * RSI 는 렌더러에 보조지표 창이 없어 그리지 않는다. 이 구간은 이평선 교차 이야기라
 * 대본에 RSI 가 나오지 않는다 — 뒤 구간에서 필요해지면 그때 만든다.
 */

const FPS = 60000 / 1001; // 59.94005994 = 29.97 × 2

/* 30.0 격자로 반올림한 컷 경계(초) — 프리미어 배치값과 같은 수를 쓴다 */
/* [정확.srt 재동기 2026-08-31] 새 컷편집 기준. c3=12.2 는 프리셋 고정 오프닝(타이틀 카드 끝)
   가정 유지 — 내레이션만 +2.1초 밀렸고 템플릿 그래픽은 고정이라는 전제다. 어긋나면 여기만 고친다. */
const AT = { c1: 5.533333, c2: 7.833333, c3: 12.2, c4: 15.9, end: 17.7 };
const CUT = {
  rule: AT.c2 - AT.c1, // 4.0000  공식
  bed: AT.c3 - AT.c2, // 4.8000  배경
  loss: AT.c4 - AT.c3, // 1.5667  손실
  signal: AT.end - AT.c4, // 1.7667  신호 하나
};

/**
 * 아래 market 으로 만든 캔들에서 실측한 값이다 (눈대중으로 바를 찍지 않는다).
 *   node src/tools/find-cross.mjs scenes/cmg12-cross.scenes.js
 *     골든크로스  bar=26  교차가=61221.4  종가=61361.0  이후 10봉 -0.63%
 *     데드크로스  bar=33  교차가=61250.9  종가=61013.0  이후 10봉 -1.27%
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

/* ── 컷을 넘어 살아남는 요소들 ──────────────────────────────────────────
   컷을 나누는 기준은 '새 요소로 대체될 때'다. 그 전에는 요소를 지우지 않는다
   (조정 레이어 방식 — 2026-08-31 컷2 깜빡임 반려). still() 은 등장 애니메이션을
   전부 떼서, 앞 컷에서 이미 나온 요소가 컷 경계에서 다시 튀어나오지도
   사라지지도 않게 한다. */
export const still = (L) => ({ ...L, in: [-1, 0], out: undefined, drawDur: 0, popDur: 0, growDur: 0 });

const buyTag = { type: 'cmgArrow', bar: X.golden, price: X.goldenPrice - 150, dir: 'buy', label: '매수', size: 36, gap: 18 };
const sellTag = { type: 'cmgArrow', bar: X.dead, price: X.deadPrice + 150, dir: 'sell', label: '매도', size: 36, gap: 18 };
const note5 = { type: 'cmgNote', text: '5 이평선', bar: 13, price: 61302.1 - 190, size: 44, color: '#0D9488' };
const note20 = { type: 'cmgNote', text: '20 이평선', bar: 20, price: 61242.4 + 205, size: 44, color: '#F38808' };
const goldenCircle = { type: 'cmgCircle', bar: X.golden, price: X.goldenPrice, rx: 88, ry: 76, width: 12 };
const goldenNote = { type: 'cmgNote', text: '골든크로스', bar: X.golden, price: X.goldenPrice - 330, size: 60 };
const deadCircle = { type: 'cmgCircle', bar: X.dead, price: X.deadPrice, rx: 88, ry: 76, width: 12 };
const deadNote = { type: 'cmgNote', text: '데드크로스', bar: X.dead, price: X.deadPrice + 390, size: 60 };
/* 컷3에서 태어나는 것들 */
const entryLine = { type: 'cmgLevel', price: X.entry, fromBar: X.golden, color: 'rgba(0,0,0,0.72)', thickness: 4 };
const lossBand = { type: 'cmgLevel', price: X.exit, fromBar: X.golden, fillTo: X.entry, fill: '#FEBABA', color: '#9F0000', thickness: 23 };
const lossNote = { type: 'cmgNote', text: '수익이 아니라 손실', bar: X.dead + 4, price: X.deadPrice - 900, size: 60, color: '#E90054' };
const lossUnder = { type: 'cmgUnderline', bar: X.dead + 4, price: X.deadPrice - 900, dy: 54, width: 392, align: 'center' };
/* 컷4에서 '골든크로스' 라벨을 대체하는 문장 */
const signalNote = { type: 'cmgNote', text: '크로스 신호 하나', bar: X.golden, price: X.goldenPrice - 330, size: 56 };

/* 컷1 요소 전부 — 컷2·컷3이 정지 상태로 이어받는다 */
const CUT1_SET = [note5, note20, goldenCircle, goldenNote, buyTag, deadCircle, deadNote, sellTag];

/* 컷4가 끝났을 때 화면에 남아 있는 것들 — 컷5·컷6(cmg12-hook2)이 이어받는다.
   goldenNote 는 signalNote 로 대체됐고, lossNote/lossUnder 는 컷4 줌인 때 넘겨준다(아래 참조). */
export const INTRO_CARRY = [
  note5, note20, goldenCircle, buyTag, deadCircle, deadNote, sellTag,
  entryLine, lossBand, signalNote,
].map(still);

/* 레이어 층 정의 — 어느 타입이 어느 층으로 가는지 한 곳에서 정한다.
   아래에서 위로 쌓인다. 프리미어 트랙 번호와 순서가 같다. */
export const LAYERS = {
  candle: { 층: 1, 이름: '캔들', types: [], chart: { showMAs: false }, opaque: true },
  ma: { 층: 2, 이름: '이평선', types: [], chart: { showCandles: false } },
  mark: { 층: 3, 이름: '강조', types: ['cmgCircle', 'cmgLevel'], chart: { showCandles: false, showMAs: false } },
  tag: { 층: 4, 이름: '매수매도', types: ['cmgArrow'], chart: { showCandles: false, showMAs: false } },
  text: { 층: 5, 이름: '텍스트', types: ['cmgNote', 'cmgUnderline'], chart: { showCandles: false, showMAs: false } },
};

/* 컷 정의 — 레이어와 무관한 원본. build() 가 여기서 걸러 낸다 */
const SCENES = [
  /* ── ① "골든크로스에 사고 데드크로스에 팔아라." ─────────────────── */
  {
    id: 'cut1-rule',
    name: '① 교과서 공식',
    duration: CUT.rule,
    chart: {
      ...chartBase,
      reveal: [
        { t: 0, v: 28 }, // 골든크로스(26)는 이미 지나 있다
        { t: 0.5, v: 30, ease: 'linear' },
        { t: 1.15, v: 35, ease: 'inOutCubic' }, // 데드크로스(33)가 여기서 드러난다
        { t: CUT.rule, v: 40, ease: 'linear' },
      ],
    },
    layers: [
      /* '5 이평선'은 '골든크로스' 라벨과 겹치지 않게 왼쪽으로 뺀 자리다 */
      { ...note5, in: [0.05, 0.2] },
      { ...note20, in: [0.2, 0.2] },
      // 골든크로스 — 사라
      { ...goldenCircle, drawDur: 0.5, in: [0.35, 0.15] },
      { ...goldenNote, in: [0.6, 0.25] },
      { ...buyTag, in: [0.8, 0.3] },
      // 데드크로스 — 팔아라
      { ...deadCircle, drawDur: 0.5, in: [1.3, 0.15] },
      { ...deadNote, in: [1.55, 0.25] },
      { ...sellTag, in: [1.75, 0.3] },
    ],
  },

  /* ── ② 프리셋 인트로 애니메이션·타이틀 카드 구간 ──────────────── */
  {
    id: 'cut2-bed',
    name: '② 타이틀 구간 — 컷1 요소 유지',
    duration: CUT.bed,
    chart: {
      ...chartBase,
      /*  [2026-08-31 반려 수정] 원래 '프리셋 타이틀이 화면을 덮는다'는 가정으로 라벨을
          비웠는데, 실제 편집본에서는 차트가 그대로 보여 요소가 사라졌다 되돌아오는
          깜빡임이 됐다. 컷1 요소를 전부 정지 상태로 유지한다 — 새로 등장하는 것만 없다.  */
      reveal: [
        { t: 0, v: 40 },
        { t: CUT.bed, v: 44, ease: 'linear' },
      ],
    },
    layers: CUT1_SET.map(still),
  },

  /* ── ③ "이 공식대로 수익이 나는 경우는 많지 않습니다" ──────────── */
  {
    id: 'cut3-loss',
    name: '③ 공식대로 하면 손실',
    duration: CUT.loss,
    chart: {
      ...chartBase,
      reveal: [
        { t: 0, v: 44 },
        { t: CUT.loss, v: 45.3, ease: 'linear' },
      ],
    },
    layers: [
      /* 컷1·컷2의 요소는 그대로 — 새로 태어나는 건 손실 표현뿐 */
      ...CUT1_SET.map(still),
      /*  진입~청산 사이의 실제 손실 밴드 (진입선 + 밴드).
          cmgProfit 은 높이가 '현재가'를 따라가서 청산 뒤에도 깊어진다 — 실제 손실(-348)보다
          커 보이는 거짓말이라 cmgLevel 고정 밴드로 그린다. 라벨은 안 단다(손절 주문이 아니라
          데드크로스 청산). growEase outCubic — 기본 outExpo 는 순간 스냅이라 '대충 그린 느낌'
          이라는 피드백(2026-08-31)이 있었다. 천천히 정성 들여 긋는다.  */
      { ...entryLine, growDur: 0.6, growEase: 'outCubic', in: [0.25, 0.15] },
      { ...lossBand, growDur: 1.3, growEase: 'outCubic', in: [0.55, 0.3] },
      { ...lossNote, in: [1.9, 0.25] },
      { ...lossUnder, drawDur: 0.35, in: [2.5, 0.15] },
    ],
  },

  /* ── ④ "크로스 신호만 보고 진입했다가" ─────────────────────────── */
  {
    id: 'cut4-signal-only',
    name: '④ 크로스 신호 하나',
    duration: CUT.signal,
    chart: {
      ...chartBase,
      /*  뷰는 오른쪽 끝(reveal + rightGap)에 고정이라 zoom 만 키우면 최신 봉만 커진다.
          교차 지점을 다시 잡으려면 reveal 을 되감아야 한다. 컷이 나뉘어 있어 점프컷으로 읽힌다.  */
      reveal: [
        { t: 0, v: 32 },
        { t: CUT.signal, v: 34, ease: 'linear' },
      ],
      zoom: [
        { t: 0, v: 1.15 },
        { t: CUT.signal, v: 1.5, ease: 'inOutCubic' },
      ],
    },
    layers: [
      /* 요소 유지 + 카메라만 되감아 파고든다. 원을 다시 그리지 않는다 */
      ...[note5, note20, goldenCircle, buyTag, deadCircle, deadNote, sellTag, entryLine, lossBand].map(still),
      /* '수익이 아니라 손실'은 줌인과 함께 짧게 넘겨준다 — 새 문장이 그 역할을 대체 */
      { ...still(lossNote), out: [0.1, 0.35] },
      { ...still(lossUnder), out: [0.1, 0.35] },
      /* '골든크로스' 라벨이 같은 자리의 새 문장으로 교체된다 (크로스페이드) */
      { ...still(goldenNote), out: [0.15, 0.3] },
      { ...signalNote, in: [0.35, 0.3] },
    ],
  },
];

/**
 * @param {'all'|'candle'|'ma'|'mark'|'tag'|'text'} layer
 */
export function build(layer = 'all') {
  const L = layer === 'all' ? null : LAYERS[layer];
  if (layer !== 'all' && !L) throw new Error(`모르는 레이어: ${layer} (${Object.keys(LAYERS).join(', ')})`);

  return {
    title: `차트명가 #12 — 골든/데드크로스 인트로 4컷${L ? ` · ${L.이름} 층` : ''}`,
    width: 1920,
    height: 1080,
    fps: FPS,
    fpsExpr: '60000/1001',

    /*  오버레이 층은 배경을 지운다. 캔들 층만 흰 배경을 깔고 스택의 바닥이 된다.  */
    theme: { preset: 'chartmyeongga', ...(L && !L.opaque ? { transparent: true } : {}) },

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

    scenes: SCENES.map((s) => ({
      ...s,
      /*  chart 설정(reveal·zoom)은 층마다 똑같아야 한다. 하나라도 다르면 좌표가 어긋난다.
          레이어별로 더하는 것은 '무엇을 그리지 않을지' 뿐이다.  */
      chart: { ...s.chart, ...(L ? L.chart : {}) },
      layers: L ? s.layers.filter((y) => L.types.indexOf(y.type) >= 0) : s.layers,
    })),
  };
}

export default build('all');
