# 시즌1 레드팀 리뷰 브리프 (Fable 5.1 UltraCode 세션용)

작성 2026-09-04 총괄 · **이 문서가 네 임무서다. CLAUDE.md 를 먼저 읽었다는 전제로 쓴다.**

## 0. 네가 누구고 무엇을 하는가

- 너는 이 프로젝트 팀 밖에서 온 **레드팀 리뷰어**다. 시즌1(2026-08-26 ~ 09-05) 동안
  에이전트 4자리(총괄 클라우드 + 로컬 B 썸네일·D AE·E 스크립트)가 만든 설계 전체를
  **적대적으로** 검토한다. 우리가 맞다고 믿는 것을 깨는 게 네 일이다.
- **렌즈는 효율성 하나다** (팀장 지시, 2026-09-03). 보안·프라이버시 지적은 범위 밖 —
  한 건도 내지 마라. 여기는 1인 채널의 사내 파이프라인이고, 그 시간에 낭비를 하나 더 찾아라.
- 기준은 **최신 설계 하나**다. 과거 커밋·중간 판본·레거시는 보지 않는다(§3 바이패스).
- 결과는 §6 규약대로 **옆가지로 푸시**한다. 본류에 직접 푸시하지 않는다.

## 1. 리뷰 대상 — 다섯 덩어리

| # | 덩어리 | 진입점 | 주인 |
|---|---|---|---|
| 1 | **렌더러** — 결정적 차트 모션그래픽 | `src/cli.mjs` → `src/render/engine.js`·`layers.js`·`chart.js`·`theme.js`·`scene.html`·`capture.mjs` | 총괄 |
| 2 | **씬 문법** — 컷 선언 | `scenes/cmg12-*.scenes.js`(최신 문법)·`sl-11-*.scenes.js`·`thumb-ch12-*.scenes.js` | 총괄(씬)·B(thumb) |
| 3 | **AE 이식 파이프라인** — 씬 → After Effects 컴포지션 | `tools/ae/scene-export.mjs`(진입) → `text-metrics.mjs`·`jobs/_ae.jsx`·`jobs/_types.jsx`·`jobs/b2_build.jsx`·`diff.mjs`·`pack.mjs` | D |
| 4 | **썸네일 툴체인** — 포토샵 COM 빌드 | `tools/photoshop/build_thumb.jsx`·`config.json`·`run.ps1` + 컨테이너 대체 경로 `tools/thumbnail_png.py`·`psdedit.py` | B |
| 5 | **컷편집·숏폼 도구** | `tools/cutedit/*.py`(STT 컷·srt 규칙·챕터·범퍼 실측)·`tools/shortform.py` | E |

가로지르는 것: **기록 시스템**(`log/build_worklog_db.py` 가 worklog.db·WORKLOG.md·worklog.html·README.md 를 전부 생성, `log/save.py` 가 세이브/로드) — 총괄. **스펙 문서**(`brand/STYLE.md`·`brand/EDIT-RULEBOOK.md`) — 실측 기반, 코드가 일부 강제.

## 2. 리뷰 관점 — 효율성. 이 여섯 갈래로 낭비를 찾아라

모든 지적은 "이대로 두면 **무엇이(시간·렌더·재작업·유지보수) 얼마나 낭비되는가**"로
끝나야 한다. 그 문장이 안 나오는 지적은 내지 마라. 보안·프라이버시는 §0 대로 범위 밖.

1. **재작업 폭탄 — 정합성 붕괴 지점**: 씬 문법 ↔ 렌더러 ↔ AE 변환기 ↔ 썸네일 씬이 같은
   레이어 시그니처를 공유한다. 한쪽이 바뀌면 어디가 **소리 없이** 깨져 납품 라운드를
   통째로 날리는가? (실례: cmgArrow 만 잉크 상자 중심 — 정렬 기준이 자리마다 제각각이라
   일반화가 틀렸던 적 있음. AE-LAB.md 09-03 절. 이번 시즌 반려 12라운드의 대부분이
   이런 어긋남이었다 — request 52~65 참조)
2. **중복·사장 코드**: 같은 일을 두 곳이 하는 자리(예: 썸네일 로컬 JSX ↔ 컨테이너 파이썬
   경로, 씬 좌표 계산의 렌더러/AE 이중화), 이제 안 쓰는데 살아 있는 코드. 삭제/단일화
   제안까지.
3. **렌더·실행 시간**: 블러 80분 사고(constraint 1) 같은 게 또 숨어 있는가? 씬당 렌더
   시간을 늘리는 낭비 패턴, --stills 로 잡을 수 있는데 실렌더로 잡는 절차.
4. **수작업 루프**: 사람이 매 회차 반복하는데 도구화 안 된 절차(대본→씬 변환, 검증,
   납품 패키징, 결재 왕복). 워크플로 단계 자체의 낭비.
