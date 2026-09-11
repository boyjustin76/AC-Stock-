/**
 * 새 채널 스타일 스틸 — "고정 소스 총집합" 한 장 (2026-09-11).
 *
 * 차트명가의 고정 소스(매수/매도 태그·익절/손절 밴드+라벨·손그림 원·문구·자막)를 한 화면에
 * 다 올린다. 틀(베젤)·타이틀 바·칩·로고는 렌더러가 아니라 tools/style/frame.py 가 위에 얹는다 —
 * 그래서 차트는 **창 자리**(x 40~1880 · y 150~980)만 쓰도록 layout 패딩을 준다.
 *
 * 시장·수치는 scenes/cmg-20ma-runner.scenes.js 의 것을 그대로 쓴다 (seed 11, 눌림목 42번 봉).
 * 한 장짜리라 duration 0.5, 모든 레이어는 이미 다 나온 상태(in 음수·popDur 0·growDur 0·drawDur 0).
 *
 *   node src/cli.mjs --config scenes/newch-style.scenes.js --all --stills 1 --out out/newch
 */
const LV = { entry: 23795, stop: 23665, target: 24055 };

export default {
  title: '새 채널 스타일 — 고정 소스 총집합',
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
    name: '고정 소스 총집합',
    duration: 0.5,
    chart: {
      /* 진입 봉(42)이 창의 6할 지점에 오게 — 앞쪽 고점(33)의 매도 태그까지 보인다.
         뒤쪽 급등(62 이후)은 잘라 익절 밴드가 화면을 다 먹지 않게 한다. */
      visibleBars: 56,
      reveal: 62,
      pricePad: 0.14,
      showGrid: false, showAxes: false, showLast: false,
      include: [LV.stop - 80, LV.target + 60],
      /* 창 자리만 쓴다. 위 150 은 틀의 상단 띠, 아래 100 은 하단 띠.
         창 안쪽 여백까지 더해 위 190 / 아래 150 으로 둔다. */
      layout: { padLeft: 60, padRight: 60, padTop: 190, padBottom: 150, rightGap: 6 },
      ma: [{ type: 'ema', period: 20, width: 5 }],
    },
    layers: [
      /* 익절·손절 밴드 — 진입 봉(42)에서 오른쪽 끝까지 */
      { type: 'cmgLevel', price: LV.stop, fromBar: 42, fillTo: LV.entry, fill: '#FEBABA', color: '#9F0000',
        label: '손절', labelSize: 62, thickness: 23, in: [-1, 0.2], growDur: 0 },
      { type: 'cmgLevel', price: LV.target, fromBar: 42, fillTo: LV.entry, fill: '#BAFDC0', color: '#14FF36',
        label: '익절', labelSize: 62, thickness: 23, in: [-1, 0.2], growDur: 0 },
      { type: 'cmgLevel', price: LV.entry, fromBar: 42, color: 'rgba(0,0,0,0.72)', thickness: 4, in: [-1, 0.2], growDur: 0 },
      /* 손그림 원 — 진입 뒤 20일선 재지지 자리. 진입 봉 근처는 태그·손절 라벨이 살아서 비운다 */
      { type: 'cmgCircle', bar: 52, price: LV.entry + 130, rx: 76, ry: 84, width: 11, color: '#E90054', drawDur: 0, in: [-1, 0.2] },
      /* 문구 — 검정 외곽선 흰 글자는 규칙 ⑤ 에 따라 자동 */
      /* 문구는 원 왼쪽 아래 — 손절 라벨(진입 봉 왼쪽에 붙음)과 안 겹치게 봉 27 */
      { type: 'cmgNote', bar: 27, price: LV.stop - 70, text: '20일선 눌림목', size: 46, color: '#F38808', align: 'center', in: [-1, 0.2] },
      /* 태그 — 매수는 진입 봉, 매도는 앞쪽 고점 봉(가격 생략 → 그 봉 종가) */
      { type: 'cmgArrow', bar: 42, price: LV.entry, dir: 'buy', label: '매수', size: 36, gap: 18, popDur: 0, in: [-1, 0.2] },
      { type: 'cmgArrow', bar: 33, dir: 'sell', label: '매도', size: 36, gap: 18, popDur: 0, color: '#0200F3', in: [-1, 0.2] },
      /* 손익비 배지 — 창 왼쪽 아래 */
      /* 손익비 배지 — 창 오른쪽 아래 (왼쪽 아래는 문구·라벨이 산다) */
      { type: 'cmgBadge', text: '손익비  1 : 2', x: 1820, y: 900, size: 40, color: '#E90054', align: 'right', in: [-1, 0.2] },
    ],
  }],
};
