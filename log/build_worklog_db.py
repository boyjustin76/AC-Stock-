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
import os
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
       '롱폼 파이프라인 4단계 중 3. 모션그래픽 및 소스 넣기. 1·2 단계와 숏폼은 아직 범위 밖 (v_scope 참고)' AS detail
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
UNION ALL SELECT 13, '파일·폴더 이름 규칙', 'naming_rule 테이블'\nUNION ALL SELECT 14, '썸네일 만드는 법', 'thumbnail_rule / tools/thumbnail.py'
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
]

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
]


REPO_FILES = {
    "tools/psdedit.py": ("도구", "템플릿 .psd 를 편집한다 — 그룹 복제·텍스트 교체·픽셀 교체"),
    "src/tools/profile-render.mjs": ("도구", "한 프레임이 어디에 시간을 쓰는지 쪼개서 잰다"),
    "src/tools/exp-capture.mjs": ("도구", "캡처 경로 4가지를 실전 루프로 재고 픽셀·mp4 md5 동일성을 대조한다"),
    "log/THUMBNAIL-REVIEW.md": ("문서", "썸네일 코드 검토 보고서 + 로컬 푸시 확인 절차 (2026-08-27)"),
    "log/RENDER-REVIEW.md": ("문서", "렌더 속도 리뷰 의뢰서 — 코드 지도·실측·열린 질문"),
    "tools/thumbnail_png.py": ("도구", "롱폼 썸네일을 .png 로 뽑는다 — 차트 한 장, 완성본 한 장"),
    "brand/thumbnail/btn_매수.png": ("에셋", "템플릿에서 뜯은 매수 버튼 원본 픽셀 (189x90)"),
    "brand/thumbnail/btn_익절.png": ("에셋", "매수 버튼을 좌우 반전해 #00FF24 로 칠하고 익절 글자를 얹은 것 (185x90)"),
    "brand/thumbnail/틀.png": ("에셋", "템플릿 '틀' 도형 원본 픽셀 (안쪽 투명)"),
    "brand/thumbnail/로고.png": ("에셋", "템플릿 로고 원본 픽셀 (209x52)"),
    "brand/thumbnail/종이배경.png": ("에셋", "템플릿 종이 텍스처 원본 픽셀"),
    "tools/psdwrite.py": ("도구", ".psd 를 직접 쓴다 (레이어·한글 이름·RLE)"),
    "tools/thumbnail.py": ("도구", "썸네일 조립 — 타이틀 자동 크기, 템플릿 효과"),
    "brand/thumbnail": ("애셋", "템플릿에서 뽑은 로고·종이 배경"),
    "out/thumbnail": ("산출물", "차11 썸네일 2안 (.psd + 미리보기)"),
    "scenes/thumb-ch11.scenes.js": ("씬", "차11 썸네일용 차트 2안"),
    "tools/photoshop/dump_episodes.jsx": ("도구", "완성 회차를 한 장씩 뽑고 레이어 트리를 받아 적는다 — 규칙을 뽑을 때"),
    "tools/photoshop/dump_layer_fx.jsx": ("도구", "레이어 효과(lfx2)를 ActionManager 로 값까지 읽는다"),
    "tools/photoshop/build_thumb.jsx": ("도구", "회차 그룹 복제 → 차트 교체 → 타이틀 교체 → 다른 회차 제거 → .psd/.png/.jpg"),
    "tools/photoshop/config.json": ("설정", "템플릿·차트·출력 경로와 회차 문구"),
    "tools/photoshop/run.ps1": ("도구", "포토샵을 COM 으로 띄워 .jsx 를 실행하는 드라이버"),
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
    "deliver/thumbnail": ("산출물", "채택된 썸네일. out/ 은 .gitignore 라 여기에 따로 둔다"),
}

