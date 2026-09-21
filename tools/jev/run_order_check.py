"""자리 치우침 검사 — 선택지 **차례만** 바꿔 같은 질문을 두 번 묻는다.

E 가 배너 A/B 비교에서 찾은 것(2026-09-21): 자리를 바꾸면 13편 중 3편이 뒤집혔고
한 방향으로만 재면 92%, 양쪽 다 맞아야 하면 69% 였다.
D 의 시험은 쌍 비교가 아니라 여러 선택지 중 고르기라 같은 함정인지 따로 재야 한다.

두 번 물어 답이 같으면 '안정', 다르면 '흔들림'. 흔들리는 것은 사람이 본다.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'mt5'))
import jev  # noqa: E402
import run_d2 as D2  # noqa: E402
import run_d3 as D3  # noqa: E402
import scenes  # noqa: E402


def both_ways(state, instructions, options):
    """선택지 차례를 뒤집어 두 번 묻는다 → (정순 답, 역순 답, conf 둘)."""
    fwd = dict(options)
    rev = dict(reversed(list(options.items())))
    a = jev.ask(state, {'q': jev.choice(instructions, fwd)})
    b = jev.ask(state, {'q': jev.choice(instructions, rev)})
    x, cx = jev.pick(a, 'q')
    y, cy = jev.pick(b, 'q')
    return x, y, cx, cy


def check_d3():
    cons = json.load(io.open(os.path.join(HERE, 'constraints_63.json'), encoding='utf-8'))
    options = {str(c['id']): c['topic'] for c in cons}
    options['없음'] = '해당하는 것이 목록에 없다'
    rows = []
    for text, want in D3.CASES:
        x, y, cx, cy = both_ways(text, '이 일은 아래 기록 중 어느 것인가', options)
        rows.append({'정답': want, '정순': x, '역순': y, 'conf': (cx, cy),
                     '안정': x == y, '둘다맞음': str(x) == str(want) == str(y)})
        print(f"{'=' if x == y else '≠'} 정답 {want:>3} · 정순 {str(x):>3}({cx:.2f}) · 역순 {str(y):>3}({cy:.2f})")
    n = len(rows)
    print(f"\nD-3  안정 {sum(r['안정'] for r in rows)}/{n} · "
          f"양쪽 다 정답 {sum(r['둘다맞음'] for r in rows)}/{n}")
    return rows


def check_d2():
    labels = json.load(io.open(os.path.join(HERE, 'd2_labels.json'), encoding='utf-8'))['items']
    by_id = {}
    for x in labels:
        by_id.setdefault(x['id'].split('(')[0], x)
    text = io.open(os.path.join(ROOT, 'log', 'data', 'ref_cha10', 'script10.txt'),
                   encoding='utf-8').read()
    beats = {b['id']: b for b in scenes.split_beats(text)}
    rows = []
    for bid, lab in sorted(by_id.items()):
        if bid not in beats or bid not in D2.EVENT_OF:
            continue
        x, y, cx, cy = both_ways(beats[bid]['text'], '이 대목은 어떤 성격인가', D2.KINDS)
        rows.append({'id': bid, '정답': lab['kind'], '정순': x, '역순': y, '안정': x == y,
                     '둘다맞음': x == lab['kind'] == y})
        print(f"{'=' if x == y else '≠'} {bid:<5} 정답 {lab['kind']:<5} · "
              f"정순 {x:<5}({cx:.2f}) · 역순 {y:<5}({cy:.2f})")
    n = len(rows)
    print(f"\nD-2  안정 {sum(r['안정'] for r in rows)}/{n} · "
          f"양쪽 다 정답 {sum(r['둘다맞음'] for r in rows)}/{n}")
    return rows


if __name__ == '__main__':
    print('── D-3 오류 분류 ──')
    r3 = check_d3()
    print('\n── D-2 비트 성격 ──')
    r2 = check_d2()
    json.dump({'d3': r3, 'd2': r2},
              io.open(os.path.join(HERE, 'order_check.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
