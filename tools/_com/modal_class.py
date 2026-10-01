"""모달 문구를 보고 **어떻게 다룰지**를 고른다 — 아는 문구면 표대로, 모르면 '죽이고 기록'.

next_step 46 · decision 37 ③ · 총괄 2026-09-21 (`log/inbox/2026-09-21_총괄_Jev_결정_2.md`):
"아는 문구면 정해진 대로 **기록**, 아니면 죽이고 기록. **문 0.8, 두 순서 일치.**"

정하는 것은 _fail.txt 에 적히는 말뿐이다 — **모달을 닫지 않는다.** 닫는 길이 없다(B B1·B2).
그래서 이 판정이 틀려도 최악은 '사람이 읽을 한 줄이 틀린 것' 이고, 잡은 어차피 멈춰 있다.

  1) 표(`modal_known.json`) 에 조각이 걸리면 그대로. 값도 안 들고 흔들리지도 않는다.
  2) 안 걸리면 Jev 에게 묻는다 — **선택지 순서를 뒤집어 두 번**, 둘 다 같고 confidence ≥ 0.8 일 때만 인정.
     B-1 실측 5/6(정답표 기준) · 맞은 다섯의 confidence 0.83~0.99 · 유일한 오답이 0.60 (2026-09-21).
  3) 어느 쪽도 아니면 '모름'. 그래도 앱은 죽이고 기록한다 — 판정이 처리를 바꾸지 않는다.

    python modal_class.py --text "..."           # 글자를 바로 준다
    python modal_class.py --from modal.json      # modal_text.py 가 쓴 것
    python modal_class.py --from modal.json --no-jev   # 표만 (키 없어도 된다)

stdout 은 ASCII 한 줄(PowerShell 5.1 이 cp949 로 받는다 — constraint 63 과 같은 뿌리).
사람이 읽을 한글은 `--json` 파일로 나간다.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(HERE, "modal_known.json")
GATE = 0.8                       # 총괄 2026-09-21. 자동으로 움직이는 자리라 0.7 이 아니라 0.8 (constraint 65)
UNKNOWN = "모름"


def load_table(path=TABLE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def by_table(text, table):
    """조각이 하나라도 들어 있으면 그 처리. (처리, 걸린 조각) 또는 (None, None)."""
    for row in table["처리표"]:
        for frag in row["조각"]:
            if frag in text:
                return row["처리"], frag
    return None, None


def hints(text, table):
    return [r["힌트"] for r in table["힌트표"] if any(f in text for f in r["조각"])]


def options(table):
    return [r["처리"] for r in table["처리표"]] + [UNKNOWN]


def by_jev(text, opts):
    """선택지 순서를 뒤집어 두 번 묻는다. 둘 다 같고 문(0.8)을 넘어야 인정한다."""
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "jev"))
    import jev

    instr = "어도비 앱 자동화 도중 이 창이 떴다. 어떻게 다루어야 하는가?"
    got = []
    for order in (opts, list(reversed(opts))):
        ans = jev.ask({"모달 문구": text}, {"q": jev.choice(instr, order)})
        pick, conf = jev.pick(ans, "q")
        got.append({"choice": pick, "confidence": conf})
    같음 = got[0]["choice"] == got[1]["choice"]
    문통과 = all((g["confidence"] or 0) >= GATE for g in got)
    return {
        "앞순서": got[0], "뒤집음": got[1],
        "자리무관": 같음, "문통과": 문통과,
        "처리": got[0]["choice"] if (같음 and 문통과) else UNKNOWN,
    }


def classify(text, use_jev=True, table=None):
    table = table or load_table()
    res = {"문구": text, "처리": UNKNOWN, "근거": "없음", "힌트": hints(text, table)}
    if not text.strip():
        res["근거"] = "문구가 비어 있다 — 어도비가 직접 그린 창이면 자식 창이 없어 글자가 안 나온다. 그림을 보라"
        return res

    처리, frag = by_table(text, table)
    if 처리:
        res["처리"] = 처리
        res["근거"] = f"표 — 조각 '{frag}'"
        return res

    if not use_jev:
        res["근거"] = "표에 없다 (Jev 안 씀)"
        return res

    try:
        j = by_jev(text, options(table))
    except SystemExit as e:                  # 키가 없거나 HTTP 오류 — 실행기를 멈추지 않는다
        res["근거"] = f"표에 없고 Jev 도 못 물었다: {e}"
        return res
    except Exception as e:
        res["근거"] = f"표에 없고 Jev 도 못 물었다: {type(e).__name__} {e}"
        return res

    res["Jev"] = j
    res["처리"] = j["처리"]
    if j["처리"] == UNKNOWN:
        까닭 = []
        if not j["자리무관"]:
            까닭.append(f"순서를 바꾸니 답이 갈렸다({j['앞순서']['choice']} / {j['뒤집음']['choice']})")
        if not j["문통과"]:
            까닭.append(f"confidence 가 문({GATE}) 아래다"
                        f"({j['앞순서']['confidence']:.2f} · {j['뒤집음']['confidence']:.2f})")
        res["근거"] = "Jev — 안 잡혔다: " + " · ".join(까닭 or ["Jev 가 모름을 골랐다"])
    else:
        res["근거"] = (f"Jev — 두 순서 같음 · confidence "
                       f"{j['앞순서']['confidence']:.2f} · {j['뒤집음']['confidence']:.2f}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="모달 글자")
    ap.add_argument("--from", dest="src", help="modal_text.py 가 쓴 .json")
    ap.add_argument("--json", help="판정을 쓸 자리 (.json, UTF-8)")
    ap.add_argument("--no-jev", action="store_true", help="표만 본다 — 키가 없어도 된다")
    a = ap.parse_args()

    text = a.text or ""
    본것 = None
    if a.src and os.path.exists(a.src):
        with open(a.src, encoding="utf-8") as f:
            본것 = json.load(f)
        text = 본것.get("문구", "") or text
    if not a.text and not a.src:
        ap.error("--text 나 --from 중 하나는 있어야 한다")

    res = classify(text, use_jev=not a.no_jev)
    # 글자가 없을 때 왜 없는지를 갈라 적는다 — '모달이 아예 없다' 와 '창은 있는데 글자를 못 읽었다'는 다르다.
    if not text.strip() and 본것 is not None:
        res["근거"] = ("모달 창을 못 찾았다 — 멈춘 곳이 창이 아니거나 앱이 아직 안 떴다. 그림을 보라"
                       if not 본것.get("모달") else
                       "창은 찾았는데 글자가 안 나왔다 — 어도비가 직접 그린 창이면 자식 창이 없다. 그림을 보라")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

    # ASCII 한 줄 — 한글은 --json 으로 나간다
    옵 = options(load_table())
    print(f"class={옵.index(res['처리']) if res['처리'] in 옵 else -1} "
          f"source={'table' if res['근거'].startswith('표') else ('jev' if 'Jev' in res else 'none')} "
          f"hints={len(res['힌트'])} chars={len(text)}")
    return 0 if res["처리"] != UNKNOWN else 3


if __name__ == "__main__":
    sys.exit(main())
