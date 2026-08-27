# 포토샵으로 썸네일 만들기 (로컬 윈도우 전용)

**썸네일은 이 경로가 최신이다.** 포토샵이 있는 PC 에서 템플릿 `.psd` 를 직접 편집한다.

컨테이너(리눅스)에는 포토샵이 없어 `tools/psdedit.py` · `tools/thumbnail_png.py` 로
`.psd` 를 **써서** 만들었고, 그 방식은 포토샵이 파일을 거부하는 문제를 계속 냈다.
포토샵이 있으면 그럴 이유가 없다 — 포토샵더러 직접 편집하게 하면
라이브 텍스트 · 레이어 효과 · 그룹 구성이 전부 네이티브로 남는다.

리눅스에서만 돌려야 할 때는 예전 도구를 그대로 쓰면 된다. 지우지 않았다.

---

## 필요한 것

| | |
|---|---|
| Photoshop | 2026 (27.9.1 로 확인). COM ProgID `Photoshop.Application` |
| Node.js | 차트를 렌더러로 뽑는다. `winget install OpenJS.NodeJS.LTS` |
| Chromium | `npx playwright install chromium` — `npm install` 만으로는 안 받아진다 |
| 템플릿 `.psd` | `차트명가(롱)_하이라이트 - 복사본.psd` (180MB). **저장소에 없다** — 회사 드라이브에 있다 |

폰트(Gmarket Sans · S-Core Dream 1~9)는 `brand/fonts/` 에 있고 PC 에 설치돼 있어야 한다.

---

## 순서

**1. 차트를 뽑는다**

```
node src/cli.mjs --config scenes/thumb-ch11-A.scenes.js --all --stills 1
```

`out/stills/A_t0.00s.png` 가 나온다. 이걸 `config.json` 의 `chartDir` 로 복사하고
이름을 `variants[].chart` 와 맞춘다.

**2. `config.json` 을 채운다**

`template` · `chartDir` · `outDir` 경로와, 회차 이름 · 타이틀 두 줄.
경로는 슬래시(`/`)로 쓴다. 역슬래시는 JSX 문자열에서 이스케이프로 먹힌다.

**3. 만든다**

```
.\tools\photoshop\run.ps1 build_thumb
```

`outDir` 에 안별로 `.psd` · `.png` · `.jpg` 가 나온다. 회차 하나만 남기므로 `.psd` 는 11MB 안팎이다.

---

## 다른 스크립트

**`dump_episodes`** — 완성된 회차를 한 장씩 뽑고(960x540) 레이어 트리를 받아 적는다.
새 회차를 만들기 전에 이걸 돌려서 **열 회차를 다 보고** 규칙을 잡는다.
한 회차만 보고 따라 하면 그 회차를 베낀 것이 된다.

**`dump_layer_fx`** — 레이어 효과를 값으로 읽는다. DOM 에는 길이 없어서
`executeActionGet` 으로 `layerEffects` 를 직접 뜯는다.
`#6` · `#7` 의 매수 버튼이 **외부 광선 하나만** 켜져 있다는 것을 이걸로 확인했다.

---

## 규칙 (`thumbnail_rule` 참고)

전체는 `log/worklog.db` 의 `thumbnail_rule` 테이블에 있다. 자주 틀리는 것만:

- **타이틀 크기를 자동으로 맞추지 마라.** 이 채널은 *글자 높이가 고정이고 폭이 자유*다.
  윗줄 141px / 아랫줄 194px 이 `#2`~`#6` 에서 완전히 일치한다.
  폭에 맞춰 크기를 역산하면 회차마다 글자가 들쭉날쭉해진다.
  `build_thumb.jsx` 는 글자만 바꾸고 크기·좌표는 건드리지 않는다.
- **복제 직후 흑백 조정 레이어를 꺼라.** `Black & White 823` 이 83.9% 로 켜져 있어서,
  안 끄면 우리 차트 색이 전부 죽는다 (`#00FF24` 가 `#75947A` 로).
- **레이어 잠금을 먼저 풀어라.** 템플릿에 `lspf` 가 걸려 있어 삭제가 오류 8800 으로 막힌다.
- **인물은 주인공 트레이더가 있는 회차만.** 없으면 차트가 화면 전체를 쓴다.
- **버튼 글씨는 에스코어 드림 5 Medium.** 타이틀(Gmarket Sans Bold)과 다른 폰트다.

---

## 알아 둘 것

- 스크립트는 템플릿을 열어 두고 끝난다. 다음 실행이 빨라진다.
  끝나면 히스토리를 처음 상태로 되돌리므로 **템플릿 파일은 바뀌지 않는다.**
  그래도 안전하게 사본(`config.json` 의 `template`)으로 작업하는 것을 권한다.
- `outDir` 이 저장소 안이면 `.gitignore` 의 `out/` 에 걸린다. 결과물은 저장소에 안 들어간다.
- 채택된 결과물은 `deliver/thumbnail/` 에 따로 넣어 둔다.
