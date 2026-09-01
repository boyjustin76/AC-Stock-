/**
 * 차트명가 #12 — 골든/데드크로스 인트로+후킹 · **연속 클립 1개** (레이어 분리 빌더)
 *
 * [2026-09-01 재구성] 원래 컷 6개(컷1~4 이 파일 + 컷5·6 cmg12-hook2)였다.
 * 피드백: "컷3과 컷4~5의 차이가 거의 없는데 컷을 쪼개서 요소 대부분을 반복하니
 * 템포가 빠르고 정신없다. 컷을 나누는 기준은 새 요소로 대체할 때뿐 — 그 전에는
 * 한 클립을 쭉 끌고 가면서 요소를 하나씩 더하고 카메라로 내보내라. 뒤 챕터
 * (guide·fail — 컷 길이 9.7~29.6초)의 호흡이 모범답안이다."
 * 실측으로도 인트로만 컷 중앙값 3.3초·요소 등장 초당 3.5개로, 뒤 챕터(중앙값
 * ~17초·초당 0.5개)의 6배 밀도였다. 대체가 일어나는 경계가 인트로 안에는 없어서
 * (골든크로스→크로스 신호 하나 문구 교체는 같은 클립 안 크로스페이드로 충분)
 * 5.533~28.667초 전체를 클립 하나로 합쳤다. 컷4의 카메라 되감기 점프컷과
 * 줌인→줌아웃 왕복(내용에 도움 없는 줌이라는 피드백)도 함께 없앴다.
 * → 이월(still/INTRO_CARRY) 장치 자체가 필요 없어졌다. 요소는 한 번 태어나서
 *   크로스페이드로 대체되거나 카메라로 퇴장할 뿐이다. (룰북 ⑧⑬)
 *
 * 레이어별 분리 렌더(포토샵 레이어 그룹처럼 트랙에 쌓는 용도)는 그대로 지원한다:
 *   build('all') / build('candle') / build('ma') / build('mark') / build('tag') / build('text')
 *
 * ── 자막 원본 ─────────────────────────────────────────────────────────
 * 차명12롱폼 음성자막-한국어.srt [정확.srt 재동기 2026-08-31]
 *   ③      3.390~ 7.400  "골든크로스에 사고 / 데드크로스에 팔아라."
 *   ⑤~⑧   7.400~13.770  공식을 대입해보지만 실전에서는 수익이 많지 않다
 *   ⑨     13.770~15.520  "크로스 신호만 보고 진입했다가"
 *   ⑩⑪   17.700~20.600  "곧바로 하락하는 가짜 신호에 속아 손실을 보거나"
 *   ⑫~⑯  20.600~28.667  "추세가 이어지다가 지표가 꺾이는 순간 어디서
 *                          익절해야 할지 몰라 손실 전환으로 마감 …"
 *
 * ── 배치 ─────────────────────────────────────────────────────────────
 *   클립 1개  intro-hook  5.533~28.667  (23.1333s = 시퀀스 30fps 로 694프레임,
 *   시작점 프레임 166).  구간 내부 국면 (t 는 클립 상대 시각):
 *     A 공식        0      ~ 2.300   원·라벨·태그 등장 (자막 ③)
 *     B 타이틀      2.300  ~ 6.667   새 요소 없음 — 카메라만 흐른다 (프리셋 타이틀 구간)
 *     C 손실        6.667  ~10.367   진입선·손실 밴드·문장 (자막 ⑤~⑧)
 *     D 신호 하나  10.367  ~12.167   '골든크로스'→'크로스 신호 하나' 크로스페이드 (자막 ⑨)
 *     E 가짜 신호  12.167  ~15.067   하락 강조원·'가짜 신호' (자막 ⑩⑪)
 *     F 손실 전환  15.067  ~23.133   랠리→늦은 데드크로스→손실 전환 (자막 ⑫~⑯)
 *
 * ── 시장 실측 (node src/tools/find-events.mjs · 눈대중으로 바를 찍지 않는다) ──
 * 교차1 (인트로): 골든 bar=26 교차가 61221.4 → 데드 bar=33. 진입 61361(27봉 시가)
 *   → 청산 61013(34봉 시가) = -348. '곧바로 하락하는 가짜 신호'.
 * 교차2 (후킹, 2026-09-01 랠리 확대 — ↑16봉 s2.0 / ↓10봉 s2.4):
 *   골든2 bar=62 → 진입 60161.0(63봉 시가) → 고점 61168.0@72봉 (+1007, +1.67%)
 *   → 5이평 꺾임 bar=73 → 데드2 bar=77 (고점 5봉 뒤 — 후행성)
 *   → 청산 59953.5(78봉 시가) = -207.5. '수익이었다가 손실 전환'.
 *   세그먼트 이어붙이기는 앞 캔들을 바꾸지 않는다 (0~55봉 o/h/l/c 동일 — 실측).
 *
 * 카메라: 줌 없음. reveal 단일 진행 — 랠리 구간만 한 번 가속하고 그 뒤로는
 * 계단식으로만 감속한다 (룰북 ⑪). 자막·타이틀·로고는 넣지 않는다(프리셋과 겹침).
 *
 * 색: 20 이평선 #F38808 (brand_token 4 실측) · 5 이평선 #0D9488 (프리셋 색상 범례).
 * RSI 는 이 구간 대본에 나오지 않아 그리지 않는다.
 */

