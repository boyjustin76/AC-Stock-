# 차트 컷씬 렌더러 — 새 세션이 먼저 읽을 것

해외선물 유튜브 채널 **차트명가** 영상에 쓸 차트 모션그래픽 소스 영상을 코드로 렌더한다.

## 범위 — 여기부터 헷갈리지 말 것

영상 한 편은 네 단계다. **이 저장소는 두 칸을 맡는다 — 롱폼 3단계, 숏폼 1단계.**

| 포맷 | 1. 대본 만들기 | 1.5 성우 녹음 | 2. 컷편집·자막 | 3. 모션그래픽·소스 |
|---|---|---|---|---|
| **롱폼** | 사람 (결과물 인덱스만 보유) | 외부 | 사람 · 프리미어 | **← 이 저장소** |
| **숏폼** | **← 이 저장소** (규칙·지시서·검사) | 외부 | 미착수 | 미착수 (화면 톤앤매너 미조사) |

- **롱폼 3단계** — 받는 것은 타임코드가 붙은 대본, 내놓는 것은 차트만 있는 영상 클립.
  프리미어에 얹는 것은 사람이 한다. 롱폼 대본을 쓰거나 컷을 자르지 않는다.
- **숏폼 1단계** — 롱폼 챕터 하나를 골라 350~560자로 **다시 쓴다**. 복붙이 아니다.
  대본을 대신 쓰는 게 아니라 규칙·작성 지시서·검사를 준다. `tools/shortform.py`
- 일정표에서 `숏폼(포)` 로 표시된 편은 기획형이라 이 규칙 밖이다. 손대지 않는다.

자세한 것은 `SELECT * FROM v_scope;`

## 여기부터

1. **`log/worklog.db`** (SQLite) 가 작업 기록의 원본이다. 읽는 형태는 `log/WORKLOG.md`,
   보는 형태는 `log/worklog.html`. 셋 다 `log/build_worklog_db.py` 에서 만들어진다.
2. `brand/STYLE.md` — 브랜드 스펙. 색·크기는 전부 레퍼런스 영상에서 실측한 값이다. 짐작으로 바꾸지 않는다.
3. `README.md` — 렌더러 사용법.

```sql
-- 컨텍스트가 날아갔을 때 순서대로
SELECT * FROM v_start_here;
SELECT * FROM v_scope;         -- 파이프라인 어디를 맡는가
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
SELECT * FROM script_doc;      -- 지난 회차 대본 15편 인덱스
SELECT * FROM episode_prproj;  -- 회차별 프리미어 파일 (레퍼런스 확인용)
SELECT * FROM motion_preset;   -- 회사 고유 모션 (프레임·이징)
SELECT * FROM shortform_rule;  -- 숏폼 대본 뽑는 규칙 17개 (근거 포함)
SELECT * FROM shortform_part;  -- 숏폼 뼈대와 목표 분량
SELECT * FROM shortform_doc;   -- 나간 숏폼 25편
SELECT * FROM shortform_map;   -- 일정표의 롱폼↔숏폼 대응 47건

-- 새 대본이 오면 겹치는 회차부터 찾는다
SELECT ep, snippet(script_fts, 2, '[', ']', '…', 12)
  FROM script_fts WHERE script_fts MATCH '눌림목 OR 20일선';
SELECT ep, hits FROM script_keyword WHERE keyword = '손익비' ORDER BY hits DESC;
```

## 세이브 / 로드

```bash
python3 log/save.py "어디까지 했는지 한 줄"   # 로그 다시 만들고 커밋·태그·푸시까지
python3 log/save.py --list                    # 되돌릴 수 있는 시점 목록
python3 log/save.py --load <슬롯|해시>        # 되돌리는 방법
git restore --source=<해시> -- .              # 실제로 되돌리기 (그 뒤 다시 save)
```

작업을 한 덩어리 끝낼 때마다 `save.py` 를 부른다. 슬롯 이름은 `save/YYYY-MM-DD-HHMM` (KST).
**태그 푸시는 이 저장소에서 403 으로 막혀 있다.** 그래서 슬롯 이름과 커밋 해시의 짝을
`log/data/checkpoints.json` 에 적어 브랜치와 함께 올린다. 새 컨테이너에서 clone 만 해도
`--list` 가 그대로 나온다.

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
- **대본은 이미 저장소 안에 있다** (`log/data/scripts.json`, 16편). 드라이브에 다시 붙지 않는다.
  새 회차가 생겼을 때만 갱신한다.
- **모션은 짐작하지 않는다.** 회차 `.prproj` 를 받아 `<Keyframes>` 를 읽으면 프레임 수와 이징이 나온다.
- **숏폼 대본은 롱폼을 복붙하지 않는다.** 10자 겹침이 중앙값 2.2%다. 챕터를 고른 뒤 다시 쓴다.
- **숏폼 규칙은 경향이지 법이 아니다.** 기존 24편 중 5개 규칙을 다 지킨 건 2편뿐이다.
  `필수` 만 지키고 `권장`·`선택` 은 어겨도 된다. 다만 어겼으면 이유를 적어 둔다.
- **`#N` 의 CTA 질문이 `#N+1` 의 주제다.** 숏폼은 사슬처럼 이어진다.

## 작업 브랜치

`claude/futures-youtube-video-edit-fhio4s`