5. **기록 시스템의 비용**: build_worklog_db.py 단일 파이썬 소스가 진실의 원본이고 재배번
   같은 수동 관례가 있다. 이 구조가 회차가 쌓일수록 어디서 비싸지는가? (단, "SQLite 대신
   X 를 써라"류의 전면 교체 제안은 이관 비용까지 셈해서만)
6. **협업 규약의 왕복 낭비**: 옆가지 → 총괄 병합 · 결재 흐름에서 불필요한 대기·중복 검증·
   같은 정보의 반복 전달이 어디서 생기는가?

이미 아는 벽 37개는 `SELECT * FROM constraint_note;` — **재보고는 감점, 그 방어가 뚫리는
시나리오나 더 싼 우회의 발견은 득점**이다.

## 3. 바이패스 — 열지도 마라

- `tools/legacy/` — 1세대 썸네일 도구(폭 역산). 실행 금지 격리.
- `brand/thumbnail/legacy/`
- `tools/ae/anchors.mjs`·`tools/ae/jobs/_anchors.jsx`·`tools/ae/jobs/a1~a5*.jsx` — A 계열 파일럿. B 계열로 대체됨.
- `lab/ae/pilot.aep`·`lab/ae/차11-4 손익비.mogrt`·`lab/ae/cut2-base.scenes.js`·`lab/ae/a3/`·`lab/ae/a6/`·`lab/ae/AEP-MOGRT-조사보고.txt` — 파일럿 증거물.
- `src/tools/exp-drift.mjs`·`exp-survey.mjs` — 초기 조사용, 현행 미사용.
- `scenes/thumb-ch11.scenes.js` — 구판 (thumb-ch11-A/B/C 로 대체).
- `scenes/cmg-*.scenes.js` 중 차11 이전 회차분 — 문법 견본으로만 존재.
- **생성물**: `log/worklog.db`·`log/worklog.html`·`log/WORKLOG.md`·`README.md` — 리뷰는
  생성기(`log/build_worklog_db.py`)를 본다. 생성물의 오류는 곧 생성기의 오류다.
- `deliver/` — 납품 결과물(픽셀). 코드 리뷰 대상 아님.
- `scripts/shortform/` — 콘텐츠 산출물. 규칙 리뷰는 `shortform_rule` 테이블과 `tools/shortform.py` 로.
- 지난 회차 대본·프리미어 파일 데이터(`log/data/scripts.json` 등) — 데이터이지 설계가 아님.

## 4. 저장소 밖 — 검증 불가로 치고 넘어가라

| 자리 | 내용 |
|---|---|
| 로컬 B `C:\cmgwork\` | 템플릿 src.psd(180MB)·빌드 out/·차트 입력 png |
| 로컬 D `C:\aelab\` | 납품 zip v6 2개·AE 중간물 199MB (저장소 `lab/ae/full/` 에 v6 사본 있음) |
| 로컬 E 개인 메모리 | recency-beats-exceptions.md 등 |
| G드라이브 | 회사 원본 전부 (`SELECT * FROM drive_map;`) — 읽기 전용 원천 |

이들 부재로 재현 불가한 검증(포토샵 실행, AE 실행, 원본 대조)은 **"로컬 검증 필요"로
표시만** 하고 추론으로 때우지 마라.

## 5. 실행법 — 컨테이너에서 되는 것

```bash
npm install                     # 의존성 (Chromium 은 사전 설치)
node src/cli.mjs --config scenes/cmg12-bridge.scenes.js --all --stills 4 --out /tmp/rt   # 구도 확인
node src/cli.mjs --config scenes/sl-11-4.scenes.js --scene cut3-conditions --format mp4 --out /tmp/rt  # 실렌더
python3 log/build_worklog_db.py # DB 재생성 (결정성 검증에 써라)
python3 tools/shortform.py check --kind point <파일>   # E 도구 스모크
```

- 렌더 벤치는 `SELECT * FROM benchmark;` — 블러 씬 230~420s/클립이 정상 범위다.
- **`log/save.py` 는 실행 금지** — 커밋·푸시까지 해 버린다. 네 커밋은 §6 대로 직접.
- AE·포토샵·프리미어 실행은 불가(§4). `.prproj` 는 `gunzip -c` 로 읽을 수 있다.

## 6. 결과 반환 규약

1. 산출물은 **`lab/redteam/FINDINGS.md`** 하나로 모아라. 항목 형식:
   `[P0~P3] [덩어리] 제목 / 증거(파일:줄) / 낭비 시나리오(무엇이 얼마나 새는가) / 제안(선택)`.
   P0 = 납품 라운드를 날리는 급, P1 = 회차마다 시간을 먹는 급, P2 = 유지보수 비용,
   P3 = 정리하면 좋은 것. 재현 스크립트는 `lab/redteam/` 아래에 같이 둔다.
2. **본류·기존 파일 수정 금지** (코드 픽스도 금지 — 지적만). `log/` 이하와
   `build_worklog_db.py` 는 절대 건드리지 않는다(총괄 전용).
3. 브랜치 **`local/redteam-51`** 를 본류에서 새로 파 커밋하고
   `git push -u origin local/redteam-51` 로 올려라. 태그 푸시는 403 이다.
4. 커밋 메시지는 한 줄 요약 + 본문. 마치면 P0/P1 개수와 브랜치명을 보고하고 끝낸다.
   총괄이 취합·판정한다.

## 7. 시즌1 스냅샷 좌표

- 본류 `claude/futures-youtube-video-edit-fhio4s` 의 시즌1 마감 커밋이 기준이다
  (금요일 마감 후 `season/1` 표식 예정 — 없으면 그냥 본류 최신).
- 복구 좌표는 `log/data/checkpoints.json` (태그 대용 슬롯↔해시 짝).

---

## 부록 — 세션 시작 프롬프트 (이정찬용, 새 Fable 5.1 세션에 이대로 복붙)

> ultracode. 너는 이 저장소(boyjustin76/AC-Stock-, 본류 브랜치
> claude/futures-youtube-video-edit-fhio4s)의 시즌1 설계에 대한 레드팀 리뷰어야.
> CLAUDE.md 를 읽은 다음 log/REDTEAM-BRIEF.md 를 읽어 — 그게 네 임무서고,
> 리뷰 렌즈(효율성 단독)·바이패스 목록·결과 반환 규약이 전부 거기 있어.
> 임무서와 이 프롬프트가 다르면 이 프롬프트가 우선이야. 철저하게, 여러 갈래로
> 교차 검증해서 봐 줘. 다 되면 P0/P1 개수와 브랜치명만 보고해.
