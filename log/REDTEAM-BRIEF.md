# 시즌1 레드팀 리뷰 브리프 (Fable 5.1 UltraCode 세션용)

작성 2026-09-04 총괄 · **이 문서가 네 임무서다. CLAUDE.md 를 먼저 읽었다는 전제로 쓴다.**

## 0. 네가 누구고 무엇을 하는가

- 너는 이 프로젝트 팀 밖에서 온 **레드팀 리뷰어**다. 시즌1(2026-08-26 ~ 09-05) 동안
  에이전트 4자리(총괄 클라우드 + 로컬 B 썸네일·D AE·E 스크립트)가 만든 설계 전체를
  **적대적으로** 검토한다. 우리가 맞다고 믿는 것을 깨는 게 네 일이다.
- **렌즈는 효율성 하나다** (팀장 지시, 2026-09-03). 보안·프라이버시 지적은 범위 밖 —
  한 건도 내지 마라. 여기는 1인 채널의 사내 파이프라인이고, 그 시간에 낭비를 하나 더 찾아라.
- 기준은 **최신 설계 하나**다. 과거 커밋·중간 판본·레거시는 보지 않는다(§3 바이패스).
- **문서 우선순위**: 이 브리프 > CLAUDE.md > DB 의 안내 뷰·테이블. CLAUDE.md 의 상시
  관례(save.py 호출, 견본 파일, 세이브 슬롯)와 이 브리프가 다르면 브리프가 우선이다.
  DB 안내성 데이터에서 낡은 서술을 발견하면 그건 §2-5 의 정식 득점 소재다.
- 결과는 §6 규약대로 **옆가지로 푸시**한다. 본류에 직접 푸시하지 않는다.

## 1. 리뷰 대상 — 다섯 덩어리

**대상 판정 규칙**: 아래 표의 진입점은 **요약이지 전수 목록이 아니다**. 각 진입점에서
import/실행 그래프로 도달하는 파일 전부가 대상이다 — §3 명시 바이패스만 예외.

| # | 덩어리 | 진입점 | 주인 |
|---|---|---|---|
| 1 | **렌더러** — 결정적 차트 모션그래픽 | `src/cli.mjs` → `src/render/`(engine·layers·chart·theme·anim·capture·encode·server·split + scene.html)·`src/market/candles.js` | 총괄 |
| 2 | **씬 문법** — 컷 선언 | 대형 씬 본체 `scenes/cmg12-cross.build.js`(`cross`·`layer-*` 의 `.scenes.js` 는 build() 를 부르는 껍데기 — 정의 리뷰는 build.js 에서), 단독 씬 `cmg12-bridge`·`cmg12-buy` 등 `cmg12-*`, `sl-11-*`, `thumb-ch12-*` | 총괄(씬)·B(thumb) |
| 3 | **AE 이식 파이프라인** — 씬 → After Effects 컴포지션 | `tools/ae/scene-export.mjs`(진입) 포함 **`tools/ae/` 전체에서 §3 의 A 계열 명단을 뺀 나머지 전부** (text-metrics.mjs·diff.mjs·pack.mjs·bridge.jsx·run.ps1·wins.ps1·config.json·jobs/_ae·_types·_lib·b0~b7) | D |
| 4 | **썸네일 툴체인** — 포토샵 COM 빌드 | `tools/photoshop/` 전체(build_thumb.jsx·config.json·run.ps1·dump_*.jsx 3종) + 컨테이너 대체 경로 `tools/thumbnail_png.py`·`psdedit.py` | B |
| 5 | **컷편집·숏폼 도구** | `tools/cutedit/*.py`(STT 컷·srt 규칙·챕터·범퍼 실측)·`tools/shortform.py` | E |

보조 도구도 대상: `src/tools/exp-capture.mjs`(현행 벤치)·`find-events.mjs`·`probe-labels.mjs`·
`install-fonts.mjs`, `tools/premiere_xml.py`(FCP7 XML 납품 보조 — 바이패스된 `tools/premiere/`
와 다른 현행 파일이다)·`tools/render-cmg12-layers.mjs`(층 분리 렌더 구동기).

