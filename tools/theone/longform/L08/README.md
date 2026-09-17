# L08 더블볼린저밴드 — 롱폼 첫 편의 판단 자료 (2026-09-11)

납품물은 `더원트레이더/0910/L08_더블볼린저밴드매매법_260923/` 에 있다. 여기 있는 것은
**다시 만들려면 필요한데 기계가 다시 못 만드는 것** — 사람이 확인·수정한 값들이다.

| 파일 | 무엇 |
|---|---|
| `script.txt` | 촬영 대본 .docx → `docx_script.py` 산출물 (105줄, L92 는 다시 읽은 자리에서 쪼갬) |
| `cam/` | 캠 녹화 — 정렬·전사·무음, `verified.json`(문구 확인), `text_fix.json` 4곳, `cut_fix.json` 4곳(IN 손질) |
| `pd/` | PD 설명 녹화 — 정렬·전사·무음, `align_fix.json`(74줄 끝에 붙은 PD 목소리 잘라냄) |
| `pdnar/` | PD 나레이션만 — 캠에서 찾은 줄을 비운 정렬(`--exclude`), `text_fix.json` 9곳, 컷 22개 |
| `full/` | 합본 — `assembled.json`(컷리스트) · `assembled.srt` · `assemble_report.json`(덩어리별 시연 고른 내역) |
| `pd_motion5fps.json` | PD 영상 5fps 움직임 (포인터 찾기용). 다시 재면 28분짜리에 몇 분 걸린다 — 그래서 남긴다 |

**경로 주의** — `cam/cuts.json`·`pdnar/cuts.json`·`full/assembled.json` 의 `source` 는 컷을 딴 그 PC 의
자리다. 다른 PC 에서 시퀀스를 다시 만들 때는 `make_xml.py … --source-root <원본이 든 폴더>` 를 준다
(json 은 손대지 않는다). 컷 값은 원본 파일 기준이라 그대로 맞는다.

**없는 것** — 원본 .mp4, 16k .wav, 대조용 PNG. 용량 때문이고 원본은 촬영 폴더에 있다.
`pdnar/cam_transcript.json` 도 없다 — `pd/cam_transcript.json` 과 같은 파일이니 복사해 쓰면 된다.

## 다시 만들기

```bash
# 0) 원본 두 개를 촬영 폴더에서 가져와 전사 (STT medium)
python tools/cutedit/transcribe.py <폴더> <영상.mp4>
# 1) 정렬 — PD 쪽은 캠에서 찾은 줄을 비운다
python tools/cutedit/align_take.py cam script.txt
python tools/cutedit/align_take.py pd  script.txt --exclude cam/aligned.json
# 2) 컷·자막 (각 폴더)         3) 검사          4) 합본            5) 시퀀스
python tools/cutedit/cut_and_srt.py <폴더> --long --source <영상.mp4> --name <이름>
python tools/cutedit/srt_rules.py check --long <자막.srt>
python tools/cutedit/assemble_longform.py cam pdnar script.txt --pd-src <PD.mp4> \
       --motion pd_motion5fps.json --name <이름> --out full
python tools/cutedit/make_xml.py full/assembled.json <전체.xml>
```

규칙과 근거는 `tools/theone/README.md` 「L08 에서 확인한 것」.
