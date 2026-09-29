"""콘티 → **촬영 큐시트** (전문가가 리플레이로 찍을 때 보는 표).

    python tools/mt5/cue_sheet.py <콘티폴더> [--title 차11] [--lead 30]

비트마다 "어느 종목·주기를, 언제부터 재생해서, 무엇을 보여 주는가" 한 줄이다.
재생 시작은 고른 구간의 **시작보다 lead 봉 앞**으로 잡는다 — 전문가가 말을 시작할 여유를 둔다.

왜 필요한가: 지금은 D 가 고른 구간을 D 만 안다. 전문가가 리플레이(커스텀 심볼 방식)로 직접 진행하면
편집이 거의 사라지는데, 그러려면 **입력할 시각**이 손에 있어야 한다 (이정찬 2026-09-29).
"""
import argparse
import datetime as dt
import io
import json
import os

STEP = {'M1': 1, 'M2': 2, 'M5': 5, 'M15': 15, 'M30': 30, 'H1': 60, 'H4': 240, 'D1': 1440}


def back(ts, period, bars):
    """'2026.09.21 11:32:00' 에서 bars 봉 앞 시각 (주말·휴장은 셈에 안 넣는다 — 대략값이다)."""
    t = dt.datetime.strptime(ts[:16], '%Y.%m.%d %H:%M')
    return (t - dt.timedelta(minutes=STEP.get(period, 1) * bars)).strftime('%Y.%m.%d %H:%M')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--title', default='차11')
    ap.add_argument('--lead', type=int, default=30, help='재생 시작을 구간 시작보다 몇 봉 앞에 둘까')
    a = ap.parse_args()
    conti = json.load(io.open(os.path.join(a.folder, '콘티.json'), encoding='utf-8'))

    rows = ['# %s 촬영 큐시트 (리플레이용)' % a.title, '',
            '재생 시작은 구간 시작보다 %d봉 앞이다. 표시할 것은 "왜 이 장면인가" 에서 왔다.' % a.lead, '',
            '| 비트 | 종목·주기 | 재생 시작 | 장면이 나오는 구간 | 켤 지표 | 보여 줄 것 | 대본 |',
            '|---|---|---|---|---|---|---|']
    for c in conti:
        if not c.get('symbol'):
            rows.append('| %s | — | — | — | — | 못 찾음 | %s |' % (c['id'], c.get('text', '')[:30]))
            continue
        rows.append('| %s | %s %s | **%s** | %s ~ %s | %s | %s | %s… |' % (
            c['id'], c['symbol'], c['period'],
            back(c['from'], c['period'], a.lead),
            c['from'][5:16], c['to'][5:16],
            ','.join(c.get('indicators') or []) or '없음',
            c.get('why', ''), c.get('text', '')[:30]))
    out = os.path.join(a.folder, '촬영큐시트.md')
    io.open(out, 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
    print('%d줄 → %s' % (len(conti), out))


if __name__ == '__main__':
    main()
