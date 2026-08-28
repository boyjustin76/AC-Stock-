# 작업 로그 — 차트 컷씬 렌더러

- 날짜: 2026-08-26
- 저장소: `boyjustin76/AC-Stock-` / 브랜치 `claude/futures-youtube-video-edit-fhio4s`
- 목표: 롱폼 제작 4단계 중 [3. 모션그래픽 및 소스 넣기] 를 코드로 자동화한다. 대본 작성(1)·성우 녹음(1.5)·컷편집과 자막(2) 은 사람이 하고 이 저장소는 손대지 않는다. 숏폼은 아직 범위 밖이다
- 환경: Chromium+Playwright 프레임 캡처, ffmpeg-static 인코딩, Pretendard/Gmarket Sans/S-Core Dream/경기천년/나눔고딕

> 이 문서는 `log/worklog.db` 에서 뽑아냅니다. 고칠 때는 `log/build_worklog_db.py` 를 고치고 다시 실행하세요.

## 처음 여는 사람에게

0. **이 저장소가 맡는 범위** — 롱폼 파이프라인 4단계 중 3. 모션그래픽 및 소스 넣기. 1·2 단계와 숏폼은 아직 범위 밖 (v_scope 참고)
1. **무엇을 하는 저장소인가** — 롱폼 제작 4단계 중 [3. 모션그래픽 및 소스 넣기] 를 코드로 자동화한다. 대본 작성(1)·성우 녹음(1.5)·컷편집과 자막(2) 은 사람이 하고 이 저장소는 손대지 않는다. 숏폼은 아직 범위 밖이다
2. **어디에 무엇이 있나** — repo_file 테이블 / brand/STYLE.md / log/WORKLOG.md
3. **환경 다시 깔기** — env_tool 테이블의 install 열을 순서대로
4. **렌더 돌리기** — runbook 테이블
5. **새 대본 받으면** — next_step 테이블 1번
6. **원본 자료 위치** — drive_map 테이블
7. **대본 받고 납품까지 순서** — workflow_step 테이블
8. **렌더에 걸리는 시간** — benchmark 테이블
9. **지난 회차 대본 찾기** — script_fts MATCH '키워드' 또는 script_keyword
10. **회사 모션 문법** — motion_preset 테이블
11. **되돌릴 수 있는 시점** — checkpoint 테이블 / python3 log/save.py --list
12. **숏폼 대본 만드는 법** — shortform_rule / shortform_part / tools/shortform.py
13. **파일·폴더 이름 규칙** — naming_rule 테이블
14. **썸네일 만드는 법** — thumbnail_rule / tools/thumbnail.py

### 환경 다시 깔기

| 도구 | 버전 | 위치 | 설치 | 비고 |
|---|---|---|---|---|
| Node.js | 22.x | `/opt/node22/bin/node` | 컨테이너 기본 제공 |  |
| Playwright | ^1.56 | `node_modules/playwright` | npm install | 브라우저는 내려받지 않는다 |
| Chromium | 1194 빌드 | `/opt/pw-browsers/chromium` | 사전 설치본 사용 | capture.mjs 의 resolveChromium() 이 환경변수 CHROMIUM_PATH → 이 경로 → 기본값 순으로 찾는다 |
| ffmpeg-static | 7.0.2 | `node_modules/ffmpeg-static/ffmpeg` | npm install | libx264/prores/qtrle/libvpx-vp9 포함. Playwright 번들 ffmpeg 는 webm 만 되므로 쓰지 않는다 |
| Pretendard | 1.3.9 | `node_modules/pretendard` | npm install | 다크 테마용 |
| JetBrains Mono | 5.x | `node_modules/@fontsource/jetbrains-mono` | npm install | 숫자 표기용 |
| 브랜드 폰트 | - | `brand/fonts` | 저장소에 포함 | Gmarket Sans / S-Core Dream / 나눔고딕 / 경기천년제목 |
| SQLite | 3.45 | `파이썬 내장 sqlite3` | 설치 불필요 | 로그 DB |
| Photoshop (로컬 PC) | 2026 / 27.9.1 | `C:/Program Files/Adobe/Adobe Photoshop 2026` | 이미 설치돼 있음 | COM ProgID 'Photoshop.Application' 의 DoJavaScriptFile 로 .jsx 를 실행한다. 썸네일은 여기서 편집한다 |
| Node.js (로컬 PC) | 24.19.0 | `C:/Program Files/nodejs` | winget install OpenJS.NodeJS.LTS | 설치 후 PATH 갱신이 필요하다 |
| Python (로컬 PC) | 3.11.9 | `-` | winget install Python.Python.3.11 | log/save.py · build_worklog_db.py 실행용. PYTHONUTF8=1 필요 |
| Chromium (로컬 PC) | 151 headless shell | `%LOCALAPPDATA%/ms-playwright` | npx playwright install chromium | npm install 만으로는 브라우저가 안 받아진다 |

### 명령어

**0. 썸네일 만들기** — 롱폼 썸네일을 템플릿 규격대로 조립해 .psd 로 쓴다
```
npm run render -- --config scenes/thumb-ch11.scenes.js --all --stills 1 --out out/thumb && python3 tools/thumbnail.py '차명#11_...v1' --chart out/thumb/stills/thumb-a_t0.00s.png --sub '손익비 1:5 만드는' --main '20일선 매매법'
```
타이틀 크기는 폭(윗줄 1120 · 아랫줄 1185)에 맞춰 자동으로 잡힌다

**0. 숏폼 — 롱폼 챕터 보기** — 어느 챕터를 숏폼으로 뽑을지 고른다
```
python3 tools/shortform.py chapters 11
```
이미 만든 숏폼과 일정표에 잡힌 편까지 같이 보여 준다

**0. 숏폼 — 작성 지시서** — 챕터 하나로 숏폼을 쓰기 위한 지시서를 만든다
```
python3 tools/shortform.py brief 11 --chapter '전략 1' --no 4
```
챕터 원문 · 목표 분량 · 고정 문구 · 앞 편이 던진 질문까지 한 장에

**0. 숏폼 — 자막으로 길이 재기** — 나간 편의 실제 길이와 초당 글자수를 확인한다
```
python3 -c "import sqlite3;c=sqlite3.connect('log/worklog.db');print(*c.execute('SELECT folder,seconds,chars,cps FROM shortform_srt WHERE rerun=0 ORDER BY seconds'),sep=chr(10))"
```
자막 원본은 각 숏폼 폴더의 '소스+원본' 안에 있다

**0. 숏폼 — 이름 짓기** — 회사 규칙대로 폴더·파일 이름을 만든다
```
python3 tools/shortform.py name 11 --no 4 --title '20일선 추세추종 매매법'
```
작업 중이면 (중간) 이 붙는다. 확정본은 --final

**0. 숏폼 — 초안 검사** — 써 놓은 초안이 규칙에 맞는지 본다
```
python3 tools/shortform.py check 'scripts/shortform/차11_#4_20일선 추세추종 매매법.txt'
```
필수/권장/선택 등급으로 나온다. 권장·선택은 어겨도 된다

**0. 세이브** — 지금 상태를 되돌릴 수 있는 시점으로 굳힌다
```
python3 log/save.py "어디까지 했는지 한 줄"
```
로그를 다시 만들고 커밋·태그·푸시까지 한 번에. 태그 이름은 save/YYYY-MM-DD-HHMM (KST)

**0. 슬롯 목록 / 되돌리기** — 언제로 돌아갈 수 있는지 보고 되돌린다
```
python3 log/save.py --list   #  그 다음  git restore --source=save/<...> -- .
```
checkout 은 구경용, restore 는 실제로 되돌릴 때. restore 뒤에는 다시 save 를 한 번 한다

**0. 대본 키워드 검색** — 새 대본의 소재와 겹치는 지난 회차를 찾는다
```
python3 -c "import sqlite3;c=sqlite3.connect('log/worklog.db');print(*c.execute(\"SELECT ep,snippet(script_fts,2,'[',']','…',12) FROM script_fts WHERE script_fts MATCH '눌림목 OR 20일선' LIMIT 10\"),sep=chr(10))"
```
가중치를 보려면 script_keyword 테이블에서 keyword 로 조회한다

**0. 레퍼런스 회차의 .prproj 받기** — 확인 대상 프로젝트 파일을 내려받는다
```
python3 -c "import sqlite3;c=sqlite3.connect('log/worklog.db');print(*c.execute(\"SELECT ep,name,drive_id FROM episode_prproj WHERE kind='최종'\"),sep=chr(10))" # 그 다음 curl -sL 'https://drive.usercontent.google.com/download?id=<ID>&export=download&confirm=t' -o ep.prproj
```
gunzip -c ep.prproj > ep.xml 로 열면 된다

**0. 레퍼런스 .prproj 확인** — 프리미어 없이 편집 구성을 읽는다
```
gunzip -c 'brand/premiere/차트명가_메인프리셋(24버전).prproj' > /tmp/preset.xml && grep -o '<DisplayName>[^<]*' /tmp/preset.xml | sort | uniq -c | sort -rn
```
미디어 경로는 <ActualMediaFilePath>, 프레임레이트는 <FrameRate> 를 254016000000 으로 나눈다

**0. 컷별 병렬 렌더** — 코어 수만큼 동시에 돌려 시간을 반으로 줄인다
```
for c in cut1-pullback-entry cut2-profit-runs cut3-fear cut4-early-exit; do node src/cli.mjs --config scenes/cmg-20ma-runner.scenes.js --scene $c --out out/cmg & done; wait
```
결과물이 순차 렌더와 md5 까지 같다

**1. 설치** — 저장소를 새로 받았을 때
```
npm install && npm run setup:fonts
```
setup:fonts 는 리눅스만 필요

**2. 씬 목록** — 어떤 컷이 있는지 확인
```
node src/cli.mjs --config scenes/cmg-20ma-runner.scenes.js
```
**3. 구도 확인** — 전체 렌더 전에 스틸컷만 빠르게
```
node src/cli.mjs --config scenes/cmg-20ma-runner.scenes.js --all --stills 5
```
컷당 몇 초. 여기서 겹침을 먼저 잡는다

**4. 전체 렌더** — 컷 전부 + 이어붙인 릴
```
node src/cli.mjs --config scenes/cmg-20ma-runner.scenes.js --all --format mp4 --out out/cmg --reel
```
1080p 4컷에 약 1분 30초

**5. 한 컷만** — 고친 컷만 다시
```
node src/cli.mjs --config <config> --scene cut4-early-exit --format mp4 --out out/cmg
```
**6. 알파 오버레이** — 촬영본 위에 차트만 얹을 때
```
node src/cli.mjs --config scenes/nq-overlay.scenes.js --all --format alpha
```
theme.transparent 가 true 여야 한다

**7. 프레임 수 확인** — 타임코드와 맞는지 검증
```
ffmpeg -i <file> -map 0:v:0 -f null - 2>&1 | tail -3
```
ffmpeg 는 node -e "console.log(require('ffmpeg-static'))" 경로

**8. 드라이브 폴더 목록** — 공유 폴더 안을 보기 (인증 없이 됨)
```
curl -sSL 'https://drive.google.com/embeddedfolderview?id=<FOLDER_ID>#list'
```
flip-entry 클래스에서 파일 id 와 이름을 뽑는다

**9. 드라이브 파일 받기** — 공유 링크 파일을 컨테이너로
```
curl -sSL -o out.bin 'https://drive.usercontent.google.com/download?id=<FILE_ID>&export=download&confirm=t'
```
대용량도 confirm=t 로 한 번에 받아진다

**10. 로그 갱신** — 작업 로그 다시 뽑기
```
python3 log/build_worklog_db.py --md && python3 log/build_worklog_page.py
```
DB 가 원본이다

