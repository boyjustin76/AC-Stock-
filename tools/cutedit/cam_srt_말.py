# -*- coding: utf-8 -*-
"""컷 시퀀스에 맞춘 자막(.srt) — **실제로 말한 대로** 쓴다.

`cam_srt.py` 와 짝이다. 다른 것은 **글자를 어디서 가져오는가** 하나뿐이다.
  · `cam_srt.py`   글자는 **대본**에서. 낭독이 대본과 거의 같을 때 쓴다 (마01).
  · 이것          글자는 **받아쓰기**에서. 대본과 많이 다르게 말했을 때 쓴다.

왜 따로 두나 (이정찬 2026-10-08, 마02)
  "대본과 사람 말이 많이 다를거야. 그럴땐 사람 말을 기준으로 자막 써주면 돼."
  마02 의 5장은 아예 대본 밖이고(전문가 답변을 즉석에서 풀어 말함), 3장도 프롬프터를
  그대로 읽지 않았다. 대본을 자막으로 쓰면 **화면의 입과 글자가 어긋난다.**

대본을 안 쓰는 대신 잃는 것 — 받아쓰기 오인식이 그대로 나간다. 그래서 **고침표**를 받는다
  (`--고침 고침표.json`, `{"하이킨아시": "Heiken ashi", …}`). 낱말 단위로 바꾸고, 바꾼 것은
  전부 찍어 낸다. 짐작으로 고치지 않는다 — 고칠 말은 사람이 보고 적는다.

시각은 받아쓰기 **낱말 시각**이 진본이다. 컷에 남은 낱말만 시퀀스 시각으로 옮겨 쓰므로,
덜어낸 무음·재촬영은 저절로 빠진다 (cam_srt.py 와 같은 방식).
큐를 가르는 것은 `ko_clause.조각내기` — 글자 수가 아니라 구·절이 기준이다.

    python3 tools/cutedit/cam_srt_말.py <작업폴더> <컷리스트.json> <낼.srt>
        [--고침 <고침표.json>] [--사이 0.6] [--도구 <E_Script/tools/cutedit>]
"""
import argparse
import io
import json
import os
import re
import sys

#  구·절 가르기(`ko_clause`)와 줄바꿈·시각 찍기(`cam_srt`)는 **E_Script 에 있는 것이 진본**이다.
#  옮겨 적으면 두 벌이 되어 어긋난다 — 그 폴더를 받아서 불러 쓴다.
#  자리는 PC 마다 다르니 박아 두지 않는다 — `--도구` 또는 환경변수 `CUTEDIT_TOOLS`.
도구환경 = 'CUTEDIT_TOOLS'

군더더기 = re.compile(r"[\s'\"‘’“”.,!?()\[\]/·…~\-+:;]")


def 맨글(t):
    return 군더더기.sub('', t)


def 표만들기(컷리스트, 시작맵, fps):
    """컷마다 (원본 시각 처음, 끝, 시퀀스 시각 처음). 시퀀스 자리는 **프레임으로** 센다."""
    표, 자리프 = [], 0
    for c in 컷리스트['cuts']:
        if c.get('track', 1) != 1:
            continue
        바닥 = 시작맵.get(c['src'], 0.0)
        표.append((바닥 + c['in'], 바닥 + c['out'], 자리프 / fps))
        자리프 += round(c['out'] * fps) - round(c['in'] * fps)
    return 표


def 남은낱말(받, 표):
    """컷에 남은 낱말만 (글, 시퀀스시작, 시퀀스끝, 컷번호) 로. 컷에 걸친 낱말은 컷 안쪽으로 자른다."""
    모두 = sorted((w for s in 받 for w in (s.get('words') or [])), key=lambda w: float(w['s']))
    out = []
    for w in 모두:
        ws, we = float(w['s']), float(w['e'])
        for k, (a, b, s) in enumerate(표):
            if ws < b and we > a:
                글 = str(w.get('w', '')).strip()
                if 맨글(글):
                    out.append((글, s + max(0.0, ws - a), s + min(b - a, we - a), k))
                break
    return out