RUNBOOK = [
    (0, "썸네일 만들기", "롱폼 썸네일을 템플릿 규격대로 조립해 .psd 로 쓴다",
     "npm run render -- --config scenes/thumb-ch11.scenes.js --all --stills 1 --out out/thumb"
     " && python3 tools/thumbnail.py '차명#11_...v1' --chart out/thumb/stills/thumb-a_t0.00s.png"
     " --sub '손익비 1:5 만드는' --main '20일선 매매법'",
     "타이틀 크기는 폭(윗줄 1120 · 아랫줄 1185)에 맞춰 자동으로 잡힌다"),
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
    (14, "레이어 효과 값 읽기", "템플릿에 실제로 걸린 fx 를 값으로",
     ".\\tools\\photoshop\\run.ps1 dump_layer_fx",
     "DOM 에는 레이어 효과를 읽는 길이 없다. executeActionGet 으로 layerEffects 를 직접 뜯는다"),
    (12, "로그 갱신 (윈도우)", "윈도우에서 DB·MD·HTML 다시 뽑기",
     "$env:PYTHONUTF8='1'; python log/build_worklog_db.py --md; python log/build_worklog_page.py; python log/build_readme.py",
     "PYTHONUTF8 없이는 한글 경로에서 cp949 로 죽는다. --print 는 out/ 이 없으면 요약 단계에서 터지니 빼고 쓴다"),
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
    ("cmgNote", "차트명가", "차트 위 외곽선 주석", "text, bar, price, x, y, size, color"),
    ("cmgCircle", "차트명가", "손그림 색연필 원 강조", "bar, price, rx, ry, width, drawDur, turns"),
    ("cmgUnderline", "차트명가", "손그림 빨간 밑줄", "bar, price, dy, width, align, thickness, drawDur"),
    ("cmgMissed", "차트명가", "놓친 구간 빗금 + 화살표", "from, to, fromBar, color, arrow(false 로 화살표 끔), arrowFrac"),
    ("image", "공통", "이미지 (로고 등). engine 이 미리 로드", "src, x, y, width, align, opacity"),
    ("flash", "공통", "컷 전환용 플래시", "at, dur, strength, color"),
    ("watermark", "공통", "채널명 워터마크", "text, x, y, opacity, align"),
    ("letterbox", "공통", "상하 시네마 레터박스", "height, color"),
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
    ("저장소에 없는 것", "템플릿 차트명가(롱)_하이라이트 - 복사본.psd(180MB)와 완성본 레퍼런스 PNG 10장은 "
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
    (16, "차11 썸네일 마감", "A(추세추종)·C(통합) 채택. 최종 파일은 deliver/thumbnail/차11_20일선의 비밀/ 에 있다. "
     "B(박스권)는 요소가 많다는 이유로 보류 — 씬 파일과 미리보기 png 는 남겨 두었다",
     None),
    (17, "다음 회차 썸네일", "tools/photoshop/config.json 의 group·variants 만 바꾸면 된다. "
     "인물이 있는 회차면 base 를 #5 나 #7 로 바꾸고 '그룹 1'(인물 자리)에 이미지를 넣는다",
     "회차 대본과 인물 이미지"),
    (18, "1세대 썸네일 도구의 타이틀 크기 계산", "tools/thumbnail.py 의 fit_size 와 psdedit 의 _fit·bake_text 가 "
     "아직 '폭에 맞춰 폰트 크기를 역산' 하는 방식이다. 완성본 실측으로 규칙이 뒤집혔으므로"
     "(글자 높이 고정·폭 자유, thumbnail_rule 4·5) 그 경로로 뽑으면 규격이 어긋난다. "
     "포토샵이 없는 환경에서 그 도구를 다시 쓸 일이 생기면 먼저 고쳐야 한다",
     "리눅스에서 썸네일을 다시 뽑아야 할 때"),
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
     "같은 곳 03_자주 쓰는 효과음+BGM\\01_효과음\\ 이 있다",
     "<ActualMediaFilePath> 추출"),
    (5, "brand/premiere/차트명가_메인프리셋(24버전).prproj", "공용 애셋 이름",
     "매도 버튼(좌우).png, 차트명가_배경(종이).jpg, 종이 배경.jpg, 차트명가_배경(종이질감).mp4, "
     "차트명가_우측 로고 타이틀.png, 차트명가_유튜브 댓글 유도.png, 차트명가_아웃트로(fix).mp4, "
     "차 명가 bgm.wav, hyoushigi1.mp3, Nintendo Switch Snap Sound Effect",
     "미디어 경로에서 파일명만 추출"),
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
     "사람", 0, "미착수",
     "자막·타이틀·로고는 여기서 이미 들어가므로 3단계 렌더에는 넣지 않는다"),
    (9, "롱폼", "2.5", "썸네일 제작",
     "템플릿 .psd 규격대로 차트·타이틀 2줄·틀·로고를 얹어 만든다. 보통 2~3안을 뽑는다",
     "로컬 클로드", 0, "자료만",
     "**이 컨테이너는 손을 뗐다.** 포토샵이 있는 PC 의 클로드가 .psd 를 직접 다룬다. "
     "여기서 남긴 자료는 그대로 쓰면 된다 — thumbnail_rule 17개(규격 실측), "
     "log/data/thumbnail_fx.json(레이어 32개 효과값), brand/thumbnail/*.png(템플릿에서 뜯은 원본 픽셀), "
     "tools/thumbnail_png.py·psdedit.py·thumbnail.py, scenes/thumb-ch11.scenes.js. "
     "constraint_note 에 이미 부딪힌 벽이 적혀 있으니 먼저 읽는 편이 빠르다"),
    (4, "롱폼", "3", "모션그래픽 및 소스 넣기",
     "타임코드가 붙은 대본을 받아 차트 컷씬을 프레임 단위로 렌더해 납품한다. 프리미어에 얹는 것은 사람이 한다",
     "이 저장소", 1, "진행중",
     "workflow_step 테이블의 9단계가 이 단계의 내부 절차다"),
    # 숏폼
    (5, "숏폼", "1", "대본 만들기",
     "롱폼 챕터 하나를 골라 350~560자로 다시 쓴다. 뽑는 규칙을 숏폼 25편에서 역으로 구해 "
     "shortform_rule 17개로 정리했고 tools/shortform.py 가 지시서 작성과 검사를 한다",
     "사람 + 이 저장소", 1, "진행중",
     "대본을 대신 쓰는 게 아니라 규칙·지시서·검사를 제공한다. 최종 판단은 사람이 한다"),
    (6, "숏폼", "1.5", "성우 녹음", "롱폼과 같은 방식으로 보이나 확인 안 됨", "외부", 0, "해당없음", None),
    (7, "숏폼", "2", "컷편집 및 자막 달기", "9:16 세로 프레임. 자막 크기·위치가 롱폼과 다르다", "사람", 0, "미착수", None),
    (8, "숏폼", "3", "모션그래픽 및 소스 넣기",
     "세로 프레임용 차트 레이아웃이 따로 필요하다. 렌더러는 그대로 쓰되 layout·visibleBars 를 다시 잡아야 한다",
     "이 저장소", 0, "미착수",
     "먼저 최종본 숏츠를 실측해 톤앤매너부터 잡아야 한다"),
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
    try:
        out = subprocess.run(
            ["git", "log", "--reverse", "--pretty=format:%H%x1f%aI%x1f%s"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    except Exception:
        return []
    rows = []
    for i, line in enumerate(out.splitlines(), 1):
        sha, authored, subject = line.split("\x1f")
        stat = subprocess.run(
            ["git", "show", "--shortstat", "--pretty=format:", sha],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.strip()
        files = ins = dele = None
        if stat:
            import re
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
