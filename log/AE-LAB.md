# AE 실험 일지 — .aep / .mogrt 납품 가능성

> D 세션(로컬 PC)이 쓴다. 지시서는 `AELABMANUAL.md`(사용자 데스크톱), 근거는
> `lab/ae/AEP-MOGRT-조사보고.txt`. 옆가지 `local/ae-lab` 에만 올린다.
> 프리미어 실험 일지는 `log/PREMIERE-LAB.md`, 총괄 보고는 `log/PREMIERE-LAB-REPORT.md`.

---

## 2026-08-31 · A0 — 환경 실측과 준비

### 설치 상태

| | |
|---|---|
| After Effects | **없었다 → 이 세션 중 사용자가 설치**. `Adobe After Effects 2026`, AfterFX.exe **26.3** |
| Photoshop | 2026 (BridgeTalk 전송로 — 프리미어 M1~M6 에서 검증됨) |
| Premiere Pro | 2026 (26.3.2 = 타깃 `premierepro-26.0`) |
| Media Encoder | 2026 |

AE 는 26.3 이므로 BridgeTalk 타깃은 `aftereffects-26.0` **일 것으로 보이지만 박지 않았다** —
매뉴얼 §3-2 대로 `getSpecifier` 로 실측해서 쓴다(아래).

### 드라이버 — 프리미어 것을 베끼되 한 군데 고쳤다

```
tools/ae/run.ps1      tools/premiere/run.ps1 을 베낌. -Job <이름>
tools/ae/bridge.jsx   포토샵 안에서 돌며 BridgeTalk 으로 AE 에 전달
tools/ae/config.json  labDir C:/aelab · target "" (비우면 실측)
tools/ae/jobs/        a1_smoke.jsx …
```

프리미어와 다른 점 둘:

1. **타깃을 실측한다.** `config.target` 이 비어 있으면 `BridgeTalk.getSpecifier("aftereffects")`
   로 얻는다. 못 얻으면 `getTargets(null)` 전체 목록과 함께 `NO_TARGET` 으로 즉시 실패한다 —
   600초 타임아웃을 기다리지 않는다. 실측값은 `C:/aelab/_target.txt` 에 남는다.
2. **잡은 측정값을 반환값에도 싣는다.** AE 는 환경설정 "스크립트가 파일 쓰기 허용" 이 꺼져
   있으면 로그 파일이 **조용히** 안 생긴다(매뉴얼 §6 의 1순위 용의자). 파일에만 쓰면
   실패했을 때 아무 정보가 없다. 그래서 A1 은 같은 내용을 반환값으로도 보내고,
   **파일이 생겼는지 여부 자체를 환경설정 판정으로 쓴다.**

### 좌표는 자로 재지 않았다 — 렌더러의 매핑을 다시 계산했다

매뉴얼 A3 은 "좌표는 스틸 위에서 실측해라(자로 잰다)" 지만, 그 스틸을 만든 매핑을
그대로 다시 부르는 편이 정확하다. `tools/ae/anchors.mjs` 가 한다:

```
node tools/ae/anchors.mjs        →  C:/aelab/anchors.json
```

`lab/ae/cut2-base.scenes.js` 의 chart 설정은 `scenes/sl-11-4.scenes.js` 컷②와 **동일하다**
(visibleBars 32 · pricePad 0.14 · include 없음 · ema20 · 여백 0 · rightGap 6 · market seed 11 동일).
그래서 `reveal 63 · zoom 1` 로 `chart.makeScale()` 을 부르면 스틸 위 좌표가 그대로 나온다.

**이 전제를 증명했다.** 바닥 스틸을 이 PC 에서 다시 렌더해 저장소의 것과 대조했더니
**바이트 단위로 같았다** (md5 `51813b0f82110282a65e7c54588fef3d`). 같은 코드가 같은 그림을
내므로, 그 코드가 내는 좌표도 그 그림의 좌표다.

실측 좌표 (1080×1080, AE 는 좌상단 원점이라 그대로 쓴다):

| | x | | | 가격 | y |
|---|---|---|---|---|---|
| bar 42 (진입) | 168.75 | | | 진입 23,795 | 807.00 |
| bar 53 (익절) | 540.00 | | | 손절 23,665 | 961.50 |
| bar 57 (놓친구간 글자) | 675.00 | | | 익절 24,055 | 497.99 |
| bar 62 (놓친 고점) | 843.75 | | | 놓친고점 24,418.25 | 66.28 |
| 오른쪽 끝 | 1080 | | | 글자 자리 24,270 | 242.47 |

봉 폭 22.28px · 1px = 0.84 포인트 · 뷰포트 bar 37~69 / 23,565.3~24,474.0.

**자체 검증**: 1:2 손익비가 픽셀에서도 맞아야 한다.
손절폭 961.5−807 = **154.50px**, 익절폭 807−497.99 = **309.01px** → **1 : 2.0001**. 맞다.

### 씬에서 뽑은 그리기 규칙 (A3 이 그대로 옮길 것)

`src/render/layers.js` 실측. AE 셰이프로 옮길 때 이 수치를 쓴다.

- **cmgLevel(색박스)** — 채움 `fillRect(x0, min(y,y2), w, |y2−y|)` 에 **불투명도 0.55**,
  그 위에 선 `fillRect(x0, y−th/2, w, th)`, th=14. x0=bar42 의 x, w=(1080−x0)·grow.
  라벨은 **선 시작점 왼쪽에 딱 붙는 각진 박스**(모서리 둥글기 없음), 높이 = size×1.35,
  폭 = 글자폭 + 24×2, 글자는 흰색 외곽선 없음, 세로 중심에서 +2px.
  → 라벨 박스 폭은 **AE 에서 `sourceRectAtTime` 으로 재서** 맞춘다. 글자폭을 짐작하지 않는다.
