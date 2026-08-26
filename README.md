# 차트 컷씬 렌더러

해외선물 유튜브 영상에 쓸 **차트 모션그래픽 소스 영상**을 만드는 도구입니다.
캔들차트를 코드로 그리고, 프레임 단위로 캡처해서 편집 프로그램에 바로 얹을 수 있는
영상 파일로 뽑습니다.

- 1920×1080 / 60fps (기본값, 설정에서 변경 가능)
- 실시세를 받아오지 않고 **시나리오대로 캔들을 생성** → 어떤 기법이든 원하는 모양으로 연출
- `seed` 를 고정하므로 몇 번을 렌더해도 캔들이 똑같이 나옴 → 컷을 나눠 뽑아도 앞뒤가 안 어긋남
- 알파 채널(투명 배경) 출력 지원 → 실제 촬영본 위에 차트만 오버레이 가능

---

## 빠른 시작

```bash
npm install
npm run setup:fonts       # 리눅스만. Pretendard / JetBrains Mono 등록
npm run render            # 씬 목록 보기
npm run render -- --all   # 전 컷 렌더 (out/ 에 저장)
```

## 자주 쓰는 명령

| 하고 싶은 것 | 명령 |
|---|---|
| 씬 목록 확인 | `npm run render` |
| 전체 렌더 (mp4) | `npm run render -- --all` |
| 특정 컷만 | `npm run render -- --scene 04-entry` |
| 여러 컷 | `npm run render -- --scene 04-entry,05-tpsl` |
| 전 컷 + 이어 붙인 릴 | `npm run render -- --all --reel` |
| 편집용 ProRes | `npm run render -- --all --format mov` |
| 투명 배경 오버레이 | `npm run render -- --scene 05-tpsl --format alpha` |
| PNG 시퀀스 | `npm run render -- --scene 06-result --format png` |
| 구도만 빠르게 확인 | `npm run render -- --all --stills 5` |
| 쇼츠 비율로 | `npm run render -- --all --width 1080 --height 1920` |

### 출력 포맷

| `--format` | 파일 | 용도 |
|---|---|---|
| `mp4` (기본) | H.264 CRF 12 | 유튜브 업로드 / 일반 편집 |
| `mov` | ProRes 422 HQ | 프리미어·파컷에서 가볍게 스크럽 |
| `alpha` | QuickTime RLE (무손실 알파) | 차트만 오려서 오버레이 |
| `webm` | VP9 알파 | 웹용 |
| `png` | PNG 시퀀스 | 애프터이펙트 반입 |

투명 배경으로 뽑으려면 씬(또는 프로젝트) `theme` 에 `transparent: true` 를 넣고
`--format alpha` 로 렌더합니다. `scenes/nq-overlay.scenes.js` 가 그렇게 잡혀 있습니다.

```bash
npm run render -- --config scenes/nq-overlay.scenes.js --all --format alpha
```

`alpha`(QuickTime RLE)는 무손실이라 용량이 큽니다 — 1080p 60fps 5초에 20~40MB.
편집에는 이쪽이 좋고, 파일을 주고받아야 할 때만 `--format webm`(VP9 알파, 1/10 크기)을 쓰세요.
참고로 ProRes 4444 는 같은 클립이 150MB 넘게 나와서 알파 용도로는 오히려 손해입니다.

---

## 기본 세트 — `scenes/nq-basic.scenes.js`

나스닥 100 선물(NQ) 5분봉 한 편을 6컷으로 나눈 것입니다. 순서대로 붙이면 그대로 한 편이 됩니다.

| 컷 | 길이 | 내용 |
|---|---|---|
| `01-open` | 7.0s | 캔들이 그려지며 타이틀 등장 |
| `02-structure` | 7.5s | 지지·저항선과 박스권 표시 |
| `03-breakdown` | 7.0s | 하단 이탈 → 가짜 이탈(스탑 헌팅) |
| `04-entry` | 7.0s | 되돌림 롱 진입 마커 |
| `05-tpsl` | 7.5s | 손절·익절 박스와 손익비 1:2 |
| `06-result` | 9.0s | 익절 도달 + 손익 카운터 + 결과 카드 |