def 문장나누기(낱말들, 사이):
    """낱말을 문장 덩어리로 끊는다 — 문장부호 뒤, `사이`보다 벌어진 자리, 그리고 **컷 경계**.

    컷 경계를 넘어 뭉치면 서로 다른 두 문장이 한 큐에 들어간다. 컷에서 말끝이 잘려 나가
    문장부호가 없는 데다, 컷을 이어 붙이면 시퀀스에서는 사이가 0초라 벌어짐으로도 안 걸린다
    (마02 실측: `이걸 선색 하나로 가르는 | 색이 그대로면 아직 그 추세고` 가 한 큐가 됐다).
    """
    덩어리, 지금 = [], []
    for k, w in enumerate(낱말들):
        지금.append(w)
        뒤 = 낱말들[k + 1] if k + 1 < len(낱말들) else None
        끝남 = w[0].rstrip().endswith(('.', '?', '!', '…'))
        벌어짐 = 뒤 is not None and 뒤[1] - w[2] > 사이
        컷바뀜 = 뒤 is not None and len(w) > 3 and len(뒤) > 3 and 뒤[3] != w[3]
        if 끝남 or 벌어짐 or 컷바뀜 or 뒤 is None:
            덩어리.append(지금)
            지금 = []
    return [d for d in 덩어리 if d]


def 조각시각(덩어리, 조각들):
    """조각마다 (시작, 끝) — 조각의 글자를 낱말에서 차례로 먹어 들어가며 짚는다.

    글자가 낱말을 이어 붙인 것 그대로라 짐작할 자리가 없다. 맞대기(difflib)를 쓰지 않는다.
    """
    k, 남은 = 0, 맨글(덩어리[0][0]) if 덩어리 else ''
    때 = []
    for 조 in 조각들:
        글 = 맨글(조)
        if not 글:
            때.append(None)
            continue
        #  **다 먹은 낱말을 먼저 넘긴다.** 안 넘기면 조각 머리가 앞 조각의 마지막 낱말을 가리켜
        #  자막이 한 낱말 앞에서 뜬다.
        while not 남은 and k + 1 < len(덩어리):
            k += 1
            남은 = 맨글(덩어리[k][0])
        첫, 쓴 = k, 0
        while 쓴 < len(글):
            if not 남은:
                if k + 1 >= len(덩어리):
                    break
                k += 1
                남은 = 맨글(덩어리[k][0])
                continue
            먹 = min(len(남은), len(글) - 쓴)
            쓴 += 먹
            남은 = 남은[먹:]
        때.append((덩어리[첫][1], 덩어리[k][2]))
    return 때


def 더가르기(글, 조각내기, 한도):
    """`조각내기` 가 낸 조각이 아직 길면, **같은 규칙으로** 한 번 더 가른다.

    `ko_clause` 는 한 번에 둘로만 쪼갠다 (`아주길다` 를 넘는 조각을 반으로). 받아쓰기 글은
    문장부호가 드물어 한 조각이 길게 뭉치므로, 더 안 쪼개질 때까지 되풀이한다.
    가르는 **자리를 고르는 것은 끝까지 ko_clause** 다 — 여기서 글자 수로 자르지 않는다.
    """
    조각 = 조각내기(글)
    for _ in range(4):
        새 = []
        for c in 조각:
            새 += 조각내기(c) if len(c) > 한도 else [c]
        if 새 == 조각:
            break
        조각 = 새
    return 조각


def 만들기(작업, 컷리스트, 조각내기, 두줄, 시각, 사이=0.6, 당김=0.15, fps=29.97, 줄당=0,
          한도=24):
    받 = json.load(io.open(os.path.join(작업, 'cam_transcript.json'), encoding='utf-8'))
    파일들 = json.load(io.open(os.path.join(작업, 'cam_files.json'), encoding='utf-8'))
    시작맵 = {f['파일'][:8]: f['시작'] for f in 파일들}
    프레임 = lambda t: round(t * fps) / fps                                  # noqa: E731

    낱말들 = 남은낱말(받, 표만들기(컷리스트, 시작맵, fps))
    줄들 = []
    for 덩어리 in 문장나누기(낱말들, 사이):
        글 = re.sub(r'\s+', ' ', ' '.join(w[0] for w in 덩어리)).strip()
        if not 맨글(글):
            continue
        조각들 = [c for c in 더가르기(글, 조각내기, 한도) if c.strip()]
        for 조, 때 in zip(조각들, 조각시각(덩어리, 조각들)):
            if not 때 or 때[1] <= 때[0]:
                continue
            줄들.append((프레임(max(0.0, 때[0] - 당김)), 프레임(때[1]), 조.strip()))

    줄들.sort()
    for i in range(len(줄들) - 1):                      # 겹치면 앞 자막을 당겨 끊는다
        if 줄들[i][1] > 줄들[i + 1][0]:
            줄들[i] = (줄들[i][0], max(줄들[i][0] + 0.3, 줄들[i + 1][0] - 0.05), 줄들[i][2])
    줄들 = [(a, b, t) for a, b, t in 줄들 if b > a]
    글 = '\n'.join('%d\n%s --> %s\n%s\n' % (i, 시각(a), 시각(b), 두줄(t, 줄당) if 줄당 else t)
                   for i, (a, b, t) in enumerate(줄들, 1))
    return 글, 줄들


