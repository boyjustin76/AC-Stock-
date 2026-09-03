# data/nq — 실제 NQ 시세 (차12 재작 r13 부터 배경 차트의 원본)

야후 파이낸스 v8 chart API 에서 받은 실데이터다. **합성 캔들(`src/market/candles.js` seed)이 아니다.**
씬에서 `market: { bars: ... }` 로 주입한다 (`src/market/loadBars.js`).

| 파일 | 심볼 | 주기 | 범위 | 비고 |
|---|---|---|---|---|
| `NQ_1m.json` | NQ=F (CME 나스닥100 선물) | 1분 | 최근 ~5일 | **야후가 5일치만 준다 — 소멸 데이터.** `--merge` 로 누적 |
| `NQ_5m.json` | NQ=F | 5분 | 최근 1달 | |
| `NQ_1d.json` | NQ=F | 일봉 | 최근 5년 | |

갱신:

```bash
node src/tools/fetch-yahoo.mjs --symbol 'NQ=F' --interval 1m --range 5d --out data/nq/NQ_1m.json --merge
node src/tools/fetch-yahoo.mjs --symbol 'NQ=F' --interval 5m --range 1mo --out data/nq/NQ_5m.json --merge
node src/tools/fetch-yahoo.mjs --symbol 'NQ=F' --interval 1d --range 5y --out data/nq/NQ_1d.json
```

- UA 헤더 필수(스크립트가 붙인다). o/h/l/c null 봉은 드랍. 갭(세션 경계)은 남긴다 —
  차트 x 축이 인덱스 기반이라 그림은 안 깨진다. 갭 위치는 수급 시 stdout 리포트.
- 씬에 박제된 슬라이스 구간(`scenes/cmg12s-base.js`)이 이 파일들을 가리키므로,
  **--merge 누적은 안전하지만 파일 삭제·재생성은 슬라이스 인덱스를 깨뜨린다.** 지우지 말 것.
- 최초 수급 2026-09-03 (1m 4797봉 / 5m 6320봉 / 1d 1258봉).
