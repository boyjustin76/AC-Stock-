"""다른 컴퓨터에 옮길 꾸러미를 만든다 (MT5 포터블용).

    python tools/mt5/pack_portable.py [--out <폴더>]

MT5 는 `terminal64.exe /portable` 로 띄우면 **설치 폴더 안**에 모든 자료를 둔다.
그래서 옮길 것은 우리 파일 몇 개뿐이다 — 아래 구조 그대로 풀면 된다.

    MQL5/Experts/Replay_Tool_CMG.ex5     리플레이 도구 (소스도 같이 넣는다)
    MQL5/Scripts/CMG_ReplayStep.ex5      장면 이동·감기 (자동화용)
    MQL5/Scripts/CMG_SetReplay.ex5       시작 시각 넣기
    MQL5/Profiles/Templates/CMG_촬영.tpl 촬영용 차트 모양
    MQL5/Files/cmg_cues.csv              촬영 큐시트 (있으면)
    설치방법.md

컴파일된 .ex5 는 어느 PC 에서나 그대로 돈다(빌드가 같은 계열이면). 안 되면 MetaEditor 로 다시 컴파일한다 —
그래서 .mq5 소스도 함께 넣는다.
"""
import argparse
import io
import os
import shutil
import zipfile

TERMINAL_ID = os.environ.get('MT5_TERMINAL_ID', '061BAFBAE5645A1204F350EE84A4B55F')
MQL5 = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'MetaQuotes',
                    'Terminal', TERMINAL_ID, 'MQL5')
HERE = os.path.dirname(os.path.abspath(__file__))

ITEMS = [
    ('MQL5/Experts/Replay_Tool_CMG.ex5',          os.path.join(MQL5, 'Experts', 'Replay_Tool_CMG.ex5')),
    ('MQL5/Experts/Replay_Tool_CMG.mq5',          os.path.join(HERE, 'Replay_Tool_CMG.mq5')),
    ('MQL5/Scripts/CMG_ReplayStep.ex5',           os.path.join(MQL5, 'Scripts', 'CMG_ReplayStep.ex5')),
    ('MQL5/Scripts/CMG_ReplayStep.mq5',           os.path.join(HERE, 'CMG_ReplayStep.mq5')),
    ('MQL5/Scripts/CMG_SetReplay.ex5',            os.path.join(MQL5, 'Scripts', 'CMG_SetReplay.ex5')),
    ('MQL5/Scripts/CMG_SetReplay.mq5',            os.path.join(HERE, 'CMG_SetReplay.mq5')),
    ('MQL5/Profiles/Templates/CMG_촬영.tpl',      os.path.join(MQL5, 'Profiles', 'Templates', 'CMG_촬영.tpl')),
    ('MQL5/Files/cmg_cues.csv',                   os.path.join(MQL5, 'Files', 'cmg_cues.csv')),
    ('사용법_전문가용.md',                         os.path.join(HERE, '사용법_전문가용.md')),
]

