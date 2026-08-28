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
python tools\premiere\verify.py <원본> <저장본>
```

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
