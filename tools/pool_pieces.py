# -*- coding: utf-8 -*-
"""뼈대의 **조각 출처를 Pool 원문에 대고 검사한다.**

    python tools/pool_pieces.py log/차13_..._뼈대.md            # 검사만
    python tools/pool_pieces.py log/차13_..._뼈대.md --채우기    # 원문 글자수를 재서 표에 써 넣는다

## 왜 필요한가

차13부터 대본은 **Pool 조각을 레고처럼 조립해서** 만든다(이정찬 2026-09-21).
그러면 뼈대에 적힌 "어느 원고 몇 절에서 가져왔다"가 맞는지를 **사람이 눈으로 확인할 수 없다.**
173편 466,763자를 일일이 뒤질 수 없기 때문이다. 그래서 기계가 대조한다.

**눈대중 금지 — 규칙은 정답 자료에 대고 채점해서 고른다**(이정찬). 이 도구가 그 채점기다.

## 뼈대에 적는 꼴

구간마다 이 표를 둔다. `출처` 칸에 **앵커(원문에 실제로 있는 토막)** 를 따옴표로 붙인다.

    | 순서 | 조각 | 출처 | 원문→쓸 | 앞 조각과 잇는 말 |
    |---|---|---|---|---|
    | 2 | SMA 는 추세 중에도 이탈이 잦다 | 트팩_260820 §3 "수시로 이탈" | ?→80자 | "먼저" |

- `트팩_260820` — Pool 파일 이름에 들어 있는 토막이면 된다(`*260820*` 으로 찾는다).
- `§3` — 원고 안 절 번호. 참고용이라 검사하지 않는다.
- `"수시로 이탈"` — **이게 핵심이다.** Pool 원문에 그대로 있어야 한다. 없으면 실격.
- `?→80자` — `?` 자리에 원문 문장의 글자수가 들어간다. `--채우기` 가 재서 넣는다.

출처가 `—` 이거나 앵커가 없는 줄은 **빈칸**으로 세어 따로 알린다. 빈칸은 잘못이 아니라
"아직 못 채운 자리"다 — 전문가·팀장 확인이 필요한 자리를 감추지 않기 위해 일부러 남긴다.

## 실격 판정

- 앵커가 그 파일에 없다 → **지어낸 출처다.** exit 1.
- 앵커가 Pool 어디에도 없다 → 더 무겁다. 같이 알린다.
- 파일 토막이 여러 편에 걸린다 → 어느 편인지 못 정하므로 실격.
"""
import argparse
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# tools → E_Script → 01_저장소 → 스크립트_컷편집_통합. **세 번 올라가야 한다.**
# 두 번만 올라가서 Pool 을 0편으로 보고 조각 54개가 전부 "틀림" 으로 나왔다(2026-09-21).
통합 = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(통합, "05_대본자료", "도구"))
try:
    from paths import POOL
except ImportError:
    POOL = os.path.join(통합, "05_대본자료", "Pool")
if not os.path.isdir(POOL):
    raise SystemExit("Pool 이 없다: %s" % POOL)

행 = re.compile(r"^\s*\|\s*(\d+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|")
출처꼴 = re.compile(r'([^\s§"]+)\s*(§\S+)?\s*"([^"]+)"')
끝맺음 = re.compile(r"(?<=[.!?다요])\s+")


def 원고찾기(토막):
    후보 = [p for p in glob.glob(os.path.join(POOL, "*.txt"))
            if 토막 in os.path.basename(p)]
    return 후보


def 문장(글, 앵커):
    """앵커가 든 문장 하나를 돌려준다. 줄 → 문장 순으로 좁힌다."""
    for line in 글.split("\n"):
        if 앵커 in line:
            for s in 끝맺음.split(line):
                if 앵커 in s:
                    return s.strip()
            return line.strip()
    return None


def 온Pool에서(앵커):
    n = 0
    for p in glob.glob(os.path.join(POOL, "*.txt")):
        if 앵커 in io.open(p, encoding="utf-8").read():
            n += 1
    return n


