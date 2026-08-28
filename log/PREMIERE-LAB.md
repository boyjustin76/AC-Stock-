# 프리미어 직접 편집 실험 일지 — D 세션 (로컬 윈도우)

> 매뉴얼: `log/PREMIERE-LAB-MANUAL.md`. 이 파일은 §5 가 정한 유일한 보고 창구다.
> 여기 적힌 숫자는 전부 이 PC 에서 실측한 것이다. 추측에는 "추정"이라고 붙였다.

---

## 2026-08-28 · §0 점검 → M1 통과

**결론 먼저.** 프리미어에는 포토샵 같은 COM 자동화 ProgID 가 **없다**. 대신 포토샵을 거친
**BridgeTalk** 로 닿았고, 그 경로로 M1(열기·복제·저장)을 끝냈다. 설치한 것은 아무것도 없다.

    PowerShell → Photoshop.Application (COM) → bridge.jsx → BridgeTalk → premierepro-26.0

---

### §0-1 PC — 맞다. 그러나 **회사 드라이브가 D: 가 아니다**

포토샵 실험을 성공시킨 그 PC 가 맞다. `C:\cmgwork` 에 흔적이 그대로 있다 —
`src.psd` 171MB, `build11.jsx`, `chartA/B/C.png`, 전부 8/27~8/28.

| | |
|---|---|
| 컴퓨터 | DESKTOP-PB0PVBQ · Gigabyte H310M HD3 2.0 · Windows 11 Pro 26200 |
| 포토샵 | 2026 / **27.9.1** — `Photoshop.Application` COM 정상 |
| 프리미어 | 2026 / **26.3.2** (build 2) |
| 드라이브 | **C: 와 G: 뿐. D: 는 존재하지 않는다.** |