const FPS = 60000 / 1001; // 59.94005994 = 29.97 × 2

const DUR = 23.133333; // 28.666667 - 5.533333 · 30fps 격자로 정확히 694프레임

/* 국면 시작 시각 (클립 상대) — 자막 경계를 30.0 격자로 반올림한 값 */
const PH = { rule: 0, bed: 2.3, loss: 6.666667, signal: 10.366667, fake: 12.166667, turn: 15.066667 };

/* 교차1 실측값 */
const X = {
  golden: 26,
  goldenPrice: 61221.4, // 교차 시점의 20 이평선 값 — 강조원의 중심
  dead: 33,
  deadPrice: 61250.9,
  entry: 61361.0, // 골든크로스 다음 봉(27) 시가
  exit: 61013.0, // 데드크로스 다음 봉(34) 시가
};
/* 교차2 실측값 (랠리 확대 뒤 재실측 2026-09-01) */
const Y = {
  golden2: 62,
  entry2: 60161.0, // 63봉 시가
  peakBar: 72,
  peakHigh: 61168.0,
  bend: 73, // 5이평선이 하락으로 도는 첫 봉
  dead2: 77,
  exit2: 59953.5, // 78봉 시가
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

/* ── 요소들 — 전부 클립 안에서 한 번만 태어난다 ─────────────────────────
   퇴장은 두 가지뿐 (룰북 ⑧⑨⑩):
   · 크로스페이드 대체 — 골든크로스→크로스 신호 하나, 수익이 아니라 손실→(역할 인계)
   · 카메라 — 봉에 앵커된 요소는 reveal 이 진행되면 프레임 밖으로 흘러 나간다.
     늦게까지 사는 라벨엔 clamp:false (세로 클램프가 상단에 붙잡지 않게),
     끝난 거래의 밴드·선엔 toBar:47 (새 랠리 위까지 따라오지 않게). */

/* 레이어 층 정의 — 아래에서 위로. 프리미어 트랙 번호와 순서가 같다.
   버튼(tag)이 맨 위다 — 팀장 규칙 ⑭ '버튼은 무조건 레이어 맨 앞' (2026-09-01). */
export const LAYERS = {
  candle: { 층: 1, 이름: '캔들', types: [], chart: { showMAs: false }, opaque: true },
  ma: { 층: 2, 이름: '이평선', types: [], chart: { showCandles: false } },
  mark: { 층: 3, 이름: '강조', types: ['cmgCircle', 'cmgLevel', 'cmgCross'], chart: { showCandles: false, showMAs: false } },
  text: { 층: 4, 이름: '텍스트', types: ['cmgNote', 'cmgUnderline'], chart: { showCandles: false, showMAs: false } },
  tag: { 층: 5, 이름: '매수매도', types: ['cmgArrow'], chart: { showCandles: false, showMAs: false } },
};

/**
 * @param {'all'|'candle'|'ma'|'mark'|'tag'|'text'} layer
 */
export function build(layer = 'all') {
  const L = layer === 'all' ? null : LAYERS[layer];
  if (layer !== 'all' && !L) throw new Error(`모르는 레이어: ${layer} (${Object.keys(LAYERS).join(', ')})`);

  const scene = {
    id: 'intro-hook',
    name: '인트로+후킹 연속 클립 (23.1333s · 5.533 배치)',
    duration: DUR,
    chart: {
      ...chartBase,
      ...(L ? L.chart : {}),
      /* 줌 없음 — 단일 reveal. 랠리 사슬(14.2~16.6)만 가속하고, 그 뒤로는
         7.9 → 2.5 → 1.3 봉/초로 계단식 감속만 한다 (룰북 ⑪) */
      reveal: [
        { t: 0, v: 28 }, // 골든크로스(26)는 이미 지나 있다
        { t: 0.5, v: 30, ease: 'linear' },
        { t: 1.15, v: 35, ease: 'inOutCubic' }, // 데드크로스(33)가 여기서 드러난다
        { t: 2.3, v: 40, ease: 'linear' },
        { t: PH.loss, v: 44, ease: 'linear' }, // 타이틀 구간 — 흐르기만 한다
        { t: PH.signal, v: 45.3, ease: 'linear' },
        { t: 12.9, v: 47, ease: 'linear' }, // 가짜 신호 하락의 끝(47봉)까지
        { t: 14.2, v: 55, ease: 'inOutQuad' }, // 완만히 출발해
        { t: 16.6, v: 74, ease: 'linear' }, // 랠리와 꺾임(73)을 등속으로 드러낸다
        { t: 19.4, v: 81, ease: 'linear' }, // 데드크로스2(77)·손절(79)
        { t: DUR, v: 86, ease: 'linear' },
      ],
    },
    layers: [
      /* ── A 공식 (자막 ③) — '5 이평선'은 '골든크로스' 라벨과 안 겹치는 왼쪽 자리 ── */
      { type: 'cmgNote', text: '5 이평선', bar: 13, price: 61112.1, size: 44, color: '#0D9488', clamp: false, in: [0.05, 0.2] },
      { type: 'cmgNote', text: '20 이평선', bar: 20, price: 61447.4, size: 44, color: '#F38808', clamp: false, in: [0.2, 0.2] },
      // 골든크로스 — 사라
      { type: 'cmgCircle', bar: X.golden, price: X.goldenPrice, rx: 88, ry: 76, width: 12, drawDur: 0.5, in: [0.35, 0.15] },
      { type: 'cmgNote', text: '골든크로스', bar: X.golden, price: X.goldenPrice - 330, size: 60, in: [0.6, 0.25], out: [10.516667, 0.3] },
      { type: 'cmgArrow', bar: X.golden, price: X.goldenPrice - 150, dir: 'buy', label: '매수', size: 36, gap: 18, in: [0.8, 0.3] },
      // 데드크로스 — 팔아라
      { type: 'cmgCircle', bar: X.dead, price: X.deadPrice, rx: 88, ry: 76, width: 12, drawDur: 0.5, in: [1.3, 0.15] },
      /*  데드크로스 라벨·매도 태그는 F 국면에서 카메라가 랠리로 나아가면 가격 천장이
          낮아져 상단에 반쯤 걸린 채 지나간다(probe 실측 16.55/17.55초~). 세로로 잘리기
          직전에 페이드 — 카메라 퇴장의 세로판이다. 다시 돌아오지 않으니 깜빡임이 아니다.  */
      { type: 'cmgNote', text: '데드크로스', bar: X.dead, price: X.deadPrice + 390, size: 60, clamp: false, in: [1.55, 0.25], out: [16.15, 0.4] },
      { type: 'cmgArrow', bar: X.dead, price: X.deadPrice + 150, dir: 'sell', label: '매도', size: 36, gap: 18, in: [1.75, 0.3], out: [17.1, 0.45] },

      /* ── B 타이틀 (2.3~6.667) — 새 요소 없음. 지우지도 않는다 ── */

      /* ── C 손실 (자막 ⑤~⑧) — 진입~청산의 실제 손익.
         cmgProfit 은 높이가 현재가를 따라가 청산 뒤에도 깊어지는 거짓말이라 cmgLevel 고정
         밴드로 그린다. growEase outCubic — 기본 outExpo 는 순간 스냅이라 '대충 그린 느낌'
         피드백(2026-08-31). toBar 47 — 끝난 거래의 밴드가 뒤 랠리까지 따라오지 않게.  */
      { type: 'cmgLevel', price: X.entry, fromBar: X.golden, toBar: 47, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0.6, growEase: 'outCubic', in: [PH.loss + 0.25, 0.15] },
      { type: 'cmgLevel', price: X.exit, fromBar: X.golden, toBar: 47, fillTo: X.entry, fill: '#FEBABA', color: '#9F0000', thickness: 23, growDur: 1.3, growEase: 'outCubic', in: [PH.loss + 0.55, 0.3] },
      { type: 'cmgNote', text: '수익이 아니라 손실', bar: X.dead + 4, price: X.deadPrice - 900, size: 60, color: '#E90054', in: [PH.loss + 1.9, 0.25], out: [PH.signal + 0.1, 0.35] },
      { type: 'cmgUnderline', bar: X.dead + 4, price: X.deadPrice - 900, dy: 54, width: 392, align: 'center', drawDur: 0.35, in: [PH.loss + 2.5, 0.15], out: [PH.signal + 0.1, 0.35] },

      /* ── D 신호 하나 (자막 ⑨) — '골든크로스'가 같은 자리의 새 문장으로 교체 (크로스페이드).
         '수익이 아니라 손실'은 새 문장이 역할을 인계받으며 짧게 넘겨준다. 카메라는 계속 간다 ── */
      { type: 'cmgNote', text: '크로스 신호 하나', bar: X.golden, price: X.goldenPrice - 330, size: 56, clamp: false, in: [PH.signal + 0.35, 0.3] },

      /* ── E 가짜 신호 (자막 ⑩⑪) — 하락 전체를 강조원으로 ── */
      { type: 'cmgNote', text: '가짜 신호', bar: 39, price: 61350, size: 56, color: '#E90054', clamp: false, in: [PH.fake + 0.45, 0.3], out: [17.75, 0.4] }, // 상단 잘림(18.17~) 직전 퇴장 — 원은 남는다
      { type: 'cmgCircle', bar: 39, price: 60600, rx: 210, ry: 270, width: 12, color: '#E90054', drawDur: 0.55, in: [PH.fake + 0.9, 0.2] },

      /* ── F 손실 전환 (자막 ⑫~⑯) — 골든크로스2 에서 공식대로 또 매수 ── */
      { type: 'cmgArrow', bar: Y.golden2 + 1, price: 59920, dir: 'buy', label: '매수', size: 36, gap: 18, in: [PH.turn + 0.75, 0.35] },
      { type: 'cmgLevel', price: Y.entry2, fromBar: Y.golden2 + 1, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0.35, in: [PH.turn + 0.95, 0.2] },
      /* 지표가 꺾이는 순간 — 5 이평선이 고점(72) 하나 뒤에야 눕는다 */
      { type: 'cmgCircle', bar: Y.peakBar, price: 60840, rx: 120, ry: 90, width: 12, drawDur: 0.5, in: [PH.turn + 1.5, 0.2] },
      /*  이 시점의 가격 천장은 랠리 고점(61168) 언저리라 그 위엔 자리가 없다(probe 실측).
          하락이 끝나고 비어 있는 왼쪽 상공(55~60봉 위)에 둔다.  */
      { type: 'cmgNote', text: '익절 기준이 없다', bar: 57, price: 60900, size: 52, color: '#111111', in: [PH.turn + 2.7, 0.3] },
      /* 데드크로스2 — 청산 신호가 왔을 때는 이미 늦었다 */
      { type: 'cmgCircle', bar: Y.dead2, price: 60400, rx: 96, ry: 80, width: 12, drawDur: 0.5, in: [PH.turn + 3.7, 0.2] },
      { type: 'cmgArrow', bar: 79, price: 60170, dir: 'sell', label: '손절', color: '#9F0000', size: 36, gap: 18, in: [PH.turn + 4.15, 0.35] },
      /* 진입가~청산가 — 수익이었다가 손실로 뒤집힌 구간 (앞 밴드와 같은 두께·속도감) */
      { type: 'cmgLevel', price: Y.exit2, fromBar: Y.golden2 + 1, fillTo: Y.entry2, fill: '#FEBABA', color: '#9F0000', thickness: 23, growDur: 1.0, growEase: 'outCubic', in: [PH.turn + 4.55, 0.25] },
      { type: 'cmgNote', text: '또 손실 전환', bar: 70, price: 59650, size: 56, color: '#E90054', in: [PH.turn + 5.25, 0.3] },
      { type: 'cmgUnderline', bar: 70, price: 59650, dy: 50, width: 340, align: 'center', drawDur: 0.35, in: [PH.turn + 5.65, 0.15] },
      /* "손실의 경험이 더 많으셨을 것" — 실패 공식 위에 큰 ✕ */
      { type: 'cmgCross', in: [PH.turn + 6.35, 0.2] },
    ].filter((y) => (L ? L.types.indexOf(y.type) >= 0 : true)),
  };

  return {
    title: `차트명가 #12 — 인트로+후킹 연속 클립${L ? ` · ${L.이름} 층` : ''}`,
    width: 1920,
    height: 1080,
    fps: FPS,
    fpsExpr: '60000/1001',

    /* 오버레이 층은 배경을 지운다. 캔들 층만 흰 배경을 깔고 스택의 바닥이 된다 */
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
        /* ── 후킹용 이어붙임 (앞 캔들 불변 — 실측) · 2026-09-01 랠리 확대 ── */
        { type: 'trend', dir: 1, bars: 16, strength: 2.0 }, // 56~71  느리게 이어지는 큰 상승
        { type: 'trend', dir: -1, bars: 10, strength: 2.4 }, // 72~81  꺾임 → 손실 전환
        { type: 'range', bars: 5, width: 0.5 }, // 82~86
      ],
    },

    scenes: [scene],
  };
}

export default build('all');
