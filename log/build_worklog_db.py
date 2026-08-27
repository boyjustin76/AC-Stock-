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

-- 세이브 슬롯 (git 태그 = 되돌릴 수 있는 시점)
CREATE TABLE checkpoint (
  id            INTEGER PRIMARY KEY,
  tag           TEXT NOT NULL UNIQUE,
  kst           TEXT NOT NULL,
  utc           TEXT NOT NULL,
  sha           TEXT,
  summary       TEXT NOT NULL
);

-- 처음 여는 사람이 순서대로 읽을 것
CREATE VIEW v_start_here AS
SELECT 1 AS ord, '무엇을 하는 저장소인가' AS step, goal AS detail FROM session
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
    "해외선물 유튜브(차트명가) 영상용 차트 모션그래픽 소스 영상을 코드로 렌더한다",
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
]


REPO_FILES = {
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
}

RUNBOOK = [
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
]

DRIVE_MAP = [
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
    (1, "새 대본 받으면", "타임코드를 프레임으로 환산(같은 분 안이면 드롭프레임 보정 불필요) → scenes/cmg-20ma-runner.scenes.js 를 본떠 새 config 를 만들고 layers 를 채운다 → --stills 로 구도 확인 → --all --reel", None),
    (2, "전략 1 컷 (아직 안 만듦)", "기획서의 익절 기준이 '종가가 20일선을 하방 이탈하는 음봉, 아래꼬리조차 20일선에 닿지 않는 완전 이격 캔들'. 이 조건을 그대로 그리는 컷이 뒤에 필요하다", "대본"),
    (3, "전략 2 컷 (아직 안 만듦)", "박스권 횡보장 스위칭. 이평선이 눕는 것 확인 → 직전 고점 윗꼬리·저점 아랫꼬리로 라인 → 하단 지지에서 매수, 상단 저항에서 익절", "대본"),
    (4, "규격 통일 여부", "채널 최종본은 720p/30fps. 1080p/59.94 유지 중인데 다른 소스와 맞출지 결정 필요", "사용자 판단"),
    (6, "컷별 병렬 렌더 스크립트", "지금은 셸에서 손으로 백그라운드를 띄운다. "
     "npm run render:par 로 코어 수만큼 자동 샤딩하게 만들면 매번 절반 시간에 끝난다", "사용자 승인"),
    (8, "차명14·15 대본 미작성", "두 회차 문서가 927자짜리 빈 템플릿이고 본문이 서로 완전히 동일하다. "
     "레퍼런스로 쓸 수 없으니 대본이 채워지면 log/data/scripts.json 을 다시 만든다", "사용자"),
    (9, "모션 문법 표본 부족", "motion_preset 3종은 차명11 최종본 하나에서만 뽑았다. "
     "다른 회차 .prproj 도 같은 방식으로 훑으면 회사 표준 이징·지속시간이 더 정확해진다", None),
    (7, "알파(.mov) 렌더 시간 미측정", "mp4 는 956프레임에 순차 93초/병렬 45초로 쟀는데 "
     "무손실 알파(qtrle)는 파일이 커서 I/O 가 더 붙는다. 필요해지면 따로 측정한다", None),
    (5, "로고 워터마크", "지금은 렌더에 넣지 않음(프리미어 프리셋과 중복). 필요하면 image 레이어로 brand/logo 사용", None),
]


BENCHMARKS = [
    (1, "2026-08-26", "scenes/cmg-20ma-runner.scenes.js", "serial", 4, 956, 15.95, 93.0, 10.3,
     "컷 4개를 --all 로 차례로. 컷별 250f/23.4s, 234f/19.6s, 152f/14.6s, 320f/26.9s"),
    (2, "2026-08-26", "scenes/cmg-20ma-runner.scenes.js", "parallel", 4, 956, 15.95, 45.0, 21.2,
     "컷별 프로세스 4개 동시. 순차 대비 2.07배. 결과물이 순차와 md5 까지 동일해 렌더가 결정론적임을 확인"),
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
    (8, "렌더", "컷별 프로세스를 코어 수만큼 동시에 띄운다", "자동", "ready", "benchmark 2번 참고"),
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
                                 cwd=ROOT, capture_output=True, text=True)
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
            cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except Exception:
        return []
    rows = []
    for i, line in enumerate(out.splitlines(), 1):
        sha, authored, subject = line.split("\x1f")
        stat = subprocess.run(
            ["git", "show", "--shortstat", "--pretty=format:", sha],
            cwd=ROOT, capture_output=True, text=True).stdout.strip()
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
    raw = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True).stdout
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
