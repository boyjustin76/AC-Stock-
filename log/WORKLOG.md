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


### 파일 지도

| 경로 | 역할 | 설명 |
|---|---|---|
| `.gitignore` | 기타 |  |
| `CLAUDE.md` | 기타 |  |
| `log/build_readme.py` | 기타 |  |
| `log/save.py` | 기타 |  |
| `package-lock.json` | 기타 |  |
| `log/worklog.db` | 데이터 | 작업 로그 원본 (SQLite) |
| `tools` | 도구 | 숏폼 대본 규칙(shortform.py) 등 대본·자료용 스크립트 |
| `tools/psdedit.py` | 도구 | 템플릿 .psd 를 편집한다 — 그룹 복제·텍스트 교체·픽셀 교체 |
| `tools/psdwrite.py` | 도구 | .psd 를 직접 쓴다 (레이어·한글 이름·RLE) |
| `tools/thumbnail.py` | 도구 | 썸네일 조립 — 타이틀 자동 크기, 템플릿 효과 |
| `README.md` | 문서 | 렌더러 사용법 · 포맷 선택 기준 · 씬 설정 레퍼런스 |
| `brand/STYLE.md` | 문서 | 차트명가 브랜드 스펙. 색·레이아웃·폰트·스크립트 6단 구조 |
| `log/WORKLOG.md` | 문서 | 이 DB 에서 뽑은 작업 로그 |
| `log/worklog.html` | 문서 | 브라우저로 보는 작업 로그 |
| `scripts/shortform` | 산출물 | 숏폼 대본 초안. 규칙대로 쓴 것 |
| `package.json` | 설정 | 의존성과 npm 스크립트 |
| `log/build_worklog_db.py` | 스크립트 | 로그 DB 생성. 내용을 고칠 때 여기만 고친다 |
| `log/build_worklog_page.py` | 스크립트 | DB → HTML 페이지 |
| `src/tools/install-fonts.mjs` | 스크립트 | 폰트를 시스템에 등록 |
| `scenes/cmg-20ma-runner.scenes.js` | 씬 | 차트명가 20일선 4컷. 새 대본은 이 파일을 본떠 만든다 |
| `scenes/nq-basic.scenes.js` | 씬 | 다크 테마 NQ 6컷 (첫 버전, 브랜드 적용 전) |
| `scenes/nq-overlay.scenes.js` | 씬 | 투명 배경 오버레이 3컷 |
| `scenes/thumb-ch11.scenes.js` | 씬 | 차11 썸네일용 차트 2안 |
| `brand/fonts` | 애셋 | Gmarket Sans / S-Core Dream / 나눔고딕 / 경기천년제목 |
| `brand/logo` | 애셋 | 차트명가 로고 7종 |
| `brand/premiere` | 애셋 | 차트명가_메인프리셋(24버전).prproj |
| `brand/reference` | 애셋 | 레퍼런스 영상 캡처 4장. 색을 실측한 원본 |
| `brand/sfx` | 애셋 | 효과음 2종 |
| `brand/texture` | 애셋 | 종이 배경, 모눈종이·땡땡이 패턴, 점선 |
| `brand/thumbnail` | 애셋 | 템플릿에서 뽑은 로고·종이 배경 |
| `brand/ui` | 애셋 | 매수·매도 버튼, 시네마스코프, 댓글 유도 |
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
6. **컷별 병렬 렌더 스크립트** — 지금은 셸에서 손으로 백그라운드를 띄운다. npm run render:par 로 코어 수만큼 자동 샤딩하게 만들면 매번 절반 시간에 끝난다  _(대기: 사용자 승인)_
7. **알파(.mov) 렌더 시간 미측정** — mp4 는 956프레임에 순차 93초/병렬 45초로 쟀는데 무손실 알파(qtrle)는 파일이 커서 I/O 가 더 붙는다. 필요해지면 따로 측정한다
8. **차명14·15 대본 미작성** — 두 회차 문서가 927자짜리 빈 템플릿이고 본문이 서로 완전히 동일하다. 레퍼런스로 쓸 수 없으니 대본이 채워지면 log/data/scripts.json 을 다시 만든다  _(대기: 사용자)_
9. **모션 문법 표본 부족** — motion_preset 3종은 차명11 최종본 하나에서만 뽑았다. 다른 회차 .prproj 도 같은 방식으로 훑으면 회사 표준 이징·지속시간이 더 정확해진다
10. **숏폼 화면 톤앤매너 조사** — 대본 쪽은 끝났고 화면이 남았다. 숏츠 기본 양식.prproj (drive_map) 를 뜯어 1080x1920 에서 자막·차트·라벨이 어떻게 배치되는지 실측하면 숏폼 3단계(모션그래픽)를 시작할 수 있다
11. **롱폼 2단계(컷편집·자막) 연동** — 지금은 타임코드를 사람이 옮겨 적어 준다. .srt 를 그대로 받아 컷 경계를 자동으로 나누면 3단계 입력이 손을 안 탄다  _(대기: 사용자)_
12. **숏폼 #4·#5 초안 검토** — 차11 전략1·전략2 로 초안 두 편을 규칙대로 써 두었다 (scripts/shortform/). 팀장님이 쓰신 것과 얼마나 다른지 보면 규칙의 정확도를 알 수 있다  _(대기: 사용자)_
13. **숏폼 대본 규칙 검증** — 차13·차14·차15 숏폼이 나오면 규칙대로 예측해 보고 맞는지 확인한다. 지금 규칙은 차01~차12 25편에서만 뽑았다  _(대기: 새 숏폼)_
14. **썸네일 PSD 열어 보기** — EngineData 짝 어긋남을 고치고 타이틀 래스터도 새 글자로 구웠다. 포토샵에서 열리는지, 두 줄 간격이 붙어 보이지 않는지 확인이 필요하다  _(대기: 사용자)_
15. **썸네일 인물** — 차11 은 인물이 없는 회차라 비워 뒀다. 넣으려면 이미지를 받아야 한다. tools/thumbnail.py 의 --person 과 psdedit 의 '그룹 1' 자리가 이미 있다  _(대기: 사용자)_

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

