/**
 * 차트명가 #12 — 말 구간 설명 카드 2클립 (인포그래픽 브리지)
 *
 * [2026-09-01] "차트가 딱히 필요 없는 개념/논리 구간도 비우지 말고, 팀장(기존 제작자)
 * 최종본을 실측해 그 스타일대로 간단한 설명 카드를 넣어라" (이정찬 — 빼더라도 본인이 뺀다).
 *
 * 스타일 실측 원본: 차명#4_TF시그널 (최종).mp4 (드라이브 11eZrZdLgp4MLABX0dNR8dKF1lfMCZmSz)
 *   — 개념 구간 = 세게 블러+화이트 워시된 차트 배경 위에 큰 검정(흰 외곽선+옅은 그림자)
 *     타이포가 리스트로 쌓인다. 키워드는 형광펜 #F8D890, 아직 차례가 안 온 항목은
 *     예고 베이지 #F9E9BF 로 미리 떠 있다가 자기 내레이션에 본색이 된다.
 *   — 구현: cmgText 레이어(layers.js) + chart.blurPx/alpha (engine.js). 서체 Gmarket Sans.
 *
 * 자막 원본: 차명12롱폼 음성자막_정확.srt
 *   브리지1  큐 17~32  28.667~58.600 (29.9333s)  문제의 원인 → 오늘 배울 것 예고
 *   브리지2  큐 54~63  97.967~116.967 (19.0000s)  스윙 아님 — 1분/5분봉 초단타·스캘핑
 *
 * 배치 (30fps 격자):
 *   bridge-intro  프레임  860 (00:00:28:20) · 길이 898 (끝 1758 = guide-intro 앞 말끝)
 *   bridge-scalp  프레임 2939 (00:01:37:29) · 길이 570 (끝 3509 = guide-set 시작)
 *
 * 배경 차트는 각각 인트로(seed 12)·소개(seed 161) 시장을 이어받아 천천히 흐른다 —
 * 블러 16px + 알파 0.15 (레퍼런스 워시 실측 근사). 요소 규칙은 룰북 ⑧⑨⑪ 그대로.
 */

import { market as guideMarket } from './cmg12-guide.scenes.js';

const FPS = 60000 / 1001;

const washBase = {
  visibleBars: 46,
  pricePad: 0.16,
  showGrid: false,
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 216, padBottom: 162, rightGap: 5 },
  blurPx: [{ t: 0, v: 16 }],
  alpha: [{ t: 0, v: 0.15 }],
};