def 고치기(작업, 고침길):
    """받아쓰기 오인식을 낱말 단위로 되돌린다. 바꾼 것은 전부 찍는다.

    고침표의 열쇠는 **정규식**이고, 낱말 하나(앞뒤 공백을 뗀 것)에만 댄다.
    그냥 글자 겹치기로 하면 엉뚱한 낱말을 먹는다 — `들은 → 드린` 하나가 `여러분들은` 을
    `여러분드린` 으로 만들었다 (2026-10-08 실측). 겹치기로 족한 것은 그대로 적고,
    낱말 전체를 가리켜야 하는 것은 `^…$` 로 묶는다.
    """
    표 = [(re.compile(a), b) for a, b in json.load(io.open(고침길, encoding='utf-8')).items()]
    길 = os.path.join(작업, 'cam_transcript.json')
    받 = json.load(io.open(길, encoding='utf-8'))
    셈 = {}
    for s in 받:
        for w in (s.get('words') or []):
            원 = str(w.get('w', ''))
            속 = 원.strip()
            새속 = 속
            for 개, b in 표:
                새속 = 개.sub(b, 새속)
            if 새속 != 속:
                w['w'] = 원.replace(속, 새속)
                셈[속] = 셈.get(속, 0) + 1
        s['text'] = ''.join(w['w'] for w in (s.get('words') or [])) or s.get('text', '')
    json.dump(받, io.open(길, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for k, n in sorted(셈.items(), key=lambda kv: -kv[1]):
        print('  고침 %-16s %d번' % (k, n))
    return sum(셈.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('작업')
    ap.add_argument('컷리스트')
    ap.add_argument('낼곳')
    ap.add_argument('--고침', default=None, help='받아쓰기 오인식 고침표 (json)')
    ap.add_argument('--사이', type=float, default=0.6, help='이보다 벌어지면 문장을 끊는다 (초)')
    ap.add_argument('--당김', type=float, default=0.15)
    ap.add_argument('--fps', type=float, default=29.97)
    ap.add_argument('--줄당', type=int, default=0, help='0 이면 한 줄로 둔다')
    ap.add_argument('--한도', type=int, default=24,
                    help='이보다 긴 조각은 ko_clause 로 한 번 더 가른다 (마01 납품본 최대 28자)')
    ap.add_argument('--도구', default=os.environ.get(도구환경),
                    help='E_Script/tools/cutedit 폴더 (환경변수 %s 로도 준다)' % 도구환경)
    a = ap.parse_args()

    if not a.도구 or not os.path.isdir(a.도구):
        sys.exit('ko_clause·cam_srt 가 있는 폴더를 주세요 — --도구 <E_Script/tools/cutedit> '
                 '또는 환경변수 %s. (지금: %s)' % (도구환경, a.도구 or '없음'))
    sys.path.insert(0, a.도구)
    import cam_srt                                                   # noqa: E402
    import ko_clause                                                 # noqa: E402

    if a.고침:
        n = 고치기(a.작업, a.고침)
        print('받아쓰기 고침 %d곳' % n)

    컷리스트 = json.load(io.open(a.컷리스트, encoding='utf-8'))
    ko_clause.아주길다 = min(ko_clause.아주길다, a.한도)      # 되풀이해 가르려면 문턱도 낮춘다
    글, 줄들 = 만들기(a.작업, 컷리스트, ko_clause.조각내기, cam_srt.두줄, cam_srt.시각,
                     사이=a.사이, 당김=a.당김, fps=a.fps, 줄당=a.줄당, 한도=a.한도)
    io.open(a.낼곳, 'w', encoding='utf-8').write(글)
    총 = sum(b - a2 for a2, b, _ in 줄들)
    길이 = [len(t) for _, _, t in 줄들] or [0]
    print('%s · 큐 %d개 · 말하는 시간 %.1f분 · 평균 %.1f초 · 글자 중앙 %d · 최대 %d'
          % (a.낼곳, len(줄들), 총 / 60, 총 / max(1, len(줄들)),
             sorted(길이)[len(길이) // 2], max(길이)))


if __name__ == '__main__':
    main()