---

## 대본에 맞춰 고치기

컷 내용은 전부 `scenes/*.scenes.js` 한 파일에 선언형으로 들어 있습니다.
시간 단위는 초이고, `in: [시작, 등장시간]` / `out: [시작, 퇴장시간]` 입니다.

```js
{
  id: '04-entry',
  name: '진입 — 되돌림 롱',
  duration: 7,
  chart: {
    visibleBars: 56,
    reveal: [{ t: 0, v: 68 }, { t: 3.2, v: 70, ease: 'inOutCubic' }],
  },
  layers: [
    { type: 'marker', bar: 68, dir: 'long', label: '롱 진입  24,688.75', in: [1.5, 0.5] },
    { type: 'caption', title: '진입 근거', text: '...', in: [2.4, 0.6], out: [6.2, 0.4] },
  ],
}
```

### 차트 움직임 (`chart`)

| 키 | 뜻 |
|---|---|
| `reveal` | 몇 번째 캔들까지 그릴지. 키프레임을 주면 캔들이 그려지는 애니메이션이 된다 |
| `zoom` | 화면에 보이는 캔들 개수 배율 |
| `priceOffset` | 세로 방향 이동 |
| `visibleBars` | 한 화면에 보이는 캔들 수 |
| `include` | 화면에 반드시 들어와야 하는 가격 목록 (손절선·익절선 등) |
| `layout.rightGap` | 마지막 캔들 오른쪽으로 비워 둘 칸 수 |
| `ma` | 이동평균선 `[{ type:'ema', period:20, color, width }]` |

### 레이어 종류 (`layers`)

| `type` | 쓰임 |
|---|---|
| `titleCard` | 전체 화면 타이틀 (인트로 / 챕터 전환) |
| `caption` | 하단 자막 · 로어서드 |
| `hud` | 좌상단 종목 / 현재가 / 등락 |
| `hline` | 수평 가격선 + 라벨 (지지·저항·진입가) |
| `zone` | 가격 밴드 (박스권·매물대) |
| `marker` | 진입 화살표 + 펄스 |
| `tradeBox` | 손절·익절 박스와 손익비 |
| `counter` | 숫자 카운트업 패널 (수익금·포인트) |
| `statCard` | 결과 요약 카드 |
| `label` | 캔들에 붙는 지시선 라벨 |
| `flash` | 컷 전환용 플래시 |
| `letterbox` | 시네마 레터박스 |
| `watermark` | 채널명 |

### 캔들 시나리오 (`market.segments`)

| `type` | 모양 |
|---|---|
| `trend` | 한 방향 추세 |
| `range` | 박스권 (중심선으로 되돌아옴) |
| `breakout` | 눌림 뒤 강한 이탈 |
| `pullback` | 추세 중 되돌림 |
| `spike` | 지표 발표식 급등락 |

`seed` 숫자만 바꾸면 같은 구조의 다른 캔들이 나옵니다.

### 상승/하락 색

기본은 해외 플랫폼 표준(상승 초록 / 하락 빨강)입니다.
국내식으로 바꾸려면 프로젝트 또는 씬의 `theme` 에:

```js
theme: { candleScheme: 'korea' }   // 상승 빨강 / 하락 파랑
```

---

## 구조

```
scenes/                컷 정의 (대본이 바뀌면 여기만 수정)
src/
  cli.mjs              렌더 CLI
  market/candles.js    캔들 생성기
  render/
    scene.html         렌더 스테이지
    engine.js          씬 런타임 (프레임 단위 렌더)
    chart.js           캔들차트 캔버스 드로잉
    layers.js          오버레이 레이어
    theme.js           색 / 폰트
    capture.mjs        Playwright 프레임 캡처
    encode.mjs         ffmpeg 인코딩
    server.mjs         렌더용 정적 서버
  tools/install-fonts.mjs
out/                   렌더 결과 (git 추적 안 함)
```

렌더는 실시간 재생이 아니라 프레임 번호를 넣고 그리는 방식이라,
컴퓨터가 느려도 결과 영상의 fps 는 정확합니다.