**매뉴얼 §0-1 정정.** 회사 드라이브는 `D:\01_구글 드라이브(파가드AC)\트레이딩팩토리\` 가
아니라 **`G:\내 드라이브\트레이딩팩토리\`** 에 스트리밍 마운트돼 있다. 내용은 동일하다
(차명01~15 폴더 실재, 프리셋이 참조하는 샘플 파일 `Test-Path` = True).

매뉴얼이 근거로 든 `prproj_fact` 4번은 method 가 `<ActualMediaFilePath> 추출` —
**파일 안에 적힌 경로**지 이 PC 의 마운트 실측이 아니다. 그 회차를 만든 편집자 PC 는
D: 에 미러 동기화를 걸어 뒀던 것으로 **추정**된다.

결과: 프리셋을 열면 미디어가 오프라인이 된다. 프리미어가 직접 센 값으로 **53 / 64**.
(프리셋 XML 의 `<ActualMediaFilePath>` 는 68개, 드라이브 문자가 붙은 고유 경로는 49개.)

방증이 하나 더 있다 — `Profile-user\LocateDialog Column Settings` 가 **8/27 에 쓰였다.**
이 PC 는 이미 "미디어 연결" 대화상자를 만난 적이 있다.

### §0-2 프리미어 — **COM 자동화 ProgID 가 없다**

| 확인한 것 | 결과 |
|---|---|
| `HKLM\SOFTWARE\Classes` 의 `Premiere*` | `Adobe.Premiere.*.26` **12개 — 전부 파일 연결(셸 동사)** |
| `HKCU\SOFTWARE\Classes` 의 `Premiere*` | 없음 |
| `CLSID\*\LocalServer32` 전수 스캔 | Premiere 경로는 `WMEncodingHelper.exe` **하나뿐** — 자동화 서버가 아니다 |
| 타입 라이브러리(.tlb/.olb) | 설치 폴더에 없음 |
| CEP | 있음 (`CEP\extensions`, ExtendScript 살아 있음) |
| UXP | 있음 (`UXP\plugins`) |
| 스타트업 스크립트 | `...\Scripts\Startup\` 에 어도비 .jsx 3개. **Program Files 라 관리자 권한 없이는 못 쓴다** (쓰기 시도 → Access denied) |
| `CSXS.9~12` 의 `PlayerDebugMode` | **전부 미설정** — 미서명 CEP 확장은 지금 상태로 못 뜬다 |

즉 매뉴얼 §3-2 의 `New-Object -ComObject Premiere.Application` 은 그대로는 안 된다.
그러나 §3-3 이 금지한 "그러니 프리미어는 못 한다"는 결론에는 가지 않았다.

### 뚫은 길 — BridgeTalk

포토샵 안에서 잰 값이다 (`tools/premiere` 를 만들기 전, 일회성 프로브):

```
BridgeTalk.getTargets()                 →  photoshop, premierepro, ame
BridgeTalk.getSpecifier("premierepro")  →  premierepro-26.0
BridgeTalk.getStatus("premierepro")     →  ISNOTRUNNING   (설치됨, 안 떠 있음)
```

전송로가 있다. 프리미어가 안 떠 있으면 BridgeTalk 이 띄운다. 설치·관리자 권한·
미서명 확장 허용 **전부 불필요**하고, 검증된 포토샵 COM 드라이버를 그대로 재사용한다.

### §0-3 git

작업 시작 시점 `d4a96a9` = `origin/claude/futures-youtube-video-edit-fhio4s`, 최신.
`log/PREMIERE-LAB.md` 와 `lab/` 은 없었고 `origin/local/thumb-ch11` 은 본류에 완전히
병합돼 겹치는 파일이 없다. clone·fetch 가 인증 없이 통과했다 — 이 PC 에 자격증명이
캐시돼 있다 (constraint_note 19 의 비대화형 셸 문제는 이 PC 에서는 안 걸렸다).

---

## 드라이버 — `tools/premiere/`

포토샵 쪽 `tools/photoshop/run.ps1` 구조를 그대로 베꼈다. 실행 대상만 BridgeTalk 로 넘긴다.

| 파일 | 하는 일 |
|---|---|
| `run.ps1` | 잡 이름을 받아 `_job.txt` 에 경로를 쓰고, 포토샵 COM 으로 `bridge.jsx` 를 돌린다. UTF-8 **with BOM** (§6) |
| `bridge.jsx` | 포토샵 안에서 돈다. BridgeTalk 메시지를 만들어 `premierepro-26.0` 에 보내고 `BridgeTalk.pump()` 로 응답을 기다린다 |
| `jobs/*.jsx` | 프리미어 안에서 도는 실제 작업 |
| `verify.py` | **프리미어를 안 거친다.** 저장된 .prproj 를 gunzip 해서 숫자로 검사한다 (§3-5) |
| `config.json` | `labDir` · `src` · `target` · `timeoutSec` |

```
.\tools\premiere\run.ps1 probe        # 스크립팅 표면만 잰다
.\tools\premiere\run.ps1 m1_open      # 프리셋 사본을 열고 구조를 잰다
.\tools\premiere\run.ps1 m1_clone     # 시퀀스를 복제하고 saveAs
.\tools\premiere\run.ps1 baseline     # 열고 아무것도 안 하고 saveAs — 검증 기준선
.\tools\premiere\run.ps1 m2_swap      # 복제본의 클립 하나를 차트로 교체
python tools\premiere\verify.py <저장본> [--baseline <기준선>] [--seq-delta N]
```

기준선은 생략하면 `lab/premiere/baseline_open_save.prproj` 를 쓴다. **아래 M2 항목의
정정을 먼저 읽어라** — 기준선을 잘못 잡으면 기록 경로 차이가 작업 손실로 둔갑한다.

---

## 프리미어 스크립팅 표면 (실측)

```
app.version 26.3.2 · app.build 2
app 멤버   anywhere, bind, build, encoder, getAppPrefPath, getAppSystemPrefPath,
           getPProPrefPath, getPProSystemPrefPath, isStagingEnvironment, lastSender,
           learnPanelContentDirPath, learnPanelExampleProjectDirPath, path, production,
           project, projectManager, projects, properties, setTimeout, sourceMonitor,
           unbind, userGuid, version
project    activeSequence, cloudProjectlocalID, documentID, isCloudProject, name, path,
           rootItem, sequences
sequence   audioDisplayFormat, audioTracks, end, frameSizeHorizontal, frameSizeVertical,
           id, markers, name, projectItem, sequenceID, timebase, videoDisplayFormat,
           videoTracks, zeroPoint
```

**§3-6 사례.** 위 열거(`for..in`)에 **안 잡히는데 실재하는 함수가 있다.**
직접 `typeof` 로 찍어야 나온다:

| | |
|---|---|
| 있다 | `app.openDocument` · `app.newProject` · `app.quit` · `app.setSDKEventMessage` |
| 있다 | `project.save` · `project.saveAs` · `project.closeDocument` · `project.importFiles` · `project.createNewSequence` · `project.openSequence` |
| 있다 | **`sequence.clone`** · `sequence.createSubsequence` · `sequence.exportAsProject` · `sequence.close` · `sequence.getSettings` · `sequence.setSettings` |
| 없다 | `sequence.duplicate` · `sequence.save` · `sequence.saveAs` |

열거 목록만 믿었으면 `clone()` 을 못 찾고 qe 층으로 내려갔을 것이다.

**qe 층은 열려 있다** (§3-3).

```
app.enableQE()  →  true (첫 호출) / false (그 뒤)     ← §3-4 사례. 실패가 아니다
qe.version      →  26.3.2
qe 멤버         audioChannelMapping, codeProfiler, config, ea, language, location,
                name, platform, project, source, tqm, version
qe.project 멤버 currentRendererName, importFailures, isAudioConforming,
                isAudioPeakGenerating, isIndexing, name, numActiveProgressItems,
                numAudioPeakGeneratedFiles, numBins, numConformedFiles, numIndexedFiles,
                numItems, numSequenceItems, numSequences, path
```

M1 에서는 qe 를 **쓰지 않았다.** 공개 DOM 으로 됐다. M3 키프레임에서 필요해지면 쓴다.

---

## 프리셋 시퀀스 9개 (실측)

| # | 이름 | end (틱) | 초 |
|---|---|---|---|
| 0 | 최종_이평+rsi | 4,148,928,000,000 | 16.33 |
| 1 | 중첩 시퀀스 25 | 4,868,640,000,000 | 19.17 |
| 2 | **롱폼 고정 양식** | 20,634,566,400,000 | **81.23** |
| 3 | 최종_프랙탈 | 3,996,518,400,000 | 15.73 |
| 4 | 중첩 시퀀스 10 | 1,593,425,433,600 | 6.27 |
| 5 | [롱폼] | 0 | 0 |
| 6 | 중첩 시퀀스 08 | 1,185,408,000,000 | 4.67 |
| 7 | 중첩 시퀀스 11 | 1,703,609,107,200 | 6.71 |
| 8 | 중첩 시퀀스 08 | 1,457,814,758,400 | 5.74 |

`롱폼 고정 양식` 이 표준 뼈대로 보인다 — 1920x1080 · **timebase 8467200000 (30.0fps)** ·
비디오 트랙 11 · 오디오 트랙 4 · 잠긴 트랙 없음.

**주의.** 매뉴얼 M1 은 "FrameRate 틱이 8475667200(29.97) 그대로인지"를 검증 조건으로
들었는데, 이 시퀀스의 timebase 는 **8467200000(30.0)** 이다. 프리셋 안에 두 값이 섞여
있고(`prproj_fact` 2번과 일치) 롱폼 뼈대 쪽은 30.0 이다. 대본 타임코드가 29.97 이라는
근거와 어긋나 보이므로 **M4 회차 조립 전에 어느 쪽이 회차의 기준인지 확정해야 한다.**

---

## M1. 열기 · 복제 · 저장 — **통과**

`C:\pprolab\src.prproj`(저장소 프리셋의 사본)를 열고, `롱폼 고정 양식` 을 이름으로 찾아
(§3-10 — 인덱스·트랙 번호를 박지 않았다) `clone()` 하고 `C:\pprolab\m1_out.prproj` 로
`saveAs` 했다. 프리미어가 보고한 값이 아니라 **저장된 파일을 gunzip 해서** 검증했다 (§3-5).

`verify.py` 가 저장소 원본 ↔ `m1_out.prproj` 를 비교한 결과:

```
시퀀스 정의        9 → 10  (+1)
늘어난 시퀀스      롱폼 고정 양식 복사  (0820dc50-2da9-402c-b9e9-72300c12f838)
사라진 시퀀스      (없음) — 원본 9개 UID 전부 그대로
키프레임 블록      41 → 77  (+36)
FrameRate 값 집합  {5292000, 5760000, 8467200000, 8475667200} — 그대로. 새 값 없음
```

**키프레임이 +36 늘었다** — 복제본이 모션을 물려받았다는 뜻이다. 이 실험의 전제
("키프레임·모션 효과는 프리셋 것을 그대로 물려받는다")가 파일 수준에서 성립한다.

FrameRate 는 **값 집합은 그대로지만 개수가 줄었다** (8475667200 이 61 → 55,
5292000 이 175 → 112). 이건 복제 때문이 아니라 아래의 열기 재작성 때문이다.

산출물: `lab/premiere/m1_out.prproj`

---

## ⚠ 새로 나온 사실 — **여는 것만으로 .prproj 가 다시 쓰인다**

매뉴얼 §7 의 "회사 드라이브 원본 .prproj 열기 금지"는 조심하라는 말이 아니라
**실제로 파일이 바뀐다**는 뜻이다. 따로 실험해서 못 박았다 (`jobs/opentest.jsx`):

저장소 프리셋을 그대로 복사한 파일(md5 `f0d69df0…`, 288,434 바이트)을
`app.openDocument()` 로 **열기만** 했다. 복제도 저장도 호출하지 않았다.

```
before   288,434 바이트   12:25:10
after    278,880 바이트   12:25:18      ← 8초 만에. 우리는 아무것도 저장하지 않았다
```

열기 재작성이 하는 일 (저장소 원본 → 열기만 한 파일):

```
XML          3,652,362 → 3,290,253 바이트  (-10%)
시퀀스        9 → 9        (UID 전부 동일)
키프레임      41 → 41      (보존)
미디어 참조   68 → 67      (-1)
FrameRate    5292000 175→92 · 8475667200 61→54 · 8467200000 29→28 · 5760000 5→5
```

**해석(추정).** 시퀀스·키프레임은 온전하고 중복 항목만 정리된다. 파괴적이진 않지만
회사 드라이브 원본에 하면 되돌릴 수 없다. **사본으로만 작업한다는 §2-2 는 절대 규칙이다.**

증거 파일: `lab/premiere/m1_after_open_only.prproj` (열기만 한 결과물)

---

## §6 에 추가할 함정

1. **BridgeTalk 본문에 스크립트 소스를 실어 보내지 마라.** 역슬래시 이스케이프가
   전송 중에 한 번 더 이스케이프된다. `"\t"` 가 프리미어에서 **글자 `\t`** 로 실행됐다.
   본문은 `$.evalFile(new File("<경로>"))` 한 줄만 보내고, 소스는 프리미어가 디스크에서
   직접 읽게 한다. 덤으로 본문이 짧아져 메시지 크기 제한에서도 자유롭다.
2. **`_job.txt` 같은 인자 파일은 BOM 없는 UTF-8 로 써라.** 저장소 경로에 한글이 있어
   ASCII 로는 안 되고, PowerShell 5.1 의 `Set-Content -Encoding UTF8` 은 BOM 을 붙여
   JSX 가 경로를 못 찾는다.
   `[System.IO.File]::WriteAllText(p, s, (New-Object System.Text.UTF8Encoding($false)))`.
3. **`app.openDocument` 는 비동기다.** 호출 직후 `numSequences` 가 0 일 수 있다.
   `$.sleep` 으로 폴링해라 (이 PC 에서는 대부분 0초 만에 들어왔지만 보장은 없다).
4. **`app.enableQE()` 는 두 번째부터 `false` 를 준다.** 실패가 아니라 "이미 켜져 있다"다.
   반환값으로 성공을 판정하지 말고 `typeof qe` 를 봐라.
5. **네이티브 함수의 `.length`(arity)는 전부 0 이다.** `app.openDocument.length` = 0.
   인자 개수를 알아내는 데 못 쓴다.
6. `run.ps1` 은 UTF-8 **with BOM**, JSX 는 BOM 없는 UTF-8. 섞으면 각각 다르게 깨진다.

---

## 다음 (M2 — 소스 교체)

1. `npm run render` 로 차트를 뽑아 `C:\pprolab` 로 복사한다.
2. 복제한 시퀀스 안의 클립 하나를 그 파일로 교체 (`projectItem.changeMediaPath` 계열이
   공개 DOM 에 있는지 `typeof` 로 먼저 찍는다 — 열거에 안 잡히는 함수가 있다).
3. 검증: `<ActualMediaFilePath>` 가 새 파일을 가리키는지, **교체한 클립의 스케일이
   멋대로 재계산되지 않았는지** (§3-4 — 소스 해상도가 바뀌면 스케일이 파생값으로 다시
   계산될 수 있다). `verify.py` 에 스케일 비교를 붙인다.

**M2 전에 결정된 것:** 오프라인 미디어는 G: 로 되살린다. GUI 에서 사람이 한 번
`G:\내 드라이브\트레이딩팩토리` 를 지정하면 나머지는 자동 추적된다. 다만 그렇게 저장한
파일은 경로가 D: → G: 로 바뀌므로, 클라우드가 판정할 때 원본과 달라 보인다는 점을 미리 알린다.

## 클라우드에 요청

1. `lab/premiere/m1_out.prproj` 를 gunzip 해서 위 숫자를 독립적으로 확인해 달라.
2. **매뉴얼 §0-1 의 `D:\01_구글 드라이브(파가드AC)\` 를 `G:\내 드라이브\` 로 정정**하고,
   `prproj_fact` 4번에 "파일 안의 경로이며 이 PC 의 마운트와 다르다"는 단서를 달아 달라.
3. **매뉴얼 §3-2 의 `Premiere.Application` COM 전제를 BridgeTalk 경로로 바꿔 달라.**
   COM 자동화 ProgID 는 없다 (레지스트리 전수 확인).
4. 매뉴얼 M1 검증 조건의 FrameRate 8475667200 을, 롱폼 뼈대는 8467200000(30.0)이라는
   실측에 맞춰 다시 써 달라. 대본 타임코드 29.97 과의 관계는 M4 전에 확정이 필요하다.
5. 위 §6 함정 6건과 "열기만 해도 재작성" 을 DB 에 넣어 달라 (`build_worklog_db.py` 는
   §5 대로 건드리지 않았다).

---

## 2026-08-28 · M2 통과 — 소스 교체 (+ 검증 기반 재정비)

**결론 먼저.** 복제 시퀀스의 클립 하나를 렌더러 차트로 교체했고, **원본 시퀀스는 안 바뀌었다.**
모션·자르기 값이 소수점까지 그대로 남았다. 저장본을 새로 열어 확인했다.

교체 전에 검증 기반을 먼저 고쳤는데, **거기서 기준선 자체가 틀렸다는 게 나왔다.**

---

### ⚠ 정정 — `m1_after_open_only.prproj` 은 기준선으로 쓰면 안 된다

총괄 지시 1번은 기준선을 `m1_after_open_only.prproj` 로 바꾸라는 것이었다. 바꿔서 M1 을
다시 재 보니 `RangeLocked` 가 102 → 66 (**-36**) 으로 손실처럼 잡혔다. 대조군을 만들어 갈랐다
(`jobs/baseline.jsx` — 프리셋 사본을 열고 **아무것도 안 하고 saveAs**):

| | RangeLocked | 부모 분포 | StartKeyframe(문자열) | VideoComponentParam |
|---|---|---|---|---|
| 저장소 원본 | 214 | Audio 164 + Video 50 | 5,966 | 2,249 |
| 열기만 (in-place 재작성) | 102 | Audio 52 + Video 50 | 5,906 | **2,224** |
| **열기+saveAs (대조군)** | 52 | Audio 52 | **6,002** | **2,249** |
| M1 출력 | 66 | Audio 66 | 10,571 | 3,971 |

읽는 법:

1. `RangeLocked` 의 Video 50개는 **복제가 아니라 `saveAs` 가 지운다.** 값은 전부 `false`
   (기본값)이라 의미 손실은 아니다. 기준선을 saveAs 출력으로 잡으면 M1 은 52 → 66 (**+14**),
   손실이 아니라 증가다. 가짜 손실이었다.
2. **더 중요한 것 — 열기만 한 파일은 `saveAs` 출력과 24종의 태그에서 다르다.**
   in-place 재작성은 **부분 기록**이라 `VideoComponentParam` 이 2,224 로 깎여 있는데,
   `saveAs` 하면 2,249 로 원본과 같아진다. 즉 열기 재작성은 "정규화"가 아니라 **불완전한 기록**이다.
3. 그래서 `prproj_fact` 22 의 "열기 정규화가 StartKeyframe 60개 지운다"도 반쪽이다.
   -60 은 열기만 한 파일 기준이고, **`saveAs` 하면 6,002 로 원본(5,966)보다 오히려 36 늘어난다.**

**규칙: 기준선은 산출물과 같은 기록 경로(`saveAs`)를 지난 파일이어야 한다.**
안 그러면 기록 경로 차이가 작업 손실로 둔갑한다. 기준선을
`lab/premiere/baseline_open_save.prproj` 로 바꿨다.
`m1_after_open_only.prproj` 는 "열기가 파일을 바꾼다"의 증거로만 남긴다.

### `verify.py` 재작성

| 무엇 | 어떻게 |
|---|---|
| 기준선 | `lab/premiere/baseline_open_save.prproj` (기본값). `--baseline` 으로 교체 |
| 기대 증감 | `--seq-delta N`. 생략하면 실측값을 기대값으로 쓴다 (M2 는 `--seq-delta 0`) |
| 키프레임 | 컨테이너 말고 **점**. `StartKeyframe` · `StartKeyframePosition` · `StartKeyframeValue` 를 따로 세고, 합의 지표인 문자열 출현 수도 같이 낸다 |
| 시퀀스 단위 객체 | **8종 전수 검사** (아래) |
| 손실 감지 | 줄어든 태그를 전부 보고. 편집기 세션 상태 3종만 좁게 제외 |

**시퀀스 단위 객체 8종**은 추측하지 않고 실측으로 골랐다 — 기준선에서 개수가 시퀀스 정의 수(9)와
같고 복제 후 정확히 +1 이 되는 태그 중, 시퀀스 객체 그래프의 척추만 남겼다:

```
Sequence · VideoSequenceSource · AudioSequenceSource · TrackGroups
VideoTrackGroup · AudioTrackGroup · DataTrackGroup · MasterTrack
```

(기준선 대비 +1 인 태그는 실제로 114종이다. 8종은 그중 구조 척추만 추린 것이고,
나머지는 UI 상태·오디오 설정 등이라 반쪽 복제 판정에 쓰기엔 잡음이 많다.)

제외한 편집기 세션 상태는 셋뿐이다 — `MZ.PrefixKey.`(열려 있던 시퀀스 탭),
`list.view.expanded.state.`(패널 트리 펼침), `project.icon.view.`(아이콘 정렬).
**넓히면 진짜 손실을 가리므로 이 이상 늘리지 않는다.**

### M1 재검증 (정정된 기준선)

```
시퀀스        9 → 10 (+1, 기대 +1)   늘어난 것: 롱폼 고정 양식 복사
8종 전수      전부 +1 ✓
StartKeyframe 2,728 → 4,843 (+2,115) · 문자열 6,002 → 10,571 (+4,569)
내용물 손실   0종        편집기 세션 상태  6종 (무시)
고유 미디어   49 → 49    FrameRate 값 집합 불변
판정: 통과 ✓
```

---

### M2-a. 프로브 — 가장 큰 함정부터

`prproj_fact` 23 의 "원본 미디어는 복사되지 않고 공유된다"가 교체에 직결된다. 확인했다:

```
복제 시퀀스의 클립이 쓰는 마스터 클립 nodeId 15개
→ 15개 전부 원본 시퀀스와 공유 (000f42ad … 000f42ba)
```

즉 `projectItem.changeMediaPath()` 를 그냥 걸면 **원본 시퀀스까지 같이 바뀐다.**
격리되는 길을 먼저 찾아야 했다.

프로브에서 걸린 것 하나 — `trackItem.projectItem` 이 **null 인 클립이 많다.**
"흰 배경"·"그래픽"·"조정 레이어" 같은 합성 소스다. 트랙의 첫 클립을 잡으면 바로 터진다
(`TypeError: null is not an object`). 성질로 고르랬는데(§3-10) 인덱스로 고른 대가였다.

### M2-b. 교체 — `clip.projectItem` 대입이 된다

두 경로를 순서대로 시도하게 짜고, 되는 쪽을 기록하게 했다:

1. 차트를 새 projectItem 으로 import → **`clip.projectItem = newItem` 대입** ← **이게 됐다**
2. (예비) 공유 항목에 `changeMediaPath()` — 원본도 같이 바뀜

`projectItem` 은 열거상 속성이고 문서에 쓰기가 없는데 **대입이 먹힌다.** 이게 격리의 열쇠다.
클립의 이펙트·키프레임은 클립에 붙어 있어 소스만 갈아 끼워도 그대로 남는다.

대상은 성질로 찾았다 (§3-10) — 미디어 경로가 `차10_1-5.png` 로 끝나는 클립 = 복제본 `V1[2]`.

```
importFiles         true        rootItem 자식 36 → 37
새 항목             chartA.png  node=000f42bb   (1920x1080)
clip.projectItem 대입 → 000f42bb
결과 경로            C:\cmgwork\chartA.png
```

### M2-c. 검증

**(1) 클립 상태 — 교체 전후 (§3-4 스케일 검사)**

```
                 BEFORE                    AFTER
start            3742502400000             3742502400000     동일
end              8060774400000             8060774400000     동일
duration         4318272000000             4318272000000     동일
inPoint          915405926400000           914456685542400   ← 바뀜
outPoint         919724198400000           918774957542400   ← 바뀜 (폭은 동일)

모션   비율 조정=100 · 폭 비율 조정=100 · 균일 비율=true · 위치=0.5,0.5 · 기준점=0.5,0.5
       → 전부 불변. 스케일이 멋대로 재계산되지 않았다 ✓
자르기 왼쪽=0 · 위=8.05355834960938 · 오른쪽=3.38429260253906 · 아래=8.07402038574219
       → 소수점까지 불변 ✓
```

`inPoint`/`outPoint` 만 이동했다. 이건 **소스 내부 좌표**라 소스를 갈면 따라 움직이는 게 맞다 —
§3-4 가 말한 "이미 계산된 짝"의 사례다. **폭(duration)과 타임라인 위치(start/end)는 보존된다.**
판정할 때 inPoint 절대값을 보면 안 되고 duration 을 봐야 한다.

**(2) 파일 검사 (`verify.py`, 기준선 = `m1_out.prproj`, `--seq-delta 0`)**

```
시퀀스        10 → 10 (+0)        8종 전수 전부 +0 ✓
StartKeyframe 4,843 → 4,843 (+0)  키프레임 손실 없음
내용물 손실   0종                  편집기 세션 상태 0종
고유 미디어   49 → 50   +C:\cmgwork\chartA.png   ← 교체한 것만 늘었다
FrameRate     8475667200 이 55 → 56 (+1). 값 집합 불변
판정: 통과 ✓
```

**(3) 오프라인 대비 — 총괄이 말한 그 증거**

런타임 상태라 파일로는 못 재고 프리미어에게 물어야 한다:

```
오프라인 / 전체        53 / 66
온라인 미디어          chartA.png  ← 하나뿐
chartA.png.isOffline   false
chartA.png.mediaPath   C:\cmgwork\chartA.png
chartA.png 해석        frameRate=29.97002997003  pixelAspect=1
```

교체한 항목만 온라인이다. (FrameRate 55→56 의 정체도 이것 — 프리미어가 이 스틸에
29.97 을 물렸다.)

**(4) 되읽기 — 저장본 사본을 새로 열어서 (§3-5)**

```
복제.V1[2]   chartA.png     | start=3742502400000 | C:\cmgwork\chartA.png
원본.V1[2]   차10_1-5.png    | start=3742502400000 | D:\…\차10_1-5.png     ← 안 바뀜
복제.V1[2] 자르기  위=8.05355834960938 · 오른쪽=3.38429260253906 · 아래=8.07402038574219
원본.V1[2] 자르기  위=8.05355834960938 · 오른쪽=3.38429260253906 · 아래=8.07402038574219
```

**격리 성립.** 같은 마스터 클립을 공유하던 두 시퀀스가 이제 서로 다른 소스를 본다.

산출물: `lab/premiere/m2_out.prproj` · 기준선 `lab/premiere/baseline_open_save.prproj`

---

### §6 에 추가할 함정 (M2 분)

7. **`trackItem.projectItem` 은 null 일 수 있다.** "흰 배경"·"그래픽"·"조정 레이어" 같은
   합성 소스가 그렇다. 트랙의 첫 클립을 잡아 `projectItem` 을 쓰면 바로
   `TypeError: null is not an object` 다. 클립을 고를 때는 **`projectItem` 이 붙어 있는지부터** 본다.
8. **`clip.projectItem` 은 대입이 된다.** 문서에 없는 쓰기다. 마스터 클립이 원본 시퀀스와
   공유되는 상황에서 **격리 교체를 가능하게 하는 유일한 길**이라 잊지 마라.
   `changeMediaPath()` 는 공유 항목을 바꾸므로 원본까지 오염된다.
9. **소스를 교체하면 `inPoint`/`outPoint` 는 바뀌고 `duration`/`start`/`end` 는 보존된다.**
   in/out 절대값으로 판정하면 멀쩡한 교체를 실패로 읽는다.
10. PowerShell 에서 `... | Select-Object -First N` 으로 출력을 자르면 파이프가 끊겨
    **exit 255** 가 난다. 잡 실패가 아니다 — `bridge:` 줄을 봐라.

---

### 클라우드에 요청

1. `lab/premiere/m2_out.prproj` 를 `lab/premiere/m1_out.prproj` 기준으로 재계산해 달라
   (`--seq-delta 0`). 고유 미디어 경로가 `+C:\cmgwork\chartA.png` 하나만 늘고
   `차10_1-5.png` 이 남아 있으면 격리 성공이다.
2. **`prproj_fact` 22 를 정정해 달라.** "열기 정규화가 StartKeyframe 60개 지운다"는
   열기만 한 파일 기준이다. `saveAs` 출력은 5,966 → 6,002 으로 **늘어난다.**
   열기 재작성은 정규화가 아니라 **부분 기록**이고 `saveAs` 출력과 24종 태그에서 다르다
   (`VideoComponentParam` 2,224 vs 2,249). **기준선은 saveAs 출력이어야 한다** —
   `lab/premiere/baseline_open_save.prproj`.
3. `prproj_fact` 23 에 덧붙여 달라 — 마스터 클립은 공유되지만
   **`clip.projectItem` 대입으로 격리 교체가 된다.** M4 회차 조립에서 원본 시퀀스를
   지우기 전에도 안전하게 소스를 갈 수 있다는 뜻이다.
4. 시퀀스 단위 객체 8종 목록을 DB 에 박아 달라 (위 코드블록). 총괄이 8종이라고만 해서
   실측으로 골랐는데, 클라우드가 쓴 것과 같은지 대조가 필요하다.

### 다음 (M3 — 키프레임)

교체한 클립(`복제.V1[2]`, 지금은 `chartA.png`)의 모션 파라미터가 전부 정적이다
(`isTimeVarying` 전부 `-`). `motion_preset` 3건을 재현하려면 키프레임을 **새로 만들어야** 한다.
읽기 → 수정 → 생성 순으로 가고, 공개 DOM(`property.addKey`/`setValueAtKey` 계열)이
없으면 qe 층을 본다 (§3-3). 검증은 `<Keyframes>` 평문의 틱·값·보간타입을 파싱해 대조한다.
