# HyperFrames 합성 (HTML → 영상)

`heygen-com/hyperframes` (Apache 2.0, 전부 로컬, 크레딧 안 씀). HTML+CSS+GSAP 를 결정론적으로 렌더한다.
쓰는 이유와 실측은 `log/inbox/2026-09-18_D_외부도구_HyperFrames·Remotion_실측.md` 와 A/B 보고서에 있다.

## 준비 (이 PC 에는 PATH 에 ffmpeg 가 없다)

```bash
npm i ffmpeg-static ffprobe-static            # 그 폴더에만
npx hyperframes browser ensure                # Chrome 을 ~/.cache 에 받는다
export PATH="$PWD/node_modules/ffmpeg-static:$PWD/node_modules/ffprobe-static/bin/win32/x64:$PATH"
export HYPERFRAMES_NO_TELEMETRY=1             # 익명 통계 끈다
npx hyperframes render -o renders/out.mp4
```

## 들어 있는 것

| 폴더 | 무엇 |
|---|---|
| `ab_pnl/` | A/B 시험용 — `scenes/nq-overlay.scenes.js` 의 `ov-pnl` 컷을 HTML 로 옮긴 것. 우리 렌더러와 비교했다(6.9초 대 31.0초, 다른 픽셀 1% 이내) |
| `mt5_frame/` | MT5 화면을 병풍 틀에 넣고 배지·강조·로고를 얹은 첫 시험 (표시는 눈대중) |
| `mt5_calib/` | 같은 것을 **계산한 자리**에 얹은 판. `calib.json` 의 격자·가격축 식으로 좌표를 구한다 (RMS 1.93px) |

`assets/` 는 올리지 않았다 — MT5 캡처와 납품 틀·로고라 그때그때 만든다.
`mt5_calib/index.html` 은 `tools/mt5/` 로 찍은 그림과 `calib.json` 이 있어야 그대로 렌더된다.

## 규격 (실측)

- `-f 60000/1001` 유리수 fps 그대로 나온다 (우리 롱폼 규격).
- `--format mov` = 알파 있는 ProRes 4444(`yuva444p10le`), `--format png-sequence` = RGBA PNG.
- **색을 보증해야 하면 PNG 시퀀스로 뽑는다.** ProRes 는 YUV 라 `#0D9488` 이 (12,148,135) 로 1 어긋난다.
- 틀 `01_납품_차트명가NEW/틀만_완성/B_병풍_틀만.png` 뚫린 자리 x81~1839 · y81~999, 여백색 #F3EEE3.
