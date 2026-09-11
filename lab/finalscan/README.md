# 최종본 #1~#10 기계 실측 원자료 (2026-09-03, 차12 r13 재작 근거)

결론 문서는 `brand/FX-WHITELIST.md` 다. 여기는 그 표를 만든 **원자료**로, 다른 회차·다른
질문(예: "이 회차에서 딤 처리는 몇 초 썼나")을 다시 재 볼 때 쓴다. 로컬 세션은 mp4 를
드라이브에서 다시 받지 않아도 이 폴더만으로 대부분 답이 나온다.

원본 mp4 10편은 드라이브 `02_차트명가(최종본)` 에 있고 저장소에 없다 (`drive_map` 참고).
차명#11 은 팀원(이정찬) 자작이라 표본에서 뺐다.

## 폴더

| 경로 | 내용 |
|---|---|
| `chN/sheet_K.png` | 콘택트시트 — 2초 간격(fps=0.5) 프레임을 5×6 타일로. 영상 전체를 훑을 때 이것부터 |
| `chN/ydif.csv` | 프레임별 차트영역 휘도 변화 (`t,YDIF`, 30fps 전 프레임). 0 에 가까우면 정지 |
| `chN/scene.csv` | 프레임별 장면 전환 점수 (`t,scene_score`). 0.35 이상 = 하드컷, 0.015~0.30 연속 = 디졸브 |
| `chN/freeze.txt` | ffmpeg freezedetect 원문 — 차트영역 1.5초 이상 정지 구간 (ch2·ch10 만) |
| `chN/analysis.json` | `analyze.py` 결과: 컷 시각·디졸브 구간·세그먼트 경계 (ch2·ch10 만) |
| `chN/frame_fT.png` | 원본 해상도 단일 프레임 (T = 초). 픽셀 실측(색·두께·위치)에 쓴 것 |
| `copymap_candidates/` | 카피맵 후보 스틸 23장 (`chN_tT.jpg`). 채택된 16장은 `deliver/cutscene/차12_…/카피맵_참고스틸/` |
| `prproj_map.json` | 드라이브 회차 폴더별 `.prproj` 파일 ID·경로 목록 (11편 파싱 원천). 파싱 결과는 `log/data/prproj_kf_survey.json` |
| `analyze.py` | scene/freeze 텍스트 → 컷·디졸브·정지 통계 |

## 측정 명령 (재현)

차트영역 = 화면 중앙 800×500 (1920×1080 기준 x900 y250). 최종본이 1280×720 이면 비율로 환산한다.

```bash
# 콘택트시트 (2초 간격, 5x6 타일)
ffmpeg -i chN.mp4 -vf "fps=0.5,scale=384:-1,tile=5x6" chN_sheet_%d.png
# 차트영역 프레임간 휘도 변화 (정지 판정)
ffmpeg -i chN.mp4 -vf "crop=800:500:900:250,signalstats,metadata=print:key=lavfi.signalstats.YDIF:file=chN_ydif.txt" -f null -
# 장면 전환 점수 (하드컷·디졸브)
ffmpeg -i chN.mp4 -vf "select='gte(scene,0)',metadata=print:key=lavfi.scene_score:file=chN_scene.txt" -f null -
# 차트영역 정지 구간
ffmpeg -i chN.mp4 -vf "crop=800:560:1050:260,freezedetect=n=0.0005:d=1.5,metadata=print:file=chN_freeze.txt" -f null -
python3 analyze.py chN
```

`ydif.csv`·`scene.csv` 는 위 metadata 텍스트에서 `t,값` 만 남긴 것이다 (원문 1MB → 200KB).

## 읽는 법 한 줄

- 정지 비율 = `ydif < 0.1` 인 프레임 비율. 차트 구간은 중앙값 0.001 — 완전 정지가 정상이다.
- 등장 모션 길이 = ydif 가 0 을 벗어난 **연속 런 길이**. 1~2f 즉시, 3~5f 팝/펴기, 6~9f 상승, 10~18f 슬라이드·드로우온, 25~34f 디졸브.
- 프레임 시각 ↔ 대본은 `.srt` 큐로 잇는다. 차12 카피맵이 그 형식이다.
