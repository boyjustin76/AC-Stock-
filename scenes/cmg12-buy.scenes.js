/**
 * 차트명가 #12 — 핵심 개념 + 매수 관점 5컷 (컷16~20) · 1분 차트
 *
 * 자막 원본: 차명12롱폼 음성자막-한국어.srt (30.0 격자 반올림)
 *   [정확.srt 재동기 2026-08-31]
 *   컷16 buy-core   255.167~265.433 (10.2667s)  130~134 핵심: 추세 필터 + 진짜 눌림목
 *   컷17 buy-array  265.433~280.667 (15.2333s)  135~142 1분 차트, 10일선이 34일선 위 — 배열
 *   컷18 buy-trend  280.667~293.533 (12.8667s)  143~150 정배열 = 상승 추세, 매수 관점만
 *   컷19 buy-entry  293.533~305.733 (12.2000s)  151~157 RSI 55 재돌파 + 양봉 → 다음 캔들 시가 매수
 *   컷20 buy-exit   305.733~319.600 (13.8667s)  158~166 손절·익절 1:2, 절반 분할 후 러너
 *
 * 시장 실측 (seed 161 · find-events):
 *   정배열 유지 bar 33~96 (s10 > s34 전 구간)
 *   눌림: RSI 87.8(41) → 40.7(48) → 54.2(51) → 55 상향돌파 bar 52 (60.5 · 양봉)
 *   진입 = 53번 시가 15553.25 · 손절 = 51번 저점 15515.50 (R=37.75) · 익절 1:2 = 15628.75
 *   1:2 도달 bar 59 (고가 15650.5) · 이후 러너 15983 까지 (+11.4R)
 * 컷 경계는 (reveal, zoom) 을 일치시켜 심리스로 잇는다 (숏폼 업그레이드).
 */

import { market, chartBase as guideBase, COLOR } from './cmg12-guide.scenes.js';

const FPS = 60000 / 1001;

const LV = {
  signal: 52,
  entry: 15553.25, // 53번 시가
  stop: 15515.5, // 51번 저점
  get target() { return this.entry + (this.entry - this.stop) * 2; }, // 15,628.75
};

const chartBase = {
  ...guideBase,
  rsi: {
    ...guideBase.rsi,
    /* 컷10에서 그어진 55/45선이 여기서부터 상시 기준선 */
    levels: [
      { v: 55, label: '55', color: 'rgba(17,17,17,0.62)', width: 2.5 },
      { v: 45, label: '45', color: 'rgba(17,17,17,0.62)', width: 2.5 },
    ],
  },
};