가로지르는 것: **기록 시스템** — `log/save.py` 가 세이브마다 `log/build_worklog_db.py`
(worklog.db + WORKLOG.md) → `log/build_worklog_page.py`(worklog.html) → `log/build_readme.py`
(README.md) 를 차례로 돌린다. 전부 총괄. **스펙 문서**(`brand/STYLE.md`·`brand/EDIT-RULEBOOK.md`)
— 실측 기반, 코드가 일부 강제.

주인 지도 각주 (2026-09-03 전수 스윕으로 확정):
- D 는 `tools/ae/`·`lab/ae/` 외에 **`tools/premiere/`·`lab/premiere/`** 도 소유 — 프리미어
  직접 편집 랩(M1~M6). 이 계열은 AE 채택으로 **보류** 상태라 §3 바이패스.
- `brand/` 하위 전부(logo/·reference/·sfx/·texture/·premiere/·fonts/·ui/·SHORTFORM-FX-POOL.md,
  thumbnail/ 만 B), `scenes/nq-*`, `log/build_readme.py`·`build_worklog_page.py` — 총괄.
- `tools/cutedit/` 는 E 가 개발·유지하되 STT 컷편집 자체는 저장소(총괄) 소관, E 이관분은
  srt 추출(2026-09-01) — 경계는 CLAUDE.md 범위표.
- `tools/thumbnail_png.py` 는 B 기준 소유 / 총괄 유지보수 (컨테이너 전용 경로).

## 2. 리뷰 관점 — 효율성. 이 여섯 갈래로 낭비를 찾아라

모든 지적은 "이대로 두면 **무엇이(시간·렌더·재작업·유지보수) 얼마나 낭비되는가**"로
끝나야 한다. 그 문장이 안 나오는 지적은 내지 마라. 보안·프라이버시는 §0 대로 범위 밖.

**내부어 소사전** (이 소사전 없이는 기록이 안 읽힌다):
차N / 차명N = 차트명가 N화(같은 회차의 두 표기) · 결재/반려 = 팀장(또는 총괄) 승인/거절 ·
rN = 같은 납품물의 N차 교체본 · 6안 = 썸네일 시안 A·B·C(+강조판 A2·B2·C2) ·
재배번 = 로그 항목 id 를 병합 때 다시 매기는 수동 관례 · `constraint N`/`request N` =
worklog.db 의 constraint_note.id / request.id · A/B 계열 = AE 파일럿/현행, M1~M6 =
프리미어 랩 마일스톤 · 이정찬 = 팀원(컷편집 담당, 이 시스템의 운영자) · 잉크 상자 =
글리프 픽셀 경계(전진폭과 다름) · 격자박스(titleBox) = 썸네일 타이틀이 앉는 실측 상자.

1. **재작업 폭탄 — 정합성 붕괴 지점**: 씬 문법 ↔ 렌더러 ↔ AE 변환기 ↔ 썸네일 씬이 같은
   레이어 시그니처를 공유한다. 한쪽이 바뀌면 어디가 **소리 없이** 깨져 납품 라운드를
   통째로 날리는가? (실례: cmgArrow 만 잉크 상자 중심 — 정렬 기준이 자리마다 제각각이라
   일반화가 틀렸던 적 있음. AE-LAB.md 09-03 절. 이번 시즌 반려 12라운드의 대부분이
   이런 어긋남이었다 — request 52~65 참조)
2. **중복·사장 코드**: 같은 일을 두 곳이 하는 자리(예: 썸네일 로컬 JSX ↔ 컨테이너 파이썬
   경로, 씬 좌표 계산의 렌더러/AE 이중화), 이제 안 쓰는데 살아 있는 코드. 삭제/단일화
   제안까지. 알려진 출발점 하나: **컨테이너 썸네일 경로는 지금 죽어 있다** —
   `tools/thumbnail_png.py` 는 차12 config(6안 전부 `scene` 키 없음)에서 즉시 종료하고,
   titleBox 격자박스도 안 읽는다(폭 1185/1120 하드코딩 잔존). 두 경로를 유지할 가치가
   있는가부터 물어라.
