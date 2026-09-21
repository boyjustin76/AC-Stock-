#!/usr/bin/env python3
"""
작업 로그를 SQLite 한 파일로 정리한다.

  python3 log/build_worklog_db.py          # log/worklog.db 새로 만듦
  python3 log/build_worklog_db.py --print  # 만들고 요약까지 출력
  python3 log/build_worklog_db.py --md     # log/WORKLOG.md 도 같이 뽑음

DB 가 원본이고 마크다운은 거기서 만들어 낸다. 내용을 고칠 때는 이 파일만 고치면 된다.

왜 SQLite 인가: .db 한 파일로 끝나고, 서버를 띄울 필요가 없고,
파이썬·프리미어 스크립팅·DB 뷰어 어디서든 그냥 열린다.
PostgreSQL/MySQL 은 서버 프로세스가 필요해서 "파일 하나" 요구에 맞지 않는다.

커밋 이력은 실행 시점의 git 에서 직접 읽어 오고,
렌더 결과 파일도 실제 디스크에서 크기를 읽는다. 나머지는 이 파일에 적어 둔 사실이다.
"""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "log" / "worklog.db"

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 작업 세션 한 건
CREATE TABLE session (
  id            INTEGER PRIMARY KEY,
  started_on    TEXT NOT NULL,
  repo          TEXT NOT NULL,
  branch        TEXT NOT NULL,
  goal          TEXT NOT NULL,
  environment   TEXT
);

-- 사용자 요청 → 대응 (대화 흐름)
CREATE TABLE request (
  id            INTEGER PRIMARY KEY,
  seq           INTEGER NOT NULL,
  asked         TEXT NOT NULL,
  did           TEXT NOT NULL,
  outcome       TEXT
);

-- 진행 단계
CREATE TABLE phase (
  id            INTEGER PRIMARY KEY,
  seq           INTEGER NOT NULL,
  title         TEXT NOT NULL,
  detail        TEXT NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('done','partial','dropped'))
);

-- 대본 (타임코드는 29.97 드롭프레임)
CREATE TABLE script_line (
  id            INTEGER PRIMARY KEY,
  project       TEXT NOT NULL,
  section       TEXT NOT NULL,
  seq           INTEGER NOT NULL,
  tc_in         TEXT NOT NULL,
  tc_out        TEXT NOT NULL,
  frames_2997   INTEGER NOT NULL,
  seconds       REAL NOT NULL,
  text          TEXT NOT NULL
);

-- 컷씬 정의
CREATE TABLE scene (
  id            INTEGER PRIMARY KEY,
  config        TEXT NOT NULL,
  scene_id      TEXT NOT NULL,
  name          TEXT NOT NULL,
  seq           INTEGER NOT NULL,
  fps           REAL NOT NULL,
  frames        INTEGER NOT NULL,
  seconds       REAL NOT NULL,
  script_line_id INTEGER REFERENCES script_line(id),
  synopsis      TEXT,
  UNIQUE (config, scene_id)
);

-- 렌더 산출물
CREATE TABLE render (
  id            INTEGER PRIMARY KEY,
  scene_id      INTEGER REFERENCES scene(id),
  path          TEXT NOT NULL,
  format        TEXT NOT NULL,
  width         INTEGER NOT NULL,
  height        INTEGER NOT NULL,
  fps           REAL NOT NULL,
  frames        INTEGER,
  bytes         INTEGER,
  alpha         INTEGER NOT NULL DEFAULT 0,
  note          TEXT
);

-- 브랜드 스펙 (레퍼런스에서 실측한 값)
CREATE TABLE brand_token (
  id            INTEGER PRIMARY KEY,
  category      TEXT NOT NULL,
  name          TEXT NOT NULL,
  value         TEXT NOT NULL,
  unit          TEXT,
  source        TEXT NOT NULL,
  note          TEXT
);

-- 받아 온 자료
CREATE TABLE asset (
  id            INTEGER PRIMARY KEY,
  kind          TEXT NOT NULL,
  name          TEXT NOT NULL,
  drive_id      TEXT,
  bytes         INTEGER,
  stored        TEXT,
  note          TEXT
);

-- 문제와 해결
CREATE TABLE issue (
  id            INTEGER PRIMARY KEY,
  seq           INTEGER NOT NULL,
  title         TEXT NOT NULL,
  symptom       TEXT NOT NULL,
  root_cause    TEXT NOT NULL,
  fix           TEXT NOT NULL,
  verification  TEXT,
  status        TEXT NOT NULL CHECK (status IN ('fixed','worked-around','open'))
);

-- 판단과 근거
CREATE TABLE decision (
  id            INTEGER PRIMARY KEY,
  seq           INTEGER NOT NULL,
  topic         TEXT NOT NULL,
  choice        TEXT NOT NULL,
  rationale     TEXT NOT NULL,
  revisit_when  TEXT
);

-- git 커밋
CREATE TABLE commit_log (
  id            INTEGER PRIMARY KEY,
  seq           INTEGER NOT NULL,
  sha           TEXT NOT NULL UNIQUE,
  authored      TEXT NOT NULL,
  subject       TEXT NOT NULL,
  files_changed INTEGER,
  insertions    INTEGER,
  deletions     INTEGER
);


-- 저장소 파일 지도
CREATE TABLE repo_file (
  id            INTEGER PRIMARY KEY,
  path          TEXT NOT NULL UNIQUE,
  role          TEXT NOT NULL,
  note          TEXT
);

-- 실행 절차
CREATE TABLE runbook (
  id            INTEGER PRIMARY KEY,
  seq           INTEGER NOT NULL,
  topic         TEXT NOT NULL,
  purpose       TEXT NOT NULL,
  command       TEXT NOT NULL,
  note          TEXT
);

-- 환경과 도구 (컨테이너가 날아가면 이걸 보고 다시 깐다)
CREATE TABLE env_tool (
  id            INTEGER PRIMARY KEY,
  name          TEXT NOT NULL,
  version       TEXT,
  location      TEXT,
  install       TEXT NOT NULL,
  note          TEXT
);

-- 구글 드라이브 폴더/파일 지도
CREATE TABLE drive_map (
  id            INTEGER PRIMARY KEY,
  kind          TEXT NOT NULL,
  name          TEXT NOT NULL,
  drive_id      TEXT NOT NULL,
  parent        TEXT,
  note          TEXT
);

-- 오버레이 레이어 카탈로그 (새 컷을 짤 때 쓰는 재료)
CREATE TABLE layer_catalog (
  id            INTEGER PRIMARY KEY,
  name          TEXT NOT NULL UNIQUE,
  family        TEXT NOT NULL,
  purpose       TEXT NOT NULL,
  key_options   TEXT NOT NULL
);

-- 씬 설정 키
CREATE TABLE scene_option (
  id            INTEGER PRIMARY KEY,
  grp           TEXT NOT NULL,
  key           TEXT NOT NULL,
  meaning       TEXT NOT NULL,
  example       TEXT
);

-- 컷에 쓴 매매 시나리오 수치
CREATE TABLE trade_setup (
  id            INTEGER PRIMARY KEY,
  config        TEXT NOT NULL,
  instrument    TEXT NOT NULL,
  seed          INTEGER NOT NULL,
  bars          INTEGER NOT NULL,
  entry         REAL NOT NULL,
  stop          REAL NOT NULL,
  target        REAL NOT NULL,
  rr            TEXT NOT NULL,
  entry_bar     INTEGER,
  tp_bar        INTEGER,
  run_high      REAL,
  run_r         TEXT,
  note          TEXT
);

-- 환경이 거는 제약
CREATE TABLE constraint_note (
  id            INTEGER PRIMARY KEY,
  topic         TEXT NOT NULL,
  limit_value   TEXT NOT NULL,
  workaround    TEXT NOT NULL
);

-- 다음에 할 일
CREATE TABLE next_step (
  id            INTEGER PRIMARY KEY,
  seq           INTEGER NOT NULL,
  item          TEXT NOT NULL,
  detail        TEXT NOT NULL,
  blocked_by    TEXT
);

-- 렌더 속도 실측 ("프리셋 고정 후 순수 클립만 뽑는 시간")
CREATE TABLE benchmark (
  id            INTEGER PRIMARY KEY,
  measured_on   TEXT NOT NULL,
  config        TEXT NOT NULL,
  mode          TEXT NOT NULL,
  cores         INTEGER,
  frames        INTEGER NOT NULL,
  seconds_video REAL,
  wall_seconds  REAL NOT NULL,
  fps_capture   REAL,
  note          TEXT
);

-- 대본 수령부터 납품까지의 표준 작업 순서
CREATE TABLE workflow_step (
  id            INTEGER PRIMARY KEY,
  format        TEXT NOT NULL DEFAULT '롱폼',
  stage         TEXT NOT NULL DEFAULT '3. 모션그래픽 및 소스 넣기',
  seq           INTEGER NOT NULL,
  step          TEXT NOT NULL,
  how           TEXT NOT NULL,
  who           TEXT NOT NULL CHECK (who IN ('사용자','클로드','자동')),
  status        TEXT NOT NULL CHECK (status IN ('ready','partial','todo')),
  note          TEXT
);

-- 외부 도구 검토 결과 (도입 / 보류 근거)
CREATE TABLE external_tool (
  id            INTEGER PRIMARY KEY,
  name          TEXT NOT NULL,
  source        TEXT,
  purpose       TEXT NOT NULL,
  requirement   TEXT,
  verdict       TEXT NOT NULL CHECK (verdict IN ('adopt','local-only','rejected','pending')),
  reason        TEXT NOT NULL
);

-- .prproj 를 프리미어 없이 직접 뜯어서 확인한 사실
CREATE TABLE prproj_fact (
  id            INTEGER PRIMARY KEY,
  file          TEXT NOT NULL,
  topic         TEXT NOT NULL,
  finding       TEXT NOT NULL,
  method        TEXT
);

-- 회차별 대본 인덱스 (log/data/scripts.json 에서 적재)
CREATE TABLE script_doc (
  id            INTEGER PRIMARY KEY,
  ep_no         INTEGER NOT NULL,
  ep            TEXT NOT NULL,
  file          TEXT NOT NULL,
  drive_id      TEXT NOT NULL,
  chars         INTEGER NOT NULL,
  headline      TEXT,
  keywords      TEXT,
  status        TEXT NOT NULL
);

-- 대본 전문 검색 (SELECT * FROM script_fts WHERE script_fts MATCH '눌림목')
CREATE VIRTUAL TABLE script_fts USING fts5(ep, file, body, tokenize='unicode61');

-- 키워드 → 회차 역인덱스
CREATE TABLE script_keyword (
  keyword       TEXT NOT NULL,
  ep            TEXT NOT NULL,
  hits          INTEGER NOT NULL,
  PRIMARY KEY (keyword, ep)
);

-- 회차별 프리미어 프로젝트 파일 (레퍼런스 확인 대상)
CREATE TABLE episode_prproj (
  id            INTEGER PRIMARY KEY,
  ep            TEXT NOT NULL,
  name          TEXT NOT NULL,
  drive_id      TEXT NOT NULL,
  kind          TEXT NOT NULL
);

-- 프리셋·최종본에서 뽑아낸 회사 고유 모션 문법
CREATE TABLE motion_preset (
  id            INTEGER PRIMARY KEY,
  name          TEXT NOT NULL,
  param         TEXT NOT NULL,
  from_value    TEXT NOT NULL,
  to_value      TEXT NOT NULL,
  frames_2997   REAL NOT NULL,
  seconds       REAL NOT NULL,
  easing        TEXT,
  source        TEXT NOT NULL,
  note          TEXT
);

-- 영상 포맷. 롱폼과 숏폼은 규격도 톤앤매너도 다르다.
CREATE TABLE format (
  id            INTEGER PRIMARY KEY,
  name          TEXT NOT NULL UNIQUE,
  aspect        TEXT NOT NULL,
  final_spec    TEXT NOT NULL,
  source_spec   TEXT,
  length        TEXT,
  tone          TEXT,
  status        TEXT NOT NULL CHECK (status IN ('작업중','조사됨','미조사'))
);

-- 제작 파이프라인. 이 저장소가 어디를 맡는지 여기서 정한다.
CREATE TABLE pipeline_stage (
  id            INTEGER PRIMARY KEY,
  format        TEXT NOT NULL REFERENCES format(name),
  seq           TEXT NOT NULL,
  name          TEXT NOT NULL,
  detail        TEXT NOT NULL,
  owner         TEXT NOT NULL,
  in_repo       INTEGER NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('진행중','자료만','미착수','해당없음')),
  note          TEXT
);

-- 숏폼 대본 (롱폼에서 추출한 것만. '포인트' 편은 기획형이라 제외)
CREATE TABLE shortform_doc (
  id            INTEGER PRIMARY KEY,
  aired         TEXT NOT NULL,
  ep            INTEGER,
  no            INTEGER,
  folder        TEXT NOT NULL,
  file          TEXT NOT NULL,
  drive_id      TEXT NOT NULL,
  chars         INTEGER NOT NULL,
  est_sec       REAL NOT NULL,
  long_window   INTEGER,
  ngram4        REAL,
  ngram10       REAL,
  size_ratio    REAL,
  rerun         INTEGER NOT NULL DEFAULT 0
);

-- 숏폼 대본 전문 검색
CREATE VIRTUAL TABLE shortform_fts USING fts5(folder, body, tokenize='unicode61');

-- 롱폼 → 숏폼 추출 규칙. hits/total 은 기존 24편 중 몇 편이 지켰는지.
CREATE TABLE shortform_rule (
  id            INTEGER PRIMARY KEY,
  grp           TEXT NOT NULL,
  rule          TEXT NOT NULL,
  evidence      TEXT NOT NULL,
  hits          INTEGER,
  total         INTEGER,
  tier          TEXT NOT NULL CHECK (tier IN ('필수','권장','선택','수치'))
);

-- 숏폼 대본의 뼈대와 목표 분량
CREATE TABLE shortform_part (
  id            INTEGER PRIMARY KEY,
  seq           INTEGER NOT NULL,
  name          TEXT NOT NULL,
  purpose       TEXT NOT NULL,
  chars_min     INTEGER NOT NULL,
  chars_max     INTEGER NOT NULL,
  phrasing      TEXT
);

-- 일정표가 말하는 롱폼 ↔ 숏폼 대응
CREATE TABLE shortform_map (
  id            INTEGER PRIMARY KEY,
  aired         TEXT NOT NULL,
  kind          TEXT NOT NULL,
  title         TEXT NOT NULL,
  source        TEXT NOT NULL,
  ep            INTEGER
);

-- 숏폼 자막(.srt) 실측. 각 숏폼 폴더의 '소스+원본' 안에 있다.
CREATE TABLE shortform_srt (
  id            INTEGER PRIMARY KEY,
  folder        TEXT NOT NULL,
  file          TEXT NOT NULL,
  drive_id      TEXT NOT NULL,
  seconds       REAL NOT NULL,
  cues          INTEGER NOT NULL,
  chars         INTEGER NOT NULL,
  cps           REAL NOT NULL,
  hook_sec      REAL, hook_chars INTEGER,
  body_sec      REAL, body_chars INTEGER,
  cta_sec       REAL, cta_chars  INTEGER,
  rerun         INTEGER NOT NULL DEFAULT 0
);

-- 롱폼 썸네일 규격. 템플릿 .psd 와 완성본 11장에서 실측했다.
CREATE TABLE thumbnail_rule (
  id            INTEGER PRIMARY KEY,
  part          TEXT NOT NULL,
  spec          TEXT NOT NULL,
  measured      TEXT,
  note          TEXT
);

-- 폴더·파일 이름 규칙 (회사 매뉴얼)
CREATE TABLE naming_rule (
  id            INTEGER PRIMARY KEY,
  scope         TEXT NOT NULL,
  pattern       TEXT NOT NULL,
  example       TEXT NOT NULL,
  conformance   TEXT,
  note          TEXT
);

-- 세이브 슬롯 (git 태그 = 되돌릴 수 있는 시점)
CREATE TABLE checkpoint (
  id            INTEGER PRIMARY KEY,
  tag           TEXT NOT NULL UNIQUE,
  kst           TEXT NOT NULL,
  utc           TEXT NOT NULL,
  sha           TEXT,
  summary       TEXT NOT NULL
);

-- 이 저장소가 파이프라인의 어디를 맡는가
CREATE VIEW v_scope AS
SELECT p.format, p.seq, p.name,
       CASE WHEN p.in_repo THEN '← 이 저장소' ELSE '' END AS here,
       p.owner, p.status
FROM pipeline_stage p JOIN format f ON f.name = p.format
ORDER BY f.id, CAST(p.seq AS REAL);

-- 처음 여는 사람이 순서대로 읽을 것
CREATE VIEW v_start_here AS
SELECT 0 AS ord, '이 저장소가 맡는 범위' AS step,
       '롱폼 3단계(모션그래픽·소스)와 숏폼 2·3단계. 숏폼 1(대본)은 E 세션, 썸네일 2.5 는 로컬 B. 자세한 것은 v_scope' AS detail
UNION ALL
SELECT 1, '무엇을 하는 저장소인가', goal FROM session
UNION ALL SELECT 2, '어디에 무엇이 있나', 'repo_file 테이블 / brand/STYLE.md / log/WORKLOG.md'
UNION ALL SELECT 3, '환경 다시 깔기', 'env_tool 테이블의 install 열을 순서대로'
UNION ALL SELECT 4, '렌더 돌리기', 'runbook 테이블'
UNION ALL SELECT 5, '새 대본 받으면', 'next_step 테이블 1번'
UNION ALL SELECT 6, '원본 자료 위치', 'drive_map 테이블'
UNION ALL SELECT 7, '대본 받고 납품까지 순서', 'workflow_step 테이블'
UNION ALL SELECT 8, '렌더에 걸리는 시간', 'benchmark 테이블'
UNION ALL SELECT 9, '지난 회차 대본 찾기', "script_fts MATCH '키워드' 또는 script_keyword"
UNION ALL SELECT 10, '회사 모션 문법', 'motion_preset 테이블'
UNION ALL SELECT 11, '되돌릴 수 있는 시점', "checkpoint 테이블 / python3 log/save.py --list"
UNION ALL SELECT 12, '숏폼 대본 만드는 법', 'shortform_rule / shortform_part / tools/shortform.py'
UNION ALL SELECT 13, '파일·폴더 이름 규칙', 'naming_rule 테이블'\nUNION ALL SELECT 14, '썸네일 만드는 법', 'thumbnail_rule / tools/photoshop (로컬 기준)'
ORDER BY ord;

-- 컷과 대본 싱크 한눈에
CREATE VIEW v_cut_sync AS
SELECT s.seq, s.scene_id, s.name,
       l.tc_in, l.tc_out, l.frames_2997 AS frames_2997,
       s.frames AS frames_5994, ROUND(s.seconds, 3) AS seconds,
       l.text
FROM scene s
JOIN script_line l ON l.id = s.script_line_id
ORDER BY s.seq;

-- 렌더 요약
CREATE VIEW v_render_summary AS
SELECT r.format, COUNT(*) AS files,
       SUM(r.frames) AS frames,
       ROUND(SUM(r.bytes) / 1048576.0, 1) AS mb
FROM render r GROUP BY r.format ORDER BY mb DESC;

-- 진행 순서대로 훑기
CREATE VIEW v_timeline AS
SELECT 'phase'   AS kind, seq, title  AS what, detail AS detail FROM phase
UNION ALL
SELECT 'request' AS kind, seq, asked  AS what, did    AS detail FROM request
ORDER BY seq, kind;
"""

SESSION = (
    1, "2026-08-26", "boyjustin76/AC-Stock-", "claude/futures-youtube-video-edit-fhio4s",
    "롱폼 제작 4단계 중 [3. 모션그래픽 및 소스 넣기] 를 코드로 자동화한다. "
    "대본 작성(1)·성우 녹음(1.5)·컷편집과 자막(2) 은 사람이 하고 이 저장소는 손대지 않는다. 숏폼은 아직 범위 밖이다",
    "Chromium+Playwright 프레임 캡처, ffmpeg-static 인코딩, Pretendard/Gmarket Sans/S-Core Dream/경기천년/나눔고딕",
)

REQUESTS = [
    (1, "해외선물 유튜브용 차트 모션그래픽 소스 영상을 만들어 달라. 일단 컷씬처럼.",
     "Playwright+ffmpeg 프레임 단위 렌더 파이프라인을 만들고, NQ 5분봉 다크 테마 6컷(45초)을 뽑았다.",
     "mp4 6컷 + 릴 전달"),
    (2, "규격·종목 선택 (1080p 16:9 60fps / 나스닥). 씬 구성은 대본 주면 자율로.",
     "씬을 선언형 설정 파일로 분리해서 대본이 오면 layers 배열만 갈아끼우게 설계했다.",
     "scenes/*.scenes.js 구조 확정"),
    (3, "회사 스타일 매뉴얼 400MB를 어떻게 전달하나.",
     "채팅 첨부 30MB 한도라 불가. Drive 공유 링크를 권했다.",
     "Drive 링크로 결정"),
    (4, "GitHub Release 했는데 보이나.",
     "초안 상태 + 저장소 비공개라 에셋을 받을 수 없음을 확인하고 이유를 정리했다.",
     "GitHub 경로 폐기"),
    (5, "Drive 링크. 압축 풀어서 GitHub에 옮길 수 있나.",
     "422MB 받아 풀었다(765MB/76파일). 100MB 초과 3개는 GitHub가 거부하므로 가벼운 35MB만 brand/ 로 커밋했다.",
     "brand/ 35MB 커밋"),
    (6, "대본 4줄 + 타임코드. 모션그래픽만 뽑아 달라(자막은 직접 넣음).",
     "타임코드를 프레임으로 환산(478f)해 4컷을 짜고 차트명가 테마를 새로 만들었다.",
     "cmg 4컷 전달"),
    (7, "매수 버튼만 자주 깜빡인다.",
     "프레임 단위로 재서 컷 경계마다 등장 애니메이션이 재생되는 것을 확인하고 고쳤다.",
     "컷2~3 386프레임 중 누락 0"),
    (8, "최종본 폴더 보고 디자인 디테일을 더 회사스럽게.",
     "최종본 롱폼·숏츠를 받아 프레임에서 색·크기를 실측하고 태그/영역/배지를 보정했다.",
     "디자인 보정본 전달"),
    (9, "익절·손절만 이상하다. 아까 게 정답에 가까웠다.",
     "기본 프리셋 프레임을 픽셀 단위로 재서 복구했고, layers.js 중복 정의 버그도 찾아 제거했다.",
     "프리셋 실측값으로 복구"),
    (10, "지금까지 로그를 정리하고 .db 로 저장.",
     "SQLite 한 파일로 스키마를 짜서 세션 전체를 넣었다.",
     "log/worklog.db"),
    (11, "매번 Opus 높은 노력으로 뽑으면 느리지 않나. Sonnet 여러 개로 팀을 쪼갤까, Opus 노력 최저로 갈까.",
     "렌더는 모델이 아니라 Playwright+ffmpeg 의 CPU 작업이라 모델 선택과 무관함을 실측으로 보였다. "
     "실제 지연은 판단 실패(익절/손절 회귀, layers.js 중복 정의, 매수 태그 깜빡임)에서 나왔고 병렬화로 줄지 않는다. "
     "Opus 유지 + 노력 중간, 대신 컷별 병렬 렌더와 검증 자동화를 권했다.",
     "benchmark 테이블에 순차 93초 / 병렬 45초 기록"),
    (12, "작업 방식 확정: .srt 대본 → 키워드 정리 → 작업물 폴더 검색 → 레퍼런스 확정 → 확인. "
     "확인 단계가 빡세니 프리미어 MCP(antipaster / leancoderkavy)를 받아 .prproj 를 직접 보게 하자.",
     "두 MCP 를 클론해 요구사항을 확인했다. 어시스턴트·서버·CEP 커넥터·프리미어가 모두 같은 PC 에 있어야 한다. "
     "이 컨테이너는 리눅스에 프리미어가 없어 붙을 대상이 없다. "
     "대신 .prproj 가 gzip 압축 XML 이라는 것을 확인하고 직접 파싱해서 29.97·이펙트 구성·회사 드라이브 실제 경로를 뽑아냈다.",
     "workflow_step / external_tool / prproj_fact 신설"),
    (13, "숏폼 폴더·파일 이름 매뉴얼. 작업 중이면 앞에 (중간).",
     "나간 25편에 대조해 보니 폴더 규칙은 25/25, 파일 규칙은 5/25(차09·차11)만 지켰다. "
     "최근 편들이 지킨 쪽을 새 표준으로 보고 tools/shortform.py 에 name 명령과 검사를 넣었다.",
     "naming_rule 테이블 · 초안 2편 이름 교체"),
    (14, "숏폼 폴더의 '소스+원본' 안에 .srt 가 있다. 분량 규칙을 다시 잡아라. 45초가 이상적.",
     "자막 14개를 받아 실측: 초당 6.82자, 영상 길이 중앙값 55.9초, 훅 26자/CTA 26자는 고정이고 "
     "본문만 늘고 준다. 45초 = 307자로 목표를 바꾸고 초안 두 편을 77초→47초, 71초→50초로 다시 썼다.",
     "shortform_srt 테이블 · 목표 45초"),
    (15, "회사 전체 드라이브 등록. 롱폼 썸네일 2안을 .psd 로. 템플릿 거의 그대로.",
     "템플릿 .psd(180MB) 를 psd-tools 로 뜯어 규격을 실측하고, 차11 차트를 렌더해 2안을 만들었다. "
     "처음엔 PSD 를 직접 써서(tools/psdwrite.py) 6레이어짜리를 만들었다.",
     "thumbnail_rule · tools/thumbnail.py · psdwrite.py"),
    (16, "레이어 효과 값 뽑을 수 있나. 없으면 내보내 주겠다.",
     "뽑힌다. 32개 레이어의 fx 를 전부 값으로 읽어 log/data/thumbnail_fx.json 에 넣었다. "
     "타이틀은 획 6px + 그림자(76%/90°/거리10/스프레드11/크기18) 두 개만 켜져 있다. "
     "내가 13px 로 그렸던 것을 실측값으로 교정했다.",
     "thumbnail_fx.json · 효과 교정"),
    (17, "레이어 구성을 템플릿과 완전 동일하게. 필요하면 MCP·토큰 받아 주겠다.",
     "외부 도구가 필요 없는 문제였다. 템플릿을 psd-tools 로 열어 회차 그룹을 통째로 복제하고 "
     "그 안의 차트·타이틀만 바꾸는 방식으로 바꿨다(tools/psdedit.py). 구성이 100% 보존된다.",
     "psdedit.py · PSD 25.5MB"),
    (18, "만든 .psd 가 포토샵에서 '프로그램 오류로 인하여 열 수 없습니다' 로 안 열린다.",
     "EngineData 의 StyleRun 이 스타일 3개 · 길이 1개로 짝이 어긋나 있었다. 글자를 바꾸면서 "
     "길이 배열만 줄이고 스타일 배열을 안 줄인 탓이다. 둘을 함께 줄이도록 고치고, "
     "저장 전에 걸러 내는 Template.check() 를 붙였다. 타이틀 래스터도 새 글자로 구웠다(bake_text).",
     "두 파일 다시 전달"),
    (19, "그래도 안 열린다. 그리고 적용한 효과가 원래 쓰는 것과 다르다. "
     ".psd 는 됐고 — ① 매수·매도 버튼이 들어간 차트 .png ② 완성된 썸네일 .png 를 버전 2개로.",
     "버튼을 코드로 그린 것이 어긋난 원인이었다. 템플릿의 진짜 버튼 픽셀을 topil() 로 뜯어 썼다 "
     "(composite() 는 빈 그림을 주지만 topil() 은 원본 픽셀을 준다). "
     "타이틀도 psd-tools 가 템플릿 lfx2 를 그대로 그리게 하고, 종이 텍스처 30% 겹치기도 실측대로 맞췄다. "
     "버튼 자리는 짐작하지 않고 probe 컷으로 좌표를 찍어 읽었다.",
     "PNG 4장 (차트 2 · 완성본 2) · tools/thumbnail_png.py"),
    (20, "썸네일은 이제 로컬 클로드가 한다 (포토샵이 있어 .psd 를 직접 다룬다). "
     "너는 썸네일에서 빠지고, 같은 저장소를 쓰니 충돌만 안 나게 해라.",
     "병렬로 나눠 쓰는 대신 썸네일 전체를 넘겼다. 한쪽만 손대면 충돌이 애초에 없다. "
     "넘길 자료가 저장소에 다 들어가 있는지 확인하고(규격·효과값·원본 픽셀·도구·씬), "
     "저장소에 없는 것(템플릿 .psd, 완성본 레퍼런스 PNG)이 무엇인지 적어 두었다.",
     "썸네일 소유권 이전 · 이 컨테이너는 롱폼 3단계와 숏폼 1단계만"),
    (21, "템플릿 .psd 를 직접 편집해서 '#11 20일선의 비밀' 썸네일을 만들어 달라.",
     "여기는 포토샵이 있는 로컬 PC 다. 파이썬도 Node 도 없어서 psdedit.py 는 못 돌렸고, "
     "대신 Photoshop 2026 을 COM(Photoshop.Application.DoJavaScriptFile)으로 띄워 "
     "ExtendScript 로 템플릿을 직접 편집했다. #1 쿠라마기 그룹을 복제해 타이틀 두 줄만 바꿨다.",
     "PSD 195MB · 라이브 텍스트와 레이어 효과 그대로 보존"),
    (22, "#1 만 베끼니 카피캣이 됐다. #1~#10 전부 참고해서 방식만 뽑아라. 차트는 Node 를 설치해서 뽑아라.",
     "10회차를 전부 솔로 렌더해 눈으로 비교하고 PSD 에서 좌표를 실측했다. 타이틀은 폭이 아니라 "
     "글자 높이가 고정(윗줄 141px / 아랫줄 194px)이고 폭은 자유였다 — 앞서 적어 둔 '폭을 맞춘다' 는 틀렸다. "
     "인물 유무는 '주인공 트레이더가 있는 회차인가' 로 갈린다. 베이스를 인물 없는 #6 으로 바꿨다. "
     "Node 24.19 + Playwright 를 깔아 차트는 레포 렌더러로 뽑았다.",
     "타이틀 규격 교정 · 베이스 #6 · thumbnail_rule 4·5 수정"),
    (23, "A·B·C 를 차트와 노랑 타이틀까지 서로 다른 안으로. 그 다음 매수·매도 버튼 효과를 바꿔라(#6·#7 열어봐라).",
     "A 추세추종 / B 박스권 / C 통합 세 안을 씬·타이틀·후킹 전부 다르게 만들었다. B 는 seed 41 로는 "
     "EMA20 이 그려지기도 전에 추세가 시작돼 순수 range 시장(seed 7, 72봉)을 새로 만들었다. "
     "버튼은 #6·#7 의 lfx2 를 ActionManager 로 읽어 외부 광선 하나만 켜져 있는 것을 확인하고 그대로 옮겼다. "
     "화살촉 0.86h → 0.49h, 흰 헤일로 제거, 글씨 검정 획 제거.",
     "PSD 3개 각 11.5MB"),
    (24, "버튼에 쓰는 폰트는 에스코어 드림 5 Medium 이다. SCDream1~9 다 있다.",
     "cmgArrow·cmgBadge·cmgLevel 의 글씨를 Gmarket Sans Bold → S-Core Dream 500 으로 바꿨다. "
     "폰트가 바뀌자 advance 기준 상수(h=1.34·size, w=tw+1.15·size)가 어긋나 글씨가 화살촉을 침범해서, "
     "잉크 박스에서 브랜드 비율을 직접 계산하도록 고쳤다. SCDream1~3 도 레포에 넣어 1~9 를 다 쓴다.",
     "조재희 팀장(파가드AC) 확인 — A·C 채택, B 는 내용이 많아 보류"),
    # 25 부터는 이 클라우드 세션 몫 — 로컬이 미푸시 커밋에서 21~24 를 이미 썼다 (2026-08-27 대화록 확인)
    (25, "모션그래픽 로그를 꼼꼼히 검토하고 렌더 시간을 최소화할 방안을 내라. "
     "모델(Opus/Fable/Sonnet)·effort(low~max)·에이전트 구성(솔로/멀티)까지 포함해서.",
     "의뢰서의 열린 질문 5개를 추측 대신 실험(exp-capture.mjs, 실전 루프 각 3회)으로 닫았다. "
     "캡처를 canvas.toDataURL 로 교체해 전체 렌더 93s → 26.8s (픽셀·mp4 출력 md5 동일 증명), "
     "rawvideo 경로는 746ms/f 로 탈락, 병렬 렌더는 이득 소멸로 폐기, --preset/--capture 를 CLI 로 개방. "
     "encode.mjs 의 리스너 누수도 수정.",
     "렌더 3.5배 가속 · benchmark 10~17 · decision 18"),
    (26, "썸네일 쪽 코드도 효율성 검토해라. 단, 작업자가 여럿이라(클라우드 A/C · 로컬 B) 조심할 것. "
     "먼저 로컬 세션 링크가 열리는지 확인하고 맥락을 파악한 뒤 검토해라.",
     "세션 링크는 메타데이터만 열렸다(대화 내용 열람 도구 없음). 대신 1차 자료로 확인한 결과 "
     "로컬 클로드의 커밋이 저장소 어디에도 없다 — '저장했다' 는 로컬 PC 안 얘기다. "
     "코드 검토는 log/THUMBNAIL-REVIEW.md 에: 1세대 도구(thumbnail.py+psdwrite.py)가 "
     "지금도 실행되며 틀린 썸네일을 만든다는 것, 타이틀 캐시가 입력을 안 보는 것, "
     "애셋 신구 이중화가 핵심. 썸네일 파일은 로컬이 기준이라 한 글자도 안 고쳤다. "
     "[정정 2026-08-28] '커밋이 저장소에 없다' 는 검토 시점(미푸시 상태)의 관찰이다. "
     "원인은 인증 차단으로 확정됐고 로컬 커밋 6개는 전부 합류됐다 — 경위는 request 27.",
     "검토 보고서만 · 코드 무수정 · 로컬 푸시 확인 절차 포함"),
    (27, "로컬 커밋을 깃허브로 옮겨라. 썸네일은 로컬이 우선이다.",
     "푸시가 인증에 막혀 있었다(비대화형 셸이라 브라우저 로그인 불가). 사용자가 로그인해 "
     "옆가지 local/thumb-ch11 로 먼저 올린 뒤, 원격을 받아 보니 클라우드 세션이 렌더 가속 등 "
     "11커밋을 올려 놓아 갈라져 있었다. 공통 조상 0a15606 에서 병합했다. "
     "src/render/layers.js·theme.js·scene.html 은 자동 병합됐고(버튼 작업 + 검토 주석 공존), "
     "실제 충돌은 build_worklog_db.py 와 checkpoints.json 둘뿐이었는데 둘 다 같은 자리에 "
     "서로 다른 항목을 더한 것이라 양쪽을 다 남겼다. 클라우드가 ID 를 25·26/18 로 미리 비켜 둔 덕이다.",
     "세이브 슬롯 25개 · 강제 푸시 없이 합류"),
    (28, "썸네일 검토 지적 중 ③ 타이틀 캐시 무효화와 ⑤ 차11 하드코딩 config 분리를 실행해라. "
     "(①·④ 격리는 전날 승인·완료 — decision 20)",
     "thumbnail_png.py 의 회차 스펙(VERSIONS·출력 이름 '차명#11_…')을 걷어내고 로컬 JSX 와 같은 "
     "tools/photoshop/config.json 을 읽게 했다 — 두 경로의 스펙이 한 곳이 됐다. 타이틀 캐시는 "
     "meta 첫 줄의 spec 해시 비교로 무효화된다. 템플릿 .psd 가 컨테이너에 없어 타이틀 절반은 "
     "로직 단위검증(결정성·문구/템플릿 변경 감지·옛 형식 재생성 판정), 차트 절반은 probe 렌더부터 "
     "합성까지 실제 실행으로 검증했다. 부수 발견: README 는 build_readme.py 가 재생성하는 "
     "파일이라 어제 README 에 직접 고친 렌더 속도 문단(병렬 루프 권장)이 옛날로 돌아가 있었다 — "
     "생성기를 v2 실측(serial-v2 26.8s·medium 24.1s·병렬 이득 소멸)으로 고쳐 재발을 막았다.",
     "decision 21 · 검토 지적 ③·⑤ 처리 · README 생성기 정정"),
    (29, "프리미어 직접 편집(파이프라인 2단계)을 로컬 실험으로 뚫어 보자. 새 로컬 세션 D 를 만들 테니 "
     "실험 매뉴얼을 써 달라. 클립 생성 방식(구)은 백업으로 유지. 로컬의 포토샵 실험 기록 전문을 먼저 읽어라.",
     "로컬 보고서를 반영해 검토를 수정했다 — MCP 보다 COM+ExtendScript 를 먼저(설치·보안 검토 없이 "
     "포토샵에서 검증된 경로), prproj_fact 는 21건이 아니라 12건(내 착각 정정). 로컬이 지시한 DB 기록 "
     "(thumbnail_rule 22~25 · issue 16~17 · runbook 17 · repo_file)을 넣고, D 매뉴얼을 "
     "log/PREMIERE-LAB-MANUAL.md 로 작성했다 — 경로·사용자 작업·마일스톤 M1~M4·이중값 함정·"
     "되읽기 검증·병합 프로토콜(D 는 이 DB 를 건드리지 않는다)·금지 목록.",
     "log/PREMIERE-LAB-MANUAL.md · next_step 21"),
    (30, "로컬(B)의 문자 단위 강조 푸시(f841107)를 받아라. config.json 은 로컬 것이 상위집합. "
     "당부: emphasis 가 붙은 안에는 scene·tags 를 달지 마라 — 컨테이너가 강조 빠진 그림을 같은 id 로 만든다.",
     "ff-only 로 합류했다. config 검증 결과 A 의 scene·tags 생존, A2·C2 는 emphasis 만 보유 — 상위집합 맞다. "
     "당부는 주석에 이미 있었지만 코드 가드로 승격했다: load_spec 이 scene+emphasis 동시 보유를 발견하면 "
     "즉시 거부한다(오조합 config 로 테스트 통과). 로컬이 병합 중 낸 CRLF 사고(충돌 해소 스크립트가 "
     "'=======\\r' 을 못 알아봐 자기 변경을 날림, stash 커밋 객체로 복구)는 constraint 로 남겼다.",
     "합류 e2c2c36 · scene+emphasis 가드 · CRLF constraint"),
    (31, "D 의 프리미어 M1 보고와 B 의 재검증 의견을 받아라.",
     "옆가지 local/premiere-lab(d694fb0)을 본류에 ff 합류하고 3자 검증을 했다 — B 의 숫자와 전부 일치: "
     "기준선(열기만 한 파일) 대비 손실 0, 시퀀스 단위 객체 전수 9→10, StartKeyframe 5,906→10,571, "
     "고유 미디어 경로 52 불변. M1 판정 통과. 추가 발견: 열기 정규화가 StartKeyframe 점도 60개 지운다 — "
     "기준선 교정(B 제안 1)의 근거가 하나 더 늘었다. 매뉴얼을 실측으로 정정했다: COM ProgID 없음 → "
     "BridgeTalk 경로, 기준선·점 세기·전수 검사 규칙, 멱등 반환값(거짓 실패) 별도 항목, 동시 실행 금지, "
     "M2 는 오프라인 진행(미디어 되살리기는 M4 로 — B 제안 채택, 총괄 결정). "
     "constraint 4건·prproj_fact 22~23·fact 4 정정을 기록했다.",
     "M1 통과 판정 · 매뉴얼 6곳 정정 · M2 지시 확정"),
    (32, "대본(스크립트)용 로컬 서브 에이전트(E)를 새로 판다. 아는 대본 관련 내용을 전부 전달해 달라. "
     "클라우드는 계속 총괄·저장소 관리. (D 는 M2 완료, M3 진행 중.)",
     "log/SCRIPT-AGENT-MANUAL.md 를 작성했다 — 자산 지도(규칙 21·뼈대 4단·나간 25편·자막 실측 14·"
     "대응 47·롱폼 인덱스 16·전문검색·이름규칙·scripts.json 원문), 외울 숫자(45초=307자·6.82자/초·"
     "훅/CTA 고정·실태 55.9초를 표준으로 착각 말 것·겹침 2.2%·CTA 사슬), 작업 순서(chapters→brief→"
     "초안→check→name), 팀 대원칙 4개, 병합 프로토콜(보고는 log/SCRIPT-LAB.md, 옆가지 local/script-lab, "
     "DB 빌더 금지), 윈도우 함정, 금지 목록(롱폼 대필은 결정 전 금지 포함). "
     "tools/shortform.py 와 scripts/shortform/ 의 (중간) 초안 2편은 E 영역으로 이관.",
     "log/SCRIPT-AGENT-MANUAL.md · 4작업자 체제"),
    (33, "E(대본)의 첫 인계 보고를 받아라 — 포인트 편 촬영 완료, 새 갈래 실측 3종, 도구 승인 요청.",
     "local/script-lab 을 본류에 합류했다. 포인트_차 갈래의 실측(New 기준선 53.9초·362자·6.70자/초, "
     "갈래별 속도, 카피 모드 A/B 와 간격 5.5개월 분기, 방향 판정, 재업 2건, Old/New 경계 260725)을 "
     "shortform_rule 22~27 · naming_rule 5~6 으로 등재했다. tools/shortform.py 의 --kind point "
     "(발화만 세기·갈래별 cps·포인트 이름 규칙·토크편 훅 면제)는 승인 — 나간 편 실측(53.1초·43.1초)으로 "
     "검증됐고 도구는 E 영역이다. E 의 기준선 4회 오판 교훈(전수가 항상 옳지 않다·모집단을 걸러라·"
     "사실→규칙 추론은 지시자가 정한다)은 보고서(log/SCRIPT-LAB.md §8)가 원본이다.",
     "합류 6ef287b · 규칙 6건+이름 2건 등재 · 도구 승인"),
    (34, "D(프리미어)의 M2~M6 총괄 보고를 받아라 — 판정 대기 6건, 등재 요청, 판단 요청 4건.",
     "local/premiere-lab 을 본류에 합류하고 verify.py 7행을 전부 재현했다. 6행 통과, M2 행만 실패했는데 "
     "원인은 손실이 아니라 표의 플래그 오기 — m2_out 에는 M1 복제 시퀀스가 들어 있어 --seq-delta 1 이 맞고, "
     "그리로 돌리면 통과(고유 경로 +chartA.png 하나만 증가, D 의 확인점 그대로). M2~M6 전부 통과 판정. "
     "D 가 고친 src/render(showCandles·showMAs 토글)는 기존 씬 재렌더 md5 동일로 회귀 없음 확인. "
     "등재: prproj_fact 24~27(시퀀스 생성·qe 도구·키프레임 함정·고정 오프닝), constraint 2건(릴링크·모달), "
     "brand_token 0D9488, 마운트 대응표. 판단 4건 중 차트-대본 정합은 판정 완료 — 대본이 '공식대로 하면 "
     "수익 나는 경우가 많지 않다' 이므로 −0.57% 완만한 손실 + 상방 +0.44% 는 과장이 아니라 절제된 예시다. "
     "적합. 텍스트 편집(1·3)은 M7 로, A/B 본류(2)는 B-중첩-A 가설 지지하되 팀장 확정 필요.",
     "M2~M6 통과 · 등재 완료 · M7 지시"),
    (35, "주말 클라우드 작업 — SL 차11-4·11-5 숏폼 편집. 원테이크 촬영본(CAM, 3편 뭉텅이)에서 "
     "포인트_차를 걸러내고 ① 컷편집 ② 자막(.srt) ③ 1:1 박스용 차트 모션그래픽까지. 조립은 사용자가.",
     "faster-whisper(medium int8) 로 전사 → 통합 대본과 문장 정렬(마지막 테이크 채택, 역방향 사슬) → "
     "ffmpeg 로 편별 내레이션·참고영상 컷편집. NG 재테이크·디렉팅 멘트 자동 배제, 낭독자가 문구를 바꾼 "
     "1문장('짧게 수익 실현합니다')은 음성을 따름. STT 가 단어 안에 삼킨 침묵은 silencedetect 로 보정해 "
     "'누워버리면' 뒤 2.8초 등 죽은 공백 제거(11-4 46.77초/3스팬, 11-5 50.58초/7스팬). 자막은 기존 14편 "
     "실측 스타일(큐 8~12자·버트조인·단어 경계 스냅). 소스는 scenes/sl-11-4·5 — 1080x1080/30fps, "
     "레퍼런스 완성본(#11-1·#11-3) 실측으로 숏폼 화면 구성(얼굴 없음·차트 중앙 박스) 확인 후 제작. "
     "11-4 는 러너 마켓(seed 11) 연장, 11-5 는 seed 71 튜닝(박스·휩쏘·장대음봉). 프레임 수 1405/1519 검증.",
     "드라이브에 srt·컷리스트 업로드, 소스 패키지 2건(29MB)·미리보기·참고영상 전달"),
    (36, "SL 차11-4·11-5 v2 — 사용자·팀장 피드백 반영. 컷편집 노이즈 더 타이트하게(크흠 잔재·쩝 소리·"
     "'돌파에서..' 헛출발 필수 제거), 차트 소스는 '#11 스타일'이 아니라 차트명가 스타일로 — 최신 SL "
     "최종본을 최신순으로 읽고 1:1 박스 효과를 pool 로 저장하라.",
     "컷편집 v3: 정밀 무음 지도(-33dB/0.35s, 87건)로 스팬 경계를 무음 가장자리에 스냅(경계 밖 "
     "헛기침·쩝을 떨굼), 스팬 안 0.55초+ 침묵은 0.3초로 압축, 스니펫 재전사로 '누워버리면' 뒤 헛출발 "
     "'돌파의…'(88.70~89.35) 실측 제거 → 43.37초/46.03초. 스타일: SL 최종본 6편(차12·차10·차09·차11-2) "
     "콘택트시트 전수 조사 → brand/SHORTFORM-FX-POOL.md 22종 + 팀장 규칙 4개 기록. 씬 v2: 손익비 1:2 를 "
     "익절 초록·손절 갈색 색 박스로(cmgLevel fillTo — 선=테두리 정합), 수익 실현은 '익절' 태그(매도는 숏 "
     "전용), 박스권 상단·하단 검은 선, 휩쏘는 '손절'+화면 전체 손그림 ✕(cmgCross 신설), 20일선 라벨 "
     "처음부터, 등장 모션은 첫 컷만(growDur 0·labelDelay -1 로 깜빡임 제거). 프레임 1302/1382 검증.",
     "v2 패키지·미리보기 재전달, 드라이브 자막·컷리스트 교체"),
    (37, "SL v3 디테일 — ① 손익비 컷에 '놓친 구간' 빗금 추가(팀장: 더 먹을 수 있었던 걸 느끼게) "
     "② 컷 경계 줌 뚝 끊김 제거(콘티 느낌) ③ 11-5 휩쏘 컷 차트가 박스권으로 안 보임 "
     "④ 두 번째 '손절' 싱크 타이트하게 ⑤ 손절 라인 다음 컷 유지.",
     "①: cut2 를 5.87초로 늘려 익절→추세 내달림(reveal 63)→cmgMissed(24,055→24,418)→스우프 순서로. "
     "②: 전 컷 visibleBars 통일 + 경계에서 (reveal, 줌폭) 일치 + 줌 전환은 컷 안 keyframe 으로 "
     "(줌은 오른쪽 끝 앵커 visibleBars/zoom — 11-4: 1→1.4545→0.55→0.8, 11-5: 컷⑥ 1→0.74). "
     "11-5 는 include 를 전 컷 동일하게 걸어 세로 프레이밍도 고정. "
     "③: 마켓 재튜닝 seed 73·박스 22봉 — 가짜 상향 +44/하향 -86 둘 다 박스 관통, 장대 음봉(몸통 114pt)이 "
     "상단을 윗꼬리로 찍고 무너짐. ④: 어절 실측(12.3초)에 in 5.42 로. ⑤: stopHeld 를 컷⑤에 이어받음. "
     "부수: cmgLevel 라벨이 fromBar 와 함께 화면 밖으로 나가던 것을 왼쪽 가장자리 클램프로 고정(labelClamp).",
     "v3 렌더·패키지 재납품"),
    (38, "SL v4 — ① '놓친 구간' 라벨이 위로 반 잘림 ② 마무리 텍스트는 화면 살짝 페이드아웃 + 정중앙 대형으로 "
     "(레퍼런스 엔딩 스타일 그대로) ③ 두 번째 '손절' 여전히 늦음.",
     "①: 라벨을 뷰포트 상단(형성 캔들 따라 숨쉼) 대신 빗금 한가운데(24,240)로, 노출도 4.05~5.15초로 확장. "
     "②: 롱폼용 titleCard 레이어 재사용 — 스크림 0.85 + 흰 글자 104px 정중앙 ('옆으로 누우면?' / "
     "'추세장? 박스권?'). ③: 어절 재실측 — '손절' 2번째 발화는 95.22초(출력 12.05초)인데 그래픽이 12.29초 "
     "→ in 5.05·페이드 0.15 로 스냅. 첫 번째도 3.22 로 당김.",
     "v4 렌더·패키지 재납품"),
    (39, "놓친 구간 라벨은 롱폼 최종본 5:41(러너 컷4에서 렌더된 장면)과 똑같이 — 빗금 안에 크게 + 빨간 밑줄.",
     "러너 기법 이식: cmgNote 58px(빗금 한가운데) + cmgUnderline(300px, 손그림 빨강). 11-4만 재렌더.",
     "11-4 v4 최종 재납품"),
    (40, "11-4 줌 동선 — '이격 음봉'은 봉 하나 얘기니 그 순간부터 다시 줌인해야 뒤 CTA 줌과 자연스럽게 이어진다.",
     "컷4 줌 트랙을 인(1.45)→아웃(0.55, 추세 전체)→'이격된 음봉' 어절에 다시 인(1.1, 청산 캔들)으로. "
     "컷5는 1.1 에서 시작해 0.8 로 완만히. 에피소드 줌 동선: 인→아웃→인(음봉)→아웃(박스권 예고).",
     "11-4 v5 재납품"),
    (41, "11-5 '이평선이 옆으로 누워버리면' — 누운 구간에만 이평선 위 주황 굵은 덧칠, 일부러 수평에 가깝게. "
     "팀장 단골 기법: 선이면 그 구간에만 접선 그리듯 굵게 덧칠.",
     "cmgTrace 레이어 신설 — MA 오버레이 값을 따라 구간(fromBar~toBar)을 굵게 긋되 flatten(0~1)으로 "
     "구간 평균 높이의 수평선에 가깝게 눕힌다. 11-5 컷2 에 39~50번·flatten 0.65·16px 적용 "
     "('누워버리면' 어절 1.55초 in, 휩쏘 마크들과 함께 7.5초 out). FX pool #9 구현 완료로 갱신.",
     "11-5 v5 재납품"),
    (42, "11-4 v6 — ① 이격음봉 세트(원·라벨·익절)가 컷 경계에서 너무 빨리 사라짐 ② CTA 원이 캔들보다 먼저 "
     "등장 (캔들 먼저 → 원, 당연한 모션 순서).",
     "①: 세트를 컷⑤가 이어받아(원 drawDur 0·in [0,0], 태그 popDur 0) 팬 시작 후 1.4~1.9초에 페이드아웃. "
     "②: CTA 원 in 을 0.5→4.3초로 — 리빌이 그 자리(113번 부근)를 다 그린 다음에 원을 친다. "
     "레이어 순서도 titleCard 뒤로 옮겨 딤 위에 선명하게. 교훈: 컷 경계 이어받기는 선·태그만이 아니라 "
     "원·라벨 세트에도 똑같이 적용해야 한다.",
     "11-4 v6 재납품"),
    (43, "11-4 v7 — CTA 원의 레이어 쌓임 순서는 '타이틀 > 스크림 > 동그라미 > 차트'가 맞다. v6 에서 등장 "
     "순서 지적을 쌓임 순서까지 바꾸는 걸로 오버해석했던 것(원을 스크림 위에 올림)을 정정.",
     "동그라미 레이어를 titleCard 앞(아래)으로 되돌림 — 스크림에 같이 딤. 등장 시점(캔들 리빌 후 4.3초)은 "
     "유지. 교훈: 등장 순서(시간)와 쌓임 순서(z)는 별개 지시다 — 지적받은 축만 고친다.",
     "11-4 v7 최종 납품"),
    (44, ".aep/.mogrt 납품 가능성 조사 — 팀장이 수치 하나 건드릴 수 있게 mp4/zip 대신 시퀀스/템플릿 "
     "파일로 줄 수 있는지, 어도비 공식 자료를 뒤져 우리 .psd(완파)·.prproj(부분) 실측과 비교해 달라. "
     "답은 채팅이 아니라 텍스트 파일로.",
     "공식 자료 조사(helpx Projects·Creating MOGRTs·Scripting Guide): .aep 는 스펙 비공개 RIFX, "
     ".aepx 는 마커·경로·이름만 고칠 수 있는 반쪽 XML — 직접 쓰기는 .psd 실패의 재판이라 배제. "
     "대신 ExtendScript DOM 이 창작 전체(컴포지션·키프레임·이징·표현식)와 mogrt 내보내기"
     "(exportAsMotionGraphicsTemplate 등)를 공식으로 덮는다. mogrt 는 노출한 컨트롤만 프리미어 "
     "Essential Graphics 에서 편집되고 조건(Classic 3D, 금지 효과 회피 등) 지키면 AE 없이도 돌아간다. "
     "제안: scenes.js→compile_jsx.py→build.jsx(클라우드)→로컬 AE 가 BridgeTalk/afterfx -r 로 "
     "굽기(포토샵 성공 공식). 1차는 차트 바닥 footage + 주석 네이티브 하이브리드. "
     "선행 확인 3개(AE 설치 여부·팀장 편집 자리·파일럿 대상)는 사용자 몫.",
     "lab/ae/AEP-MOGRT-조사보고.txt 납품"),
    (45, "확인 3개 답변 수신 — ① AE 설치 가능(내 자리 + 팀장 자리) ② 팀장 습관 무관, 이어서 수정 가능한 "
     "프리미어/AE 용 파일이면 됨 ③ 파일럿은 sl-11-4 컷② 손익비. 캔들은 png/mp4 여도 됨(팀장도 스크린샷 "
     "위에 작업하는 스타일), 폰트 설치 완료. D 에게 전달할 Tasks 매뉴얼을 만들어 달라 — 사용자가 직접 "
     "할 일도 단계 사이에 끼워서, 매뉴얼만 보고 D 와 둘이 진행할 수 있게.",
     "log/AE-LAB-MANUAL.md 작성 (프리미어 매뉴얼 관례 그대로: 대원칙·마일스톤 A1~A6·사람 단계 §2·"
     "함정·보고 프로토콜). 토큰/API/MCP 발급은 불필요함을 명시(전부 로컬 앱 자동화). 유일한 클라우드 "
     "의존이던 무주석 바닥 스틸도 미리 렌더해 동봉 — lab/ae/cut2-base-r63-무주석.png "
     "(+재현 씬 cut2-base.scenes.js). 컷② 재현 스펙은 §5 에 표로 박음. 보고는 log/AE-LAB.md, "
     "잡은 tools/ae/jobs/, 푸시는 옆가지 local/ae-lab 만.",
     "매뉴얼 납품 — 출근 후 D 세션에 전달하면 시작"),
    (46, "롱폼 차12(RSI+이평선 스캘핑) 본편 클립 — 차명12롱폼 음성자막-한국어.srt 에 맞춰, 롱폼 11화 방식과 "
     "숏폼 업그레이드를 다 적용해서. .prproj 직접 편집 말고 SL 11-4·11-5 의 mp4+zip 조합 전략으로.",
     "srt 231큐(7:02) 전체를 대본 6단에 매핑, 인트로 4컷(3.4~15.5, 기존 납품)에 이어 컷5~26 20클립을 "
     "6파일로 설계(경계는 30.0 격자 반올림 — 인트로와 동일 규칙). 렌더러에 RSI 서브패널 신설"
     "(wilderRsi/formingRsi, 패널 분할, rsiLevel/rsiZone/rsiTrace 레이어, ma별 등장 알파, rsi 앵커). "
     "색·문법은 차12#1 숏폼 최종본에서 픽셀 실측(10일선 주황·34일선 초록·RSI 하늘색 #0FBDF8·70선 빨강밴드·"
     "30선 파랑밴드·지표명 핑크 배지·RSI 빨간 덧칠). 시장 7종은 find-events(신설)로 시드 스윕 실측 — "
     "매수 seed161(55 재돌파 bar52 양봉·1:2 도달·러너 +11R), 매도 seed68(45 재이탈 bar49 음봉), "
     "횡보 seed96(교차 10회), 강추세 seed25(RSI70 위 45봉), 파동 seed2, 인트로 seed12 이어붙임(앞 봉 불변 검증). "
     "숏폼 업그레이드 전부 적용: 심리스 줌(경계 reveal·줌폭 일치), 팀장 규칙 ②③④, 색박스 손익비, "
     "cmgTrace 접선, 헬드 패턴, 컷 안 줌 전환.",
     "본편 20클립 + 컷리스트_본편.txt 납품 (아웃트로·말 구간 3곳 제외는 배치표에 명기)"),
    (47, "차114_소스패키지_v7.zip · 차115_소스패키지_v5.zip 둘 다 윈도우에서 '압축풀기를 완료할 수 없다'며 안 열림.",
     "원인: zip 엔트리의 한글 파일명(리눅스 zip 의 UTF-8 이름을 윈도우 기본 압축풀기가 못 읽음). 원본 zip 은 "
     "컨테이너 재시작으로 사라져서 저장소 재료로 전부 재조립 — 씬(v7/v5) 재렌더(프레임 1301/1382 재검증), "
     "내레이션은 CAM 재다운로드 + 커밋된 컷리스트 스팬으로 ffmpeg 재컷(43.36s/46.03s 일치), 미리보기 재먹싱. "
     "패키지 구조를 전부 영문 파일명으로 바꿔 재전송(chart/cutN.mp4·narration.wav·subtitle.srt·cutlist.txt·"
     "README.txt). 차12 zip 중 한글 txt 가 들어 있던 1of4·4of4 도 영문명으로 재빌드·재전송. 교훈은 constraint 로.",
     "영문명 패키지 재납품"),
    (48, "조립 실측 — 숏폼 틀이 예상보다 타이트하다. 하단 자막까지가 틀이라 영상 Y 를 960→840 으로 올려야 "
     "안 가렸고, 상단 틀도 983 기준. 즉 우리 영상에서 아래 120·위 23 정도를 줄여야 한다.",
     "1080x1080 캔버스는 유지하고 차트·라벨을 세이프 에어리어(1080x937)에 가두는 방식 채택 — "
     "sl-11-4·5 layout 에 padTop 23·padBottom 120, 손익비 배지 y 1004→884. 프리미어에서는 기본 배치"
     "(540,960)로 되돌리면 끝. v8/v6 재렌더·재패키징(영문명), 규칙은 FX pool 문서와 constraint 에 기록.",
     "sl-11-4 v8 · sl-11-5 v6 재납품"),
    (49, "하단 흰 여백 15px 더. 그리고 zip 만 말고 프리미어 중첩시퀀스 파일도 — 넣으면 알아서 정리된 형태로.",
     "padBottom 120→135(1080x922) 재렌더. 시퀀스 파일은 .prproj 직접 쓰기 금지 규칙 대신 프리미어 공식 "
     "가져오기 포맷인 FCP7 XML(xmeml v4)로 — tools/premiere_xml.py 신설(컷 프레임 배치 + 내레이션 트랙, "
     "갭 배치 @프레임 지원). 패키지에 sequence.xml 동봉: 가져오기만 하면 컷+음성 정렬된 1080x1080/30fps "
     "시퀀스가 생기고, zip 을 C:\\ 바로 아래 풀면 pathurl 이 일치해 미디어 연결까지 자동. "
     "주의: 프리미어 실물 임포트는 아직 미검증 — 사용자 확인이 판정.",
     "sl-11-4 v9 · sl-11-5 v7 납품 (sequence.xml 포함)"),
    (50, "xml 가져오기 성공 확인. 차12도 시퀀스 xml 로.",
     "FCP XML 경로 검증 완료(사용자 실물 확인) — 이제 표준 납품 경로다. 차12 본편 20컷을 배치표 30f# "
     "타임코드 그대로 갭 포함 배치한 1920x1080/30fps 시퀀스 xml 생성(tools/premiere_xml.py --clips @프레임). "
     "clipitem 22(파일 20 + 중복 참조), 겹침 없음 검증. 사용법: C:/ch12_source 에 zip 4개를 전부 풀면 "
     "pathurl 일치로 미디어 연결까지 자동, 가져온 시퀀스를 컷편집 타임라인 0초에 중첩.",
     "ch12_sequence.xml 납품"),
    (51, "내가 줬던 차12 srt 가 구버전이었다 — 프로젝트 안에서 자막이 많이 수정돼 있었는데 내보내기를 안 했던 것. "
     "프로젝트에서 직접 내보낸 '정확.srt' 기준으로 다시 해달라.",
     "새 srt(241큐·7:21, 구 srt 대비 +2~19초 이동) 전수 비교 → 인트로 4컷 포함 26컷 경계 전부 재산정"
     "(30.0 격자). 인트로 컷1은 4.0→2.3초라 연출 압축, 컷3은 1.6→3.7초라 이완, 컷3 경계 12.2초는 "
     "'프리셋 고정 오프닝 불변' 가정으로 유지(배치표에 명시). 매도 파트는 경계 이동으로 '매도 관점만' 라벨을 "
     "컷21로 옮김(RSI 패널 하단 앵커). 5컷은 길이 동일해 재렌더만. 26/26 프레임 검증, 배치표 v2 + "
     "26 clipitem 시퀀스 xml + zip 4개(영문명) + 통합 미리보기 재납품, 드라이브에 배치표 v2 업로드. "
     "정확판 srt 는 저장소에 보관.",
     "차12 v2 재납품 — 구 클립·구 xml 폐기 안내"),
    (52, "차12 v2 미리보기 피드백: ①검정/남색 글자에 검정/남색 테두리 — 전부 안 읽힘 ②영상 내내 가장 오른쪽 "
     "열이 흰 여백(틀처럼) + 상단 등장 텍스트가 세로 절반만 보이는 경우 다수 ③(선택) 진행 속도가 지수함수처럼 "
     "가속이 극단적 — 요소가 몰아치다 지루해짐.",
     "①cmgNote 기본 테두리를 fill 휘도로 판정(0.16 미만이면 흰색) — 어두운 글자의 획 뭉개짐을 전 씬에서 일괄 "
     "해소. ②padRight 110→0(4파일), drawRsi 기준선 라벨을 패널 안쪽 우측정렬+흰 필로 — 흰 열 자체를 제거. "
     "③렌더 없이 라벨 y 를 전 구간 계산하는 감사 도구 src/tools/probe-labels.mjs 신설(스텁 ctx 로 SceneRuntime "
     "구동, engine.keyframe export) — 26컷 전수에서 완전 화면 밖 4개 포함 7곳 적발, 앵커 하향 + cmgNote 세로 "
     "클램프(안전망) 후 재감사 전부 통과. ④컷6·14·20·23 reveal 을 연쇄 inOutCubic → inOutQuad+linear 로 평탄화 "
     "(내레이션 앵커 시각·bar 도달 제약은 검산 후 유지). 26/26 프레임 검증(길이 불변), r3 zip 4개(영문명, "
     "sequence.xml root=ch12r3_source)+배치표 v3+720p 미리보기 재납품, 배치표 v3 드라이브 업로드.",
     "차12 v3 재납품 — 배치는 v2 와 동일, 시각만 변경"),
    (53, "v3 다 해결 확인 + 인트로 피드백 3건: ①컷1 요소가 컷2에서 사라졌다 컷3에서 돌아옴 — 컷을 나누는 "
     "기준은 새 요소로 대체할 때고 그 전엔 지우지 마라(조정 레이어 방식), 비운 논리가 뭐냐 ②컷3부터의 손절 "
     "빨간 선·박스가 대충 그려지는 느낌 ③컷4~6 대본 해석 의문 — 하락이 가짜고 그 뒤 상승이 진짜 아니냐. "
     "그리고: 나는 팀장이 아니라 팀원 이정찬이다. 이번 피드백과 해결 방식을 룰북에 박아라.",
     "①컷2 비움의 근거였던 '프리셋 타이틀이 7.8~12.2를 덮는다' 가정이 실제 편집본에서 틀림을 인정하고 "
     "연속성 체계로 전환: still() 헬퍼 + INTRO_CARRY 로 컷1 요소를 컷2~6이 정지 상태로 이월, 문장 교체는 "
     "크로스페이드(컷4 '골든크로스'→'크로스 신호 하나'), 컷6에선 카메라 이동으로 자연 퇴장(cmgNote clamp:false "
     "신설, cmgLevel toBar 신설 — 끝난 거래 밴드가 새 랠리까지 안 따라오게). ②cmgLevel growEase 신설 — "
     "outExpo 순간 스냅 대신 outCubic 1.0~1.3s, 밴드 두께 23px 통일. ③해석 근거 제시: '~보거나' 병렬 + "
     "'익절할지 몰라 손실 전환'은 보유 포지션 필요 + 기획서의 가짜 신호 정의 — 별개 두 사례로 읽었다고 답하고 "
     "결정 대기(next_step 29). 룰북 brand/EDIT-RULEBOOK.md 신설(규칙 12개 + 반려 사례 + 코드 대응), "
     "introfix zip(컷1~6, 파일명·길이 동일 — XML 재가져오기 불필요) 납품.",
     "인트로 연속성 반려 해결 + 룰북 신설 · 사용자는 이정찬(팀원, 컷편집)"),
    (54, "인트로 추가 피드백: 컷3과 컷4~5의 차이가 원 하나·문구 하나뿐인데 클립을 쪼개 요소 대부분을 반복하니 "
     "템포 빠르고 요소 많아 정신없다(도움 안 되는 줌인 포함). 컷3을 쭉 끌고 가며 추가분만 더하면 된다 — "
     "깜빡임과 정신없음은 같은 뿌리. 뒤 챕터(guide·fail)의 호흡을 모범답안으로 삼아 분석·해결하라. "
     "그리고 컷4~6 대본 해석은 총괄 해석을 따르겠다.",
     "실측 분석으로 추측 확인(인트로 컷 중앙값 3.3초·등장 초당 3.5개 vs 뒤 챕터 ~17초·0.5개 — 6배 밀도. "
     "대체가 일어나는 경계는 인트로에 없음): 컷1~6을 연속 클립 1개(intro-hook, 23.1333초, 프레임 166 배치)로 "
     "병합 — 요소는 한 번만 등장, 퇴장은 크로스페이드·카메라뿐, still/INTRO_CARRY 이월 장치 자체를 제거, "
     "컷4 되감기 점프컷·줌 왕복 삭제. cmg12-hook2.scenes.js 는 cmg12-cross.build.js 로 흡수·삭제. "
     "해석 확정에 따라 랠리 확대: 세그먼트 ↑16봉 s1.3→2.0·↓10봉 s1.3→2.4 (앞 55봉 불변 실측), "
     "골든2 bar62·진입 60161·고점 61168@72(+1007)·5이평 꺾임@73·데드2 bar77(고점 5봉 뒤)·청산 59953.5(-208). "
     "카메라-큐 전수 검산(check_cues) + probe-labels 재감사(세로 잘림 4건 → 잘림 직전 페이드·앵커 이동으로 "
     "해소, 룰북 ⑩ 보충). 룰북 ⑬(호흡) 신설, 배치표 v3(26→21클립), ch12r5_intro_merged.zip + 720p 미리보기 납품.",
     "인트로+후킹 병합 재납품 — 기존 6클립 삭제 후 intro-hook.mp4 하나 배치"),
    (55, "병합본 확인·배치 완료. 피드백 하나(매우 중요, 팀장 강조): '버튼은 무조건 레이어 맨 앞으로 배치. "
     "그 위에 뭐 쌓을 거면 차라리 잠깐 투명화해.' — 병합 인트로에서 손절 버튼이 손실 밴드 뒤에 있어 가려짐. "
     "인트로는 이것만 수정하고, 뒤 챕터들도 최신 룰북 기준으로 재검토해서 수정하라.",
     "①룰북 ⑭ 신설 + 렌더러 강제: engine.js 가 cmgArrow 를 배열 순서와 무관하게 맨 마지막에 그린다(안정 정렬) "
     "— 전 씬 자동 적용, 씬별 실수 원천 차단. 레이어 분리 트랙도 tag 를 최상위(층5)로. "
     "②룰북 전수 재검토 결과 — ⑭ 추가 위반 2곳(buy-exit 매수 태그가 손절 박스에, sell-entry 매도 태그가 "
     "손절 박스에 덮임 — 렌더러 수정으로 함께 해소), ⑧ 경계 증발 11곳(guide 7→8·8→9, fail 11→12·14→15, "
     "buy 16→17→18→19→20, sell 21→22→23, recap 24→25→26 — 인접 컷의 끝 화면을 still 이월하고 후속 요소 "
     "등장 시점에 크로스페이드/카메라로 퇴장), ⑬ 위반 1곳(fail-combo 가 반려된 인트로 컷4와 같은 되감기 "
     "점프컷+줌 — 컷11 끝 reveal 73에서 이어받아 컷 안 팬백으로 재작성). probe 재감사에서 buy-entry 이월 "
     "문장 상단 잘림 1건 → 팬백 초반 페이드로 해소. 본편 20컷 + 병합 인트로 전체 재렌더(r6) 재납품.",
     "r6 재납품 — 클립 이름·길이·배치 전부 동일, 시각만 변경 (전 클립 교체)"),
    (56, "숏폼 .srt 추출을 E 세션으로 이관하라. 추가 규칙: 숏츠 자막은 큐당 띄어쓰기 포함 14자 최대, "
     "더 짧게는 허용, 가능하면 절/구 단위로 자연스럽게 — '~하는 것까지'를 '~하는|것까지'로 끊는 류 금지. "
     "이 피드백까지 반영해 E가 srt 를 뽑을 수 있게 빠뜨리는 것 없이 넘겨라.",
     "①tools/cutedit/srt_rules.py 신설 — 규칙의 진본: split_cue(어절 DP — 14자 상한, 쉼표/연결어미 뒤 선호, "
     "의존명사 시작 금지 벌점, '-는' 관형형 뒤 분리 벌점) + check(14자 초과·의존명사 시작 검출 CLI). "
     "②build_cuts.py cue_chunks 를 구 12자(공백 제외) 로직에서 srt_rules 위임으로 교체. "
     "③SCRIPT-AGENT-MANUAL.md §8 신설 — 규칙 5개·도구 표(스크래치 경로 고침 필요 명시)·파이프라인 순서· "
     "무음 보정 지식·자막 파일 위치 관례(소스+원본, 14/25편 실측)·검사 의무·한 것/안 한 것. "
     "④기존 납품분 검사: 차11-4(15자 2개·의존명사 시작 1개)·차11-5(14자 초과 3개·의존명사 시작 1개) — "
     "새 규칙 기준 소급 위반, 다음 편부터 적용(재발행 여부는 이정찬 결정). CLAUDE.md 범위표에 이관 반영.",
     "E 인수인계 — srt 규칙·도구·검사까지. E는 매뉴얼 §8부터 읽는다"),
    (57, "D 가 m1~m6 실험 성공 — AE 로 '레이어 다 쪼갠 걸로 모아놓은 컴포지션 만들기' 됨. D 에게 넘길 것 "
     "넘겨라: 이번에 추가한 것들, 차12 소스·모션, 작업물 폴더 전체 경로 등 꼼꼼하게. E 에게 전할 말도 정리.",
     "AE-LAB-MANUAL.md §8 신설(D 인수인계): 차12 씬 파일 7종 지도, 배치표 경로, 레이어 렌더 명령과 산출 경로 "
     "(out/cmg12/layers/1_candle~5_tag — out 은 gitignore 라 로컬 재렌더), 층 순서=tag 최상위(⑭), "
     "m6_build.jsx 구 경로 주의, 새 렌더러 문법 4종, motion_preset 3종 실측, 룰북·STYLE 포인터, 프로토콜. "
     "render-cmg12-layers.mjs 를 병합 클립(intro-hook 층당 1파일) 기준으로 재작성하고 실렌더 검증(5층 완료). "
     "next_step 27 을 파일럿 성공 후속(실전 컴포지션)으로 갱신. E·D 전달용 요약문은 대화로 제공.",
     "D 인수인계 — 매뉴얼 §8 + 레이어 도구 갱신"),
    (58, "차12 롱폼 r6 조립 피드백 4건 — 로직 검토 후 의도/실수 분류하고, 실수는 고치고 의도는 설명하라: "
     "①28:20~58:18 인포그래픽 없음 ②guide-rsi 1:35 '① 방향' 사라짐 왜? ③1:37~1:56 인포그래픽 없음 "
     "④2:46 fail-combo '교차 = 반전 신호?'와 '교차 + RSI 30 = 매수?' 겹침 — 이전 게 사라져야.",
     "분류: ①③=의도(배치표 v1부터 말 구간 — 대본에 차트 지시가 없는 전환/성격 설명 멘트라 비움, "
     "next_step 28 확인 요청 ③로 두 번 올렸던 항목. 설명 + 채울 경우의 콘티 제안 제시), ②=실수(⑧ 제정 "
     "이전 설계의 잔재 — 후속 없는 컷 중간 퇴장. r6 재검토가 컷 경계만 감사하고 컷 중간을 안 본 게 원인. "
     "out 제거로 ①·② 나란히 유지), ④=실수(카메라 퇴장 검산이 앵커 봉만 보고 글자 폭 450px 을 무시 — "
     "팬백 후에도 문장 왼쪽 절반이 가장자리에 잔류. 팬백 중 페이드로 수정 + 이월 RSI 원(46)↔새 원(47) "
     "이중 링도 교체로 정리). 룰북 ⑩ 보충2(폭 포함 판정·컷 중간에도 ⑧ 적용) 기록. "
     "guide-rsi·fail-combo 재렌더, 스틸 검증(1:35 ①② 공존, 2:46 겹침 해소), ch12r7_fix2.zip 납품.",
     "r7 — 두 클립만 교체. ①③은 이정찬 결정 대기(채우면 콘티부터)"),
    (59, "말 구간 결정: 차트가 필요 없는 개념/논리 구간도 비우지 말고, 팀장(기존 제작자) 최종본을 실측·카피해서 "
     "그 스타일대로 인포그래픽을 일단 다 만들어라(빼는 건 이정찬이 뺀다). + 추가 지시: 레퍼런스가 적어 획일화 "
     "우려 — 팀장은 자율적이니, 작업물 폴더의 프로젝트 파일들을 열어 '스크린샷_*'와 안 겹치는 애셋 위주로 "
     "어휘를 넓혀 확인하라.",
     "①차명#4 최종본(7:32) 2초 간격 전수 스캔 + 대표 프레임 픽셀 실측: 워시 리스트 카드(블러+화이트 워시 차트 "
     "위 큰 타이포, 항목 누적), 예고 베이지 #F9E9BF→본색 전환, 형광펜 #F8D890, 3패널 카드(테두리 #D81028, "
     "헤더 #50504A), 한줄평·챕터 카드. ②회차 12편의 최종 .prproj 애셋 인구조사(스크린샷 제외): 종이 배경 12/12, "
     "매수·매도 버튼 12/12, PPT 설명 카드 다수, 물음표/화살표 알파 모션, 실제 지수 차트 스샷, 스톡 풋티지 — "
     "자율적 혼용 확인. ③구현: cmgText 레이어(형광펜·예고→본색·파츠 색) + chart.blurPx(engine) 신설, "
     "scenes/cmg12-bridge.scenes.js 2클립 — bridge-intro(29.9333s, 프레임 860, 워시 리스트 문법: 원인→오늘 "
     "배울 것 ①②③)·bridge-scalp(19.0s, 프레임 2939, 종이 배경+매수→익절 버튼 3쌍 반복 문법: 스윙✗→1분/5분봉 "
     "→기계적 진입·청산). 룰북 §E(말 구간 어휘 카탈로그 12종 + 획일화 금지) 신설.",
     "브리지 2클립 신설 — 배치표에 추가, 회차 내 카드 문법은 섞는다"),
    (60, "병합본 확인 피드백 3건: ①bridge-scalp 버튼 3쌍 가운데 정렬 + '초단타·스캘핑'이 자막 바로 위 — "
     "전반적으로 요소가 커 좌상단 타이틀·우상단 로고·자막과 겹침. 75% 축소 실험으로 격자 실측: 세로 위 20%·"
     "아래 15% 여백, 좌상단 박스 35%x20%, 우상단 12%x20%, 자막 세로 15% — 가로는 꽉 채우고 세로만 여백. "
     "이 세이프 에어리어 룰 추가하라. ②buy-exit '손익비 1:2' 배지가 익절 초록 영역에 덮임 — 레이어 순서 "
     "'버튼/동그라미>영역>차트' 고정. ③recap ①의 폰트 프리셋을 ②③에 통일, ② 서브텍스트는 팔레트 다른 색으로.",
     "①룰북 ⑮ 세이프 에어리어(콘텐츠 존 y216~918) — 전 씬 layout padTop 216/padBottom 162(가격·RSI 앵커 "
     "자동 수납), 상단 배지 y96→262, 브리지 카드 y 재배치, 버튼 3쌍 가운데 정렬(x274 시작, 쌍 간 80px), "
     "probe-labels 에 --top/--bottom 비대칭 마진 추가 후 전 씬 재감사(위반 0 — 인트로 '20 이평선' 1건은 "
     "가로 퇴장 후 허위 경보). ②engine z 확장: 영역 0 < 동그라미·배지 1 < 버튼 2 (룰북 ⑭ 확장). "
     "③recap ②③을 52px #111111 로 통일, '하락장' 서브텍스트는 매도 남보라 #473385 (차명#4 실측 팔레트, "
     "룰북 ⑯). ④추가 반려(차트가 오른쪽 끝까지 안 참): layout rightGap 5→0 전 씬 — 캔들·이평선·RSI 선이 끝까지 차게(룰북 ⑥ 보충). 우측 끝 라벨 2개 가로 넘침 보정(fail-combo 문장 55→51봉, buy-entry '다음 캔들 시가' align right). 23클립 전체 재렌더(r8) — 이름·길이·배치 동일, 전 클립 교체 납품.",
     "r8 전 클립 교체 — 세이프 에어리어 시대 시작. 이후 모든 씬은 존 안에서 짠다"),
    (61, "guide 이후 전 클립에서 재등장 오류 — 정확히 '첫 10프레임'. 클립 단위 처리라 생기는 문제 같다. "
     "D 가 곧 레이어 단위로 풀어주겠지만 이 영상까지는 완성시키자 — 같은 레이어(요소)라면 매 클립 반복되는 "
     "첫 10프레임 등장 효과를 고칠 것.",
     "원인: 이월 요소를 in [0,0]·popDur/drawDur/growDur 0 으로 선언해도 레이어 타입들이 등장 연출 창을 "
     "고정값으로 갖고 있었다 — cmgBadge 팝 0.35s(=30fps 로 딱 10프레임), cmgNote 라이즈, 라벨 지연 등 "
     "32곳. 수정: layers.js isStill()(in[0]≤0·페이드 0) + enter() 헬퍼로 이월 요소의 모든 등장 진행도를 "
     "완료 상태로 강제 — 씬이 아니라 렌더러가 보장(룰북 ⑧ 보충). guide-ma·buy-trend 첫 프레임 스틸로 "
     "완성 상태 검증 후 본편 20클립 재렌더(r9), r8 대비 md5 변경분만 교체 납품.",
     "r9 — 변경 클립만 교체. 근본 해소는 D 의 레이어 분해 후"),
    (62, "r9 확인 — 완벽. 그리고 11-4·11-5 원본 촬영본을 컷만 편집한 것(내레이션 말고, 가장 초반 작업물) 줄 수 "
     "있나? 혹시 버렸나? + 여기까지 피드백·해결 전부를 원래 정리하던 곳에 원래 방식으로 정리해 두라(압축 예정).",
     "CAM 컷편집 풀해상도 2편이 스크래치에 생존 — 전송 상한(30MiB) 때문에 각 2파트로 무손실 분할(-c copy, "
     "11-4: 22초 지점·11-5: 23초 지점)해 컷리스트와 함께 재전송, 4파트 저장 확인받음. 정리: 차12 조립 r9 확정 "
     "기록, next_step 28·29 재편(D 후속·브리지 톤앤매너), 룰북 결정 기록에 r9 확정 추가. 진행 중 한도 초기화로 "
     "1회 중단 — 저장소는 전부 커밋·푸시 상태여서 롤백 불요 확인.",
     "차12 롱폼 3단계 사실상 완결 — 이후는 브리지 스타일 교체와 D 후속"),
    (63, "차명10 스샷 3장([롱폼]차명10_양방향 매매법 프리미어 캡처) 기준으로 Bridge 계열의 팔레트·폰트 등 "
     "톤앤매너만 교체하라 — 전개 자체는 마음에 든다.",
     "①스샷 실측: 회색 바탕(~#C4C6C5) 위 차트 은은히, 경기천년바탕 Bold 흰 글자(외곽선 없음), 그림자 "
     "프리미어값(불투명 95·135°·거리 7·크기 12.8·블러 40), 키워드는 핑크 #EF2767 풀밴드 위 흰 글자. "
     "②폰트 입수: 눈누 CDN woff → fonttools 로 TTF 변환 → brand/fonts/경기천년바탕_Bold.ttf + "
     "scene.html @font-face 'GyeonggiBatang'. ③렌더러: strokeText 그림자 확장(shadowColor/OffsetX/Y, "
     "무외곽선이면 채움 글자에 직접), cmgText hlStyle:'band'(풀밴드+hlTextColor, 반높이 size×0.72), "
     "fill 레이어 신설(전체 화면 단색 덮개, 등장 연출 없음). ④씬: cmg12-bridge 를 T10 공통 const 로 "
     "재스타일 — 텍스트·타이밍·구성 유지, bridge-scalp 종이 배경→회색+워시 차트(ema5/20), ✗ 색 "
     "#D81028→#EF2767, 최종 줄 y862→854(밴드 하단 세이프 에어리어 검산). 룰북 §E-2 신설. "
     "⑤렌더 중 이정찬이 80분 무반응으로 중단 — 원인은 ctx.filter 블러가 차트 드로우콜마다 도는 "
     "엔진 구조(constraint_note). 오프스크린 1장 합성으로 수정, 인트로 4800초→212초(23배). "
     "2클립 재렌더(r10) 후 교체 납품.",
     "브리지 2클립만 교체(r10) — 이름·길이·배치 동일. 차명#4 문법은 §E 대안으로 보존"),
    (64, "r10 반려 3건 + 지시: ①핑크 박스는 제목에만 쓴다(본문 키워드 밴드 금지) ②제목(박스 위)에도 그림자를 "
     "다 넣는다 — 단 박스가 아니라 '텍스트'에 그림자 ③그림자가 너무 심하다. 스샷의 텍스트 설정(경기천년바탕 "
     "Bold·그림자 패널 수치 전부)을 그대로 따르되, 작업물 폴더의 차명10 prproj 를 직접 열어 '미국 본장 시간 "
     "추천' 텍스트의 프리셋을 따올 것.",
     "①차명10 최종·복사본_1 prproj 를 드라이브에서 받아 gunzip — '미국 본장 시간 추천'의 소스 텍스트 "
     "FlatBuffers 블롭을 파싱(루트→스타일 테이블 vtable). 두 파일 블롭 동일 = 프리셋 확정: 폰트 "
     "GyeonggiBatangB·크기 117.265·그림자 불투명 95.349·크기 12.791 저장(패널 95/12.8/117 표시와 일치), "
     "선(외곽선) 4.0 은 꺼짐. 각도135/거리7/블러40 은 패널 표시값 채택. ②layers.js: premTextShadow 신설 — "
     "글자 크기 스크래치에 실루엣→블러 합성(전체 캔버스 filter 는 프레임당 수백 ms — r11 1차 렌더가 "
     "600s+ 로 늘어진 원인. 차트 블러와 같은 처방). 체감 보정 σ=블러×0.35·스프레드=크기×0.35·알파=×0.7 "
     "(차명10 완성본 실측 톤). 밴드 박스는 민짜(그림자 제거), 그림자는 제목 글자 포함 텍스트 전 파트. "
     "③씬: 본문 키워드 hl 전부 제거(흰 글자), 제목 3줄만 T10H(117px)+풀밴드 — 손실의 진짜 이유·오늘 "
     "알려드릴 것·짧은 시간 반복 거래. ④룰북 §E-2 갱신, 2클립 재렌더(r11) 교체 납품.",
     "r11 납품 — 박스는 제목 전용·민짜, 그림자는 텍스트만. 프리셋은 prproj 블롭이 원본"),
    (65, "r11 반려 2건: ①기울임(패널의 T-이탤릭 버튼)이 빠졌다 ②그림자는 우하단에만 있어야 하는데 사방으로 "
     "번진다. 그대로 뽑은 것 맞나?",
     "패널을 다시 보니 기울임꼴 버튼이 켜져 있었는데 놓쳤다 — 인정. ①cmgText 에 italic 지원: 글리프만 "
     "베이스라인 기준 ~14° 전단(그림자 실루엣 포함), 박스는 프리미어처럼 똑바로. ②premTextShadow 매핑 수정 "
     "σ=블러×0.15·스프레드=크기×0.3 — σ가 오프셋(거리7→5/5)보다 크면 좌상단까지 번져 후광이 되는 게 원인. "
     "스틸로 우하단 낙하 확인 후 2클립 재렌더(r12, 클립당 렌더가 600s 제한을 넘어 씬별 분할 실행) 교체 납품, "
     "룰북 §E-2 갱신.",
     "r12 납품 — 기울임꼴·우하단 그림자. 패널 스샷은 수치만이 아니라 토글 상태까지 읽는다"),
    (66, "차12 썸네일도 만들어 달라. 기획서 docx 기반으로.",
     "기획서에서 후킹 세 갈래를 뽑아 A·B·C 를 만들고 강조판 A2·B2·C2 까지 6안을 냈다 — "
     "A 진짜 눌림목만 잡는(해법·매수 타점) / B 골든크로스 사지 마세요(문제·횡보 가짜 신호) / "
     "C 70·30선은 버리세요(설정값·과매수 함정). 아랫줄은 기획서의 메인 그대로 이평선+RSI 매매법(C 만 스캘핑). "
     "차트는 본편 씬(cmg12-*)의 seed 161·96·25 를 그대로 써서 썸네일과 영상이 같은 장을 보게 했다. "
     "규칙 22 대로 빨강은 부정당하는 대상(골든크로스·70·30선)에만 붙이고 긍정문 A2 는 크기만 키웠다. "
     "이번에 새로 걸린 함정 둘을 규칙·이슈로 남겼다: 타이틀 자리(규칙 26)와 틀·로고 안전 영역(규칙 27), "
     "윗줄 최대폭 초과(이슈 18)와 t=0 스틸에서 배지가 사라지는 것(이슈 19).",
     "deliver/thumbnail/차12_RSI+이평선 스캘핑/ 6안 · thumbnail_rule 26~27 · issue 18~19"),
    (67, "썸네일 3안 다 좌상단 타이틀이 너무 크다. 비율 15~20% 줄여라. "
     "그리고 앞으로는 이전 썸네일의 글자 크기(수치)를 그대로 따르지 말고 "
     "맥락(격자박스)으로 파악해서 상자 안에 딱 들어가게 해라 "
     "(영상 고정 양식의 좌상단·우상단·자막 상자를 안내선으로 실측한 스샷 4장 첨부)",
     "크기 수치를 손으로 정하던 것을 상자 맞춤으로 바꿨다 — config.json 에 titleBox "
     "(75,100)~(1306,394) 를 두고, build_thumb.jsx 가 두 줄 중 넓은 줄이 상자 폭을 넘을 때만 "
     "두 줄을 같은 배율로 줄인다(확대는 안 한다). 차12 는 아랫줄 1488px 라 x0.827 — 17% 축소로 "
     "요청 구간(15~20%) 안에 들어왔고 세 안이 전부 같은 배율이다. 6안 전부 재빌드해 다시 납품. "
     "규칙 28(썸네일 격자박스)·29(영상 고정 양식 상자)를 새로 남기고 규칙 26 좌표를 갱신했다",
     "thumbnail_rule 28~29 · config.json titleBox · build_thumb.jsx · deliver 6안 갱신"),
    (68, "r12 확인 — 완벽. 정리해 두고, B·E·(D) 가 커밋 푸시해 둔 것들이 잘 병합됐는지 확인하고 너도 정리하라 "
     "(압축 예정).",
     "①옆가지 4개 점검: local/premiere-lab·local/thumb-ch11 은 이미 흡수(0커밋), local/script-lab(E 14커밋)·"
     "local/ae-lab(D 7커밋)을 본류에 병합 — 충돌 0. ②E 인계(SCRIPT-LAB §15·16): 도구 7종(chapters.py·"
     "prproj_titles.py 신규, srt_rules 버그 2건 수정, shortform.py 포인트 갈래), §9 DB 반영분은 지난 라운드에 "
     "이미 반영돼 있음을 확인(naming_rule 5·6, shortform_rule 22, 카피 모드), 총괄 몫 §16-7 처리 — 매뉴얼 §8 "
     "설치 목록에 imageio-ffmpeg 추가(+재발행 안 함 결정 반영). 남은 대기: 범퍼 문구 확정(팀장/이정찬), "
     "SL 배너 문구·차12 범퍼 6개 교체(D), 다음 포인트 편 집필(E). ③D 인계(AE-LAB A0~A6): .mogrt 실험 성공 — "
     "프리미어 [속성]에 한글 컨트롤 9개(색 5·문구 4), 표현식이 프리미어 안에서 산다. 판정: 채택. "
     "④차12 브리지 r12 확정 기록(next_step 29 종결), 룰북 결정 기록 갱신.",
     "브리지 톤앤매너 확정(r12) + 옆가지 전부 본류 합류 — 압축 준비 완료"),
    (69, "D 의 검토 요청(01fc065, lab/ae/검토-글자치수/) — AE 로 옮긴 글자가 우측 3.5px·아래 5px 밀린다. "
     "원인은 실측으로 잡았다(가로: 전진폭 대 잉크상자, 어긋남=획/2−좌사이드베어링≈3.45 일치 / 세로: "
     "middle 의 em 상자 대 잉크상자 가운데). 길 A(하네스에서 캔버스 API 런타임 계측, src/ 무변경) 대 "
     "길 B(렌더러가 치수를 1급 계약으로 내보냄) 중 렌더러 주인의 판단을 구함.",
     "길 A 채택. 근거: src/ 무변경·중복 없음·되돌리기 쉬움, 조용히 빌 위험은 픽셀 대조가 잡는다. "
     "단 렌더러 주인으로서 함정 셋을 얹었다 — ①텍스트가 항상 본 캔버스에 직접 그려지지 않는다: "
     "premTextShadow 의 그림자 실루엣은 스크래치 캔버스(layers.js _shadowScratch)에 fillText 후 "
     "drawImage 합성이라 그 호출의 좌표는 스크래치 로컬이다. 래퍼는 호출마다 ctx.canvas 가 본 캔버스인지 "
     "가려 스크래치 패스를 버리거나 CTM 으로 되돌려야 한다(본문 흰 글자는 본 캔버스 직접이라 그것만 믿으면 "
     "된다). ②차명10 기울임은 fillText 전에 ctx.transform 전단이라 좌표가 축정렬이 아니다 — "
     "ctx.getTransform() 을 호출마다 함께 기록할 것. ③블러 씬은 engine.js 가 차트 ctx 를 _blurLayer 로 "
     "바꿔치기하므로 차트 축 라벨도 오프스크린에 찍힌다. 세로 기준 전환(질문 3)은 부결 — 씬 좌표 전부가 "
     "middle 기준 실측 보정을 거쳤고, 5px 은 A 가 AE 쪽에서 잡는다. B 가 필요해지면 렌더 부수효과가 아니라 "
     "별도 치수 질의 진입점(--metrics 류 JSON 덤프)으로 낸다.",
     "길 A 채택 + 함정 3(스크래치 캔버스·전단 CTM·블러 스왑) · 세로 기준 전환 부결"),
    (70, "D 의 완료 보고와 결재 요청 둘 (2026-09-03) — ①길 A 완료(tools/ae/text-metrics.mjs, 함정 셋 반영, "
     "39건 실측 전부 일치, +3.5px 정체는 판 폭: 잉크폭 263.8 대 전진폭 256.86, 배지 실측 전부 0px). "
     "②결재: engine.js zOf 에 레이어별 z 손잡이 — 동그라미가 글자를 가르던 것(차11-4 컷③·⑤)의 국소 해법. "
     "③결재: sl-11-4 컷③ 문구 z:15, 컷⑤ titleCard 를 스크림 카드+원+scrim:false 본 카드로 분리 — "
     "최종 그림이 실제로 달라짐.",
     "②③ 모두 승인, 본류 병합. 검증: D 본인 커밋이 worklog DB 소스를 안 건드림·검토 폴더 삭제 확인, "
     "engine.js 는 z 미지정 시 기존 순서 보존(기본 층 0/10/20 재배율 + 안정 정렬 — 값 순서 동형), "
     "titleCard 의 scrim:false·rule:false 는 layers.js 기존 지원 옵션이라 씬 분리 성립, "
     "text-metrics.mjs 에 함정 셋(본 캔버스 필터·getTransform CTM·블러 스왑) 코드로 들어간 것 확인. "
     "스틸 직접 렌더로 컷③ '기울기 상방' 원 선이 글자 뒤로, 컷⑤ 원이 스크림 위·글자가 원 위임을 눈으로 "
     "확인. 룰북 ⑭ 에 보충 한 줄(기본 층 0/10/20·z 관례 15) 얹음 — 총괄 결정. "
     "주의 이월: cmgArrow 만은 캔버스도 잉크 상자를 중심에 둔다(세 자리 정렬 기준 제각각 — D 실측). "
     "cmg10 기울임(비축정렬 CTM)은 길만 깔림 — 실전 검증은 차12 AE 이식 때.",
     "z 손잡이·sl-11-4 컷③⑤ 승인 + 룰북 ⑭ 보충 · 길 A 완료 접수(배지 오차 0px)"),
    (71, "시즌1 준비 — B·D·E 의 '건드린 경로 전부' 보고 3부를 취합하고, 금요일 전체저장 후 주말에 "
     "Fable 5.1 UltraCode 새 세션이 최신 설계 기준(레거시 바이패스)으로 레드팀 리뷰하게 준비하라. "
     "관점은 효율성 단독 — 보안·프라이버시는 불요.",
     "①D 의 lab/ae/full v6 커밋(426ec3f) 본류 합류. ②워크플로 1(에이전트 5): 세 보고서의 경로·주장 "
     "전수 검증 — B·D·E 주장 대부분 사실, 정정 3건(psdedit.py 는 config.json 안 읽음, thumb 씬 사용 "
     "타입은 9종 중 6종, 차11 B안은 png만) + git 추적 전수 분류로 지도 공백 발견(프리미어 랩 "
     "tools/premiere/·lab/premiere/ 가 D 영역인데 누락, brand/ 하위·생성기 2종 무주공산). "
     "③log/REDTEAM-BRIEF.md 작성(임무서). ④워크플로 2(에이전트 3): 브리프를 모르는 눈 드라이런 — "
     "블로커 6건 적발(§5 결정성 검증이 §6 금지구역을 더럽힘, 최신 문법 본체 cmg12-cross.build.js 가 "
     "글롭 밖, sqlite3 CLI 부재, 기준커밋 고정 절차 없음, DB 안내 뷰 낡음, 내부어 소사전 없음). "
     "⑤원인 소스 수정: CLAUDE.md 생성기 3종·견본 문장 정정, pipeline_stage 5행·v_start_here 를 "
     "숏폼 이관 후 현실로 갱신. ⑥브리프 최종판: 대상 판정을 import 폐쇄 규칙으로, 바이패스에 잔여 "
     "포괄 조항, §5 전 명령 실측치, 반환 규약에 기준커밋 고정·경로 지정 add·브랜치 local/redteam-s1.",
     "REDTEAM-BRIEF.md 완성(검증 8에이전트 통과) + CLAUDE.md·DB 뷰 낡음 원인 수정 — 시즌1 마감 절차는 next_step 32"),
    (72, "차12 전면 재작 r13 (2026-09-03, 긴급) — 팀장이 승인본(r9+r12)을 반려: ①기존 영상과 너무 다름 "
     "②움직이는 것 금지(멀미·실제 MT5 스크린샷·진짜 캔들) ③이평선 초록 안 보임(AI 티) ④RSI 경계 안 보임(AI 티). "
     "이정찬: '나는 로컬에서 실스크린샷 판을 만들 테니 너는 병행 판을 처음부터. 우리 영상들과 아예 똑같이 — "
     "정확히 얘네가 쓴 효과·연출·기법만. 최종본 #1~#11 다 받아서 프레임 단위로 실측해라. 정확도 최우선.' "
     "(차11 은 본인 자작이라 표본 제외. 배경 수급은 '둘 다' — 실데이터 렌더로 완주 후 스크린샷 오면 교체판.)",
     "①실 NQ 시세 수급(fetch-yahoo.mjs, 1m/5m/1d — 1m 은 5일 소멸이라 즉시 커밋, data/nq/). "
     "②기법 실측: 최종본 mp4 10편 전량 다운로드(드라이브 curl) → 콘택트시트 전수 육안 + 픽셀 군집 실측 + "
     "기계 실측(차트영역 YDIF 중앙값 0.001/255 = 정지 60~90%, 컷 중앙값 6~15s) + 최종 prproj 11편 키프레임 "
     "전수 파싱(디졸브 858개 68%가 30f, 등장 모션 4종뿐 4f/7f/4f/15f, 불투명도·크롭·회전·슬로우줌 kf 0개, "
     "스크린샷 중앙값 4장) + 프레임 단위 YDIF 런 분석(등장 지배 문법 = 1~4f 즉시·팝) → brand/FX-WHITELIST.md. "
     "결정타: 차명#2(이평선+RSI)가 차12 직접 선례 — 빨강/파랑 캔들, 10일선 빨강·35일선 주황(초록 이평선은 "
     "캐논에 없음 = 지적 ③의 뿌리), RSI 는 #9 파랑 프레임+칩 문법. "
     "③렌더러: makeCandles bars 주입 가드, loadBars(브라우저/Node 겸용), theme cmgMt5 프리셋, chart.js 옵트인 "
     "키(maOnTop·wickWidth·candleBorder·gridStyle·axisFontPx·rsiFrame), engine chart.phases(정지 스틸 30f "
     "디졸브 교체 + layer.phase 앵커), cmgBadge popDur — 전부 키 부재 시 기존 경로, 대표 5씬 스틸 48장 md5 "
     "회귀 0건 2회 확인. ④scan-nq.mjs 로 실데이터 6국면 확정(가짜골든 -6.7%/데드후+2.25% 한 창, 17회 교차 "
     "횡보, RSI70+ 29봉, 눌림목 R6→+15R, 역배열 R20→+6R — 전부 무갭). ⑤cmg12s-* 8파일 23컷: 배치표 타임코드 "
     "그대로, 전 컷 차트 1장 정지, 등장은 4f 팝·30f 디졸브·드로우온만, 카메라·줌·리빌 0. 스틸 구도 검사 + "
     "probe-labels 전수 + 프레임 재보정(IN.fade 4f, phases 1.0s). 배치표 r13·MT5 촬영지시서·verify-still 동봉.",
     "23컷 r13 재작 완료 — 실데이터·정지·화이트리스트 문법, 납품 패키지는 out/cmg12s (시즌1 마감은 보류 유지)"),
    (73, "시즌3 '나만의 채널' — 해외선물 매매기법 새 채널 톤앤매너 스틸 4~5장(로고·고정소스 총집합·틀·아웃트로). 팀장: 화이트 톤·심플·중장년 대상. 규칙: Firecrawl 검색·비전 MCP·단계별 시간 기록·오래 걸리면 베껴라 (2026-09-10~11, 로컬 PC)",
     'Gemini MCP(@houtini/gemini-mcp)와 비전 스크립트 tools/style/vision.mjs 설치. v1~v4 = 브라우저 창 틀(점3·탭·주소창) + 차트명가 결. 반려 흐름: 틀이 레퍼런스와 다름·총집합 요소 부족 → 저장소(FX-WHITELIST·prproj_kf_survey·카피맵 r13)를 안 읽었다 → r13 에 치중했다(lab/finalscan 전편 결로) → 기존과 다를 게 없다, 적당히 변형하라. 이미지 생성은 Gemini 무료 등급 429·OpenAI 크레딧 0 으로 불가, 사용자는 유료 거부.',
     "v4 납품(차트명가 NEW/신규안_v1) — 이후 'AI 느낌' 반려로 전통 컨셉 v2 로 전환"),
    (74, '만들수록 AI 느낌이 강하다 — 기존 차트명가 스타일 버리고 이름·로고만. korean traditional 로 검색 위주 레퍼런스, 로고 결합은 맨 마지막 (2026-09-11)',
     "Firecrawl 레퍼런스 21장(오방색·단청·낙관·창호·병풍·책거리·한글 포스터·전통문양) + 픽셀 실측 팔레트 + Gemini 판독 → 무드보드 '병풍 위의 차트'. scenes/newch-trad(캔들+오방색 이평 3선) + tools/style/trad.py 합성기(한지·병풍·창호 사진 띠·낙관·담채 존·붓 원·현판·족자) → 스틸 5장. 반려 '글씨 깨짐·이평선 잘림': PIL stroke_width 가 한글 겹침 윤곽에 구멍을 낸다 → 마스크 팽창으로, 합성 시장이 0봉부터라 이평이 늦게 시작 → 워밍업 60봉(tools/style/trad-bars.mjs). 기존 원형 로고는 인주색 두인으로 변주.",
     '차트명가 NEW/신규안_v2_전통 스틸 5장 · 무드보드·결과·시간기록'),
    (75, '여기까지 만든 요소를 전부 쪼개 PNG 와 AE 컴포지션으로 — 저번(ch11-4 꾸러미)처럼',
     "trad.py 를 층 목록 구조로 바꿔 합성본과 층 PNG 를 같은 그리기 함수로 낸다(--split, manifest). tools/ae/jobs/c1_trad_build.jsx 가 컴포지션 4개 65층 (차트 바닥은 흰 PNG + Multiply). c2_trad_check 재열기 + 0프레임 캡처 대조 0.00%(로고 0.17% = 비교 표식). AE 첫 기동 '경고' 대화상자로 BridgeTalk 60초 타임아웃 두 번.",
     '신규안_v2_전통/AE_꾸러미_trad_ae (trad.aep + footage 65층)'),
    (76, '여태 버전 중 틀만 조립 완성본 — 레퍼런스처럼 가운데를 뚫고, 제목 같은 것 없이 깨끗하게',
     'tools/style/frames_clean.py — 레퍼런스 트팩 틀만과 같은 형식(1920×1080 RGBA, 콘텐츠 자리 알파 0·RGB 0). A 브라우저창(v1 계열) · B 병풍(v2). 체커보드·모서리 확대로 검증.',
     '차트명가 NEW/틀만_완성 — 틀만 2종 + 적용예시'),
    (77, '① 병풍 틀의 지붕(창호 사진) 한지와 배경이 다르다, 배경은 단색이다 ② 족자는 두루마리 펼침 애니메이션과 함께 AE 컴포지션으로 ③ 계획해 둔 애니메이션이 있는 소스는 전부 소스별 .aep/.mogrt 로 (2026-09-14)',
     "① 실측 — 창호 종이 213,198,177 편차 15 대 바탕 편차 2. 바탕을 Magnific 무료 닥종이 사진 결(tools/style/tex/hanji_mulberry.jpg)로, 창호 띠는 종이 부분만 같은 톤으로 → 띠 235,226,211 / 바탕 237,228,212. v2 스틸·틀만 B·trad_ae 재생성(재조립 캡처 0.00%). ②③ 층에 anim 메타(stamp·drawon·scroll) + tools/ae/trad_motion_pack.py(중복 제외 20개) + c3_trad_motion.jsx: 낙관 '쾅' 17 · 붓 원 드로우온 1(트림 매트) · 족자 펼침 2(글자는 AE 궁서, 종이 폭·높이 표현식 추종) · 보호 구간 마커 · 위치/크기/자막 노출 · mogrt 20. c4 재열기(표현식 104회 무오류) · f40 대조 18개 0.00% · 미리보기 GIF. 함정: mogrt 내보내기 한 번 뒤 들고 있던 CompItem 이 전부 무효 → 이름으로 재조회. AE 캡처는 비동기라 다음 잡이 프로젝트를 닫으면 사라진다.",
     '신규안_v2_전통/AE_모션_trad_motion (aep + mogrt 20 + 미리보기). 닥종이 사진은 출처 표기 조건'),
    (78, 'MCP 52개 목록 중 그동안 썼으면 효율적·효과적·확장적이었을 것 분석, 필요한 API 키 한 번에 받게',
     '작업 병목(도형 그리기의 AI 느낌·한글 글자 깨짐·수작업 픽셀 대조·가독성·벡터 부재) 대비 분석. 확실히 도움: magicui+브라우저 캡처 · pixelmatch+opencv · color-tools · svg 계열 · colorthief. Figma 공식 커넥터는 연결돼 있으나 Starter 요금제·View 좌석이라 MCP 읽기 월 20회(공식 문서) → 반복 작업 불가. 추천 도구는 키 불필요. 목록에 이미지 생성·스톡 소재 도구는 없다.',
     '보고만 — 설치는 request 79'),
    (79, '프리미어 저장하고 끄고, 도움되는 MCP 를 공식 GitHub README 대로 설치해 제대로 작동할 때까지 시험',
     'tools/premiere/jobs/save_quit.jsx — 열린 프로젝트 1개 save()(수정시각 갱신 확인) 후 app.quit, 프로세스 종료 확인. MCP 8개 사용자 범위 등록: magicuidesign-mcp · chrome-devtools(--headless --workspace) · pixelmatch · opencv(uvx --with mcp<2) · color-theory(npm 미등록이라 소스 빌드) · color-palette(소스 빌드) · imagetosvg · svg2png(GTK3 런타임이 관리자 요구 → 7-Zip MSI 를 관리자 없이 풀어 DLL 을 PATH 로). stdio 시험기(mcp_test*.mjs)로 실제 도구 호출 전부 성공, claude mcp list 전부 Connected. 막힌 곳: mcp 파이썬 SDK 2.x 가 FastMCP 를 없앰, opencv 한글 경로 불가, chrome 파일 쓰기는 roots 밖 차단.',
     'C:/Users/user/mcp-servers/설치기록.md — 새 도구는 Claude Code 재시작 후 세션에 보인다'),
    (80, "익절&손절 박스 모션(C:/aelab/mogrt/차11-4 손익비.mogrt)을 신규안_v2_전통 스타일로. 중간: '차트 배경은 빼도 돼. 소스별로 잘라서 쓸거야.' 컴퓨터 비정상 종료 뒤 '보수적으로 되돌아가서 안전하게 이어서' (2026-09-14)",
     "옛 a3_build 의 요소 9종·등장 박자를 그대로 옮기고 모양만 전통으로 — tools/style/trad_rr.py(낙관 면·담채·점선·빗금·붓 밑줄 PNG + 요소별 대조 기준, 청산 봉 53·놓친 고점 24,418.25 는 데이터에서 계산) → c5_trad_rr.jsx 소스 컴포 12(0프레임 등장, 표현식은 자기 컴포 안만) + 전체 1(176f) · 글자는 AE 궁서라 문구를 바꾸면 낙관 면·현판 판이 따라 늘어남(c7 시험 3건). 실측: 낙관 기울기 부호 반대(PIL 반시계/AE 시계) · 필수 속성은 스크립트로 부모 템플릿에 못 연다(canAdd=false, c5b) → 전체는 위치·크기만. 12:58 컴퓨터 비정상 종료(멈춘 AE 강제 종료·재실행 사슬 중) → 재부팅 뒤 파일 무결성(NUL·py_compile·node --check) 확인 · 로컬 WIP 커밋 · AE 잡 한 번에 하나. mogrt 내보내기 함정: 내보낸 뒤 프로젝트가 줄어 남음(c5c) → 하나마다 aep 새로 열기(c5x) · 반환값 true 여도 무작위로 한 개씩 푸티지 누락(손절 박스 2 → 전체 12) → zip 안 definition.json 검사 후 실패분만 재내보내기(trad_rr_mogrt_check.py · trad_rr_export.ps1) · 내보내기는 수정된 프로젝트를 저장한다(c5t 시험이 aep 를 오염 → 소스에서 다시 지음). 검증: 재열기 푸티지 12·표현식 85 무오류 · mogrt 13 누락 0 · AE f150 vs 합성 기준 화면 0.85%.",
     '신규안_v2_전통/AE_손익비_trad_rr (aep + footage 12 + mogrt 13 + 미리보기 · 읽어보기) · C:/aelab/mogrt/차11-4 손익비 (전통).mogrt 추가(옛 파일 그대로)'),
    (81, "익절선&박스 · 손절선&박스 · 진입선: ① 선이 화면 전체를 덮게 ② 버튼에서 선이 뻗어 나가게(지금은 버튼이 도착점이고 선보다 늦게 나와 인과가 틀렸다) ③ 셋은 .aep 로도. + 지지선·저항선이 없으면 같은 버튼-선 세트로(박스 없이) · 방향은 왼→오 한 방향 (2026-09-14)",
     "처음 '지지선'이 무엇인지 AskUserQuestion 으로 확인 → 진입선(말 실수) + 지지·저항 추가. 지지·저항은 v2 모션에 낙관 도장만 있고 선 세트는 없었다. trad_rr.py 에 kind='set'(버튼 PNG 면 + 0~1920 선 PNG + 0~1920 박스 PNG) — 버튼은 왼쪽 열 x=166(v2 지지·저항 낙관 자리), c5 buildSet: 버튼 '쾅' 0~10f → 선 마스크 앞끝이 화면 왼끝에서 4~20f 오른끝으로 → 박스 6~22f, 박스 색은 선 색 표현식 추종, 컨트롤 문구·버튼 색·선 색·위치·크기. 옛 소스 6개 → 세트 3 + 지지선·저항선(전체엔 안 넣음). 현판을 왼쪽 열 아래로 옮겼다가 초반 캔들을 덮어 되돌림. c9_trad_rr_set_aep 가 c5 빌더를 빌려(__RR_LIB_ONLY) 세트마다 aep 저장·재열기. c5x·검사기가 기대 개수·이름을 rr.json 에서 읽게. 검증: 재열기 푸티지 16·표현식 105 무오류 · 세트 aep 5 연결 · mogrt 12 누락 0(붓 밑줄 무작위 누락 1회 재내보내기) · AE vs 기준 세트 0.24~1.04% · 연속 사진으로 버튼→선 순서 확인 · 문구 늘림 3건. 납품 전 1차본을 이전_1331 로 복사 보관.",
     '신규안_v2_전통/AE_손익비_trad_rr 갱신 (aep · 소스별_aep 5 · mogrt 12 · 미리보기) · 이전_1331 보관 · C:/aelab/mogrt/차11-4 손익비 (전통).mogrt 새 판'),
    (82, "선이 잘 안 보인다 — 버튼과 똑같은 스타일로 선을 굵게. 이전 차트명가 오리지널 버튼&선 세트(버튼과 선이 잘 보이고 매우 자연스럽다)를 참고 (2026-09-14)",
     "옛 cmgLevel(src/render/layers.js: 선 13px, 같은 색 라벨판이 선 시작점에 붙음, 높이 54)과 옛 컷② 렌더(lab/ae/a3/렌더러_5_00s.png)를 확인. trad_rr.seal_line — 낙관과 같은 rough_mask 재질·같은 색·굵기 낙관 높이×0.26(13/12px), 화면 밖까지. 확대로 반투명 낙관 뒤 선이 비쳐 진한 띠가 생긴 것을 잡음 → 선에서 낙관 면 안쪽을 비움(면 빈틈을 흐림으로 메운 뒤 문턱·3px 줄이기). c5 buildSet 색 컨트롤 하나(면→선→박스 표현식), 앞끝 흐림 10. 도중 사용자가 프리미어(L08) 작업 중 — BridgeTalk 잡이 프리미어 dynamiclinkmanager 가 띄운 AE 로 들어가 응답 끊김(부모 프로세스로 확인) → AE 자동화 멈추고 AskUserQuestion, 프리미어 종료 뒤 남은 AE 를 c8q_close_quit(저장 없이 닫고 scheduleTask 로 app.quit)로 정상 종료하고 새 AE 에서 이어감. 검증: 재열기 푸티지 16·표현식 130 무오류 · 세트 aep 5(컨트롤 4) · mogrt 12 첫 시도 누락 0 · AE vs 기준 세트 0.24~0.83%, 화면 0.84% · AE 캡처 이음새 확대 · 문구 늘림 3건. 결과 응답이 안 오는 NO_RESPONSE 600s 가 반복 — 완료는 로그 판정 줄로 판단.",
     '신규안_v2_전통/AE_손익비_trad_rr 3차 (aep · 소스별_aep 5 · mogrt 12 · 미리보기) · 2차는 이전_1427 보관 · C:/aelab/mogrt/차11-4 손익비 (전통).mogrt 새 판'),
    (83, '(실수로 보낸 요청 — 뒤에 취소) 박스권 또는 볼린저밴드 (2026-09-15)',
     "tools/style/trad_bands.py — 박스권 세트(팀장 규칙 ② 검은 선: 먹 버튼 '박스 상단/하단' + 굵은 인주 선 + 먹 박스, 횡보 28~43봉에서 잰 23,855/23,700) · 더블 볼린저밴드(차명03 대본 '지표 설정 팩트' 내부 20·σ0.5 / 외부 20·σ3, 매수 우위=적 · 매도 우위=쪽 · 중립 비움, 구간 이름 낙관). 합성기 스틸 3장까지 내고 사용자가 '실수로 엔터' 라 해서 중단.",
     '신규안_v2_전통/시안_박스권_볼린저 (스틸 3장) — AE 소스화는 안 함'),
    (84, "'B_병풍_틀만.png' 에서 위 기와(창호 띠)를 뺀 한지만 버전, 뚫린 가운데는 유지. 한지는 살짝 더 하얀 톤으로 (팀장) (2026-09-15)",
     'frames_clean.py 에 --variant clean 추가 — frame_byeongpung_clean(창호 띠 없이 한지+병풍 테두리 · 한지 #ECE3D3→#F3EEE3 · 결은 같은 닥종이 사진). 두 종: 뚫린 자리를 기존 B 와 같게 둔 것(81,139,1839,999)과, 띠가 빠진 만큼 위 여백을 60 으로 맞춘 것(81,81,1839,999). 기존 A·B 파일은 해시 그대로 두고 새 이름으로만 저장. 위 여백 실측 평균색 #F3EFE4.',
     '차트명가 NEW/틀만_완성 — B_병풍_한지만(+여백균등) 틀만·적용예시 4장 · 읽어보기 갱신'),
    (85, '매도 버튼 색을 아예 파란색으로 — 매수:매도 = 빨강:파랑. mogrt 는 이름 그대로 유지해서 한번에 일괄 적용되게 (2026-09-15)',
     "색은 계산으로: 인주 적 #D42A26(oklch L0.565 C0.206 H27.8)과 채도를 같게 두고 색상 262°·밝기 0.53 → #1F60E0. color-theory MCP 확인 — 도장 글자(#FAF6EE) 대비 5.12:1(적 4.68) · 쪽 #2C3358 과 ΔE2000 23.2. 정확한 보색 #0091B3 은 청록이라 배제. trad.py 에 BLUE 상수·매도 낙관·팔레트 9칸(간격 100). 재생성 검증: 스틸은 전통_2·5 만 바뀌고 1·3·4 해시 동일 · 층 PNG 66장 중 s21_seal_sell 하나만 변경 → 모션 팩·납품 사본 4곳 교체. c10_trad_motion_export_one 으로 '낙관 매도.mogrt' 를 같은 이름으로 재내보내기(저장 안 함 · 팩 밖으로 낸 뒤 zip 안 PNG 해시·누락 0 확인하고 교체). 프리미어는 파일 교체만으로 기존 클립이 안 바뀐다 — Alt 끌어놓기로 프로젝트 전체 적용(어도비 도움말). 템플릿 ID 는 내보낼 때마다 새로 생김. 이날 비정상 종료 2회(15:17·16:47) 뒤 매번 무결성 확인부터 다시 시작.",
     '신규안_v2_전통 — 전통_2·전통_5 스틸 · s21_seal_sell.png(팩·납품 4곳) · 낙관 매도.mogrt(팩·납품) · 이전_매도쪽빛 보관 · 무드보드/결과/시간기록 갱신'),
    (86, "로컬에 흩어진 것을 한 폴더로 단일화 + Portable, 최신만 zip. 중간: 'G드라이브 업로드는 내가 할거니까 로컬에만 둬' · '남은 부산물 전부 지워, 똑같은 파일이 여러 곳에 있지 않게' · C:/aelab 을 연결(junction)로만 둔 1차안은 '경로가 둘이면 그것도 흩뿌려짐' 이라고 반려 (2026-09-16)",
     "차트명가NEW_통합/ 하나로 모음 — 01 납품 · 02 AE작업실 · 03 저장소(작업본+bundle) · 04 작업메모 · 05 도구와설정 · 06 실험실 · 99 이전판. 지우기 전에 파일마다 sha256 으로 꾸러미 안 존재를 확인(차트명가 NEW 397개 · aelab 3527개 · cmgwork · pprolab). **C:/aelab 을 완전히 없앰**: 경로를 박던 자리를 자기 위치에서 위로 올라가며 '02_AE작업실_aelab' 을 찾는 방식으로 교체 — labdir.py/.mjs/.ps1 신설(순서: AELAB_DIR → config.labDir → 위로 탐색 → 옛 자리), _lib.jsx·bridge.jsx·a1_smoke.jsx 는 ExtendScript 라 같은 해석기를 인라인. config.json labDir 을 빈 값(=자동)으로. 실측: a1 스모크 통과(새 작업실에 로그 씀) · c11_relink_check 로 팩 5개 112개 푸티지 '못 찾음 0' — .aep 에 옛 절대경로가 박혀 있어도 footage/ 가 .aep 옆에 함께 있어 AE 가 상대경로로 재연결한다(열면 dirty=true 가 되므로 저장하지 않고 닫는다). 버린 것은 ae/ref·diff·frames 검증 PNG 2906장뿐, 그 폴더의 스크립트·설정·로그·영상 소스 117개는 _기타 로 살림.",
     '차트명가NEW_통합/ (00_먼저읽기.md · 도구/복원.ps1) · 차트명가NEW_통합_20260916.zip(로컬 보관, 업로드는 사용자가 직접) · 틀만_완성/읽어보기.txt 실측 정정'),
    (87, "D 알림 — C:/cmgwork 을 지우고 통합 폴더로 옮겼다. 포토샵 자동화가 그 경로를 쓰고 있었다면 끊겨 있다. "
     "경로를 박지 말고 스스로 찾게 하라(tools/ae/labdir.* 방식). .psd 의 링크 자원도 함께 볼 것 (2026-09-16)",
     "끊겨 있었다 — tools/photoshop/config.json 이 template·chartDir·outDir 세 개를 C:/cmgwork 으로 박고 있었다. "
     "labdir 규칙을 그대로 가져와 고쳤다: labdir.ps1(run.ps1 용) + _labdir.jsx(jsx 4개 공용) 신설, "
     "찾는 순서 CMGWORK_DIR → config.labDir → 위로 8단계 '06_실험실/cmgwork' → 'cmgwork' → 옛 자리 C:/cmgwork. "
     "config 의 세 경로는 작업실 기준 상대경로로 바꿨다(src.psd · . · out). "
     "D 는 jsx 에 같은 코드를 인라인했지만 여기는 $.evalFile 로 한 파일을 불러 쓴다 — 4벌 복사가 곧 같은 문제라서. "
     "실측: run.ps1 이 작업실을 06_실험실/cmgwork 으로 찾았고 A안을 실제로 빌드해 "
     "9/3 납품본과 픽셀 동일(diff bbox None, 최대 채널차 0)·격자박스 x0.827 재현. "
     "링크 자원 문제는 없었다 — 템플릿이 전부 임베드라 대화상자 없이 열렸다. "
     "남은 것: tools/premiere/jobs 의 m2_swap·m4_place·m5_intro·m2_check 가 아직 C:/cmgwork 을 박고 있다(프리미어 영역).",
     "tools/photoshop/labdir.ps1 · _labdir.jsx 신설 · config.json 경로 3개 상대화 · A안 픽셀 동일 검증"),
    (88, "E 긴급 보고 — 통합 폴더로 옮긴 탓에 정찬님이 편집 중이던 더원 L08 프로젝트의 소스 10개가 오프라인이 됐다. 되돌릴지 새 자리를 알릴지 판단 요청 (2026-09-16)",
     "되돌리지 않고 .prproj 안의 경로를 새 자리로 고쳐 썼다 — 프리미어는 열지 않고 gzip XML 을 풀어 접두사만 치환('차트명가 NEW\\' → '차트명가NEW_통합\\01_납품_차트명가NEW\\'). 세 군데에 들어 있었다: ActualMediaFilePath 10 · FilePath 10 (절대) · RelativePath 20 ('..\\..\\..\\' 는 새 폴더도 이정찬\\ 바로 아래라 그대로 유효). 접두사에 & 가 없어 '손절선&박스.aep' 이스케이프는 건드리지 않았다. 본편 40건 + 자동저장 20개 588건 = 628건 (자동저장까지 고친 이유는 되돌렸을 때 다시 끊기는 함정을 남기지 않으려고). 검증: 끊김 10→0 · gzip 해제 정상·</PremiereData> 로 닫힘 · 이정찬\\ 아래 모든 .prproj 재검사 결과 옛 경로 0개 · 원본 21개 백업. 이어서 tools/premiere 의 박힌 C:/pprolab·C:/cmgwork 를 _labdir.jsx·labdir.ps1 자동 탐색으로 교체(잡 29개+config+bridge+run.ps1) — m4_place 는 작은따옴표라 1차에 안 잡혔고 B 지적으로 발견. **원인: 옮기기 전에 '파일이 다 담겼는지'(해시)만 재고 '누가 이 경로를 물고 있는지'를 안 쟀다.** 담는 쪽만 보고 쓰는 쪽을 안 봤다. 후속: E 가 꾸러미 **안쪽**(내 1차 검사가 제외한 곳)의 '차트명가New 프리셋.prproj' 20건을 찾아줬다 — 절대경로는 새 자리로, 상대경로는 '..\\..\\..\\차트명가 NEW\\' → '..\\' 로 줄여 꾸러미만으로 열리게 했다. 백업 대조로 절대 끊김 6→0 확인, 남은 상대 끊김 22건은 이 프리셋이 L08 폴더에서 복사돼 온 탓에 원래부터 끊겨 있던 것(프리미어는 절대경로를 먼저 본다). E 는 RelativePath 가 원래 이중 이스케이프(&amp;amp;)라는 것을 대조로 확인해 자기 1차 보고를 정정했고, B 는 치환 뒤 재훑기로 저장소에 남은 옛 경로가 전부 의도된 폴백·주석임을 확인했다. 셋이 합의한 이동 전 점검 3종: 해시(담는 쪽) · prlinks(프로젝트가 무는 것) · 정규식 grep(코드가 박은 것).",
     '더원 L08 .prproj 21개 경로 정정 · 꾸러미 안 차트명가New 프리셋.prproj 도 정정(절대 끊김 6→0, 상대는 꾸러미 안에서 짧게 만들어 자립) · tools/premiere/_labdir.jsx·labdir.ps1 신설 · 잡 29개 경로 자동화'),
    (89, "AE 꾸러미 세 폴더도 같은 게 중복이다 — 최신 것으로 단일화해라 (2026-09-16)",
     "해시로 재보니 단순 중복이 아니라 **drift 였다**: 납품 AE_손익비_trad_rr 은 3차(박스 반투명), 작업실 pack/trad_rr 은 4차(단색) — 9/14 에 요청받고 코드까지 넣었던 박스 단색화가 소스 PNG 에만 반영되고 aep·mogrt·납품본에는 안 퍼져 있었다. 현재 코드로 footage 를 임시 폴더에 다시 뽑아 작업실 18개와 완전 일치(납품은 4개 다름)를 확인하고 4차로 통일했다. c5(trad_rr.aep, 컨트롤 44 노출) → c9(세트 aep 5, 박스 불투명도 포함) → trad_rr_export.ps1(mogrt 12, 검사 12/12 첫 통과) → c8q 정상 종료. 단색이 mogrt 까지 갔는지는 .mogrt 안 project.aegraphic(중첩 zip)을 열어 zone PNG 해시로 확인 — 새것(알파 255) 일치, 옛 납품본은 반투명이었다. 구조: 납품의 AE_* 세 폴더를 지우고 pack/ 한 벌만 남겼다. 지우기 전 184개 파일을 해시로 대조해 팩이나 99_이전판에 있음을 확인했고, 납품에만 있던 미리보기 17장·읽어보기는 팩으로, 1차 mogrt 15개와 3차 구본 21개는 99_이전판으로 옮겼다.",
     'pack/trad_rr 4차(aep·세트 aep 5·mogrt 12·미리보기·읽어보기) · pack/trad_motion 미리보기 8 · 납품 AE_* 3폴더 제거 + AE_꾸러미는_어디에.txt · 99_이전판/손익비_3차_반투명박스·손익비_1차_mogrt · 결과.md 8차 · 시간기록 347분'),
    (90, "라이브 롤링 광고(라이브_롤링 광고_1.prproj)를 차트명가 NEW 판으로. 영상 구성은 이미지 이어 붙이기+디졸브뿐이라 핵심은 원본()_ 두 폴더의 이미지. 트레이딩팩토리 문구·구성은 똑같이 두고 에셋 스타일·톤앤매너만 바꿀 것. 로고는 준 파일을 그대로 쓸 것 (2026-09-16)",
     "원본 11장(8000x504 5 · 8000x750 5 · 고정댓글 377x71)을 색 무리별 바운딩 박스로 실측해 좌표를 옮겼다 — 긴 판 글자띠 y127~399·CTA x6347~7915, 짧은 판 글자띠 y224~606·CTA x5970~7835. 문구는 gemini flash 로 판독해 한 자도 안 바꿨다(pro 는 무료 할당 소진). 바꾼 것: 검정→한지 #F3EEE3 · 형광연두 #01FF17→인주 적 · 흰 본문→먹 · 노랑→단청 황 #9E7B12 · 청록/보라 평행사변형→쪽 두 겹 · 빨강 알약 CTA→현판(옻칠+금테+흰 궁서) · 연두 테두리 박스→인주 적 박스 · TF 로고→차트명가 로고를 그대로 얹음 · 글꼴 궁서. 실측으로 바로잡은 것 둘 — (1) 왼쪽에 박스나 로고가 오는 판에는 원본도 모서리 장식이 없다, (2) 글자가 CTA 현판에 물려서 남은 폭에 맞춰 크기를 자동으로 줄이는 fit() 을 넣었다. trad.hanji() 의 결 텍스처가 1920 폭 고정이라 8000 을 한 번에 못 만들어 1920 조각을 좌우 반전해 이어 붙였다(이음매 안 보임). 파일 이름·폴더명·크기를 원본과 똑같이 맞춰 11/11 일치 — 프리미어에서 푸티지 바꾸기로 갈아 끼우면 편집이 산다. 프리미어가 켜져 있어 .prproj 는 건드리지 않았다.",
     '01_납품_차트명가NEW/라이브화면/롤링광고 (이미지 11 + 읽어보기) · tools/style/roll_ad.py (문구는 COPY 한 곳에 모음)'),
    (91, "'차트명가 NEW 라이브화면구성.ai' 를 만들어라. 구성·양식은 Claude/라이브화면 프레임 의 "
     "260114_라이브화면구성(2026v).ai, 톤앤매너는 local/newch-style(D 의 전통안). 핵심은 Reference_01~03 "
     "같은 세트를 우리도 똑같이 만드는 것 — MVP 완성도 우선. 문구는 트팩 것 그대로 쓰고(갖다 쓸 게 바꿀 것보다 "
     "많다), 단순 캡쳐 유형(차트·종류/거래량·수익·스티커메모·댓글창)은 트팩 것을 그대로 갖다 쓴다. "
     "로고는 준 파일을 그냥 쓴다. 차트명가NEW_통합 안을 건드리려면 D 승인을 받아라 (2026-09-16)",
     "tools/illustrator 신설(D 승인) — run.ps1·labdir.ps1·_lib.jsx·config.json·build_live.jsx·"
     "make_bg.py·dump_ai·dump_caps·dump_board·export_obs. 아트보드 6개(배경·오프닝틀·메인틀·가이드·"
     "최종출력샘플 오프닝/메인)로 트팩 Reference_01~03 대응. "
     "**실측이 전제를 뒤집었다**: 원본 .ai 는 8000x4500 이 아니라 1920x1080 pt 이고 OBS png 가 417% 출력본이다 — "
     "덕분에 D 의 전통 소스를 1:1 로 썼다(낙관 재생성·한지 타일링 불필요). 구역 좌표는 가이드·프레임 png 의 "
     "알파를 재서 얻었다. 캡쳐는 참고용 PNG 를 줄여 자르던 것을 원본 .ai 에서 duplicate() 로 항목째 복사하도록 "
     "고쳤다(정찬님 지적 — 압축+축소로 두 번 열화). 한지·낙관은 D 의 trad.py 함수를 그대로 불러 구웠다. "
     "D 검수 4건 반영: 칸마다 두꺼운 띠 → 바깥 한 바퀴만(병풍은 폭 사이가 이음선), 정보 띠 19.6:1 현판 → "
     "편액은 채널 이름만(글자가 판 길이를 정한다), 낙관을 차트 밖으로, 광고 자리 인주 적 전폭 → 한지. "
     "이후 정찬님이 06 을 직접 고친 것을 dump_board 로 떠서 값으로 옮겨 여섯 아트보드에 반영(27항목 일치). "
     "색은 컬러팔레트.png 의 역할 기반 브랜드 팔레트를 따른다 — 방송시간·입장문의에 0D9488(반대 개념 강조)을 "
     "쓴 것은 잘못이라 334155(부가 설명 자막)로 정정.",
     "01_납품_차트명가NEW/라이브화면/ (.ai 6보드 + 미리보기 6 + OBS 3 + 읽어보기) · tools/illustrator/ · "
     "brand/EXTENDSCRIPT-TRAPS.md"),
    (92, "2026-09-17 15:00 이정찬 — 압축 뒤 '검토·자가발전(효율·정확·적절)'. 맨땅에 헤딩하지 말고 남들이 찾은 지름길을 갖다 쓴다. 승인은 인박스로 로컬이 판단. 첨부 .txt(핫 논문·스타 속도)는 방법론 참고, '우리 오류에 도움되는 레이더'는 실제로 만든다. 일상 작업(회차 진행)은 총괄이 관여하지 않고 해결/미해결만 안다. RLHF 의 H 는 Mainstream 으로; User 역할 비효율도 피드백 받겠다", "① 병합 newch-style(ff)+script-lab(3-way) 1fceff7 ② 인박스 4건+E 회신 → issue 20~37·constraint_note 38~51·decision 23~28·next_step 34~39 ③ save.py --only/--status/범위 밖 보존 ④ build_cuts.py·premiere_xml.py → tools/legacy ⑤ 옛 경로 문서 8개 머리말 ⑥ 조사 세션 2개(주류 패턴 조사·코드 품질 검토, 읽기 전용) ⑦ .claude/settings.json(UTF-8 env)·pyproject·pre-commit·tests 16·git_guard.py(미연결)·tools/radar.py+스킬 ⑧ 총괄 코드 버그 2건(split.mjs timebase·DB \\01 제어문자) 재현 후 수정 ⑨ 개선안 log/inbox/2026-09-17_총괄_작업체계·도구품질_개선안.md — 워크트리·훅 이관·소유자별 코드 품질·User 역할 피드백 8건", "저장소 전용은 적용·커밋. 로컬 판단 항목(워크트리·훅·각자 코드)은 인박스 회신 대기(next_step 40). 미해결: issue 35(토큰 재발급)·next_step 34~37"),
]
# 주의: 66·67 은 B(썸네일 로컬), 68 은 총괄 — 같은 날 병합하며 시간순으로 재배번 (2026-09-03)

PHASES = [
    (1, "환경 구축", "Chromium(사전설치본 사용), ffmpeg-static(libx264/prores/qtrle/vp9), Pretendard·JetBrains Mono 설치", "done"),
    (2, "렌더러 1차", "프레임 번호를 받아 그리는 결정적 렌더링. 캔들 생성기·차트 드로잉·오버레이 레이어·캡처·인코딩", "done"),
    (3, "다크 테마 6컷", "NQ 5분봉, 하락→박스권→가짜이탈→되돌림 롱→손익비→익절, 45초", "done"),
    (4, "알파 오버레이", "QuickTime RLE 무손실 알파 3컷. 모서리 픽셀 RGBA(0,0,0,0) 확인", "done"),
    (5, "프리셋 입수", "Drive 422MB 다운로드 → 765MB/76파일. 폰트·로고·패턴·prproj 만 추림", "done"),
    (6, "브랜드 분석", "레퍼런스 프레임에서 색·레이아웃 실측 → brand/STYLE.md", "done"),
    (7, "차트명가 테마", "흰 배경 라이트 테마, cmg* 레이어 8종 추가", "done"),
    (8, "20일선 4컷", "대본 타임코드 478프레임에 맞춘 4컷 + 릴", "done"),
    (9, "최종본 대조", "롱폼·숏츠 최종본 실측으로 태그 크기·영역 색·배지 보정", "done"),
    (10, "익절·손절 복구", "기본 프리셋 실측값으로 되돌리고 layers.js 중복 536줄 제거", "done"),
    (11, "작업 로그 DB", "SQLite 단일 파일로 세션 전체 정리", "done"),
    (12, "썸네일 방식 도출", "#1~#10 을 전부 솔로 렌더해 비교 + PSD 좌표 실측 → 고정 높이 타이틀·인물 판단·차트 핵심요소 규칙 확정", "done"),
    (13, "차11 썸네일 3안", "Photoshop 2026 COM + ExtendScript 로 템플릿 직접 편집. A/B/C 각 .psd(11.5MB) + .png", "done"),
    (14, "버튼 브랜드 정합", "매수·매도 버튼의 도형·효과·색·폰트를 brand/ui 원본과 #6·#7 fx 실측값에 맞춤", "done"),
]

SCRIPT_LINES = [
    (1, "차11_20일선의 비밀", "4. 문제 제시", 1, "00;05;26;27", "00;05;31;02", 125, 4.1708,
     "다수의 트레이더는 20일선 눌림목에서 진입하는 것까지는 성공합니다."),
    (2, "차11_20일선의 비밀", "4. 문제 제시", 2, "00;05;31;02", "00;05;34;29", 117, 3.9039,
     "하지만 막상 수익이 발생하면 추세를 끝까지 끌고 가지 못합니다."),
    (3, "차11_20일선의 비밀", "4. 문제 제시", 3, "00;05;34;29", "00;05;37;15", 76, 2.5359,
     "확보한 수익을 다시 잃을까 두려운 나머지,"),
    (4, "차11_20일선의 비밀", "4. 문제 제시", 4, "00;05;37;15", "00;05;42;25", 160, 5.3387,
     "짧은 저항선이나 1:2 정도의 얕은 구간에서 기계적으로 이익을 실현해 버립니다."),
]

FPS_5994 = 60000 / 1001
SCENES = [
    # (id, config, scene_id, name, seq, fps, frames, seconds, script_line_id, synopsis)
    (1, "cmg-20ma-runner", "cut1-pullback-entry", "① 20일선 눌림목 진입", 1, FPS_5994, 250, 250 * 1001 / 60000, 1,
     "상승 추세 → 20일선까지 눌림 → 색연필 원으로 눌림목 강조 → 매수 태그"),
    (2, "cmg-20ma-runner", "cut2-profit-runs", "② 수익 발생", 2, FPS_5994, 234, 234 * 1001 / 60000, 2,
     "진입선 위로 초록 수익 영역이 커진다"),
    (3, "cmg-20ma-runner", "cut3-fear", "③ 수익을 잃을까 두려움", 3, FPS_5994, 152, 152 * 1001 / 60000, 3,
     "화면 미세 진동 + 수익 영역 윗선이 진입선 쪽으로 당겨졌다 돌아옴"),
    (4, "cmg-20ma-runner", "cut4-early-exit", "④ 1:2 조기 익절 + 놓친 구간", 4, FPS_5994, 320, 320 * 1001 / 60000, 4,
     "손절·익절선과 손익비 1:2 → 익절 체결 → 줌아웃하며 놓친 구간이 빗금으로 차오름"),
    (5, "nq-basic", "01-open", "오프닝 — 캔들 드로잉 + 타이틀", 11, 60, 420, 7.0, None, "다크 테마 NQ 5분봉"),
    (6, "nq-basic", "02-structure", "구조 — 지지·저항 박스권", 12, 60, 450, 7.5, None, None),
    (7, "nq-basic", "03-breakdown", "이탈 — 하단 붕괴와 스탑 헌팅", 13, 60, 420, 7.0, None, None),
    (8, "nq-basic", "04-entry", "진입 — 되돌림 롱", 14, 60, 420, 7.0, None, None),
    (9, "nq-basic", "05-tpsl", "세팅 — 손절·익절과 손익비", 15, 60, 450, 7.5, None, None),
    (10, "nq-basic", "06-result", "결과 — 익절 도달 + 요약 카드", 16, 60, 540, 9.0, None, None),
    (11, "nq-overlay", "ov-chart", "오버레이 — 캔들만 그려지기", 21, 60, 300, 5.0, None, "투명 배경"),
    (12, "nq-overlay", "ov-tpsl", "오버레이 — 손절·익절 박스", 22, 60, 300, 5.0, None, "투명 배경"),
    (13, "nq-overlay", "ov-pnl", "오버레이 — 손익 카운터만", 23, 60, 300, 5.0, None, "투명 배경"),
]

RENDERS = [
    # (scene_id, path, format, w, h, fps, frames, alpha, note)
    (1, "out/cmg/cut1-pullback-entry.mp4", "mp4", 1920, 1080, FPS_5994, 250, 0, "29.97 기준 125f"),
    (2, "out/cmg/cut2-profit-runs.mp4", "mp4", 1920, 1080, FPS_5994, 234, 0, "29.97 기준 117f"),
    (3, "out/cmg/cut3-fear.mp4", "mp4", 1920, 1080, FPS_5994, 152, 0, "29.97 기준 76f"),
    (4, "out/cmg/cut4-early-exit.mp4", "mp4", 1920, 1080, FPS_5994, 320, 0, "29.97 기준 160f"),
    (None, "out/cmg/_reel.mp4", "mp4", 1920, 1080, FPS_5994, 956, 0, "4컷 이어붙임, 29.97 기준 478f"),
    (5, "out/01-open.mp4", "mp4", 1920, 1080, 60, 420, 0, None),
    (6, "out/02-structure.mp4", "mp4", 1920, 1080, 60, 450, 0, None),
    (7, "out/03-breakdown.mp4", "mp4", 1920, 1080, 60, 420, 0, None),
    (8, "out/04-entry.mp4", "mp4", 1920, 1080, 60, 420, 0, None),
    (9, "out/05-tpsl.mp4", "mp4", 1920, 1080, 60, 450, 0, None),
    (10, "out/06-result.mp4", "mp4", 1920, 1080, 60, 540, 0, None),
    (None, "out/_reel.mp4", "mp4", 1920, 1080, 60, 2700, 0, "다크 6컷 릴 45초"),
    (11, "out/ov-chart.mov", "qtrle", 1920, 1080, 60, 300, 1, "무손실 알파. 30MB 초과라 채팅 전송 불가"),
    (11, "out/ov-chart.webm", "vp9a", 1920, 1080, 60, 300, 1, "전송용 압축본"),
    (12, "out/ov-tpsl.mov", "qtrle", 1920, 1080, 60, 300, 1, None),
    (13, "out/ov-pnl.mov", "qtrle", 1920, 1080, 60, 300, 1, None),
]

BRAND = [
    ("차트", "배경", "#FFFFFF", None, "레퍼런스 프레임 실측", "축·그리드 없이 화면을 꽉 채움"),
    ("차트", "상승 캔들", "#0B8C7F", None, "레퍼런스 프레임 실측", "딥 틸"),
    ("차트", "하락 캔들", "#E80001", None, "레퍼런스 프레임 실측", None),
    ("차트", "20일 이동평균선", "#F38808", None, "레퍼런스 프레임 실측", "얇은 주황 실선"),
    ("매매", "익절 선", "#14FF35", "23px", "기본 프리셋 실측", "두께가 캔들보다 확실히 굵다"),
    ("매매", "익절 영역", "#BAFDC0", None, "최종본 실측", None),
    ("매매", "손절 선", "#9F0000", "23px", "기본 프리셋 실측", None),
    ("매매", "손절 영역", "#FEBABA", None, "최종본 실측", None),
    ("매매", "익절·손절 라벨 박스", "173x84", "px", "기본 프리셋 실측", "각진 사각형, 선과 같은 색, 선 시작점 왼쪽에 붙임"),
    ("매매", "익절·손절 라벨 글씨", "#FFFFFF / 62px", None, "기본 프리셋 실측", "검정 외곽선 없음"),
    ("매매", "매수 태그", "#E80001", "116x48px", "최종본 실측", "흰 글씨, 검정 외곽선 없이 얇은 흰 헤일로"),
    ("매매", "매도 태그", "#0200F3", "116x48px", "최종본 실측", None),
    ("배지", "종목·타임프레임", "#E90054", None, "레퍼런스 프레임 실측", "흰 글씨, 검정 테두리 없음"),
    ("배지", "소제목", "#8E8E8E", None, "레퍼런스 프레임 실측", None),
    ("배지", "타이틀 바", "#8C535D ~ #D76D83", None, "레퍼런스 프레임 실측", "질감 있는 자주 그라데이션, 이탤릭 흰 글씨"),
    ("강조", "손그림 마크", "#C0272D", "12px", "최종본 아웃트로", "원·밑줄·X. 색연필 질감"),
    ("자막", "하단 자막", "검정 박스 + 흰 굵은 글씨", None, "최종본 실측", "편집에서 넣으므로 렌더에는 미포함"),
    ("폰트", "제목·강조", "Gmarket Sans", None, "프리셋 폰트 폴더", None),
    ("폰트", "본문", "S-Core Dream / 나눔고딕", None, "프리셋 폰트 폴더", None),
    ("폰트", "제목 대체", "경기천년제목", None, "프리셋 폰트 폴더", None),
    ("출력", "최종본 롱폼 규격", "1280x720 / 30fps", None, "최종본 파일 메타", "컷씬 소스는 1080p 로 납품 중"),
    ("썸네일 버튼", "매수", "#FF0000", "186x88px", "brand/ui/매수 버튼(좌우).png 실측", "화살촉 43px · 모서리 r7 · 글씨 잉크 128x67"),
    ("썸네일 버튼", "매도", "#0000FF", "186x88px", "brand/ui/매도 버튼(좌우).png 실측", None),
    ("썸네일 버튼", "익절", "#00FF24", "185x90px", "#7 익절 도형 solidFill rgb(0,255,36)", "같은 도형에 색상 오버레이만 얹은 것"),
    ("썸네일 버튼", "글씨", "S-Core Dream 5 Medium", None, "브랜드 PNG · #7 익절 텍스트 레이어",
     "흰색, 검정 외곽선 없음. 타이틀(Gmarket Sans Bold)과 다른 폰트다"),
    ("썸네일 버튼", "효과", "외부 광선 검정 18% · 스프레드 72 · 크기 10 · 노이즈 22", None,
     "#6·#7 lfx2 를 ActionManager 로 읽음", "드롭섀도우·내부 그림자·획·그레이디언트는 전부 꺼져 있다"),
    ("썸네일 버튼", "비율", "글씨높이/버튼높이 0.761 · (버튼폭-글씨폭)/버튼높이 0.659", None, "brand/ui PNG 실측",
     "글씨는 몸통 한가운데에서 화살촉 쪽으로 0.04·h. 폰트가 바뀌어도 이 비율로 역산한다"),
    ("썸네일 타이틀", "윗줄 글자 높이", "141px 고정", "왼쪽 x=88 · 베이스라인 y=198", "#2~#6 실측", "폭은 1017~1306 으로 자유"),
    ("썸네일 타이틀", "아랫줄 글자 높이", "194px 고정", "왼쪽 x=74 · 베이스라인 y=395", "#2~#6 실측", "폭은 1148~1583 으로 자유"),
    ("프리미어", "상반 지표 서브 강조", "#0D9488", None, "메인 프리셋 색상 범례 원문",
     "'반대되는 개념의 서브 강조 (예: 매수/매도, 상승/하락 등 상반된 지표 비교)'. 단기 이평선처럼 "
     "20일선과 대비되는 선에 쓴다. 같은 범례: EF2767(메인 타이틀)·ED7F89(서브 타이틀)·1E293B·334155"),
]

ASSETS = [
    ("압축본", "00_메인 프리셋(차트명가).zip", "1bfxw8NubZr42brF5kIuRUcsYL-S0mJ4f", 422099429, "받아서 해제(765MB/76파일)", "기본 프리셋 일체"),
    ("폴더", "02_차트명가(최종본)", "1HOplrH8GowSLJPrbxIVvVTCDEL6sUPac", None, "목록만 조회", "롱폼 10편 + 숏츠 60여 편"),
    ("폴더", "차명01~15 소스", "1hqkgml4CV9cZDyD-mJiE-aRTzAX49b3A", None, "목록만 조회", "회차별 원본·프리미어·기획서"),
    ("영상", "차명#1_쿠리마기_EMA+박스권(최종).mp4", "1Fuhxm4hwSCULvf8wAFlHHZBFZyBf5vcb", 266586708, "프레임 실측용", "1280x720/30fps, 7분15초"),
    ("영상", "260711_[SL_차11_#3]20일선이 중요한 이유(최종).mp4", "1_wTyqenNmieugt3zEOXaoMKLO9LxCcEy", 83108129, "프레임 실측용", "숏츠 1080x1920"),
    ("영상", "260703_[SL_차11_#1]20일선 120%활용법(최종).mp4", "11XeXHXJdfGqqAeG4vCPMZIApex65yc_m", 57043949, "프레임 실측용", "숏츠"),
    ("문서", "[차11_20일선의 비밀]_롱폼 기획서+스크립트.docx", "1vMJf7EYysVMFv3Sa8bhS8iu7eZ0GX-hj", 31867, "본문 추출", "이번 대본 4줄의 출처"),
    ("저장소", "brand/ (폰트·로고·패턴·prproj·레퍼런스)", None, 36700000, "커밋됨", "100MB 초과 3개와 BGM·인트로 영상은 제외"),
]

ISSUES = [
    (1, "Playwright 브라우저 빌드 불일치",
     "설치한 playwright 가 chromium-1234 를 찾는데 컨테이너에는 1194 만 있음",
     "패키지 버전과 사전 설치 브라우저 빌드 번호가 다름",
     "환경변수 → 사전 설치 경로 → 기본값 순으로 찾는 resolveChromium() 추가",
     "다운로드 없이 렌더 성공", "fixed"),
    (2, "400MB 매뉴얼 전달 경로",
     "채팅 첨부 30MB 한도라 올릴 수 없음",
     "전송 수단의 크기 제한",
     "Drive 공유 링크를 받아 컨테이너에서 직접 curl 다운로드",
     "422MB 정상 수신", "worked-around"),
    (3, "GitHub Release 로는 못 받음",
     "릴리스는 보이는데 에셋을 가져올 수 없음",
     "초안 상태 + 태그 없음 + 저장소 비공개, api.github.com 은 프록시 차단",
     "GitHub 경로를 폐기하고 Drive 로 전환. 공개 저장소 릴리스는 curl 로 받아짐을 테스트로 확인",
     "원인 3가지 특정", "worked-around"),
    (4, "알파 무손실 파일 전송 실패",
     "ov-chart.mov 38.5MB 가 30MB 한도 초과",
     "QuickTime RLE 무손실이라 용량이 큼",
     "VP9 알파 webm(3.4MB)으로 압축해 전달하고, 무손실 재생성 명령을 안내",
     "ProRes 4444 는 155MB 로 더 나빠서 배제", "worked-around"),
    (5, "매수 태그가 컷 경계마다 깜빡임",
     "16초 동안 3번 사라졌다 다시 나타남. 다른 요소는 멀쩡",
     "4컷 전부에 들어가는 유일한 요소라 컷마다 등장 애니메이션이 재생됨. 등장 시각을 줘도 첫 프레임이 투명해짐",
     "cmgArrow 에 popDur 옵션 추가(0이면 처음부터 완성 크기), cue 가 in 생략을 '이미 떠 있음'으로 처리",
     "릴 956프레임 전수 측정: 컷2~3 386프레임 중 누락 0, 경계 전후 태그 폭 41~42px 일정", "fixed"),
    (6, "색연필 원이 컷 경계에서 끊김",
     "컷1 끝에 떠 있던 원이 컷2 첫 프레임에 사라짐",
     "컷1 에만 있는 레이어인데 퇴장 시각이 없었음",
     "컷 안에서 미리 페이드아웃하도록 out 시각 추가",
     "경계 전후 연속 확인", "fixed"),
    (7, "익절·손절 표기 스타일 오판",
     "영역 한가운데 큰 글씨로 바꿨더니 회사 스타일과 멀어짐",
     "최종본 한 영상의 변형을 표준으로 착각. 기본 프리셋의 컬러 박스가 표준",
     "프리셋 프레임을 픽셀 단위로 재서 복구(선 23px, 박스 173x84, 흰 글씨, 선 왼쪽에 붙임)",
     "프리셋 프레임과 대조", "fixed"),
    (8, "layers.js 레이어 정의 중복",
     "고친 코드가 렌더에 반영되지 않음",
     "객체 리터럴에 zone~cmgLevel 10종이 두 벌 들어가 뒤쪽(옛 코드)이 이김. 인덱스 기반 수정이 앞쪽에만 적용됨",
     "중복 536줄 제거",
     "정의 32개 → 22개, 중복 0", "fixed"),
    (9, "라벨 겹침 다수",
     "손익비 배지가 익절 라벨을, 익절 라벨이 매도 태그를 가림",
     "줌아웃하면서 요소 간 거리가 좁아짐",
     "배지를 좌하단으로, 라벨 박스를 선 왼쪽 바깥으로, 놓친 구간 화살표 제거",
     "컷4 전 구간 스틸 확인", "fixed"),
    (10, "복제한 회차의 차트 색이 죽음",
     "렌더한 차트를 넣었더니 캔들과 태그가 전부 탁해졌다 (#00BF1B 가 #75947A 로)",
     "회차 그룹 안의 'Black & White 823' 조정 레이어(불투명도 214/255 = 83.9%)가 켜져 있었다. "
     "합성값을 역산하니 정확히 회색 83.9% 혼합이었다",
     "복제 후 BLACKANDWHITE 조정 레이어를 끈다",
     "#00FF24 가 그대로 나옴", "fixed"),
    (11, "ExtendScript 에서 레이어 삭제가 막힘",
     "'삭제 명령은 현재 사용할 수 없습니다' (오류 8800)",
     "템플릿 레이어에 lspf(레이어 잠금)가 걸려 있다",
     "복제한 그룹을 재귀적으로 allLocked/pixelsLocked/positionLocked = false 로 푼 뒤 삭제",
     "다른 회차 9개 제거 성공", "fixed"),
    (12, "썸네일 .psd 가 180MB",
     "회차 하나짜리 결과물인데 템플릿 크기 그대로였다",
     "10회차 그룹이 전부 들어 있다",
     "저장 전에 #11 을 뺀 나머지 '#' 그룹을 통째로 삭제 (psdedit.drop_group 과 같은 발상)",
     "195MB → 11.5MB", "fixed"),
    (13, "폰트를 바꾸자 버튼 여백이 어긋남",
     "S-Core Dream 으로 바꾸니 글씨 잉크(122px)가 몸통(114px)을 넘어 화살촉을 침범했다",
     "버튼 크기가 advance width 기준 상수(h = 1.34·size, w = tw + 1.15·size)로 잡혀 있었다. "
     "이 값은 Gmarket Sans 로 잰 것이라 폰트가 바뀌면 반드시 깨진다",
     "actualBoundingBox 로 잉크를 재서 브랜드 비율(글씨h/버튼h = 0.761, (버튼w-글씨w)/버튼h = 0.659)로 역산",
     "버튼 189x90 — 컨테이너가 템플릿 픽셀에서 잰 189x90 과 같다", "fixed"),
    (14, "윈도우에서 log 도구가 안 돌아감",
     "build_worklog_db.py 가 UnicodeDecodeError (cp949) 로 죽는다",
     "git 출력은 UTF-8 인데 subprocess 의 text=True 가 윈도우 기본 로케일(cp949)로 읽는다. "
     "한글 경로가 있는 저장소라 바로 터진다",
     "git 을 부르는 subprocess.run 에 encoding='utf-8' 을 붙였다 (save.py 2곳, build_worklog_db.py 4곳). "
     "파일 입출력은 PYTHONUTF8=1 로 덮는다",
     "윈도우에서 db·md·html·README 4개 다 생성됨", "fixed"),
    (15, "run.ps1 이 파싱 오류로 안 뜸",
     "Unexpected token '}' — 멀쩡한 스크립트인데 PowerShell 이 거부한다",
     "PowerShell 5.1 은 BOM 이 없는 .ps1 을 시스템 ANSI(cp949)로 읽는다. "
     "한글 주석의 UTF-8 바이트가 깨지면서 따옴표가 생겨 구문이 어긋난다",
     "run.ps1 을 UTF-8 with BOM 으로 저장",
     "run.ps1 build_thumb 이 3안을 그대로 다시 뽑음", "fixed"),
    (16, "문자 단위 크기가 조용히 무시된다",
     "textStyleRange 의 size 를 바꿔 써도 적용되지 않는다. 오류도 안 난다. 색은 정상 적용된다",
     "타이틀 레이어에 큰 변형이 걸려 있다(transform xx=9.629). 그래서 textStyle 이 "
     "size(11.95px) 와 impliedFontSize(=size x 배율, 115.065px) 를 같이 들고 있고, "
     "둘이 어긋나면 포토샵이 impliedFontSize 를 믿고 size 를 되돌린다",
     "size 와 impliedFontSize 를 같은 배율로 함께 쓴다. build_thumb.jsx 의 paintRuns()",
     "A2.psd 를 다시 읽어 [0,3) 목표가 #FF0000 14.03px 확인 — #8 의 14.03px 과 일치",
     "fixed"),
    (17, "덤프가 섞인 줄의 색을 하나로 적었다",
     "ref_tree.txt 가 #8 윗줄을 통째로 #FF0000 이라고 적어 놨다. 실제로는 가짜신호만 빨강이다",
     "DOM 의 textItem.color 는 첫 글자 색 하나만 돌려준다. 문자별 서식은 "
     "textKey 디스크립터의 textStyleRange 목록에만 있다",
     "tools/photoshop/dump_text_runs.jsx 를 새로 만들어 ActionManager 로 구간별로 읽는다",
     "10회차 재확인 — 섞인 줄 3개(#8·#10·#7)를 정확히 집어냈다",
     "fixed"),
    (18, "윗줄이 관측 최대폭을 넘었다",
     "차12 B 안 골든크로스에 사지 마세요 가 폭 1258 · 오른쪽 끝 1335 로 관측 최대폭 1306 을 넘었다. "
     "빨강 강조판(B2)은 1.174배를 얹으면 1419 가 된다",
     "글자 크기가 고정 규격이라(규칙 4) 줄이 길면 폭으로만 늘어난다. 열두 자는 이 채널에서 처음이다",
     "① 조사 에 를 뺐다 — 골든크로스 사지 마세요 (1229). "
     "② 강조 배율을 1.174 대신 #7 조합(#FF5353 · 1.087)으로 낮췄다 (규칙 23의 예외값)",
     "B 1229 · B2 1275 — 둘 다 1306 안. build_log 의 폭 경고 사라짐",
     "fixed"),
    (19, "t=0 스틸에서 배지·기준선 라벨이 안 보인다",
     "썸네일용 스틸(--stills 1, t=0.00s)에서 cmgBadge 와 rsiLevel 의 라벨이 통째로 사라진다. "
     "popDur: 0 을 줘도 그대로다",
     "두 레이어의 등장 스케일은 popDur 이 아니라 in[0] 을 기준으로 span(t, in0, in0+0.35) 로 계산된다. "
     "in 을 안 주면 in0=0 이라 t=0 에서 배율이 0 이다. 영상 컷은 t 가 0.35 를 넘겨서 안 드러났다",
     "in: [-1, 0.2] 로 등장 시점을 t=0 앞으로 민다. 스틸 한 장을 뽑는 씬에서는 이게 기본이다",
     "차12 A·B·C 세 씬에서 RSI 배지와 70선 라벨이 정상 출력",
     "fixed"),
    # ── 2026-09-17 인박스 등재 (원자료 log/inbox/*, 총괄 문장) ──
    (20, "폴더를 옮겨 더원 L08 프리미어 소스가 끊김 — 같은 날 두 번 (2026-09-16)", "'차트명가 NEW\\' 를 통합 폴더로 옮긴 뒤 L08 편집본 소스 10개 오프라인. 오후에 AE 꾸러미 3폴더를 pack/ 으로 합치며 4개 또 끊김. 두 번째는 이정찬이 14:08 프리미어로 열다 발견", "옮기기 전 '다 담겼나'(해시 184개)만 재고 '누가 이 경로를 무는가'는 안 쟀다. 오전에 D 가 제안한 규칙(prlinks find)을 오후에 D 가 어겼다", "프리미어를 열지 않고 .prproj gzip XML 안 경로 치환(1차 628곳·2차 404곳 — ActualMediaFilePath·FilePath·RelativePath, 상대경로는 &amp;amp; 이중 이스케이프). E 가 tools/cutedit/prlinks.py 신설 — 옮기기 전 find, 옮긴 뒤 check (runbook 19)", "E 검증 14:56 — 본편 32·수정본 65 모두 연결, 옛 폴더 이름 무는 프로젝트 0. 이정찬이 프리미어로 직접 연 것은 14:08(끊긴 상태)이 마지막 — 눈 확인은 next_step 34. 원문 log/inbox/2026-09-17_D_오류·비효율.md A1 · log/E-회신-260916.md §3-3", "fixed"),
    (21, "참조 스캔에서 목적지 폴더를 빼 프리셋의 옛 경로를 놓침 (09-16)", "차트명가New 프리셋.prproj 가 옛 경로를 물고 있었는데 D 의 스캔이 통합 폴더(목적지)를 제외해 못 봤다. E 가 잡았다", "'이미 정리한 곳'이라며 새 폴더를 검사 범위에서 뺐다", "검사 범위에서 목적지 폴더를 빼지 않는다 — prlinks.py 머리말에 명문화", "prlinks check 끊김 0. 원문 log/inbox/2026-09-17_D_오류·비효율.md A2", "fixed"),
    (22, "경로 치환이 작은따옴표 형태를 놓침 (09-16)", "\"C:/cmgwork/ 로만 바꿔 m4_place.jsx 의 'C:/cmgwork/cmg12/cut1.png' 가 남았다. B 가 잡았다", "따옴표 모양을 가정한 치환. 재검사 정규식도 heredoc 역슬래시로 깨짐(constraint_note 'Bash 도구 heredoc')", "치환 뒤 따옴표와 무관한 문자열로 전체 재검색", "재검색 0건. 원문 log/inbox/2026-09-17_D_오류·비효율.md A3", "fixed"),
    (23, "같은 작업실을 경로만 달리 두 곳에 둠 — C:\\aelab 정션 잔존 (09-16)", "통합 폴더로 복사한 뒤 C:\\aelab 을 정션으로 남겨 '물리적으로 하나'라고 봤다. 이정찬: '이게 내가 말한 흩뿌려짐이야'", "코드가 C:/aelab 을 박고 있어 정션으로 살렸다 — 경로 박기가 원인", "C:\\aelab 제거. tools/ae/labdir.py|mjs|ps1 · tools/premiere/_labdir.jsx · tools/photoshop/_labdir.jsx — 환경변수 → config → 위로 8단계 폴더 이름 → 옛 경로 순으로 찾는다", "a1 스모크 통과, c11 로 팩 5개×푸티지 112개 누락 0. 원문 log/inbox/2026-09-17_D_오류·비효율.md A5", "fixed"),
    (24, "save.py 가 같은 작업트리의 B 미커밋 파일을 휩쓸어 커밋 — 세 번 (09-16)", "D 가 save.py 를 돌릴 때 B 가 고치던 tools/illustrator 파일이 D 커밋에 섞였다. 매번 사후 통보", "save.py 가 git add -A 로 작업트리 전체를 커밋한다. B·D 가 한 clone·한 브랜치(local/newch-style)를 같이 쓴다", "(1) save.py — 저장 전 git status 를 보여 주고 --only <경로> 로 범위를 제한, 범위 밖 변경이 있으면 멈춘다 (2026-09-17 총괄). (2) 근본 해법은 세션마다 git worktree — log/inbox 제안서(작업체계)", "총괄 컨테이너에서 --only 동작 확인. 로컬 재발 여부는 D·B 보고로. 원문 log/inbox/2026-09-17_D_오류·비효율.md A6", "worked-around"),
    (25, "AE 꾸러미 세 벌이 '중복'이 아니라 drift 였음 (09-16)", "납품 쪽 AE_꾸러미_trad_* 3폴더(3차)와 작업실 pack/trad_rr(4차 박스 단색)이 이름이 같아 중복으로 보였다", "이름만 보고 같다고 판단. 4차는 09-16 14:06 빌드로 아무도 실물을 못 봤다", "푸티지 재생성으로 작업실본과 18/18 일치 확인 후 aep + 세트 aep 5 + mogrt 12 재빌드", "mogrt 안 project.aegraphic PNG 해시로 단색 박스 반영 확인. 4차 실물 확인은 next_step 35. 원문 log/inbox/2026-09-17_D_오류·비효율.md A7", "fixed"),
    (26, "롤링광고 prproj 미디어 10개 끊김 — 사람이 폴더를 옮김 (09-17)", "이정찬이 롤링광고\\옻칠판\\ 내용을 한 단계 위로 꺼내자 라이브_롤링 광고_1.prproj 가 무는 jpg/png 10개 오프라인", "옮기는 주체가 Claude 가 아니면 hookify 규칙이 못 막는다", "프리미어 꺼진 상태에서 \\옻칠판\\ → \\ 45곳 치환 (이정찬 승인). 사람이 옮길 때도 prlinks find 를 먼저 — next_step 39", "prlinks check: 미디어 12·끊김 2 (D:\\ 2개는 원래 끊김). 원문 log/inbox/2026-09-17_D_오류·비효율.md A8 · log/inbox/2026-09-17_B_오류·비효율.md G2", "worked-around"),
    (27, "롤링광고 본문이 CTA 현판에 닿음 — B 보고를 D 가 처음에 부정 (09-16)", "B: 라이브_a_2 본문 끝↔현판 3px, B_2 13px. D 첫 판단 '한지 섬유 오검출'", "fit() 글자 줄이기 바닥값 0.55 라 긴 문구가 줄다 말고 멈춤. 오진은 한 표본으로 원인을 단정하고 색만 보고 모양(연속성)을 안 본 탓", "바닥값 0.34 + 틈 좁히기 + MARGIN 150. B_2 13px 만 섬유(세로 6px 연속 조건)", "git show 12e246e 로 당시 코드 되살려 임계 6조합 재측정 — a_2 전부 3~4px 실제 접촉. 원문 log/inbox/2026-09-17_D_오류·비효율.md A9", "fixed"),
    (28, "AE a3_frame2 판정이 틀렸음 — 쓰기 직후 확인의 거짓 음성 (08월 판정, 09-16 정정)", "8월 '표기 ⑥ 만 작동' 결론. 09-16 디스크에 v1~v4 전부 52,792 바이트로 다 작동", "쓰기 직후 확인해 아직 안 써진 것을 실패로 봄 (brand/EXTENDSCRIPT-TRAPS.md ⑯)", "a3_frame2.jsx 머리 주석 정정. 완료 판정은 반환값이 아니라 <작업실>/log/<잡>.txt 의 판정 줄", "원문 log/inbox/2026-09-17_D_오류·비효율.md C1", "fixed"),
    (29, "일러스트레이터 CS6 호환 저장 → 열 때마다 '이전 버전 텍스트' 창 → COM 300초 타임아웃 (09-17)", "so.compatibility = ILLUSTRATOR17 로 저장한 .ai 를 다시 열면 모달 창. PowerShell 출력은 '열린 문서: 0' 뿐", "CS6(17) 호환 저장이 텍스트를 구판 형식으로 낮춘다. 이 PC 의 Compatibility 열거값은 17·24 두 개뿐(기본 24)", "build_rollad.jsx · build_live.jsx 둘 다 Compatibility.ILLUSTRATOR24 (커밋 6e4b3f9)", "알림 켠 채 열고 40초 뒤 화면 캡처 — 창 없음. 미리보기 6장 재빌드 픽셀 평균차 0.0. 원문 log/inbox/2026-09-17_B_오류·비효율.md A1", "fixed"),
    (30, "모달 창이 뒤에 남은 채 같은 파일 saveAs → 저장 실패 ID -54 (09-17)", "재빌드가 600초 타임아웃을 넘겨 백그라운드로. '파일이 읽기 전용이거나 다른 응용 프로그램에서 사용 중'", "앞선 확인용 열기(issue 29)의 창이 파일을 잡고 있었다", "창 닫기 → 남은 미저장 문서 Close(2) → 재빌드", "재빌드 완료. 원문 log/inbox/2026-09-17_B_오류·비효율.md A2", "fixed"),
    (31, "트팩 원본 .ai 의 끊긴 링크 창에 build_live 가 멈춤 (09-17)", "'연결된 파일 09012023_15.jpg 를 찾을 수 없습니다' 창. 이정찬이 화면에서 발견", "원본(260114_라이브화면구성(2026v).ai)은 저장 금지라 링크를 못 고친다", "build_live.jsx openRef() — app.userInteractionLevel = DONTDISPLAYALERTS 로 열고 finally 로 복원 (커밋 3516487)", "검증됨 — 09-17 16:10·16:48 두 빌드에서 원본 .ai 끊긴 링크 창 없이 끝까지 돌았다 (B 회신 1-2). 원문 log/inbox/2026-09-17_B_오류·비효율.md A3", "fixed"),
    (32, "PowerShell 실행 정책 차단을 못 보고 mv 가 미리보기 6장을 옮김 (09-17)", "powershell -File run.ps1 이 UnauthorizedAccess 로 안 돌았는데 bash 루프가 mv 로 본판 미리보기 6장을 비교 폴더로 옮김", "성공 여부를 안 보는 mv. 실행 정책은 -ExecutionPolicy Bypass 없이 -File 불가", "-ExecutionPolicy Bypass + 결과에 'OK 아트보드 6' 있을 때만 mv. 백업에서 복구", "cmp 로 6장 일치. 원문 log/inbox/2026-09-17_B_오류·비효율.md C1", "fixed"),
    (33, "bash while-read 가 끝 줄바꿈 없는 마지막 줄을 빠뜨려 jpg 1장 누락 (09-17)", "'덮어씀' 7줄, ls 에서 하이라이트_B_2.jpg 만 옛 시각", "jsx 가 map.txt 를 out.join('\\n') 으로 써 끝 줄바꿈이 없었다. read 는 마지막 미완 줄에서 실패를 돌려준다", "수동 복사. 이후 jsx 는 join('\\n') + '\\n'", "8장 cmp 일치. 원문 log/inbox/2026-09-17_B_오류·비효율.md C2", "fixed"),
    (34, "PIL 로 그린 밑줄이 일러스트레이터에서 1px 어긋남 (09-17)", "roll_ad.py rule() 이 y0=151.64 같은 소수 좌표 — PIL 은 151~158행, AI 사각형은 소수 그대로라 위아래 행이 반만 칠해짐", "PIL rectangle 은 끝 좌표 포함·정수 래스터, AI 는 벡터 소수 좌표", "build_rollad.jsx addRect 에서 Math.floor. 좌표 규칙: 폭 = x1−x0+1 · outline 은 안쪽으로 자란다(선 가운데 정렬이면 w/2 들여) · bold=1 = MaxFilter(3) = 같은 색 선 2pt", "하이라이트_B_2 평균차 0.28→0.23, '그 밖' 4468→408px. 남는 차이(▼ 안티앨리어싱 340~408px, 획 가장자리 1px)는 허용. 원문 log/inbox/2026-09-17_B_오류·비효율.md D1~D3", "fixed"),
    (35, "GitHub MCP 인증 실패 — 자리표시자 그대로 실행, 토큰 원문이 대화기록에 남음 (09-17)", "'Authorization header is badly formatted'. 환경변수 값 길이 2('토큰' 두 글자). 값을 넣고 재시작해도 같은 오류", "1차: 안내 명령의 자리표시자를 그대로 실행. 2차: 터미널이 값 넣기 전부터 열려 있어 옛 환경 상속. 그 과정에서 토큰 원문이 B 대화기록에 남았다(저장소 public)", "터미널 새로 열어 해결(get_me → boyjustin76). D 는 대화기록을 bundle 에서 뺐다. 토큰 재발급은 이정찬 몫 — 아직 (next_step 36)", "커밋 기록 전체 키 패턴 검사 0건(log/inbox/2026-09-17_D_오류·비효율.md C11). 원문 log/inbox/2026-09-17_B_오류·비효율.md F1", "open"),
    (36, "hookify 플러그인이 Windows 에서 조용히 안 돎 (09-17)", "훅이 python3 을 부르는데 이 PC 의 python3 은 MS 스토어 가짜. 규칙 파일·stdin 을 cp949 로 읽어 한글 경로에서 예외 → 예외 나면 허용. 차단 사유가 systemMessage 에만 들어가 Claude 는 'denied' 만 봄. PowerShell 도구 훅은 확장자 없는 sh shim 을 못 찾음", "플러그인이 Linux/mac 전제(python3 이름·utf-8 콘솔·sh)", "python3 shim(sh + python3.cmd, PYTHONUTF8=1) · ~/.claude/hooks/hookify_reason.py 로 permissionDecisionReason 채움 · 규칙 정규식을 실행 형태로 좁힘(오탐 4건) · 플러그인 끔. 규칙 3개: block-push-mainline / block-commit-without-status / block-move-without-prlinks", "차단 확인 [E-126]. 공식 hooks 로 옮길지는 log/inbox 제안서(작업체계). 원문 log/inbox/2026-09-17_D_오류·비효율.md B7·B8", "worked-around"),
    (37, "저장소가 private 이라는 인수인계 전제가 틀림 (09-17)", "B 인수인계 요약에 private. GitHub API 는 private:false", "확인 없이 전해진 전제", "이정찬 결정으로 public 유지(decision 25). 커밋 기록 키 패턴 0건. 인박스 부록의 키 모양은 [가림] 처리", "원문 log/inbox/2026-09-17_D_오류·비효율.md C11 · log/inbox/2026-09-17_B_오류·비효율.md G1", "fixed"),
    (38, "worktree 로 옮기자 labdir 가 참고자료 폴더를 못 찾음 — 위로 8단계 한계 (09-17)", "worktree-ps 첫 빌드: '라이브화면 참고자료 폴더를 못 찾았습니다. LIVEFRAME_DIR 환경변수나 config.json 의 labDir 을 주세요.'", "일러스트레이터 labdir.ps1 이 위로 8단계만 걷는데 .claude/worktrees/ps 는 3단계 더 깊다", "11단계로 (84367a5). 포토샵·AE·프리미어의 labdir 는 8단계지만 찾는 폴더가 통합 폴더 안이라 7단계에서 걸려 영향 없음 (B 경로 계산, D 에게 알림)", "worktree-ps 재빌드 통과. 원문 log/inbox/2026-09-17_B_개선안회신.md §2-A", "fixed"),
    (39, "trad.py 가 09-16 에 없앤 폴더를 박고 있었다 — 코드 검토 D-5 가 실제 버그 (09-17)", "tools/style/trad.py:19 REF = '…\\차트명가 NEW\\신규안_v2_전통\\레퍼런스' — 통합 때 지운 자리", "통합 때 해시 비교·prlinks 는 봤지만 파이썬 소스 안에 박힌 경로는 못 봤다. 프리미어 잡 4개(m5_intro2·m6_build·m6_probe·m6_probe2)도 옛 저장소 자리를 박고 있었다", "ref() 가 NEWCH_REF_DIR → 위로 올라가며 <통합>/01_납품_차트명가NEW/신규안_v2_전통/레퍼런스 를 찾고 못 찾으면 멈춘다. 프리미어 잡은 _labdir.jsx repoRootPath(). C:/aelab 폴백도 제거(없는 폴더를 돌려줘 늦게 터지던 것) (44efdf5)", "roll_ad.py --theme lacquer 재생성 3장이 납품본과 바이트 동일. py·mjs·ps1 각각 실행 확인. 원문 log/inbox/2026-09-17_D_개선안회신.md §4 D-5", "fixed"),
    (40, "silences.py 가 ffmpeg 실패를 삼켜 빈 무음 목록을 쓴다 — 코드 검토 E-1 이 실제 버그 (09-17)", "깨진 wav(텍스트 파일)로 돌리면 '무음 0구간 · 0구간' 을 찍고 빈 silences.txt 를 쓴다 → cut_and_srt 가 조용히 받아 컷 0개로 이어질 자리", "subprocess.run 에 check 가 없었다 (ruff PLW1510)", "check=True — CalledProcessError 로 그 자리에서 멈춘다. assemble_longform.duration 도 파일 없음·길이 줄 없음을 각각 한국어로 멈추게 (ffprobe 는 이 PC 에 없어 의존성 안 늘림) (ea36a4a)", "정상 녹음(L08 캠 앞 400초) 28·64구간 그대로. 회귀 45항목 해시 동일. 원문 log/inbox/2026-09-17_E_개선안회신.md §4 E-1·E-2", "fixed"),
    (41, "save.py 가 본류 이름을 박아 두고 있어 worktree 세션의 세이브가 본류로 향함 (09-18, D 발견)", "worktree-D_Video 에서 save.py 를 돌리자 커밋은 제 가지에 됐는데 마지막에 'git push -u origin <본류> 실패 ! [rejected] (non-fast-forward)'. 막힌 건 훅이 아니라 원격이 앞서 있던 우연", "save.py:167 git push -u origin BRANCH — worktree 로 나누기 전엔 맞던 코드. git_guard 는 python 안에서 도는 git 을 못 본다(훅은 Bash 명령줄만) → 세이브 스크립트가 가드 밖", "푸시는 현재 브랜치(rev-parse --abbrev-ref HEAD)로. 본류(MAINLINE)는 git config ac.role=총괄 인 clone 만 민다. upstream 도 두지 않는다. tests/test_save.py 3 (2026-09-18 총괄)", "pytest 통과. 실제 옆가지 세이브 확인은 D·B·E 다음 세이브에서. 원문 log/inbox/2026-09-18_D_훅연결_실측.md §5", "fixed"),
]

DECISIONS = [
    (1, "렌더 방식", "실시간 재생이 아니라 프레임 번호를 받아 그린다",
     "느린 환경에서도 fps 가 정확하고, 같은 프레임을 다시 그려도 결과가 같다", None),
    (2, "캔들 데이터", "실시세 대신 시드 고정 생성기",
     "대본에 맞는 가격 이야기를 만들 수 있고, 컷을 나눠 뽑아도 앞뒤가 어긋나지 않는다", "실제 차트를 그대로 써야 할 때"),
    (3, "프레임레이트", "59.94fps(=29.97x2)로 렌더",
     "대본 타임코드가 드롭프레임이라 프레임 수가 정확히 2배가 되어 29.97 시퀀스에 프레임 단위로 맞는다", None),
    (4, "해상도", "1080p 유지",
     "최종본 롱폼은 720p 지만 축소는 손해가 없고 확대는 손해다", "다른 소스와 규격을 통일하기로 할 때"),
    (5, "자막·타이틀·로고", "렌더에 넣지 않는다",
     "프리미어 프리셋에 이미 있어 겹친다. 차트 위 라벨만 시각자료로 넣는다", None),
    (6, "저장소에 넣을 애셋", "35MB 만 커밋",
     "GitHub 는 파일당 100MB 를 거부하고, 대용량 바이너리는 히스토리에 영구히 남는다", None),
    (7, "로그 저장 형식", "SQLite 단일 파일",
     ".db 한 파일로 끝나고 서버가 필요 없다. PostgreSQL/MySQL 은 서버 프로세스가 있어야 해서 요구와 맞지 않는다", None),
    (8, "모델 운용", "Opus 유지, 노력은 중간. 서브에이전트로 쪼개지 않는다",
     "렌더는 CPU 작업이라 모델과 무관하다. 실제 지연은 브랜드 판단·버그 진단에서 났고 그건 병렬화로 줄지 않는다. "
     "여러 에이전트가 브랜드를 각자 해석하면 익절/손절 회귀 같은 실수가 병렬로 늘어난다",
     "기계적 확인(스틸 겹침 검사 등)만 따로 떼어낼 때"),
    (9, "렌더 병렬화", "컷별로 프로세스를 나눠 코어 수만큼 동시 실행",
     "순차 93초가 45초로 줄고 결과물은 md5 까지 동일하다. 렌더가 결정론적이라 쪼개도 안전하다", None),
    (10, "레퍼런스 확인 방법", ".prproj 를 gunzip 해서 XML 을 직접 읽는다",
     "프로젝트 파일이 gzip XML 이라 프리미어도 MCP 도 필요 없다. 영상 프레임을 찍어 색을 재는 것보다 빠르고, "
     "값이 렌더링을 거치지 않은 원본이라 더 정확하다", None),
    (11, "프리미어 MCP", "이 세션에는 설치하지 않는다. 사용자 PC 용으로 보류",
     "어시스턴트·서버·CEP 커넥터·프리미어가 같은 PC 에 있어야 하는데 이 컨테이너는 리눅스에 프리미어가 없다. "
     "클립을 타임라인에 자동 반입하는 단계가 필요해지면 사용자 윈도우 PC + Claude Desktop 에 깐다",
     "컷 납품 자동화를 시작할 때"),
    (12, "썸네일 편집 도구", "포토샵이 있는 로컬 PC 에서는 psd-tools 대신 Photoshop 2026 을 COM 으로 띄워 ExtendScript 로 편집한다",
     "컨테이너가 psd-tools 로 쓴 .psd 를 포토샵이 끝내 거부한 문제가 여기서는 아예 생기지 않는다. "
     "포토샵이 직접 편집하면 텍스트·효과·그룹이 전부 네이티브로 다시 그려진다. "
     "리눅스 컨테이너에는 포토샵이 없으므로 psdedit.py·thumbnail_png.py 도 그대로 둔다",
     "리눅스에서만 돌려야 할 때"),
    (13, "복제할 베이스 회차", "#1 쿠라마기가 아니라 인물 없는 #6 지지와 저항",
     "#1 하나만 참고하면 그 회차를 그대로 베낀 것이 된다. #1 은 타이틀이 가운데 정렬인 예외 회차이기도 하다. "
     "#2~#6 다섯 회차가 좌표까지 완전히 같은 표준이고, #11 은 주인공 인물이 없는 회차라 #6·#9 계열이다", None),
    (14, "버튼 색", "썸네일 버튼은 brand/ui 원본값 #FF0000/#0000FF, 영상 태그는 theme.js 의 #E80001/#0200F3 을 그대로 둔다",
     "STYLE.md 의 값은 영상 프레임에서 잰 것이고 썸네일 버튼은 브랜드 PNG 를 그대로 쓴다. "
     "둘이 실제로 다르므로 theme 를 건드리지 않고 씬에서 지정한다", None),
    (15, "버튼을 그릴 것인가 뜯어 쓸 것인가", "렌더러(cmgArrow)가 그린다. 단 브랜드 실측 비율을 그대로 넣는다",
     "컨테이너는 포토샵을 띄울 수 없어 brand/thumbnail/btn_*.png 를 뜯어 쓰는 쪽을 택했고 "
     "thumbnail_rule 8 에 '직접 그리지 않는다' 로 적었다. 그 방법은 픽셀이 정확한 대신 라벨이 "
     "매수·익절 두 개로 고정된다. 로컬 PC 는 포토샵이 있어 제약이 없고, 렌더러가 그리면 손절·중립 같은 "
     "다른 글자도 같은 모양으로 나오며 차트 좌표에 바로 붙는다. 실제로 그려 보니 189x90 · 화살촉 0.49h 로 "
     "템플릿 픽셀 실측값과 같았다. **썸네일은 로컬 쪽이 최신이다** — 컨테이너가 소유권을 넘겼다(request 20)",
     "브랜드 버튼 디자인이 바뀔 때"),
    (16, "버튼 크기 계산", "폰트별 상수 대신 잉크 박스에서 브랜드 비율로 역산한다",
     "폰트를 바꿀 때마다 여백이 깨지는 것을 한 번 겪었다. 비율(0.761 / 0.659)은 브랜드 실측이라 불변이고 "
     "잉크 폭·높이만 런타임에 재면 어떤 폰트에서도 같은 모양이 나온다", None),
    (17, "차11 썸네일 채택안", "A(추세추종)와 C(통합) 채택, B(박스권)는 보류",
     "조재희 팀장(파가드AC) 확인 — '1번과 3번이 가장 간결하게 잘 뽑혔다, 두번째는 조금 내용이 많아 보인다'. "
     "B 는 박스 상하단 점선 두 개 + 매수 + 익절 + 누운 이평선이 한 화면에 다 들어가 요소가 가장 많다",
     "박스권 단독 숏폼(#5) 썸네일이 따로 필요해질 때"),
    # 18 인 이유: 로컬 미푸시 커밋이 decision 12~17 을 쓰고 있다
    (18, "프레임 캡처 경로", "page.screenshot 대신 canvas.toDataURL 로 PNG 를 뽑는다",
     "스크린샷은 컴포지터 경유라 프레임당 ~52ms, 캔버스 직접 인코드는 ~21ms 다. "
     "세 경로(screenshot/toDataURL/getImageData)의 픽셀이 md5 까지 같고 mp4 출력도 동일함을 "
     "src/tools/exp-capture.mjs 로 증명한 뒤 바꿨다. 전체 렌더 93s → 26.8s. "
     "예전 경로는 --capture shot 으로 남겨 뒀다", None),
    (19, "옆가지 local/thumb-ch11", "지우지 않고 남긴다",
     "썸네일이 순수하게 로컬에서만 검증됐던 마지막 지점(0652cac)이다 — 팀장 컨펌(A·C 채택) 이후, "
     "tools/photoshop 을 실제로 돌려 3안 재현을 확인한 뒤, 클라우드 렌더 가속이 섞이기 전. "
     "본 브랜치에 전부 병합돼 있어 지워도 커밋은 안 사라지지만(merge-base --is-ancestor 로 확인), "
     "작업자가 셋이고 하루에 충돌이 두 번 난 상황이라 '여기까진 확실히 됐다' 는 기준점에 "
     "이름표를 남겨 두는 값이 이름표 하나 값보다 크다. 렌더 가속은 이 가지에 없다",
     "썸네일이 다시 크게 바뀌어 이 시점이 의미를 잃을 때"),
    (20, "1세대 썸네일 도구 격리", "tools/legacy/ 와 brand/thumbnail/legacy/ 로 이동",
     "thumbnail.py+psdwrite.py 는 효과 손그림·타이틀 폭 역산·포토샵이 거부한 출력 경로라 "
     "지금 돌리면 규격이 어긋난 썸네일이 나온다. 지우지 않고 격리한 것은 획 근사·그림자 "
     "산술 같은 실측 기록이 코드 안에 있어서다. 구세대 애셋 3개(다운샘플 종이배경 등)도 "
     "같이 옮겨 brand/thumbnail/ 에는 현행만 남겼다. 검토 지적 ①·④ 의 실행", "사용자 승인 2026-08-28"),
    (21, "썸네일 회차 스펙을 config.json 한 곳으로", "thumbnail_png.py 가 tools/photoshop/config.json 을 읽는다",
     "회차 이름(group)과 안별 문구(variants)가 로컬 JSX 와 컨테이너 파이썬 양쪽에 따로 박혀 있으면 "
     "한쪽만 고치는 사고가 난다. 컨테이너 전용 키 scene·tags 를 variants 에 얹는 방식이라 "
     "JSX 는 모르는 키를 무시하고 그대로 돈다. scene 은 probe 와 같은 차트(seed 41)를 쓰는 "
     "안에만 달 수 있어 차11 은 A안만 컨테이너로 재현된다 — B(seed 7)·C 는 로컬 전용. "
     "타이틀 캐시도 같이 고쳤다: meta 첫 줄에 spec 해시(문구·크기·색·템플릿·글꼴 mtime)를 적고 "
     "다르면 다시 굽는다. 옛 형식(좌표만)은 자동으로 재생성 판정. 검토 지적 ③·⑤ 의 실행",
     "사용자 승인 2026-08-28"),
    (22, "썸네일 타이틀 크기", "수치를 베끼지 않고 격자박스에 맞춘다 — 넘칠 때만 줄이고 절대 키우지 않는다",
     "규칙 4·5 의 고정 높이(윗줄 141 · 아랫줄 194)는 열 회차 완성본에서 잰 '수치'다. 문구가 길어지면 "
     "같은 높이에서 폭만 늘어나 차트를 덮는다 — 차12 아랫줄이 1488px 로 익절 태그와 붙어 3안이 다 반려됐다 "
     "(2026-09-03 이정찬). 그렇다고 폭에 맞춰 항상 역산하면(옛 컨테이너 방식) 짧은 문구가 거대해진다. "
     "그래서 상자를 상한선으로만 쓴다: 넘을 때만 두 줄을 같은 배율로 줄이고, 안 넘으면 고정 높이 그대로다. "
     "고정 높이 규칙을 버린 게 아니라 그 위에 얹었다. 구현 config.json titleBox + build_thumb.jsx, 규칙 28",
     "상자 밖으로 나가야 읽히는 디자인 요구가 생길 때"),
    (23, "EXTENDSCRIPT-TRAPS.md 이관 여부", "문서로 둔다. DB 는 번호로만 가리킨다", "코드 주석이 번호를 가리키고, 증상→원인→처방의 긴 사연을 한 칸에 넣으면 줄어든다. 문서 원칙 '남의 실측을 요약해 옮기지 마라'. B 판단서(log/inbox/2026-09-17_B_EXTENDSCRIPT-TRAPS_이관판단.md)와 일치", "문서가 40항목을 넘어 찾기 어려워질 때"),
    (24, "오류·비효율 기록 절차", "세션은 log/inbox/YYYY-MM-DD_<세션>_<주제>.md 에 원자료(로그 원문·사용자 원문)를 남기고, 총괄이 issue/constraint_note 문장을 쓴다. DB 행은 반드시 '원문 <파일> <절>' 을 단다", "build_worklog_db.py 는 총괄 전용이라 병목이었다(issue·constraint_note 가 09-01 에서 멈춤). D 제안 09-16, 이정찬 확정 09-17. 총괄이 개선안을 낼 때도 같은 함(log/inbox)에 올리고 로컬이 판단한다", "인박스가 20건 넘게 쌓이면 등재 주기를 정한다"),
    (25, "저장소 공개 여부", "public 유지 (이정찬 결정 09-17)", "인수인계에 private 로 적혀 있었으나 API 는 public. 커밋 기록 키 패턴 0건. 이후 인박스는 키 모양을 [가림]", "키가 한 번이라도 커밋되면"),
    (26, "롤링광고 원본은 코드가 아니라 사람 손질본 .ai", "롤링광고_사용자수정.ai 가 원본. roll_ad.py 로 납품 폴더에 다시 그리지 않는다", "이정찬이 조선100년체·자간·크기·청록을 손봤고 jpg 8장은 거기서 뽑았다. 다시 그리면 손질이 사라진다(읽어보기.txt 경고). 원문 log/inbox/2026-09-17_D_오류·비효율.md C12", "문구를 대량 교체해야 할 때"),
    (27, "tools/cutedit/build_cuts.py 격리", "tools/legacy/build_cuts.py 로 옮기고 머리에 레거시 표기. 도구는 cut_and_srt.py", "이름이 cut_and_srt.py 안의 build_cuts() 와 같아 헷갈렸고 09-01 이후 안 썼다. E 제안(log/E-회신-260916.md §1-2), 총괄 실행 09-17", "숏폼 컷편집을 다시 할 때 cut_and_srt.py 가 못 하는 게 있으면"),
    (28, "총괄의 관여 범위 — 일상 작업은 상태만", "회차별 진행(반려·재작·경로 정정)은 로컬이 한다. 총괄은 저장소·병합·기록·작업체계·도구 품질을 맡고 일상 항목은 해결/미해결만 안다", "이정찬 09-17: '넌 Fable 이기 때문에 그런 곳에 쓰기 아까워'. 미해결 목록은 issue.status='open' 과 next_step 의 담당자(blocked_by)로 본다", "로컬이 막혀 총괄 판단이 필요할 때"),
    (29, "총괄의 피드백 대상 — 에이전트만이 아니라 이정찬도", "총괄은 작업체계·지시 방식·시간표에서 이정찬 쪽 비효율도 근거를 달아 말한다. '주류'라고 말할 때는 출처(공식 문서·채택도)를 붙이고, 내 판단이면 판단이라고 표시한다", "이정찬 09-17: '피드백을 에이전트들에게만 하지 말고 나한테도 해. Mainstream 을 읽을 시간이 없어서 니 말이 곧 정론이다 하고 듣겠다.' 그래서 출처 표시가 의무다 — 내 말이 정론이 되면 틀렸을 때 비용이 그쪽으로 간다. 첫 회차: 개선안 §5 (U-1·U-2·U-4·U-6 은 이정찬 반박으로 정정)", "피드백이 일을 늦추거나, 근거 없이 나갔다고 지적받을 때"),
    (30, "옆가지 이름 — local/* → worktree-*", "새 커밋은 worktree-B_Image(B)·worktree-D_Video(D)·worktree-E_Script(E) — 09-17 저녁 이정찬이 폴더·브랜치 이름을 세션 글자+역할로 확정(runbook 24·25). 첫 판 이름 ps·ae·script 는 본류 병합 뒤 지운다. local/* 다섯 가지는 동결(지우지 않는다 — 검증됐던 마지막 지점의 이름표). 병합은 총괄이 본류로(runbook 23). upstream 은 두지 않는다 — push 는 항상 `git push origin worktree-<이름>`", "2-A 채택으로 B·D 가 09-17 16시 합의해 실제로 땄다. D 질문 3 에 대한 답. 원문 log/inbox/2026-09-17_D_개선안회신.md 질문 3", "세션 시작 폴더(next_step 41)가 바뀌어 claude --worktree 가 브랜치를 스스로 만들 때"),
    (31, "git_guard 설계 — 경로 한정·삭제 포함·인자 없는 push 차단", "이동·삭제 규칙은 작업 폴더 이름(이정찬·차트명가·aelab·cmgwork·pprolab·납품·더원)이 명령에 있을 때만. rm -r·Remove-Item -Recurse·rmdir·DeleteDirectory 도 같은 규칙. 브랜치 이름 없는 push(인자 없음·HEAD)는 브랜치 확인 없이 막고 이름을 쓰게 한다. git 규칙은 명령 머리의 git 만 본다(따옴표 안 grep 은 제외)", "D 실측 6경우 — 경로를 안 가리면 오탐이 잦아 표식을 습관적으로 만들게 되고, 09-16 에 지운 폴더도 누가 무는지 봐야 했다. 인자 없는 push 는 세션 cwd 가 저장소 밖이면 현재 브랜치를 못 읽는 설계 한계 → 단순한 쪽. 원문 log/inbox/2026-09-17_D_개선안회신.md §2-B ③④", "오탐·미탐이 인박스로 보고될 때"),
    (32, "API 키·토큰 두는 자리 — 저장소 밖 C:/Users/user/.secrets/ac_keys.env", "YOUTUBE_API_KEY · HF_TOKEN 등은 이정찬이 발급해 이 파일에. 저장소(public)에도, G드라이브로 가는 꾸러미 zip 에도 넣지 않는다. 코드는 파일을 읽어 dict 로 쓴다", "저장소가 public(decision 25)이고 토큰 노출 전례(issue 35)가 있다. 에이전트는 키 값을 받지 않는다는 기존 규칙과 같은 선. 원문 log/inbox/2026-09-18_E_도구공유_유튜브·한국어NLP.md §1", "키가 세 개를 넘거나 다른 PC 가 생길 때(credential manager 검토)"),
    (33, "완료 보고 양식 — '확인한 것 / 안 본 것' 두 줄 필수", "인박스·회신·세이브 한 줄에 붙인다. 둘째 줄이 비면 보고로 안 친다. 양식 log/inbox/_완료보고_양식.md", "사고 41건을 원인별로 가르면 셋 — 흩뿌려짐(20·23·25·26·39, 처방 있음: 통합 폴더·labdir·prlinks·guard) · 환경 함정(constraint_note 61, 처방 있음: radar) · **검증 범위 오류(10·13·19·21·25·27·28·37 — 일부를 보고 전체를 판단, 처방 없었음)**. 훅으로 못 막는 종류라 글로 강제한다. 주류 유사물: GitHub PR 템플릿 'Testing done / Not tested'. 진단은 이정찬이 딥시크에 물어 가져온 것(09-18), 총괄이 DB 로 확인", "양식이 형식만 남고 '안 본 것: 없음' 이 늘어날 때"),
    (34, "반복 사고는 문서가 아니라 장치로 막는다 — 킴 지적 넷 중 셋을 장치로 (2026-09-18)", "① save.py 기본값 '전체' 폐지 — 총괄 clone 외에는 --only/AC_SAVE_SCOPE 없이 안 돈다 ② git_guard 규칙 4: 역슬래시 든 heredoc 차단(따옴표 없는 <<EOF 는 어디서나, <<'EOF' 는 Windows 에서) → Write/Edit ③ tests/test_no_path_literals.py 래칫 — 코드에 새 절대경로 리터럴이 생기면 시험 실패, 남은 것(pairs.py 2)은 BASELINE 에 적고 고치면 줄인다 ④ 옛 자리는 옮긴 뒤 일주일 안 지운다(runbook 19)", "킴(이정찬이 물어 옴): '같은 실수가 두 번 나오면 환경 문제, 환경 문제는 장치로'. heredoc 은 세 세션이 다 밟고도 처방이 '습관' 이었다(constraint_note 38). 경로 리터럴은 폴더 통합 때 셋 터졌다(issue 20·23·39). 주류 유사물: 안전한 기본값 · pre-commit 훅 · 아키텍처 래칫 테스트", "guard 4 가 오탐(정당한 heredoc)을 자주 내면 — 그땐 Write 도구가 답이지 규칙 완화가 아니다"),
    (35, "배너·대본 판정관 — 팀장 선택 표본 없이는 보류, 수동 수집으로 대체 (2026-09-21)", "LLM 판정관·선호 학습은 팀장이 고른/버린 쌍이 수십 개 쌓일 때까지 보류. 대신 팀장 반려가 올 때마다 고친 문장의 앞/뒤 쌍을 tools/theone/ 에 쌓는다(팀장 부담 0). 방송본 5쌍은 '나간 것의 범위' 기준선으로만 쓰고, 초안 규격을 방송 기준으로 다시 잡지 않는다", "E 실측 09-21: 더원 채널 방송 7편 자막(전부 ASR)을 받아 초안 5쌍과 대조 — 분량↑ 4/5·규칙어↓ 4/5 는 경향이지 법 아님(L01 한 편이 평균을 끌어올림). 이건 before/after 라 A/B 선택이 아니고, 변화 원인(첨삭·애드립·컷편집·ASR)을 팀장에게 못 돌린다. 판정관이 재는 건 취향이 아니라 '나간 것처럼 들리는가' — 그 차이를 흐리지 않는다(E). 이정찬: 팀장 직접 소통 없이는 힘들면 패스", "팀장 선택 쌍이 30개를 넘을 때"),
    (36, "공용 실행기 — 판정 줄 없는 옛 잡은 '경고 통과', 대신 수가 늘지 않게 래칫", "판정 줄 있음 → 성공. 없음 + 시간 안 넘김 + bridge 응답 → 통과(경고). 시간 초과·응답 없음 → 실패. tests/test_verdict_lines.py 가 판정 줄 없는 잡 수(09-21 기준 46)를 상한으로 잰다 — 새 잡은 판정 줄 필수, 옛 잡은 손댈 때 넣는다", "제안서는 '없으면 실패' 였으나 잡 대부분이 옛 것이라 그대로면 아무것도 못 돌린다(D). 완화는 받되 문서가 아니라 장치로 묶는다(decision 34). -StrictVerdict 스위치는 안 만든다 — 래칫이 0 이 되면 기본을 엄격으로 바꾼다. 원문 log/inbox/2026-09-21_D_공용실행기_1단계.md", "BASELINE 이 0 이 될 때 — 그때 '없으면 실패' 로"),
]


REPO_FILES = {
    "tools/cutedit": ("도구", "컷편집 파이프라인(E 소유) — transcribe(전사)·align_take(테이크 정렬)·cut_and_srt(컷·자막, 실측 무음 경계)·make_xml(프리미어 XML)·prlinks(prproj 경로 검사)·srt_rules(14자 큐)·verify_text·grade/(채점대). build_cuts.py 는 2026-09-17 tools/legacy 로"),
    "brand/SHORTFORM-FX-POOL.md": ("문서", "숏폼 1:1 박스 효과 pool 실측 22종 + 팀장 규칙 4개 (최종본 6편 전수 조사)"),
    "brand/EXTENDSCRIPT-TRAPS.md": ("문서", "포토샵·일러스트레이터·AE·프리미어가 같은 ExtendScript 를 쓰면서 서로 밟은 함정 모음. 증상 → 원인 → 처방. 새로 밟으면 여기 적는다"),
    "brand/EDIT-RULEBOOK.md": ("문서", "연출 룰북 — 피드백에서 확정된 규칙 12개 (반려 사례·코드 대응 포함). 피드백 라운드마다 여기에 쌓는다"),
    "scenes/sl-11-4.scenes.js": ("씬", "숏폼 차11-4 추세추종 5컷 — 1080x1080/30fps, 내레이션 46.77초에 동기"),
    "scenes/sl-11-5.scenes.js": ("씬", "숏폼 차11-5 박스권 6컷 — seed 71 튜닝(가짜 돌파 2회·하단 반등·장대 음봉)"),
    "deliver/shortform": ("산출물", "납품한 숏폼 자막·컷리스트 (영상·음성은 드라이브/전달분에만)"),
    "lab/cutedit": ("기록", "CAM 촬영본 전사 원본(cam_transcript.json) — 컷 재현·재검증용"),
    "lab/finalscan": ("기록", "최종본 #1~#10 기계 실측 원자료 — 콘택트시트·프레임별 YDIF/장면점수 csv·"
        "freeze·단일 프레임·카피맵 후보 23장·prproj 드라이브 지도. FX-WHITELIST 의 원천 (2026-09-11 등재)"),
    "lab/ae/AEP-MOGRT-조사보고.txt": ("문서", ".aep/.mogrt 납품 가능성 조사 — 공식 자료 vs 우리 실측, "
        "결론: 파일 직접 쓰기 배제, ExtendScript 로 AE 가 굽게 한다 (next_step 27)"),
    "tools/render-cmg12-layers.mjs": ("도구", "차12 병합 인트로(intro-hook)를 5층으로 렌더 — 1_candle(mp4 바닥)/"
        "2_ma/3_mark/4_text/5_tag(QT RLE 알파). tag 최상위(규칙 ⑭). AE/프리미어 조립 소스"),
    "log/AE-LAB-MANUAL.md": ("매뉴얼", "AE .aep/.mogrt 파일럿(sl-11-4 컷② 손익비) — D 세션용 마일스톤 "
        "A1~A6 + 사용자 단계. 보고는 log/AE-LAB.md, 잡은 tools/ae/jobs/, 옆가지 local/ae-lab"),
    "lab/ae/cut2-base-r63-무주석.png": ("소재", "컷② 무주석 바닥 스틸 (reveal 63, 캔들+20일선만) — "
        "AE 파일럿 A3 의 바닥. 재현 씬은 lab/ae/cut2-base.scenes.js"),
    "scenes/cmg12-cross.build.js": ("씬", "차12 인트로+후킹 연속 클립 1개(intro-hook, 구 컷1~6 병합 2026-09-01) "
        "+ 레이어 분리 빌더. 랠리 확대 실측값·국면표 머리말 참조. 구 cmg12-hook2.scenes.js 는 흡수·삭제"),
    "scenes/cmg12-bridge.scenes.js": ("씬", "차12 말 구간 설명 카드 2클립 — bridge-intro(워시 리스트, 프레임 860)·"
        "bridge-scalp(종이 배경+버튼 반복, 프레임 2939). 스타일은 차명#4 실측 카피, 룰북 §E"),
    "scenes/cmg12-guide.scenes.js": ("씬", "차12 소개·설정 4컷 — RSI 패널 첫 등장, 실측 색 원본(COLOR export)"),
    "scenes/cmg12-fail.scenes.js": ("씬", "차12 본론1·문제제시 5컷 — 씬별 시장 3종(파동·횡보·강추세)"),
    "scenes/cmg12-buy.scenes.js": ("씬", "차12 매수 관점 5컷 — seed161, 55선 재돌파 bar52, 1:2·분할·러너"),
    "scenes/cmg12-sell.scenes.js": ("씬", "차12 매도 관점 3컷 — seed68 5분봉, 45선 재이탈 bar49"),
    "scenes/cmg12-recap.scenes.js": ("씬", "차12 요약 3컷 — 매수 시장 재사용, ①②③"),
    "src/tools/find-events.mjs": ("도구", "MA 교차·배열 + RSI 레벨 교차·70+ 유지 구간 실측 (find-cross 확장판)"),
    "src/tools/probe-labels.mjs": ("도구", "렌더 없이 라벨 클리핑 전수 감사 — 등장~퇴장 0.25초 간격으로 앵커 y 를 계산해 잘림 구간을 표로"),
    "tools/psdedit.py": ("도구", "템플릿 .psd 를 편집한다 — 그룹 복제·텍스트 교체·픽셀 교체"),
    "src/tools/profile-render.mjs": ("도구", "한 프레임이 어디에 시간을 쓰는지 쪼개서 잰다"),
    "src/tools/exp-capture.mjs": ("도구", "캡처 경로 4가지를 실전 루프로 재고 픽셀·mp4 md5 동일성을 대조한다"),
    "log/THUMBNAIL-REVIEW.md": ("문서", "썸네일 코드 검토 보고서 + 로컬 푸시 확인 절차 (2026-08-27)"),
    "log/PREMIERE-LAB-MANUAL.md": ("문서", "프리미어 직접 편집 실험(D 세션) 매뉴얼 — 경로·마일스톤·함정·병합 프로토콜"),
    "log/SCRIPT-AGENT-MANUAL.md": ("문서", "대본 담당(E 세션) 인수인계 매뉴얼 — 자산 지도·숫자·작업 순서·병합 프로토콜 "
        "+ §8 숏폼 .srt 추출 이관(2026-09-01, 자막 14자 규칙·도구·검사)"),
    "tools/cutedit/srt_rules.py": ("도구", "숏폼 자막 규칙의 진본 — split_cue(14자 상한·절/구 선호·의존명사 분리 금지 DP) "
        "+ check CLI. build_cuts.py 가 위임. E 세션 소유(2026-09-01 이관)"),
    "log/SCRIPT-LAB.md": ("문서", "E 의 인계 보고서 — 포인트_차 실측 3종(카피 모드·기준선·New 형식), 기준선 오판 교훈, 미반영 피드백 3건과 참고 원고"),
    "log/PREMIERE-LAB-REPORT.md": ("문서", "D 의 M2~M6 총괄 보고 — 판정표·매뉴얼 정정·등재 요청·판단 요청 4건"),
    "tools/premiere": ("도구", "프리미어 자동화 (D 영역) — run.ps1(BridgeTalk 드라이버)·jobs/*.jsx·verify.py(되읽기 검사기)·presets/30fps sqpreset"),
    "log/RENDER-REVIEW.md": ("문서", "렌더 속도 리뷰 의뢰서 — 코드 지도·실측·열린 질문"),
    "tools/thumbnail_png.py": ("도구", "롱폼 썸네일을 .png 로 뽑는다 — 차트 한 장, 완성본 한 장"),
    "brand/thumbnail/btn_매수.png": ("에셋", "템플릿에서 뜯은 매수 버튼 원본 픽셀 (189x90)"),
    "brand/thumbnail/btn_익절.png": ("에셋", "매수 버튼을 좌우 반전해 #00FF24 로 칠하고 익절 글자를 얹은 것 (185x90)"),
    "brand/thumbnail/틀.png": ("에셋", "템플릿 '틀' 도형 원본 픽셀 (안쪽 투명)"),
    "brand/thumbnail/로고.png": ("에셋", "템플릿 로고 원본 픽셀 (209x52)"),
    "brand/thumbnail/종이배경.png": ("에셋", "템플릿 종이 텍스처 원본 픽셀"),
    "tools/legacy": ("도구", "1세대 도구 격리(실행 금지) — psdwrite.py·thumbnail.py(썸네일 효과 손그림·폭 역산, 2026-08-28)·build_cuts.py(컷편집 1세대, 2026-09-17)"),
    "brand/thumbnail": ("애셋", "템플릿에서 뽑은 로고·종이 배경"),
    "out/thumbnail": ("산출물", "차11 썸네일 2안 (.psd + 미리보기)"),
    "scenes/thumb-ch11.scenes.js": ("씬", "차11 썸네일용 차트 2안"),
    "tools/photoshop/dump_episodes.jsx": ("도구", "완성 회차를 한 장씩 뽑고 레이어 트리를 받아 적는다 — 규칙을 뽑을 때"),
    "tools/photoshop/dump_layer_fx.jsx": ("도구", "레이어 효과(lfx2)를 ActionManager 로 값까지 읽는다"),
    "tools/photoshop/dump_text_runs.jsx": ("도구", "타이틀을 문자 단위로 읽어 한 줄 안에서 색·크기가 갈리는 곳을 찾는다. "
                                           "config 에 runsTarget 을 넣으면 결과물 .psd 도 검사한다"),
    "tools/photoshop/build_thumb.jsx": ("도구", "회차 그룹 복제 → 차트 교체 → 타이틀 교체 → 다른 회차 제거 → .psd/.png/.jpg"),
    "tools/photoshop/config.json": ("설정", "템플릿·차트·출력 경로와 회차 문구 — 컨테이너의 thumbnail_png.py 도 같은 파일을 읽는다(스펙 단일화, decision 21)"),
    "tools/photoshop/run.ps1": ("도구", "포토샵을 COM 으로 띄워 .jsx 를 실행하는 드라이버"),
    "tools/illustrator": ("도구", "일러스트레이터 COM 자동화 — 라이브화면구성.ai 를 짓고 OBS 용 8000x4500 을 뽑는다. tools/photoshop 과 같은 구조로 경로를 안 박는다"),
    "tools/photoshop": ("도구", "포토샵 COM+ExtendScript 로 템플릿 .psd 를 직접 편집한다 — 썸네일은 이 경로가 최신"),
    "tools": ("도구", "숏폼 대본 규칙(shortform.py) 등 대본·자료용 스크립트"),
    "scripts/shortform": ("산출물", "숏폼 대본 초안. 규칙대로 쓴 것"),
    "log/data": ("자료", "롱폼 대본 인덱스·숏폼 대본·세이브 슬롯 (JSON)"),
    "README.md": ("문서", "렌더러 사용법 · 포맷 선택 기준 · 씬 설정 레퍼런스"),
    "brand/STYLE.md": ("문서", "차트명가 브랜드 스펙. 색·레이아웃·폰트·스크립트 6단 구조"),
    "log/WORKLOG.md": ("문서", "이 DB 에서 뽑은 작업 로그"),
    "log/worklog.db": ("데이터", "작업 로그 원본 (SQLite)"),
    "log/worklog.html": ("문서", "브라우저로 보는 작업 로그"),
    "log/build_worklog_db.py": ("스크립트", "로그 DB 생성. 내용을 고칠 때 여기만 고친다"),
    "log/build_worklog_page.py": ("스크립트", "DB → HTML 페이지"),
    "package.json": ("설정", "의존성과 npm 스크립트"),
    "scenes/nq-basic.scenes.js": ("씬", "다크 테마 NQ 6컷 (첫 버전, 브랜드 적용 전)"),
    "scenes/nq-overlay.scenes.js": ("씬", "투명 배경 오버레이 3컷"),
    "scenes/cmg-20ma-runner.scenes.js": ("씬", "차트명가 20일선 4컷. 새 대본은 이 파일을 본떠 만든다"),
    "src/cli.mjs": ("코어", "렌더 CLI. --all --scene --format --stills --reel"),
    "src/market/candles.js": ("코어", "시드 고정 캔들 생성기. 추세/박스권/돌파/눌림/급등락"),
    "src/render/anim.js": ("코어", "이징·타임라인·cue. in 을 생략하면 처음부터 떠 있는 것으로 본다"),
    "src/render/chart.js": ("코어", "캔들·이평선·축·그리드 캔버스 드로잉, 뷰포트 계산"),
    "src/render/layers.js": ("코어", "오버레이 레이어 22종. 레이어를 추가하려면 여기"),
    "src/render/theme.js": ("코어", "테마 프리셋. dark / chartmyeongga"),
    "src/render/engine.js": ("코어", "씬 런타임. 프레임 번호를 받아 그린다"),
    "src/render/scene.html": ("코어", "렌더 스테이지. @font-face 선언이 여기 있다"),
    "src/render/capture.mjs": ("코어", "Playwright 프레임 캡처, 크로미움 경로 탐색"),
    "src/render/encode.mjs": ("코어", "ffmpeg 인코딩. mp4/mov/alpha/webm/png"),
    "src/render/server.mjs": ("코어", "렌더용 정적 서버"),
    "src/tools/install-fonts.mjs": ("스크립트", "폰트를 시스템에 등록"),
    "brand/fonts": ("애셋", "Gmarket Sans / S-Core Dream / 나눔고딕 / 경기천년제목"),
    "brand/logo": ("애셋", "차트명가 로고 7종"),
    "brand/texture": ("애셋", "종이 배경, 모눈종이·땡땡이 패턴, 점선"),
    "brand/ui": ("애셋", "매수·매도 버튼, 시네마스코프, 댓글 유도"),
    "brand/sfx": ("애셋", "효과음 2종"),
    "brand/premiere": ("애셋", "차트명가_메인프리셋(24버전).prproj"),
    "brand/reference": ("애셋", "레퍼런스 영상 캡처 4장. 색을 실측한 원본"),
    "scenes/thumb-ch11-A.scenes.js": ("씬", "차11 썸네일 A안 — 추세추종. 눌림목 매수 53번 → 완전 이격 음봉 익절 87번"),
    "scenes/thumb-ch11-B.scenes.js": ("씬", "차11 썸네일 B안 — 박스권. 순수 range 시장(seed 7)으로 EMA20 이 화면 내내 눕는다"),
    "scenes/thumb-ch11-C.scenes.js": ("씬", "차11 썸네일 C안 — 통합. 박스 점선 + 추세 진입/청산을 한 컷에"),
    "scenes/thumb-ch12-A.scenes.js": ("씬", "차12 썸네일 A안 — 진짜 눌림목. 본편 매수 챕터와 같은 seed 161, RSI 55 재돌파에 빨간 원"),
    "scenes/thumb-ch12-B.scenes.js": ("씬", "차12 썸네일 B안 — 골든크로스의 함정. 횡보 seed 96, 교차 다섯 곳에 빨간 원 + 손절 둘"),
    "scenes/thumb-ch12-C.scenes.js": ("씬", "차12 썸네일 C안 — 70·30의 함정. 강추세 seed 25, RSI 가 70선 위에서 안 꺾인다"),
    "deliver/thumbnail": ("산출물", "채택된 썸네일. out/ 은 .gitignore 라 여기에 따로 둔다"),
    'scenes/newch-style.scenes.js': ('씬', '새 채널 스타일 v1~v4 — 브라우저 창 틀용 차트 본체(seed 11)'),
    'scenes/newch-trad.scenes.js': ('씬', "새 채널 v2 전통 '병풍 위의 차트' — 캔들 + 오방색 이평 3선만. 봉은 data/synth/newch-trad.json(워밍업 60봉)"),
    'data/synth/newch-trad.json': ('데이터', 'seed 11 합성 시장 앞에 워밍업 60봉 — 이평선이 첫 화면 봉부터 그려지게 (tools/style/trad-bars.mjs)'),
    'tools/style/trad-bars.mjs': ('도구', 'newch-trad 봉 데이터 생성기 (워밍업 60봉)'),
    'tools/style/frame.py': ('도구', '새 채널 v1~v4 합성기 — 브라우저 창 크롬·타이틀 블록·툴킷'),
    'tools/style/trad.py': ('도구', '새 채널 v2 전통 합성기 — 한지(실사 닥종이 결)·병풍·창호 띠·낙관·족자. --split 으로 층 PNG+manifest(anim 메타)'),
    'tools/style/frames_clean.py': ('도구', '틀만 조립 완성본 — 가운데 뚫은 투명 PNG 2종(브라우저창·병풍)'),
    'tools/style/vision.mjs': ('도구', 'Gemini/OpenAI 비전 판독 스크립트 (키는 환경변수·레지스트리에서)'),
    'tools/style/pixel.py': ('도구', '영역 픽셀 실측 (검정·흰색 걸러 대표색)'),
    'tools/style/tex/hanji_mulberry.jpg': ('애셋', '실사 닥종이 사진 (Magnific 무료 53876-102589, 출처 표기 조건)'),
    'tools/style/fonts/NanumBrushScript.ttf': ('애셋', '나눔손글씨 붓 (OFL) — 붓 물음표'),
    'tools/ae/trad_motion_pack.py': ('도구', 'anim 메타가 붙은 층만 골라 AE 모션 꾸러미 재료로 (중복 제외)'),
    'tools/ae/trad_motion_preview.py': ('도구', 'AE 캡처로 움직임 GIF·등장 끝 프레임 대조 (프리멀티 알파 처리)'),
    'tools/ae/jobs/c1_trad_build.jsx': ('도구', '전통 층 PNG 65장 → 컴포지션 4개 (trad.aep)'),
    'tools/ae/jobs/c2_trad_check.jsx': ('도구', 'trad.aep 재열기 검사 + 0프레임 캡처'),
    'tools/ae/jobs/c3_trad_motion.jsx': ('도구', "애니메이션 소스 20개 → 컴포지션 + mogrt (낙관 '쾅'·붓 원·족자 펼침)"),
    'tools/ae/jobs/c4_trad_motion_check.jsx': ('도구', 'trad_motion.aep 재열기 검사 + 프레임 캡처 (캡처가 다 떨어질 때까지 다른 잡 금지)'),
    'tools/premiere/jobs/save_quit.jsx': ('도구', '열린 프리미어 프로젝트 전부 저장 후 종료 (경로 없는 프로젝트가 있으면 끄지 않는다)'),
    'tools/style/trad_rr.py': ('도구', '차11-4 손익비 모션 전통판 재료 — 낙관 면·담채·점선·빗금·붓 밑줄 PNG + rr.json/jsx + 요소별 대조 기준(refs)'),
    'tools/ae/jobs/c5_trad_rr.jsx': ('도구', '손익비 전통 — 소스 컴포지션 12 + 전체 1 짓고 aep 저장 (mogrt 는 c5x)'),
    'tools/ae/jobs/c5x_trad_rr_export.jsx': ('도구', '손익비 전통 mogrt 내보내기 — 하나마다 aep 새로 열기 · 저장 안 함 · _only.txt 에 적힌 것만 다시'),
    'tools/ae/jobs/c9_trad_rr_set_aep.jsx': ('도구', '버튼-선 세트 5개(익절선&박스·손절선&박스·진입선·지지선·저항선)를 세트마다 aep 로 저장·재열기 (c5 빌더 차용)'),
    'tools/ae/jobs/c8q_close_quit.jsx': ('도구', '열린 AE 프로젝트를 저장 없이 닫고 scheduleTask 로 AE 를 스스로 종료 (프리미어 다이내믹 링크가 남긴 AE 정리 · 강제 종료 대신)'),
    'tools/ae/jobs/c10_trad_motion_export_one.jsx': ('도구', 'trad_motion 템플릿 하나만 같은 이름으로 다시 내보내기 (저장 안 함 · 팩 밖으로 낸 뒤 검사하고 교체)'),
    'tools/style/trad_bands.py': ('도구', '박스권 세트·더블 볼린저밴드 시안 합성기 (요청 83 보류 — AE 소스화 전 단계)'),
    'tools/ae/labdir.py': ('도구', 'AE 작업실 폴더를 박지 않고 찾는다 (파이썬) — AELAB_DIR → config.labDir → 위로 탐색 → 옛 자리'),
    'tools/ae/labdir.mjs': ('도구', '같은 것의 Node 판 — pack.mjs·diff.mjs·anchors.mjs·scene-export.mjs 가 쓴다'),
    'tools/ae/labdir.ps1': ('도구', '같은 것의 PowerShell 판 — run.ps1·trad_rr_export.ps1 이 점으로 불러 쓴다'),
    'tools/ae/jobs/c11_relink_check.jsx': ('도구', '작업실을 옮긴 뒤 .aep 5개가 푸티지를 스스로 찾는지 실측 (저장 안 함)'),
    'tools/premiere/_labdir.jsx': ('도구', '프리미어 실험실 폴더를 박지 않고 찾는다 (ExtendScript · 잡들이 $.evalFile 로 불러 쓴다)'),
    'tools/premiere/labdir.ps1': ('도구', '같은 것의 PowerShell 판 — run.ps1 이 점으로 불러 쓴다'),
    'tools/style/roll_ad.py': ('도구', '라이브 롤링 광고 배너 11장 — 트팩 원본 좌표 실측 + 전통 톤 (문구는 COPY 한 곳)'),
    'tools/ae/trad_rr_mogrt_check.py': ('도구', 'mogrt zip 안 definition.json 누락 자산 검사 → 실패 이름을 _only.txt 로 (반환값 true 는 증거가 아니다)'),
    'tools/ae/trad_rr_export.ps1': ('도구', '내보내기 → 검사 → 누락분만 재내보내기(최대 3회) → 전부 통과 + aep 그대로일 때만 팩으로 (UTF-8 BOM)'),
    'tools/ae/jobs/c6_trad_rr_check.jsx': ('도구', 'trad_rr.aep 재열기 검사 + 전체 f150·소스 f30·움직임 캡처'),
    'tools/ae/jobs/c7_trad_rr_stretch.jsx': ('도구', '문구를 바꾸면 판이 따라 늘어나는지 시험 캡처 (저장 안 함)'),
    'tools/ae/jobs/c8_close_nosave.jsx': ('도구', '열린 AE 프로젝트를 저장 없이 닫기 (시험 문구가 남은 채 저장되는 사고 방지)'),
    'tools/ae/trad_rr_preview.py': ('도구', '손익비 전통 AE 캡처 vs 합성 기준 픽셀 대조 · 차트 위 움직임 GIF·연속 사진'),
    'tools/ae/jobs/c5b_ess_probe.jsx': ('도구', '실측 1회용 — 소스 필수 속성이 부모 템플릿에 canAdd=false 인 구조 확인'),
    'tools/ae/jobs/c5c_state_probe.jsx': ('도구', '실측 1회용 — 열린 프로젝트 상태 읽기만 (내보낸 뒤 줄어든 프로젝트 확인)'),
    'tools/ae/jobs/c5t_export_trial.jsx': ('도구', '실측 1회용 — mogrt 누락 원인 시험 4종 (주의: 내보내기가 수정된 프로젝트를 저장해 aep 를 오염시켰다)'),
    "log/inbox": ("기록", "로컬 세션 → 총괄 원자료 함 (오류·비효율 로그 원문, 판단 요청, 스킬 목록, 총괄 개선안). 이름 YYYY-MM-DD_<세션>_<주제>.md. DB 로 옮긴 뒤에도 지우지 않는다 — DB 행이 여기를 '원문' 으로 가리킨다 (decision 24)"),
    "log/E-회신-260916.md": ("기록", "E 가 총괄 문의서(09-16)에 답한 것 — srt_rules 회귀 확인·build_cuts 레거시·채점 일치·배너 모델 홀드아웃·L08 사고 두 번·DB 등재 조건"),
    "tools/legacy/build_cuts.py": ("도구", "레거시(2026-09-17 격리) — 1세대 컷편집 스크립트. 실행 금지. 도구는 tools/cutedit/cut_and_srt.py (decision 27)"),
    ".claude/settings.json": ("설정", "저장소에 커밋되는 Claude Code 프로젝트 설정 — 모든 세션이 받는다. 지금은 env(PYTHONUTF8=1·PYTHONIOENCODING)만. 훅 연결은 로컬 판단(인박스 개선안 §2-B)"),
    ".claude/hooks/git_guard.py": ("도구", "PreToolUse 훅 — 본류 push·전체 스테이징(add -A/commit -a)·prlinks 없는 이동을 막고 이유를 돌려준다. D 의 로컬 훅 3규칙 이식. 미연결 — 켜는 법은 파일 머리. 시험 tests/test_git_guard.py"),
    ".claude/skills/radar/SKILL.md": ("지침", "오류 레이더 스킬 — 같은 오류 두 번째·10분 넘게 막히면 tools/radar.py 로 우리 기록→Stack Overflow→GitHub 를 먼저 본다"),
    "tools/radar.py": ("도구", "오류 레이더 — 오류 문장에서 서명을 뽑아 worklog.db(issue·constraint_note)·TRAPS·inbox → Stack Overflow(키 없음 300/일) → GitHub Issues(비인증 10/분) 순으로 찾는다. 의존성 0. --save 로 log/inbox/radar/ 에 남김"),
    "tests": ("검증", "pytest 단위 시험 — test_git_guard(훅 규칙 11)·test_radar(서명·우리 기록·응답 파싱 5). python3 -m pytest"),
    "pyproject.toml": ("설정", "ruff(E·F·B·UP, E501 제외)+pytest 설정. 경고 0 을 요구하지 않는다 — 새 코드와 고치는 줄부터"),
    ".pre-commit-config.yaml": ("설정", "커밋 전 ruff — 1단계는 F·E9(미정의 이름·안 쓰는 import·문법)만 막는다. 켜는 건 각자: pip install pre-commit && pre-commit install"),
    "tools/legacy/premiere_xml.py": ("도구", "레거시(2026-09-17 격리) — 08-31 숏폼 FCP7 XML 생성기. XML 은 tools/cutedit/make_xml.py(컷편집)·src/render/split.mjs(렌더 배치)"),
    "log/inbox/2026-09-17_총괄_작업체계·도구품질_개선안.md": ("기록", "총괄 → B·D·E 개선안 — 이미 적용(§1)·워크트리·훅 이관·레이더·소유자별 코드 품질·User 역할 피드백. 주류 근거 §6. 회신은 항목별 채택/보류/반려"),
    "log/inbox/2026-09-17_B_개선안회신.md": ("기록", "B 회신 — 2-A worktree-ps 채택, B-1·2·3 적용(a75d139·84367a5), D-6 반려, labdir 11단계, 라이브화면 6→10 아트보드·잉크 비율 배치"),
    "log/inbox/2026-09-17_D_개선안회신.md": ("기록", "D 회신 — worktree-ae 채택, git_guard 실측 6경우·구멍 2개 수정, D-1 반려(evalFile 실측), D-5 실제 버그, 세션 시작 폴더 문제 제기, 총괄 질문 3"),
    "log/inbox/2026-09-17_총괄_개선안회신답.md": ("기록", "총괄 답 — 세션 시작 폴더는 이정찬 결정(next_step 41), guard 경로 한정·삭제 포함·인자 없는 push 차단(decision 31), 옆가지 worktree-*(decision 30), 채택 현황표"),
    "tools/ae/_labdir.jsx": ("도구", "AE 작업실 찾기 공용 aeLabDir(start, cfgLabDir) — bridge.jsx(포토샵 쪽)·jobs/_lib.jsx(AE 잡 35개)가 부른다. 복붙 10벌 중 AE 쪽 통일 (D, 44efdf5)"),
    "tools/legacy/roll_ad_check.py": ("도구", "레거시(2026-09-17 격리) — 지운 한지판 전용 롤링광고 검사기 (D)"),
    "log/inbox/2026-09-17_E_개선안회신.md": ("기록", "E 회신 — worktree-script(가지만 전환), E-1 실제 버그 재현·E-2 방식 변경(ffprobe 없이)·E-3 정규화 7벌→textnorm·E-4 srt 파싱→read_srt/sec·E-5 prlinks 표식·E-6 시험 8·E-7 문구, 회귀 45항목 동일, 오류 원자료 2"),
    "tools/cutedit/textnorm.py": ("도구", "한글 정규화 한 벌 — 7곳(align_cut·align_take·cut_and_srt·verify_text·cuetune·banner_model·pairs)이 쓴다 (E, ea36a4a)"),
    "tests/test_cutedit.py": ("검증", "컷편집 시험 8 — split_cue(14자·글자 보존)·read_srt(번호 없음·여러 줄·깨진 타임코드)·make_xml rate/pathurl·fmt·S015 컷 12·check 겹침. 저장소 안 자료만 (E)"),
    "tools/theone/상단배너_공식.md": ("문서", "더원 상단 배너 공식 2판 — 대본 첫 문장을 두 도막으로 쪼개 뒤집는다(앞도막→아랫줄 7~11자, 뒷도막→윗줄 8~14자). 증거표 8편(두 줄 다 뒤집힌 5/8, 예외 S009·S008), 1판이 틀린 이유, 꼬리·화행 슬롯. 09-18 로컬에서 저장소로 (E, 519625b)"),
    "log/inbox/2026-09-18_D_훅연결_실측.md": ("기록", "D — 훅 저장소 연결 완료. ${CLAUDE_PROJECT_DIR} 펼침·exec form args·env 실측, 차단 2종 확인, save.py 본류 푸시 버그 발견(issue 41), heredoc 오탐 요령"),
    "log/inbox/2026-09-18_B_세션폴더_이전완료.md": ("기록", "B — worktree-B_Image 이전 완료, labdir 실측, PYTHONUTF8=1 확인, 옛 ps 정리"),
    "log/inbox/2026-09-18_E_세션시작폴더_적용.md": ("기록", "E — E_Script 폴더·가지 전환, pathurl 윈도우 회귀 4개 동일, 배너 공식 문서 저장소로, 로컬만 남은 문서 둘"),
    "tests/test_save.py": ("검증", "save.py 푸시 대상 규칙 3 — 옆가지는 자기 가지로, 본류는 총괄만, detached 는 안 민다"),
    "tools/theone/상단배너_로직.md": ("문서", "더원 배너 1판(낡음 표시 있음) — 배너 12편 실측표, 규격(윗줄 8~14·아랫줄 7~11), 윗줄 5유형(개수 약속·통념 도발·대비·조건·행동), S016 3안. '아랫줄=최다 출현어' 는 폐기, 유형·규격만 유효. 09-18 총괄이 E 대신 등재"),
    "tools/theone/상단배너_임베딩분석.md": ("문서", "더원 배너 임베딩 채점(KURE-v1·Chroma) — prproj 텍스트+srt 쌍 53개, 아랫줄이 대본 전체에 +0.051 더 가깝다, 아랫줄 띠 0.496~0.592(6편)·윗줄 0.403~0.685, 후보 채점 5개, 다시 돌리는 명령. 대본→인덱스→임베딩→로직 수치 원문. 09-18 총괄 등재"),
    "log/inbox/2026-09-18_B·E_경로끝공백_constraint후보.md": ("기록", "B·E 공동 — 윈도우 경로 끝 공백·마침표 실측표(파이썬·PowerShell, 두 사람이 따로 재현), 사례 셋, 처방 strip(' .'). constraint_note 56"),
    "log/inbox/2026-09-18_E_도구공유_유튜브·한국어NLP.md": ("기록", "E → D·B 도구 공유 — 키 자리(.secrets), yt-dlp 명령 7종·함정 4, YouTube API 한도, 한국어 도구 3종·함정, MCP 자가점검, 안 쓰기로 한 것. constraint_note 57~59 · external_tool 4~10 · env_tool 13~15"),
    "log/inbox/2026-09-18_총괄_등재번호.md": ("기록", "총괄 → B·E — 09-18 오후 등재 번호(constraint_note 56~59 · decision 32 · external_tool 4~10 · env_tool 13~15 · next_step 43·44)"),
    "AGENTS.md": ("지침", "Claude Code 바깥 에이전트(Codex 등)용 — 훅이 대신 막아 주던 규칙(본류 push·이름 없는 push·add -A·작업폴더 이동/삭제·DB 원본·키 자리)을 글로. CLAUDE.md 가 본문이고 이 파일은 차이점만 (2026-09-18)"),
    "tools/mt5": ("도구", "MT5 촬영 파이프라인(D) — mcp.py(MCP 클라이언트)·scenes.py(대본 docx → 비트 → 사건 → 실제 봉 구간 선정, 팀장 차10 기준 5)·capture_scene.py(ChartNavigate 후 창 캡처)·capture.py·shot.py+CMG_Shot.mq5(자체 렌더 캡처 지표)·calibrate.py(봉 격자·가격축 보정 RMS 1.93px). README 있음"),
    "tools/hf": ("도구", "HyperFrames HTML 합성 3벌(D) — ab_pnl(A/B 판)·mt5_frame(MT5 틀 합성)·mt5_calib(좌표 계산 합성)·hyperframes.json. 우리 렌더러에 없는 모양용"),
    "log/data/ref_cha10": ("기록", "팀장 차10 참고자료(D) — script10.txt 대본 본문·기준측정.json 그림 실측·콘티_차트장면.json 엔진이 고른 콘티·읽어보기.md. scenes.py 규칙의 근거"),
    "tools/mcp_probe.py": ("도구", "MCP 자가점검(E) — initialize → tools/list → tools/call 까지 그 자리에서 띄워 본다. 별 수 믿지 말고 띄워 보고 판단(external_tool 10 전례)"),
    "tools/grade_draft.py": ("도구", "대본 초안 채점기(E) — 낭독분만 골라 분량·문장 길이·금지어(부정문·낱말 속 오탐 제외)·근거·수치·반말을 잰다. 차12·차13 초안이 통과"),
    "tests/test_shortform_names.py": ("검증", "shortform 이름 왕복 시험 4 — safe_tail 로 끝 공백·마침표 뗀 뒤 folder_name↔check_name 왕복 (E)"),
    "log/LIVE-SCREEN-MANUAL.md": ("문서", "라이브화면·롤링광고 매뉴얼(B 세션용, 09-18) — 실제로 겪어 확인한 것만, 값은 build_live.jsx 가 최신"),
    "log/차12_더블볼린저_초안.md": ("기록", "차12 더블 볼린저밴드 촬영용 대본 초안(E) — 레퍼런스 사슬대로 재구성, 기간값 20, 규격 채점 통과. 일상 작업(총괄은 상태만)"),
    "log/차13_테스타칼만ATR_초안.md": ("기록", "차13 테스타 칼만 이평선+ATR 촬영용 대본 초안(E) — 새 사슬(일정표→레퍼런스 자막→Pool→완성) 적용. 뼈대는 차13_테스타칼만ATR_뼈대.md"),
    "log/inbox/2026-09-18_D_아스트라_인수인계.md": ("기록", "D → 아스트라 인수인계 — 이 PC 경로 지도(저장소·키·MT5·HyperFrames·시험 결과물)·하던 일과 남은 일 4·실측 함정 11(MT5 7·렌더 3·윈도우 1)·팀장 기준 5. 세션은 worktree 폴더에서"),
    "log/inbox/2026-09-18_D_MT5_MCP연동_시험.md": ("기록", "D — MT5 MCP 연동 시험: 도구 50종 확인, 창 캡처로 차트 배경, 틀·배지·로고 얹어 3초 렌더"),
    "log/inbox/2026-09-18_D_외부도구_HyperFrames·Remotion_실측.md": ("기록", "D — HyperFrames·Remotion 실측: 59.94 유리수 fps·ProRes4444 알파·PNG 시퀀스 확인, 색 정확도 차이"),
    "log/inbox/2026-09-18_D_AB시험_우리렌더러_대_HyperFrames.md": ("기록", "D — A/B 시험: ov-pnl 컷을 우리 렌더러와 HyperFrames 로 각각 300장, 속도 6.9초 vs 31.0초·줄수·픽셀 대조"),
    "log/inbox/2026-09-18_D_대본에서_차트장면_뽑기.md": ("기록", "D — 대본에서 차트장면 뽑기 보고: 팀장 차10 기준 5가지와 실측 함정 5가지"),
    "log/inbox/_완료보고_양식.md": ("지침", "완료 보고 두 줄 — 확인한 것 / 안 본 것 (decision 33). 검증 범위 오류 여덟 건의 처방"),
    "log/inbox/2026-09-18_총괄_공용실행기_제안.md": ("기록", "총괄 → B·D — 어도비 공용 실행기(pre-flight·watchdog·판정 줄) 제안, next_step 46"),
    "tests/test_no_path_literals.py": ("검증", "절대경로 리터럴 래칫 — 코드(tools·src·scenes·log/*.py)에 C:/ 나 /c/Users 문자열이 새로 박히면 실패. BASELINE 은 줄이기만 (decision 34)"),
    "log/inbox/2026-09-22_월요일_전달묶음.md": ("기록", "이정찬이 월요일에 B·D·E 에게 전할 것 한 장 — 토큰 재발급(5분, 첫째)·완료 보고 두 줄·guard 4·save.py 기본값·경로 래칫·파트별 할 일"),
    "log/inbox/2026-09-21_B_constraint56_일러스트레이터_실측.md": ("기록", "B — 일러 saveAs 끝 공백·마침표 네 경우 실측(파이썬과 동일), 오류 문구 the operation was cancelled, TRAPS ⑨-4 pdfCompatible·⑨-5 PrintWindow 모달 읽기"),
    "tools/_com/run.ps1": ("도구", "어도비 공용 실행기(D, 1단계) — 시작 전 앱·프리미어 켜짐 검사(AE 잡이면 중단), Start-Job 시간 제한→taskkill, 로그 '판정' 줄로 성공, 실패 시 <잡>_fail.png/.txt. 앱별 차이는 표 하나(photoshop·illustrator 자리 있음). ae/run.ps1·premiere/run.ps1 이 얹혀 있다"),
    "log/inbox/2026-09-21_D_공용실행기_1단계.md": ("기록", "D — 공용 실행기 1단계 보고: 4단계 반영, 판정 줄 없는 잡 완화(decision 36), 실측 4(성공·통과·실패 경로), PS 5.1 BOM 함정(constraint 63)"),
    "tests/test_verdict_lines.py": ("검증", "판정 줄 없는 어도비 잡 수 래칫(기준 46, 줄이기만). 공용 실행기의 '경고 통과' 완화를 장치로 묶는다 (decision 36)"),
    "log/inbox/2026-09-21_총괄_Jev_판정관_시험제안.md": ("기록", "총괄 — TypeSafe Jev 조사(문서 9쪽)와 우리 자리 판정(판정관 1순위·비트 분류 2순위·가드/글자 수 제외), E 시험 설계 4단계·합격선, 이정찬 결정(미공개 대본 외부 전송)"),
    "log/inbox/2026-09-21_총괄_Jev_시험_D·B.md": ("기록", "총괄 — D·B Jev 시험 설계 각 3(정답 자료·합격선), 하지 말 것(이미지·셈·색·날짜), 알아서 하나, 보고 형식. next_step 50·51"),
    "tools/_com/shot_window.py": ("도구", "대상 프로세스의 보이는 최상위 창 중 가장 큰 것을 PrintWindow(PW_RENDERFULLCONTENT) 로 찍는다(가려져 있어도). 공용 실행기 실패 캡처용. MainWindowHandle 은 안 믿는다(constraint 64). 못 찾으면 exit 2 (D)"),
    "tools/md_to_script_docx.py": ("도구", "초안 .md → 촬영용 스크립트 .docx (E). 표지 줄은 L<번호> (이정찬 09-21)"),
    "log/inbox/2026-09-21_D_공용실행기_남은둘_실측.md": ("기록", "D — 공용 실행기 남은 둘 실측: 프리미어 probe·save_quit 실행(경고 통과·엄격 성공·정상 종료), 프리미어 떠 있을 때 AE 잡 차단(AE 안 뜸 — TRAPS ⑦ 막음), 실패 캡처를 창 단위로"),
}

RUNBOOK = [
    (0, "썸네일 만들기 — 레거시, 쓰지 마라", "1세대 경로였다. 2026-08-28 tools/legacy/ 로 격리",
     "(실행 금지 — 효과 손그림 · 타이틀 폭 역산이라 규격이 어긋난다)",
     "현행: 로컬은 runbook 의 tools/photoshop 항목, 컨테이너는 tools/thumbnail_png.py"),
    (0, "숏폼 — 롱폼 챕터 보기", "어느 챕터를 숏폼으로 뽑을지 고른다",
     "python3 tools/shortform.py chapters 11",
     "이미 만든 숏폼과 일정표에 잡힌 편까지 같이 보여 준다"),
    (0, "숏폼 — 작성 지시서", "챕터 하나로 숏폼을 쓰기 위한 지시서를 만든다",
     "python3 tools/shortform.py brief 11 --chapter '전략 1' --no 4",
     "챕터 원문 · 목표 분량 · 고정 문구 · 앞 편이 던진 질문까지 한 장에"),
    (0, "숏폼 — 자막으로 길이 재기", "나간 편의 실제 길이와 초당 글자수를 확인한다",
     "python3 -c \"import sqlite3;c=sqlite3.connect('log/worklog.db');"
     "print(*c.execute('SELECT folder,seconds,chars,cps FROM shortform_srt WHERE rerun=0 ORDER BY seconds'),sep=chr(10))\"",
     "자막 원본은 각 숏폼 폴더의 '소스+원본' 안에 있다"),
    (0, "숏폼 — 이름 짓기", "회사 규칙대로 폴더·파일 이름을 만든다",
     "python3 tools/shortform.py name 11 --no 4 --title '20일선 추세추종 매매법'",
     "작업 중이면 (중간) 이 붙는다. 확정본은 --final"),
    (0, "숏폼 — 초안 검사", "써 놓은 초안이 규칙에 맞는지 본다",
     "python3 tools/shortform.py check 'scripts/shortform/차11_#4_20일선 추세추종 매매법.txt'",
     "필수/권장/선택 등급으로 나온다. 권장·선택은 어겨도 된다"),
    (0, "세이브", "지금 상태를 되돌릴 수 있는 시점으로 굳힌다",
     "python3 log/save.py \"어디까지 했는지 한 줄\"",
     "로그를 다시 만들고 커밋·태그·푸시까지 한 번에. 태그 이름은 save/YYYY-MM-DD-HHMM (KST)"),
    (0, "슬롯 목록 / 되돌리기", "언제로 돌아갈 수 있는지 보고 되돌린다",
     "python3 log/save.py --list   #  그 다음  git restore --source=save/<...> -- .",
     "checkout 은 구경용, restore 는 실제로 되돌릴 때. restore 뒤에는 다시 save 를 한 번 한다"),
    (0, "대본 키워드 검색", "새 대본의 소재와 겹치는 지난 회차를 찾는다",
     "python3 -c \"import sqlite3;c=sqlite3.connect('log/worklog.db');"
     "print(*c.execute(\\\"SELECT ep,snippet(script_fts,2,'[',']','…',12) FROM script_fts "
     "WHERE script_fts MATCH '눌림목 OR 20일선' LIMIT 10\\\"),sep=chr(10))\"",
     "가중치를 보려면 script_keyword 테이블에서 keyword 로 조회한다"),
    (0, "레퍼런스 회차의 .prproj 받기", "확인 대상 프로젝트 파일을 내려받는다",
     "python3 -c \"import sqlite3;c=sqlite3.connect('log/worklog.db');"
     "print(*c.execute(\\\"SELECT ep,name,drive_id FROM episode_prproj WHERE kind='최종'\\\"),sep=chr(10))\""
     " # 그 다음 curl -sL 'https://drive.usercontent.google.com/download?id=<ID>&export=download&confirm=t' -o ep.prproj",
     "gunzip -c ep.prproj > ep.xml 로 열면 된다"),
    (0, "레퍼런스 .prproj 확인", "프리미어 없이 편집 구성을 읽는다",
     "gunzip -c 'brand/premiere/차트명가_메인프리셋(24버전).prproj' > /tmp/preset.xml"
     " && grep -o '<DisplayName>[^<]*' /tmp/preset.xml | sort | uniq -c | sort -rn",
     "미디어 경로는 <ActualMediaFilePath>, 프레임레이트는 <FrameRate> 를 254016000000 으로 나눈다"),
    (0, "컷별 병렬 렌더", "코어 수만큼 동시에 돌려 시간을 반으로 줄인다",
     "for c in cut1-pullback-entry cut2-profit-runs cut3-fear cut4-early-exit; do"
     " node src/cli.mjs --config scenes/cmg-20ma-runner.scenes.js --scene $c --out out/cmg & done; wait",
     "결과물이 순차 렌더와 md5 까지 같다"),
    (1, "설치", "저장소를 새로 받았을 때", "npm install && npm run setup:fonts", "setup:fonts 는 리눅스만 필요"),
    (2, "씬 목록", "어떤 컷이 있는지 확인", "node src/cli.mjs --config scenes/cmg-20ma-runner.scenes.js", None),
    (3, "구도 확인", "전체 렌더 전에 스틸컷만 빠르게", "node src/cli.mjs --config scenes/cmg-20ma-runner.scenes.js --all --stills 5", "컷당 몇 초. 여기서 겹침을 먼저 잡는다"),
    (4, "전체 렌더", "컷 전부 + 이어붙인 릴", "node src/cli.mjs --config scenes/cmg-20ma-runner.scenes.js --all --format mp4 --out out/cmg --reel", "1080p 4컷에 약 1분 30초"),
    (5, "한 컷만", "고친 컷만 다시", "node src/cli.mjs --config <config> --scene cut4-early-exit --format mp4 --out out/cmg", None),
    (6, "알파 오버레이", "촬영본 위에 차트만 얹을 때", "node src/cli.mjs --config scenes/nq-overlay.scenes.js --all --format alpha", "theme.transparent 가 true 여야 한다"),
    (7, "프레임 수 확인", "타임코드와 맞는지 검증", "ffmpeg -i <file> -map 0:v:0 -f null - 2>&1 | tail -3", "ffmpeg 는 node -e \"console.log(require('ffmpeg-static'))\" 경로"),
    (8, "드라이브 폴더 목록", "공유 폴더 안을 보기 (인증 없이 됨)", "curl -sSL 'https://drive.google.com/embeddedfolderview?id=<FOLDER_ID>#list'", "flip-entry 클래스에서 파일 id 와 이름을 뽑는다"),
    (9, "드라이브 파일 받기", "공유 링크 파일을 컨테이너로", "curl -sSL -o out.bin 'https://drive.usercontent.google.com/download?id=<FILE_ID>&export=download&confirm=t'", "대용량도 confirm=t 로 한 번에 받아진다"),
    (10, "로그 갱신", "작업 로그 다시 뽑기", "python3 log/build_worklog_db.py --md && python3 log/build_worklog_page.py", "DB 가 원본이다"),
    (11, "썸네일 (로컬 윈도우)", "포토샵으로 템플릿 .psd 를 직접 편집",
     "node src/cli.mjs --config scenes/thumb-ch11-A.scenes.js --all --stills 1"
     "  →  차트 png 를 config.json 의 chartDir 로 복사  →  .\\tools\\photoshop\\run.ps1 build_thumb",
     "경로와 문구는 tools/photoshop/config.json 에서 고친다. 포토샵이 있어야 한다 — "
     "리눅스 컨테이너에서는 tools/thumbnail_png.py 나 psdedit.py 를 쓴다"),
    (13, "썸네일 규칙 다시 뽑기", "새 회차를 만들기 전에 완성본 열 장을 다 본다",
     ".\\tools\\photoshop\\run.ps1 dump_episodes",
     "회차 하나만 보고 따라 하면 그 회차를 베낀 것이 된다. outDir/ref/ep00~09.jpg 와 ref_tree.txt 가 나온다"),
    (18, "썸네일 차트를 새 회차용으로 그리기", "타이틀·틀·로고를 피해서 차트 씬을 만든다",
     "scenes/thumb-ch12-A.scenes.js 를 본떠 새로 만든다 — 본편 씬의 market/seed 를 그대로 import 하면 "
     "썸네일과 영상이 같은 장을 보게 된다",
     "네 가지를 꼭 지킨다 — ① duration 0.5 에 모든 레이어를 in: [-1, 0.2] 로 (t=0 스틸에서 "
     "cmgBadge·rsiLevel 은 in[0] 기준이라 안 그러면 사라진다, issue 19) "
     "② chart.include 로 없는 값을 끼워 캔들을 타이틀 자리(아랫줄 x~1563 · y 250~446) 아래로 내린다 "
     "③ 오른쪽 태그는 x 1563 보다 오른쪽에서 시작하게 봉 번호를 고른다 (규칙 26) "
     "④ layout.padRight 40 · 배지는 (1560,1005) — 틀 26px 과 좌하단 로고를 피한다 (규칙 27). "
     "다 그린 뒤 out/stills 의 png 를 눈으로 보고 나서 build_thumb 를 돌린다"),
    (14, "레이어 효과 값 읽기", "템플릿에 실제로 걸린 fx 를 값으로",
     ".\\tools\\photoshop\\run.ps1 dump_layer_fx",
     "DOM 에는 레이어 효과를 읽는 길이 없다. executeActionGet 으로 layerEffects 를 직접 뜯는다"),
    (12, "로그 갱신 (윈도우)", "윈도우에서 DB·MD·HTML 다시 뽑기",
     "$env:PYTHONUTF8='1'; python log/build_worklog_db.py --md; python log/build_worklog_page.py; python log/build_readme.py",
     "PYTHONUTF8 없이는 한글 경로에서 cp949 로 죽는다. --print 는 out/ 이 없으면 요약 단계에서 터지니 빼고 쓴다"),
    (15, "검증 시점으로 돌아가기", "썸네일이 로컬에서만 검증됐던 상태를 보고 싶을 때",
     "git checkout 0652cac        (구경만. 돌아올 때 git checkout claude/futures-youtube-video-edit-fhio4s)",
     "옆가지 local/thumb-ch11 이 같은 커밋을 가리킨다. 렌더 가속 전 코드라 렌더는 느리다"),
    (16, "윈도우에서 명령 줄 때", "PowerShell 5.1 에 bash 문법을 주면 안 된다",
     "cd \"<통합 폴더>\\03_저장소\\AC-Stock-\" 를 먼저 실행하고 다음 줄에 git 명령을 준다 (옛 C:\\cmgwork\\repo 는 2026-09-16 에 없앴다)",
     "PowerShell 5.1 에는 && 가 없다 — '토큰은 이 버전에서 올바른 문 구분 기호가 아닙니다' 로 죽는다. "
     "한 줄로 붙이려면 ; 를 쓰거나 A; if ($?) { B } 로 쓴다"),
    (17, "윗줄 일부만 빨강으로 빼기 (로컬 윈도우)", "config 의 emphasis 로 문자 단위 강조를 건다",
     "config.json 의 그 안(variant)에 \"emphasis\": [{\"text\": \"목표가\", \"color\": \"#FF0000\", \"scale\": 1.174}]",
     "text 는 그 줄 안의 조각으로 찾는다 — 인덱스를 손으로 세지 마라. 같은 글자가 여러 번이면 "
     "nth 로 고른다. color 를 빼면 크기만 바뀐다. line: \"main\" 이면 아랫줄(노랑). "
     "build 에 뽑을 id 만 적으면 그것만 만든다. 넣은 뒤 build_log 의 폭 경고를 봐라 — "
     "윗줄 오른쪽 끝이 1306 을 넘으면 관측 최대폭 밖이다. 키우는 대신 조사를 줄여라(규칙 25). "
     "emphasis 는 포토샵(ActionManager) 전용 — 컨테이너 thumbnail_png.py 로는 못 만든다"),
    (18, "숏폼 컷편집 (원테이크 → 편별 내레이션+자막)", "촬영본에서 NG·디렉팅 멘트를 걸러 편별로 자른다",
     "pip install faster-whisper  →  tools/cutedit/transcribe.py → align_take.py → cut_and_srt.py <작업폴더> --source <원본.mp4> --name <시퀀스이름>   (build_cuts.py 는 2026-09-17 레거시 격리)",
     "스크립트 안 S(작업 폴더)와 대본 경로를 세션에 맞게 바꾼다. 원리: STT(단어 시각) → 대본 문장 정렬 "
     "(역방향 사슬 = 같은 문장 여러 테이크면 마지막 채택) → silencedetect 로 단어 경계 보정 → 스팬 병합·클램프. "
     "정렬 로그의 미매칭·저유사도 행은 반드시 눈으로 확인. 문구를 바꿔 읽은 문장은 오버라이드로 잇는다"),
    (19, "프리미어 프로젝트 경로 검사 — 폴더 옮기기 전·후", "옮기기 전 누가 그 경로를 무는지, 옮긴 뒤 끊긴 클립이 있는지 프리미어 없이 본다", "python3 tools/cutedit/prlinks.py find \"<경로조각>\" \"<검색 루트>\"   →  옮긴다  →  python3 tools/cutedit/prlinks.py check \"<회차 폴더>\"", "검사 범위에서 목적지 폴더를 빼지 않는다. 자동저장본까지 보려면 --all. 옮긴 뒤 **옛 자리는 최소 일주일 지우지 않는다**(킴 지적 09-18 — 늦게 발견되는 참조가 있다). 2026-09-16 L08 사고 두 번(issue 20)의 재발 방지"),
    (20, "오류 레이더 — 벽에 두 번째 부딪히면", "혼자 우회법을 짜기 전에 이미 나온 답을 찾는다 (우리 기록 → Stack Overflow → GitHub)", "python3 tools/radar.py \"<오류 붙여넣기>\"   ·   --file err.txt --repo owner/name --save   ·   --no-web (오프라인)", "스킬 .claude/skills/radar. 총괄 컨테이너는 GitHub 검색 API 가 막혀 MCP search_issues 로. 답은 우리 환경(cp949·ES3·COM)에 맞는지 확인 후 적용"),
    (21, "파이썬 검사 — 커밋 전", "진짜 버그(미정의 이름·안 쓰는 import·문법)와 단위 시험을 돌린다", "python3 -m ruff check tools log tests --select F,E9   ·   python3 -m pytest   ·   (한 번) pip install ruff pytest pre-commit && pre-commit install", "pyproject.toml 이 설정. ruff 기본 규칙 전체는 333건(09-17 기준)이라 강제하지 않는다 — 고치는 줄부터"),
    (22, "세이브 범위 — 같은 작업트리를 나눠 쓸 때", "내 경로만 커밋하고 남의 작업은 두고 간다", "python3 log/save.py --status   ·   python3 log/save.py \"한 줄\" --only tools/illustrator log/inbox   ·   AC_SAVE_SCOPE=\"tools/photoshop tools/illustrator\"", "로그 산출물(worklog.db·WORKLOG.md·worklog.html·README.md·checkpoints.json)은 항상 들어간다. 푸시는 현재 브랜치로 간다(09-18, issue 41) — 옆가지에서 세이브하면 그 가지로. 본류는 ac.role=총괄 만. 로컬은 save.py 대신 git add -- <내 경로> + commit 으로 올려도 된다(E 방식 — DB 재빌드는 총괄 병합 때 한다)"),
    (23, "옆가지 → 본류 병합 (총괄)", "worktree-* 를 본류에 합친다. 겹침을 먼저 재고, 합친 뒤 검사 셋을 돌린다", "git fetch origin  →  겹침: comm -12 <(git diff --name-only $(git merge-base HEAD origin/worktree-ae) origin/worktree-ae | sort) <(같은 식으로 worktree-ps)  →  git merge --no-edit origin/worktree-ae  →  python3 log/build_worklog_db.py --md && python3 -m pytest && python3 -m ruff check tools log tests --select F,E9  →  python3 log/save.py \"병합 …\"", "로컬은 본류에 push 하지 않는다(git_guard). 병합 뒤 로컬은 git fetch && git rebase origin/<본류> 또는 새 worktree. build_worklog_db.py 는 총괄이 번호로 부탁한 줄만 로컬이 만진다(runbook 16 처럼)"),
    (24, "세션 띄우기 — 자기 worktree 폴더에서 (이정찬 확정 2026-09-17)", "저장소 .claude/(UTF-8 env·훅·radar 스킬)은 세션을 시작한 폴더에서만 읽힌다. /cd 로 옮겨도 안 걸린다", "D:  cd \"<통합>\\03_저장소\\worktrees\\D_Video\" ; claude      B:  cd \"<통합>\\03_저장소\\worktrees\\B_Image\" ; claude      E:  cd \"<E 저장소>\\E_Script\" ; claude      총괄(클라우드): 저장소 루트에서 시작됨 — 첫 명령 git config ac.role 총괄", "폴더 이름 = 세션 글자 + 역할 (이정찬이 안 헷갈리게). 브랜치 이름도 같이 간다: worktree-D_Video · worktree-B_Image · worktree-E_Script. 괄호 대신 밑줄 — 괄호는 bash·PowerShell 둘 다 따옴표를 요구한다. 공식 근거: code.claude.com/docs/en/settings 'reads the shared .claude/settings.json from the session's primary working directory'"),
    (25, "worktree 만들기·이름 바꾸기 (D·B) — 공용 clone 에서", "세션당 작업트리 하나. 저장소 밖 03_저장소\\worktrees\\ 에 둔다 (공용 작업트리에 추적 안 된 폴더로 안 보이게 — D 판단)", "cd \"<통합>\\03_저장소\\AC-Stock-\"  ;  git fetch origin  ;  git worktree add \"..\\worktrees\\D_Video\" -b worktree-D_Video origin/claude/futures-youtube-video-edit-fhio4s      옛것 정리(본류 병합 확인 뒤):  git worktree remove \"..\\worktrees\\ae\"  ;  git branch -D worktree-ae  ;  git push origin --delete worktree-ae", "upstream 은 두지 않는다 — push 는 git push origin worktree-D_Video. B 는 .claude/worktrees/ps 안에 뒀던 것을 같은 방식으로 밖으로 옮긴다. E 는 clone 하나를 혼자 쓰니 worktree 없이 폴더 이름만 E_Script 로 (git switch -c worktree-E_Script origin/<본류>). 옛 이름 세 개(ae·ps·script)는 09-17 본류에 다 들어갔으니 지워도 된다"),
]

ENV_TOOLS = [
    ("Node.js", "22.x", "/opt/node22/bin/node", "컨테이너 기본 제공", None),
    ("Playwright", "^1.56", "node_modules/playwright", "npm install", "브라우저는 내려받지 않는다"),
    ("Chromium", "1194 빌드", "/opt/pw-browsers/chromium", "사전 설치본 사용", "capture.mjs 의 resolveChromium() 이 환경변수 CHROMIUM_PATH → 이 경로 → 기본값 순으로 찾는다"),
    ("ffmpeg-static", "7.0.2", "node_modules/ffmpeg-static/ffmpeg", "npm install", "libx264/prores/qtrle/libvpx-vp9 포함. Playwright 번들 ffmpeg 는 webm 만 되므로 쓰지 않는다"),
    ("Pretendard", "1.3.9", "node_modules/pretendard", "npm install", "다크 테마용"),
    ("JetBrains Mono", "5.x", "node_modules/@fontsource/jetbrains-mono", "npm install", "숫자 표기용"),
    ("브랜드 폰트", "-", "brand/fonts", "저장소에 포함", "Gmarket Sans / S-Core Dream / 나눔고딕 / 경기천년제목"),
    ("SQLite", "3.45", "파이썬 내장 sqlite3", "설치 불필요", "로그 DB"),
    ("Photoshop (로컬 PC)", "2026 / 27.9.1", "C:/Program Files/Adobe/Adobe Photoshop 2026", "이미 설치돼 있음",
     "COM ProgID 'Photoshop.Application' 의 DoJavaScriptFile 로 .jsx 를 실행한다. 썸네일은 여기서 편집한다"),
    ("Node.js (로컬 PC)", "24.19.0", "C:/Program Files/nodejs", "winget install OpenJS.NodeJS.LTS", "설치 후 PATH 갱신이 필요하다"),
    ("Python (로컬 PC)", "3.11.9", "-", "winget install Python.Python.3.11", "log/save.py · build_worklog_db.py 실행용. PYTHONUTF8=1 필요"),
    ("Chromium (로컬 PC)", "151 headless shell", "%LOCALAPPDATA%/ms-playwright", "npx playwright install chromium",
     "npm install 만으로는 브라우저가 안 받아진다"),
    ("yt-dlp (로컬 PC)", "2026.08.19", "pip", "pip install -U yt-dlp", "월 1회 갱신 — 유튜브가 추출 경로를 자주 바꾼다. --js-runtimes node"),
    ("kiwipiepy (로컬 PC)", "-", "pip", "pip install kiwipiepy", "형태소·문장 분리. 용어 add_user_word"),
    ("KURE-v1 (로컬 PC)", "nlpai-lab/KURE-v1 · 1024차원", "huggingface 캐시(첫 회 2.2GB)", "pip install sentence-transformers (torch cpu) · tiktoken sentencepiece protobuf", "한국어 유사도. v2 는 3.7배 느려 안 쓴다. tools/theone/banner_model.py 가 쓴다"),
]

DRIVE_MAP = [
    ("폴더", "★ 회사 전체 드라이브 루트 (트레이딩팩토리)", "1JfQCjJgMwHzyq2mpSu-OoiDEIiBpyUXH", None,
     "여기서 다 내려간다. 01_영상_최종 아웃풋 / 02_영상_소스_롱폼 / 03_영상_소스_숏츠 / "
     "04_영상_에셋_디자인 작업물 / 05_문서_기획+스크립트 / 07_문서_채널 관리_일정+성과분석 / "
     "08_문서_프로젝트_툴북(DB) / 11_기타_MT5 보조지표 등 14개"),
    ("폴더", "05_썸네일 / 06_차트명가_주 1회", "1YWaxUBaVcmUE9PwzWrYULfLjO0vpHvH9", None,
     "롱폼 썸네일. 04_영상_에셋_디자인 작업물 → 01_영상(유튜브) 관련 → 05_썸네일 아래. "
     "완성본 .png 11장과 템플릿 .psd 3개가 있다. 차11 은 아직 없다"),
    ("템플릿", "차트명가(롱)_하이라이트 - 복사본.psd", "1K9EkS57eVU58FtAn4dSLognffDxe8E-9",
     "1YWaxUBaVcmUE9PwzWrYULfLjO0vpHvH9",
     "180MB · 1920x1080. 회차별 그룹(#1~#10) 안에 v2(차트) + 타이틀(2줄)이 들어 있고 "
     "'고정' 그룹에 틀과 로고가 있다. thumbnail_rule 이 여기서 나왔다"),
    ("폴더", "각 숏폼 폴더의 '소스+원본' (일부는 '소스'/'원본')",
     "1xpW_VHXA3XZQDvhURn2DthQCwP_gfwtR", None,
     "숏폼 루트 아래 각 26XXXX_[SL_...] 폴더 안에 있다. 자막 .srt 가 여기 들어 있고, "
     "25개 폴더 중 14개에만 있다. 초당 글자수와 단별 분량을 여기서 실측했다. "
     "파일별 드라이브 ID 는 shortform_srt 테이블에 있다"),
    ("폴더", "03_영상_소스_숏츠 / 차트명가(숏)", "1xpW_VHXA3XZQDvhURn2DthQCwP_gfwtR", None,
     "숏폼 대본·소스. 26XXXX_[SL_차NN_#N]제목 폴더 안에 .txt 대본이 있다. "
     "[포인트_차] 폴더는 기획형이라 롱폼 추출 규칙과 무관하다"),
    ("문서", "차트명가(유튜브)_업로드 현황(2026).xlsx", "129vEIFCHgNco6U4mUWoP_4JYOjuIQ2Ba", None,
     "일정표. '유형' 열이 숏폼(SL)=롱폼 추출 / 숏폼(포)=기획형을 가른다. "
     "'추출 원본' 열이 롱폼↔숏폼 대응의 정답"),
    ("문서", "차트명가_숏츠 프롬프터 학습용 데이터.txt", "1zpwz-xtFvHup2EhtXpP4vbW3xOUN0LAI",
     "1xpW_VHXA3XZQDvhURn2DthQCwP_gfwtR",
     "숏폼 대본 30편을 --- 로 이어붙인 모음집. 포인트 편도 섞여 있다"),
    ("프로젝트", "숏츠 기본 양식.prproj", "1Or596wJAfylN6iiL7W9bvK8ScFKijub9",
     "1oxFlIGpiMtO6ru9TCIqSj2WO3YrMBBqZ",
     "숏폼 프리미어 템플릿. 1080x1920 / 30fps. 숏폼 3단계 시작할 때 여기서 실측한다"),
    ("영상", "260703_[SL_차11_#1]20일선 120%활용법(최종).mp4", "11XeXHXJdfGqqAeG4vCPMZIApex65yc_m", None,
     "초당 글자수 실측에 쓴 최종본. 1080x1920 / 30fps / 83.4초, 내레이션 548자 → 6.6자/초"),
    ("폴더", "02_차트명가(최종본)", "1HOplrH8GowSLJPrbxIVvVTCDEL6sUPac", None, "소유 krtradingfactory@gmail.com. 완성본 영상"),
    ("폴더", "└ 롱폼_매매기법(차트명가)", "11eZrZdLgp4MLABX0dNR8dKF1lfMCZmSz", "02_차트명가(최종본)", "차명#1~#10 최종본 mp4. 디자인 실측 원본"),
    ("폴더", "└ 숏츠_영상(차트명가)", "1El3msCDwc3JM4toYMrVYvDQ15V2NC8RN", "02_차트명가(최종본)", "숏츠 60여 편"),
    ("폴더", "차명 회차 소스 루트", "1hqkgml4CV9cZDyD-mJiE-aRTzAX49b3A", None, "회차별 원본·프리미어·기획서"),
    ("폴더", "└ [컷편집]기본 프리셋+가이드", "14V0_LG6eakNf0H7_8WT7O4DAGO0sVTj0", "차명 회차 소스 루트", "컷편집 기준 프리셋"),
    ("폴더", "└ 차명00_중간 광고+아웃트로", "1kU0Oa5iGPgNbHL67wwA0QZryjDw_w8_g", "차명 회차 소스 루트", None),
    ("폴더", "└ 차명01_쿠리마기_지수 이평선", "1r95SHLu_l-X-IcQIkldAEMl0zgqOEIOr", "차명 회차 소스 루트", None),
    ("폴더", "└ 차명06_지지와 저항", "1L-mB1A4G7CQcqzv4XtL_VCJBTL4FERjB", "차명 회차 소스 루트", None),
    ("폴더", "└ 차명11_20일선의 비밀", "1AMis7v5zu0l0oxYpSN6v5knLGOUYa2q1", "차명 회차 소스 루트", "지금 작업 중인 회차"),
    ("폴더", "  └ 소스", "180LPp4FBAmbTo3Vl9DG56PUstPh3QEGU", "차명11_20일선의 비밀", None),
    ("폴더", "  └ 원본", "1Iw6D1rQ5ONIxP4cJa7H1alS6eneW_EjK", "차명11_20일선의 비밀", None),
    ("폴더", "  └ [차명11_최종]프리미어 프로", "1mFChRJUIUAFSc1Ceo2BZajwtsok9z9fp", "차명11_20일선의 비밀", None),
    ("폴더", "  └ [차명11_컷편집]프리미어 프로", "1Th5RFpxrQR8dN1huZFhOr5Nz5ZhzQCkH", "차명11_20일선의 비밀", None),
    ("문서", "[차11_20일선의 비밀] 기획서+스크립트 docx", "1vMJf7EYysVMFv3Sa8bhS8iu7eZ0GX-hj", "차명11_20일선의 비밀", "이번 대본 4줄의 출처. 전략1·2 전문 포함"),
    ("문서", "[차11_20일선의 비밀] 기획서+스크립트 pdf", "16zA0W88DaAfBO1h4j_73__5Jd9Cf21JP", "차명11_20일선의 비밀", None),
    ("문서", "[차XX_기본폼] 롱폼 기획서+스크립트 docx", "1y7rP69dRYtM1IotFjmyAREiSIB689130", "차명 회차 소스 루트", "스크립트 6단 구조 원본"),
    ("파일", "차트명가_메인프리셋(24버전).prproj", "1Udh6JHEBXO-XkfyJGtpFT_bAzoZEdmyD", "차명 회차 소스 루트", "brand/premiere 에 사본 있음"),
    ("압축", "00_메인 프리셋(차트명가) 422MB", "1bfxw8NubZr42brF5kIuRUcsYL-S0mJ4f", None, "해제 765MB/76파일. 가벼운 것만 brand/ 로 커밋"),
    ("영상", "차명#1_쿠리마기_EMA+박스권(최종)", "1Fuhxm4hwSCULvf8wAFlHHZBFZyBf5vcb", "롱폼_매매기법(차트명가)", "매수 태그·익절손절 영역 실측에 쓴 영상"),
    ("영상", "차명#6_지지와 저항(최종)", "18WxhXSFxdjM5foQ4PuqmhiQ-Gq_wu1BN", "롱폼_매매기법(차트명가)", None),
    ("영상", "260711_[SL_차11_#3] 20일선이 중요한 이유", "1_wTyqenNmieugt3zEOXaoMKLO9LxCcEy", "숏츠_영상(차트명가)", "숏츠 룩 참고"),
    ("영상", "260703_[SL_차11_#1] 20일선 120%활용법", "11XeXHXJdfGqqAeG4vCPMZIApex65yc_m", "숏츠_영상(차트명가)", None),
]

LAYERS = [
    ("titleCard", "공통", "전체 화면 타이틀 카드", "kicker, title(배열이면 여러 줄), subtitle, size, in, out"),
    ("caption", "공통", "하단 자막 · 로어서드", "title, text, accent, in, out"),
    ("hud", "공통", "좌상단 종목 / 현재가 / 등락", "symbol, name, tf, basePrice"),
    ("hline", "공통", "수평 가격선 + 라벨", "price, label, color, priceTag, dash, growDur"),
    ("zone", "공통", "가격 밴드", "from, to, label, color, opacity"),
    ("marker", "공통", "삼각형 진입 마커 + 펄스", "bar, dir, price, label, pulse"),
    ("tradeBox", "공통", "손절·익절 박스와 손익비", "entry, tp, sl, fromBar, toBar, showRR"),
    ("counter", "공통", "숫자 카운트업 패널", "label, from, to, prefix, suffix, signed, panel, align"),
    ("statCard", "공통", "결과 요약 카드", "title, badge, rows[{k,v,tone}]"),
    ("label", "공통", "지시선 달린 자유 라벨", "bar, price, text, dx, dy"),
    ("cmgProfit", "차트명가", "진입가와 현재가 사이 평가손익 영역", "entry, fromBar, pulse, pulseSpeed, pulseAmount"),
    ("cmgLevel", "차트명가", "익절·손절 굵은 선 + 컬러 박스 라벨", "price, fillTo, fill, color, label, labelSize, thickness, fromBar, labelStyle('inzone' 은 변형)"),
    ("cmgArrow", "차트명가", "매수·매도 화살표 태그", "bar, price, dir('buy'|'sell'), label, size(기본 36), gap, popDur(0이면 등장 연출 없음), halo"),
    ("cmgBadge", "차트명가", "브랜드 배지 (손익비·종목 등)", "text, x, y, size, color, align, border"),
    ("cmgText", "차트명가", "화면 좌표 고정 카드 텍스트 — 말 구간 설명 카드 (차명#4 실측 문법: 흰 외곽선 검정 "
        "타이포, 형광펜 #F8D890, 예고 베이지 #F9E9BF→본색)", "y, x, size, text|parts[{text,color,hl}], activeAt, preColor, hlColor, align"),
    ("cmgNote", "차트명가", "차트 위 외곽선 주석", "text, bar, price, x, y, size, color"),
    ("cmgCircle", "차트명가", "손그림 색연필 원 강조", "bar, price, rx, ry, width, drawDur, turns"),
    ("cmgUnderline", "차트명가", "손그림 빨간 밑줄", "bar, price, dy, width, align, thickness, drawDur"),
    ("cmgMissed", "차트명가", "놓친 구간 빗금 + 화살표", "from, to, fromBar, color, arrow(false 로 화살표 끔), arrowFrac"),
    ("image", "공통", "이미지 (로고 등). engine 이 미리 로드", "src, x, y, width, align, opacity"),
    ("flash", "공통", "컷 전환용 플래시", "at, dur, strength, color"),
    ("watermark", "공통", "채널명 워터마크", "text, x, y, opacity, align"),
    ("letterbox", "공통", "상하 시네마 레터박스", "height, color"),
    # 2026-09-03 보정 — 코드(layers.js LAYERS 29종)에 있는데 카탈로그에 빠져 있던 6종
    # (레드팀 준비 중 발견, RSI 경계 담당 rsiLevel/rsiZone 이 문서 사각지대였다)
    ("fill", "공통", "화면 전체 단색 덮개 (카드 씬 바탕)", "color, opacity"),
    ("cmgTrace", "차트명가", "이평선 접선 덧칠 강조 (드로우온)", "overlay(ma 인덱스), fromBar, toBar, flatten, width, color, drawDur"),
    ("rsiTrace", "차트명가", "RSI 라인 덧칠 강조", "fromBar, toBar, width, color, drawDur"),
    ("cmgCross", "차트명가", "화면 전체 손그림 ✕", "x, y, size, width, color, drawDur"),
    ("rsiLevel", "차트명가", "RSI 패널 기준선 (55/45/70/30)", "v, label, color, width, dash, growDur"),
    ("rsiZone", "차트명가", "RSI 패널 구간 밴드 (과열/과매도)", "from, to, color, fromBar, toBar, growDur"),
]

SCENE_OPTIONS = [
    ("scene", "duration", "컷 길이(초). 프레임 수 / fps 로 넣는다", "f(250) = 250*1001/60000"),
    ("scene", "fadeIn / fadeOut", "컷 안에서의 페이드. 이어지는 컷에는 쓰지 않는다", "0.3"),
    ("scene", "camera.shake", "화면 흔들림 키프레임. 난수를 안 써서 다시 렌더해도 같다", "[{t:0,v:0},{t:0.3,v:1}]"),
    ("chart", "reveal", "몇 번째 캔들까지 그릴지. 키프레임을 주면 그려지는 애니메이션", "[{t:0,v:34},{t:2.6,v:43,ease:'inOutCubic'}]"),
    ("chart", "zoom", "보이는 캔들 수 배율. 1보다 작으면 더 넓게 보인다", "[{t:0,v:1},{t:5,v:0.5}]"),
    ("chart", "priceOffset", "세로 이동", "[{t:0,v:0},{t:1.2,v:30}]"),
    ("chart", "visibleBars", "한 화면에 보이는 캔들 수", "40"),
    ("chart", "include", "화면에 반드시 들어와야 하는 가격들", "[23665]"),
    ("chart", "layout.rightGap", "마지막 캔들 오른쪽으로 비워 둘 칸 수", "6"),
    ("chart", "ma", "이동평균선", "[{type:'ema',period:20,width:5}]"),
    ("chart", "showGrid / showAxes / showLast", "그리드·축·현재가 표시 여부. 차트명가는 전부 false", "false"),
    ("layer", "in", "[시작초, 등장시간]. 생략하면 처음부터 떠 있는 것으로 본다", "[1.5, 0.4]"),
    ("layer", "out", "[시작초, 퇴장시간]", "[3.45, 0.5]"),
    ("project", "fps / fpsExpr", "유리수 프레임레이트는 fpsExpr 로 정확히 넘긴다", "60000/1001 · '60000/1001'"),
    ("market", "seed / segments", "가격 이야기. seed 를 바꾸면 같은 구조의 다른 캔들", "trend / range / breakout / pullback / spike"),
]

TRADE_SETUPS = [
    ("cmg-20ma-runner", "일봉 (종목 표기 없음)", 11, 95, 23795, 23665, 24055, "1 : 2", 42, 53, 24977.5, "9.1R",
     "20일선 눌림목 진입 → 1:2 조기 익절 → 이후 추세는 9.1R 까지. 손절폭 130pt"),
    ("nq-basic", "NQ 5분봉", 42, 82, 24688.75, 24614.75, 24836.75, "1 : 2", 68, 80, 24871.5, "2.4R",
     "박스권 가짜 이탈 후 되돌림 롱. NQ 1계약 = 1포인트당 $20 → 148pt = $2,960"),
]

CONSTRAINTS = [
    ("ctx.filter 블러 비용", "ctx.filter='blur()' 를 켠 채 chart.frame() 을 부르면 캔들·꼬리·이평선 "
     "드로우콜 하나하나에 블러 패스가 따로 돈다 — 브리지 인트로 1794프레임에 80분 (프레임당 2.7초, "
     "r8~r9 때 '블러는 백그라운드로 돌린다'며 참고 지나갔던 그 느림의 정체)",
     "engine.js 가 블러 씬에서는 차트를 오프스크린 캔버스에 완성한 뒤 그 한 장에만 blur 를 걸어 "
     "drawImage 로 합성한다 (2026-09-02 수정). 같은 클립이 212초 — 23배. 이제 블러 씬도 "
     "포그라운드 렌더면 충분하다"),
    ("저장소에 없는 것","템플릿 차트명가(롱)_하이라이트 - 복사본.psd(180MB)와 완성본 레퍼런스 PNG 10장은 "
     "저장소에 없다. out/ 도 .gitignore 라 뽑아 낸 썸네일 자체는 안 들어간다",
     "셋 다 회사 드라이브에 있다 (drive_map 참고). 로컬 PC 에는 이미 있으니 문제가 안 된다. "
     "저장소에 있는 것은 그 파일들에서 뽑아 낸 값과 픽셀이다 — "
     "thumbnail_rule · thumbnail_fx.json · brand/thumbnail/*.png"),
    ("psd-tools 레이어 뽑기", "composite() 가 투명한 빈 그림을 주는 레이어가 많다 "
     "(꺼져 있는 그룹 안, 아트보드 문서, 복제 직후)",
     "topil() 은 레이어에 저장된 픽셀을 그대로 준다. 효과가 필요하면 그룹을 solo() 로 켠 뒤 composite. "
     "원본 회차 그룹은 대부분 꺼져 있어서 복제본도 꺼진 채로 나온다 — 켜지 않으면 빈 그림이다"),
    ("PSD 텍스트 EngineData", "스타일 구간 배열 RunArray 와 길이 배열 RunLengthArray 의 개수가 다르면 "
     "포토샵이 '프로그램 오류로 인하여 열 수 없습니다' 로 파일을 거부한다",
     "글자를 바꿀 때 두 배열을 함께 손본다. 길이 합은 글자 수(문단 끝 \\r 포함)와 같아야 한다. "
     "tools/psdedit.py 의 Template.check() 가 저장 전에 자동으로 잡는다"),
    ("드라이브 업로드", "Google Drive MCP 는 파일 내용을 base64 로 tool 인자에 실어 보낸다",
     "25MB 파일이면 인자가 3천4백만 자가 되어 한 번의 호출로 못 보낸다. "
     "채팅 첨부(파일당 30MB)로 보내고 사람이 드라이브에 넣는다"),
    ("썸네일 PSD 크기", "템플릿을 그대로 편집하면 180MB 를 물려받는다",
     "쓰지 않는 회차 그룹을 drop_group 으로 들어내고(180→41MB) "
     "교체한 차트를 RLE 로 압축하면(41→25.5MB) 채팅으로 보낼 수 있다"),
    ("psd-tools 합성", "아트보드가 있는 문서는 composite() 가 빈 화면을 준다",
     "원본 템플릿도 똑같다. 회차 그룹만 따로 composite(force=True) 해서 캔버스에 얹는다"),
    ("psd-tools 텍스트", "텍스트를 바꿔도 미리보기에는 예전 글자가 보인다",
     "레이어에 래스터가 캐시돼 있어서다. 포토샵도 열 때 그 픽셀을 그대로 보여 준다. "
     "Template.bake_text() 가 EngineData 와 픽셀을 함께 새 글자로 바꾼다. "
     "획·그림자는 그리지 않는다 — lfx2 가 살아 있어 포토샵이 얹어 준다"),
    ("레이어 복제", "lyid(레이어 ID)를 새로 매기지 않으면 복제본이 합성에서 통째로 빠진다",
     "clone_group 이 최대 ID+1 부터 다시 매긴다"),
    ("PSD 레이어 이름", "옛 pascal 이름 칸은 macroman 이라 한글이 안 들어간다",
     "한글을 cp949 로 인코딩한 바이트를 macroman 으로 읽은 값을 넣는다. 원본도 그렇게 돼 있다. "
     "포토샵이 읽는 진짜 이름은 luni(유니코드) 블록이다"),
    ("채팅 첨부", "파일당 30MB", "무손실 알파는 VP9 알파 webm 으로 압축해 보내고, 무손실본은 로컬에서 재생성"),
    ("GitHub 파일 크기", "파일당 100MB 하드 리젝트", "대용량 소스는 저장소에 넣지 않고 드라이브에 둔다"),
    ("GitHub API", "api.github.com 은 프록시 차단", "MCP github 도구와 git push/pull 만 사용"),
    ("비공개 저장소", "릴리스 에셋을 curl 로 못 받음", "드라이브 공유 링크 사용"),
    ("컨테이너", "세션이 끝나면 디스크가 사라짐", "남길 것은 반드시 커밋. 원본 자료는 drive_map 을 보고 다시 받는다"),
    ("Playwright 브라우저", "패키지가 기대하는 빌드 번호와 사전 설치본이 다를 수 있음", "resolveChromium() 이 경로를 찾아 준다. playwright install 을 돌리지 않는다"),
    ("프리미어 MCP", "어시스턴트·서버·CEP 커넥터·프리미어가 모두 같은 PC 에 있어야 함",
     "원격 리눅스 컨테이너에서는 쓸 수 없다. 레퍼런스 확인은 .prproj 직접 파싱으로 대체하고, "
     "타임라인 자동 반입이 필요해지면 사용자 윈도우 PC 에 설치한다"),
    ("렌더 병렬화", "코어 수만큼만 빨라짐 (4코어에서 2.07배)",
     "컷 수보다 코어가 적으면 가장 긴 컷이 하한이 된다"),
    ("최종본 규격", "채널 롱폼 최종본은 1280x720 / 30fps", "컷씬 소스는 1080p / 59.94fps 로 납품. 축소는 손해가 없다"),
    ("저장소 공개 범위", "2026-08-27 저녁에 private 으로 전환됐다(사용자 의도). "
     "익명 접근이 전부 막힌다 — api.github.com 은 404, git ls-remote·fetch 는 인증을 요구한다",
     "clone·fetch·push 모두 자격증명이 필요하다. 윈도우는 Git Credential Manager 가 브라우저 로그인을 "
     "띄우는데, 비대화형 셸에서는 그 창을 못 띄워 막힌다. 사람이 터미널에서 한 번 로그인하면 캐시된다. "
     "raw.githubusercontent.com 으로 파일을 바로 읽던 절차도 이제 안 된다"),
    ("CRLF 파일의 줄 비교",
     "윈도우 CRLF 파일에서 l == '=======' 같은 줄 비교는 '\\r' 이 붙어 어긋난다 — "
     "로컬 세션의 충돌 해소 스크립트가 이걸로 자기 변경을 통째로 날렸다 (2026-08-28, config.json)",
     "줄 단위 비교는 rstrip 후에 한다. 그리고 해소 직후 결과를 파싱해서(JSON.parse 등) 되읽어 확인한다 — "
     "눈으로 보면 멀쩡해 보여서 못 잡는다. 복구는 git stash drop 이 커밋 객체를 남기는 성질로 했다"),
    ("프리미어 COM",
     "프리미어에는 COM 자동화 ProgID 가 없다 — Premiere.Application 류 없음, Adobe.Premiere.* 12개는 "
     "전부 파일 연결, CLSID LocalServer32 전수 스캔에도 자동화 서버 없음 (26.3.2 실측)",
     "BridgeTalk 경유가 검증된 길이다: PowerShell → Photoshop.Application(COM) → bridge.jsx → "
     "BridgeTalk → premierepro-26.0. 설치·관리자 권한·미서명 확장 불필요. 단 이 경로는 포토샵 설치에 "
     "의존한다 — 포토샵이 빠지면 프리미어 자동화도 같이 죽는다. 탈출구인 Scripts\\Startup\\ 은 "
     "상시 편집용 PC 라 권하지 않는다(켤 때마다 스크립트가 돈다)"),
    ("BridgeTalk 본문 이스케이프",
     "잡 소스를 BridgeTalk 본문에 실으면 역슬래시 이스케이프가 전송 중 한 번 더 풀린다 — "
     "\\t 가 프리미어에서 글자 t 로 실행됐다",
     "본문에는 '이 파일을 실행해라' 한 줄만 보내고 잡 소스는 프리미어가 디스크에서 직접 읽게 한다"),
    ("파일 안에 적힌 경로",
     "산출물 안의 경로(<ActualMediaFilePath> 등)는 그 파일을 만든 환경을 말할 뿐, 지금 이 PC 의 "
     "마운트 사실이 아니다 — 프리셋의 D:\\ 가 그랬다(사무실 PC 실측은 G:\\내 드라이브\\, 문자는 가변)",
     "경로를 기록할 때는 드라이브 문자를 박지 말고 '드라이브 안 상대 경로 + config 의 마운트 지점 한 곳' "
     "으로 적는다. 포토샵 config.json 의 template/chartDir 이 그 형태다. "
     "실측 대응표: 편집자 PC 'D:\\01_구글 드라이브(파가드AC)\\트레이딩팩토리\\...' = "
     "사무실 PC 'G:\\내 드라이브\\트레이딩팩토리\\...' — 트레이딩팩토리 아래는 동일. "
     "이 차이 때문에 프리미어 자동 탐색이 실패하고 미디어가 전부 오프라인이 된다"),
    ("프리미어 릴링크",
     "relinkMedia 라는 API 는 없다. 릴링크하면 OfflineReason 이 사라지고(14→0) FrameRate 집계가 바뀐다"
     "(자리표시자 대신 진짜 값을 읽는다) — 정상이다",
     "projectItem.changeMediaPath(path, true) 가 답이고 canChangeMediaPath(path) 로 미리 물어볼 수 있다. "
     "성공 판정은 반환값 말고 getMediaPath() 를 다시 읽어서. verify 는 --allow-lost OfflineReason:-N 으로 선언"),
    ("프리미어 모달",
     "모달 대화상자가 뜨면 그 뒤의 모든 잡이 TIMEOUT 이고 로그도 안 남는다(잡이 끝나야 파일을 쓰므로). "
     "createNewSequence 가 대표적",
     "위험한 호출 앞에서는 로그를 먼저 flush 한다. TIMEOUT 이 반복되면 프리미어 창 목록부터 열거해라 — "
     "vis=True en=True 인 창이 모달이다. WM_CLOSE 로 닫으면 살아난다"),
    ("위스퍼가 단어 안에 침묵을 삼킨다",
     "word_timestamps 가 긴 침묵을 앞 단어에 붙인다 — '누워버리면' 이 88.16~92.38(4.2초)로 나왔는데 "
     "실제 발화는 1초, 나머지는 무음. VAD 필터로도 안 잡힌다. 이대로 컷을 만들면 죽은 공백이 그대로 남는다",
     "ffmpeg silencedetect(-35dB, 0.8s+) 실측으로 단어 경계를 보정하고, 행 안 1.2초+ 공백은 스팬을 쪼개 잘라낸다. "
     "tools/legacy/build_cuts.py(격리됨) 의 SILENCES 가 그 목록"),
    ("컨테이너에서 나가는 파일 한도",
     "SendUserFile 은 파일당 30MiB 를 거부한다. 드라이브 커넥터 create_file 은 base64 를 툴 호출에 실어야 해서 "
     "수 MB 만 돼도 컨텍스트를 태운다 — 영상 업로드 경로가 아니다",
     "텍스트(자막·컷리스트)만 커넥터로 드라이브에 직접 올리고, 영상·음성은 zip 으로 묶어 SendUserFile(30MiB 미만 단위). "
     "넘으면 재인코딩(참고영상 720p)이나 분할. 드라이브 폴더 실내용 확인은 embeddedfolderview(runbook 8)가 정답 — "
     "커넥터 검색은 회사 계정 파일을 통째로 빼먹는다"),
    ("차트 라벨을 뷰포트 상단 근처에 두지 마라",
     "뷰포트 상단은 '형성 중인 캔들'의 부분 고가를 따라 프레임마다 숨쉰다. cmgNote 를 상단 여백에 앵커하면 "
     "어느 프레임에선 멀쩡하고 어느 프레임에선 잘린다 (sl-11-4 컷3 에서 두 번 당함)",
     "include 로 바닥을 고정한 뒤 하단 여백에 두는 게 안정적이다. 왼쪽 창 경계 근처는 align: 'left' + dx 로. "
     "스틸은 라벨이 떠 있는 시각(in~out 사이)으로 찍어서 확인해라"),
    ("줌 컷의 절대가 라벨은 소리 없이 화면 밖으로 나간다",
     "줌인 컷은 뷰포트 가격폭이 좁아지고 상단은 스무딩(_priceRange 가중평균)까지 얹혀서, 넓은 화면 기준으로 "
     "잡은 절대 가격 라벨이 통째로 프레임 위로 나가 버린다. 오류도 경고도 없어서 렌더가 '된 것처럼' 보인다 "
     "(차12 buy-entry '양봉 마감' — 코드 버그로 오인해 한참 헤맴)",
     "줌 컷 안의 라벨은 절대가 대신 기준 캔들 price + dy 픽셀 오프셋으로 앵커한다. 의심되면 스틸에서 라벨 "
     "유무부터 세라 — 안 보이면 위치 문제지 레이어 문제가 아니다"),
    ("자막의 진본은 프리미어 프로젝트에서 방금 내보낸 .srt 뿐이다",
     "드라이브에 있던 차명12 srt 는 프로젝트 안에서 자막이 수정된 뒤 다시 내보내지 않은 구버전이었다 — "
     "그걸 기준으로 26컷을 동기했다가 전부 재작업했다 (컷 경계가 +2~19초씩 어긋남)",
     "롱폼 동기 작업 전에 사용자에게 '프로젝트에서 지금 내보낸 srt' 를 요청한다. 폴더에 있는 srt 는 "
     "만든 날짜가 컷편집 수정일보다 뒤인지부터 의심한다"),
    ("zip 납품물 안에 한글 파일명을 넣지 마라",
     "리눅스 zip 은 한글 이름을 UTF-8 로 넣는데, 윈도우 기본 압축 풀기가 이를 CP949 로 읽다 '압축풀기를 "
     "완료할 수 없습니다' 로 통째로 실패한다 (SL 차11-4 v7 · 차11-5 v5 패키지가 사용자 PC 에서 실제로 안 열림)",
     "zip 안의 폴더·파일 이름은 전부 영문/숫자로 짓고, 한글 안내는 README.txt 의 '내용'으로만 넣는다. "
     "zip 파일 자체의 이름(바깥)은 한글이어도 된다 — 풀기 실패는 엔트리 이름에서 난다"),
    ("숏폼 1:1 소스의 실제 가시 영역은 1080x937 이다",
     "숏츠 템플릿의 상단 틀이 y≈23 까지 내려오고 하단 자막 검은 띠가 y≈960 부터 덮는다 — 1080x1080 을 "
     "가득 쓰면 위 23px·아래 120px 가 가려진다 (2026-08-31 사용자 프리미어 실측: 영상 Y 960→840 으로 "
     "올려야 자막을 피했고, 상단은 983 기준). 차11-4 손익비 배지(y1004)가 실제로 자막에 덮였다",
     "씬 layout 에 padTop 23 · padBottom 135(가림 120+여유 15) 를 넣어 차트를 세이프 에어리어에 가둔다 — 그러면 프리미어 "
     "기본 배치(540,960)를 안 움직여도 된다. 절대좌표 레이어는 y ≤ 960-높이/2. 규칙은 brand/SHORTFORM-FX-POOL.md"),
    ("어두운 글자에 검정 테두리를 두르면 획이 뭉개져 안 읽힌다",
     "흰 글자+검정 테두리가 채널 기본 표기라 cmgNote 기본 stroke 가 #000000 이었는데, #111111·#9F0000 같은 "
     "어두운 fill 에 그대로 얹히면 자간·속공간이 테두리로 메워져 덩어리가 된다 (차12 v2 '익절 기준이 없다' 등 "
     "전 컷 — 사용자가 '가시성 최악'으로 반려)",
     "layers.js cmgNote 가 fill 휘도(가중평균, 0.16 미만)로 기본 테두리를 흰색으로 고른다. 씬에서 stroke 를 "
     "명시하면 그게 우선. 새 텍스트 레이어를 만들 때도 같은 판정을 넣어라"),
    ("라벨 클리핑은 스틸 몇 장이 아니라 probe-labels 로 전수 감사한다",
     "뷰포트가 리빌·줌·스무딩으로 매 프레임 움직여서, 라벨이 '등장 시각엔 잘리고 나중에 들어오는' 문제는 "
     "스틸 표본으로는 계속 새 나간다 (차12 v2 에서 완전 화면 밖 라벨 4개가 납품까지 통과)",
     "node src/tools/probe-labels.mjs --config scenes/xxx.scenes.js — 렌더 없이 등장~퇴장 0.25초 간격으로 "
     "가격/RSI 앵커 레이어의 y 를 전부 계산해 잘림 구간을 표로 낸다. 씬을 고치면 반드시 다시 돌린다. "
     "cmgNote 에는 세로 클램프 안전망도 있지만, 클램프에 기대지 말고 앵커를 옮기는 게 정답이다"),
    ("컷 경계에서 요소를 지우면 깜빡임이다 — 대체 전까지 유지한다",
     "컷을 새로 시작할 때 앞 컷의 라벨·태그·원을 layers 에 안 넣으면 화면에서 뚝 사라졌다 다음 컷에서 "
     "다시 튀어나온다. 차12 인트로 컷2를 '프리셋 타이틀이 덮는다'는 가정으로 비웠다가 반려됨 — "
     "실제 편집본에선 차트가 그대로 보였다 (2026-09-01 이정찬). 화면을 덮는 그래픽 가정은 실측 전엔 믿지 마라",
     "컷을 나누는 기준은 '새 요소로 대체할 때'. 대체가 없는 구간은 아예 클립을 병합한다(2026-09-01 추가 반려 — "
     "쪼개면 이월이 어긋날 때 깜빡임, 안 어긋나게 재등장시키면 반복·과밀). 교체는 같은 자리 크로스페이드, "
     "퇴장은 카메라 이동으로만(clamp:false·toBar). 규칙 전문은 brand/EDIT-RULEBOOK.md ⑧~⑩·⑬"),
    ("호흡이 짧으면 깜빡임과 정신없음이 같이 온다 — 뒤 챕터의 컷 길이가 모범답안이다",
     "차12 인트로가 컷 6개(중앙값 3.3초·요소 등장 초당 3.5개)로 쪼개져 '템포 빠르고 요소 많아 정신없다' 반려 "
     "(2026-09-01 이정찬). guide·fail 은 컷 9.7~29.6초(중앙값 ~17초)·초당 0.5개 — 같은 영상 안에서 6배 차이. "
     "컷3→컷4~5 처럼 차이가 원 하나·문구 하나뿐인데 클립을 쪼개 요소 대부분을 반복한 게 원인. "
     "내용에 도움 없는 줌인(줌인→줌아웃 왕복·카메라 되감기)도 같이 지적됨",
     "대체가 일어나지 않는 한 클립을 쭉 끌고 간다 — 인트로+후킹 23.13초를 클립 1개로 병합(intro-hook). "
     "새 씬을 짤 때 컷 길이·요소 밀도를 guide·fail 수준에 맞춘다. brand/EDIT-RULEBOOK.md ⑬"),
    # ── 2026-09-17 인박스 등재 — 로컬 PC 벽 ──
    ("Bash 도구 heredoc — 역슬래시·유니코드 이스케이프가 깨진다 (D 반복 08-28~09-17 · B 09-17 · E 09-17 — 세 세션 다 밟았다)", "'unexpected EOF while looking for matching' · 'grep: Trailing backslash' · 파일이 안 써지고 다음 명령이 '파일 없음'. replaceAll('\\\\','/') · 정규식 [/\\\\] · \\uC774 가 UTF-8 바이트로 바뀜 · settings.json 의 C:\\Users 가 \\U 이스케이프로 해석", "**역슬래시 든 코드는 Write/Edit 도구로만 쓴다** (E 처방 09-17 — f-string 의 \\n 이 진짜 줄바꿈으로 박혀 SyntaxError, ruff E9 가 잡음). String.fromCharCode(92) · chr(92) · 경로는 슬래시(/). 원문 log/inbox/2026-09-17_D_오류·비효율.md B1 · 2026-09-17_B_오류·비효율.md C2 · 2026-09-17_E_개선안회신.md 오류 원자료 1"),
    ("Windows 콘솔 cp949 — 파이썬 출력·파일 읽기가 한글·특수문자(—, ⚠)에서 죽는다 (반복)", "UnicodeEncodeError: 'cp949' codec can't encode character. PowerShell Start-Job 결과도 ?묒뾽 로 깨짐", "PYTHONUTF8=1 (PEP 540 — 이 PC 의 python3 shim 에 넣음) · 파일은 encoding='utf-8' 명시 · PowerShell 은 grep 'OK' 로만 판정. 원문 log/inbox/2026-09-17_D_오류·비효율.md B2 · log/inbox/2026-09-17_B_오류·비효율.md C3"),
    ("Bash → Windows 파이썬에 /c/Users/... 경로를 넘기면 한글이 깨진다", "FileNotFoundError '/c/Users/user/Desktop/������/...'", "파이썬 안에서는 C:/Users/... 형태. 원문 log/inbox/2026-09-17_D_오류·비효율.md B3"),
    ("Node ESM 은 Windows 절대경로 import 를 못 받는다", "ERR_UNSUPPORTED_ESM_URL_SCHEME — Received protocol 'c:'", "pathToFileURL() 또는 상대경로. 원문 log/inbox/2026-09-17_D_오류·비효율.md B4"),
    ("Claude Code 자동 모드 분류기가 막는 것 (로컬 PC)", "rm -rf → Irreversible Local Destruction · 대화기록 복사+키 가림 → Sensitive-Source Provenance · ~/.claude/hooks 쓰기 → Self-Modification · Remove-Item 와일드카드 · Start-Sleep 35 · .mcp.json cat → Credential Leakage · 환경변수 설정/조회 → Unauthorized Persistence / Credential Materialization", "휴지통 삭제(VisualBasic FileSystem::DeleteDirectory SendToRecycleBin) 한 경로씩 · 대화기록은 bundle 에서 뺀다 · 훅 파일은 이정찬이 bypass 모드로. 원문 log/inbox/2026-09-17_D_오류·비효율.md B5 · log/inbox/2026-09-17_B_오류·비효율.md F1"),
    ("세션이 붙잡은 폴더는 옮길 수 없다 · PowerShell 은 앞 줄 실패를 모르고 다음 줄을 돈다", "Move-Item: item is in use · mv: Device or resource busy → 뒤따른 정션 만들기가 그대로 진행", "세션을 닫고 옮긴다. PowerShell 여러 줄은 $ErrorActionPreference='Stop'. 원문 log/inbox/2026-09-17_D_오류·비효율.md B6"),
    ("파이썬 subprocess 로 'python3' 을 부르면 WindowsApps 가짜가 잡혀 거짓 통과", "규칙 시험이 전부 deny=False, 오류 메시지 없음", "sys.executable 로 부른다. 원문 log/inbox/2026-09-17_D_오류·비효율.md B8"),
    ("Gemini 비전 MCP — 쿼터·모델 폐기", "429 쿼터 초과 · 404 gemini-3-pro-preview 폐기 → gemini-3.1-pro-preview", "모델 이름은 설정 한 곳에. 키 재발급은 이정찬(next_step 36). 원문 log/inbox/2026-09-17_D_오류·비효율.md B9"),
    ("AE·프리미어 잡 — 앱이 파일을 잡고 있으면 zip 실패, 완료는 반환값이 아니라 로그 파일", "ZipArchiveHelper: being used by another process · 도구 타임아웃 2분/10분 · 프리미어가 켜져 있으면 BridgeTalk 잡이 프리미어의 AE 로(EXTENDSCRIPT-TRAPS ⑦)", "앱 닫고 zip · 판정은 <작업실>/log/<잡>.txt 의 판정 줄 · 쓰기 직후 확인은 거짓 실패(TRAPS ⑯). 원문 log/inbox/2026-09-17_D_오류·비효율.md B10"),
    ("일러스트레이터 모달 창은 SendKeys·UI Automation 으로 못 닫는다", "SendKeys 는 IME/포커스에 막힘, UIA 트리에 모달이 안 잡힘. COM 은 창이 떠 있는 동안 답이 없다(120s·300s 타임아웃)", "화면 1920x1080 가정 좌표 클릭(SetCursorPos+mouse_event) · COM 이 답을 안 주면 화면부터 찍는다 · 확인용 열기는 알림 켠 채 Start-Job 으로 열고 40초 뒤 캡처(알림을 끄면 문제가 가려진다). 원문 log/inbox/2026-09-17_B_오류·비효율.md B1~B3 · C4 · E3"),
    ("일러스트레이터 Compatibility 열거값은 이 PC 에서 17·24 두 개뿐", "ILLUSTRATOR25~30 없음, 기본 24. 17 로 저장하면 열 때마다 '이전 버전 텍스트' 창(issue 29)", "Compatibility.ILLUSTRATOR24. 원문 log/inbox/2026-09-17_B_오류·비효율.md A1"),
    ("build_live.jsx 는 한 번에 752초 — 24MB 트팩 원본을 매번 연다", "exit 0 · 752초. 그중 몇 분은 끊긴 링크 창 대기. '응답 없음' 표시가 멈춤과 구분 안 됨", "멈춤 판정은 CPU 20초 증분(+4s 면 작업 중 / +1s·메모리 고정이면 멈춤). 원문 log/inbox/2026-09-17_B_오류·비효율.md E1"),
    ("한지 텍스처 trad.hanji() 는 1920 폭 고정", "8000px 배너를 한 번에 못 만든다", "좌우 뒤집어 타일링. 원문 log/inbox/2026-09-17_D_오류·비효율.md B11"),
    ("ExtendScript 함정 ①~㉒ 는 brand/EXTENDSCRIPT-TRAPS.md 가 원문 — DB 로 옮기지 않는다", "코드 주석이 번호로 가리킨다(run.ps1 ⑥, build_rollad.jsx ⑮). 번호가 정리 안 됨(⑫ 두 번, ⑭→⑮ 건너뜀). 남의 실측을 요약해 옮기면 틀린다(⑦⑩⑪ 전례)", "DB 는 '원문 ⑯' 처럼 번호만 가리킨다. 새 함정은 문서에 먼저 적고 DB 는 그 번호. 총괄 결정 2026-09-17 (decision 23). 원문 log/inbox/2026-09-17_B_EXTENDSCRIPT-TRAPS_이관판단.md"),
    ("ExtendScript $.evalFile 은 BOM 없는 UTF-8 한글을 정상으로 읽는다 — TRAPS ③ 은 File.read 얘기다", "코드 검토 세션이 scene-export.mjs 의 한글 .jsx 를 TRAPS ③ 위반으로 지적했으나 D 실측(AE 26.5)에서 코드포인트 일치. _lib.jsx 도 BOM 없는 한글 파일로 35개 잡이 써 왔다", "evalFile 은 그대로. File.read() 로 읽을 때만 encoding='UTF-8' 을 먼저 준다(TRAPS ③). 남의 지적도 실측으로 되돌린다. 원문 log/inbox/2026-09-17_D_개선안회신.md §4 D-1"),
    ("ffmpeg stderr 를 그대로 담은 파일(silences.txt)은 실행마다 메모리 주소가 바뀐다", "줄 머리 `[silencedetect @ 000001650716bc00]` — 해시 회귀에서 '다름' 으로 뜬다. 도구 결과에는 영향 없음(read_silences 는 숫자만 읽는다)", "내용 비교는 주소를 빼고 한다. 원문 log/inbox/2026-09-17_E_개선안회신.md 오류 원자료 2"),
    ("git_guard 는 명령 텍스트만 본다 — 문서를 heredoc 으로 쓰면 본문의 'git push …' 줄에 걸린다", "D 보고서(본류 이름+push 낱말 포함)를 heredoc 으로 덧붙이는 명령이 차단됐다. 옛 로컬 훅도 같았다. 규칙을 느슨하게 하면 진짜를 놓친다", "문서는 셸 heredoc 이 아니라 Write/Edit 도구로 쓴다(역슬래시 문제와 같은 처방). 조각을 파일 도구로 만들고 cat 으로 잇는다. 원문 log/inbox/2026-09-18_D_훅연결_실측.md §6"),
    ("make_xml.pathurl — 드라이브 문자 경로는 abspath 를 안 거치니 정규화도 안 된다", "C:/Users/../Users/user/x.mp4 같은 경로가 그대로 URL 에 박힌다. cuts.json 의 source 는 전부 정규화된 절대경로라 지금은 영향 없음", "상대·리눅스 경로는 전처럼 abspath. 필요해지면 os.path.normpath 만 추가. E 윈도우 회귀 4개 바이트 동일. 원문 log/inbox/2026-09-18_E_세션시작폴더_적용.md"),
    ("윈도우는 경로 조각 끝의 공백·마침표를 조용히 떼어낸다 — 공백은 나중에 터지고, 마침표는 이름만 달라진다 (B 정리 → E 재현 → D 가 마침표를 갈라냄 → B 재확인, 세 사람 실측 09-18)", "폴더 '끝공백 ' → 디스크 '끝공백', 그 경로로 쓰기·listdir 은 FileNotFoundError(공백은 만들 때만 떨어지고 풀 때는 안 떨어진다). 폴더 '끝점.' → 디스크 '끝점', 쓰기·읽기 다 성공 — 이름이 달라진 걸 아무도 모른다(마침표는 풀 때도 떨어진다). 파일은 둘 다 이름만 달라진다. isdir('끝공백 ') 는 True 라 검사로 안 걸린다. 조용한 쪽(마침표)이 더 골치다 — 납품·회차 폴더 이름이 지시서와 달라져도 소리가 안 난다. 사례: E yt-dlp 채널 폴더(실제)", "경로 조각을 만들 때 뗀다 — 파이썬 rstrip(' .') · ExtendScript name.replace(/[ .]+$/, ''). 반영 완료(이정찬 승인 09-18): E shortform.py safe_tail(6bb8b0e, 왕복 시험 tests/test_shortform_names.py) · B 일러스트레이터 safeName(aed48bd) · D tools/style 6개 --out rstrip(2a7eddd). **일러스트레이터 saveAs 도 같다(2026-09-21 B 실측, Illustrator 30.8.1, 네 경우 전부 파이썬과 동일)** — 부모 폴더 끝이 공백이면 `오류: the operation was cancelled` 로 실패한다. 폴더가 없다는 말이 아니라 원인을 찾기 어렵다. new File(\"…ai \") 은 만들기 전부터 .name 이 공백 없는 이름이라 디버깅에서 더 헷갈린다. 원문 log/inbox/2026-09-21_B_constraint56_일러스트레이터_실측.md · log/inbox/2026-09-18_B·E_경로끝공백_constraint후보.md"),
    ("yt-dlp 함정 넷 (E 실측 09-18, 2026.08.19)", "① --print 는 --simulate 를 함축 → 자막·썸네일 안 받아진다 ② --convert-subs 는 ffmpeg 를 부른다(이 PC 에 없음) ③ --js-runtimes node 없으면 JS 런타임 경고 ④ 자막 트랙 ko-orig 와 ko 가 따로 있는 영상이 있다", "① --no-simulate 를 같이 ② --sub-format srt 로 유튜브가 주는 SRT 를 그대로(json3 130KB → srt 18KB) ③ --js-runtimes node ④ ko-orig 먼저, 없으면 ko. 월 1회 pip install -U. 남의 영상 다운로드는 약관 위반 — 참고용과 재배포는 다르고, 로그인 쿠키는 안 쓴다. 원문 log/inbox/2026-09-18_E_도구공유_유튜브·한국어NLP.md §2"),
    ("YouTube Data API 한도·제약 (E 09-18)", "videos·channels·commentThreads·playlistItems 는 1유닛/하루 10,000. search.list 만 하루 100콜 별도. 남의 채널 자막은 못 받는다(403 이 정상). 남의 채널 데이터는 30일 넘게 원본 보관 금지", "검색은 yt-dlp ytsearchN: 으로 대신. API 는 좋아요 수처럼 yt-dlp 가 못 주는 것만. 키는 C:/Users/user/.secrets/ac_keys.env (decision 32). 원문 log/inbox/2026-09-18_E_도구공유_유튜브·한국어NLP.md §3"),
    ("한국어 도구는 과교정한다 — 자동 파이프라인에 넣지 않는다 (E 실측 09-18)", "맞춤법 MCP(@winterjung/mcp-korean-spell)는 네이버 검사기 비공식 사용이고 우리 용어도 고친다(메인밴드→메인 밴드). Kiwi space() 도 과교정(매매 법·21 기간). j5ng/et5-typos-corrector 는 '하락 구조'를 '상승 구조'로 바꿔 놓는다. KURE-v2 는 리더보드 1위지만 11편 인코딩 v1 68초 · v2 250초", "맞춤법은 사람이 볼 때만, 고유 용어는 예외 목록. Kiwi 는 고칠 자리 찾는 용도로만(add_user_word 로 용어 등록). 뜻이 바뀌는 교정기는 안 쓴다. 임베딩은 KURE-v1. tiktoken 오류면 pip install tiktoken sentencepiece protobuf. 원문 log/inbox/2026-09-18_E_도구공유_유튜브·한국어NLP.md §4"),
    ("MT5 MCP — 인증·세션·캡처 함정 7 (D 실측 09-18)", "① 인증은 Authorization: Bearer <키> 뿐, initialize 의 Mcp-Session-Id 를 계속 싣고 notifications/initialized 는 id 없이 ② ChartScreenShot 은 스크롤 자리를 무시하고 늘 최신 구간 — 크기를 키우면 봉이 더 들어올 뿐 ③ ChartNavigate 는 자동스크롤 끄고 CopyRates 로 그 날짜 이력을 먼저 ④ chart_apply_template 은 지표를 통째로 갈아 끼움(3초 쉬고 붙인다) ⑤ 지표 목록은 터미널 시작 때 한 번 — 새 지표는 재시작 ⑥ PrintWindow 는 자식 핸들을 줘도 본 창 — 차트 판은 그림에서 찾는다 ⑦ trade_* 7종은 부르지 않는다", "과거 장면은 ChartNavigate 로 옮긴 뒤 창을 PrintWindow 로 찍는다(tools/mt5/capture_scene.py). 키는 .secrets/ac_keys.env MT5_MCP_KEY. 원문 log/inbox/2026-09-18_D_아스트라_인수인계.md §3 · log/inbox/2026-09-18_D_MT5_MCP연동_시험.md"),
    ("렌더 색·속도 — ProRes 4444 는 YUV 라 1 어긋난다, 차트 컷씬은 우리 렌더러가 4.5배 빠르다 (D A/B 실측 09-18)", "#0D9488 이 ProRes4444 에서 (12,148,135). ov-pnl 같은 컷: 우리 렌더러 6.9초 vs HyperFrames 31.0초(300장). 이 PC PATH 에 ffmpeg 없음", "색을 보증해야 하면 PNG 시퀀스. HyperFrames 는 우리 레이어에 없는 모양을 새로 만들 때만. ffmpeg 는 06_실험실/hf_smoke/node_modules 것을 PATH 앞에. 원문 log/inbox/2026-09-18_D_AB시험_우리렌더러_대_HyperFrames.md · log/inbox/2026-09-18_D_외부도구_HyperFrames·Remotion_실측.md"),
    ("일러스트레이터 저장·모달 함정 둘 — TRAPS ⑨-4·⑨-5 가 원문 (B 실측 2026-09-21)", "⑨-4 pdfCompatible=false 로 saveAs 하면 'Acrobat PDF 파일 포맷에 문제가 있습니다' 모달이 뜨고 COM 이 멈춘다(CPU 증분 0.41s). ⑨-5 화면 캡처는 다른 창에 가려지면 헛장, UIA 는 어도비 자작 창 속을 못 읽는다(OS_ViewContainer 하나)", "pdfCompatible 은 true 로 둔다(파일 커져도). 모달 판별은 메인 창 IsWindowEnabled=False, 내용은 프로세스의 #32770 창에 PrintWindow(h,hdc,2). 닫을 땐 좌표 클릭보다 PostMessage(VK_RETURN) — 그래도 닫기보다 죽이고 기록(next_step 46). 원문 brand/EXTENDSCRIPT-TRAPS.md ⑨-4·⑨-5"),
    ("PowerShell 5.1 은 BOM 없는 .ps1 의 한글을 cp949 로 읽는다 (D 실측 2026-09-21)", "새로 쓴 run.ps1 이 'The string is missing the terminator: \\\"' 로 죽었다. 파일은 멀쩡했고 한글이 깨지며 따옴표가 먹혔다. 저장소의 기존 .ps1 넷은 전부 BOM 이 있어 안 겪던 일", "한글이 든 .ps1 은 UTF-8 with BOM 으로 쓴다(.jsx 가 읽는 JSON 은 반대로 BOM 없이 — constraint 38·B-1 과 구분). 원문 log/inbox/2026-09-21_D_공용실행기_1단계.md"),
    ("Windows MainWindowHandle 은 못 믿는다 — 일러스트레이터가 160×28 짜리 엉뚱한 창을 돌려줬다 (D 실측 2026-09-21)", "Process.MainWindowHandle 로 창을 잡아 PrintWindow 하면 빈 조각이 찍힌다. PowerShell Add-Type P/Invoke 는 System.Drawing.Rectangle 참조를 못 찾아 컴파일이 깨진다", "프로세스의 보이는 최상위 창 중 가장 큰 것을 고른다 — tools/_com/shot_window.py 한 벌(파이썬). 못 찾으면 종료코드 2, 실행기는 화면 전체로 물러선다. 원문 log/inbox/2026-09-21_D_공용실행기_남은둘_실측.md §3"),
]

NEXT_STEPS = [
    (17, "로컬 커밋 6개 합류 — 완료 (2026-08-28)",
     "제안한 절차 그대로 진행됐다: 사용자가 로그인해 옆가지 local/thumb-ch11 로 올리고, "
     "로컬이 공통 조상 0a15606 에서 병합(dd04e8b, force 없음, 양쪽 보존). "
     "옆가지는 지우지 않고 둔다 — '썸네일이 로컬에서만 검증됐던 마지막 지점'(0652cac, "
     "팀장 컨펌 직후·클라우드 미합류)의 이름표로 쓴다. 사용자 결정 2026-08-28", "완료"),
    (1, "새 대본 받으면", "타임코드를 프레임으로 환산(같은 분 안이면 드롭프레임 보정 불필요) → scenes/cmg-20ma-runner.scenes.js 를 본떠 새 config 를 만들고 layers 를 채운다 → --stills 로 구도 확인 → --all --reel", None),
    (2, "전략 1 컷 (아직 안 만듦)", "기획서의 익절 기준이 '종가가 20일선을 하방 이탈하는 음봉, 아래꼬리조차 20일선에 닿지 않는 완전 이격 캔들'. 이 조건을 그대로 그리는 컷이 뒤에 필요하다", "대본"),
    (3, "전략 2 컷 (아직 안 만듦)", "박스권 횡보장 스위칭. 이평선이 눕는 것 확인 → 직전 고점 윗꼬리·저점 아랫꼬리로 라인 → 하단 지지에서 매수, 상단 저항에서 익절", "대본"),
    (4, "규격 통일 여부", "채널 최종본은 720p/30fps. 1080p/59.94 유지 중인데 다른 소스와 맞출지 결정 필요", "사용자 판단"),
    (16, "렌더 속도 — 적용 완료 (2026-08-27)",
     "잰 병목 두 곳을 그대로 실행했다. 캡처를 canvas.toDataURL 로 바꿔 93s → 26.8s (md5 동일 증명), "
     "인코딩은 --preset 으로 열어 medium 이면 24.1s. 남은 여지는 WebCodecs 로 브라우저 안에서 "
     "h264 를 직접 뽑는 것 정도인데, baseline 프로파일 제약이 있어 화질 요건과 안 맞는다. "
     "benchmark 10~17번이 근거다", "완료"),
    (6, "컷별 병렬 렌더 — 폐기 (2026-08-27)",
     "캡처가 빨라진 뒤로는 단일 프로세스가 이미 4코어를 포화시켜 병렬 이득이 없다 "
     "(순차 26.8s = 병렬 26.8s, benchmark 17). npm run render:par 를 만들 이유가 사라졌다. "
     "코어가 훨씬 많은 머신에서만 다시 검토한다", "폐기"),
    (14, "썸네일 .psd — 로컬 클로드가 이어받음",
     "포기가 아니라 넘긴 것이다. 포토샵이 있는 PC 에서는 파일을 직접 만들면 되니 "
     "여기서 겪은 문제(psd-tools 로 쓴 파일을 포토샵이 거부)가 애초에 생기지 않는다. "
     "여기서 잡은 것: EngineData 의 RunArray/RunLengthArray 짝, lyid 중복, macroman 이름칸. "
     "못 잡은 것: 그 셋을 다 고친 뒤에도 열리지 않은 이유", "넘김 — 로컬"),
    (15, "썸네일 인물", "차11 은 인물이 없는 회차라 비워 뒀다. 템플릿 '그룹 1' 이 인물 자리다 "
     "(#1 은 쿠라마기 그림이 거기 들어 있다)", "넘김 — 로컬"),
    (12, "숏폼 #4·#5 초안 검토", "차11 전략1·전략2 로 초안 두 편을 규칙대로 써 두었다 "
     "(scripts/shortform/). 팀장님이 쓰신 것과 얼마나 다른지 보면 규칙의 정확도를 알 수 있다", "사용자"),
    (13, "숏폼 대본 규칙 검증", "차13·차14·차15 숏폼이 나오면 규칙대로 예측해 보고 맞는지 확인한다. "
     "지금 규칙은 차01~차12 25편에서만 뽑았다", "새 숏폼"),
    (10, "숏폼 화면 톤앤매너 조사", "대본 쪽은 끝났고 화면이 남았다. "
     "숏츠 기본 양식.prproj (drive_map) 를 뜯어 1080x1920 에서 자막·차트·라벨이 어떻게 배치되는지 "
     "실측하면 숏폼 3단계(모션그래픽)를 시작할 수 있다", None),
    (11, "롱폼 2단계(컷편집·자막) 연동", "지금은 타임코드를 사람이 옮겨 적어 준다. "
     ".srt 를 그대로 받아 컷 경계를 자동으로 나누면 3단계 입력이 손을 안 탄다", "사용자"),
    (8, "차명14·15 대본 미작성", "두 회차 문서가 927자짜리 빈 템플릿이고 본문이 서로 완전히 동일하다. "
     "레퍼런스로 쓸 수 없으니 대본이 채워지면 log/data/scripts.json 을 다시 만든다", "사용자"),
    (9, "모션 문법 표본 부족", "motion_preset 3종은 차명11 최종본 하나에서만 뽑았다. "
     "다른 회차 .prproj 도 같은 방식으로 훑으면 회사 표준 이징·지속시간이 더 정확해진다", None),
    (7, "알파(.mov) 렌더 시간 미측정", "mp4 는 956프레임에 순차 26.8초(캡처 교체 후)로 재놨는데 "
     "무손실 알파(qtrle)는 파일이 커서 I/O 가 더 붙는다. 필요해지면 따로 측정한다", None),
    (5, "로고 워터마크", "지금은 렌더에 넣지 않음(프리미어 프리셋과 중복). 필요하면 image 레이어로 brand/logo 사용", None),
    (19, "차11 썸네일 마감", "A(추세추종)·C(통합) 채택. 최종 파일은 deliver/thumbnail/차11_20일선의 비밀/ 에 있다. "
     "B(박스권)는 요소가 많다는 이유로 보류 — 씬 파일과 미리보기 png 는 남겨 두었다",
     None),
    (20, "다음 회차 썸네일", "tools/photoshop/config.json 의 group·variants 만 바꾸면 된다. "
     "인물이 있는 회차면 base 를 #5 나 #7 로 바꾸고 '그룹 1'(인물 자리)에 이미지를 넣는다. "
     "컨테이너 대체 경로(thumbnail_png.py)도 같은 config 를 읽는다 — probe 컷이 있는 씬을 만들고 "
     "variants 에 scene·tags 를 달면 된다(decision 21)",
     "회차 대본과 인물 이미지"),
    (21, "프리미어 직접 편집 실험 (D 세션) — M1 통과, M2 진행", "M1(BridgeTalk 열기·시퀀스 복제·저장) 은 "
     "2026-08-28 3자 검증으로 통과. 다음은 M2 소스 교체 — 오프라인 상태로, 기준선은 "
     "m1_after_open_only.prproj, 차트는 C:\\cmgwork\\chartA.png 등. 그 뒤 M3 키프레임 → M4 회차 조립"
     "(미디어 되살리기는 M4 에서). 산출물은 옆가지 local/premiere-lab, 판정은 클라우드",
     "D 가 verify.py 기준선 교체 후 M2 시작"),
    (22, "대본 — 방영일 확정 시 마무리", "포인트 편 (중간)·260828 을 방영일로 갱신해 뗀다. SL 2편(차11 #4·#5)은 "
     "팀장 컨펌 대기. 다음 포인트_차 편 주제는 '손절 기준을 어디에 두느냐'(이번 CTA 가 던진 질문 — "
     "260715 '못하는 이유' 와 겹치지 않게), 팀장 피드백 3건(포인트_차 화법·라이브톤 유지·New 기준) 적용, "
     "참고 원고는 log/SCRIPT-LAB.md §7",
     "방영일 확정 · 팀장 컨펌"),
    (23, "shortform.py --kind point 구현 (E, 승인됨)", "①발화만 세기(제목·라벨·지문 제외) ②갈래별 cps"
     "(토크 6.91/기법 6.70/모드A 5.90) ③포인트 이름 규칙 ④'포인트' 표기 검사 해제 ⑤토크편 훅 면제. "
     "나간 편(후행스팬 53.1초·캔들꼬리 43.1초)으로 검증하며 넣는다",
     "E 다음 세션"),
    (24, "프리미어 M7 — 텍스트를 편집 가능하게 (D)", "프리셋 안 그래픽 텍스트 클립의 소스 텍스트를 스크립트로 "
     "바꾸는 길을 탐색한다(미탐색·D 판단요청 1·3 통합). 타이틀이 아직 차명10 문구인 것도 이걸로 풀린다. "
     ".mogrt 는 사람 손이 한 번 필요하니 후순위. 안 뚫리면 현행 구조(텍스트 층 재렌더 9초) 유지",
     "D 다음 세션"),
    (25, "팀장 확정 2건 (사용자)", "① 회차 조립 본류 — B(새 시퀀스)를 A(프리셋)에 중첩하는 구성이 맞는지 "
     "② 편집자가 글자를 직접 고치는 일이 얼마나 잦은지(M7 의 우선순위를 정한다)",
     "사용자가 팀장에게"),
    (18, "1세대 썸네일 도구의 타이틀 크기 계산", "tools/legacy/thumbnail.py(격리됨) 의 fit_size 와 psdedit 의 _fit·bake_text 가 "
     "아직 '폭에 맞춰 폰트 크기를 역산' 하는 방식이다. 완성본 실측으로 규칙이 뒤집혔으므로"
     "(글자 높이 고정·폭 자유, thumbnail_rule 4·5) 그 경로로 뽑으면 규격이 어긋난다. "
     "포토샵이 없는 환경에서 그 도구를 다시 쓸 일이 생기면 먼저 고쳐야 한다",
     "리눅스에서 썸네일을 다시 뽑아야 할 때"),
    (26, "SL 차11-4·11-5 조립 피드백 반영", "사용자가 프리미어에서 소스 패키지로 조립한 뒤 나오는 지적 — "
     "컷 타이밍·차트 연출·자막 줄바꿈 — 을 받아 scenes/sl-11-4·5 와 컷리스트를 고친다. "
     "특히 11-5 '누워버리면' 침묵 컷(92.38 이음새)이 귀로 자연스러운지 확인 필요",
     "사용자 조립 후"),
    (27, "AE 실전 — 차12 인트로 레이어 컴포지션 (파일럿 성공 후속)", "이정찬 보고(2026-09-01): D 가 m1~m6 "
     "실험으로 '레이어 다 쪼갠 걸로 모아놓은 컴포지션 만들기' 성공. 인수인계는 AE-LAB-MANUAL §8 — "
     "차12 씬 파일 지도, node tools/render-cmg12-layers.mjs (병합 intro-hook 층당 1파일, tag 최상위 ⑭), "
     "새 렌더러 문법(growEase·toBar·clamp:false·cmgArrow z 강제), motion_preset 3종, 룰북 14개. "
     "주의: m6_build.jsx 는 구 컷4개×층 경로 기준이라 파일 목록 수정 필요. 본편 20컷 레이어 분리는 "
     "필요해지면 총괄이 확장. → A0~A6 병합·판정 완료(2026-09-03, request 68): .mogrt 채택 — 프리미어 "
     "[속성] 한글 컨트롤 9개, 표현식 생존. 글자 3~5px 이동은 길 A(하네스 런타임 계측) 채택 — request 69. "
     "남은 것은 차12 실전 컴포지션(next_step 28)과 양산기"
     "(scenes.js→jsx 변환) 논의",
     "D 작업 후 (파일럿 판정 완료 — 실전 대기)"),
    (28, "차12 롱폼 — r9 확정이 r13 반려로 뒤집힘", "r9+r12 는 이정찬 확정이었으나 팀장이 반려 "
     "(2026-09-03: 기존 영상과 다름·움직임 금지·이평선 초록 안 보임·RSI 경계 안 보임 — request 72). "
     "r13 전면 재작 완료: 실 NQ 데이터 + 정지 차트 + FX-WHITELIST 문법, scenes/cmg12s-* 23컷. "
     "이전 cmg12-* 씬·r9 납품물은 반려본으로 보존(롤백 지점). D 의 AE 레이어 분해 후속도 r13 문법 "
     "기준으로 다시 판단한다",
     "r13 납품 후 이정찬·팀장 반응"),
    (29, "차12 브리지 톤앤매너 교체 — 차명10 카드 문법으로", "이정찬 스샷 실측(2026-09-02): 차명10 개념 카드는 "
     "회색 배경 + 흰 글자(경기천년바탕 Bold 117px급) + 강한 그림자(불투명 95%·135도·거리 7·크기 12.8·블러 40) "
     "+ 핑크 #EF2767 풀밴드 하이라이트 + 좌상단 핑크 박스 타이틀. 전개(구성·타이밍)는 유지하고 팔레트·폰트만 "
     "이 문법으로. ep4 문법(검정 글자+흰 테두리·노랑 형광펜·베이지 예고)은 대안 스타일로 룰북 §E 에 남긴다. "
     "→ r10·r11 반려를 거쳐 r12 로 확정 (이정찬 2026-09-03 '확인했어. 완벽해'). 최종 문법: 회색 바탕+"
     "은은한 차트, 경기천년바탕 Bold 기울임꼴 흰 글자(외곽선 없음), 그림자는 텍스트에만·우하단, "
     "핑크 박스는 제목 전용·민짜. 룰북 §E-2 가 전부다",
     "완료 — r12 확정 (request 63~65)"),
    (30, "숏폼 .srt 이관 후속", "E 인수 완료 (SCRIPT-LAB §13 — srt_rules 버그 2건까지 고쳐서 씀). "
     "미결이던 2건 종결: ① 차11-4·5 재발행 안 함(이정찬 2026-09-01 결정) ② 설치 목록에 imageio-ffmpeg "
     "포함해 매뉴얼 §8 갱신(2026-09-03). 남은 것은 E 의 첫 '납품' srt 가 나오면 검사 통과를 한 번 "
     "봐 주는 것뿐",
     "E 첫 납품 후"),
    (31, "차12 썸네일 — 종료 (2026-09-16)",
     "deliver/thumbnail/차12_RSI+이평선 스캘핑/ 에 6안(A·B·C 와 강조판 A2·B2·C2)이 png 로 있다. "
     "고른 안이 정해지면 그 안의 .psd 를 다시 뽑아 같은 폴더에 넣는다 — png 만 넣은 이유는 "
     "회차당 psd 가 12MB 라 여섯 개면 72MB 이기 때문이다(폴더 README 에 재생성 명령을 적어 뒀다). "
     "차11 때처럼 문구 수정 요청이 오면 config.json 의 sub/main 만 고쳐 다시 돌리면 된다. "
     "2026-09-03 갱신: 좌상단 타이틀을 격자박스(규칙 28)에 맞춰 17% 줄여 6안을 다시 뽑았다 — "
     "지금 폴더에 있는 png 가 그 판이다. "
     "2026-09-16 종료: 차12(차트명가 구버전) 회차 자체가 끝난 지 오래라 컨펌을 더 기다리지 않는다 "
     "(이정찬). 6안 png 는 그대로 두고 .psd 는 뽑지 않는다 — 필요해지면 폴더 README 의 명령 두 줄이면 나온다. "
     "여기서 나온 격자박스 규칙(28)은 회차와 무관하게 남는다",
     "완료 — 회차 종료로 닫음"),
    (32, "시즌1 마감(금 09-05) — 스냅샷 박고 레드팀에 넘긴다",
     "이정찬 지시(2026-09-03): 금요일 작업까지를 전체저장 + 시즌1 로 박고, 주말에 Fable 5.1 "
     "UltraCode 새 세션이 최신 설계 기준(레거시 전부 바이패스) 효율성 렌즈 단독으로 레드팀 리뷰. "
     "준비는 끝났다 — log/REDTEAM-BRIEF.md (임무서: 대상 5덩어리·효율성 관점 6갈래·바이패스 목록·"
     "결과 반환 규약 local/redteam-s1 + lab/redteam/FINDINGS.md·시작 프롬프트 부록). 금요일 절차: "
     "①B·D·E 각자 마지막 커밋·푸시 확인(이정찬이 받아 총괄에 전달) ②옆가지 잔여분 본류 병합 "
     "③마지막 save ④season/1 브랜치를 그 커밋에서 푸시(태그 403 대용 — 이정찬 허가 받고) "
     "⑤이정찬이 브리프 부록의 시작 프롬프트를 새 5.1 세션에 복붙. 주말 리뷰 후 총괄이 "
     "local/redteam-51 을 받아 판정·취합한다. ※ 2026-09-03 차12 반려(request 72)로 이정찬이 "
     "시즌1 마감을 보류('지금 이거 할 때가 아니다') — 재개 신호가 오면 이 절차 그대로",
     "금요일 마감 시 (보류 중)"),
    (33, "차12 r13 후속 — 스크린샷 교체판·팀장 재검토",
     "r13(실데이터 렌더 판)은 납품 완료. 이정찬 선택 '둘 다': 로컬에서 MT5 스크린샷을 찍어 "
     "드라이브 차12/원본 에 올리면(샷리스트 = deliver/cutscene/차12.../MT5_촬영지시서_r13.txt, 7~8장) "
     "총괄이 image 레이어 배경 교체판을 추가 납품한다 — 좌표 재실측은 probe-labels + 신호 캔들 OHLC 메모. "
     "팀장 재검토 결과(무동작·실물감·이평선/RSI 가시성)가 오면 룰북 ⑧⑨⑩⑬ 대 무동작 충돌 정리를 "
     "확정 반영한다(현재 FX-WHITELIST 가 우선 문서)",
     "스크린샷 업로드 또는 팀장 반응 후"),
    (34, "L08 2차 복구 눈 확인 — 이정찬", "09-16 14:12 D 복구 뒤 이정찬이 프리미어로 직접 열어 오프라인 0 을 확인한 적이 없다(마지막 열람 14:08 끊긴 상태). E 검사로만 확인됨. 더는 편집 안 하기로 했지만(E 회신 §5) 열어서 0 인지 한 번은 본다 (issue 20)", "이정찬"),
    (35, "손익비 4차(박스 단색) 실물 확인 — 이정찬", "09-16 14:06 빌드, 02_AE작업실_aelab/pack/trad_rr. 아무도 실물을 보지 않았다 (issue 25)", "이정찬"),
    (36, "GitHub 토큰·Gemini 키 재발급 — 이정찬", "토큰 원문이 B 대화기록에 남았다(issue 35). 저장소 public. 자격증명은 이정찬 터미널에서만 다룬다 — 에이전트에 넘기지 않는다", "이정찬"),
    (37, "옛 경로 실행줄 정정 — D", "본류 문서 8개에 총괄이 '경로 주의' 머리말을 달았다(09-17). 명령줄(cd C:\\cmgwork\\repo 등)을 최신 경로로 바꾸는 것과 tools/premiere/ 29개·tools/photoshop/config.json 의 잔여 경로 점검은 D (E 회신 §5-3)", "D"),
    (38, "더원트레이더 규칙 DB 등재 — 보류", "컷 0.65s/−30dB/IN −0.08·OUT +0.07(표본 2편 50경계 0.051s) · 자막 14자(롱폼 21자 관측, 8편) · 배너 2판 공식(8편 중 5편). E 가 표본 병기 조건으로 동의. 새 채널로 넘어가 우선순위 낮음", "새 정답 자료가 생길 때"),
    (39, "prlinks.py 전 파트 공용 규칙 — 인박스 제안서", "폴더 옮기기 전 find, 옮긴 뒤 check. 검사 범위에서 목적지 폴더를 빼지 않는다. 사람이 옮기는 경우는 훅이 못 막는다 — 이정찬도 옮기기 전에 돌린다 (runbook 19)", "로컬 채택"),
    (40, "개선안 회신 — B·D·E 전부 완료 (09-17 17:3x, 셋 다 본류 병합)", "B 641f4da · D 3f32389 · E e6c16b8. 채택 현황은 log/inbox/2026-09-17_총괄_개선안회신답.md 표 + E: 2-A(가지만 전환, 작업트리 두 벌은 단일화 방침으로 안 만듦)·E-1~E-7·ruff 5 적용, 회귀 45항목 동일, pytest 29. 남은 것은 next_step 41(세션 시작 폴더, 이정찬)뿐", "완료"),
    (41, "세션 시작 폴더 — 완료. U-7(로컬 훅·bypass 되돌리기)도 완료 (이정찬+D 09-21)", "저장소 .claude/settings.json(env·훅·스킬)은 세션을 시작한 폴더에서만 읽힌다(공식 settings 문서, D 확인). 지금 B·D·E 는 …\\이정찬\\Claude 에서 시작해 아무것도 안 걸린다. 총괄 판단: 각 세션을 자기 worktree 폴더에서 띄운다(cd <worktree>; claude 또는 claude --worktree <이름>). 그러면 PYTHONUTF8·git_guard·radar 스킬이 자동으로 붙는다. 답이 오기 전엔 D 로컬 훅 유지", "이정찬"),
    (42, "더원 배너 나머지 문서 둘 — 완료 (09-18, 이정찬이 파일을 건네 총괄이 등재)", "tools/theone/상단배너_공식.md 는 올라왔다(519625b). 같은 폴더에 로컬만 있는 상단배너_로직.md(7.2KB)·상단배너_임베딩분석.md(8.3KB) — 임베딩 채점기 수치(쌍 개수·유사도 분포·홀드아웃)가 거기 있다. 이정찬이 '대본~인덱스~임베딩~로직' 자료를 찾고 있어 둘 다 tools/theone/ 으로", "E"),
    (43, "MCP 자가점검 스크립트 저장소로 — 완료 (E, 6bb8b0e → tools/mcp_probe.py)", "E 가 scratchpad/mcp_probe.py(initialize → tools/list → tools/call)를 만들어 뒀다. 별 수 믿지 말고 띄워 보는 도구라 전 파트 공용 — tools/mcp_probe.py 로 올려 달라 (radar 와 같은 자리)", "E"),
    (44, "경로 끝 공백·마침표 가드 — 완료 (B aed48bd · E 6bb8b0e · D 2a7eddd, 이정찬 승인)", "constraint_note 56. 주석에 번호를 적는다. B 의 일러스트레이터 saveAs 는 실측 뒤 반영(미실측 추정)", "B·E"),
    (45, "대본→차트장면 파이프라인 남은 것 — D (또는 아스트라)", "① 12장 일괄 촬영(비트마다 심볼·주기 바꿔 도는 부분) ② 콘티 이미지·AE 컴포지션 생성(tools/ae 잡 틀) ③ 규칙을 차10 한 편에서 뽑았다 — 다른 회차로 검증 ④ 찍은 그림을 회사 드라이브 소스 폴더에 넣을지는 이정찬 판단(지금은 안 쓴다). 인수인계 원문 log/inbox/2026-09-18_D_아스트라_인수인계.md", "D·이정찬(④)"),
    (46, "어도비 공용 실행기 — D 몫 완료(프리미어 잡 실행·프리미어 떠 있을 때 AE 차단 실측·창 단위 실패 캡처, 09-21 낮), 남은 것 B 2단계(일러·포토샵)", "run.ps1 네 벌을 tools/_com/run.ps1 하나로 합치면서 ① 앱·문서·프리미어 켜짐 검사 ② 타임아웃→taskkill→실패 기록 ③ 반환값 아닌 판정 줄로 성공 ④ 실패 시 **PrintWindow 로 모달 캡처**(화면 캡처는 가려지면 헛장 — B 09-21, TRAPS ⑨-5)+로그 30줄. 계기: GPT 가 WORKLOG 를 읽고 '진짜 위험은 모달·완료 판정·외부 앱 상태' — DB 로 확인(issue 28~31, TRAPS ⑦⑯). 제안서 log/inbox/2026-09-18_총괄_공용실행기_제안.md", "B 2단계 (실패 캡처는 tools/_com/shot_window.py 그대로 부른다)"),
    (47, "팀장 반려 문장 쌍 수동 수집 — E", "반려·첨삭이 올 때마다 고치기 전/후 문장 쌍을 tools/theone/ 에 jsonl 로. 회차·날짜·누가 고쳤나(팀장/전문가/편집) 표시. 30쌍 넘으면 decision 35 다시 본다", "반려가 올 때마다"),
    (48, "더블볼린저 편 방송 뒤 최종본 대조 — E", "차12 가 리믹스하는 더블볼린저 편은 아직 방송 전(09-21). 방송되면 자막을 받아 차12 초안과 대조. 방송 실물에서 볼린저 기본 20일 4회 확인(21 은 0회) — 차12 의 21→20 정정 뒷받침. 전문가 실사용은 기간 30·데비에이션 1", "방송 뒤"),
    (49, "Jev 판정관 시험 — E (반나절, 있는 자료만)", "① 한국어: 합격 배너 8쌍을 팀장 기준 5개 Score 로 ② 순위: S016 확정본 vs 1안, 8회차 확정본 vs 1판 문구 — 확정본이 이기는 수 ③ 방송본 5쌍 초안 vs 방송본 ④ confidence 분포. 합격선 ②에서 6/8 + ① 정상 → decision 35 갱신·채택, 아니면 external_tool 14 rejected. 미공개 대본은 안 보낸다(이정찬 결정 전). 키는 이정찬 발급 → .secrets TYPESAFE_API_KEY", "이정찬 키 발급 → E"),
    (50, "Jev 시험 — D (반나절, 셋 중 둘)", "D-1 잡 로그 성공/실패 Noul(20개 중 18, 틀린 것의 confidence 낮으면 run.ps1 경고 통과 자리에) · D-2 대본 비트 분류 Choice(차10 콘티 12장 중 10) · D-3 오류 분류 Choice(30건 중 25). 이미지·좌표·날짜는 제외. E 한국어 시험이 먼저. 설계 log/inbox/2026-09-21_총괄_Jev_시험_D·B.md", "E 시험 ① 통과 → D"),
    (51, "Jev 시험 — B (반나절, 셋 중 둘)", "B-1 모달 문구 → 처리 종류 Choice(실제 문구 5~6개 전부) · B-2 썸네일 강조 대상 Choice(규칙 22, 빨강 든 회차 전부) · B-3 오류 분류(20건 중 16). 픽셀·색 코드·캡처 판정은 제외", "E 시험 ① 통과 → B"),
]


BENCHMARKS = [
    (1, "2026-08-26", "scenes/cmg-20ma-runner.scenes.js", "serial", 4, 956, 15.95, 93.0, 10.3,
     "컷 4개를 --all 로 차례로. 컷별 250f/23.4s, 234f/19.6s, 152f/14.6s, 320f/26.9s"),
    (2, "2026-08-26", "scenes/cmg-20ma-runner.scenes.js", "parallel", 4, 956, 15.95, 45.0, 21.2,
     "컷별 프로세스 4개 동시. 순차 대비 2.07배. 결과물이 순차와 md5 까지 동일해 렌더가 결정론적임을 확인"),

    # 한 프레임을 조각내서 재 본 것. 총 시간만으로는 "왜 느린가" 를 답할 수 없어서 쪼갰다.
    # src/tools/profile-render.mjs · cut1-pullback-entry 120프레임 · 4코어 · 각 1회 측정이라 ±로 흔들린다
    (3, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "profile:그리기", 4, 120, None, 0.264, 454.5,
     "캔버스 드로잉만 (page.evaluate). 프레임당 2.2ms — 사실상 공짜다. 여기를 손봐야 소용없다"),
    (4, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "profile:스크린샷", 4, 120, None, 6.50, 18.5,
     "page.screenshot({type:'png'}). 프레임당 54.2ms — **캡처 비용의 96%가 여기다.** 지금 파이프라인의 병목"),
    (5, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "profile:toDataURL", 4, 120, None, 1.57, 76.3,
     "canvas.toDataURL('image/png') 로 대신 뽑아 봤다. 그리기 포함 13.1ms — 스크린샷보다 4배 빠르다. "
     "다만 base64 라 노드에서 디코드해야 하고, 결과가 스크린샷과 같은지는 아직 대조 안 했다"),
    (6, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "profile:CDP", 4, 120, None, 6.08, 19.7,
     "CDP Page.captureScreenshot. 50.7ms — Playwright 왕복을 빼도 거의 그대로다. PNG 인코딩 자체가 비싼 것"),
    (7, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "profile:ffmpeg-slow", 4, 120, None, 3.61, 33.2,
     "-preset slow -crf 12 (지금 설정). 프레임당 30.1ms · 376KB"),
    (8, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "profile:ffmpeg-medium", 4, 120, None, 1.68, 71.4,
     "-preset medium. 14.0ms · 383KB — **절반 시간에 파일은 2% 커질 뿐이다.** 중간 소스에 slow 는 과해 보인다"),
    (9, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "profile:ffmpeg-veryfast", 4, 120, None, 1.31, 91.6,
     "-preset veryfast. 10.9ms · 474KB (+26%)"),

    # 실전 루프(그리기→캡처→인코드 전부 포함) 실측. 조각 측정과 달리 ffmpeg 경합이 들어간다.
    # src/tools/exp-capture.mjs · cut1 120프레임 · 각 3회. 픽셀·mp4 출력 md5 동일까지 여기서 증명했다
    (10, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "loop:shot+slow", 4, 120, None, 10.8, 11.1,
     "기존 경로 실전 루프 90.2ms/f (88.4/88.2/94.0). 조각 합 56ms 와의 차이가 ffmpeg 경합 비용이다"),
    (11, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "loop:shot+medium", 4, 120, None, 10.5, 11.4,
     "87.8ms/f — 캡처가 병목인 동안에는 프리셋을 바꿔도 전체가 안 빨라진다"),
    (12, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "loop:dataurl+slow", 4, 120, None, 3.4, 34.9,
     "canvas.toDataURL 경로 28.6ms/f. 캡처가 빨라지자 이번엔 slow 인코더가 발목을 잡는다"),
    (13, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "loop:dataurl+medium", 4, 120, None, 2.8, 42.4,
     "23.6ms/f (23.2/23.8/23.8) — 기존 대비 3.8배. 편차도 거의 없다"),
    (14, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "loop:raw+medium", 4, 120, None, 89.6, 1.3,
     "getImageData→HTTP→rawvideo 는 746.6ms/f 로 탈락. 프레임당 8.3MB 전송이 PNG 절약분을 압도한다"),

    # 캡처 교체(커밋 후) 전체 렌더 재실측 — benchmark 1·2 와 같은 956프레임
    (15, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "serial-v2", 4, 956, 15.95, 26.8, 35.7,
     "toDataURL 캡처 + preset slow(기본값). 93.0s → 26.8s. 출력은 기존과 md5 까지 동일"),
    (16, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "serial-v2-medium", 4, 956, 15.95, 24.1, 39.7,
     "--preset medium. 26.8 → 24.1s. 파일 +2%"),
    (17, "2026-08-27", "scenes/cmg-20ma-runner.scenes.js", "parallel-v2", 4, 956, 15.95, 26.8, 35.7,
     "컷별 4프로세스(slow). 순차와 같은 26.8s — 병렬 이득이 사라졌다. 단일 프로세스가 이미 4코어를 포화시킨다. "
     "medium 은 22.2s 로 순차 대비 8% 이득뿐. md5 는 순차와 동일"),
]

# 사용자가 정한 표준 작업 순서 (2026-08-26)
WORKFLOW_STEPS = [
    (1, "대본 수령", "타임코드가 붙은 .srt 를 받는다", "사용자", "ready", None),
    (2, "주제·소재·키워드 정리", "대본에서 검색어가 될 키워드를 뽑는다", "클로드", "ready", None),
    (3, "작업물 폴더 검색",
     "이제 드라이브에 붙지 않아도 된다. script_fts 전문 검색과 script_keyword 역인덱스가 "
     "저장소 안에 있다 (2026-08-26 기준 16편). 새 회차가 생기면 log/data/scripts.json 을 갱신한다",
     "클로드", "ready", "원본은 .docx. unzip 해서 word/document.xml 을 읽는다"),
    (4, "레퍼런스 확정", "script_keyword 로 키워드 일치율이 가장 높은 회차를 고른다. "
     "그 회차의 최종 .prproj 는 episode_prproj 테이블에 drive_id 로 들어 있다", "클로드", "ready", None),
    (5, "레퍼런스 확인",
     "그 회차의 .prproj 를 gunzip 해서 XML 을 직접 읽는다. 시퀀스·이펙트·키프레임·애셋 경로가 모두 평문으로 들어 있다. "
     "영상 프레임을 찍어 실측하는 것보다 빠르고 정확하다",
     "클로드", "ready", "프리미어도 MCP 도 필요 없다. prproj_fact 참고"),
    (6, "컷 설계 + scenes.js 작성",
     "타임코드를 프레임으로 환산하고 cmg-20ma-runner.scenes.js 를 본떠 layers 를 채운다", "클로드", "ready", None),
    (7, "구도 확인", "--stills 로 스틸컷을 먼저 본다. 겹침은 여기서 잡는다", "클로드", "ready", None),
    (8, "렌더", "--all 순차로 충분하다 (2026-08-27 캡처 교체 후 병렬 이득 소멸)", "자동", "ready", "benchmark 15~17번 참고"),
    (9, "프리미어 반입", "지금은 사용자가 직접 넣는다. 자동화하려면 사용자 PC 에 프리미어 MCP 설치 필요",
     "사용자", "todo", "external_tool 1·2번 참고"),
]

EXTERNAL_TOOLS = [
    (1, "Adobe-Premiere-Pro-MCP", "github.com/antipaster/Adobe-Premiere-Pro-MCP",
     "프리미어를 원격 조작 (편집·이펙트·자막·익스포트 170여 도구)",
     "Windows + Premiere Pro 2023+ / CEP 패널(WebSocket 포트 8097) / install.bat 로 미서명 확장 허용 / 프리미어와 같은 PC",
     "local-only",
     "이 컨테이너는 리눅스에 프리미어가 없어 서버를 띄워도 붙을 대상이 없다. "
     "사용자 윈도우 PC 의 Claude Desktop 에 설치해야 동작한다. 저장소 크기 1.3MB"),
    (2, "premiere-pro-mcp", "github.com/leancoderkavy/premiere-pro-mcp",
     "같은 목적. 313개 도구 + UXP 패널 50개",
     "Claude Desktop 확장 번들 + 별도 서명 커넥터 MCPBridgeCEP.zxp. README 원문: "
     "\"Keep the assistant, server, connector, and Premiere on the same computer\"",
     "local-only",
     "동일한 이유로 이 세션에서는 못 쓴다. Node 없이 되는 Claude Desktop 경로가 있어 설치는 1번보다 쉽다. 저장소 크기 28MB"),
    (3, ".prproj 직접 파싱", "표준 도구 (gunzip + XML)",
     "레퍼런스 회차의 편집 구성을 확인",
     "없음. gunzip 과 파이썬 표준 라이브러리면 된다",
     "adopt",
     "프로젝트 파일이 gzip 압축 XML 이라 그냥 읽힌다. 프리미어도 MCP 도 커넥터도 필요 없고, "
     "영상 프레임을 찍어 색을 재는 것보다 훨씬 빠르며 값이 원본 그대로다"),
    (4, "yt-dlp", "github.com/yt-dlp/yt-dlp", "유튜브 자막(ko-orig srt)·썸네일 원본(1280×720 webp)·지표·채널 목록·검색·댓글 — 키 없이", "pip install -U yt-dlp · Node(JS 런타임) · ffmpeg 없이 --sub-format srt", "adopt", "E 09-18 이 PC 에서 명령 7종 검증. 함정 넷은 constraint_note 57. 약관상 참고용만"),
    (5, "YouTube Data API v3", "developers.google.com/youtube/v3", "좋아요 수·정확한 통계(yt-dlp 가 못 주는 것)", "키(.secrets/ac_keys.env) · 하루 10,000유닛 · search.list 100콜", "adopt", "필요한 것만. 한도·제약은 constraint_note 58"),
    (6, "kiwipiepy", "github.com/bab2min/kiwipiepy", "한국어 형태소·문장 분리·띄어쓰기 자리 찾기", "pip install kiwipiepy · 용어는 add_user_word", "adopt", "자동 교정은 과교정(constraint_note 59) — 찾는 용도로만"),
    (7, "@winterjung/mcp-korean-spell", "npm", "문구 맞춤법 교정 (사람이 볼 때)", "npx -y · 네이버 검사기 비공식", "local-only", "붙은 글자 3건 정확. 비공식 API 라 자동 파이프라인엔 안 넣는다(py-hanspell 전례). 용어 예외 목록 필요"),
    (8, "j5ng/et5-typos-corrector", "huggingface", "로컬 맞춤법 모델", "-", "rejected", "'하락 구조'를 '상승 구조'로 바꿨다 — 뜻이 바뀌는 교정기 (E 실측)"),
    (9, "Social Blade · playboard 스크래핑 / 유료 자막 API(Supadata 등) / bareun.ai", "-", "채널 통계·자막·맞춤법 대안", "-", "rejected", "약관 자동 수집 금지 / 클라우드 IP 차단 문제인데 우리는 집 인터넷 / 상업적 사용 유료·무료 5만 어절. 원문 E 도구공유 §7"),
    (10, "kimtaeyoon83/mcp-server-youtube-transcript", "github (★595)", "유튜브 자막 MCP", "-", "rejected", "npm 배포가 2024-11 에서 멈춰 빈 문자열을 돌려준다. 별 수 말고 띄워 보고 판단(E, mcp_probe)"),
    (11, "MT5 MCP (HedgeHood MT5 Terminal)", "로컬 MCP · 도구 50종", "대본 비트에 맞는 실제 차트 장면을 MT5 에서 찍는다 — 지표 자동 부착·제거, ChartNavigate 로 과거 구간", "MT5 설치 + MT5_MCP_KEY(.secrets) + CMG_Shot.mq5 지표 컴파일(재시작 한 번)", "adopt", "D 09-18 실측. 창 캡처 1920×1032 → calibrate.py 로 봉 격자·가격축 자동 보정 RMS 1.93px. 함정은 constraint_note 60. 사람 차트는 안 건드린다(새 차트+템플릿)"),
    (12, "HyperFrames", "github.com/hyperframes (로컬 clone 06_실험실/외부참고)", "HTML 로 합성 — MT5 틀 합성·좌표 계산 합성·A/B 판 (tools/hf/)", "Node · Chrome(.cache/hyperframes) · 59.94 유리수 fps 확인", "local-only", "우리 레이어에 없는 모양을 새로 만들 때만. 차트 컷씬은 우리 렌더러가 4.5배 빠르다(constraint_note 61). ProRes4444 알파·PNG 시퀀스 확인"),
    (13, "Remotion", "github.com/remotion-dev/remotion (로컬 clone)", "같은 목적 비교 대상", "-", "pending", "D 09-18 실측 — 59.94 fps·알파 확인. HyperFrames 와 같이 보류. 원문 D 외부도구 실측"),
    (14, "TypeSafe Jev 1.13 (System One 판단 모델)", "docs.typesafe.ai · api.typesafe.ai/v1/systemone", "판정관 — 배너·대본 후보를 팀장 기준(Score 단계)으로 채점, confidence 로 사람에게 넘길지 결정. 2순위: D 대본 비트 분류(Choice)", "pip typesafe-sdk(py≥3.10) · TYPESAFE_API_KEY(.secrets) · 입력 $0.042/M, 출력 무료 · 64k · 한국어 미문서", "pending", "이정찬 요청 09-21. 글을 안 만들고 판단만 — 정확히 decision 35 에서 보류한 자리. 약점(셈·날짜·부정문·긴 state·적대 문장)은 문서 명시 → 가드·자막 글자 수엔 안 쓴다. 시험 설계·합격선은 log/inbox/2026-09-21_총괄_Jev_판정관_시험제안.md, next_step 49"),
]

PRPROJ_FACTS = [
    (20, "숏츠 기본 양식.prproj", "숏폼 규격",
     "258KB → 2.9MB XML. FrameRate 8467200000 → 30.0fps. 모양 14 · 텍스트 10 · 그룹 10 · "
     "모션 7 · 마스크 5. 롱폼 프리셋보다 훨씬 단순하다",
     "gunzip 후 태그 집계"),
    (21, "숏츠 기본 양식.prproj", "숏폼 폰트·소스",
     "NotoSansKR-Black 이 숏폼에만 쓰인다(롱폼 프리셋에는 없음). "
     "그 외 GmarketSansTTFBold · S-CoreDream-6Bold · GyeonggiBatangB 는 롱폼과 같다. "
     "고정 소스: 차트명가_시네마스코프(숏).png, 차트명가_숏츠 아웃트로(풀영상 유도).mov, "
     "종이 배경.jpg, 효과음 뽁(뚜껑소리).wav · 딱(차트명가).mp3",
     "'소스 텍스트' base64 문자열 추출"),
    (10, "차명11 최종본 (drive 1nSw16I1CrCpzBMdZsqmeZf_tjEAFkOCe)", "규모",
     "607KB → 압축 해제 9.1MB. 텍스트 레이어 162개, 펜툴/도형 패스 96개, "
     "애니메이션 파라미터 16개에 키프레임 209개. 교차 디졸브 90회",
     "gunzip 후 태그 빈도 집계"),
    (11, "임의의 .prproj", "펜툴/도형 패스 인코딩",
     "'경로' 파라미터의 base64 = [int32 버전][int32 정점수] + 정점당 float32 7개 + 꼬리 1바이트(닫힘 여부). "
     "정점 7개 = [코너 플래그][들어오는 핸들 x,y][기준점 x,y][나가는 핸들 x,y]. "
     "핸들이 기준점과 같으면 직선 코너, 다르면 곡선. 메인프리셋 17/17개가 이 구조로 해석됨",
     "base64 디코드 후 struct.unpack('<7f')"),
    (12, "임의의 .prproj", "텍스트 레이어 인코딩",
     "'소스 텍스트' 파라미터의 base64 안에 [int32 길이][UTF-8] 형태로 폰트명과 문구가 그대로 들어 있다. "
     "프리셋에서 확인된 폰트: GmarketSansBold / GmarketSansTTFBold / GmarketSansTTFMedium / "
     "GyeonggiBatangB / NanumGothicOTF / S-CoreDream-5Medium / 6Bold / 7ExtraBold",
     "base64 디코드 후 길이 접두 문자열 스캔"),
    (13, "메인프리셋", "프리셋이 자기 자신을 설명한다",
     "프리셋 안에 색상 범례 슬라이드가 있다. 'ED7F89'·'EF2767' 같은 색상값 옆에 "
     "'메인 타이틀 위주' / '서브 타이틀 위주' / '전체 배경 또는 일반 본문 텍스트' / "
     "'부가 설명 자막, 배경 박스 테두리, 차트 UI 요소' 라는 용도 설명이 붙어 있다",
     "'소스 텍스트' 문자열 추출"),
    (14, "임의의 .prproj", "키프레임 인코딩",
     "<Keyframes> 는 평문이다. '틱,값,보간타입,0,0,베지어X,베지어Y,베지어Z;' 가 세미콜론으로 이어진다. "
     "1초 = 254,016,000,000틱. 보간타입 0=선형, 5=이즈",
     "정규식으로 <Keyframes> 추출 후 254016000000 으로 나눔"),
    (1, "brand/premiere/차트명가_메인프리셋(24버전).prproj", "파일 형식",
     "gzip 압축된 UTF-8 XML. 288KB → 압축 해제 3,696,594 바이트. 루트는 <PremiereData Version=\"3\">",
     "file 로 gzip 확인 후 gunzip -c"),
    (2, "brand/premiere/차트명가_메인프리셋(24버전).prproj", "프레임레이트",
     "FrameRate 는 틱값이며 1초 = 254,016,000,000 틱. 8475667200 → 29.97(드롭프레임), 8467200000 → 30.0, "
     "5292000 → 48000Hz, 5760000 → 44100Hz 오디오. 대본 타임코드가 29.97 인 근거가 프리셋에서 확인됨",
     "정규식으로 <FrameRate> 값 집계 후 254016000000 으로 나눔"),
    (3, "brand/premiere/차트명가_메인프리셋(24버전).prproj", "이펙트 구성",
     "텍스트 55 / 모양 39 / 모션 33 / 교차 디졸브 16 / 그룹 15 / 자르기 11 / 불투명도 9 / 변형 8 / 마스크 5 / "
     "벡터 모션 2 / 지우기 2 / 색조·시간 포스터화·파도 비틀기 각 1. 깜박임 제거 필터가 33곳에 걸려 있다",
     "<DisplayName> 빈도 집계"),
    (4, "brand/premiere/차트명가_메인프리셋(24버전).prproj", "회사 드라이브 실제 경로",
     "D:\\01_구글 드라이브(파가드AC)\\트레이딩팩토리\\ 아래에 "
     "02_영상_소스_롱폼\\차트명가(롱)\\차명_NN_* (회차별 원본·소스), "
     "04_영상_에셋_디자인 작업물\\06_공용 소스\\00_메인 프리셋(차트명가)\\ (로고·배경·아웃트로·중간광고), "
     "같은 곳 03_자주 쓰는 효과음+BGM\\01_효과음\\ 이 있다. "
     "[정정 2026-08-28] D:\\... 는 파일 안에 적힌 경로지 마운트 실측이 아니다 — 사무실 PC 실측은 "
     "G:\\내 드라이브\\트레이딩팩토리\\ 스트리밍 마운트(D: 드라이브 없음)이고, 마운트 문자는 "
     "PC 마다 다를 수 있다. 폴더 구조 자체는 그대로 유효하다",
     "<ActualMediaFilePath> 추출"),
    (5, "brand/premiere/차트명가_메인프리셋(24버전).prproj", "공용 애셋 이름",
     "매도 버튼(좌우).png, 차트명가_배경(종이).jpg, 종이 배경.jpg, 차트명가_배경(종이질감).mp4, "
     "차트명가_우측 로고 타이틀.png, 차트명가_유튜브 댓글 유도.png, 차트명가_아웃트로(fix).mp4, "
     "차 명가 bgm.wav, hyoushigi1.mp3, Nintendo Switch Snap Sound Effect",
     "미디어 경로에서 파일명만 추출"),
    (22, "임의의 .prproj", "열기만 해도 파일이 바뀐다",
     "app.openDocument() 만으로 프리미어가 파일을 다시 쓴다 — 복제도 저장도 안 했는데 "
     "288,434 → 278,880 바이트(8초). 내용은 정규화다: 같은 경로를 가리키던 중복 미디어 참조 1개와 "
     "StartKeyframe 점 60개가 정리됐고 고유 미디어 경로 52 는 불변. 그래서 검증 기준선은 원본이 아니라 "
     "'열고 아무것도 안 하고 저장한 파일' 로 잡아야 한다 — 원본 대비로 재면 정규화가 작업 손실처럼 보인다",
     "M1 실측(D) + 3자 재검증(B·클라우드). lab/premiere/m1_after_open_only.prproj"),
    (23, "brand/premiere/차트명가_메인프리셋(24버전).prproj", "시퀀스 복제의 성질",
     "sequence.clone() 은 공개 DOM 에 있다(qe 불필요). 복제하면 시퀀스 단위 객체 8종이 전부 +1, "
     "타임라인 내용물(클립·트랜지션·이펙트 파라미터 +1,722개)이 값 단위로 따라오고, 원본 미디어는 "
     "복사되지 않고 공유된다(고유 경로 52 불변·Markers 불변). 검증은 컨테이너(<Keyframes>) 말고 "
     "점(StartKeyframe)을 세고 시퀀스 단위 객체 전수(+1)를 본다 — 부분 복제를 훨씬 잘 잡는다",
     "M1: 기준선 대비 잃은 키프레임 블록 0 · StartKeyframe 5,906→10,571 (B 해시 다중집합 + 클라우드 재계산 일치)"),
    (24, "임의의 .prproj", "시퀀스를 스크립트로 만드는 유일한 길",
     "app.project.newSequence(이름, 역슬래시 .sqpreset 경로) 만 된다 — 슬래시 경로면 실패, 인자 하나면 "
     "Not Enough Parameters. createNewSequence(name,id) 는 '새 시퀀스' 모달을 띄워 세션을 죽인다(금지). "
     "qe.project.newSequence 는 true 를 주고 아무것도 안 만든다(거짓 성공). "
     "createNewSequenceFromClips 는 되지만 시퀀스가 클립의 프레임레이트를 따라간다(59.94 클립 → tb 4237833600). "
     "프리미어 기본 프리셋에 30.0 이 없어서 tools/premiere/presets/차트명가_1080p_30fps.sqpreset 을 만들어 뒀다"
     "(29.97 것을 복사해 VideoFrameRate 를 8467200000 으로)",
     "M6 실측(D). 다섯 호출 전부 시도"),
    (25, "임의의 .prproj", "qe 층의 편집 도구 3종",
     "qe...addTracks(1, idx, 0,0,0,0,0,0) — 원하는 깊이(idx)에 비디오 트랙 삽입, 기존 트랙이 밀리고 내용물 손실 0. "
     "성패는 반환값이 아니라 트랙 수 증가 + 새 트랙이 비었는지로 판정한다. "
     "qe...exportFramePNG(타임코드, 경로) — 역슬래시 경로만 받고 확장자를 스스로 붙인다(t.png → t.png.png). "
     "JPEG/TIFF/Targa/DPX 도 같은 규칙. qe...getVideoTrackAt(i).setName() — 트랙 이름 변경",
     "M4-c·M6 실측(D). 매뉴얼이 M4 의 '마지막 벽' 으로 남긴 트랙 깊이 문제가 addTracks 로 풀렸다"),
    (26, "임의의 .prproj", "키프레임·클립 조작의 함정 4건",
     "① 마지막 키는 클립 끝 틱이 아니라 끝−1프레임에 찍는다 — 끝 틱은 포함되지 않는 경계다. "
     "② 모션 속성 이름은 '비율' 이 아니라 '비율 조정' (같은 모션 안에 '폭 비율 조정'·'균일 비율' 도 있다). "
     "③ overwriteClip 은 덮은 자리의 프리셋 클립·키프레임을 오류 없이 지우고 새 클립은 프리셋 이펙트를 못 물려받는다. "
     "④ clip.end 는 Time 대입이 된다(문서에 없다) — 스틸을 기본 길이보다 길게 늘일 수 있다",
     "M3~M6 실측(D). ③의 파괴 사례는 lab/premiere/m4_place_v1_destructive.prproj 에 대조용으로 남김"),
    (27, "brand/premiere/차트명가_메인프리셋(24버전).prproj", "0~16초는 빈 자리가 아니라 고정 오프닝이다",
     "0~3.50 훅 스틸+'댓글 유도' 그래픽 / 5.93~12.20 인트로 애니메이션(지그재그+매수매도 태그, 9.60 부터 타이틀 카드) / "
     "12.20~14.73 빈 구간 / 14.73~ 본문(프리셋이 차트를 두는 자리, V1 chartA). 5.93~12.20 에 라벨 붙은 차트를 깔면 "
     "태그가 두 벌로 겹친다 — 그 구간은 라벨 없는 배경만. 파일을 뜯어 읽는 것만으로는 레이아웃 판단을 못 한다 — "
     "qe...exportFramePNG 로 합성 프레임을 뽑아서 봐야 한다",
     "M5 합성 프레임 실측(D). 증거 프레임 lab/premiere/frames/"),
]


# 최종본(.prproj)에서 디코드한 회사 고유 모션. 프리미어 없이 XML 을 읽어서 뽑았다.
MOTION_PRESETS = [
    (1, "밑줄/강조바 그리기", "높이 비율 조정", "1%", "100%", 4.0, 0.133, "선형 → 이즈",
     "차명11 최종본", "도형이 위에서 아래로 펼쳐지며 나타난다. 프리셋에도 같은 값이 있어 표준으로 보인다"),
    (2, "아래에서 올라오기", "위치", "0.5 : 1.1148", "0.5 : 0.5", 7.0, 0.234, "선형 → 이즈",
     "차명11 최종본", "화면 아래(높이의 111%)에서 중앙으로. 자막 박스 등장에 쓰인다"),
    (3, "왼쪽에서 튀어 들어오기", "위치", "-0.2562 : 0.5", "0.5 : 0.5", 15.0, 0.500,
     "이즈 4단 (오버슈트)", "차명11 최종본",
     "-0.256 → 0.544 → 0.4766 → 0.5. 중앙을 지나쳤다가 되돌아오는 바운스. 키프레임 4개 전부 이즈"),
    # 2026-09-03 — 최종 prproj 11편(차명01~10·14) 전수 파싱으로 재실측 (r13, log/data/prproj_kf_survey.json).
    # 차명11 실측 3종은 팀원 자작이라 표본에서 내렸고, 아래가 팀장 최종본들의 전량이다 (이 4종 외 등장 모션 없음).
    (4, "세로 펴기 등장", "높이 비율 조정", "1%", "100%", 4.0, 0.133, "끝 키프레임 베지어",
     "차명01~10·14 최종 prproj (70건)", "최다 등장 모션. 폭 100% 고정, 납작한 상태에서 세로로 펴진다"),
    (5, "아래→제자리 상승 등장", "위치", "960 : 1204", "960 : 540", 7.0, 0.234, "선형",
     "차명01~10·14 최종 prproj (20건)", "y 664px 상승 — 전 회차 픽셀 단위 동일"),
    (6, "균일 팝 등장", "비율 조정(스케일)", "1%", "100%", 4.0, 0.133, "끝 키프레임 베지어",
     "차명03·14 최종 prproj (7건)", "줌 계열 키프레임의 전부 — 느린 줌인(켄 번즈)은 전 회차 0건"),
    (7, "왼쪽 슬라이드 오버슈트", "위치 x", "-492", "960", 15.0, 0.500, "선형 4키",
     "차명01~05 최종 prproj (8건)", "-492 → 1045(+85) → 915(-45) → 960, 5f 간격. 감쇠 진동 정착"),
    (8, "교차 디졸브 (전환 표준)", "트랜지션", "-", "-", 30.0, 1.001, "-",
     "차명01~10·14 최종 prproj (858건 중 68%가 30f)", "전환의 지배 문법. 보조로 4~27f, 챕터 전환 40f+. "
     "그 외 비디오 트랜지션은 와이프(86건, 70%가 30f)뿐"),
]


FORMATS = [
    (1, "롱폼", "16:9",
     "1280x720 / 30fps (채널 최종본 실측)",
     "1920x1080 / 59.94fps (우리가 납품하는 컷씬 소스)",
     "10~20분", "차분한 설명조. 기획서+스크립트 6천자 안팎, 섹션 6개(후킹·소개·본론1·문제제시·본론2·아웃트로)",
     "작업중"),
    (2, "숏폼", "9:16",
     "1080x1920 / 30fps (최종본 260703 실측)",
     "미정 (모션그래픽 단계 미착수)",
     "목표 45초. 나간 편 실측 중앙값 55.9초 (자막 13편)",
     "대본은 조사됨 — 훅·근거·본론·CTA 4단, 초당 6.6자, 한 편이 롱폼의 9%. "
     "화면 톤앤매너는 아직 미조사",
     "조사됨"),
]

PIPELINE = [
    # 롱폼
    (1, "롱폼", "1", "대본 만들기",
     "기획서+스크립트 .docx 작성. 타이틀·메인·목차·섹션 6개·매매법 설정값까지 한 문서에 들어간다",
     "사람", 0, "자료만",
     "저장소에는 결과물 인덱스만 있다 (script_doc 15편 + script_fts 전문 검색). 작성 자체는 하지 않는다"),
    (2, "롱폼", "1.5", "성우 녹음",
     "대본을 성우에게 넘겨 녹음본을 받는다. 이 녹음이 타임코드의 기준이 된다",
     "외부", 0, "해당없음", "저장소가 관여하지 않는다"),
    (3, "롱폼", "2", "컷편집 및 자막 달기",
     "프리미어에서 녹음본에 맞춰 컷을 자르고 자막을 얹는다. 여기서 나온 타임코드(.srt)가 3단계 입력이 된다",
     "사람", 0, "해당없음",
     "자막·타이틀·로고는 여기서 이미 들어가므로 3단계 렌더에는 넣지 않는다"),
    (9, "롱폼", "2.5", "썸네일 제작",
     "템플릿 .psd 규격대로 차트·타이틀 2줄·틀·로고를 얹어 만든다. 회차당 여러 안을 뽑아 팀장이 고른다",
     "로컬 클로드 B", 0, "진행중",
     "기준은 tools/photoshop/ (포토샵 COM + build_thumb.jsx + config.json, B 로컬). 차트 입력은 "
     "이 저장소의 scenes/thumb-*.scenes.js 를 렌더러로 뽑아 준다. 컨테이너 대체 경로 "
     "tools/thumbnail_png.py 는 scene 키 있는 안만 뽑을 수 있고 차12 config(전부 emphasis 안)는 "
     "처리 못 한다 — 규격은 thumbnail_rule 29개, 벽은 constraint_note"),
    (4, "롱폼", "3", "모션그래픽 및 소스 넣기",
     "타임코드가 붙은 대본을 받아 차트 컷씬을 프레임 단위로 렌더해 납품한다. 프리미어에 얹는 것은 사람이 한다",
     "이 저장소", 1, "진행중",
     "workflow_step 테이블의 9단계가 이 단계의 내부 절차다"),
    # 숏폼
    (5, "숏폼", "1", "대본 만들기",
     "롱폼 챕터 하나를 골라 350~560자로 다시 쓴다. 규칙은 shortform_rule, 지시서 작성·검사는 "
     "tools/shortform.py",
     "E 세션", 0, "진행중",
     "2026-09-01 E 세션으로 이관 — 규칙·작성 지시서·검사 도구는 이 저장소가 준다. "
     "대본을 대신 쓰는 게 아니고 최종 판단은 사람이 한다"),
    (6, "숏폼", "1.5", "성우 녹음", "롱폼과 같은 방식으로 보이나 확인 안 됨", "외부", 0, "해당없음", None),
    (7, "숏폼", "2", "컷편집 및 자막 달기",
     "STT(faster-whisper)로 녹음을 전사해 무음 경계에서 컷을 자른다. 자막 .srt 는 큐 14자 규칙으로 뽑는다",
     "이 저장소 + E 세션", 1, "진행중",
     "STT 컷편집(tools/cutedit/)은 이 저장소, .srt 추출(srt_rules.py)은 2026-09-01 E 이관 — 매뉴얼 §8"),
    (8, "숏폼", "3", "모션그래픽 및 소스 넣기",
     "1:1 1080×1080 / 30fps 소스 클립. 씬은 scenes/sl-*.scenes.js, 실제 가시 영역은 1080×937 (constraint 33)",
     "이 저장소", 1, "진행중",
     "차11-4·11-5 를 이 규격으로 납품했다 (씬·컷리스트·내레이션 정렬까지 한 꾸러미)"),
]


# ── 숏폼 대본 만드는 법 ──────────────────────────────────────────────
# 숏폼 25편과 그 원본 롱폼 13편을 문장·n-gram 단위로 맞춰 본 결과.
# hits/total 은 기존 24편(파일 기준) 중 몇 편이 그렇게 했는지.
SHORTFORM_RULES = [
    # 무엇을 고르는가
    (1, "고르기", "숏폼 한 편 = 롱폼 챕터 한 개. 여러 챕터를 섞지 않는다",
     "일정표의 '추출 원본' 열이 모두 '롱폼 추출(차NN_… 편)' 하나를 가리킨다. "
     "차09 는 '4.문제 제시'→#1, '5.핵심(제품)'→#2, "
     "차11 은 '전략 1'→#4, '전략 2'→#5 로 챕터가 그대로 한 편이 된다",
     None, None, "필수"),
    (2, "고르기", "#1 은 롱폼 앞쪽, #2 는 뒤쪽에서 온다",
     "롱폼을 10구간으로 나눠 4자 n-gram 겹침이 가장 큰 구간을 찾으면 "
     "차01(20~30%→50~60%) 차02(20~30→60~70) 차03(30~40→60~70) 차06(30~40→60~70) "
     "차07(20~30→50~60) 차08(10~20→40~50) 차09(40~50→80~90) 차10(40~50→80~90) — "
     "12쌍 중 11쌍에서 #1 이 #2 보다 앞선다",
     11, 12, "권장"),
    (3, "고르기", "#1 은 '왜 필요한가/무엇이 문제인가', #2 는 '그래서 어떻게 하는가'",
     "차09_#1 '단일지표를 쓰면 안되는 이유'(문제 제시) → #2 'RSI안 볼린저밴드 더하기'(핵심). "
     "차11_#1 '20일선 120% 활용법' → #2 '횡보장은 이렇게 대응하자'",
     None, None, "권장"),
    (4, "고르기", "롱폼 한 편에서 숏폼 2편이 기본. 많으면 5편까지",
     "일정표 SL 47건 / 롱폼 15편. 차11 만 #1~#5 다섯 편이고 나머지는 2~3편",
     None, None, "수치"),
    # 어떻게 쓰는가
    (5, "쓰기", "복붙이 아니라 다시 쓴다",
     "숏폼 본문과 롱폼의 10자 n-gram 겹침 중앙값 2.2% (최대 28%). "
     "문장 단위로 봐도 그대로 옮긴 문장은 3% 뿐이고 61% 는 새로 쓴 문장이다",
     None, None, "필수"),
    (6, "쓰기", "분량은 롱폼 전체의 9% 안팎",
     "숏폼 본문(제목·마커·CTA 상투구 제외) / 롱폼 전체 = 중앙값 9.1%, 평균 10.2%",
     None, None, "수치"),
    (7, "쓰기", "45초가 목표. 307자다",
     "팀장님이 정한 이상적인 길이가 45초. 초당 6.82자(자막 13편 실측 중앙값)를 곱하면 307자. "
     "허용 밴드는 40~50초 = 273~341자",
     None, None, "필수"),
    (20, "쓰기", "나간 편들은 목표보다 24% 길다 — 55.9초",
     "자막 실측 13편: 영상 길이 중앙값 55.9초(39.3~83.4), 자수 중앙값 401자. "
     "45초 밑은 차04_#1(39.9초) 차09_#1(39.3초) 차04_#2(42.0초) 셋뿐이다. "
     "목표는 목표고 실태는 실태다 — 새로 쓸 때는 45초를 노린다",
     3, 13, "수치"),
    (21, "쓰기", "줄일 때는 본문에서만 줄인다",
     "자막 실측에서 훅 26자/3.6초, CTA 26자/2.7초는 전체 길이와 무관하게 거의 고정이고 "
     "본문(341자/49.0초)만 늘고 준다. 45초면 본문이 255자다",
     None, None, "필수"),
    (8, "쓰기", "초기보다 길어졌다. 5월 중순 344자 → 5월 말 이후 482자",
     "2026-05-29 을 경계로 구조 마커(①②③④)가 붙기 시작하고 분량이 40% 늘었다",
     None, None, "수치"),
    # 문구
    (9, "문구", "훅은 «오늘은 …를 알려드릴게요» 한 문장",
     "24편 중 22편. 예외는 차08_#1, 차12_#1", 22, 24, "필수"),
    (10, "문구", "«아래/다음 영상» 으로 넘긴다", "24편 중 20편", 20, 24, "권장"),
    (11, "문구", "근거에 역접을 한 번 넣는다 — 하지만/그런데/반대로", "24편 중 19편", 19, 24, "권장"),
    (12, "문구", "«저를 팔로우하고 / 구독해주세요»", "24편 중 17편", 17, 24, "권장"),
    (13, "문구", "CTA 를 답 없이 «…무엇일까요?» 로 넘긴다",
     "24편 중 10편. 5월 말 이후에 늘어난 최신 방식이라 선택으로 둔다", 10, 24, "선택"),
    (14, "문구", "«그렇다면» 으로 본론에서 CTA 로 넘어간다", "24편 중 13편", 13, 24, "선택"),
    # 이어붙이기
    (15, "잇기", "#N 의 CTA 질문이 곧 #N+1 의 주제다",
     "차11_#1 '박스권 횡보장에서는 어떻게?' → #2 '횡보장은 이렇게 대응하자'. "
     "차10_#1 '추세장인지 어떻게 수치로 걸러낼까요?' → #2 'ADX 지표'. "
     "차09_#1 '익절 기준은?' → #2 'RSI안 볼린저밴드 더하기'. "
     "차08_#1 '단타와 스윙을 모두 잡는 설정은?' → #2 '스텝 스토캐스틱 5분 단타'",
     None, None, "필수"),
    # 하지 않는 것
    (16, "제외", "'포인트(포)' 편은 이 규칙이 아니다",
     "일정표 유형이 '숏폼(포)' 인 47건은 '추출 원본' 이 외부 유튜브 링크나 "
     "TF_ 레퍼런스다. 롱폼 추출이 아니라 따로 기획한 편이라 규칙이 다르다",
     None, None, "필수"),
    (18, "이름", "폴더는 YYMMDD_[SL_차XX_#X]숏폼제목, 파일은 [SL]숏폼제목[롱폼제목#X].txt",
     "폴더 규칙은 나간 25편이 25/25 로 지켰다. 파일 규칙은 5/25 인데 지킨 것이 "
     "차09·차11 로 최근 편들이라 새 표준으로 본다. naming_rule 테이블 참고",
     25, 25, "필수"),
    (19, "이름", "작업 중에는 폴더·파일 맨 앞에 (중간) 을 붙인다",
     "확정되면 뗀다. tools/shortform.py name --final",
     None, None, "필수"),
    (17, "제외", "자막·타이틀·로고 문구는 대본에 쓰지 않는다",
     "숏폼 프리미어 기본 양식(숏츠 기본 양식.prproj)에 텍스트 레이어가 이미 들어 있다",
     None, None, "필수"),
    # 22~27 은 포인트_차 갈래 — SL 규칙과 별도다 (E 세션 2026-08-28 실측, log/SCRIPT-LAB.md)
    (22, "포인트", "기준선은 New 10편(260725~261001) — 중앙 53.9초 · 362자 · 6.70자/초. SL 값(6.82·307자)을 쓰면 안 된다",
     "차명 포인트_차 43편 전수 · 자막 36편 실측. Old 를 섞으면 분포가 끌려간다(속도 7.41 로 올라감). "
     "Old/New 경계는 팀장 지정 — 260725_포지션 중독부터 New",
     10, 10, "필수"),
    (23, "포인트", "갈래별로 속도가 다르다 — 토크 6.91~9.19(415~495자) · 기법 6.49~7.63 · 모드A 복제 5.71~6.19",
     "New 10편 자막 실측. 토크편은 말이 빨라 같은 초에 글자가 더 들어간다",
     None, None, "수치"),
    (24, "포인트", "트팩 원본과의 간격이 카피 모드를 가른다 — 5.5개월 이상이면 모드 A(근접 복제, 겹침 48~71%), "
     "2개월 이내면 모드 B(뼈대만, 겹침 1~5% — 문장은 다시 쓴다)",
     "트팩↔차명 짝 7건 10자 n-gram 실측. 두 채널에 비슷한 영상이 가까운 시점에 같이 나가지 않게 하는 규칙. "
     "모드 A 편은 차명 폴더에 TF(참고)_ 폴더가 통째로 들어 있다",
     7, 7, "필수"),
    (25, "포인트", "트팩 라이브에서 나온 주제는 차명이 먼저 만들고 트팩이 받는다. 방향은 참고 폴더 위치로 판정한다",
     "트팩이 차명을 벤 3편(긁히는 것·후행스팬·테스타 이평선)은 트팩 폴더에 대본 대신 라이브 질문 브리프만 있다",
     3, 3, "필수"),
    (26, "포인트", "모집단에서 재업·파생을 걸러라 — 260718 숏포지션=260525, 260801 볼린저밴드=260430 (대본 md5 동일)",
     "안 거르면 창 12편 중 4편(3분의 1)이 오염된 기준선이 된다",
     None, None, "필수"),
    (27, "포인트", "원본이 라이브 발화물이면 라이브톤을 죽이지 않는다 (팀장 판단) — 2행에 "
     "'**라이브 방송 중 답변한다는 느낌으로', 구어 종결(~거든요·~잖아요), 훅 «오늘은~» 면제",
     "New 토크편 260725·260730 실측. 차명이 라이브를 한다는 뜻이 아니다 — 연기 지시다. "
     "CTA 는 '동의하면 구독과 좋아요 / 반박하면 댓글도 환영입니다'",
     2, 2, "필수"),
]

THUMBNAIL_RULES = [
    (1, "캔버스", "1920x1080", "템플릿 아트보드", None),
    (2, "틀", "핑크 #EF2767 테두리 26px, 모서리 각짐", "완성본 11장 실측",
     "템플릿의 '틀' 은 도형 레이어라 그대로 뽑으면 안쪽 흰 면까지 딸려 온다. 실측값으로 다시 그린다"),
    (3, "배경", "종이 텍스처 (거의 흰색)", "템플릿 '종이 배경' 레이어, 4,-84 에 배치", None),
    (4, "타이틀 윗줄(서브)", "#FFFFFF · GmarketSansBold · 검정 외곽선 · 자간 -40",
     "글자 높이 141px 고정 · 왼쪽 x=88 · 베이스라인 y=198 · 폭은 1017~1306 으로 자유",
     "후킹 문구. 강조할 때는 #FF0000 (차07·차08·차10 이 그렇게 했다). "
     "예전에 '폭을 맞춘다' 고 적어 둔 것은 오해였다 — #2~#6 다섯 회차를 재 보니 글자 크기가 고정이고 폭이 변한다"),
    (5, "타이틀 아랫줄(메인)", "#FFFF00 · GmarketSansBold · 검정 외곽선 · 자간 -40",
     "글자 높이 194px 고정 · 왼쪽 x=74 · 베이스라인 y=395 · 폭은 1148~1583 으로 자유",
     "매매법 이름. #1 쿠라마기만 가운데 정렬(anchor 642 / 683)인 예외이고 #2~#10 은 왼쪽 정렬이다"),
    (6, "로고", "차트명가_로고(최종+핑크) 좌하단", "49, 977 · 209x52", None),
    (7, "차트", "매매법의 핵심을 한 장으로. 한 차트로 대본 전체를 설명할 수 있어야 한다",
     "우리 렌더러가 그린다 (scenes/thumb-*.scenes.js)",
     "브랜드 색 그대로 — 상승 #0B8C7F · 하락 #E80001 · 이평선 #F38808"),
    (8, "태그", "매수 #FF0000 (189x90) · 익절 #00FF24 (185x90). 흰 글씨, 외곽선·그림자 없음",
     "템플릿 픽셀 실측. 몸통 0~140 은 세로가 꽉 차고 141~185 가 화살촉, 꼭짓점은 세로 한가운데. "
     "왼쪽 모서리만 둥글다. 글자는 몸통 안에서 9px 여백",
     "**직접 그리지 않는다.** 템플릿 레이어를 topil() 로 뜯어 brand/thumbnail/btn_*.png 로 저장해 두었다. "
     "익절은 매수 버튼을 좌우 반전한 모양에 Color Overlay #00FF24 가 걸린 것이고, "
     "흰 '익절' 글자는 그 위 별도 텍스트 레이어다. "
     "**지금 기준은 렌더러(cmgArrow)가 그리는 쪽이다.** 차11 A·C 안이 그렇게 납품됐고 팀장 확인도 났다. "
     "브랜드 비율을 그대로 넣으니 189x90 · 화살촉 0.49h 로 위 실측값과 같게 나오고, "
     "라벨이 매수·익절 말고 다른 글자여도 같은 모양으로 붙는다(decision 15). "
     "btn_*.png 는 포토샵을 못 쓰는 컨테이너에서 쓰는 대체 경로다"),
    (16, "종이 텍스처 겹치기", "흰 바탕 → 종이 배경 30% → 배경 지운 차트",
     "완성본 흰 부분 250.2 = 0.3x239(종이) + 0.7x255. 캔들은 254.7 로 안 눌린다",
     "템플릿은 차트를 두 장 쓴다 — 밑에 원본, 위에 배경을 지운 복사본. 그 사이에 종이(77/255)가 낀다. "
     "우리는 렌더러가 --format alpha 로 배경 없는 차트를 바로 뽑으므로 한 장이면 된다"),
    (17, "타이틀 효과", "획 6px 검정 바깥쪽 · 그림자 검정 76%, 90도, 거리 10, 스프레드 11%, 크기 18",
     "레이어 fx(lfx2) 실측. 레이어를 키워도 효과는 스케일되지 않는다",
     "손으로 흉내 내지 말고 psd-tools 가 템플릿의 lfx2 를 그대로 그리게 한다"),
    (9, "인물", "[선택] 1순위는 유명 인물 + 그 인물을 소개하는 짧고 강렬한 텍스트",
     "차01·02·03·05·07 은 실존 트레이더, 차10 은 익명 스케치",
     "차11(20일선)은 특정 인물이 없는 회차라 넣지 않았다. 넣으려면 이미지를 받아야 한다"),
    (11, "타이틀 레이어 효과", "획 6px 검정 100% + 그림자 검정 76%/각도 90°/거리 10/스프레드 11/크기 18",
     "템플릿 텍스트 레이어 fx 를 그대로 읽은 값. 완성본 PNG 에서 노랑 글자 앞 검정 두께가 정확히 6px",
     "내부 광선·그레이디언트 오버레이는 걸려만 있고 꺼져 있다. "
     "레이어를 키워도 효과는 스케일되지 않는다 — 크기를 두 배로 해도 획은 6px 그대로"),
    (12, "태그 효과", "매수 버튼 = 외부 광선 검정 18%/확장 72/크기 10, 익절 = 색상 오버레이 #00FF24",
     "템플릿 fx", "전체 효과 값은 log/data/thumbnail_fx.json 에 32개 레이어분이 들어 있다"),
    (14, "만드는 방법", "템플릿 .psd 를 열어 회차 그룹을 통째로 복제하고 그 안만 바꾼다",
     "tools/psdedit.py — 그룹 복제 · 텍스트 교체 · 픽셀 교체 · 솔로",
     "처음부터 새로 쓰면 그룹·스마트오브젝트·조정레이어·레이어 효과·라이브 텍스트가 다 날아간다. "
     "템플릿을 편집하면 레이어 구성이 100% 그대로 남는다"),
    (15, "복제 후 끄는 것", "인물(그룹 1)과 매수 버튼(좌우)",
     None, "인물은 원본 회차 얼굴이라 회차가 바뀌면 안 맞고, 매수 버튼은 우리 차트가 이미 태그를 그린다"),
    (13, "내가 만들지 않는 것", "로고와 틀은 회사 자산이라 그대로 쓴다",
     None, "손대는 것은 차트 그림 · 문구 · 인물 그림(선택) 세 가지뿐이다"),
    (10, "문구", "윗줄 = 이득·문제 후킹, 아랫줄 = 매매법 이름",
     "'3년만에 100배 수익 / 이동평균선 매매법', '손절 없이 수익 내는 / 양방향 매매법', "
     "'매일 100만원 수익내는 / MACD 매매법'",
     "숫자와 손실 회피가 자주 쓰인다"),
    (18, "버튼 글씨", "에스코어 드림 5 Medium (SCDream5.otf, weight 500) 흰색",
     "브랜드 버튼 원본 픽셀 · #7 썸네일의 '익절' 텍스트 레이어가 S-CoreDream-5Medium 38px",
     "타이틀(Gmarket Sans Bold)과 다른 폰트다. 검정 외곽선은 없다. "
     "렌더러에서는 theme.fontTag / fontTagWeight 로 한 군데서 관리한다 — cmgArrow·cmgBadge·cmgLevel 이 쓴다. "
     "주석(cmgNote)은 버튼이 아니라 GmarketSans 계열이다"),
    (19, "인물 판단 기준", "주인공 트레이더가 있는 회차만 넣는다",
     "10장 중 8장에 인물이 있다. 없는 것은 #9 RSI 위에 볼린저밴드, #6 지지와 저항 — 둘 다 지표가 주제인 회차다",
     "인물이 있으면 차트가 좌측 2/3 로 밀리고, 없으면 차트가 화면 전체를 쓴다. 규칙 9 의 판단 기준이다"),
    (20, "지표 이름 라벨", "지표가 둘 이상일 때만 붙인다",
     "#9 는 (RSI)·(볼린저밴드) 두 개, #6 은 '지지선' 하나. GmarketSansMedium 36px 자간 -40",
     "#11 은 선이 20일선 하나뿐이고 타이틀이 이미 이름을 말해서 붙이지 않았다. 붙여 보니 캔들과 겹치기만 했다"),
    (21, "회차마다 반드시 바꾸는 것", "차트에 그 매매법의 핵심 시각 요소를 하나 심는다",
     "#6 초록 지지선 + '지지선' 라벨 / #9 지시 화살표 + 괄호 라벨 / #10 매수①~매도⑥ 번호 화살표 / "
     "#2 스토캐스틱 서브차트 + 가짜신호 X 표시",
     "차트가 그냥 캔들 그림이면 어느 회차인지 알 수 없다. 규칙 7 을 회차 단위로 푼 것이다"),
    # 22~25 는 로컬 세션의 2026-08-28 문자 단위 실측 (10회차 전수, dump_text_runs.jsx)
    (22, "윗줄 부분 빨강",
     "맨 앞 단어만 #FF0000 · 나머지는 흰색 유지",
     "10회차 중 3개뿐 — #8 가짜신호[0,4) · #10 변동성[0,3) · #7 가짜 반등[0,5) 는 #FF5353",
     "셋 다 부정어다. 문제를 윗줄에 던지고 아랫줄에서 해법을 준다. "
     "긍정문 윗줄에는 빨강을 쓰지 않는다 — 그래서 차11 C 안에는 안 넣었다"),
    (23, "빨강은 크기를 데리고 온다",
     "빨강 구간은 기준 대비 1.174배 (#7 만 1.087배)",
     "#8·#10 은 11.95px -> 14.03px · #7 은 11.95px -> 12.99px",
     "색만 바꾸면 채널 것처럼 안 보인다. 색과 크기가 항상 같이 움직인다"),
    (24, "크기만 쓰는 강조가 더 흔하다",
     "숫자·지표 이름을 1.17~1.32배로 키운다 · 색은 그대로",
     "#1 100배 1.323 · #10 수익 1.274 · #9 단일지표 1.174 · #8-a RSI 1.174 · #7 100만원 1.087",
     "10회차 중 7개에 있다. 아랫줄(노랑)에도 쓴다 — #9 안에 0.866"),
    (25, "조사는 줄여서 명사를 띄운다",
     "조사·어미를 0.826배로 눌러 앞 명사를 도드라지게",
     "#4 진입타점[부터] 목표가[까지] 11.95px -> 9.87px",
     "줄이 길어 최대폭(윗줄 1306)에 걸릴 때 특히 쓸모 있다 — 키우는 대신 줄이면 폭이 준다. "
     "차11 C2 가 이 방식이다"),
    (26, "차트가 타이틀 자리를 피해서 그려져야 한다",
     "글자가 앉는 자리는 격자박스 (75,100)~(1306,394) 안이다 — 규칙 28 이 정한 상자",
     "차12 실측(격자박스 적용 후) — 아랫줄 (75,225,1313,394) · 윗줄 (78,102,862,224)",
     "차트를 그릴 때 include 로 가격 눈금 천장에 없는 값을 끼워 캔들을 그 아래로 내린다. "
     "오른쪽 태그(익절·손절)는 상자 오른쪽(1306)보다 오른쪽에서 시작하게 봉 번호를 고른다. "
     "글자에 획 6px+그림자가 있어 조금 겹치는 것은 읽히지만, 태그가 글자 밑에 깔리면 태그가 죽는다. "
     "규칙 28 이 붙기 전 차12 1차 시안은 아랫줄이 1563 까지 나가 익절 태그와 붙었다 — "
     "그때 잡은 봉 번호(A 익절 91봉)는 지금 상자에서는 여유가 남는다"),
    (27, "틀과 로고가 차트 가장자리를 먹는다",
     "안전 영역은 x 26~1894 · y 26~1054 이고 왼쪽 아래 (49~258, 977~1029)는 로고 자리다",
     "틀 26px(규칙 2) · 로고 49,977 209x52(규칙 6)",
     "차12 1차 시안에서 RSI 배지를 왼쪽 아래(84,1028)에 뒀다가 로고와 겹쳤고, "
     "RSI 패널의 55/45 라벨은 패널 오른쪽 끝(r.right-14)에 붙는 구현이라 틀 밑에 반쯤 잘렸다. "
     "배지는 오른쪽 아래(1560,1005)로 옮기고, 라벨은 씬의 layout.padRight 를 40 으로 줘서 안으로 들였다 — "
     "차트 배경이 흰색이라 오른쪽에 생긴 40px 띠는 종이 배경과 구분되지 않는다"),
    (28, "타이틀은 크기를 베끼지 말고 격자박스에 넣는다",
     "좌상단 타이틀 상자는 (75,100)~(1306,394). 두 줄 중 넓은 줄이 상자 폭(1231)을 넘으면 "
     "두 줄을 같은 배율로 줄인다. 안 넘으면 그대로 두고, 절대 키우지 않는다",
     "차12 아랫줄이 1488px 라 x0.827(17% 축소) — 세 안 다 같은 배율로 (75,225,1313,394) 에 들어갔다",
     "규칙 4·5 의 고정 높이(윗줄 141 · 아랫줄 194)는 그대로다. 이건 그 위에 얹은 상한선이다 — "
     "짧은 문구는 예전 회차와 똑같은 크기로 남고, 긴 문구만 줄어든다. "
     "옛 컨테이너 방식(폭을 항상 상자에 맞춰 크기를 역산)과 다르다. 저건 짧은 문구를 거대하게 만든다. "
     "상자 오른쪽 1306 은 열 회차 완성본의 윗줄 관측 최대폭이다 — 아랫줄은 그보다 넓게 나간 회차가 "
     "있었지만 그건 차트를 덮는다. 두 줄을 따로 줄이면 윗줄·아랫줄 크기 비가 회차마다 달라져서 "
     "넓은 줄 하나가 배율을 정하고 두 줄에 똑같이 건다. 강조(규칙 22~25) 배율은 줄인 크기 기준이고, "
     "강조 글자는 베이스라인이 고정이라 상자 위로 솟는다 — 위쪽 한계는 상자가 아니라 틀 안쪽 26px 다. "
     "구현은 config.json 의 titleBox + build_thumb.jsx. 사람이 사이즈를 손으로 정하지 않는다"),
    (29, "영상 쪽 상자는 룰북 ⑮ 가 원본이다 — 썸네일은 별도다",
     "영상(고정 양식): 좌상단 타이틀 가로 35%×세로 20% · 우상단 로고 가로 12%×세로 20% · "
     "자막 세로 15% · 콘텐츠 존 y 216~918. 썸네일: 좌상단 타이틀 상자 (75,100)~(1306,394)",
     "영상 값은 이정찬이 프리미어 격자로 실측(2026-09-02, 요청 60) — brand/EDIT-RULEBOOK.md ⑮ 가 원본. "
     "썸네일 값은 열 회차 완성본 실측(규칙 4·5·28)",
     "숫자를 옮겨 적지 마라 — 영상은 룰북 ⑮, 썸네일은 여기(규칙 28)를 본다. 매체가 달라 상자가 다르다. "
     "같은 것은 방식이다: 크기를 회차마다 손으로 정하지 말고 상자를 먼저 정하고 거기 맞춘다. "
     "2026-09-03 이정찬이 그 프리미어 스샷 4장을 다시 들고 와 '썸네일도 이렇게 하라'고 지시해 "
     "규칙 28 이 나왔다 (요청 67)"),
    (30, "작업실 경로를 박지 않는다 — 스스로 찾게 한다",
     "config.json 의 template·chartDir·outDir 은 작업실 폴더 기준 상대경로다. 작업실은 "
     "CMGWORK_DIR → config.labDir → 위로 8단계 '06_실험실/cmgwork' → 'cmgwork' → C:/cmgwork 순서로 찾는다",
     "2026-09-16 C:/cmgwork 이 통합 폴더로 옮겨지며 박아 둔 경로 셋이 한꺼번에 끊긴 뒤 고침. "
     "고친 뒤 A안을 실제로 빌드해 9/3 납품본과 픽셀 동일 확인",
     "구현은 labdir.ps1(PowerShell)·_labdir.jsx(ExtendScript). jsx 는 import 가 없지만 $.evalFile 은 있어서 "
     "파일마다 복사하지 않고 한 파일을 불러 쓴다. run.ps1 이 맨 처음 '작업실: …' 을 찍으니 거기서 확인한다. "
     "tools/ae/labdir.py·.mjs·.ps1 과 같은 규칙이다 — 규칙을 두 개로 만들지 않는다. "
     "포토샵 템플릿은 링크 자원이 없어(전부 임베드) 옮겨도 다시 연결할 것이 없었다"),
]

NAMING_RULES = [
    (1, "숏폼 폴더", "YYMMDD_[SL_차XX_#X]숏폼제목",
     "260827_[SL_차11_#4]20일선 추세추종 매매법",
     "나간 25편 중 25편",
     "날짜는 방영일이다. 작업 중에는 오늘 날짜를 쓰고 확정할 때 방영일로 바꾼다"),
    (2, "숏폼 파일", "[SL]숏폼제목[롱폼제목#X].txt",
     "[SL]20일선 추세추종 매매법[20일선의 비밀#4].txt",
     "나간 25편 중 5편",
     "롱폼제목은 작업물 폴더 '차명11_20일선의 비밀' 에서 앞머리를 뗀 것. "
     "지킨 5편이 차09·차11 로 최근 편들이라 이쪽이 새 표준이다"),
    (3, "작업 중", "맨 앞에 (중간) 을 붙인다",
     "(중간)260827_[SL_차11_#4]20일선 추세추종 매매법 / "
     "(중간)[SL]20일선 추세추종 매매법[20일선의 비밀#4].txt",
     None,
     "폴더와 파일 둘 다 붙인다. 확정되면 뗀다 — tools/shortform.py name --final"),
    (4, "만들기·검사", "tools/shortform.py 가 이름을 만들고 검사한다",
     "python3 tools/shortform.py name 11 --no 4 --title '20일선 추세추종 매매법'",
     None,
     "check 명령도 파일·폴더 이름을 같이 본다"),
    (5, "포인트_차 폴더·파일", "폴더 YYMMDD_[포인트_차]제목 · 파일 [포인트_차]제목.txt",
     "260810_[포인트_차]후행스팬 / [포인트_차]후행스팬.txt",
     "차명 43편 전수 일치",
     "SL 규칙([SL_차XX_#X])과 다르다. (중간) 접두 규칙은 공통"),
    (6, "트팩 포인트 원본", "폴더 YYMMDD_[포인트]제목 · 파일 [포인트]제목.txt",
     "260809_[포인트]진화한 세력들의 악랄한 움직임",
     None,
     "트팩(트레이딩팩토리) 쪽 원본 표기. 차명으로 가져올 때 [포인트_차] 가 된다"),
]

# 45초(=307자) 기준. 자막 13편 실측에서 훅·CTA 는 길이와 무관하게 거의 고정이고
# 본문만 늘고 준다는 것이 나왔으므로, 줄일 때는 본문에서만 줄인다.
SHORTFORM_PARTS = [
    (1, 1, "① 훅 (Hook)", "무엇을 알려줄지 한 문장. 길이와 무관하게 고정 (실측 중앙값 26자 / 3.6초)",
     20, 35, "오늘은 {주제}를 알려드릴게요"),
    (2, 2, "② 근거 (Evidence)", "왜 이게 문제인가. 통념 → 역접 → 손실", 90, 130,
     "많은 분들이 … 합니다 / 하지만 … / 그래서 손실로 이어집니다"),
    (3, 3, "③ 본론 (Body)", "어떻게 하는가. 기준·설정값·순서를 숫자로. 분량은 여기서 조절한다",
     135, 155, "첫째 … 둘째 … / 손절은 … / 청산 신호는 …"),
    (4, 4, "④ 아웃트로 (CTA)", "다음 편으로 넘기는 질문 + 고정 3줄 (실측 중앙값 26자 / 2.7초)",
     20, 35, "그렇다면 {다음 주제}는 무엇일까요? / 더 자세한 내용이 궁금하시다면 / "
     "저를 팔로우하고 / 아래 영상을 주목해주세요"),
]


def load_shortform():
    """log/data/shortform.json — 숏폼 대본과 일정표 매칭."""
    f = ROOT / "log" / "data" / "shortform.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def load_checkpoints():
    """log/data/checkpoints.json — 세이브 슬롯. 커밋 해시는 태그에서 역으로 구한다."""
    f = ROOT / "log" / "data" / "checkpoints.json"
    if not f.exists():
        return []
    rows = json.loads(f.read_text(encoding="utf-8"))
    for r in rows:
        # 태그는 푸시가 막혀 있어 새 컨테이너에는 없다. json 에 적힌 해시가 먼저다.
        if not r.get("sha"):
            out = subprocess.run(["git", "rev-list", "-n", "1", "--abbrev-commit", r["tag"]],
                                 cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            r["sha"] = out.stdout.strip() or None
    return rows


def load_scripts():
    """log/data/scripts.json — 작업물 폴더에서 긁어온 회차별 대본 인덱스."""
    f = ROOT / "log" / "data" / "scripts.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def git_commits():
    """커밋마다 git show 를 띄우던 것을 git log 한 번으로 (2026-09-18 검토 ②).
    455커밋에서 rebuild 6.2초 중 대부분이 여기였다 — 세이브 한 번에 두 번 돈다."""
    try:
        out = subprocess.run(
            ["git", "log", "--reverse", "--shortstat", "--diff-merges=first-parent", "--pretty=format:%x1e%H%x1f%aI%x1f%s"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    except Exception as e:
        print(f"  경고: git log 실패 — commit_log 가 빈다 ({e})", file=sys.stderr)
        return []
    import re
    rows = []
    for i, block in enumerate([b for b in out.split("\x1e") if b.strip()], 1):
        head, _, stat = block.partition("\n")
        sha, authored, subject = head.split("\x1f")
        stat = stat.strip()
        files = ins = dele = None
        if stat:
            m = re.search(r"(\d+) files? changed", stat)
            files = int(m.group(1)) if m else None
            m = re.search(r"(\d+) insertions?", stat)
            ins = int(m.group(1)) if m else 0
            m = re.search(r"(\d+) deletions?", stat)
            dele = int(m.group(1)) if m else 0
        rows.append((i, sha, authored, subject, files, ins, dele))
    return rows


def build():
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    for suffix in ("-wal", "-shm"):
        p = Path(str(DB) + suffix)
        if p.exists():
            p.unlink()

    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)

    con.execute("INSERT INTO session VALUES (?,?,?,?,?,?)", SESSION)
    con.executemany("INSERT INTO request (seq,asked,did,outcome) VALUES (?,?,?,?)", REQUESTS)
    con.executemany("INSERT INTO phase (seq,title,detail,status) VALUES (?,?,?,?)", PHASES)
    con.executemany(
        "INSERT INTO script_line (id,project,section,seq,tc_in,tc_out,frames_2997,seconds,text)"
        " VALUES (?,?,?,?,?,?,?,?,?)", SCRIPT_LINES)
    con.executemany(
        "INSERT INTO scene (id,config,scene_id,name,seq,fps,frames,seconds,script_line_id,synopsis)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)", SCENES)

    for scene_id, path, fmt, w, h, fps, frames, alpha, note in RENDERS:
        f = ROOT / path
        size = f.stat().st_size if f.exists() else None
        con.execute(
            "INSERT INTO render (scene_id,path,format,width,height,fps,frames,bytes,alpha,note)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (scene_id, path, fmt, w, h, fps, frames, size, alpha, note))

    con.executemany(
        "INSERT INTO brand_token (category,name,value,unit,source,note) VALUES (?,?,?,?,?,?)", BRAND)
    con.executemany(
        "INSERT INTO asset (kind,name,drive_id,bytes,stored,note) VALUES (?,?,?,?,?,?)", ASSETS)
    con.executemany(
        "INSERT INTO issue (seq,title,symptom,root_cause,fix,verification,status)"
        " VALUES (?,?,?,?,?,?,?)", ISSUES)
    con.executemany(
        "INSERT INTO decision (seq,topic,choice,rationale,revisit_when) VALUES (?,?,?,?,?)", DECISIONS)

    # -z 를 써야 공백·한글이 든 경로가 쪼개지지 않는다
    raw = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    files = [f for f in raw.split("\0") if f]
    seen = set()
    for path in files:
        for key, (role, note) in REPO_FILES.items():
            if path == key or path.startswith(key + "/"):
                target = key
                break
        else:
            target, role, note = path, "기타", None
        if target in seen:
            continue
        seen.add(target)
        con.execute("INSERT INTO repo_file (path,role,note) VALUES (?,?,?)", (target, role, note))

    con.executemany("INSERT INTO runbook (seq,topic,purpose,command,note) VALUES (?,?,?,?,?)", RUNBOOK)
    con.executemany("INSERT INTO env_tool (name,version,location,install,note) VALUES (?,?,?,?,?)", ENV_TOOLS)
    con.executemany("INSERT INTO drive_map (kind,name,drive_id,parent,note) VALUES (?,?,?,?,?)", DRIVE_MAP)
    con.executemany("INSERT INTO layer_catalog (name,family,purpose,key_options) VALUES (?,?,?,?)", LAYERS)
    con.executemany("INSERT INTO scene_option (grp,key,meaning,example) VALUES (?,?,?,?)", SCENE_OPTIONS)
    con.executemany(
        "INSERT INTO trade_setup (config,instrument,seed,bars,entry,stop,target,rr,entry_bar,tp_bar,run_high,run_r,note)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", TRADE_SETUPS)
    con.executemany("INSERT INTO constraint_note (topic,limit_value,workaround) VALUES (?,?,?)", CONSTRAINTS)
    con.executemany("INSERT INTO next_step (seq,item,detail,blocked_by) VALUES (?,?,?,?)", NEXT_STEPS)
    con.executemany(
        "INSERT INTO benchmark (id,measured_on,config,mode,cores,frames,seconds_video,wall_seconds,fps_capture,note)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)", BENCHMARKS)
    con.executemany("INSERT INTO format VALUES (?,?,?,?,?,?,?,?)", FORMATS)
    con.executemany(
        "INSERT INTO pipeline_stage (id,format,seq,name,detail,owner,in_repo,status,note)"
        " VALUES (?,?,?,?,?,?,?,?,?)", PIPELINE)
    con.executemany(
        "INSERT INTO workflow_step (seq,step,how,who,status,note) VALUES (?,?,?,?,?,?)", WORKFLOW_STEPS)
    con.executemany(
        "INSERT INTO external_tool (id,name,source,purpose,requirement,verdict,reason)"
        " VALUES (?,?,?,?,?,?,?)", EXTERNAL_TOOLS)
    con.executemany(
        "INSERT INTO prproj_fact (id,file,topic,finding,method) VALUES (?,?,?,?,?)", PRPROJ_FACTS)
    con.executemany(
        "INSERT INTO motion_preset (id,name,param,from_value,to_value,frames_2997,seconds,easing,source,note)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)", MOTION_PRESETS)

    for i, c in enumerate(load_checkpoints(), 1):
        con.execute("INSERT INTO checkpoint (id,tag,kst,utc,sha,summary) VALUES (?,?,?,?,?,?)",
                    (i, c["tag"], c["kst"], c["utc"], c.get("sha"), c["summary"]))

    con.executemany(
        "INSERT INTO shortform_rule (id,grp,rule,evidence,hits,total,tier) VALUES (?,?,?,?,?,?,?)",
        SHORTFORM_RULES)
    con.executemany(
        "INSERT INTO shortform_part (id,seq,name,purpose,chars_min,chars_max,phrasing)"
        " VALUES (?,?,?,?,?,?,?)", SHORTFORM_PARTS)
    con.executemany(
        "INSERT INTO naming_rule (id,scope,pattern,example,conformance,note) VALUES (?,?,?,?,?,?)",
        NAMING_RULES)
    con.executemany(
        "INSERT INTO thumbnail_rule (id,part,spec,measured,note) VALUES (?,?,?,?,?)",
        THUMBNAIL_RULES)

    sf = load_shortform()
    if sf:
        for i, d in enumerate(sf.get("srt", {}).get("docs", []), 1):
            pt = d["parts"]
            con.execute(
                "INSERT INTO shortform_srt (id,folder,file,drive_id,seconds,cues,chars,cps,"
                "hook_sec,hook_chars,body_sec,body_chars,cta_sec,cta_chars,rerun)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (i, d["folder"], d["file"], d["drive_id"], d["seconds"], d["cues"], d["chars"],
                 d["cps"], pt["hook"]["sec"], pt["hook"]["chars"], pt["body"]["sec"],
                 pt["body"]["chars"], pt["cta"]["sec"], pt["cta"]["chars"],
                 1 if d["rerun"] else 0))
        for i, d in enumerate(sf["docs"], 1):
            con.execute(
                "INSERT INTO shortform_doc (id,aired,ep,no,folder,file,drive_id,chars,est_sec,"
                "long_window,ngram4,ngram10,size_ratio,rerun) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (i, d["date"], d["ep"], d["no"], d["folder"], d["file"], d["drive_id"],
                 d["chars"], d["est_sec"], d["long_window"], d["ngram4"], d["ngram10"],
                 d["size_ratio"], 1 if d["rerun"] else 0))
            con.execute("INSERT INTO shortform_fts (folder,body) VALUES (?,?)",
                        (d["folder"], d["text"]))
        import re as _re
        for i, r in enumerate(sf["schedule_sl"], 1):
            m = _re.search(r"차(\d{2})", r["title"] + r["source"])
            con.execute(
                "INSERT INTO shortform_map (id,aired,kind,title,source,ep) VALUES (?,?,?,?,?,?)",
                (i, r["date"], r["type"], r["title"], r["source"],
                 int(m.group(1)) if m else None))

    sc = load_scripts()
    if sc:
        for d in sc["docs"]:
            con.execute(
                "INSERT INTO script_doc (ep_no,ep,file,drive_id,chars,headline,keywords,status)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (d["ep_no"], d["ep"], d["file"], d["drive_id"], d["chars"],
                 d["headline"], ", ".join(d["keywords"]), d["status"]))
            con.execute("INSERT INTO script_fts (ep,file,body) VALUES (?,?,?)",
                        (d["ep"], d["file"], d["text"]))
            for kw, n in d["counts"].items():
                con.execute(
                    "INSERT OR REPLACE INTO script_keyword (keyword,ep,hits) VALUES (?,?,?)", (kw, d["ep"], n))
        for r in sc["prproj"]:
            con.execute("INSERT INTO episode_prproj (ep,name,drive_id,kind) VALUES (?,?,?,?)",
                        (r["ep"], r["name"], r["drive_id"], r["kind"]))
    con.executemany(
        "INSERT INTO commit_log (seq,sha,authored,subject,files_changed,insertions,deletions)"
        " VALUES (?,?,?,?,?,?,?)", git_commits())

    con.commit()
    con.execute("PRAGMA journal_mode = DELETE")  # .db 한 파일로 떨어지게
    con.execute("VACUUM")
    con.commit()
    return con


def summarize(con):
    q = lambda s: con.execute(s).fetchall()
    print(f"\n  {DB.relative_to(ROOT)}  ({DB.stat().st_size / 1024:.0f} KB)\n")
    print("  테이블별 행 수")
    for (name,) in q("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        (n,) = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()
        print(f"    {name:14} {n:4}")
    print("\n  컷 ↔ 대본 싱크")
    for r in q("SELECT scene_id, tc_in, tc_out, frames_2997, frames_5994, seconds FROM v_cut_sync"):
        print(f"    {r[0]:22} {r[1]} → {r[2]}  {r[3]:3}f(29.97) / {r[4]:3}f(59.94)  {r[5]}s")
    print("\n  렌더 요약")
    for fmt, files, frames, mb in q("SELECT * FROM v_render_summary"):
        print(f"    {fmt:6} {files:2}개  {frames:5}프레임  {mb:8.1f} MB")
    print()


def export_md(con):
    """DB 내용을 사람이 읽는 마크다운으로 옮긴다."""
    q = lambda s, *a: con.execute(s, a).fetchall()
    out = []
    w = out.append

    ses = q("SELECT * FROM session")[0]
    w("# 작업 로그 — 차트 컷씬 렌더러\n")
    w(f"- 날짜: {ses[1]}")
    w(f"- 저장소: `{ses[2]}` / 브랜치 `{ses[3]}`")
    w(f"- 목표: {ses[4]}")
    w(f"- 환경: {ses[5]}\n")
    w("> 이 문서는 `log/worklog.db` 에서 뽑아냅니다. 고칠 때는 `log/build_worklog_db.py` 를 고치고 다시 실행하세요.\n")

    w("## 처음 여는 사람에게\n")
    for ordn, step, detail in q("SELECT ord, step, detail FROM v_start_here"):
        w(f"{ordn}. **{step}** — {detail}")
    w("")

    w("### 환경 다시 깔기\n")
    w("| 도구 | 버전 | 위치 | 설치 | 비고 |")
    w("|---|---|---|---|---|")
    for name, ver, loc, inst, note in q("SELECT name,version,location,install,note FROM env_tool ORDER BY id"):
        w(f"| {name} | {ver or ''} | `{loc or ''}` | {inst} | {note or ''} |")
    w("")

    w("### 명령어\n")
    for seq, topic, purpose, cmd, note in q("SELECT seq,topic,purpose,command,note FROM runbook ORDER BY seq"):
        w(f"**{seq}. {topic}** — {purpose}")
        w(f"```\n{cmd}\n```")
        if note:
            w(f"{note}\n")
    w("")

    w("### 파일 지도\n")
    w("| 경로 | 역할 | 설명 |")
    w("|---|---|---|")
    for path, role, note in q("SELECT path,role,note FROM repo_file ORDER BY role, path"):
        w(f"| `{path}` | {role} | {note or ''} |")
    w("")

    w("## 원본 자료 (구글 드라이브)\n")
    w("폴더 목록: `curl -sSL 'https://drive.google.com/embeddedfolderview?id=<ID>#list'`  \n")
    w("파일 받기: `curl -sSL -o out 'https://drive.usercontent.google.com/download?id=<ID>&export=download&confirm=t'`\n")
    w("| 종류 | 이름 | Drive ID | 비고 |")
    w("|---|---|---|---|")
    for kind, name, did, note in q("SELECT kind,name,drive_id,note FROM drive_map ORDER BY id"):
        w(f"| {kind} | {name} | `{did}` | {note or ''} |")
    w("")

    w("## 컷을 짤 때 쓰는 재료\n")
    w("### 레이어 22종\n")
    w("| 이름 | 계열 | 쓰임 | 주요 옵션 |")
    w("|---|---|---|---|")
    for name, fam, purpose, opts in q("SELECT name,family,purpose,key_options FROM layer_catalog ORDER BY id"):
        w(f"| `{name}` | {fam} | {purpose} | {opts} |")
    w("")
    w("### 씬 설정 키\n")
    w("| 그룹 | 키 | 뜻 | 예 |")
    w("|---|---|---|---|")
    for grp, key, meaning, ex in q("SELECT grp,key,meaning,example FROM scene_option ORDER BY id"):
        w(f"| {grp} | `{key}` | {meaning} | `{ex or ''}` |")
    w("")
    w("### 컷에 쓴 매매 수치\n")
    w("| 설정 | 종목 | seed | 캔들 | 진입 | 손절 | 익절 | 손익비 | 이후 고점 | 비고 |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for cfg, inst, seed, bars, en, st, tg, rr, hi, rrun, note in q(
            "SELECT config,instrument,seed,bars,entry,stop,target,rr,run_high,run_r,note FROM trade_setup ORDER BY id"):
        w(f"| `{cfg}` | {inst} | {seed} | {bars} | {en:,.2f} | {st:,.2f} | {tg:,.2f} | {rr} | {hi:,.1f} ({rrun}) | {note} |")
    w("")

    w("## 환경이 거는 제약\n")
    w("| 항목 | 한계 | 대응 |")
    w("|---|---|---|")
    for topic, lim, wa in q("SELECT topic,limit_value,workaround FROM constraint_note ORDER BY id"):
        w(f"| {topic} | {lim} | {wa} |")
    w("")

    w("## 다음에 할 일\n")
    for seq, item, detail, blocked in q("SELECT seq,item,detail,blocked_by FROM next_step ORDER BY seq"):
        tail = f"  _(대기: {blocked})_" if blocked else ""
        w(f"{seq}. **{item}** — {detail}{tail}")
    w("")

    w("## 대본과 컷 싱크\n")
    w("타임코드는 29.97 드롭프레임. 59.94fps 로 렌더해서 프레임 수가 정확히 2배가 됩니다.\n")
    w("| 컷 | 타임코드 | 29.97 | 59.94 | 초 | 대사 |")
    w("|---|---|---|---|---|---|")
    for r in q("SELECT * FROM v_cut_sync"):
        w(f"| `{r[1]}` | {r[3]} → {r[4]} | {r[5]}f | {r[6]}f | {r[7]} | {r[8]} |")
    w("")

    w("## 진행\n")
    w("| # | 단계 | 내용 |")
    w("|---|---|---|")
    for seq, title, detail, status in q("SELECT seq,title,detail,status FROM phase ORDER BY seq"):
        w(f"| {seq} | {title} | {detail} |")
    w("")

    w("## 요청과 대응\n")
    for seq, asked, did, outcome in q("SELECT seq,asked,did,outcome FROM request ORDER BY seq"):
        w(f"**{seq}. {asked}**")
        w(f"→ {did}" + (f" ({outcome})" if outcome else ""))
        w("")

    w("## 문제와 해결\n")
    for seq, t, sym, cause, fix, ver, st in q(
            "SELECT seq,title,symptom,root_cause,fix,verification,status FROM issue ORDER BY seq"):
        w(f"### {seq}. {t}  `{st}`")
        w(f"- 증상: {sym}")
        w(f"- 원인: {cause}")
        w(f"- 조치: {fix}")
        if ver:
            w(f"- 확인: {ver}")
        w("")

    w("## 판단과 근거\n")
    for seq, topic, choice, why, revisit in q(
            "SELECT seq,topic,choice,rationale,revisit_when FROM decision ORDER BY seq"):
        w(f"- **{topic}** — {choice}")
        w(f"  - 이유: {why}")
        if revisit:
            w(f"  - 다시 볼 때: {revisit}")
    w("")

    w("## 브랜드 스펙 (실측)\n")
    w("| 분류 | 항목 | 값 | 단위 | 출처 | 비고 |")
    w("|---|---|---|---|---|---|")
    for cat, name, val, unit, src, note in q(
            "SELECT category,name,value,unit,source,note FROM brand_token ORDER BY id"):
        w(f"| {cat} | {name} | `{val}` | {unit or ''} | {src} | {note or ''} |")
    w("")

    w("## 렌더 산출물\n")
    w("| 파일 | 포맷 | 프레임 | 크기 | 비고 |")
    w("|---|---|---|---|---|")
    for path, fmt, frames, b, note in q(
            "SELECT path,format,frames,bytes,note FROM render ORDER BY id"):
        mb = f"{b/1048576:.1f} MB" if b else "-"
        w(f"| `{path}` | {fmt} | {frames or '-'} | {mb} | {note or ''} |")
    w("")

    w("## 받아 온 자료\n")
    w("| 종류 | 이름 | 크기 | 처리 | 비고 |")
    w("|---|---|---|---|---|")
    for kind, name, b, stored, note in q(
            "SELECT kind,name,bytes,stored,note FROM asset ORDER BY id"):
        mb = f"{b/1048576:.0f} MB" if b else "-"
        w(f"| {kind} | {name} | {mb} | {stored} | {note or ''} |")
    w("")

    w("## 커밋\n")
    w("| # | sha | 제목 | 변경 |")
    w("|---|---|---|---|")
    for seq, sha, subj, f, i, d in q(
            "SELECT seq,sha,subject,files_changed,insertions,deletions FROM commit_log ORDER BY seq"):
        w(f"| {seq} | `{sha[:8]}` | {subj} | {f}파일 +{i}/-{d} |")
    w("")

    path = ROOT / "log" / "WORKLOG.md"
    path.write_text("\n".join(out), encoding="utf-8")
    return path


if __name__ == "__main__":
    con = build()
    print(f"{DB.relative_to(ROOT)} 생성 완료")
    if "--md" in sys.argv:
        p = export_md(con)
        print(f"{p.relative_to(ROOT)} 생성 완료")
    if "--print" in sys.argv:
        summarize(con)
    con.close()
