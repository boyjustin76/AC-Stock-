/**
 * 차트명가 #12 — 본론1(대중의 활용법) + 문제제시 5컷 (컷11~15)
 *
 * 자막 원본: 차명12롱폼 음성자막-한국어.srt (30.0 격자 반올림)
 *   [정확.srt 재동기 2026-08-31]
 *   컷11 fail-common 144.267~161.733 (17.4667s)  72~80 크로스 신호로만 인식, RSI 70/30 역추세
 *   컷12 fail-combo  161.733~171.100 ( 9.3667s)  81~86 "교차 + RSI 30 = 매수" 조합을 정답처럼
 *   컷13 fail-chop   173.100~200.767 (27.6667s)  87~102 횡보 구간 — 이평선 교차 반복, 가짜 신호
 *   컷14 fail-blind  200.767~230.000 (29.2333s)  103~117 강한 추세 — RSI 70 위 유지, 역추세 매도?
 *   컷15 fail-loss   230.000~253.167 (23.1667s)  118~129 고점 갱신에 밀려 큰 손실 + 정리
 *
 * 씬마다 시장이 다르다 (per-scene market override — engine 이 project.market 에 병합):
 *   컷11·12  seed 2   파동 (골든 39·데드 48·골든2 66, RSI 19~82) — 실측 find-events
 *   컷13     seed 96  횡보 (10일/34일선 교차 10회 @37,43,44,50,52,65,66,68,69,79 · 박스 15393~15498)
 *   컷14·15  seed 25  강추세 (RSI 70 돌파 bar35 → 45봉 유지, 이후 +4.2%)
 * 색 실측: scenes/cmg12-guide.scenes.js 머리말 참고.
 */

import { COLOR } from './cmg12-guide.scenes.js';

const FPS = 60000 / 1001;

const chartBase = {
  visibleBars: 46,
  pricePad: 0.16,
  showGrid: false,
  showAxes: false,
  showLast: false,
  layout: { padLeft: 0, padRight: 0, padTop: 216, padBottom: 162, rightGap: 0 },
  ma: [
    { type: 'sma', period: 10, width: 5, color: COLOR.ma10 },
    { type: 'sma', period: 34, width: 5, color: COLOR.ma34 },
  ],
  /* 이 챕터는 대중의 70/30 이야기 — 55/45 기준선은 아직 없다 */
  rsi: { period: 10, height: 0.26, gap: 26, baseline: 50, levels: [], color: COLOR.rsi, width: 5 },
};

const waveMarket = {
  seed: 2,
  base: 15600,
  tick: 0.25,
  vol: 34,
  barMinutes: 1,
  startTime: Date.UTC(2026, 0, 8, 9, 0),
  segments: [
    { type: 'trend', dir: -1, bars: 20, strength: 1.0 },
    { type: 'trend', dir: 1, bars: 18, strength: 1.1 },
    { type: 'trend', dir: -1, bars: 18, strength: 1.15 },
    { type: 'trend', dir: 1, bars: 22, strength: 1.0 },
  ],
};

