/** 차11 썸네일 A안 — 추세추종 (숏폼 #4). 눌림목 진입 → 완전 이격 음봉 청산. */
const W = 1920, H = 1080;
const LV = { boxHi: 23284, boxLo: 23078, entry: 23258, exit: 23699 };
const market = {
  seed: 41, base: 23200, tick: 0.25, vol: 62, barMinutes: 1440,
  segments: [
    { type: "range", bars: 30, strength: 0.9 },
    { type: "trend", dir: 1, bars: 16, strength: 0.72 },
    { type: "pullback", dir: 1, bars: 7, strength: 1.1 },
    { type: "trend", dir: 1, bars: 34, strength: 0.86 },
    { type: "spike", dir: -1, bars: 9, strength: 1.25 },
  ],
};
const layout = { padLeft: 0, padRight: 0, padTop: 0, padBottom: 0, rightGap: 2 };
export default {
  name: "차11 A안 — 추세추종", width: W, height: H, fps: 30,
  theme: { preset: "chartmyeongga" }, market,
  scenes: [{
    id: "A", name: "추세추종", duration: 0.5,
    chart: { visibleBars: 96, reveal: 96, pricePad: 0.10, showGrid: false, showAxes: false, showLast: false,
             layout, ma: [{ type: "ema", period: 20, width: 9 }] },
    layers: [
      // 버튼 색은 brand/ui 원본 실측값(매수 #FF0000 / 매도 #0000FF)을 쓴다.
      // theme.js 의 #E80001·#0200F3 은 영상 프레임에서 잰 값이라 썸네일 버튼과 다르다.
      // 익절 #00FF24 = #7 썸네일 익절 도형의 solidFill rgb(0,255,36).
      { type: "cmgArrow", bar: 53, price: LV.entry, dir: "buy",  label: "매수", size: 74, gap: 26, popDur: 0,
        color: "#FF0000" },
      { type: "cmgArrow", bar: 87, price: LV.exit,  dir: "sell", label: "익절", size: 74, gap: 26, popDur: 0,
        color: "#00FF24" },
    ],
  }],
};