export default {
  title: '차트명가 #12 — 말 구간 설명 카드 2클립',
  width: 1920,
  height: 1080,
  fps: FPS,
  fpsExpr: '60000/1001',
  theme: { preset: 'chartmyeongga' },

  scenes: [
    /* ── 브리지1: 문제의 원인 → 오늘 배울 것 (29.9333s · 프레임 860 배치) ── */
    {
      id: 'bridge-intro',
      name: '브리지1 원인과 예고 (29.9333s)',
      duration: 29.933333,
      market: {
        /* 인트로 병합 클립과 같은 시장 — 워시 배경으로 이어진다 */
        seed: 12,
        base: 61200,
        tick: 0.5,
        vol: 160,
        barMinutes: 1440,
        startTime: Date.UTC(2026, 3, 6, 0, 0),
        segments: [
          { type: 'range', dir: 1, bars: 16, strength: 0.3 },
          { type: 'trend', dir: -1, bars: 6, strength: 0.75 },
          { type: 'trend', dir: 1, bars: 6, strength: 0.95 },
          { type: 'trend', dir: -1, bars: 20, strength: 1.5 },
          { type: 'range', dir: 1, bars: 8, strength: 0.3 },
          { type: 'trend', dir: 1, bars: 16, strength: 2.0 },
          { type: 'trend', dir: -1, bars: 10, strength: 2.4 },
          { type: 'range', bars: 5, width: 0.5 },
        ],
      },
      chart: {
        ...washBase,
        ma: [
          { type: 'ema', period: 5, width: 5, color: '#0D9488' },
          { type: 'ema', period: 20, width: 5, color: '#F38808' },
        ],
        reveal: [{ t: 0, v: 50 }, { t: 29.933333, v: 87, ease: 'linear' }],
      },
      layers: [
        /* 카드1 "매매법 자체의 문제가 아닙니다" (자막 17~18) → 카드2로 교체(⑨) */
        { type: 'cmgText', y: 500, size: 96, text: '매매법 자체의 문제가 아닙니다', in: [0.3, 0.35], out: [4.0, 0.4] },
        /* 카드2 손실의 진짜 이유 (자막 19~25) */
        { type: 'cmgText', y: 360, size: 108, text: '손실의 진짜 이유', in: [4.5, 0.35], out: [15.6, 0.4] },
        {
          type: 'cmgText', y: 560, size: 80, in: [5.8, 0.35], out: [15.6, 0.4],
          parts: [{ text: '명확한 ' }, { text: '진입 · 청산 기준', hl: true }, { text: ' 없이 운영' }],
        },
        {
          type: 'cmgText', y: 720, size: 72, in: [11.5, 0.35], out: [15.6, 0.4],
          parts: [{ text: '기준', hl: true }, { text: '에 따라 결과는 완전히 달라진다' }],
        },
        /* 카드3 오늘 알려드릴 것 (자막 26~32) — 항목은 예고 베이지 → 자기 큐에 본색 */
        { type: 'cmgText', y: 300, size: 104, text: '오늘 알려드릴 것', in: [16.1, 0.35] },
        { type: 'cmgText', y: 460, size: 84, text: '① 어떤 기준으로 매매하는가', align: 'left', x: 430, in: [16.7, 0.3], activeAt: 20.1 },
        { type: 'cmgText', y: 600, size: 84, text: '② 몇 분봉을 설정하는가', align: 'left', x: 430, in: [16.9, 0.3], activeAt: 21.9 },
        { type: 'cmgText', y: 740, size: 84, text: '③ 어떤 보조지표를 쓰는가', align: 'left', x: 430, in: [17.1, 0.3], activeAt: 23.2 },
        {
          type: 'cmgText', y: 862, size: 88, in: [25.5, 0.4],
          parts: [{ text: '이동평균선 + RSI ', hl: true }, { text: '눌림목 매매 전략' }],
        },
      ],
    },

    /* ── 브리지2: 스윙이 아니라 초단타·스캘핑 (19.0000s · 프레임 2939 배치) ──
       [획일화 방지] 브리지1(워시 차트+리스트)과 문법을 다르게 — 종이 배경(12/12 회차
       공통 브랜드 상수) + 매수/익절 버튼 반복(짧은 반복 거래의 직관화). 버튼·종이는
       brand/thumbnail/ 의 템플릿 원본 픽셀. */
    {
      id: 'bridge-scalp',
      name: '브리지2 매매 성격 (19.0000s)',
      duration: 19.0,
      market: guideMarket, // 좌표 계산용 — 종이 배경이 덮어 차트는 보이지 않는다
      chart: {
        ...washBase,
        showCandles: false,
        ma: [],
        reveal: [{ t: 0, v: 55 }, { t: 19.0, v: 70, ease: 'linear' }],
      },
      layers: [
        { type: 'image', src: '/brand/thumbnail/종이배경.png', x: 0, y: -60, width: 1920, in: [0, 0] },
        /* 카드1 스윙 매매 ✗ (자막 54~55) */
        { type: 'cmgText', y: 430, size: 72, text: '며칠씩 포지션을 끌고 가는', in: [0.3, 0.3], out: [3.5, 0.4] },
        {
          type: 'cmgText', y: 590, size: 108, in: [0.8, 0.35], out: [3.5, 0.4],
          parts: [{ text: '스윙 매매' }, { text: '  ✗', color: '#D81028' }],
        },
        /* 카드2 짧은 시간 · 반복 거래 — 매수→익절 버튼 세 쌍이 연달아 찍힌다 (자막 56~59) */
        { type: 'cmgText', y: 330, size: 76, text: '짧은 시간 · 반복 거래', in: [3.9, 0.35], out: [11.3, 0.4] },
        { type: 'image', src: '/brand/thumbnail/btn_매수.png', x: 274, y: 455, width: 189, in: [4.4, 0.2], out: [11.3, 0.4] },
        { type: 'image', src: '/brand/thumbnail/btn_익절.png', x: 493, y: 455, width: 185, in: [4.7, 0.2], out: [11.3, 0.4] },
        { type: 'image', src: '/brand/thumbnail/btn_매수.png', x: 758, y: 455, width: 189, in: [5.2, 0.2], out: [11.3, 0.4] },
        { type: 'image', src: '/brand/thumbnail/btn_익절.png', x: 977, y: 455, width: 185, in: [5.5, 0.2], out: [11.3, 0.4] },
        { type: 'image', src: '/brand/thumbnail/btn_매수.png', x: 1242, y: 455, width: 189, in: [6.0, 0.2], out: [11.3, 0.4] },
        { type: 'image', src: '/brand/thumbnail/btn_익절.png', x: 1461, y: 455, width: 185, in: [6.3, 0.2], out: [11.3, 0.4] },
        {
          type: 'cmgText', y: 700, size: 96, in: [7.0, 0.35], out: [11.3, 0.4],
          parts: [{ text: '1분봉', hl: true }, { text: '  또는  ' }, { text: '5분봉', hl: true }],
        },
        { type: 'cmgText', y: 840, size: 100, text: '초단타 · 스캘핑', in: [9.2, 0.35], out: [11.3, 0.4] },
        /* 카드3 기계적 진입·청산 (자막 60~63) */
        { type: 'cmgText', y: 400, size: 72, text: '한 번에 큰 수익을 노리기보다', in: [11.5, 0.3] },
        {
          type: 'cmgText', y: 560, size: 92, in: [13.4, 0.35],
          parts: [{ text: '짧고 ' }, { text: '확실한 지점만', hl: true }],
        },
        {
          type: 'cmgText', y: 725, size: 92, in: [15.4, 0.35],
          parts: [{ text: '기계적으로 ' }, { text: '진입 · 청산', hl: true }],
        },
      ],
    },
  ],
};