export default {
  title: '차트명가 #12 — 본론1·문제제시 5컷',
  width: 1920,
  height: 1080,
  fps: FPS,
  fpsExpr: '60000/1001',
  theme: { preset: 'chartmyeongga' },
  market: waveMarket,

  scenes: [
    /* ── 컷11 대중의 활용법 — 크로스 신호 + RSI 70/30 역추세 (16.8333s) ── */
    {
      id: 'fail-common',
      name: '컷11 대중의 지표 활용 (16.8333s)',
      duration: 17.466667,
      chart: {
        ...chartBase,
        reveal: [{ t: 0, v: 69 }, { t: 17.466667, v: 73, ease: 'linear' }],
      },
      layers: [
        /* 크로스를 추세 반전 신호로만 — 데드(48)·골든(66) 원 */
        { type: 'cmgCircle', bar: 48, price: 15393.7, rx: 80, ry: 66, width: 11, drawDur: 0.5, in: [1.2, 0.2] },
        { type: 'cmgCircle', bar: 66, price: 15375.1, rx: 80, ry: 66, width: 11, drawDur: 0.5, in: [2.4, 0.2] },
        { type: 'cmgNote', text: '교차 = 반전 신호?', bar: 58, price: 15512, size: 50, color: '#111111', in: [3.5, 0.3] },
        /* RSI 70 이상 = 과매수 → 매도 (70선 빨강 + 밴드 — 차12#1 실측 스타일) */
        { type: 'rsiLevel', v: 70, label: '70선', color: '#FE0000', width: 4, growDur: 0.5, in: [7.0, 0.2] },
        { type: 'rsiZone', from: 70, to: 100, color: '#FE0000', opacity: 0.18, in: [7.5, 0.3] },
        { type: 'cmgArrow', bar: 68, price: 15504.8, dir: 'sell', label: '매도', size: 34, gap: 16, in: [9.5, 0.35] },
        /* RSI 30 이하 = 과매도 → 매수 (30선 파랑 + 밴드) */
        { type: 'rsiLevel', v: 30, label: '30선', color: '#002EFE', width: 4, growDur: 0.5, in: [12.0, 0.2] },
        { type: 'rsiZone', from: 0, to: 30, color: '#002EFE', opacity: 0.16, in: [12.5, 0.3] },
        { type: 'cmgCircle', bar: 46, rsi: 28.2, rx: 58, ry: 46, width: 9, color: '#002EFE', drawDur: 0.5, in: [13.2, 0.2] },
        { type: 'cmgArrow', bar: 46, price: 15310.5, dir: 'buy', label: '매수', size: 34, gap: 16, in: [14.4, 0.35] },
      ],
    },

    /* ── 컷12 "교차하면서 동시에 RSI 30 밑이면 매수한다" (8.8333s) ── */
    {
      id: 'fail-combo',
      name: '컷12 보편적인 조합 (8.8333s)',
      duration: 9.366667,
      chart: {
        ...chartBase,
        /* [룰북 ⑬] 원래 reveal 56에서 뚝 시작하는 되감기 점프컷+줌이었다(인트로 컷4와
           같은 문법 — 반려됨). 컷11 끝(73)에서 이어받아 컷 안에서 조합 자리(46~48)로
           부드럽게 팬백+줌인한다. 57 밖 요소들은 팬백에 실려 자연 퇴장(⑩) */
        reveal: [
          { t: 0, v: 73 },
          { t: 2.0, v: 56, ease: 'inOutCubic' },
          { t: 9.366667, v: 57.5, ease: 'linear' },
        ],
        zoom: [
          { t: 0, v: 1.0 },
          { t: 2.0, v: 1.28, ease: 'inOutCubic' },
        ],
      },
      layers: [
        /* 컷11 끝 화면 전부 이월(⑧) — 지우는 건 없고, 팬백이 오른쪽 요소를 내보낸다.
           '교차 = 반전 신호?'(58)·매도(68)·원(66)은 reveal<58 이 되면 프레임 밖 */
        { type: 'rsiLevel', v: 70, label: '70선', color: '#FE0000', width: 4, growDur: 0, labelDelay: -1 },
        { type: 'rsiLevel', v: 30, label: '30선', color: '#002EFE', width: 4, growDur: 0, labelDelay: -1 },
        { type: 'rsiZone', from: 70, to: 100, color: '#FE0000', opacity: 0.18, in: [0, 0] },
        { type: 'rsiZone', from: 0, to: 30, color: '#002EFE', opacity: 0.16, in: [0, 0] },
        { type: 'cmgCircle', bar: 48, price: 15393.7, rx: 80, ry: 66, width: 11, drawDur: 0, in: [0, 0] },
        { type: 'cmgCircle', bar: 66, price: 15375.1, rx: 80, ry: 66, width: 11, drawDur: 0, in: [0, 0] },
        /*  [2026-09-01 반려] 앵커(58봉)는 팬백으로 화면 밖이 되지만 글자 폭(~450px)의
            왼쪽 절반이 오른쪽 가장자리에 걸려 남는다 — '교차 + RSI 30 = 매수?'(4.8)와
            겹침. 퇴장 판정은 앵커가 아니라 폭까지 봐야 한다(⑩ 보충). 팬백에 실어 페이드.  */
        { type: 'cmgNote', text: '교차 = 반전 신호?', bar: 58, price: 15512, size: 50, color: '#111111', in: [0, 0], out: [1.6, 0.4] },
        { type: 'cmgArrow', bar: 68, price: 15504.8, dir: 'sell', label: '매도', size: 34, gap: 16, popDur: 0 },
        /* 이월 RSI 원(46)은 조합의 새 원(47, 3.0)과 같은 역할·거의 같은 자리 — 교체(⑨) */
        { type: 'cmgCircle', bar: 46, rsi: 28.2, rx: 58, ry: 46, width: 9, color: '#002EFE', drawDur: 0, in: [0, 0], out: [2.8, 0.4] },
        /* 이월 매수(46, RSI30 단독)는 조합 매수(48)가 역할을 이어받으며 교체(⑨) */
        { type: 'cmgArrow', bar: 46, price: 15310.5, dir: 'buy', label: '매수', size: 34, gap: 16, popDur: 0, out: [5.5, 0.4] },
        /* 여기부터 컷12의 새 요소 — 조합의 RSI 쪽 원만 새로 그린다(48 원은 이월분 재사용) */
        { type: 'cmgCircle', bar: 47, rsi: 29, rx: 66, ry: 50, width: 9, color: '#002EFE', drawDur: 0.5, in: [3.0, 0.2] },
        { type: 'cmgNote', text: '교차 + RSI 30 = 매수?', bar: 51, price: 15505, size: 52, color: '#111111', in: [4.8, 0.3] }, // rightGap 0 — 55봉이면 오른쪽 넘침
        { type: 'cmgArrow', bar: 48, price: 15297.8, dir: 'buy', label: '매수', size: 34, gap: 16, in: [5.7, 0.35] },
        { type: 'cmgUnderline', bar: 51, price: 15505, dy: 48, width: 470, align: 'center', color: '#E90054', drawDur: 0.35, in: [7.0, 0.15] },
      ],
    },

    /* ── 컷13 첫째 한계 — 횡보 구간의 가짜 신호 (26.0000s) ── */
    {
      id: 'fail-chop',
      name: '컷13 횡보 가짜 신호 (26.0000s)',
      duration: 27.666667,
      market: {
        seed: 96,
        base: 15450,
        tick: 0.25,
        vol: 26,
        barMinutes: 1,
        startTime: Date.UTC(2026, 0, 9, 9, 0),
        segments: [
          { type: 'range', bars: 30, width: 0.9 },
          { type: 'range', bars: 30, width: 1.1 },
          { type: 'range', bars: 25, width: 0.9 },
        ],
      },
      chart: {
        ...chartBase,
        rsi: undefined, // 이 컷은 이평선 이야기 — 패널 없이 풀높이
        include: [15535, 15350], // 박스 검은 선과 라벨이 화면 끝에 붙지 않게
        ma: [
          { ...chartBase.ma[0], alpha: [{ t: 0, v: 0 }, { t: 13.9, v: 0 }, { t: 14.5, v: 1 }] },
          { ...chartBase.ma[1], alpha: [{ t: 0, v: 0 }, { t: 14.2, v: 0 }, { t: 14.8, v: 1 }] },
        ],
        reveal: [
          { t: 0, v: 40 },
          { t: 27.666667, v: 80, ease: 'linear' },
        ],
      },
      layers: [
        /* 차트를 보면 — 횡보 박스 (검은 선, 팀장 규칙 ②) */
        { type: 'cmgLevel', price: 15497, fromBar: 30, color: '#111111', thickness: 5, growDur: 0.5, in: [11.3, 0.2] },
        { type: 'cmgLevel', price: 15394, fromBar: 30, color: '#111111', thickness: 5, growDur: 0.5, in: [11.8, 0.2] },
        { type: 'cmgNote', text: '횡보 구간', bar: 45, price: 15525, size: 52, color: '#111111', in: [12.5, 0.3] },
        /* 이평선을 켜 보면(13.5) — 교차마다 빨간 원 연타 (차12#1 실측 스타일) */
        { type: 'cmgCircle', bar: 37, price: 15452, rx: 46, ry: 40, width: 9, color: '#E90054', drawDur: 0.4, in: [15.5, 0.15] },
        { type: 'cmgCircle', bar: 43, price: 15452, rx: 46, ry: 40, width: 9, color: '#E90054', drawDur: 0.4, in: [16.1, 0.15] },
        { type: 'cmgCircle', bar: 50, price: 15450, rx: 46, ry: 40, width: 9, color: '#E90054', drawDur: 0.4, in: [16.7, 0.15] },
        { type: 'cmgCircle', bar: 52, price: 15451, rx: 46, ry: 40, width: 9, color: '#E90054', drawDur: 0.4, in: [17.3, 0.15] },
        { type: 'cmgCircle', bar: 65, price: 15454, rx: 46, ry: 40, width: 9, color: '#E90054', drawDur: 0.4, in: [19.0, 0.15] },
        { type: 'cmgCircle', bar: 68, price: 15456, rx: 46, ry: 40, width: 9, color: '#E90054', drawDur: 0.4, in: [19.9, 0.15] },
        { type: 'cmgCircle', bar: 72, price: 15458, rx: 46, ry: 40, width: 9, color: '#E90054', drawDur: 0.4, in: [22.8, 0.15] },
        { type: 'cmgNote', text: '전부 가짜 신호', bar: 55, price: 15355, size: 54, color: '#E90054', in: [20.6, 0.3] },
        /* 잦은 손절을 피할 수 없다 */
        { type: 'cmgArrow', bar: 44, price: 15404, dir: 'sell', label: '손절', color: '#9F0000', size: 26, gap: 12, in: [23.4, 0.3] },
        { type: 'cmgArrow', bar: 53, price: 15412, dir: 'sell', label: '손절', color: '#9F0000', size: 26, gap: 12, in: [24.0, 0.3] },
        { type: 'cmgArrow', bar: 69, price: 15420, dir: 'sell', label: '손절', color: '#9F0000', size: 26, gap: 12, in: [24.6, 0.3] },
        { type: 'cmgCross', in: [25.8, 0.2] },
      ],
    },

    /* ── 컷14 둘째 한계 — 강한 추세에서 RSI 는 70 위에 머문다 (29.5667s) ── */
    {
      id: 'fail-blind',
      name: '컷14 RSI 70 맹신 (29.5667s)',
      duration: 29.233333,
      market: {
        seed: 25,
        base: 15200,
        tick: 0.25,
        vol: 30,
        barMinutes: 1,
        startTime: Date.UTC(2026, 0, 7, 9, 0),
        segments: [
          { type: 'trend', dir: 1, bars: 26, strength: 0.45 },
          { type: 'trend', dir: 1, bars: 26, strength: 1.35 },
          { type: 'trend', dir: 1, bars: 18, strength: 0.9 },
          { type: 'trend', dir: 1, bars: 10, strength: 0.6 },
        ],
      },
      chart: {
        ...chartBase,
        reveal: [
          /* [v3] 16초짜리 단일 inOutCubic 은 한참 느리다가 중반에 폭주한다 —
             완만히 출발해 등속으로. rsiTrace(toBar 64)가 13초대에 리빌을 따라잡는 건 유지 */
          { t: 0, v: 40 },
          { t: 2.5, v: 44, ease: 'inOutQuad' },
          { t: 13.0, v: 65, ease: 'linear' },
          { t: 16.0, v: 66, ease: 'linear' },
          { t: 29.233333, v: 74, ease: 'linear' },
        ],
      },
      layers: [
        /* 뚜렷한 상승 추세 */
        { type: 'cmgTrace', overlay: 0, fromBar: 38, toBar: 60, flatten: 0, width: 15, color: COLOR.ma10, in: [5.4, 0.6], out: [8.9, 0.35] },
        { type: 'cmgNote', text: '뚜렷한 상승 추세', bar: 44, price: 15560, size: 50, color: '#111111', in: [6.0, 0.3], out: [8.9, 0.35] },
        /* RSI 70 돌파 후 안 꺾이고 유지 */
        { type: 'rsiLevel', v: 70, label: '70선', color: '#FE0000', width: 4, growDur: 0.5, in: [8.6, 0.2] },
        { type: 'rsiZone', from: 70, to: 100, color: '#FE0000', opacity: 0.16, in: [9.3, 0.3] },
        { type: 'rsiTrace', fromBar: 36, toBar: 64, width: 11, color: '#FE0000', drawDur: 2.2, in: [10.8, 0.3] },
        { type: 'cmgNote', text: '70선 위에서 계속 버틴다', bar: 48, rsi: 30, size: 46, color: '#FE0000', in: [12.6, 0.3] },
        /* "과매수라며 매도를 잡았다면?" */
        { type: 'cmgArrow', bar: 36, price: 15408, dir: 'sell', label: '매도', size: 34, gap: 16, in: [22.5, 0.35] },
        { type: 'cmgLevel', price: 15417.8, fromBar: 36, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0.35, in: [23.1, 0.2] },
        { type: 'cmgNote', text: '과매수라서 매도?', bar: 43, price: 15295, size: 50, color: '#111111', in: [24.2, 0.3] },
      ],
    },

    /* ── 컷15 단 한 번의 진입으로 큰 손실 + 정리 (23.0667s) ── */
    {
      id: 'fail-loss',
      name: '컷15 역추세 손실과 정리 (23.0667s)',
      duration: 23.166667,
      market: {
        seed: 25,
        base: 15200,
        tick: 0.25,
        vol: 30,
        barMinutes: 1,
        startTime: Date.UTC(2026, 0, 7, 9, 0),
        segments: [
          { type: 'trend', dir: 1, bars: 26, strength: 0.45 },
          { type: 'trend', dir: 1, bars: 26, strength: 1.35 },
          { type: 'trend', dir: 1, bars: 18, strength: 0.9 },
          { type: 'trend', dir: 1, bars: 10, strength: 0.6 },
        ],
      },
      chart: {
        ...chartBase,
        reveal: [
          { t: 0, v: 74 },
          { t: 6.5, v: 79.9, ease: 'inOutCubic' },
          { t: 23.166667, v: 79.9 },
        ],
      },
      layers: [
        /* 컷14 끝 화면 전부 이어받기(⑧) — 존·궤적·문장도 지우지 않는다 */
        { type: 'cmgArrow', bar: 36, price: 15408, dir: 'sell', label: '매도', size: 34, gap: 16, popDur: 0 },
        { type: 'cmgLevel', price: 15417.8, fromBar: 36, color: 'rgba(0,0,0,0.72)', thickness: 4, growDur: 0, in: [0, 0] },
        { type: 'rsiLevel', v: 70, label: '70선', color: '#FE0000', width: 4, growDur: 0, labelDelay: -1 },
        { type: 'rsiZone', from: 70, to: 100, color: '#FE0000', opacity: 0.16, in: [0, 0] },
        { type: 'rsiTrace', fromBar: 36, toBar: 64, width: 11, color: '#FE0000', drawDur: 0, in: [0, 0] },
        { type: 'cmgNote', text: '70선 위에서 계속 버틴다', bar: 48, rsi: 30, size: 46, color: '#FE0000', in: [0, 0] },
        /* '과매수라서 매도?'는 '단 한 번에 큰 손실'(3.2)이 역할을 이어받으며 교체(⑨) */
        { type: 'cmgNote', text: '과매수라서 매도?', bar: 43, price: 15295, size: 50, color: '#111111', in: [0, 0], out: [2.9, 0.4] },
        /* 고점 갱신 상승에 밀린 손실 영역 — 진입가에서 위로 계속 자란다 */
        {
          type: 'cmgLevel',
          price: 16006,
          fromBar: 36,
          fillTo: 15417.8,
          fill: '#FEBABA',
          color: '#9F0000',
          thickness: 16,
          growDur: 1.2,
          in: [0.8, 0.3],
        },
        { type: 'cmgNote', text: '단 한 번에 큰 손실', bar: 49, price: 15750, size: 56, color: '#E90054', in: [3.2, 0.3], out: [8.2, 0.5] },
        { type: 'cmgUnderline', bar: 49, price: 15750, dy: 50, width: 440, align: 'center', drawDur: 0.35, in: [3.8, 0.15], out: [8.2, 0.5] },
        { type: 'cmgCross', in: [5.5, 0.2], out: [8.2, 0.5] },
        /* 정리 — 구조적 모순 두 줄 */
        { type: 'cmgNote', text: '횡보장 → 이평선의 가짜 신호', bar: 50, price: 16050, size: 48, color: '#111111', align: 'left', dx: -240, in: [8.0, 0.3] },
        { type: 'cmgNote', text: '추세장 → RSI 역추세 손실', bar: 50, price: 15960, size: 48, color: '#111111', align: 'left', dx: -240, in: [10.5, 0.3] },
        { type: 'cmgNote', text: '그럼 기준을 어떻게 다시 잡아야 할까?', bar: 58, price: 15600, size: 52, color: '#E90054', in: [17.3, 0.35] },
      ],
    },
  ],
};