## 렌더 산출물

| 파일 | 포맷 | 프레임 | 크기 | 비고 |
|---|---|---|---|---|
| `out/cmg/cut1-pullback-entry.mp4` | mp4 | 250 | 0.8 MB | 29.97 기준 125f |
| `out/cmg/cut2-profit-runs.mp4` | mp4 | 234 | 1.0 MB | 29.97 기준 117f |
| `out/cmg/cut3-fear.mp4` | mp4 | 152 | 1.1 MB | 29.97 기준 76f |
| `out/cmg/cut4-early-exit.mp4` | mp4 | 320 | 3.4 MB | 29.97 기준 160f |
| `out/cmg/_reel.mp4` | mp4 | 956 | 6.4 MB | 4컷 이어붙임, 29.97 기준 478f |
| `out/01-open.mp4` | mp4 | 420 | 4.4 MB |  |
| `out/02-structure.mp4` | mp4 | 450 | 4.3 MB |  |
| `out/03-breakdown.mp4` | mp4 | 420 | 4.9 MB |  |
| `out/04-entry.mp4` | mp4 | 420 | 3.7 MB |  |
| `out/05-tpsl.mp4` | mp4 | 450 | 3.6 MB |  |
| `out/06-result.mp4` | mp4 | 540 | 4.8 MB |  |
| `out/_reel.mp4` | mp4 | 2700 | 25.6 MB | 다크 6컷 릴 45초 |
| `out/ov-chart.mov` | qtrle | 300 | 38.5 MB | 무손실 알파. 30MB 초과라 채팅 전송 불가 |
| `out/ov-chart.webm` | vp9a | 300 | 3.2 MB | 전송용 압축본 |
| `out/ov-tpsl.mov` | qtrle | 300 | 17.1 MB |  |
| `out/ov-pnl.mov` | qtrle | 300 | 17.0 MB |  |

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
