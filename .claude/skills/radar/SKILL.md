---
name: radar
description: 오류나 벽에 두 번째로 부딪히거나 10분 넘게 막히면, 혼자 우회법을 짜기 전에 우리 기록·Stack Overflow·GitHub Issues 에서 이미 나온 답을 찾는다.
---

# 오류 레이더

**언제**: 같은 오류가 두 번째 났을 때 · 한 문제에 10분 넘게 걸릴 때 · 도구·라이브러리·앱(어도비 COM, 프리미어, Node, PowerShell) 이 이유 없이 거부할 때.
직접 만든 우회법은 마지막 수단이다 — 남이 이미 넘은 벽이면 그 길로 간다 (이정찬 2026-09-17: "맨땅에 헤딩하지 말고 남들이 찾아낸 지름길을 갖다 쓴다").

**어떻게**

```bash
python3 tools/radar.py "<오류 문장 붙여넣기>"             # 우리 기록 → Stack Overflow → GitHub
python3 tools/radar.py --file err.txt --repo anthropics/claude-code --save
python3 tools/radar.py "<…>" --no-web                     # 오프라인: 우리 기록만
```

1. **우리 기록에 있으면 그걸 쓴다.** `issue`·`constraint_note`·`EXTENDSCRIPT-TRAPS.md`·`log/inbox` 를 먼저 본다. 있으면 웹은 볼 필요 없다.
2. 웹 답은 **우리 환경에 맞는지 한 줄로 확인**하고 적용한다 — Windows cp949, ExtendScript(ES3), COM 모달 창, 한글 경로, 저장소 public.
3. 로컬 PC 에서는 `context7`(라이브러리 최신 문서) 과 GitHub MCP `search_issues` 도 같은 서명으로 물어본다. 총괄 컨테이너는 GitHub 검색 API 가 막혀 있어 MCP 로만 된다.
4. 해결하면 **원문**(오류 로그·고친 줄·출처 링크)을 `log/inbox/YYYY-MM-DD_<세션>_<주제>.md` 에 남긴다. 문장은 총괄이 DB 에 쓴다 (decision 24).
5. `--save` 는 검색 결과 자체를 `log/inbox/radar/` 에 남긴다 — 못 풀고 넘길 때 쓴다.

**하지 않는 것**: 답을 찾았다고 바로 커밋하지 않는다(범위·회귀 확인은 평소대로). 키·토큰이 든 로그를 그대로 넣지 않는다(`[가림]`).