export default {
  title: '차트명가 #12 — 핵심·매수 관점 5컷',
  width: 1920,
  height: 1080,
  fps: FPS,
  fpsExpr: '60000/1001',
  theme: { preset: 'chartmyeongga' },
  market,

  scenes: [
    /* ── 컷16 핵심 — 추세 필터 + 진짜 눌림목 (10.3000s) ── */
    {
      id: 'buy-core',
      name: '컷16 매매법의 핵심 (10.3000s)',
      duration: 10.266667,
      chart: {
        ...chartBase,
        reveal: [{ t: 0, v: 54 }, { t: 10.266667, v: 56, ease: 'linear' }],
      },
      layers: [
        { type: 'cmgTrace', overlay: 0, fromBar: 34, toBar: 46, flatten: 0, width: 15, color: COLOR.ma10, in: [0.8, 0.5], out: [3.6, 0.35] },
        { type: 'cmgNote', text: '① 추세 먼저 필터', bar: 40, price: 15580, size: 50, color: COLOR.ma10, in: [1.3, 0.3], out: [3.6, 0.35] },
        { type: 'cmgCircle', bar: 48, rsi: 40.7, rx: 62, ry: 50, width: 10, color: '#E90054', drawDur: 0.5, in: [4.2, 0.2] },
        { type: 'cmgCircle', bar: 52, rsi: 60.5, rx: 58, ry: 48, width: 10, color: '#E90054', drawDur: 0.5, in: [5.3, 0.2] },
        { type: 'cmgNote', text: '② 진짜 눌림목만', bar: 41, rsi: 22, size: 48, color: '#E90054', in: [5.9, 0.3] },
      ],
    },

    /* ── 컷17 1분 차트 — 배열을 본다 (15.2000s) ── */
    {
      id: 'buy-array',
      name: '컷17 정배열 확인 (15.2000s)',
      duration: 15.233333,
      chart: {
        ...chartBase,
        reveal: [{ t: 0, v: 56 }, { t: 15.233333, v: 60, ease: 'linear' }],
      },
      layers: [
        /* 컷16 끝 화면 이월(⑧) — RSI 원 두 개와 '② 진짜 눌림목만'은 컷 내내 유지
           (아래 패널이라 배열 이야기와 안 부딪힌다). 컷18이 다시 이어받는다 */
        { type: 'cmgCircle', bar: 48, rsi: 40.7, rx: 62, ry: 50, width: 10, color: '#E90054', drawDur: 0, in: [0, 0] },
        { type: 'cmgCircle', bar: 52, rsi: 60.5, rx: 58, ry: 48, width: 10, color: '#E90054', drawDur: 0, in: [0, 0] },
        { type: 'cmgNote', text: '② 진짜 눌림목만', bar: 41, rsi: 22, size: 48, color: '#E90054', in: [0, 0] },
        { type: 'cmgBadge', text: '1분 차트', x: 84, y: 262, size: 42, color: COLOR.badge, in: [2.5, 0.3] },
        { type: 'cmgNote', text: '10일선', bar: 50, price: 15588, size: 46, color: COLOR.ma10, in: [4.4, 0.3] },
        { type: 'cmgNote', text: '34일선', bar: 50, price: 15468, size: 46, color: COLOR.ma34, in: [5.4, 0.3] },
        { type: 'cmgNote', text: '크로스가 아니라 배열', bar: 40, price: 15601, size: 52, color: '#111111', in: [8.3, 0.3] },
        { type: 'cmgUnderline', bar: 40, price: 15601, dy: 48, width: 470, align: 'center', drawDur: 0.35, in: [9.0, 0.15] },
      ],
    },

    /* ── 컷18 정배열 = 상승 추세 → 매수 관점만 (12.8667s) ── */
    {
      id: 'buy-trend',
      name: '컷18 매수 관점 고정 (12.8667s)',
      duration: 12.866667,
      chart: {
        ...chartBase,
        reveal: [{ t: 0, v: 60 }, { t: 12.866667, v: 61, ease: 'linear' }],
      },
      layers: [
        /* 컷17 끝 화면 이월(⑧). 이름표는 '정배열'(2.6)이, '크로스가 아니라 배열'은
           '상승 추세 →'(5.9)가, '②'는 '눌림목 타점은 RSI'(10.2, 같은 자리)가
           역할을 이어받을 때 크로스페이드(⑨) */
        { type: 'cmgBadge', text: '1분 차트', x: 84, y: 262, size: 42, color: COLOR.badge, popDur: 0 },
        { type: 'cmgCircle', bar: 48, rsi: 40.7, rx: 62, ry: 50, width: 10, color: '#E90054', drawDur: 0, in: [0, 0] },
        { type: 'cmgCircle', bar: 52, rsi: 60.5, rx: 58, ry: 48, width: 10, color: '#E90054', drawDur: 0, in: [0, 0] },
        { type: 'cmgNote', text: '② 진짜 눌림목만', bar: 41, rsi: 22, size: 48, color: '#E90054', in: [0, 0], out: [10.0, 0.4] },
        { type: 'cmgNote', text: '10일선', bar: 50, price: 15588, size: 46, color: COLOR.ma10, in: [0, 0], out: [2.4, 0.4] },
        { type: 'cmgNote', text: '34일선', bar: 50, price: 15468, size: 46, color: COLOR.ma34, in: [0, 0], out: [2.4, 0.4] },
        { type: 'cmgNote', text: '크로스가 아니라 배열', bar: 40, price: 15601, size: 52, color: '#111111', in: [0, 0], out: [5.7, 0.4] },
        { type: 'cmgUnderline', bar: 40, price: 15601, dy: 48, width: 470, align: 'center', drawDur: 0, in: [0, 0], out: [5.7, 0.4] },
        /* 10일선이 34일선보다 위 — 두 선을 접선 덧칠로 나란히 강조 */
        { type: 'cmgTrace', overlay: 0, fromBar: 44, toBar: 58, flatten: 0, width: 14, color: COLOR.ma10, in: [1.0, 0.5], out: [4.9, 0.35] },
        { type: 'cmgTrace', overlay: 1, fromBar: 44, toBar: 58, flatten: 0, width: 14, color: COLOR.ma34, in: [1.7, 0.5], out: [4.9, 0.35] },
        { type: 'cmgNote', text: '정배열', bar: 56, price: 15477, size: 52, color: '#111111', in: [2.6, 0.3] },
        { type: 'cmgNote', text: '상승 추세 → 매수 관점만', bar: 44, price: 15636, size: 52, color: '#E90054', in: [5.9, 0.3] },
        /* 방향이 정해졌으니 이제 타이밍 — RSI 로 눌림목 */
        { type: 'cmgCircle', bar: 50, rsi: 45.7, rx: 76, ry: 54, width: 10, color: COLOR.rsi, drawDur: 0.5, in: [9.4, 0.2] },
        { type: 'cmgNote', text: '눌림목 타점은 RSI', bar: 42, rsi: 22, size: 46, color: COLOR.rsi, stroke: '#083244', in: [10.2, 0.3] },
      ],
    },

    /* ── 컷19 신호 — 55선 재돌파 + 양봉 마감 → 매수 (12.2000s) ── */
    {
      id: 'buy-entry',
      name: '컷19 진입 신호 (12.2000s)',
      duration: 12.2,
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 61 },
          { t: 2.0, v: 57, ease: 'inOutCubic' }, // 신호 자리로 되감으며
          { t: 12.2, v: 58, ease: 'linear' },
        ],
        zoom: [
          { t: 0, v: 1 },
          { t: 2.0, v: 1.4, ease: 'inOutCubic' }, // 줌인 — 컷 안에서 전환 (콘티 금지)
        ],
      },
      layers: [
        /* 컷18 끝 화면 이월(⑧) — 원 두 개는 이미 그려져 있으니 다시 그리지 않는다.
           문장들은 팬백+줌인(0~2.0)에 실어 보내거나 '55선 재돌파'(4.6)로 교체(⑨⑩보충) */
        { type: 'cmgBadge', text: '1분 차트', x: 84, y: 262, size: 42, color: COLOR.badge, popDur: 0 },
        { type: 'cmgCircle', bar: 48, rsi: 40.7, rx: 60, ry: 48, width: 10, color: '#E90054', drawDur: 0, in: [0, 0] },
        { type: 'cmgCircle', bar: 52, rsi: 60.5, rx: 56, ry: 46, width: 10, color: '#E90054', drawDur: 0, in: [0, 0] },
        { type: 'cmgNote', text: '정배열', bar: 56, price: 15477, size: 52, color: '#111111', in: [0, 0], out: [1.8, 0.4] },
        /* 줌인 뒤 뷰포트 천장 위로 걸린다(probe 1.0초~) — 팬백 초반에 실어 보낸다(⑩보충) */
        { type: 'cmgNote', text: '상승 추세 → 매수 관점만', bar: 44, price: 15636, size: 52, color: '#E90054', in: [0, 0], out: [0.65, 0.35] },
        { type: 'cmgCircle', bar: 50, rsi: 45.7, rx: 76, ry: 54, width: 10, color: COLOR.rsi, drawDur: 0, in: [0, 0], out: [1.8, 0.4] },
        { type: 'cmgNote', text: '눌림목 타점은 RSI', bar: 42, rsi: 22, size: 46, color: COLOR.rsi, stroke: '#083244', in: [0, 0], out: [4.4, 0.4] },
        { type: 'cmgNote', text: '55선 재돌파', bar: 44, rsi: 70, size: 46, color: '#E90054', in: [4.6, 0.3] },
        /* 돌파 캔들이 양봉으로 마감 */
        { type: 'cmgCircle', bar: 52, price: 15543, rx: 44, ry: 62, width: 10, drawDur: 0.5, in: [6.2, 0.2], out: [9.6, 0.4] },
        /* 줌 컷은 뷰포트 상단이 낮다 — 절대가 대신 신호 캔들에서 픽셀로 띄운다 */
        { type: 'cmgNote', text: '양봉 마감', bar: 52, price: 15543, dy: -175, size: 48, color: '#111111', in: [6.9, 0.3], out: [9.6, 0.4] },
        /* 다음 캔들 시가에 매수 */
        { type: 'cmgArrow', bar: 53, price: 15546, dir: 'buy', label: '매수', size: 34, gap: 16, in: [10.0, 0.35] },
        { type: 'cmgNote', text: '다음 캔들 시가', bar: 57.5, price: 15505, size: 40, color: '#111111', align: 'right', in: [10.7, 0.3] }, // rightGap 0 — 중앙정렬이면 오른쪽 넘침
      ],
    },

    /* ── 컷20 손절·익절 1:2 색박스 → 분할 익절 → 러너 (13.8667s) ── */
    {
      id: 'buy-exit',
      name: '컷20 손익비와 러너 (13.8667s)',
      duration: 13.866667,
      chart: {
        ...chartBase,
        include: [LV.stop - 12],
        reveal: [
          { t: 0, v: 58 },
          { t: 3.0, v: 60, ease: 'linear' },
          { t: 9.0, v: 74, ease: 'inOutQuad' }, // [v3] cubic → quad, 중반 폭주 완화
          { t: 13.866667, v: 92, ease: 'inOutCubic' }, // 러너 — 추세 끝까지 (bar 90 익절 화살표가 12.9s 전에 드러나야 해서 cubic 유지)
        ],
        zoom: [
          { t: 0, v: 1.4 },
          { t: 6.6, v: 1.4 },
          { t: 9.2, v: 1.0, ease: 'inOutCubic' }, // 줌아웃하며 수익이 자란다
        ],
      },
      layers: [
        /* 컷19 끝 화면 이월(⑧) — 배지는 '손익비'(4.9)와 크로스페이드(⑨),
           '다음 캔들 시가'는 익절 박스(3.8)가 이야기를 이어받으며 교체,
           원·'55선 재돌파'는 카메라가 러너 구간으로 나아가며 자연 퇴장(⑩) */
        { type: 'cmgBadge', text: '1분 차트', x: 84, y: 262, size: 42, color: COLOR.badge, popDur: 0, out: [4.7, 0.4] },
        { type: 'cmgCircle', bar: 48, rsi: 40.7, rx: 60, ry: 48, width: 10, color: '#E90054', drawDur: 0, in: [0, 0] },
        { type: 'cmgCircle', bar: 52, rsi: 60.5, rx: 56, ry: 46, width: 10, color: '#E90054', drawDur: 0, in: [0, 0] },
        { type: 'cmgNote', text: '55선 재돌파', bar: 44, rsi: 70, size: 46, color: '#E90054', in: [0, 0] },
        { type: 'cmgNote', text: '다음 캔들 시가', bar: 57.5, price: 15505, size: 40, color: '#111111', align: 'right', in: [0, 0], out: [3.6, 0.4] },
        { type: 'cmgArrow', bar: 53, price: 15546, dir: 'buy', label: '매수', size: 34, gap: 16, popDur: 0, out: [9.5, 0.5] },
        /* 진입 얇은 검은 선 + 손절 갈색 박스 (선과 테두리 포개짐 — 팀장 규칙 ④) */
        { type: 'cmgLevel', price: LV.entry, fromBar: 51, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0.35, in: [0.4, 0.2] },
        {
          type: 'cmgLevel',
          price: LV.stop,
          fromBar: 51,
          fillTo: LV.entry,
          fill: '#FEBABA',
          color: '#9F0000',
          label: '손절',
          labelSize: 38,
          thickness: 13,
          growDur: 0.4,
          in: [0.6, 0.2],
        },
        /* 익절 초록 박스 — 1:2 가 한눈에 */
        {
          type: 'cmgLevel',
          price: LV.target,
          fromBar: 51,
          fillTo: LV.entry,
          fill: '#BAFDC0',
          color: '#14FF36',
          label: '익절',
          labelSize: 38,
          thickness: 13,
          growDur: 0.4,
          in: [3.8, 0.2],
        },
        { type: 'cmgBadge', text: '손익비  1 : 2', x: 84, y: 262, size: 44, color: '#E90054', in: [4.9, 0.3] },
        /* 절반 분할 익절 */
        { type: 'flash', at: 6.7, dur: 0.22, strength: 0.4, color: '#14FF36' },
        { type: 'cmgArrow', bar: 59, price: 15650.5, dir: 'sell', label: '익절 1/2', color: '#0DA82A', size: 32, gap: 16, in: [6.9, 0.35] },
        /* 남은 물량 — 추세 수익 극대화 (진입가 위로 수익 영역이 계속 자란다) */
        { type: 'cmgProfit', entry: LV.entry, fromBar: 53, color: '#BAFDC0', opacity: 0.3, in: [9.8, 0.4] },
        { type: 'cmgArrow', bar: 90, price: 15890.3, dir: 'sell', label: '익절', color: '#0DA82A', size: 32, gap: 16, in: [12.9, 0.3] },
      ],
    },
  ],
};