**11. 썸네일 (로컬 윈도우)** — 포토샵으로 템플릿 .psd 를 직접 편집
```
node src/cli.mjs --config scenes/thumb-ch11-A.scenes.js --all --stills 1  →  차트 png 를 config.json 의 chartDir 로 복사  →  .\tools\photoshop\run.ps1 build_thumb
```
경로와 문구는 tools/photoshop/config.json 에서 고친다. 포토샵이 있어야 한다 — 리눅스 컨테이너에서는 tools/thumbnail_png.py 나 psdedit.py 를 쓴다

**12. 로그 갱신 (윈도우)** — 윈도우에서 DB·MD·HTML 다시 뽑기
```
$env:PYTHONUTF8='1'; python log/build_worklog_db.py --md; python log/build_worklog_page.py; python log/build_readme.py
```
PYTHONUTF8 없이는 한글 경로에서 cp949 로 죽는다. --print 는 out/ 이 없으면 요약 단계에서 터지니 빼고 쓴다

**13. 썸네일 규칙 다시 뽑기** — 새 회차를 만들기 전에 완성본 열 장을 다 본다
```
.\tools\photoshop\run.ps1 dump_episodes
```
회차 하나만 보고 따라 하면 그 회차를 베낀 것이 된다. outDir/ref/ep00~09.jpg 와 ref_tree.txt 가 나온다

**14. 레이어 효과 값 읽기** — 템플릿에 실제로 걸린 fx 를 값으로
```
.\tools\photoshop\run.ps1 dump_layer_fx
```
DOM 에는 레이어 효과를 읽는 길이 없다. executeActionGet 으로 layerEffects 를 직접 뜯는다


### 파일 지도

| 경로 | 역할 | 설명 |
|---|---|---|
| `.gitignore` | 기타 |  |
| `CLAUDE.md` | 기타 |  |
| `log/build_readme.py` | 기타 |  |
| `log/save.py` | 기타 |  |
| `package-lock.json` | 기타 |  |
| `log/worklog.db` | 데이터 | 작업 로그 원본 (SQLite) |
| `src/tools/exp-capture.mjs` | 도구 | 캡처 경로 4가지를 실전 루프로 재고 픽셀·mp4 md5 동일성을 대조한다 |
| `src/tools/profile-render.mjs` | 도구 | 한 프레임이 어디에 시간을 쓰는지 쪼개서 잰다 |
| `tools` | 도구 | 숏폼 대본 규칙(shortform.py) 등 대본·자료용 스크립트 |
| `tools/photoshop` | 도구 | 포토샵 COM+ExtendScript 로 템플릿 .psd 를 직접 편집한다 — 썸네일은 이 경로가 최신 |
| `tools/photoshop/build_thumb.jsx` | 도구 | 회차 그룹 복제 → 차트 교체 → 타이틀 교체 → 다른 회차 제거 → .psd/.png/.jpg |
| `tools/photoshop/dump_episodes.jsx` | 도구 | 완성 회차를 한 장씩 뽑고 레이어 트리를 받아 적는다 — 규칙을 뽑을 때 |
| `tools/photoshop/dump_layer_fx.jsx` | 도구 | 레이어 효과(lfx2)를 ActionManager 로 값까지 읽는다 |
| `tools/photoshop/run.ps1` | 도구 | 포토샵을 COM 으로 띄워 .jsx 를 실행하는 드라이버 |
| `tools/psdedit.py` | 도구 | 템플릿 .psd 를 편집한다 — 그룹 복제·텍스트 교체·픽셀 교체 |
| `tools/psdwrite.py` | 도구 | .psd 를 직접 쓴다 (레이어·한글 이름·RLE) |
| `tools/thumbnail.py` | 도구 | 썸네일 조립 — 타이틀 자동 크기, 템플릿 효과 |
| `tools/thumbnail_png.py` | 도구 | 롱폼 썸네일을 .png 로 뽑는다 — 차트 한 장, 완성본 한 장 |
| `README.md` | 문서 | 렌더러 사용법 · 포맷 선택 기준 · 씬 설정 레퍼런스 |
| `brand/STYLE.md` | 문서 | 차트명가 브랜드 스펙. 색·레이아웃·폰트·스크립트 6단 구조 |
| `log/RENDER-REVIEW.md` | 문서 | 렌더 속도 리뷰 의뢰서 — 코드 지도·실측·열린 질문 |
| `log/THUMBNAIL-REVIEW.md` | 문서 | 썸네일 코드 검토 보고서 + 로컬 푸시 확인 절차 (2026-08-27) |
| `log/WORKLOG.md` | 문서 | 이 DB 에서 뽑은 작업 로그 |
| `log/worklog.html` | 문서 | 브라우저로 보는 작업 로그 |
| `deliver/thumbnail` | 산출물 | 채택된 썸네일. out/ 은 .gitignore 라 여기에 따로 둔다 |
| `scripts/shortform` | 산출물 | 숏폼 대본 초안. 규칙대로 쓴 것 |
| `package.json` | 설정 | 의존성과 npm 스크립트 |
| `tools/photoshop/config.json` | 설정 | 템플릿·차트·출력 경로와 회차 문구 |
| `log/build_worklog_db.py` | 스크립트 | 로그 DB 생성. 내용을 고칠 때 여기만 고친다 |
| `log/build_worklog_page.py` | 스크립트 | DB → HTML 페이지 |
| `src/tools/install-fonts.mjs` | 스크립트 | 폰트를 시스템에 등록 |
| `scenes/cmg-20ma-runner.scenes.js` | 씬 | 차트명가 20일선 4컷. 새 대본은 이 파일을 본떠 만든다 |
| `scenes/nq-basic.scenes.js` | 씬 | 다크 테마 NQ 6컷 (첫 버전, 브랜드 적용 전) |
| `scenes/nq-overlay.scenes.js` | 씬 | 투명 배경 오버레이 3컷 |
| `scenes/thumb-ch11-A.scenes.js` | 씬 | 차11 썸네일 A안 — 추세추종. 눌림목 매수 53번 → 완전 이격 음봉 익절 87번 |
| `scenes/thumb-ch11-B.scenes.js` | 씬 | 차11 썸네일 B안 — 박스권. 순수 range 시장(seed 7)으로 EMA20 이 화면 내내 눕는다 |
| `scenes/thumb-ch11-C.scenes.js` | 씬 | 차11 썸네일 C안 — 통합. 박스 점선 + 추세 진입/청산을 한 컷에 |
| `scenes/thumb-ch11.scenes.js` | 씬 | 차11 썸네일용 차트 2안 |
| `brand/fonts` | 애셋 | Gmarket Sans / S-Core Dream / 나눔고딕 / 경기천년제목 |
| `brand/logo` | 애셋 | 차트명가 로고 7종 |
| `brand/premiere` | 애셋 | 차트명가_메인프리셋(24버전).prproj |
| `brand/reference` | 애셋 | 레퍼런스 영상 캡처 4장. 색을 실측한 원본 |
| `brand/sfx` | 애셋 | 효과음 2종 |
| `brand/texture` | 애셋 | 종이 배경, 모눈종이·땡땡이 패턴, 점선 |
| `brand/thumbnail` | 애셋 | 템플릿에서 뽑은 로고·종이 배경 |
| `brand/ui` | 애셋 | 매수·매도 버튼, 시네마스코프, 댓글 유도 |
| `brand/thumbnail/btn_매수.png` | 에셋 | 템플릿에서 뜯은 매수 버튼 원본 픽셀 (189x90) |
| `brand/thumbnail/btn_익절.png` | 에셋 | 매수 버튼을 좌우 반전해 #00FF24 로 칠하고 익절 글자를 얹은 것 (185x90) |
| `brand/thumbnail/로고.png` | 에셋 | 템플릿 로고 원본 픽셀 (209x52) |
| `brand/thumbnail/종이배경.png` | 에셋 | 템플릿 종이 텍스처 원본 픽셀 |
| `brand/thumbnail/틀.png` | 에셋 | 템플릿 '틀' 도형 원본 픽셀 (안쪽 투명) |
| `log/data` | 자료 | 롱폼 대본 인덱스·숏폼 대본·세이브 슬롯 (JSON) |
| `src/cli.mjs` | 코어 | 렌더 CLI. --all --scene --format --stills --reel |
| `src/market/candles.js` | 코어 | 시드 고정 캔들 생성기. 추세/박스권/돌파/눌림/급등락 |
| `src/render/anim.js` | 코어 | 이징·타임라인·cue. in 을 생략하면 처음부터 떠 있는 것으로 본다 |
| `src/render/capture.mjs` | 코어 | Playwright 프레임 캡처, 크로미움 경로 탐색 |
| `src/render/chart.js` | 코어 | 캔들·이평선·축·그리드 캔버스 드로잉, 뷰포트 계산 |
| `src/render/encode.mjs` | 코어 | ffmpeg 인코딩. mp4/mov/alpha/webm/png |
| `src/render/engine.js` | 코어 | 씬 런타임. 프레임 번호를 받아 그린다 |
| `src/render/layers.js` | 코어 | 오버레이 레이어 22종. 레이어를 추가하려면 여기 |
| `src/render/scene.html` | 코어 | 렌더 스테이지. @font-face 선언이 여기 있다 |
| `src/render/server.mjs` | 코어 | 렌더용 정적 서버 |
| `src/render/theme.js` | 코어 | 테마 프리셋. dark / chartmyeongga |

## 원본 자료 (구글 드라이브)

폴더 목록: `curl -sSL 'https://drive.google.com/embeddedfolderview?id=<ID>#list'`  

파일 받기: `curl -sSL -o out 'https://drive.usercontent.google.com/download?id=<ID>&export=download&confirm=t'`

