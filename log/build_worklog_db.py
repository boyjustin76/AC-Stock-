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
]


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
