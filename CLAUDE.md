# 차트 컷씬 렌더러 — 새 세션이 먼저 읽을 것

해외선물 유튜브 채널 **차트명가** 영상에 쓸 차트 모션그래픽 소스 영상을 코드로 렌더한다.

## 여기부터

1. **`log/worklog.db`** (SQLite) 가 작업 기록의 원본이다. 읽는 형태는 `log/WORKLOG.md`,
   보는 형태는 `log/worklog.html`. 셋 다 `log/build_worklog_db.py` 에서 만들어진다.
2. `brand/STYLE.md` — 브랜드 스펙. 색·크기는 전부 레퍼런스 영상에서 실측한 값이다. 짐작으로 바꾸지 않는다.
3. `README.md` — 렌더러 사용법.

```sql
-- 컨텍스트가 날아갔을 때 순서대로
SELECT * FROM v_start_here;
SELECT * FROM env_tool;        -- 환경 다시 깔기
SELECT * FROM runbook;         -- 명령어
SELECT * FROM repo_file;       -- 어디에 무엇이 있나
SELECT * FROM drive_map;       -- 원본 자료 위치 (구글 드라이브 ID)
SELECT * FROM next_step;       -- 다음에 할 일
SELECT * FROM layer_catalog;   -- 컷을 짤 때 쓰는 레이어 22종
SELECT * FROM constraint_note; -- 이미 부딪혀 본 벽
SELECT * FROM v_cut_sync;      -- 대본과 컷 싱크
SELECT * FROM workflow_step;   -- 대본 받고 납품까지의 순서
SELECT * FROM benchmark;       -- 렌더에 걸리는 시간 (실측)
SELECT * FROM external_tool;   -- 외부 도구 도입/보류 근거
SELECT * FROM prproj_fact;     -- .prproj 를 프리미어 없이 읽는 법
```

## 기억할 것

- **컨테이너는 세션이 끝나면 사라진다.** 남길 것은 반드시 커밋한다. 원본 자료는 `drive_map` 을 보고 다시 받는다.
- **대본 타임코드는 29.97 드롭프레임**이다. 59.94fps(=29.97×2)로 렌더해서 프레임 수가 정확히 두 배가 되게 한다.
- **자막·타이틀·로고는 렌더에 넣지 않는다.** 프리미어 프리셋에 이미 있어 겹친다. 차트 위 라벨만 넣는다.
- **브랜드 값은 기본 프리셋이 기준**이다. 최종본 영상마다 변형이 있는데, 그걸 표준으로 착각한 적이 있다.
- 렌더 전에 `--stills` 로 구도를 먼저 본다. 겹침은 거기서 잡는다.
- 새 대본은 `scenes/cmg-20ma-runner.scenes.js` 를 본떠 만든다.
- **`.prproj` 는 gzip 압축된 XML 이다.** 프리미어 없이 `gunzip -c` 로 열어서 시퀀스·이펙트·키프레임·
  애셋 경로를 전부 읽을 수 있다. 레퍼런스 확인은 영상 프레임을 찍지 말고 이걸로 한다.
- **렌더는 컷별로 쪼개 동시에 돌린다.** 결과물이 순차 렌더와 md5 까지 같다. 4코어에서 93초 → 45초.
- 프리미어 MCP 는 어시스턴트·서버·커넥터·프리미어가 같은 PC 에 있어야 해서 이 컨테이너에선 못 쓴다.

## 작업 브랜치

`claude/futures-youtube-video-edit-fhio4s`