| 종류 | 이름 | Drive ID | 비고 |
|---|---|---|---|
| 폴더 | ★ 회사 전체 드라이브 루트 (트레이딩팩토리) | `1JfQCjJgMwHzyq2mpSu-OoiDEIiBpyUXH` | 여기서 다 내려간다. 01_영상_최종 아웃풋 / 02_영상_소스_롱폼 / 03_영상_소스_숏츠 / 04_영상_에셋_디자인 작업물 / 05_문서_기획+스크립트 / 07_문서_채널 관리_일정+성과분석 / 08_문서_프로젝트_툴북(DB) / 11_기타_MT5 보조지표 등 14개 |
| 폴더 | 05_썸네일 / 06_차트명가_주 1회 | `1YWaxUBaVcmUE9PwzWrYULfLjO0vpHvH9` | 롱폼 썸네일. 04_영상_에셋_디자인 작업물 → 01_영상(유튜브) 관련 → 05_썸네일 아래. 완성본 .png 11장과 템플릿 .psd 3개가 있다. 차11 은 아직 없다 |
| 템플릿 | 차트명가(롱)_하이라이트 - 복사본.psd | `1K9EkS57eVU58FtAn4dSLognffDxe8E-9` | 180MB · 1920x1080. 회차별 그룹(#1~#10) 안에 v2(차트) + 타이틀(2줄)이 들어 있고 '고정' 그룹에 틀과 로고가 있다. thumbnail_rule 이 여기서 나왔다 |
| 폴더 | 각 숏폼 폴더의 '소스+원본' (일부는 '소스'/'원본') | `1xpW_VHXA3XZQDvhURn2DthQCwP_gfwtR` | 숏폼 루트 아래 각 26XXXX_[SL_...] 폴더 안에 있다. 자막 .srt 가 여기 들어 있고, 25개 폴더 중 14개에만 있다. 초당 글자수와 단별 분량을 여기서 실측했다. 파일별 드라이브 ID 는 shortform_srt 테이블에 있다 |
| 폴더 | 03_영상_소스_숏츠 / 차트명가(숏) | `1xpW_VHXA3XZQDvhURn2DthQCwP_gfwtR` | 숏폼 대본·소스. 26XXXX_[SL_차NN_#N]제목 폴더 안에 .txt 대본이 있다. [포인트_차] 폴더는 기획형이라 롱폼 추출 규칙과 무관하다 |
| 문서 | 차트명가(유튜브)_업로드 현황(2026).xlsx | `129vEIFCHgNco6U4mUWoP_4JYOjuIQ2Ba` | 일정표. '유형' 열이 숏폼(SL)=롱폼 추출 / 숏폼(포)=기획형을 가른다. '추출 원본' 열이 롱폼↔숏폼 대응의 정답 |
| 문서 | 차트명가_숏츠 프롬프터 학습용 데이터.txt | `1zpwz-xtFvHup2EhtXpP4vbW3xOUN0LAI` | 숏폼 대본 30편을 --- 로 이어붙인 모음집. 포인트 편도 섞여 있다 |
| 프로젝트 | 숏츠 기본 양식.prproj | `1Or596wJAfylN6iiL7W9bvK8ScFKijub9` | 숏폼 프리미어 템플릿. 1080x1920 / 30fps. 숏폼 3단계 시작할 때 여기서 실측한다 |
| 영상 | 260703_[SL_차11_#1]20일선 120%활용법(최종).mp4 | `11XeXHXJdfGqqAeG4vCPMZIApex65yc_m` | 초당 글자수 실측에 쓴 최종본. 1080x1920 / 30fps / 83.4초, 내레이션 548자 → 6.6자/초 |
| 폴더 | 02_차트명가(최종본) | `1HOplrH8GowSLJPrbxIVvVTCDEL6sUPac` | 소유 krtradingfactory@gmail.com. 완성본 영상 |
| 폴더 | └ 롱폼_매매기법(차트명가) | `11eZrZdLgp4MLABX0dNR8dKF1lfMCZmSz` | 차명#1~#10 최종본 mp4. 디자인 실측 원본 |
| 폴더 | └ 숏츠_영상(차트명가) | `1El3msCDwc3JM4toYMrVYvDQ15V2NC8RN` | 숏츠 60여 편 |
| 폴더 | 차명 회차 소스 루트 | `1hqkgml4CV9cZDyD-mJiE-aRTzAX49b3A` | 회차별 원본·프리미어·기획서 |
| 폴더 | └ [컷편집]기본 프리셋+가이드 | `14V0_LG6eakNf0H7_8WT7O4DAGO0sVTj0` | 컷편집 기준 프리셋 |
| 폴더 | └ 차명00_중간 광고+아웃트로 | `1kU0Oa5iGPgNbHL67wwA0QZryjDw_w8_g` |  |
| 폴더 | └ 차명01_쿠리마기_지수 이평선 | `1r95SHLu_l-X-IcQIkldAEMl0zgqOEIOr` |  |
| 폴더 | └ 차명06_지지와 저항 | `1L-mB1A4G7CQcqzv4XtL_VCJBTL4FERjB` |  |
| 폴더 | └ 차명11_20일선의 비밀 | `1AMis7v5zu0l0oxYpSN6v5knLGOUYa2q1` | 지금 작업 중인 회차 |
| 폴더 |   └ 소스 | `180LPp4FBAmbTo3Vl9DG56PUstPh3QEGU` |  |
| 폴더 |   └ 원본 | `1Iw6D1rQ5ONIxP4cJa7H1alS6eneW_EjK` |  |
| 폴더 |   └ [차명11_최종]프리미어 프로 | `1mFChRJUIUAFSc1Ceo2BZajwtsok9z9fp` |  |
| 폴더 |   └ [차명11_컷편집]프리미어 프로 | `1Th5RFpxrQR8dN1huZFhOr5Nz5ZhzQCkH` |  |
| 문서 | [차11_20일선의 비밀] 기획서+스크립트 docx | `1vMJf7EYysVMFv3Sa8bhS8iu7eZ0GX-hj` | 이번 대본 4줄의 출처. 전략1·2 전문 포함 |
| 문서 | [차11_20일선의 비밀] 기획서+스크립트 pdf | `16zA0W88DaAfBO1h4j_73__5Jd9Cf21JP` |  |
| 문서 | [차XX_기본폼] 롱폼 기획서+스크립트 docx | `1y7rP69dRYtM1IotFjmyAREiSIB689130` | 스크립트 6단 구조 원본 |
| 파일 | 차트명가_메인프리셋(24버전).prproj | `1Udh6JHEBXO-XkfyJGtpFT_bAzoZEdmyD` | brand/premiere 에 사본 있음 |
| 압축 | 00_메인 프리셋(차트명가) 422MB | `1bfxw8NubZr42brF5kIuRUcsYL-S0mJ4f` | 해제 765MB/76파일. 가벼운 것만 brand/ 로 커밋 |
| 영상 | 차명#1_쿠리마기_EMA+박스권(최종) | `1Fuhxm4hwSCULvf8wAFlHHZBFZyBf5vcb` | 매수 태그·익절손절 영역 실측에 쓴 영상 |
| 영상 | 차명#6_지지와 저항(최종) | `18WxhXSFxdjM5foQ4PuqmhiQ-Gq_wu1BN` |  |
| 영상 | 260711_[SL_차11_#3] 20일선이 중요한 이유 | `1_wTyqenNmieugt3zEOXaoMKLO9LxCcEy` | 숏츠 룩 참고 |
| 영상 | 260703_[SL_차11_#1] 20일선 120%활용법 | `11XeXHXJdfGqqAeG4vCPMZIApex65yc_m` |  |

## 컷을 짤 때 쓰는 재료

### 레이어 22종

| 이름 | 계열 | 쓰임 | 주요 옵션 |
|---|---|---|---|
| `titleCard` | 공통 | 전체 화면 타이틀 카드 | kicker, title(배열이면 여러 줄), subtitle, size, in, out |
| `caption` | 공통 | 하단 자막 · 로어서드 | title, text, accent, in, out |
| `hud` | 공통 | 좌상단 종목 / 현재가 / 등락 | symbol, name, tf, basePrice |
| `hline` | 공통 | 수평 가격선 + 라벨 | price, label, color, priceTag, dash, growDur |
| `zone` | 공통 | 가격 밴드 | from, to, label, color, opacity |
| `marker` | 공통 | 삼각형 진입 마커 + 펄스 | bar, dir, price, label, pulse |
| `tradeBox` | 공통 | 손절·익절 박스와 손익비 | entry, tp, sl, fromBar, toBar, showRR |
| `counter` | 공통 | 숫자 카운트업 패널 | label, from, to, prefix, suffix, signed, panel, align |
| `statCard` | 공통 | 결과 요약 카드 | title, badge, rows[{k,v,tone}] |
| `label` | 공통 | 지시선 달린 자유 라벨 | bar, price, text, dx, dy |
| `cmgProfit` | 차트명가 | 진입가와 현재가 사이 평가손익 영역 | entry, fromBar, pulse, pulseSpeed, pulseAmount |
| `cmgLevel` | 차트명가 | 익절·손절 굵은 선 + 컬러 박스 라벨 | price, fillTo, fill, color, label, labelSize, thickness, fromBar, labelStyle('inzone' 은 변형) |
| `cmgArrow` | 차트명가 | 매수·매도 화살표 태그 | bar, price, dir('buy'|'sell'), label, size(기본 36), gap, popDur(0이면 등장 연출 없음), halo |
| `cmgBadge` | 차트명가 | 브랜드 배지 (손익비·종목 등) | text, x, y, size, color, align, border |
| `cmgNote` | 차트명가 | 차트 위 외곽선 주석 | text, bar, price, x, y, size, color |
| `cmgCircle` | 차트명가 | 손그림 색연필 원 강조 | bar, price, rx, ry, width, drawDur, turns |
| `cmgUnderline` | 차트명가 | 손그림 빨간 밑줄 | bar, price, dy, width, align, thickness, drawDur |
| `cmgMissed` | 차트명가 | 놓친 구간 빗금 + 화살표 | from, to, fromBar, color, arrow(false 로 화살표 끔), arrowFrac |
| `image` | 공통 | 이미지 (로고 등). engine 이 미리 로드 | src, x, y, width, align, opacity |
| `flash` | 공통 | 컷 전환용 플래시 | at, dur, strength, color |
| `watermark` | 공통 | 채널명 워터마크 | text, x, y, opacity, align |
| `letterbox` | 공통 | 상하 시네마 레터박스 | height, color |

### 씬 설정 키

| 그룹 | 키 | 뜻 | 예 |
|---|---|---|---|
| scene | `duration` | 컷 길이(초). 프레임 수 / fps 로 넣는다 | `f(250) = 250*1001/60000` |
| scene | `fadeIn / fadeOut` | 컷 안에서의 페이드. 이어지는 컷에는 쓰지 않는다 | `0.3` |
| scene | `camera.shake` | 화면 흔들림 키프레임. 난수를 안 써서 다시 렌더해도 같다 | `[{t:0,v:0},{t:0.3,v:1}]` |
| chart | `reveal` | 몇 번째 캔들까지 그릴지. 키프레임을 주면 그려지는 애니메이션 | `[{t:0,v:34},{t:2.6,v:43,ease:'inOutCubic'}]` |
| chart | `zoom` | 보이는 캔들 수 배율. 1보다 작으면 더 넓게 보인다 | `[{t:0,v:1},{t:5,v:0.5}]` |
| chart | `priceOffset` | 세로 이동 | `[{t:0,v:0},{t:1.2,v:30}]` |
| chart | `visibleBars` | 한 화면에 보이는 캔들 수 | `40` |
| chart | `include` | 화면에 반드시 들어와야 하는 가격들 | `[23665]` |
| chart | `layout.rightGap` | 마지막 캔들 오른쪽으로 비워 둘 칸 수 | `6` |
| chart | `ma` | 이동평균선 | `[{type:'ema',period:20,width:5}]` |
| chart | `showGrid / showAxes / showLast` | 그리드·축·현재가 표시 여부. 차트명가는 전부 false | `false` |
| layer | `in` | [시작초, 등장시간]. 생략하면 처음부터 떠 있는 것으로 본다 | `[1.5, 0.4]` |
| layer | `out` | [시작초, 퇴장시간] | `[3.45, 0.5]` |
| project | `fps / fpsExpr` | 유리수 프레임레이트는 fpsExpr 로 정확히 넘긴다 | `60000/1001 · '60000/1001'` |
| market | `seed / segments` | 가격 이야기. seed 를 바꾸면 같은 구조의 다른 캔들 | `trend / range / breakout / pullback / spike` |

### 컷에 쓴 매매 수치

| 설정 | 종목 | seed | 캔들 | 진입 | 손절 | 익절 | 손익비 | 이후 고점 | 비고 |
|---|---|---|---|---|---|---|---|---|---|
| `cmg-20ma-runner` | 일봉 (종목 표기 없음) | 11 | 95 | 23,795.00 | 23,665.00 | 24,055.00 | 1 : 2 | 24,977.5 (9.1R) | 20일선 눌림목 진입 → 1:2 조기 익절 → 이후 추세는 9.1R 까지. 손절폭 130pt |
| `nq-basic` | NQ 5분봉 | 42 | 82 | 24,688.75 | 24,614.75 | 24,836.75 | 1 : 2 | 24,871.5 (2.4R) | 박스권 가짜 이탈 후 되돌림 롱. NQ 1계약 = 1포인트당 $20 → 148pt = $2,960 |

## 환경이 거는 제약

| 항목 | 한계 | 대응 |
|---|---|---|
| 저장소에 없는 것 | 템플릿 차트명가(롱)_하이라이트 - 복사본.psd(180MB)와 완성본 레퍼런스 PNG 10장은 저장소에 없다. out/ 도 .gitignore 라 뽑아 낸 썸네일 자체는 안 들어간다 | 셋 다 회사 드라이브에 있다 (drive_map 참고). 로컬 PC 에는 이미 있으니 문제가 안 된다. 저장소에 있는 것은 그 파일들에서 뽑아 낸 값과 픽셀이다 — thumbnail_rule · thumbnail_fx.json · brand/thumbnail/*.png |
| psd-tools 레이어 뽑기 | composite() 가 투명한 빈 그림을 주는 레이어가 많다 (꺼져 있는 그룹 안, 아트보드 문서, 복제 직후) | topil() 은 레이어에 저장된 픽셀을 그대로 준다. 효과가 필요하면 그룹을 solo() 로 켠 뒤 composite. 원본 회차 그룹은 대부분 꺼져 있어서 복제본도 꺼진 채로 나온다 — 켜지 않으면 빈 그림이다 |
| PSD 텍스트 EngineData | 스타일 구간 배열 RunArray 와 길이 배열 RunLengthArray 의 개수가 다르면 포토샵이 '프로그램 오류로 인하여 열 수 없습니다' 로 파일을 거부한다 | 글자를 바꿀 때 두 배열을 함께 손본다. 길이 합은 글자 수(문단 끝 \r 포함)와 같아야 한다. tools/psdedit.py 의 Template.check() 가 저장 전에 자동으로 잡는다 |
| 드라이브 업로드 | Google Drive MCP 는 파일 내용을 base64 로 tool 인자에 실어 보낸다 | 25MB 파일이면 인자가 3천4백만 자가 되어 한 번의 호출로 못 보낸다. 채팅 첨부(파일당 30MB)로 보내고 사람이 드라이브에 넣는다 |
| 썸네일 PSD 크기 | 템플릿을 그대로 편집하면 180MB 를 물려받는다 | 쓰지 않는 회차 그룹을 drop_group 으로 들어내고(180→41MB) 교체한 차트를 RLE 로 압축하면(41→25.5MB) 채팅으로 보낼 수 있다 |
| psd-tools 합성 | 아트보드가 있는 문서는 composite() 가 빈 화면을 준다 | 원본 템플릿도 똑같다. 회차 그룹만 따로 composite(force=True) 해서 캔버스에 얹는다 |
| psd-tools 텍스트 | 텍스트를 바꿔도 미리보기에는 예전 글자가 보인다 | 레이어에 래스터가 캐시돼 있어서다. 포토샵도 열 때 그 픽셀을 그대로 보여 준다. Template.bake_text() 가 EngineData 와 픽셀을 함께 새 글자로 바꾼다. 획·그림자는 그리지 않는다 — lfx2 가 살아 있어 포토샵이 얹어 준다 |
| 레이어 복제 | lyid(레이어 ID)를 새로 매기지 않으면 복제본이 합성에서 통째로 빠진다 | clone_group 이 최대 ID+1 부터 다시 매긴다 |
| PSD 레이어 이름 | 옛 pascal 이름 칸은 macroman 이라 한글이 안 들어간다 | 한글을 cp949 로 인코딩한 바이트를 macroman 으로 읽은 값을 넣는다. 원본도 그렇게 돼 있다. 포토샵이 읽는 진짜 이름은 luni(유니코드) 블록이다 |
| 채팅 첨부 | 파일당 30MB | 무손실 알파는 VP9 알파 webm 으로 압축해 보내고, 무손실본은 로컬에서 재생성 |
| GitHub 파일 크기 | 파일당 100MB 하드 리젝트 | 대용량 소스는 저장소에 넣지 않고 드라이브에 둔다 |
| GitHub API | api.github.com 은 프록시 차단 | MCP github 도구와 git push/pull 만 사용 |
| 비공개 저장소 | 릴리스 에셋을 curl 로 못 받음 | 드라이브 공유 링크 사용 |
| 컨테이너 | 세션이 끝나면 디스크가 사라짐 | 남길 것은 반드시 커밋. 원본 자료는 drive_map 을 보고 다시 받는다 |
| Playwright 브라우저 | 패키지가 기대하는 빌드 번호와 사전 설치본이 다를 수 있음 | resolveChromium() 이 경로를 찾아 준다. playwright install 을 돌리지 않는다 |
| 프리미어 MCP | 어시스턴트·서버·CEP 커넥터·프리미어가 모두 같은 PC 에 있어야 함 | 원격 리눅스 컨테이너에서는 쓸 수 없다. 레퍼런스 확인은 .prproj 직접 파싱으로 대체하고, 타임라인 자동 반입이 필요해지면 사용자 윈도우 PC 에 설치한다 |
| 렌더 병렬화 | 코어 수만큼만 빨라짐 (4코어에서 2.07배) | 컷 수보다 코어가 적으면 가장 긴 컷이 하한이 된다 |
| 최종본 규격 | 채널 롱폼 최종본은 1280x720 / 30fps | 컷씬 소스는 1080p / 59.94fps 로 납품. 축소는 손해가 없다 |

## 다음에 할 일

1. **새 대본 받으면** — 타임코드를 프레임으로 환산(같은 분 안이면 드롭프레임 보정 불필요) → scenes/cmg-20ma-runner.scenes.js 를 본떠 새 config 를 만들고 layers 를 채운다 → --stills 로 구도 확인 → --all --reel
2. **전략 1 컷 (아직 안 만듦)** — 기획서의 익절 기준이 '종가가 20일선을 하방 이탈하는 음봉, 아래꼬리조차 20일선에 닿지 않는 완전 이격 캔들'. 이 조건을 그대로 그리는 컷이 뒤에 필요하다  _(대기: 대본)_
3. **전략 2 컷 (아직 안 만듦)** — 박스권 횡보장 스위칭. 이평선이 눕는 것 확인 → 직전 고점 윗꼬리·저점 아랫꼬리로 라인 → 하단 지지에서 매수, 상단 저항에서 익절  _(대기: 대본)_
4. **규격 통일 여부** — 채널 최종본은 720p/30fps. 1080p/59.94 유지 중인데 다른 소스와 맞출지 결정 필요  _(대기: 사용자 판단)_
5. **로고 워터마크** — 지금은 렌더에 넣지 않음(프리미어 프리셋과 중복). 필요하면 image 레이어로 brand/logo 사용
6. **컷별 병렬 렌더 — 폐기 (2026-08-27)** — 캡처가 빨라진 뒤로는 단일 프로세스가 이미 4코어를 포화시켜 병렬 이득이 없다 (순차 26.8s = 병렬 26.8s, benchmark 17). npm run render:par 를 만들 이유가 사라졌다. 코어가 훨씬 많은 머신에서만 다시 검토한다  _(대기: 폐기)_
7. **알파(.mov) 렌더 시간 미측정** — mp4 는 956프레임에 순차 26.8초(캡처 교체 후)로 재놨는데 무손실 알파(qtrle)는 파일이 커서 I/O 가 더 붙는다. 필요해지면 따로 측정한다
8. **차명14·15 대본 미작성** — 두 회차 문서가 927자짜리 빈 템플릿이고 본문이 서로 완전히 동일하다. 레퍼런스로 쓸 수 없으니 대본이 채워지면 log/data/scripts.json 을 다시 만든다  _(대기: 사용자)_
9. **모션 문법 표본 부족** — motion_preset 3종은 차명11 최종본 하나에서만 뽑았다. 다른 회차 .prproj 도 같은 방식으로 훑으면 회사 표준 이징·지속시간이 더 정확해진다
10. **숏폼 화면 톤앤매너 조사** — 대본 쪽은 끝났고 화면이 남았다. 숏츠 기본 양식.prproj (drive_map) 를 뜯어 1080x1920 에서 자막·차트·라벨이 어떻게 배치되는지 실측하면 숏폼 3단계(모션그래픽)를 시작할 수 있다
11. **롱폼 2단계(컷편집·자막) 연동** — 지금은 타임코드를 사람이 옮겨 적어 준다. .srt 를 그대로 받아 컷 경계를 자동으로 나누면 3단계 입력이 손을 안 탄다  _(대기: 사용자)_
12. **숏폼 #4·#5 초안 검토** — 차11 전략1·전략2 로 초안 두 편을 규칙대로 써 두었다 (scripts/shortform/). 팀장님이 쓰신 것과 얼마나 다른지 보면 규칙의 정확도를 알 수 있다  _(대기: 사용자)_
13. **숏폼 대본 규칙 검증** — 차13·차14·차15 숏폼이 나오면 규칙대로 예측해 보고 맞는지 확인한다. 지금 규칙은 차01~차12 25편에서만 뽑았다  _(대기: 새 숏폼)_
14. **썸네일 .psd — 로컬 클로드가 이어받음** — 포기가 아니라 넘긴 것이다. 포토샵이 있는 PC 에서는 파일을 직접 만들면 되니 여기서 겪은 문제(psd-tools 로 쓴 파일을 포토샵이 거부)가 애초에 생기지 않는다. 여기서 잡은 것: EngineData 의 RunArray/RunLengthArray 짝, lyid 중복, macroman 이름칸. 못 잡은 것: 그 셋을 다 고친 뒤에도 열리지 않은 이유  _(대기: 넘김 — 로컬)_
15. **썸네일 인물** — 차11 은 인물이 없는 회차라 비워 뒀다. 템플릿 '그룹 1' 이 인물 자리다 (#1 은 쿠라마기 그림이 거기 들어 있다)  _(대기: 넘김 — 로컬)_
16. **렌더 속도 — 적용 완료 (2026-08-27)** — 잰 병목 두 곳을 그대로 실행했다. 캡처를 canvas.toDataURL 로 바꿔 93s → 26.8s (md5 동일 증명), 인코딩은 --preset 으로 열어 medium 이면 24.1s. 남은 여지는 WebCodecs 로 브라우저 안에서 h264 를 직접 뽑는 것 정도인데, baseline 프로파일 제약이 있어 화질 요건과 안 맞는다. benchmark 10~17번이 근거다  _(대기: 완료)_
16. **차11 썸네일 마감** — A(추세추종)·C(통합) 채택. 최종 파일은 deliver/thumbnail/차11_20일선의 비밀/ 에 있다. B(박스권)는 요소가 많다는 이유로 보류 — 씬 파일과 미리보기 png 는 남겨 두었다
17. **로컬 커밋 6개 합류 (PC 켜지면 바로)** — 대화록으로 확인: 로컬은 커밋을 다 했고 푸시만 GitHub 인증(브라우저 로그인)에서 막혔다. 단 로컬이 'fast-forward 라 안전' 을 확인한 뒤 클라우드가 8커밋을 더 올려서, 지금 그 push 명령은 거부된다(non-fast-forward). force 금지. 추천: 로컬에서 git push -u origin HEAD:local/thumb-ch11 로 옆가지에 먼저 올리고, 병합은 양쪽 사정을 다 아는 클라우드 세션이 한다. 절차는 log/THUMBNAIL-REVIEW.md 0번  _(대기: 사용자)_
17. **다음 회차 썸네일** — tools/photoshop/config.json 의 group·variants 만 바꾸면 된다. 인물이 있는 회차면 base 를 #5 나 #7 로 바꾸고 '그룹 1'(인물 자리)에 이미지를 넣는다  _(대기: 회차 대본과 인물 이미지)_
18. **1세대 썸네일 도구의 타이틀 크기 계산** — tools/thumbnail.py 의 fit_size 와 psdedit 의 _fit·bake_text 가 아직 '폭에 맞춰 폰트 크기를 역산' 하는 방식이다. 완성본 실측으로 규칙이 뒤집혔으므로(글자 높이 고정·폭 자유, thumbnail_rule 4·5) 그 경로로 뽑으면 규격이 어긋난다. 포토샵이 없는 환경에서 그 도구를 다시 쓸 일이 생기면 먼저 고쳐야 한다  _(대기: 리눅스에서 썸네일을 다시 뽑아야 할 때)_

## 대본과 컷 싱크

타임코드는 29.97 드롭프레임. 59.94fps 로 렌더해서 프레임 수가 정확히 2배가 됩니다.

| 컷 | 타임코드 | 29.97 | 59.94 | 초 | 대사 |
|---|---|---|---|---|---|
| `cut1-pullback-entry` | 00;05;26;27 → 00;05;31;02 | 125f | 250f | 4.171 | 다수의 트레이더는 20일선 눌림목에서 진입하는 것까지는 성공합니다. |
| `cut2-profit-runs` | 00;05;31;02 → 00;05;34;29 | 117f | 234f | 3.904 | 하지만 막상 수익이 발생하면 추세를 끝까지 끌고 가지 못합니다. |
| `cut3-fear` | 00;05;34;29 → 00;05;37;15 | 76f | 152f | 2.536 | 확보한 수익을 다시 잃을까 두려운 나머지, |
| `cut4-early-exit` | 00;05;37;15 → 00;05;42;25 | 160f | 320f | 5.339 | 짧은 저항선이나 1:2 정도의 얕은 구간에서 기계적으로 이익을 실현해 버립니다. |

## 진행

| # | 단계 | 내용 |
|---|---|---|
| 1 | 환경 구축 | Chromium(사전설치본 사용), ffmpeg-static(libx264/prores/qtrle/vp9), Pretendard·JetBrains Mono 설치 |
| 2 | 렌더러 1차 | 프레임 번호를 받아 그리는 결정적 렌더링. 캔들 생성기·차트 드로잉·오버레이 레이어·캡처·인코딩 |
| 3 | 다크 테마 6컷 | NQ 5분봉, 하락→박스권→가짜이탈→되돌림 롱→손익비→익절, 45초 |
| 4 | 알파 오버레이 | QuickTime RLE 무손실 알파 3컷. 모서리 픽셀 RGBA(0,0,0,0) 확인 |
| 5 | 프리셋 입수 | Drive 422MB 다운로드 → 765MB/76파일. 폰트·로고·패턴·prproj 만 추림 |
| 6 | 브랜드 분석 | 레퍼런스 프레임에서 색·레이아웃 실측 → brand/STYLE.md |
| 7 | 차트명가 테마 | 흰 배경 라이트 테마, cmg* 레이어 8종 추가 |
| 8 | 20일선 4컷 | 대본 타임코드 478프레임에 맞춘 4컷 + 릴 |
| 9 | 최종본 대조 | 롱폼·숏츠 최종본 실측으로 태그 크기·영역 색·배지 보정 |
| 10 | 익절·손절 복구 | 기본 프리셋 실측값으로 되돌리고 layers.js 중복 536줄 제거 |
| 11 | 작업 로그 DB | SQLite 단일 파일로 세션 전체 정리 |
| 12 | 썸네일 방식 도출 | #1~#10 을 전부 솔로 렌더해 비교 + PSD 좌표 실측 → 고정 높이 타이틀·인물 판단·차트 핵심요소 규칙 확정 |
| 13 | 차11 썸네일 3안 | Photoshop 2026 COM + ExtendScript 로 템플릿 직접 편집. A/B/C 각 .psd(11.5MB) + .png |
| 14 | 버튼 브랜드 정합 | 매수·매도 버튼의 도형·효과·색·폰트를 brand/ui 원본과 #6·#7 fx 실측값에 맞춤 |

## 요청과 대응

**1. 해외선물 유튜브용 차트 모션그래픽 소스 영상을 만들어 달라. 일단 컷씬처럼.**
→ Playwright+ffmpeg 프레임 단위 렌더 파이프라인을 만들고, NQ 5분봉 다크 테마 6컷(45초)을 뽑았다. (mp4 6컷 + 릴 전달)

**2. 규격·종목 선택 (1080p 16:9 60fps / 나스닥). 씬 구성은 대본 주면 자율로.**
→ 씬을 선언형 설정 파일로 분리해서 대본이 오면 layers 배열만 갈아끼우게 설계했다. (scenes/*.scenes.js 구조 확정)

**3. 회사 스타일 매뉴얼 400MB를 어떻게 전달하나.**
→ 채팅 첨부 30MB 한도라 불가. Drive 공유 링크를 권했다. (Drive 링크로 결정)

**4. GitHub Release 했는데 보이나.**
→ 초안 상태 + 저장소 비공개라 에셋을 받을 수 없음을 확인하고 이유를 정리했다. (GitHub 경로 폐기)

**5. Drive 링크. 압축 풀어서 GitHub에 옮길 수 있나.**
→ 422MB 받아 풀었다(765MB/76파일). 100MB 초과 3개는 GitHub가 거부하므로 가벼운 35MB만 brand/ 로 커밋했다. (brand/ 35MB 커밋)

**6. 대본 4줄 + 타임코드. 모션그래픽만 뽑아 달라(자막은 직접 넣음).**
→ 타임코드를 프레임으로 환산(478f)해 4컷을 짜고 차트명가 테마를 새로 만들었다. (cmg 4컷 전달)

**7. 매수 버튼만 자주 깜빡인다.**
→ 프레임 단위로 재서 컷 경계마다 등장 애니메이션이 재생되는 것을 확인하고 고쳤다. (컷2~3 386프레임 중 누락 0)

**8. 최종본 폴더 보고 디자인 디테일을 더 회사스럽게.**
→ 최종본 롱폼·숏츠를 받아 프레임에서 색·크기를 실측하고 태그/영역/배지를 보정했다. (디자인 보정본 전달)

**9. 익절·손절만 이상하다. 아까 게 정답에 가까웠다.**
→ 기본 프리셋 프레임을 픽셀 단위로 재서 복구했고, layers.js 중복 정의 버그도 찾아 제거했다. (프리셋 실측값으로 복구)

**10. 지금까지 로그를 정리하고 .db 로 저장.**
→ SQLite 한 파일로 스키마를 짜서 세션 전체를 넣었다. (log/worklog.db)

**11. 매번 Opus 높은 노력으로 뽑으면 느리지 않나. Sonnet 여러 개로 팀을 쪼갤까, Opus 노력 최저로 갈까.**
→ 렌더는 모델이 아니라 Playwright+ffmpeg 의 CPU 작업이라 모델 선택과 무관함을 실측으로 보였다. 실제 지연은 판단 실패(익절/손절 회귀, layers.js 중복 정의, 매수 태그 깜빡임)에서 나왔고 병렬화로 줄지 않는다. Opus 유지 + 노력 중간, 대신 컷별 병렬 렌더와 검증 자동화를 권했다. (benchmark 테이블에 순차 93초 / 병렬 45초 기록)

**12. 작업 방식 확정: .srt 대본 → 키워드 정리 → 작업물 폴더 검색 → 레퍼런스 확정 → 확인. 확인 단계가 빡세니 프리미어 MCP(antipaster / leancoderkavy)를 받아 .prproj 를 직접 보게 하자.**
→ 두 MCP 를 클론해 요구사항을 확인했다. 어시스턴트·서버·CEP 커넥터·프리미어가 모두 같은 PC 에 있어야 한다. 이 컨테이너는 리눅스에 프리미어가 없어 붙을 대상이 없다. 대신 .prproj 가 gzip 압축 XML 이라는 것을 확인하고 직접 파싱해서 29.97·이펙트 구성·회사 드라이브 실제 경로를 뽑아냈다. (workflow_step / external_tool / prproj_fact 신설)

**13. 숏폼 폴더·파일 이름 매뉴얼. 작업 중이면 앞에 (중간).**
→ 나간 25편에 대조해 보니 폴더 규칙은 25/25, 파일 규칙은 5/25(차09·차11)만 지켰다. 최근 편들이 지킨 쪽을 새 표준으로 보고 tools/shortform.py 에 name 명령과 검사를 넣었다. (naming_rule 테이블 · 초안 2편 이름 교체)

**14. 숏폼 폴더의 '소스+원본' 안에 .srt 가 있다. 분량 규칙을 다시 잡아라. 45초가 이상적.**
→ 자막 14개를 받아 실측: 초당 6.82자, 영상 길이 중앙값 55.9초, 훅 26자/CTA 26자는 고정이고 본문만 늘고 준다. 45초 = 307자로 목표를 바꾸고 초안 두 편을 77초→47초, 71초→50초로 다시 썼다. (shortform_srt 테이블 · 목표 45초)

**15. 회사 전체 드라이브 등록. 롱폼 썸네일 2안을 .psd 로. 템플릿 거의 그대로.**
→ 템플릿 .psd(180MB) 를 psd-tools 로 뜯어 규격을 실측하고, 차11 차트를 렌더해 2안을 만들었다. 처음엔 PSD 를 직접 써서(tools/psdwrite.py) 6레이어짜리를 만들었다. (thumbnail_rule · tools/thumbnail.py · psdwrite.py)

**16. 레이어 효과 값 뽑을 수 있나. 없으면 내보내 주겠다.**
→ 뽑힌다. 32개 레이어의 fx 를 전부 값으로 읽어 log/data/thumbnail_fx.json 에 넣었다. 타이틀은 획 6px + 그림자(76%/90°/거리10/스프레드11/크기18) 두 개만 켜져 있다. 내가 13px 로 그렸던 것을 실측값으로 교정했다. (thumbnail_fx.json · 효과 교정)

**17. 레이어 구성을 템플릿과 완전 동일하게. 필요하면 MCP·토큰 받아 주겠다.**
→ 외부 도구가 필요 없는 문제였다. 템플릿을 psd-tools 로 열어 회차 그룹을 통째로 복제하고 그 안의 차트·타이틀만 바꾸는 방식으로 바꿨다(tools/psdedit.py). 구성이 100% 보존된다. (psdedit.py · PSD 25.5MB)

**18. 만든 .psd 가 포토샵에서 '프로그램 오류로 인하여 열 수 없습니다' 로 안 열린다.**
→ EngineData 의 StyleRun 이 스타일 3개 · 길이 1개로 짝이 어긋나 있었다. 글자를 바꾸면서 길이 배열만 줄이고 스타일 배열을 안 줄인 탓이다. 둘을 함께 줄이도록 고치고, 저장 전에 걸러 내는 Template.check() 를 붙였다. 타이틀 래스터도 새 글자로 구웠다(bake_text). (두 파일 다시 전달)

**19. 그래도 안 열린다. 그리고 적용한 효과가 원래 쓰는 것과 다르다. .psd 는 됐고 — ① 매수·매도 버튼이 들어간 차트 .png ② 완성된 썸네일 .png 를 버전 2개로.**
→ 버튼을 코드로 그린 것이 어긋난 원인이었다. 템플릿의 진짜 버튼 픽셀을 topil() 로 뜯어 썼다 (composite() 는 빈 그림을 주지만 topil() 은 원본 픽셀을 준다). 타이틀도 psd-tools 가 템플릿 lfx2 를 그대로 그리게 하고, 종이 텍스처 30% 겹치기도 실측대로 맞췄다. 버튼 자리는 짐작하지 않고 probe 컷으로 좌표를 찍어 읽었다. (PNG 4장 (차트 2 · 완성본 2) · tools/thumbnail_png.py)

**20. 썸네일은 이제 로컬 클로드가 한다 (포토샵이 있어 .psd 를 직접 다룬다). 너는 썸네일에서 빠지고, 같은 저장소를 쓰니 충돌만 안 나게 해라.**
→ 병렬로 나눠 쓰는 대신 썸네일 전체를 넘겼다. 한쪽만 손대면 충돌이 애초에 없다. 넘길 자료가 저장소에 다 들어가 있는지 확인하고(규격·효과값·원본 픽셀·도구·씬), 저장소에 없는 것(템플릿 .psd, 완성본 레퍼런스 PNG)이 무엇인지 적어 두었다. (썸네일 소유권 이전 · 이 컨테이너는 롱폼 3단계와 숏폼 1단계만)

**21. 템플릿 .psd 를 직접 편집해서 '#11 20일선의 비밀' 썸네일을 만들어 달라.**
→ 여기는 포토샵이 있는 로컬 PC 다. 파이썬도 Node 도 없어서 psdedit.py 는 못 돌렸고, 대신 Photoshop 2026 을 COM(Photoshop.Application.DoJavaScriptFile)으로 띄워 ExtendScript 로 템플릿을 직접 편집했다. #1 쿠라마기 그룹을 복제해 타이틀 두 줄만 바꿨다. (PSD 195MB · 라이브 텍스트와 레이어 효과 그대로 보존)

**22. #1 만 베끼니 카피캣이 됐다. #1~#10 전부 참고해서 방식만 뽑아라. 차트는 Node 를 설치해서 뽑아라.**
→ 10회차를 전부 솔로 렌더해 눈으로 비교하고 PSD 에서 좌표를 실측했다. 타이틀은 폭이 아니라 글자 높이가 고정(윗줄 141px / 아랫줄 194px)이고 폭은 자유였다 — 앞서 적어 둔 '폭을 맞춘다' 는 틀렸다. 인물 유무는 '주인공 트레이더가 있는 회차인가' 로 갈린다. 베이스를 인물 없는 #6 으로 바꿨다. Node 24.19 + Playwright 를 깔아 차트는 레포 렌더러로 뽑았다. (타이틀 규격 교정 · 베이스 #6 · thumbnail_rule 4·5 수정)

**23. A·B·C 를 차트와 노랑 타이틀까지 서로 다른 안으로. 그 다음 매수·매도 버튼 효과를 바꿔라(#6·#7 열어봐라).**
→ A 추세추종 / B 박스권 / C 통합 세 안을 씬·타이틀·후킹 전부 다르게 만들었다. B 는 seed 41 로는 EMA20 이 그려지기도 전에 추세가 시작돼 순수 range 시장(seed 7, 72봉)을 새로 만들었다. 버튼은 #6·#7 의 lfx2 를 ActionManager 로 읽어 외부 광선 하나만 켜져 있는 것을 확인하고 그대로 옮겼다. 화살촉 0.86h → 0.49h, 흰 헤일로 제거, 글씨 검정 획 제거. (PSD 3개 각 11.5MB)

**24. 버튼에 쓰는 폰트는 에스코어 드림 5 Medium 이다. SCDream1~9 다 있다.**
→ cmgArrow·cmgBadge·cmgLevel 의 글씨를 Gmarket Sans Bold → S-Core Dream 500 으로 바꿨다. 폰트가 바뀌자 advance 기준 상수(h=1.34·size, w=tw+1.15·size)가 어긋나 글씨가 화살촉을 침범해서, 잉크 박스에서 브랜드 비율을 직접 계산하도록 고쳤다. SCDream1~3 도 레포에 넣어 1~9 를 다 쓴다. (조재희 팀장(파가드AC) 확인 — A·C 채택, B 는 내용이 많아 보류)

**25. 모션그래픽 로그를 꼼꼼히 검토하고 렌더 시간을 최소화할 방안을 내라. 모델(Opus/Fable/Sonnet)·effort(low~max)·에이전트 구성(솔로/멀티)까지 포함해서.**
→ 의뢰서의 열린 질문 5개를 추측 대신 실험(exp-capture.mjs, 실전 루프 각 3회)으로 닫았다. 캡처를 canvas.toDataURL 로 교체해 전체 렌더 93s → 26.8s (픽셀·mp4 출력 md5 동일 증명), rawvideo 경로는 746ms/f 로 탈락, 병렬 렌더는 이득 소멸로 폐기, --preset/--capture 를 CLI 로 개방. encode.mjs 의 리스너 누수도 수정. (렌더 3.5배 가속 · benchmark 10~17 · decision 18)

**26. 썸네일 쪽 코드도 효율성 검토해라. 단, 작업자가 여럿이라(클라우드 A/C · 로컬 B) 조심할 것. 먼저 로컬 세션 링크가 열리는지 확인하고 맥락을 파악한 뒤 검토해라.**
→ 세션 링크는 메타데이터만 열렸다(대화 내용 열람 도구 없음). 대신 1차 자료로 확인한 결과 로컬 클로드의 커밋이 저장소 어디에도 없다 — '저장했다' 는 로컬 PC 안 얘기다. 코드 검토는 log/THUMBNAIL-REVIEW.md 에: 1세대 도구(thumbnail.py+psdwrite.py)가 지금도 실행되며 틀린 썸네일을 만든다는 것, 타이틀 캐시가 입력을 안 보는 것, 애셋 신구 이중화가 핵심. 썸네일 파일은 로컬이 기준이라 한 글자도 안 고쳤다. (검토 보고서만 · 코드 무수정 · 로컬 푸시 확인 절차 포함)

**27. 로컬 커밋을 깃허브로 옮겨라. 썸네일은 로컬이 우선이다.**
→ 푸시가 인증에 막혀 있었다(비대화형 셸이라 브라우저 로그인 불가). 사용자가 로그인해 옆가지 local/thumb-ch11 로 먼저 올린 뒤, 원격을 받아 보니 클라우드 세션이 렌더 가속 등 11커밋을 올려 놓아 갈라져 있었다. 공통 조상 0a15606 에서 병합했다. src/render/layers.js·theme.js·scene.html 은 자동 병합됐고(버튼 작업 + 검토 주석 공존), 실제 충돌은 build_worklog_db.py 와 checkpoints.json 둘뿐이었는데 둘 다 같은 자리에 서로 다른 항목을 더한 것이라 양쪽을 다 남겼다. 클라우드가 ID 를 25·26/18 로 미리 비켜 둔 덕이다. (세이브 슬롯 25개 · 강제 푸시 없이 합류)

## 문제와 해결

### 1. Playwright 브라우저 빌드 불일치  `fixed`
- 증상: 설치한 playwright 가 chromium-1234 를 찾는데 컨테이너에는 1194 만 있음
- 원인: 패키지 버전과 사전 설치 브라우저 빌드 번호가 다름
- 조치: 환경변수 → 사전 설치 경로 → 기본값 순으로 찾는 resolveChromium() 추가
- 확인: 다운로드 없이 렌더 성공

### 2. 400MB 매뉴얼 전달 경로  `worked-around`
- 증상: 채팅 첨부 30MB 한도라 올릴 수 없음
- 원인: 전송 수단의 크기 제한
- 조치: Drive 공유 링크를 받아 컨테이너에서 직접 curl 다운로드
- 확인: 422MB 정상 수신

### 3. GitHub Release 로는 못 받음  `worked-around`
- 증상: 릴리스는 보이는데 에셋을 가져올 수 없음
- 원인: 초안 상태 + 태그 없음 + 저장소 비공개, api.github.com 은 프록시 차단
- 조치: GitHub 경로를 폐기하고 Drive 로 전환. 공개 저장소 릴리스는 curl 로 받아짐을 테스트로 확인
- 확인: 원인 3가지 특정

### 4. 알파 무손실 파일 전송 실패  `worked-around`
- 증상: ov-chart.mov 38.5MB 가 30MB 한도 초과
- 원인: QuickTime RLE 무손실이라 용량이 큼
- 조치: VP9 알파 webm(3.4MB)으로 압축해 전달하고, 무손실 재생성 명령을 안내
- 확인: ProRes 4444 는 155MB 로 더 나빠서 배제

### 5. 매수 태그가 컷 경계마다 깜빡임  `fixed`
- 증상: 16초 동안 3번 사라졌다 다시 나타남. 다른 요소는 멀쩡
- 원인: 4컷 전부에 들어가는 유일한 요소라 컷마다 등장 애니메이션이 재생됨. 등장 시각을 줘도 첫 프레임이 투명해짐
- 조치: cmgArrow 에 popDur 옵션 추가(0이면 처음부터 완성 크기), cue 가 in 생략을 '이미 떠 있음'으로 처리
- 확인: 릴 956프레임 전수 측정: 컷2~3 386프레임 중 누락 0, 경계 전후 태그 폭 41~42px 일정

### 6. 색연필 원이 컷 경계에서 끊김  `fixed`
- 증상: 컷1 끝에 떠 있던 원이 컷2 첫 프레임에 사라짐
- 원인: 컷1 에만 있는 레이어인데 퇴장 시각이 없었음
- 조치: 컷 안에서 미리 페이드아웃하도록 out 시각 추가
- 확인: 경계 전후 연속 확인

### 7. 익절·손절 표기 스타일 오판  `fixed`
- 증상: 영역 한가운데 큰 글씨로 바꿨더니 회사 스타일과 멀어짐
- 원인: 최종본 한 영상의 변형을 표준으로 착각. 기본 프리셋의 컬러 박스가 표준
- 조치: 프리셋 프레임을 픽셀 단위로 재서 복구(선 23px, 박스 173x84, 흰 글씨, 선 왼쪽에 붙임)
- 확인: 프리셋 프레임과 대조

### 8. layers.js 레이어 정의 중복  `fixed`
- 증상: 고친 코드가 렌더에 반영되지 않음
- 원인: 객체 리터럴에 zone~cmgLevel 10종이 두 벌 들어가 뒤쪽(옛 코드)이 이김. 인덱스 기반 수정이 앞쪽에만 적용됨
- 조치: 중복 536줄 제거
- 확인: 정의 32개 → 22개, 중복 0

### 9. 라벨 겹침 다수  `fixed`
- 증상: 손익비 배지가 익절 라벨을, 익절 라벨이 매도 태그를 가림
- 원인: 줌아웃하면서 요소 간 거리가 좁아짐
- 조치: 배지를 좌하단으로, 라벨 박스를 선 왼쪽 바깥으로, 놓친 구간 화살표 제거
- 확인: 컷4 전 구간 스틸 확인

### 10. 복제한 회차의 차트 색이 죽음  `fixed`
- 증상: 렌더한 차트를 넣었더니 캔들과 태그가 전부 탁해졌다 (#00BF1B 가 #75947A 로)
- 원인: 회차 그룹 안의 'Black & White 823' 조정 레이어(불투명도 214/255 = 83.9%)가 켜져 있었다. 합성값을 역산하니 정확히 회색 83.9% 혼합이었다
- 조치: 복제 후 BLACKANDWHITE 조정 레이어를 끈다
- 확인: #00FF24 가 그대로 나옴

### 11. ExtendScript 에서 레이어 삭제가 막힘  `fixed`
- 증상: '삭제 명령은 현재 사용할 수 없습니다' (오류 8800)
- 원인: 템플릿 레이어에 lspf(레이어 잠금)가 걸려 있다
- 조치: 복제한 그룹을 재귀적으로 allLocked/pixelsLocked/positionLocked = false 로 푼 뒤 삭제
- 확인: 다른 회차 9개 제거 성공

### 12. 썸네일 .psd 가 180MB  `fixed`
- 증상: 회차 하나짜리 결과물인데 템플릿 크기 그대로였다
- 원인: 10회차 그룹이 전부 들어 있다
- 조치: 저장 전에 #11 을 뺀 나머지 '#' 그룹을 통째로 삭제 (psdedit.drop_group 과 같은 발상)
- 확인: 195MB → 11.5MB

### 13. 폰트를 바꾸자 버튼 여백이 어긋남  `fixed`
- 증상: S-Core Dream 으로 바꾸니 글씨 잉크(122px)가 몸통(114px)을 넘어 화살촉을 침범했다
- 원인: 버튼 크기가 advance width 기준 상수(h = 1.34·size, w = tw + 1.15·size)로 잡혀 있었다. 이 값은 Gmarket Sans 로 잰 것이라 폰트가 바뀌면 반드시 깨진다
- 조치: actualBoundingBox 로 잉크를 재서 브랜드 비율(글씨h/버튼h = 0.761, (버튼w-글씨w)/버튼h = 0.659)로 역산
- 확인: 버튼 189x90 — 컨테이너가 템플릿 픽셀에서 잰 189x90 과 같다

### 14. 윈도우에서 log 도구가 안 돌아감  `fixed`
- 증상: build_worklog_db.py 가 UnicodeDecodeError (cp949) 로 죽는다
- 원인: git 출력은 UTF-8 인데 subprocess 의 text=True 가 윈도우 기본 로케일(cp949)로 읽는다. 한글 경로가 있는 저장소라 바로 터진다
- 조치: git 을 부르는 subprocess.run 에 encoding='utf-8' 을 붙였다 (save.py 2곳, build_worklog_db.py 4곳). 파일 입출력은 PYTHONUTF8=1 로 덮는다
- 확인: 윈도우에서 db·md·html·README 4개 다 생성됨

### 15. run.ps1 이 파싱 오류로 안 뜸  `fixed`
- 증상: Unexpected token '}' — 멀쩡한 스크립트인데 PowerShell 이 거부한다
- 원인: PowerShell 5.1 은 BOM 이 없는 .ps1 을 시스템 ANSI(cp949)로 읽는다. 한글 주석의 UTF-8 바이트가 깨지면서 따옴표가 생겨 구문이 어긋난다
- 조치: run.ps1 을 UTF-8 with BOM 으로 저장
- 확인: run.ps1 build_thumb 이 3안을 그대로 다시 뽑음

## 판단과 근거

- **렌더 방식** — 실시간 재생이 아니라 프레임 번호를 받아 그린다
  - 이유: 느린 환경에서도 fps 가 정확하고, 같은 프레임을 다시 그려도 결과가 같다
- **캔들 데이터** — 실시세 대신 시드 고정 생성기
  - 이유: 대본에 맞는 가격 이야기를 만들 수 있고, 컷을 나눠 뽑아도 앞뒤가 어긋나지 않는다
  - 다시 볼 때: 실제 차트를 그대로 써야 할 때
- **프레임레이트** — 59.94fps(=29.97x2)로 렌더
  - 이유: 대본 타임코드가 드롭프레임이라 프레임 수가 정확히 2배가 되어 29.97 시퀀스에 프레임 단위로 맞는다
- **해상도** — 1080p 유지
  - 이유: 최종본 롱폼은 720p 지만 축소는 손해가 없고 확대는 손해다
  - 다시 볼 때: 다른 소스와 규격을 통일하기로 할 때
- **자막·타이틀·로고** — 렌더에 넣지 않는다
  - 이유: 프리미어 프리셋에 이미 있어 겹친다. 차트 위 라벨만 시각자료로 넣는다
- **저장소에 넣을 애셋** — 35MB 만 커밋
  - 이유: GitHub 는 파일당 100MB 를 거부하고, 대용량 바이너리는 히스토리에 영구히 남는다
- **로그 저장 형식** — SQLite 단일 파일
  - 이유: .db 한 파일로 끝나고 서버가 필요 없다. PostgreSQL/MySQL 은 서버 프로세스가 있어야 해서 요구와 맞지 않는다
- **모델 운용** — Opus 유지, 노력은 중간. 서브에이전트로 쪼개지 않는다
  - 이유: 렌더는 CPU 작업이라 모델과 무관하다. 실제 지연은 브랜드 판단·버그 진단에서 났고 그건 병렬화로 줄지 않는다. 여러 에이전트가 브랜드를 각자 해석하면 익절/손절 회귀 같은 실수가 병렬로 늘어난다
  - 다시 볼 때: 기계적 확인(스틸 겹침 검사 등)만 따로 떼어낼 때
- **렌더 병렬화** — 컷별로 프로세스를 나눠 코어 수만큼 동시 실행
  - 이유: 순차 93초가 45초로 줄고 결과물은 md5 까지 동일하다. 렌더가 결정론적이라 쪼개도 안전하다
- **레퍼런스 확인 방법** — .prproj 를 gunzip 해서 XML 을 직접 읽는다
  - 이유: 프로젝트 파일이 gzip XML 이라 프리미어도 MCP 도 필요 없다. 영상 프레임을 찍어 색을 재는 것보다 빠르고, 값이 렌더링을 거치지 않은 원본이라 더 정확하다
- **프리미어 MCP** — 이 세션에는 설치하지 않는다. 사용자 PC 용으로 보류
  - 이유: 어시스턴트·서버·CEP 커넥터·프리미어가 같은 PC 에 있어야 하는데 이 컨테이너는 리눅스에 프리미어가 없다. 클립을 타임라인에 자동 반입하는 단계가 필요해지면 사용자 윈도우 PC + Claude Desktop 에 깐다
  - 다시 볼 때: 컷 납품 자동화를 시작할 때
- **썸네일 편집 도구** — 포토샵이 있는 로컬 PC 에서는 psd-tools 대신 Photoshop 2026 을 COM 으로 띄워 ExtendScript 로 편집한다
  - 이유: 컨테이너가 psd-tools 로 쓴 .psd 를 포토샵이 끝내 거부한 문제가 여기서는 아예 생기지 않는다. 포토샵이 직접 편집하면 텍스트·효과·그룹이 전부 네이티브로 다시 그려진다. 리눅스 컨테이너에는 포토샵이 없으므로 psdedit.py·thumbnail_png.py 도 그대로 둔다
  - 다시 볼 때: 리눅스에서만 돌려야 할 때
- **복제할 베이스 회차** — #1 쿠라마기가 아니라 인물 없는 #6 지지와 저항
  - 이유: #1 하나만 참고하면 그 회차를 그대로 베낀 것이 된다. #1 은 타이틀이 가운데 정렬인 예외 회차이기도 하다. #2~#6 다섯 회차가 좌표까지 완전히 같은 표준이고, #11 은 주인공 인물이 없는 회차라 #6·#9 계열이다
- **버튼 색** — 썸네일 버튼은 brand/ui 원본값 #FF0000/#0000FF, 영상 태그는 theme.js 의 #E80001/#0200F3 을 그대로 둔다
  - 이유: STYLE.md 의 값은 영상 프레임에서 잰 것이고 썸네일 버튼은 브랜드 PNG 를 그대로 쓴다. 둘이 실제로 다르므로 theme 를 건드리지 않고 씬에서 지정한다
- **버튼을 그릴 것인가 뜯어 쓸 것인가** — 렌더러(cmgArrow)가 그린다. 단 브랜드 실측 비율을 그대로 넣는다
  - 이유: 컨테이너는 포토샵을 띄울 수 없어 brand/thumbnail/btn_*.png 를 뜯어 쓰는 쪽을 택했고 thumbnail_rule 8 에 '직접 그리지 않는다' 로 적었다. 그 방법은 픽셀이 정확한 대신 라벨이 매수·익절 두 개로 고정된다. 로컬 PC 는 포토샵이 있어 제약이 없고, 렌더러가 그리면 손절·중립 같은 다른 글자도 같은 모양으로 나오며 차트 좌표에 바로 붙는다. 실제로 그려 보니 189x90 · 화살촉 0.49h 로 템플릿 픽셀 실측값과 같았다. **썸네일은 로컬 쪽이 최신이다** — 컨테이너가 소유권을 넘겼다(request 20)
  - 다시 볼 때: 브랜드 버튼 디자인이 바뀔 때
- **버튼 크기 계산** — 폰트별 상수 대신 잉크 박스에서 브랜드 비율로 역산한다
  - 이유: 폰트를 바꿀 때마다 여백이 깨지는 것을 한 번 겪었다. 비율(0.761 / 0.659)은 브랜드 실측이라 불변이고 잉크 폭·높이만 런타임에 재면 어떤 폰트에서도 같은 모양이 나온다
- **차11 썸네일 채택안** — A(추세추종)와 C(통합) 채택, B(박스권)는 보류
  - 이유: 조재희 팀장(파가드AC) 확인 — '1번과 3번이 가장 간결하게 잘 뽑혔다, 두번째는 조금 내용이 많아 보인다'. B 는 박스 상하단 점선 두 개 + 매수 + 익절 + 누운 이평선이 한 화면에 다 들어가 요소가 가장 많다
  - 다시 볼 때: 박스권 단독 숏폼(#5) 썸네일이 따로 필요해질 때
- **프레임 캡처 경로** — page.screenshot 대신 canvas.toDataURL 로 PNG 를 뽑는다
  - 이유: 스크린샷은 컴포지터 경유라 프레임당 ~52ms, 캔버스 직접 인코드는 ~21ms 다. 세 경로(screenshot/toDataURL/getImageData)의 픽셀이 md5 까지 같고 mp4 출력도 동일함을 src/tools/exp-capture.mjs 로 증명한 뒤 바꿨다. 전체 렌더 93s → 26.8s. 예전 경로는 --capture shot 으로 남겨 뒀다

## 브랜드 스펙 (실측)

| 분류 | 항목 | 값 | 단위 | 출처 | 비고 |
|---|---|---|---|---|---|
| 차트 | 배경 | `#FFFFFF` |  | 레퍼런스 프레임 실측 | 축·그리드 없이 화면을 꽉 채움 |
| 차트 | 상승 캔들 | `#0B8C7F` |  | 레퍼런스 프레임 실측 | 딥 틸 |
| 차트 | 하락 캔들 | `#E80001` |  | 레퍼런스 프레임 실측 |  |
| 차트 | 20일 이동평균선 | `#F38808` |  | 레퍼런스 프레임 실측 | 얇은 주황 실선 |
| 매매 | 익절 선 | `#14FF35` | 23px | 기본 프리셋 실측 | 두께가 캔들보다 확실히 굵다 |
| 매매 | 익절 영역 | `#BAFDC0` |  | 최종본 실측 |  |
| 매매 | 손절 선 | `#9F0000` | 23px | 기본 프리셋 실측 |  |
| 매매 | 손절 영역 | `#FEBABA` |  | 최종본 실측 |  |
| 매매 | 익절·손절 라벨 박스 | `173x84` | px | 기본 프리셋 실측 | 각진 사각형, 선과 같은 색, 선 시작점 왼쪽에 붙임 |
| 매매 | 익절·손절 라벨 글씨 | `#FFFFFF / 62px` |  | 기본 프리셋 실측 | 검정 외곽선 없음 |
| 매매 | 매수 태그 | `#E80001` | 116x48px | 최종본 실측 | 흰 글씨, 검정 외곽선 없이 얇은 흰 헤일로 |
| 매매 | 매도 태그 | `#0200F3` | 116x48px | 최종본 실측 |  |
| 배지 | 종목·타임프레임 | `#E90054` |  | 레퍼런스 프레임 실측 | 흰 글씨, 검정 테두리 없음 |
| 배지 | 소제목 | `#8E8E8E` |  | 레퍼런스 프레임 실측 |  |
| 배지 | 타이틀 바 | `#8C535D ~ #D76D83` |  | 레퍼런스 프레임 실측 | 질감 있는 자주 그라데이션, 이탤릭 흰 글씨 |
| 강조 | 손그림 마크 | `#C0272D` | 12px | 최종본 아웃트로 | 원·밑줄·X. 색연필 질감 |
| 자막 | 하단 자막 | `검정 박스 + 흰 굵은 글씨` |  | 최종본 실측 | 편집에서 넣으므로 렌더에는 미포함 |
| 폰트 | 제목·강조 | `Gmarket Sans` |  | 프리셋 폰트 폴더 |  |
| 폰트 | 본문 | `S-Core Dream / 나눔고딕` |  | 프리셋 폰트 폴더 |  |
| 폰트 | 제목 대체 | `경기천년제목` |  | 프리셋 폰트 폴더 |  |
| 출력 | 최종본 롱폼 규격 | `1280x720 / 30fps` |  | 최종본 파일 메타 | 컷씬 소스는 1080p 로 납품 중 |
| 썸네일 버튼 | 매수 | `#FF0000` | 186x88px | brand/ui/매수 버튼(좌우).png 실측 | 화살촉 43px · 모서리 r7 · 글씨 잉크 128x67 |
| 썸네일 버튼 | 매도 | `#0000FF` | 186x88px | brand/ui/매도 버튼(좌우).png 실측 |  |
| 썸네일 버튼 | 익절 | `#00FF24` | 185x90px | #7 익절 도형 solidFill rgb(0,255,36) | 같은 도형에 색상 오버레이만 얹은 것 |
| 썸네일 버튼 | 글씨 | `S-Core Dream 5 Medium` |  | 브랜드 PNG · #7 익절 텍스트 레이어 | 흰색, 검정 외곽선 없음. 타이틀(Gmarket Sans Bold)과 다른 폰트다 |
| 썸네일 버튼 | 효과 | `외부 광선 검정 18% · 스프레드 72 · 크기 10 · 노이즈 22` |  | #6·#7 lfx2 를 ActionManager 로 읽음 | 드롭섀도우·내부 그림자·획·그레이디언트는 전부 꺼져 있다 |
| 썸네일 버튼 | 비율 | `글씨높이/버튼높이 0.761 · (버튼폭-글씨폭)/버튼높이 0.659` |  | brand/ui PNG 실측 | 글씨는 몸통 한가운데에서 화살촉 쪽으로 0.04·h. 폰트가 바뀌어도 이 비율로 역산한다 |
| 썸네일 타이틀 | 윗줄 글자 높이 | `141px 고정` | 왼쪽 x=88 · 베이스라인 y=198 | #2~#6 실측 | 폭은 1017~1306 으로 자유 |
| 썸네일 타이틀 | 아랫줄 글자 높이 | `194px 고정` | 왼쪽 x=74 · 베이스라인 y=395 | #2~#6 실측 | 폭은 1148~1583 으로 자유 |

## 렌더 산출물

| 파일 | 포맷 | 프레임 | 크기 | 비고 |
|---|---|---|---|---|
| `out/cmg/cut1-pullback-entry.mp4` | mp4 | 250 | - | 29.97 기준 125f |
| `out/cmg/cut2-profit-runs.mp4` | mp4 | 234 | - | 29.97 기준 117f |
| `out/cmg/cut3-fear.mp4` | mp4 | 152 | - | 29.97 기준 76f |
| `out/cmg/cut4-early-exit.mp4` | mp4 | 320 | - | 29.97 기준 160f |
| `out/cmg/_reel.mp4` | mp4 | 956 | - | 4컷 이어붙임, 29.97 기준 478f |
| `out/01-open.mp4` | mp4 | 420 | - |  |
| `out/02-structure.mp4` | mp4 | 450 | - |  |
| `out/03-breakdown.mp4` | mp4 | 420 | - |  |
| `out/04-entry.mp4` | mp4 | 420 | - |  |
| `out/05-tpsl.mp4` | mp4 | 450 | - |  |
| `out/06-result.mp4` | mp4 | 540 | - |  |
| `out/_reel.mp4` | mp4 | 2700 | - | 다크 6컷 릴 45초 |
| `out/ov-chart.mov` | qtrle | 300 | - | 무손실 알파. 30MB 초과라 채팅 전송 불가 |
| `out/ov-chart.webm` | vp9a | 300 | - | 전송용 압축본 |
| `out/ov-tpsl.mov` | qtrle | 300 | - |  |
| `out/ov-pnl.mov` | qtrle | 300 | - |  |

## 받아 온 자료

| 종류 | 이름 | 크기 | 처리 | 비고 |
|---|---|---|---|---|
| 압축본 | 00_메인 프리셋(차트명가).zip | 403 MB | 받아서 해제(765MB/76파일) | 기본 프리셋 일체 |
| 폴더 | 02_차트명가(최종본) | - | 목록만 조회 | 롱폼 10편 + 숏츠 60여 편 |
| 폴더 | 차명01~15 소스 | - | 목록만 조회 | 회차별 원본·프리미어·기획서 |
| 영상 | 차명#1_쿠리마기_EMA+박스권(최종).mp4 | 254 MB | 프레임 실측용 | 1280x720/30fps, 7분15초 |
| 영상 | 260711_[SL_차11_#3]20일선이 중요한 이유(최종).mp4 | 79 MB | 프레임 실측용 | 숏츠 1080x1920 |
| 영상 | 260703_[SL_차11_#1]20일선 120%활용법(최종).mp4 | 54 MB | 프레임 실측용 | 숏츠 |
| 문서 | [차11_20일선의 비밀]_롱폼 기획서+스크립트.docx | 0 MB | 본문 추출 | 이번 대본 4줄의 출처 |
| 저장소 | brand/ (폰트·로고·패턴·prproj·레퍼런스) | 35 MB | 커밋됨 | 100MB 초과 3개와 BGM·인트로 영상은 제외 |

## 커밋

| # | sha | 제목 | 변경 |
|---|---|---|---|
| 1 | `6604e0b5` | 차트 컷씬 렌더러 추가 — 해외선물 유튜브용 모션그래픽 소스 영상 | 17파일 +2945/-0 |
| 2 | `ddc16529` | 투명 배경 오버레이 씬 세트 추가 | 1파일 +131/-0 |
| 3 | `b5301433` | README — 알파 채널 출력 용량과 포맷 선택 기준 정리 | 1파일 +9/-1 |
| 4 | `b4656021` | 차트명가 브랜드 애셋과 스타일 정리 추가 | 43파일 +114/-0 |
| 5 | `4a368e37` | 차트명가 테마와 20일선 눌림목 4컷 추가 | 8파일 +780/-12 |
| 6 | `699684f9` | 매수 태그가 컷 경계마다 다시 튀어나오던 문제 수정 | 3파일 +56/-39 |
| 7 | `373a719d` | 최종본 레퍼런스에 맞춰 디자인 디테일 보정 | 3파일 +157/-26 |
| 8 | `2f39969c` | 색연필 원을 컷1 안에서 먼저 지워 컷 경계 끊김 제거 | 1파일 +2/-0 |
| 9 | `e49d17d8` | 익절/손절 라벨을 기본 프리셋 실측값으로 복구, layers.js 중복 정의 제거 | 3파일 +28/-16 |
| 10 | `a67d11f9` | 작업 로그를 SQLite 한 파일로 정리하고 읽는 형태 두 가지를 뽑음 | 6파일 +1427/-0 |
| 11 | `00eaa635` | 로그에 복구용 정보 추가 — 환경·명령어·파일 지도·드라이브 ID·레이어 카탈로그 | 6파일 +937/-13 |
| 12 | `dbc37cab` | 로그 DB에 작업 방식·렌더 실측·prproj 파싱 결과 기록 | 6파일 +332/-7 |
| 13 | `c6566ed5` | 회차별 대본 인덱스 구축, .prproj 바이너리 파라미터 디코드 | 7파일 +1540/-10 |
| 14 | `852c0613` | 세이브 save/2026-08-27-1007 — 대본 인덱스·prproj 디코드까지 — 세이브/로드 체계 도입 | 6파일 +270/-4 |
| 15 | `d5d407a7` | 세이브 save/2026-08-27-1009 — 세이브/로드 체계 정리 — 슬롯 목록·되돌리기 안내 | 7파일 +104/-39 |
| 16 | `233f2052` | 세이브 기록 save/2026-08-27-1009 | 4파일 +11/-3 |
| 17 | `dc30b264` | 세이브 슬롯이 json에 적힌 커밋 해시를 먼저 쓰도록 수정 | 4파일 +8/-5 |
| 18 | `bdd5a32f` | 세이브 save/2026-08-27-1040 — 파이프라인 범위 명시(롱폼 3단계) · README 대시보드 자동 생성 | 9파일 +566/-146 |
| 19 | `c79d6c50` | 세이브 기록 save/2026-08-27-1040 | 5파일 +13/-4 |
| 20 | `0174bd88` | 세이브 save/2026-08-27-1137 — 숏폼 대본 추출 규칙 역설계 — 25편 분석, 규칙 17개, 도구, 초안 2편 | 12파일 +2018/-48 |
| 21 | `d9b95d47` | 세이브 기록 save/2026-08-27-1137 | 5파일 +16/-4 |
| 22 | `ae90f685` | 세이브 save/2026-08-27-1216 — 숏폼 폴더·파일 이름 규칙 반영 — (중간) 접두, 이름 생성·검사 | 11파일 +187/-7 |
| 23 | `72507179` | 세이브 기록 save/2026-08-27-1216 | 5파일 +11/-3 |
| 24 | `59619c87` | 세이브 save/2026-08-27-1251 — 숏폼 자막(.srt) 실측 반영 — 목표 45초·초당 6.82자, 초안 두 편 재작성 | 12파일 +563/-113 |
| 25 | `17c91c21` | 세이브 기록 save/2026-08-27-1251 | 5파일 +11/-3 |
| 26 | `302bcbb2` | 세이브 save/2026-08-27-1413 — 롱폼 썸네일 2안 제작 — 템플릿 실측, PSD 직접 쓰기, 회사 드라이브 루트 등록 | 15파일 +516/-9 |
| 27 | `b4d03a7c` | 세이브 기록 save/2026-08-27-1413 | 5파일 +16/-4 |
| 28 | `0524b8f7` | 세이브 save/2026-08-27-1429 — 썸네일 타이틀 효과를 템플릿 fx 실측값으로 교정 (획 6px·그림자 90°) | 7파일 +2487/-20 |
| 29 | `b52f63f8` | 세이브 기록 save/2026-08-27-1429 | 5파일 +11/-3 |
| 30 | `c678d39e` | 세이브 save/2026-08-27-1445 — 썸네일 .psd 를 템플릿 편집 방식으로 전환 — 레이어 구성 100% 보존 | 7파일 +257/-2 |
| 31 | `7328a860` | 세이브 기록 save/2026-08-27-1445 | 5파일 +11/-3 |
| 32 | `c48f1293` | 세이브 save/2026-08-27-1456 — 썸네일 PSD 25.5MB로 축소·전달, 이번 세션 전체 DB 기록 | 8파일 +119/-14 |
| 33 | `35b100c9` | 세이브 기록 save/2026-08-27-1456 | 5파일 +11/-3 |
| 34 | `dc42e803` | 썸네일 PSD 가 포토샵에서 안 열리던 원인 수정 | 7파일 +173/-19 |
| 35 | `47bab784` | 세이브 save/2026-08-27-1513 — 썸네일 PSD 포토샵 열기 오류 수정 (EngineData run 짝) + 타이틀 래스터 굽기 | 3파일 +2/-1 |
| 36 | `ea0a6947` | 세이브 기록 save/2026-08-27-1513 | 5파일 +11/-3 |
| 37 | `a377ef73` | 썸네일을 .psd 대신 .png 로 납품 — 버튼은 템플릿 원본 픽셀 사용 | 12파일 +284/-19 |
| 38 | `c808bcc9` | 세이브 save/2026-08-27-1546 — 썸네일 PNG 납품 — 템플릿 버튼 원본 픽셀 사용, .psd 접음 | 4파일 +15/-2 |
| 39 | `eb6fa0b1` | 세이브 기록 save/2026-08-27-1546 | 5파일 +11/-3 |
| 40 | `0dd9de20` | 썸네일(롱폼 2.5)을 로컬 클로드에게 넘김 | 10파일 +52/-44 |
| 41 | `e7707db9` | 세이브 save/2026-08-27-1556 — 썸네일을 로컬 클로드에게 넘김 — 이 컨테이너는 롱폼 3단계·숏폼 1단계만 | 3파일 +2/-1 |
| 42 | `0a156068` | 세이브 기록 save/2026-08-27-1556 | 5파일 +11/-3 |
| 43 | `83bd01ac` | 세이브 save/2026-08-27-1738 — 차11 썸네일 A·C 확정 — 포토샵 COM 편집, 버튼을 브랜드 실측 비율+에스코어드림5로 | 15파일 +433/-55 |
| 44 | `f1d98d77` | 세이브 기록 save/2026-08-27-1738 | 5파일 +18/-4 |
| 45 | `966df8ff` | 세이브 save/2026-08-27-1753 — 썸네일 도구 고정 — tools/photoshop(JSX+드라이버) 추가, 채택안 A·C 를 deliver/ 에 | 15파일 +689/-9 |
| 46 | `0e0e72a2` | 세이브 기록 save/2026-08-27-1753 | 5파일 +14/-4 |
| 47 | `72f79d56` | 세이브 save/2026-08-27-1756 — 파일 지도 정리 — tools/photoshop 항목이 넓은 tools 키에 먹히던 것 | 5파일 +21/-8 |
| 48 | `0652cac4` | 세이브 기록 save/2026-08-27-1756 | 5파일 +11/-3 |
