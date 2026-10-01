# -*- coding: utf-8 -*-
"""캠(얼굴&대본) 녹화에서 **구간별 테이크**를 찾는다.

촬영 버릇 (이정찬 2026-10-01)
    "~ (대제목 이름) 시작하겠습니다" + **박수** → 그 대제목 부분을 읽는다 → **박수**
  그래서 테이크 = 시작 멘트 뒤 박수 ~ 읽기가 끝난 뒤 박수.

받는 것
  대본.json      (pdf_script.py)  구간·제목·문장
  받아쓰기.json  (obs_stt.py)     파일별 말 구간
  소리.json      (obs_scan.py)    무음·박수 자리

고르는 법
  1. 받아쓴 말에서 '시작하겠습니다/시작할게요/들어가겠습니다' 가 있는 자리를 테이크 머리로 본다.
  2. 그 앞뒤 60초 안의 박수 중 **머리 뒤 첫 박수**를 진짜 시작으로 잡는다 (멘트·박수 자체는 뺀다).
  3. 테이크 몸통(다음 머리 전까지)의 말을 대본 여섯 구간과 대조해 **가장 닮은 구간**을 붙인다.
  4. 같은 구간이 여러 번 찍혔으면 **마지막 것**이 최종본이다 (틀리면 다시 읽는 습관).

내놓는 것 (json)  [{"파일":…, "구간":"2", "시작":초, "끝":초, "닮음":0.52, "글":"…"}, …]
"""
import io, re, sys, json, difflib

머리말 = re.compile(r"(시작하겠습니다|시작할게요|시작합니다|들어가겠습니다|가보겠습니다|찍겠습니다)")
한글 = re.compile(r"[^가-힣]")


def 정리(t): return 한글.sub("", t)


def 닮음(a, b):
    return difflib.SequenceMatcher(None, 정리(a)[:1200], 정리(b)[:1200]).ratio()


번호말 = {"INTRO": ["인트로", "intro", "오프닝"], "OUTRO": ["아웃트로", "outro", "엔딩", "마무리"],
          "1": ["1번", "일번", "첫번째", "첫 번째"], "2": ["2번", "이번째", "두번째", "두 번째"],
          "3": ["3번", "삼번", "세번째", "세 번째"], "4": ["4번", "사번", "네번째", "네 번째"]}


def 멘트구간(멘트, 대본):
    """시작 멘트에 구간 이름이 들어 있다 — '3번 핵심은 방향이 먼저 시작하겠습니다'."""
    납작 = 멘트.replace(" ", "").lower()
    for 키, 말들 in 번호말.items():
        if any(w.replace(" ", "").lower() in 납작 for w in 말들): return 키, 0.99
    for g in 대본:                                   # 번호 없이 제목만 말한 경우
        제 = 정리(g["제목"])
        if len(제) >= 4 and 제[:6] in 정리(멘트): return g["구간"], 0.9
    return None, 0.0


def 테이크(대본, 받아쓰기, 소리):
    소리맵 = {r["파일"]: r for r in 소리}
    구간글 = {g["구간"]: " ".join(g["문장"]) for g in 대본}
    결과 = []
    for r in 받아쓰기:
        구간들 = r["구간"]
        박수 = 소리맵.get(r["파일"], {}).get("박수", [])
        길이 = 소리맵.get(r["파일"], {}).get("길이", 구간들[-1]["e"] if 구간들 else 0)
        머리 = [i for i, s in enumerate(구간들) if 머리말.search(s["글"])]
        for k, i in enumerate(머리):
            멘트끝 = 구간들[i]["e"]
            뒤박수 = [t for t in 박수 if 멘트끝 - 1 <= t <= 멘트끝 + 25]
            시작 = (뒤박수[0] + 0.4) if 뒤박수 else 멘트끝
            다음머리 = 구간들[머리[k + 1]]["s"] if k + 1 < len(머리) else 길이
            몸통 = [s for s in 구간들 if 시작 <= s["s"] < 다음머리]
            if not 몸통: continue
            말끝 = 몸통[-1]["e"]
            끝박수 = [t for t in 박수 if 말끝 - 2 <= t <= 말끝 + 20]
            끝 = (끝박수[0] - 0.3) if 끝박수 else min(말끝 + 1.0, 다음머리)
            글 = " ".join(s["글"] for s in 몸통)
            구간, 확신 = 멘트구간(구간들[i]["글"], 대본)      # 멘트에 구간 이름이 있으면 그걸 믿는다
            점수 = {키: 닮음(글, 값) for 키, 값 in 구간글.items()}
            if 구간 is None:
                구간, 확신 = max(점수, key=점수.get), 0.0
            결과.append({"파일": r["파일"], "구간": 구간, "닮음": round(점수[구간], 3),
                         "멘트로 정함": 확신 > 0,
                         "시작": round(시작, 2), "끝": round(끝, 2), "길이": round(끝 - 시작, 1),
                         "멘트": 구간들[i]["글"][:40], "글": 글[:160]})
    return 결과


def 마지막만(테이크들):
    """같은 구간이 여럿이면 마지막(파일 순서 → 시각 순서) 것을 쓴다."""
    차례 = {이름: i for i, 이름 in enumerate(sorted({x["파일"] for x in 테이크들}))}
    고름 = {}
    for t in sorted(테이크들, key=lambda t: (차례[t["파일"]], t["시작"])):
        고름[t["구간"]] = t
    차례대로 = ["INTRO", "1", "2", "3", "4", "OUTRO"]
    return [고름[k] for k in 차례대로 if k in 고름]


if __name__ == "__main__":
    대본 = json.load(io.open(sys.argv[1], encoding="utf-8"))
    받아쓰기 = json.load(io.open(sys.argv[2], encoding="utf-8"))
    소리 = json.load(io.open(sys.argv[3], encoding="utf-8"))
    모두 = 테이크(대본, 받아쓰기, 소리)
    고름 = 마지막만(모두)
    json.dump({"모두": 모두, "고름": 고름}, io.open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("테이크 %d개 (구간 %d개 채움)\n" % (len(모두), len(고름)))
    for t in 모두:
        표 = "←쓴다" if t in 고름 else ""
        print("%-14s %5.0f~%5.0f초 (%5.1f초) 구간 %-5s 닮음 %.2f %s" %
              (t["파일"], t["시작"], t["끝"], t["길이"], t["구간"], t["닮음"], 표))
        print("      멘트: %s" % t["멘트"])
    print("\n냈다:", sys.argv[4])
