"""D-2 — 대본 비트를 보고 '어떤 차트를 보여 줄 것인가' 를 Jev 가 고르게 하고, 팀장이 실제로 고른 것과 맞춰 본다.

정답 자료: `tools/jev/d2_labels.json` (팀장 그림 14장을 D 가 판독한 것)
대본:     `log/data/ref_cha10/script10.txt` — 차10 은 **이미 나간 회차**다(최종 prproj·납품 소스 있음). 미공개 대본이 아니다.
같이 잰다: 지금 규칙 기반 `tools/mt5/scenes.py` 가 같은 비트에 뭐라 답하는지.

state 에는 **그 비트 문장만** 넣는다 (문서: 무관한 내용이 많으면 정확도가 떨어진다).
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
import scenes  # noqa: E402

KINDS = {
    '원리': '매매 원리를 말로 설명하는 대목 — 지표 이름이 안 나온다',
    '지표설명': '특정 지표(이동평균선·ADX 같은)를 어떻게 쓰는지 설명하는 대목',
    '그밖': '위 둘이 아닌 대목 — 도입·주의·마무리',
}
EVENTS = {
    '고점뒤하락': '고점을 찍고 내려가는 움직임',
    '급락': '짧은 시간에 크게 떨어지는 움직임',
    '톱니': '올랐다 내렸다를 여러 번 되풀이하는 움직임',
    '박스권': '좁은 폭 안에서만 오가는 움직임',
    '추세지속': '한 방향으로 계속 가는 움직임',
    '되돌림': '가던 방향과 반대로 밀리는 움직임',
    '변동성확대': '움직임의 폭이 갑자기 커지는 구간',
}
# 내 판독 문장을 위 낱말로 옮긴 것 (정답)
EVENT_OF = {
    '1-3': '톱니', '1-4': '급락', '1-5': '박스권', '2-1': '되돌림',
    '2-2': '고점뒤하락', '2-3': '톱니', '3-2': '추세지속', '3-3': '박스권',
    '3-4': '박스권', '4-1': '추세지속', '4-2': '되돌림',
}


def rule_kind(spec):
    if spec['indicators']:
        return '지표설명'
    return '원리' if spec['name'] in ('zigzag3', 'high_then_drop') else '그밖'


def main():
    labels = json.load(io.open(os.path.join(HERE, 'd2_labels.json'), encoding='utf-8'))['items']
    by_id = {}
    for x in labels:                      # 2-1(1)·2-1(2) 는 같은 비트 2-1 이다
        by_id.setdefault(x['id'].split('(')[0], x)

    text = io.open(os.path.join(ROOT, 'log', 'data', 'ref_cha10', 'script10.txt'),
                   encoding='utf-8').read()
    beats = {b['id']: b for b in scenes.split_beats(text)}

    rows = []
    for bid, lab in sorted(by_id.items()):
        if bid not in beats or bid not in EVENT_OF:
            continue
        beat = beats[bid]
        spec = scenes.spec_for(beat)
        ans = jev.ask(beat['text'], {
            'kind': jev.choice('이 대목은 어떤 성격인가', KINDS),
            'event': jev.choice('이 대목을 보여 주려면 차트에 어떤 움직임이 있어야 하나', EVENTS),
        })
        k, kc = jev.pick(ans, 'kind')
        e, ec = jev.pick(ans, 'event')
        rows.append({
            'id': bid, '정답_kind': lab['kind'], '정답_event': EVENT_OF[bid],
            'jev_kind': k, 'jev_kind_conf': kc, 'jev_event': e, 'jev_event_conf': ec,
            '규칙_kind': rule_kind(spec), '규칙_pattern': spec['name'],
        })
        print(f"{bid:<5} 정답 {lab['kind']:<5}/{EVENT_OF[bid]:<7} | "
              f"jev {k:<5}({kc:.2f})/{e:<7}({ec:.2f}) | 규칙 {rule_kind(spec)}")

    n = len(rows)
    kok = sum(1 for r in rows if r['jev_kind'] == r['정답_kind'])
    eok = sum(1 for r in rows if r['jev_event'] == r['정답_event'])
    rok = sum(1 for r in rows if r['규칙_kind'] == r['정답_kind'])
    print(f"\n성격: jev {kok}/{n} · 규칙 {rok}/{n}")
    print(f"움직임: jev {eok}/{n}")
    conf_ok = [r['jev_kind_conf'] for r in rows if r['jev_kind'] == r['정답_kind']]
    conf_no = [r['jev_kind_conf'] for r in rows if r['jev_kind'] != r['정답_kind']]
    if conf_ok:
        print(f"confidence 맞은 것 평균 {sum(conf_ok) / len(conf_ok):.2f}"
              + (f" · 틀린 것 평균 {sum(conf_no) / len(conf_no):.2f}" if conf_no else " · 틀린 것 없음"))
    json.dump(rows, io.open(os.path.join(HERE, 'd2_result.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
