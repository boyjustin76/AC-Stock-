/**
 * 새 채널 스타일 v2 "전통(병풍·낙관)" — 차트 본체만 렌더 (2026-09-11).
 * 기존 차트명가 문법은 쓰지 않는다. 캔들 + 오방색 이평선 3개만 렌더하고,
 * 한지·병풍 틀·낙관 태그·족자 자막은 tools/style/trad.py 가 카메라 좌표로 얹는다.
 * 이평 색 = 오방색(단청 실측): 적 #D42A26(10) · 황 #C9A227(20) · 녹 #0B8A4C(50, 오방의 靑은 단청에서 녹).
 */
import { loadBars } from '../src/market/loadBars.js';

export default {
  title: '새 채널 스타일 v2 — 전통',
  width: 1920, height: 1080, fps: 30,
  theme: { preset: 'chartmyeongga' },
  /* 봉은 data/synth/newch-trad.json (tools/style/trad-bars.mjs): seed 11 합성 + 앞에 워밍업 60봉.
     워밍업이 있어야 10/20/50 이평이 첫 화면 봉부터 그려진다 (없으면 선이 중간에서 시작해 잘린 것처럼 보인다). */
  market: { bars: (await loadBars('data/synth/newch-trad.json')).bars, tick: 0.25, barMinutes: 1440 },
  scenes: [{
    id: 'trad', name: '전통 — 차트 본체', duration: 0.5,
    chart: {
      visibleBars: 58, reveal: 124,   /* 60 워밍업 + 64 */ pricePad: 0.12,
      showGrid: false, showAxes: false, showLast: false,
      include: [23555, 24355],
      layout: { padLeft: 150, padRight: 330, padTop: 250, padBottom: 230, rightGap: 6 },
      ma: [
        { type: 'sma', period: 10, width: 5, color: '#D42A26' },
        { type: 'ema', period: 20, width: 5, color: '#C9A227' },
        { type: 'sma', period: 50, width: 5, color: '#0B8A4C' },
      ],
    },
    layers: [],
  }],
};