- **cmgArrow(매수/익절 버튼)** — 브랜드 버튼 `brand/ui/매수 버튼(좌우).png` 실측 비율.
  촉 = 0.49·h, 모서리 r = 0.08·h, 글씨높이/버튼높이 = 0.761, (버튼폭−글씨폭)/높이 = 0.659.
  촉 끝 x = bar 의 x − gap(16). 경로는 7점(직선 5 + 꼬리쪽 2차 베지어 2) — AE Shape 로 그대로 옮긴다.
  그림자: 검정 18% · 블러 0.114·h · 3회 겹침.
- **cmgMissed(빗금)** — 사각형 `x0..1080`, `y(24055)..y(24418.25)` 를 색 10% 로 채우고
  그 위에 **42px 간격 · 굵기 6 · 색 28% 의 45° 사선**. 화살표는 이 컷에서 꺼져 있다(`arrow:false`).
- **cmgNote(글자)** — 700 굵기 58px, 가운데 정렬, 흰 글씨 + 검정 외곽선 굵기 size×0.16 = 9.28.
  등장할 때 18px 아래에서 올라온다.
- **cmgUnderline(밑줄)** — 폭 300, 굵기 12, 둥근 끝, 중심 정렬. 흔들림은
  `sin(p·7.3+1.1)·3.2 + sin(p·2.1)·2.4` — 파일럿에선 직선이어도 합격(매뉴얼 §5).
- **cmgBadge(손익비)** — x64 y1004, 46px, 색 #E90054, **테두리 없음**(`border:false`),
  둥글기 10, 높이 = 46×1.5 = 69, 좌우 여백 = 46×0.5 = 23, 글자는 흰색 + 검정 외곽선 6.9.

### 아직 못 한 것 (사람 대기)

- AE 를 **한 번도 실행한 적이 없다** — 환경설정 파일이 아직 안 생겼다.
  첫 실행 모달(홈 화면·로그인·업데이트)은 사람이 닫아야 한다(매뉴얼 §2-4).
- **환경설정 > 스크립팅 및 표현식 > "스크립트가 파일 쓰기 및 네트워크 액세스 허용"** 체크 필요(§2-2).

이 둘이 끝나면 A1 을 돌린다:

```
powershell -ExecutionPolicy Bypass -File tools\ae\run.ps1 -Job a1_smoke
```

---

## 2026-08-31 · A1 — 통신 스모크 · **통과**

```
powershell -ExecutionPolicy Bypass -File tools\ae\run.ps1 -Job a1_smoke
```

왕복 **0.3초**. 프리미어 M1 때와 같은 전송로가 AE 에도 그대로 통한다.

### 타깃 — 실측

```
getSpecifier("aftereffects")   aftereffects-26.0
getTargets(null)               photoshop-200.064 | premierepro-26.0 | ame-26.0 | aftereffects-26.0
```

짐작했던 `aftereffects-26.0` 이 맞았지만, **맞았다는 것도 실측으로 알았다.**
`config.json` 의 `target` 은 계속 비워 둔다 — 버전이 올라가도 알아서 따라간다.

### 측정값

| | |
|---|---|
| app.version / buildName | 26.3x87 |
| isoLanguage | **ko_KR** — 속성 이름이 한글이다. 프리미어에서 `비율 조정` 에 물린 것과 같은 함정이 온다 |
| ExtendScript | 4.5.6 |
| os | Windows/64 10.0 |
| `app.project.items.addComp` | function (있다) |
| `CompItem` | 있다 (mogrt API 의 그릇) |
| `app.exitAfterLaunchAndEval` | true |
| `beginSuppressDialogs` / `endSuppressDialogs` | 둘 다 호출됨 |

### 벽 하나 — 파일 쓰기 거부 (예상대로)

```
ReferenceError: 권한이 거부되었습니다.
[환경 설정] > [스크립팅 및 표현식] > [스크립트를 통한 파일 쓰기 및 네트워크 액세스 허용]
```

**이게 안 보일 뻔했다.** 매뉴얼 A1 은 "버전을 파일에 써라" 인데, 파일 쓰기 자체가 막히면
파일이 안 생기고 그러면 아무 정보도 안 남는다. 잡이 측정값을 **반환값에도** 실었기 때문에
로그 없이도 원인까지 왔다. 이 설계는 앞으로도 유지한다.

#### ⚠ 함정 — 0바이트 파일이 생긴다. "파일이 있다" 는 증거가 아니다

권한이 없어도 `f.open("w")` 은 **통과하고 빈 파일을 만든다.** 거부는 `f.write()` 에서 난다.

```
C:\aelab\log\a1.txt   0 bytes
```

그래서 `_lib.jsx` 의 `_write` 를 고쳤다 — 쓰고 나서 **길이가 0보다 큰지** 확인해야 성공이다.
프리미어에서 배운 "성공 반환값은 증거가 아니다" 의 AE 판이다.

#### ⚠ 함정 — pref 키로는 이 설정을 못 읽는다 (26.3)

```
app.preferences.getPrefAsLong("Main Pref Section v2", "Pref_SCRIPTING_FILE_NETWORK_SECURITY", ...)
  → After Effects 오류: 환경 설정에서 섹션 이름 및 키를 찾을 수 없습니다.
```

널리 도는 그 키가 26.3 엔 없다. **설정 여부는 실제로 한 번 써 보고 길이를 재는 것으로만 판정한다.**
그래서 A1 의 파일쓰기 시도가 곧 환경설정 판정이다.

→ 사용자에게 체크를 요청했다. 켜진 뒤 A1 을 다시 돌려 `파일쓰기 결과` 가
   `성공 (n bytes)` 로 바뀌는 것을 확인하고 A2 로 간다.
