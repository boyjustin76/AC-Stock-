#!/usr/bin/env node
/**
 * 컷② 주석 레이어의 **픽셀 좌표를 실측**한다.
 *
 *   node tools/ae/anchors.mjs
 *
 * 매뉴얼 A3 은 "좌표는 스틸 위에서 자로 재라" 지만, 스틸을 만든 매핑을 그대로
 * 다시 계산하는 편이 정확하다. 바닥 스틸(lab/ae/cut2-base-r63-무주석.png)은
 * cut2-base.scenes.js 로 뽑은 것이고, 그 chart 설정은 sl-11-4 컷②와 **동일하다**
 * (visibleBars 32 · pricePad 0.14 · include 없음 · ma ema20 · layout 여백 0 · rightGap 6).
 * 그러므로 reveal 63 · zoom 1 로 makeScale 을 부르면 스틸 위 좌표가 그대로 나온다.
 *
 * 출력은 C:/aelab/anchors.json 에도 쓴다 — AE 잡이 이 파일을 읽어 좌표를 박는다.
 * 즉 좌표는 사람 눈이 아니라 렌더러가 정한다.
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { makeCandles } from '../../src/market/candles.js';
import { Chart } from '../../src/render/chart.js';
import { makeTheme } from '../../src/render/theme.js';
import base from '../../lab/ae/cut2-base.scenes.js';

const REVEAL = 63;
const ZOOM = 1;

const { bars } = makeCandles(base.market);
const c = base.scenes[0].chart;

// ctx 는 좌표 계산에 안 쓰인다 (그리기에만 쓴다) — 더미로 충분하다.
const chart = new Chart({
  ctx: null,
  width: base.width,
  height: base.height,
  bars,
  theme: makeTheme(base.theme),
  layout: c.layout,
  view: { visibleBars: c.visibleBars, pricePad: c.pricePad, include: c.include ?? null, ma: c.ma },
});

const vp = chart.viewport(REVEAL, ZOOM, 0);
const s = chart.makeScale(vp);
const r = (n) => Math.round(n * 100) / 100;

/* sl-11-4.scenes.js 의 LV 와 같은 값 — 진실은 씬 파일이다 */
const LV = { entry: 23795, stop: 23665, target: 23795 + (23795 - 23665) * 2, missedHigh: 24418.25, note: 24270 };

const out = {
  _설명: 'tools/ae/anchors.mjs 가 만든 실측 좌표. 1080x1080, 컷② reveal 63 · zoom 1 기준. AE 는 좌상단 원점.',
  comp: { w: base.width, h: base.height, fps: base.fps, frames: 176, duration: r(176 / base.fps) },
  viewport: { left: r(vp.left), right: r(vp.right), lo: r(vp.lo), hi: r(vp.hi) },
  barW: r(s.barW),
  plot: { x: s.plot.x, y: s.plot.y, w: s.plot.w, h: s.plot.h, right: s.plot.right, bottom: s.plot.bottom },
  x: { bar42: r(s.x(42)), bar53: r(s.x(53)), bar57: r(s.x(57)), bar62: r(s.x(62)), right: r(s.plot.right) },
  y: {
    entry: r(s.y(LV.entry)),
    stop: r(s.y(LV.stop)),
    target: r(s.y(LV.target)),
    missedHigh: r(s.y(LV.missedHigh)),
    note: r(s.y(LV.note)),
  },
  price: LV,
  픽셀당가격: r((vp.hi - vp.lo) / s.plot.h),
};

console.log(JSON.stringify(out, null, 2));
mkdirSync('C:/aelab', { recursive: true });
writeFileSync('C:/aelab/anchors.json', JSON.stringify(out, null, 2), 'utf8');

/*  AE 잡이 바로 읽을 수 있게 .jsx 로도 낸다. 런타임에 파일을 읽지 않아도 되고
    (파일쓰기 권한과 무관하게 안전하다) ExtendScript 에 JSON 파서가 없는 판에서도 통한다.
    저장소에 커밋되므로 좌표가 언제 바뀌었는지도 diff 로 남는다.  */
const jsx =
  '/*  tools/ae/anchors.mjs 가 생성한다. 손으로 고치지 마라 — node tools/ae/anchors.mjs 로 다시 낸다.\n' +
  '    컷② reveal 63 · zoom 1 기준 실측 좌표. 1080x1080, 좌상단 원점.  */\n' +
  'var ANCHORS = ' + JSON.stringify(out, null, 2) + ';\n';
writeFileSync(new URL('./jobs/_anchors.jsx', import.meta.url), jsx, 'utf8');
console.error('\nC:/aelab/anchors.json 과 tools/ae/jobs/_anchors.jsx 에 썼다.');
