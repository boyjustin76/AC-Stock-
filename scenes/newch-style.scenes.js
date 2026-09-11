/**
 * 새 채널 스타일 스틸 v2 — 브라우저 창 안의 차트 (2026-09-11).
 *
 * 렌더러는 **브랜드 정확도가 필요한 것만** 그린다: 캔들 · 20일선(주황) · 50일선(청록) ·
 * 익절/손절 밴드+라벨 · 매수/매도 태그 · 손그림 원 · 문구. 나머지 도구 견본(지지/저항/청산/
 * 골든·데드크로스 링, 구간 박스, 추세선, 지시선, 자막, 배지, 범례, 브라우저 크롬)은
 * tools/style/frame.py 가 이 씬의 카메라 값(scene-export 의 X0·BW·Y0·K)으로 같은 좌표계에 그린다.
 *
 * 창 자리: 브라우저 콘텐츠 영역 x 34~1886 · y 150~1010. 그 안에서 타이틀·칩(위 140)과
 * 자막(아래 100)을 비워 layout 패딩을 잡는다.
 *
 *   node src/cli.mjs --config scenes/newch-style.scenes.js --all --stills 1 --out out/newch
 *   node tools/ae/scene-export.mjs scenes/newch-style.scenes.js --out C:/aelab/ae   # 카메라 값
 */
const LV = { entry: 23795, stop: 23665, target: 24055 };

export default {
  title: '새 채널 스타일 v2 — 브라우저 창 안의 도구 총집합',
  width: 1920,
  height: 1080,
  fps: 30,
  theme: { preset: 'chartmyeongga' },
  market: {
    seed: 11, base: 23400, tick: 0.25, vol: 58, barMinutes: 1440,
    startTime: Date.UTC(2026, 0, 5, 0, 0),
    segments: [
      { type: 'trend', dir: 1, bars: 34, strength: 0.52 },
      { type: 'pullback', dir: 1, bars: 9, strength: 1.15 },
      { type: 'trend', dir: 1, bars: 52, strength: 0.82 },
    ],
  },
  scenes: [{
    id: 'sources',
    name: '도구 총집합',
    duration: 0.5,
    chart: {
      visibleBars: 56,
      reveal: 62,
      pricePad: 0.12,
      showGrid: false, showAxes: false, showLast: false,
      include: [LV.stop - 120, LV.target + 380],
      layout: { padLeft: 74, padRight: 74, padTop: 300, padBottom: 170, rightGap: 6 },
      /* 새 문법: 20일선 주황(브랜드) + 50일선 청록(팔레트 0D9488) — 더원의 범례 박스와 짝 */
      ma: [
        { type: 'ema', period: 20, width: 5 },
        { type: 'sma', period: 50, width: 4, color: '#0D9488' },
      ],
    },
    layers: [
      /* 밴드는 진입 2봉 뒤(44)부터 — 라벨이 진입 봉 왼쪽에 붙는 구조라 42 에서 시작하면 태그·원과 겹친다 */
      { type: 'cmgLevel', price: LV.stop, fromBar: 44, fillTo: LV.entry, fill: '#FEBABA', color: '#9F0000',
        label: '손절', labelSize: 56, thickness: 20, in: [-1, 0.2], growDur: 0 },
      { type: 'cmgLevel', price: LV.target, fromBar: 44, fillTo: LV.entry, fill: '#BAFDC0', color: '#14FF36',
        label: '익절', labelSize: 56, thickness: 20, in: [-1, 0.2], growDur: 0 },
      { type: 'cmgLevel', price: LV.entry, fromBar: 44, color: 'rgba(0,0,0,0.72)', thickness: 4, in: [-1, 0.2], growDur: 0 },
      /* 손그림 원(차트명가 서명)은 골든크로스 자리에 — 트팩의 노란 링을 이걸로 대신한다 */
      { type: 'cmgCircle', bar: 14, price: 23425, rx: 58, ry: 64, width: 9, color: '#E90054', drawDur: 0, in: [-1, 0.2] },
      { type: 'cmgNote', bar: 33, price: 23560, text: '20일선 눌림목', size: 42, color: '#F38808', align: 'center', in: [-1, 0.2] },
      { type: 'cmgArrow', bar: 42, price: LV.entry + 30, dir: 'buy', label: '매수', size: 34, gap: 18, popDur: 0, in: [-1, 0.2] },
      { type: 'cmgArrow', bar: 28, dir: 'sell', label: '매도', size: 34, gap: 18, popDur: 0, color: '#0200F3', in: [-1, 0.2] },
    ],
  }],
};