3. **렌더·실행 시간**: 블러 80분 사고(constraint 1) 같은 게 또 숨어 있는가? 씬당 렌더
   시간을 늘리는 낭비 패턴, --stills 로 잡을 수 있는데 실렌더로 잡는 절차.
4. **수작업 루프**: 사람이 매 회차 반복하는데 도구화 안 된 절차(대본→씬 변환, 검증,
   납품 패키징, 결재 왕복). 조사 진입점: `workflow_step` 테이블(9단계 절차 정의),
   `request` 테이블 52~65(이번 시즌 반려 라운드 전문 — 왕복의 원문이다).
5. **기록 시스템의 비용**: build_worklog_db.py 단일 파이썬 소스가 진실의 원본이고 재배번
   같은 수동 관례가 있다. 이 구조가 회차가 쌓일수록 어디서 비싸지는가? (단, "SQLite 대신
   X 를 써라"류의 전면 교체 제안은 이관 비용까지 셈해서만)
6. **협업 규약의 왕복 낭비**: 옆가지 → 총괄 병합 · 결재 흐름에서 불필요한 대기·중복 검증·
   같은 정보의 반복 전달이 어디서 생기는가? 규약의 원문: `log/AE-LAB-MANUAL.md`·
   `SCRIPT-AGENT-MANUAL.md`·`PREMIERE-LAB-MANUAL.md`(보류 계열이라 규약 부분만)와
   각 랩 보고서(`AE-LAB.md`·`SCRIPT-LAB.md`).

이미 아는 벽 37개는 constraint_note 테이블(§5 의 질의법으로) — **재보고는 감점, 그 방어가
뚫리는 시나리오나 더 싼 우회의 발견은 득점**이다.

## 3. 바이패스 — 열지도 마라

(2026-09-03 전수 스윕으로 각 항목의 "현행 코드가 참조 안 함"을 grep 확인한 목록이다)

- `tools/legacy/` — 1세대 썸네일 도구(폭 역산). 실행 금지 격리.
- `brand/thumbnail/legacy/` — 참조는 tools/legacy 안에서만.
- `tools/ae/anchors.mjs`·`tools/ae/jobs/_anchors.jsx`·`tools/ae/jobs/a1~a5*.jsx`(11개) — A 계열 파일럿. B 계열로 대체됨.
- `lab/ae/pilot.aep`·`차11-4 손익비.mogrt`·`cut2-base.scenes.js`·`cut2-base-r63-무주석.png`·`a3/`·`a6/`·`AEP-MOGRT-조사보고.txt` — 파일럿 증거물.
- **`tools/premiere/`·`lab/premiere/`** — 프리미어 직접 편집 랩(M1~M6) 일체.
  AE 채택으로 보류된 계열이라 코드 리뷰 제외. 단 "보류 계열을 저장소에 유지하는 비용"
  자체는 §2-2 관점에서 지적 가능.
- `src/tools/exp-drift.mjs`·`exp-survey.mjs`·`find-cross.mjs`·`profile-render.mjs` — 초기
  조사용/대체됨(profile-render 는 자기 헤더가 exp-capture 로 대체됐다고 명시), 현행 미사용.
- `scenes/nq-overlay.scenes.js`·`lab/cmg12/rsi-smoke.scenes.js` — 초기 데모/스모크, 참조 0.
- `scenes/thumb-ch11-A/B/C.scenes.js` — 차11 납품 확정 구판(현행 견본은 thumb-ch12-*). 배선 없음.
- **생성물**: `log/worklog.db`·`WORKLOG.md`(← build_worklog_db.py)·`worklog.html`(← build_worklog_page.py)·`README.md`(← build_readme.py)·`log/data/checkpoints.json`(← save.py) —
  리뷰는 생성기를 본다. 생성물의 오류는 곧 생성기의 오류다.
- `deliver/` — 납품 결과물(픽셀). 코드 리뷰 대상 아님.
- `scripts/shortform/` — 콘텐츠 산출물. 규칙 리뷰는 `shortform_rule` 테이블과 `tools/shortform.py` 로.
- 지난 회차 대본·프리미어 파일 데이터(`log/data/*.json`, `brand/premiere/*.prproj` 등) — 데이터이지 설계가 아님.
- **잔여 포괄 조항**: §1 대상도 위 목록도 아닌 나머지는 에셋·데이터·문서다(brand/ 에셋,
  log/*.md 보고서·매뉴얼, lab/ae/full/·lab/cutedit/, CLAUDE.md, package*.json) — 열 필요
  없다. 단 무분류로 남은 파일이 **코드**라면 그 자체가 분류 누락이니 FINDINGS 에 적어라.

**배선이 남은 구세대 셋 — 내용 리뷰는 건너뛰되 배선은 지적 대상**:
- `scenes/nq-basic.scenes.js` — 브랜드 이전 첫 씬인데 `src/cli.mjs`·`engine.js` 의
  **config 미지정 기본값**으로 아직 배선돼 있다.
- `scenes/cmg-20ma-runner.scenes.js` — 구세대 문법 견본 + `src/tools/exp-capture.mjs`(벤치)가
  기준 씬으로 참조.
- `scenes/thumb-ch11.scenes.js`(구판) — `exp-capture.mjs` 의 투명 씬 검증 경로가 참조.

## 4. 저장소 밖 — 검증 불가로 치고 넘어가라

| 자리 | 내용 |
|---|---|
| 로컬 B `C:\cmgwork\` | 템플릿 src.psd(180MB)·빌드 out/·차트 입력 png |
| 로컬 D `C:\aelab\` | 납품 zip v6 2개·AE 중간물 199MB (저장소 `lab/ae/full/` 에 v6 사본 있음) |
| 로컬 E 개인 메모리 | recency-beats-exceptions.md 등 |
| G드라이브 | 회사 원본 전부 (drive_map 테이블) — 읽기 전용 원천 |

이들 부재로 재현 불가한 검증(포토샵 실행, AE 실행, 원본 대조)은 **"로컬 검증 필요"로
표시만** 하고 추론으로 때우지 마라. 그 항목들은 FINDINGS.md 맨 끝에 **"로컬 검증 필요"
별도 절**로 모아라 — 무엇을 어느 자리(B/D/E)에서 어떤 명령으로 확인하면 되는지까지 적으면,
총괄이 그대로 로컬 세션에 넘긴다.

## 5. 실행법 — 컨테이너에서 되는 것 (전부 2026-09-03 실측)

```bash
npm install       # 이미 깔려 있으면 0.4s 무변경 통과. Chromium 은 사전 설치
# 구도 확인 — 2씬×4장 PNG 가 <out>/stills/ 에, 실측 약 5초
node src/cli.mjs --config scenes/cmg12-bridge.scenes.js --all --stills 4 --out /tmp/rt
# 실렌더 (플래그·씬 id 유효 확인됨. 블러 씬은 230~420s/클립이 정상 — benchmark 테이블)
node src/cli.mjs --config scenes/sl-11-4.scenes.js --scene cut3-conditions --format mp4 --out /tmp/rt
# DB 질의 — sqlite3 CLI 는 이 컨테이너에 없다. python3 표준 모듈로 읽는다(읽기 전용 mode=ro)
python3 -c "import sqlite3;[print(r) for r in sqlite3.connect('file:log/worklog.db?mode=ro',uri=True).execute('SELECT * FROM constraint_note')]"
# E 도구 스모크 — 임의 파일이면 이름 규칙 지적 2건(파일·폴더)이 기본으로 나온다. 명령 자체는 정상
python3 tools/shortform.py check --kind point <파일>
```

- **기록 시스템 결정성 검증은 이렇게만**: `python3 log/build_worklog_db.py` 는
  `log/worklog.db` 를 제자리에서 다시 쓰고, commit_log 를 실행 시점 git log 에서 뽑기
  때문에 **커밋본과는 항상 달라진다(그건 버그가 아니다)**. 판정선은 "같은 HEAD 에서
  2회 빌드 → md5 동일"(실측 통과). 끝나면 반드시 `git restore log/` 로 되돌려라.
- **`log/save.py` 는 실행 금지** — 커밋·푸시까지 해 버린다. 네 커밋은 §6 대로 직접.
- AE·포토샵·프리미어 실행은 불가(§4). `.prproj` 는 `gunzip -c` 로 읽을 수 있다.

## 6. 결과 반환 규약

1. **시작 즉시 기준커밋을 고정해라**: `git rev-parse HEAD` 를 `lab/redteam/FINDINGS.md`
   머리에 적고, 모든 증거(파일:줄)는 그 해시 기준으로 쓴다. 리뷰 중 본류가 전진해도
   갈아타지 않는다.
2. 산출물은 **`lab/redteam/FINDINGS.md`** 하나로 모아라(이 폴더는 지금 없다 — 네가
   만든다. 폴더명 `out/` 은 .gitignore 전역 매칭에 걸리니 쓰지 마라). 항목 형식:
   `[P0~P3] [덩어리] 제목 / 증거(파일:줄) / 낭비 시나리오(무엇이 얼마나 새는가) / 제안(선택)`.
   P0 = 납품 라운드를 날리는 급, P1 = 회차마다 시간을 먹는 급, P2 = 유지보수 비용,
   P3 = 정리하면 좋은 것. 재현 스크립트는 `lab/redteam/` 아래에 같이 둔다.
3. **기존 파일 수정 금지, 새 파일도 `lab/redteam/` 밖 생성 금지** (코드 픽스도 금지 —
   지적만). §5 의 재생성으로 트리가 더러워졌으면 커밋 전에 `git restore log/` 로 되돌리고,
   커밋은 반드시 `git add lab/redteam/` 경로 지정으로만 — `git add -A`/`git commit -a` 금지.
4. 브랜치는 **`local/redteam-s1`** (s1 = 시즌1. 이름 그대로 써라). 본류에서 새로 파서
   커밋하고 `git push -u origin local/redteam-s1` 로 올려라. 원격에 local/* 선례가 4개
   있으니 브랜치 푸시는 열려 있다 — 태그 푸시만 403 이다.
5. 커밋 메시지는 한 줄 요약 + 본문. 마치면 기준커밋 해시·P0/P1 개수·브랜치명을 보고하고
   끝낸다. 총괄이 취합·판정한다.

## 7. 시즌1 스냅샷 좌표

- 본류 `claude/futures-youtube-video-edit-fhio4s` 의 시즌1 마감 커밋이 기준이다
  (금요일 마감 후 `season/1` 표식 예정 — 없으면 본류 최신을 §6-1 로 고정해서 쓴다).
- 복구 좌표는 `log/data/checkpoints.json` (태그 대용 슬롯↔해시 짝).

---

## 부록 — 세션 시작 프롬프트 (이정찬용, 새 Fable 5.1 세션에 이대로 복붙)

> ultracode. 너는 이 저장소(boyjustin76/AC-Stock-, 본류 브랜치
> claude/futures-youtube-video-edit-fhio4s)의 시즌1 설계에 대한 레드팀 리뷰어야.
> CLAUDE.md 를 읽은 다음 log/REDTEAM-BRIEF.md 를 읽어 — 그게 네 임무서고,
> 리뷰 렌즈(효율성 단독)·대상과 바이패스·결과 반환 규약이 전부 거기 있어.
> 범위와 규약은 임무서를 따르고, 철저하게, 여러 갈래로 교차 검증해서 봐 줘.
> 보고는 임무서 §6-5 형식(기준커밋·P0/P1 개수·브랜치명)으로.
