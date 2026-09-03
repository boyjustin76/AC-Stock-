/**
 * 차12 썸네일 A안 — 진짜 눌림목 (매수 관점).
 * 시장은 본편 매수 챕터(cmg12-buy)와 같은 seed 161 을 그대로 쓴다 —
 * 썸네일과 영상이 같은 차트를 보여야 회차가 하나로 읽힌다.
 *   정배열 bar 33~96 · RSI 55 상향돌파 bar 52 · 진입 bar 53 · 러너 bar 90
 * 타이틀이 좌상단을 덮으므로 값싼 여백은 왼쪽 위에 남긴다.
 */
import { market, COLOR } from './cmg12-guide.scenes.js';

const W = 1920, H = 1080;

export default {
  name: '차12 A안 — 진짜 눌림목', width: W, height: H, fps: 30,
  theme: { preset: 'chartmyeongga' }, market,
  scenes: [{
    id: 'A', name: '진짜 눌림목', duration: 0.5,
    chart: {
      visibleBars: 52, reveal: 92, pricePad: 0.10,
      /* 타이틀 두 줄(y 57~395)이 좌상단을 덮는다. 위쪽에 없는 값을 include 로 끼워
         가격 눈금 천장을 올려 캔들 전체를 아래로 내린다 — 글자와 안 겹치게 */
      include: [16220],
      showGrid: false, showAxes: false, showLast: false,
      /* padRight 40 — RSI 55/45 라벨은 패널 오른쪽 끝에 붙는데,
         그대로 두면 완성본에서 틀(핑크 26px) 밑에 반쯤 잘린다. 40px 안으로 들인다.
         차트 배경이 흰색이라 오른쪽에 생긴 띠는 종이 배경과 구분되지 않는다 */
      layout: { padLeft: 0, padRight: 40, padTop: 0, padBottom: 0, rightGap: 2 },
      ma: [
        { type: 'sma', period: 10, width: 9, color: COLOR.ma10 },
        { type: 'sma', period: 34, width: 9, color: COLOR.ma34 },
      ],
      rsi: {
        period: 10, height: 0.24, gap: 22, baseline: 50, color: COLOR.rsi, width: 7,
        levels: [
          { v: 55, label: '55', color: 'rgba(17,17,17,0.62)', width: 3 },
          { v: 45, label: '45', color: 'rgba(17,17,17,0.62)', width: 3 },
        ],
      },
    },
    layers: [
      /* 이름표는 RSI 하나만 붙인다. 10일선·34일선 이름표는 아랫줄 타이틀
         (오른쪽 끝 x=1563, 아래 y=446)에 그대로 깔려서 뺐다 — 주황·초록 두 선은
         타이틀의 '이평선' 이 이미 이름을 대 준다(규칙 20 의 #11 판단과 같다) */
      /* cmgBadge 의 등장 스케일은 in[0] 기준이라 t=0 스틸에서는 0배로 사라진다.
         in 을 음수로 밀어 이미 다 나온 상태로 잡는다 (popDur 은 이 레이어가 안 본다).
         자리는 오른쪽 아래다 — 왼쪽 아래는 템플릿 로고 자리(49,977 · 209x52)라 겹친다 */
      { type: 'cmgBadge', text: 'RSI', x: 1560, y: 1005, size: 52, color: COLOR.badge, in: [-1, 0.2] },
      // 55선 재돌파 — 이 회차의 핵심 시각 요소(규칙 21)
      { type: 'cmgCircle', bar: 52, rsi: 60.5, rx: 62, ry: 50, width: 11, color: '#E90054', drawDur: 0 },
      // 버튼 색은 brand/ui 원본 실측 (매수 #FF0000 / 익절 #00FF24) — 차11 과 같다
      { type: 'cmgArrow', bar: 53, price: 15546, dir: 'buy',  label: '매수', size: 74, gap: 26, popDur: 0, color: '#FF0000' },
      { type: 'cmgArrow', bar: 91, price: 15920, dir: 'sell', label: '익절', size: 74, gap: 26, popDur: 0, color: '#00FF24' },
    ],
  }],
};
