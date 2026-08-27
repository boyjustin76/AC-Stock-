/**
 * 차11 썸네일 B안 — 박스권 (숏폼 #5).
 *
 * A·C 와 달리 시장 자체를 순수 박스권으로 새로 만든다.
 * 원본 seed 41 은 앞 30봉만 박스라 EMA20 이 채 그려지기 전에 추세가 시작돼서,
 * "20일선이 옆으로 눕는다" 는 대본의 그림이 안 나온다.
 *
 * seed 7 · range 72봉 → EMA20 이 화면 내내 평평하다 (스프레드 58pt / 레인지 261pt).
 * 화면은 20~58 번봉. 이 구간은 23086~23263 안에서만 논다 = 박스.
 *   매수 44번  43번 하단 터치 뒤 양봉 마감
 *   익절 54번  박스 상단에서 직전 양봉을 덮는 장대 음봉 (대본의 청산 신호)
 */
const W = 1920, H = 1080;
const BOX = { hi: 23260, lo: 23086 };

export default {
  name: "차11 B안 — 박스권", width: W, height: H, fps: 30,
  theme: { preset: "chartmyeongga" },
  market: {
    seed: 7, base: 23200, tick: 0.25, vol: 58, barMinutes: 1440,
    segments: [{ type: "range", bars: 72, strength: 0.95, width: 2.0 }],
  },
  scenes: [{
    id: "B", name: "박스권", duration: 0.5,
    chart: {
      visibleBars: 39, reveal: 59, pricePad: 0.12,
      showGrid: false, showAxes: false, showLast: false,
      layout: { padLeft: 0, padRight: 0, padTop: 0, padBottom: 0, rightGap: 2 },
      ma: [{ type: "ema", period: 20, width: 9 }],
    },
    layers: [
      // 버튼 색은 brand/ui 원본 실측값(매수 #FF0000 / 매도 #0000FF)을 쓴다.
      // theme.js 의 #E80001·#0200F3 은 영상 프레임에서 잰 값이라 썸네일 버튼과 다르다.
      // 익절 #00FF24 = #7 썸네일 익절 도형의 solidFill rgb(0,255,36).
      { type: "hline", price: BOX.hi, color: "#9F0000", width: 11, dash: [30, 20], growDur: 0 },
      { type: "hline", price: BOX.lo, color: "#0B8C7F", width: 11, dash: [30, 20], growDur: 0 },
      { type: "cmgArrow", bar: 44, price: 23098, dir: "buy",  label: "매수", size: 74, gap: 26, popDur: 0,
        color: "#FF0000" },
      { type: "cmgArrow", bar: 54, price: 23245, dir: "sell", label: "익절", size: 74, gap: 26, popDur: 0,
        color: "#00FF24" },
    ],
  }],
};
