"""콘티 → **촬영 큐시트** (전문가가 리플레이로 찍을 때 보는 표 + 리플레이가 읽는 표).

    python tools/mt5/cue_sheet.py <콘티폴더> [--title 차11] [--lead 30] [--no-install]

비트마다 "어느 종목·주기를, 언제부터 재생해서, 무엇을 보여 주는가" 한 줄이다.
재생 시작은 고른 구간의 **시작보다 lead 봉 앞**으로 잡는다 — 전문가가 말을 시작할 여유를 둔다.

내놓는 것 둘
  - `촬영큐시트.md`  : 사람이 보는 표
  - `cmg_cues.csv`   : 리플레이 도구가 읽는 표. MQL5\\Files 에도 같이 넣는다(--no-install 로 끈다).
    전문가는 차트에서 **N(다음 장면)·B(이전 장면)** 만 누르면 그 종목·주기·시각으로 바로 간다.

왜 필요한가: 지금은 D 가 고른 구간을 D 만 안다. 전문가가 리플레이(커스텀 심볼 방식)로 직접 진행하면
편집이 거의 사라지는데, 그러려면 **입력할 시각**이 손에 있어야 한다 (이정찬 2026-09-29).
"""
import argparse
import datetime as dt
import io
import json
import os

STEP = {'M1': 1, 'M2': 2, 'M5': 5, 'M15': 15, 'M30': 30, 'H1': 60, 'H4': 240, 'D1': 1440}

TERMINAL_ID = os.environ.get('MT5_TERMINAL_ID', '061BAFBAE5645A1204F350EE84A4B55F')


def mql5_files():
    return os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'MetaQuotes',
                        'Terminal', TERMINAL_ID, 'MQL5', 'Files')


def back(ts, period, bars):
    """'2026.09.21 11:32:00' 에서 bars 봉 앞 시각 (주말·휴장은 셈에 안 넣는다 — 대략값이다)."""
    t = dt.datetime.strptime(ts[:16], '%Y.%m.%d %H:%M')
    return (t - dt.timedelta(minutes=STEP.get(period, 1) * bars)).strftime('%Y.%m.%d %H:%M')


def write_csv(path, title, lead, cues):
    """리플레이 도구가 읽는 표. MQL5 가 FILE_TXT 로 읽으므로 **UTF-16LE + BOM** 이다."""
    lines = ['# %s 촬영 큐시트 — 리플레이가 읽는다 (재생 시작은 구간 시작 %d봉 앞)' % (title, lead),
             '# 비트,종목,주기,시작시각,메모']
    for c in cues:
        lines.append('%s,%s,%s,%s,%s' % (c['id'], c['symbol'], c['period'], c['start'],
                                         c['note'].replace(',', ' ')))
    io.open(path, 'w', encoding='utf-16').write('\n'.join(lines) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--title', default='차11')
    ap.add_argument('--lead', type=int, default=30, help='재생 시작을 구간 시작보다 몇 봉 앞에 둘까')
    ap.add_argument('--no-install', action='store_true', help='MQL5\\Files 에 넣지 않는다')
    a = ap.parse_args()
    conti = json.load(io.open(os.path.join(a.folder, '콘티.json'), encoding='utf-8'))

    rows = ['# %s 촬영 큐시트 (리플레이용)' % a.title, '',
            '재생 시작은 구간 시작보다 %d봉 앞이다. 표시할 것은 "왜 이 장면인가" 에서 왔다.' % a.lead,
            '차트에서 **N** 을 누르면 다음 장면, **B** 는 이전 장면이다 (순서는 이 표 그대로).', '',
            '| 비트 | 종목·주기 | 재생 시작 | 장면이 나오는 구간 | 켤 지표 | 보여 줄 것 | 대본 |',
            '|---|---|---|---|---|---|---|']
    cues = []
    for c in conti:
        if not c.get('symbol'):
            rows.append('| %s | — | — | — | — | 못 찾음 | %s |' % (c['id'], c.get('text', '')[:30]))
            continue
        start = back(c['from'], c['period'], a.lead)
        rows.append('| %s | %s %s | **%s** | %s ~ %s | %s | %s | %s… |' % (
            c['id'], c['symbol'], c['period'], start,
            c['from'][5:16], c['to'][5:16],
            ','.join(c.get('indicators') or []) or '없음',
            c.get('why', ''), c.get('text', '')[:30]))
        cues.append({'id': c['id'], 'symbol': c['symbol'], 'period': c['period'],
                     'start': start, 'note': c.get('why', '')})

    out = os.path.join(a.folder, '촬영큐시트.md')
    io.open(out, 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
    print('%d줄 → %s' % (len(conti), out))

    csv = os.path.join(a.folder, 'cmg_cues.csv')
    write_csv(csv, a.title, a.lead, cues)
    print('%d줄 → %s' % (len(cues), csv))

    if not a.no_install:
        dst_dir = mql5_files()
        if os.path.isdir(dst_dir):
            dst = os.path.join(dst_dir, 'cmg_cues.csv')
            write_csv(dst, a.title, a.lead, cues)
            print('       → %s (리플레이가 여기서 읽는다)' % dst)
        else:
            print('       MQL5\\Files 를 못 찾았다 — 손으로 넣으세요: %s' % dst_dir)


if __name__ == '__main__':
    main()