HOWTO = """# 다른 컴퓨터에 설치하기 (MT5 포터블)

이 꾸러미는 **우리가 만든 파일만** 들어 있습니다. MT5 자체는 그 컴퓨터에 있어야 합니다.

## 1) MT5 를 포터블로 띄운다

두 가지 중 하나입니다.

**가. 그 컴퓨터에 MT5 를 새로 깐다 (권장)**
1. 쓰는 증권사(HedgeHood) 홈페이지에서 MT5 설치 파일을 받아 깝니다.
   설치 위치를 `D:\\MT5_촬영` 처럼 **짧고 쉬운 곳**으로 정합니다.
2. 바탕화면에 바로가기를 만들고, 바로가기 > 속성 > **대상** 맨 뒤에 한 칸 띄우고 `/portable` 을 붙입니다.
   `"D:\\MT5_촬영\\terminal64.exe" /portable`
3. 그 바로가기로 실행합니다. 이제 설정·자료가 전부 `D:\\MT5_촬영` 안에 들어갑니다.

**나. 지금 쓰는 MT5 폴더를 통째로 복사한다**
1. `C:\\Program Files\\HedgeHood MT5 Terminal` 폴더를 USB 로 복사해 새 컴퓨터에 붙입니다.
2. 위와 같이 바로가기에 `/portable` 을 붙여 실행합니다.
   (계정·차트까지 그대로 따라오지만, 시세 자료는 다시 받아야 합니다.)

## 2) 이 꾸러미를 푼다

압축을 풀면 `MQL5` 폴더가 나옵니다. 그것을 **MT5 설치 폴더 안에** 덮어씁니다.

    D:\\MT5_촬영\\MQL5\\Experts\\Replay_Tool_CMG.ex5
    D:\\MT5_촬영\\MQL5\\Scripts\\CMG_ReplayStep.ex5
    D:\\MT5_촬영\\MQL5\\Profiles\\Templates\\CMG_촬영.tpl
    D:\\MT5_촬영\\MQL5\\Files\\cmg_cues.csv

> 포터블이 아니면 자리가 다릅니다: `파일 > 데이터 폴더 열기` 로 열리는 폴더 안의 `MQL5` 입니다.

## 3) MT5 를 켜고 준비한다

1. 증권사 계정으로 로그인합니다.
2. 내비게이터(Ctrl+N) 에서 **오른쪽 클릭 > 새로 고침** 을 한 번 합니다. (새 파일을 알아채게 하는 것)
3. 쓸 종목 차트를 엽니다. 예: `US100.` 1분봉.
   **차트를 한동안 열어 두어 과거 자료를 내려받게 합니다** (리플레이는 이 자료로 만듭니다).
   빨리 받으려면 차트에서 Home 키를 몇 번 눌러 과거로 끕니다.
4. 그 차트에 **Replay_Tool_CMG** 를 끌어다 놓습니다 → `<종목>_REPLAY` 라는 리플레이 종목이 생깁니다.
5. **새로 생긴 `<종목>_REPLAY` 차트를 열고**, 거기에 다시 **Replay_Tool_CMG** 를 끌어다 놓습니다.
   이번에는 조작판이 뜹니다. (1단계는 종목 만들기, 2단계가 실제 사용입니다.)
6. 그 차트에서 오른쪽 클릭 > 템플릿 > **CMG_촬영** 을 씌웁니다. 그리고 4-5번처럼 EA 를 다시 붙입니다.
   (템플릿을 씌우면 EA 가 떨어질 수 있습니다.)

## 4) 촬영 설정값

EA 를 붙일 때 입력값을 이렇게 둡니다.

| 입력 | 값 | 뜻 |
|---|---|---|
| `InpShiftPercent` | 50 | 오른쪽을 절반 비운다 |
| `InpChartScale` | 4 | 봉 굵기 (0~5) |
| `InpHidePanel` | true | 조작판을 숨긴다 (H 로 다시 보임) |
| `InpForceDarkTheme` | false | 템플릿 색을 그대로 쓴다 |
| `InpCueFile` | cmg_cues.csv | 촬영 큐시트 |
| `InpMaskFuture` | true | 미래를 가리는 방식 — 화면이 안 움직인다 (끄면 옛 방식) |

## 5) 쓰는 법

`사용법_전문가용.md` 를 보세요. 요약하면 **X 앞으로 · Z 뒤로 · S/A 열 봉 · 스페이스 재생 ·
N 다음 장면 · B 이전 장면 · H 조작판**.

## 알아 둘 것

- **되감아도 화면은 그대로입니다.** 미래를 지우는 대신 **배경색으로 덮기** 때문입니다(`InpMaskFuture=true`).
  가리개가 화면 끝에 닿을 때만 한 번 가운데로 잡습니다. 옛 방식(`false`)은 절반에서 화면이 따라옵니다.
- 리플레이 자료는 **그 컴퓨터가 받아 둔 과거 시세**로 만듭니다. 새 컴퓨터에서는 처음에 시간이 좀 걸립니다.
- 1분봉은 증권사가 최근 것만 줍니다(여기선 약 10만 봉 = 70 거래일). 그보다 옛날 장면은
  도구가 알아서 차트 주기 자료로 바꿔 받습니다.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(os.path.expanduser('~'), 'Desktop'))
    a = ap.parse_args()

    stage = os.path.join(a.out, 'CMG_리플레이_포터블')
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)

    missing = []
    for rel, src in ITEMS:
        dst = os.path.join(stage, rel.replace('/', os.sep))
        if not os.path.exists(src):
            missing.append(rel)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print('넣음 ', rel)
    io.open(os.path.join(stage, '설치방법.md'), 'w', encoding='utf-8').write(HOWTO)
    print('넣음  설치방법.md')

    zpath = stage + '.zip'
    if os.path.exists(zpath):
        os.remove(zpath)
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(stage):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, stage))

    if missing:
        print('\n없어서 못 넣은 것:', ', '.join(missing))
    print('\n폴더 →', stage)
    print('압축 →', zpath, '(%.1f MB)' % (os.path.getsize(zpath) / 1e6))


if __name__ == '__main__':
    main()