def 검사(md경로, 채우기=False):
    줄들 = io.open(md경로, encoding="utf-8").read().split("\n")
    구간 = "(머리)"
    맞음, 빈칸, 틀림, 레퍼 = 0, [], [], []
    잰것 = 0
    몫 = {}   # 구간 → [Pool 원문 합계, 쓸 합계]

    # 뼈대에는 조각 표 말고 다른 표도 있다(구간 배분·비워 둔 것). 머리글을 보고 **조각 표만** 읽는다.
    # 안 그러면 `| 1 | 785자 |` 같은 배분표 줄이 출처 없는 조각으로 잡혀 빈칸이 부풀어 오른다.
    조각표 = False

    for i, line in enumerate(줄들):
        if line.startswith("### "):
            구간, 조각표 = line[4:].strip(), False
            continue
        if line.startswith("|") and "순서" in line and "조각" in line and "출처" in line:
            조각표 = True
            continue
        if not line.strip():
            조각표 = False
            continue
        m = 행.match(line) if 조각표 else None
        if not m:
            continue
        순서, 조각, 출처, 분량 = (x.strip() for x in m.groups())
        자리 = "%s · %s" % (구간.split("[")[0].strip(), 조각[:34])

        mm = 출처꼴.search(출처)
        if not mm:
            # `레퍼런스 …` 는 **Pool 밖이지만 근거가 있는 자리**다 — 영상 자막에서 온 설정값 따위.
            # 아직 못 채운 빈칸과 한 칸에 몰아 세면 "무엇이 진짜 비었는지"가 가려진다.
            (레퍼 if 출처.startswith("레퍼런스") else 빈칸).append(자리)
            continue
        토막, _, 앵커 = mm.groups()

        후보 = 원고찾기(토막)
        if len(후보) != 1:
            틀림.append((자리, "원고 토막 '%s' 이 %d편에 걸린다" % (토막, len(후보))))
            continue

        글 = io.open(후보[0], encoding="utf-8").read()
        if 앵커 not in 글:
            어디든 = 온Pool에서(앵커)
            틀림.append((자리, '앵커 "%s" 가 그 원고에 없다 (Pool 전체 %d편에서 발견)'
                         % (앵커, 어디든)))
            continue

        맞음 += 1
        원문 = 문장(글, 앵커)
        mq = re.match(r"(\d+)\s*→\s*(\d+)\s*자", 분량.replace(" ", ""))
        if mq:
            몫.setdefault(구간.split("[")[0].strip(), [0, 0])
            몫[구간.split("[")[0].strip()][0] += int(mq.group(1))
            몫[구간.split("[")[0].strip()][1] += int(mq.group(2))
        if 채우기 and 원문 and "?" in 분량:
            새 = 분량.replace("?", str(len(원문)), 1)
            줄들[i] = line.replace("|" + m.group(4), "| %s " % 새, 1)
            잰것 += 1

    if 채우기 and 잰것:
        io.open(md경로, "w", encoding="utf-8", newline="").write("\n".join(줄들))

    print("조각 %d개 — Pool 출처 맞음 **%d** · 레퍼런스 **%d** · 빈칸 **%d** · 틀림 **%d**"
          % (맞음 + len(레퍼) + len(빈칸) + len(틀림), 맞음, len(레퍼), len(빈칸), len(틀림)))
    if 채우기:
        print("  원문 글자수를 잰 칸 %d개" % 잰것)
    if 몫:
        # `원문` 은 **앵커가 든 문장 하나**의 길이다. 조각은 보통 원고에서 두세 문장에 걸쳐 있으므로
        # 이 값은 밑바닥이지 조각의 전부가 아니다. `쓸` 이 더 크면 그 차이가 **풀어 쓸 몫** 이다.
        # 팀장 지시가 "2~3줄만이라도 더 설명" 이었으니 몫이 있는 것 자체는 방향에 맞다.
        # 다만 그 몫은 **Pool 어휘 안에서** 채워야 한다 — 초안 단계에서 `inpool.py` 가 잡는다.
        print("\n구간별 분량 (원문=앵커 문장 기준)")
        원계, 쓸계 = 0, 0
        for 구간, (원, 쓸) in 몫.items():
            원계 += 원; 쓸계 += 쓸
            print("  %-34s Pool 원문 %4d자 → 쓸 %4d자 · 풀어 쓸 몫 %+4d자" % (구간, 원, 쓸, 쓸 - 원))
        print("  %-34s Pool 원문 %4d자 → 쓸 %4d자 · 풀어 쓸 몫 %+4d자" % ("합계", 원계, 쓸계, 쓸계 - 원계))
    for 자리 in 레퍼:
        print("  [레퍼런스] %s" % 자리)
    for 자리 in 빈칸:
        print("  [빈칸] %s" % 자리)
    for 자리, 왜 in 틀림:
        print("  [틀림] %s — %s" % (자리, 왜))
    return 0 if not 틀림 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="뼈대의 조각 출처를 Pool 원문에 대고 검사한다")
    ap.add_argument("md")
    ap.add_argument("--채우기", action="store_true", help="원문 글자수를 재서 ? 자리에 써 넣는다")
    a = ap.parse_args()
    raise SystemExit(검사(a.md, a.채우기))
