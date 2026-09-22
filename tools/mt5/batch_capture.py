"""대본 한 편 → 비트마다 차트 장면을 **골라서 찍는다** (next_step 45 ①).

scenes.py 는 '무엇을 보여 줄지' 와 '어느 구간인지' 를 고르는 데서 멈췄고, 열린 차트 하나(종목·주기 고정)만 봤다.
여기서는 그 뒤를 잇는다.

 1. 비트 → 찾을 움직임.  scenes.RULES 가 먼저. 낱말이 하나도 안 맞아 기본값(trend_burst)으로 떨어진 비트만
    **Jev 에게 뜻으로 묻는다** (confidence 0.7 미만이면 기본값 그대로). 뜻만 보고 가르는 자리라 맡긴다 —
    수를 견주는 자리는 안 맡긴다(D-4, constraint 67).
 2. 종목·주기도 고른다. 팀장 그림 14장은 BTCUSD M1 9 · BTCUSD M5 3 · US100 M1 4(겹침 있음) · 일봉 1 이었다
    (tools/jev/d2_labels.json). 후보마다 같은 움직임을 찾아 **점수가 가장 높은 곳**을 쓴다.
    점수는 전부 비율(낙폭/구간폭 등)이라 주기가 달라도 견줄 수 있다. 같으면 BTCUSD M1 (팀장이 가장 많이 쓴 것).
 3. 찍는다. 비트마다 **새 차트를 열어** 템플릿을 입히고, CMG_Shot 으로 그 시각에 옮기고 지표를 켠 뒤
    창을 PrintWindow 로 찍고, 차트를 닫는다 — 사람이 보던 차트는 안 건드린다.

    python tools/mt5/batch_capture.py <대본.docx|.txt> <출력폴더> [--dry] [--no-jev]
           [--cands BTCUSD:M1,BTCUSD:M5,US100.:M1] [--from 2026-09-01] [--to 2026-09-22]

  --dry     고르기만 하고 찍지 않는다 (MT5 창을 안 건드린다)
  출력      <폴더>/<비트>.png · 콘티.json · 콘티.md(비트마다 왜 이 장면인지)

trade_* 도구는 부르지 않는다. 읽기만 한다.
"""
import argparse
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'jev'))
import scenes as S  # noqa: E402
from mcp import MT5  # noqa: E402

STEP = {'M1': 60, 'M2': 120, 'M5': 300, 'M15': 900, 'M30': 1800, 'H1': 3600, 'H4': 14400, 'D1': 86400}
PREFER = ('BTCUSD', 'M1')          # 동점일 때
TEMPLATE = '기본값.tpl'            # 지표 없는 깨끗한 판 — 켤 지표는 CMG_Shot 이 붙인다
SCALE = 4                          # 봉 하나 16px → 1920 폭에 약 117봉 (탐색 창 110봉과 맞춘다)
JEV_GATE = 0.7

# Jev 에게 보이는 선택지 설명. RULES 의 why 는 **차트 말**뿐이라 대본 문장과 잇지 못했다 —
# 차10 3-4("1단계 매수, 2단계 매도 후 다시 올라 3단계 매수") 에 톱니를 못 골랐다(0.46).
# 그래서 '대본이 이런 말을 할 때 → 차트는 이렇게' 로 쓴다.
JEV_DESC = {
    'ema200_adx_entry': '대본이 200EMA·ADX 로 방향을 정하고 첫 진입하는 법을 설명할 때 → 200EMA 위(아래)에서 ADX 가 25 를 넘는 자리',
    'ema20_switch': '대본이 첫 진입 뒤 20EMA 를 기준으로 반대 포지션으로 바꾸는 법을 설명할 때 → 20EMA 를 반대로 깨는 자리',
    'zigzag3': '대본이 매수·매도를 번갈아 넣는 단계(1단계 매수 → 2단계 매도 → 3단계 매수…)를 말할 때 → 올랐다 내렸다 다시 오르는 톱니',
    'high_then_drop': '대본이 매수했는데 가격이 밀려 손실이 난 상황을 말할 때 → 고점 뒤로 하락이 이어지는 구간',
    'support_break': '대본이 지지선이 깨지는 상황을 말할 때 → 지지선을 뚫고 내려가는 움직임',
    'chop_box': '대본이 방향 없이 오르내리기만 하는 장, 박스권, 횡보를 말할 때 → 좁은 박스 안의 등락',
    'session_burst': '대본이 장 시작·개장 시간·변동성이 커지는 시간대를 말할 때 → 조용하다가 크게 흔들리기 시작하는 구간',
    'whipsaw': '대본이 방향을 맞히려다 양쪽으로 손실을 보는 상황을 말할 때 → 위아래로 크게 쓸리는 구간',
}


# ─── 1. 비트 → 움직임 ──────────────────────────────────────────────────

def ask_jev(beat, rules):
    """규칙이 못 잡은 비트를 Jev 에게 뜻으로 묻는다 → (규칙 dict | None, confidence)."""
    try:
        import jev
    except Exception:
        return None, 0.0
    opts = {r['name']: JEV_DESC.get(r['name'], r['why']) for r in rules}
    opts['none'] = '대본이 특정 움직임을 말하지 않는다(질문·원칙·숫자 설명 등) → 한 방향으로 뻗는 추세면 충분하다'
    try:
        ans = jev.ask({'대본 대목': beat['text'][:500]},
                      {'q': jev.choice('이 대목을 말할 때 화면의 차트는 어떤 움직임을 보여 줘야 하는가', opts)})
        got, conf = jev.pick(ans, 'q')
    except Exception as e:                          # 값·망 문제로 막혀도 촬영은 계속한다
        print(f'   (Jev 실패: {e})')
        return None, 0.0
    if got == 'none':
        return 'none', conf
    if conf < JEV_GATE:
        return None, conf
    return next(r for r in rules if r['name'] == got), conf


def spec_of(beat, use_jev):
    sp = S.spec_for(beat)
    sp['by'] = '규칙'
    if sp['name'] == S.FALLBACK['name'] and use_jev:
        r, conf = ask_jev(beat, S.RULES)
        if r == 'none':
            sp['by'] = f'기본값 (Jev: 특정 움직임 없음 {conf:.2f})'
        elif r:
            sp = dict(r, id=beat['id'], by=f'Jev {conf:.2f}')
        else:
            sp['by'] = f'기본값 (Jev {conf:.2f} — 문 {JEV_GATE} 아래)'
    return sp


# ─── 2. 종목·주기·구간 ────────────────────────────────────────────────

def choose(sp, pools):
    """후보 (종목, 주기) 마다 pick 을 해 보고 점수가 가장 높은 것 하나를 고른다."""
    best = None
    for key, pool in pools.items():
        trial = list(pool['used'])
        got = S.pick(sp, pool['bars'], used=trial, step_sec=STEP.get(key[1], 60))
        if not got:
            continue
        rank = (got['score'], key == PREFER)
        if best is None or rank > best[0]:
            best = (rank, key, got, trial)
    if best is None:
        return None
    _, key, got, trial = best
    pools[key]['used'] = trial                      # 고른 후보에만 '쓴 구간' 을 남긴다
    got.update(symbol=key[0], period=key[1])
    return got


# ─── 3. 찍기 ──────────────────────────────────────────────────────────

def capture(m, got, out):
    import capture as CAP
    from capture_scene import IND
    cid = str(m.call('chart_open', {'symbol': got['symbol'], 'period': got['period']})['chart_id'])
    try:
        m.call('chart_apply_template', {'chart_id': cid, 'template_filename': TEMPLATE})
        time.sleep(3.0)                             # 템플릿이 지표를 갈아 끼우는 중에 붙이면 같이 지워진다
        inds = '+'.join(got['indicators'])          # 쉼표는 MCP 가 인자 구분자로 먹는다 — '+' 로 잇는다
        m.call('chart_add_indicator', {
            'chart_id': cid, 'indicator_name': 'CMG_Shot', 'custom_indicator_path': IND,
            'indicator_parameters': f"ShotFile=,ShotEndTime={got['to'][:16]},ShotScale={SCALE},"
                                    f"ShotInds={inds},SelfRemove=true,KeepInds=true"})
        # CMG_Shot 은 1.2초마다 한 단계 — 자리 잡기가 3.6초에 끝나고 4.8초에 스스로 빠진다.
        # KeepInds 라 지표는 남으니 넉넉히 기다린다 (차트째 닫으므로 사람 차트엔 안 남는다)
        time.sleep(6.5)
        ch = next((c for c in m.open_charts() if str(c['chart_id']) == cid), None)
        # 붙었다고 믿지 않는다 — 차트에 실제로 달린 지표를 세어 요청과 맞춘다.
        # (09-22: 쉼표 때문에 EMA200 하나만 붙었는데 아무 오류도 없었다)
        on = [i.get('name', '') for i in (ch or {}).get('indicators', [])]
        want_ma = sum(1 for x in got['indicators'] if x.startswith('EMA'))
        want_adx = sum(1 for x in got['indicators'] if x == 'ADX')
        have_ma = sum(1 for n in on if 'Moving Average' in n)
        have_adx = sum(1 for n in on if 'ADX' in n or 'Average Directional' in n)
        got['indicators_on'] = on
        if have_ma < want_ma or have_adx < want_adx:
            got['warn'] = f'지표가 덜 붙었다: 요청 {got["indicators"]} · 차트 {on}'
            print(f"   경고 — {got['warn']}")
        full = CAP.shoot(CAP.find_window())
        top = CAP.chart_top(full)
        w = ch['rect_right'] if ch else full.size[0]
        h = ch['rect_bottom'] if ch else full.size[1] - top
        full.crop((0, top, w, top + h)).save(out)
        return ch
    finally:
        m.call('chart_close', {'chart_id': cid})


# ─── 실행 ─────────────────────────────────────────────────────────────

def read_script(path):
    if path.lower().endswith('.docx'):
        return S.read_docx(path)
    return io.open(path, encoding='utf-8').read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('script')
    ap.add_argument('out')
    ap.add_argument('--cands', default='BTCUSD:M1,BTCUSD:M5,US100.:M1')
    ap.add_argument('--from', dest='dt_from', default='2026-09-01')
    ap.add_argument('--to', dest='dt_to', default=time.strftime('%Y-%m-%d'))
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--no-jev', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    beats = S.split_beats(read_script(a.script))
    print(f'비트 {len(beats)}개')
    m = MT5()
    pools = {}
    for c in a.cands.split(','):
        sym, per = c.split(':')
        bars = m.history(sym, per, a.dt_from + 'T00:00:00', a.dt_to + 'T00:00:00')
        pools[(sym, per)] = {'bars': bars, 'used': []}
        print(f'  {sym} {per}: 봉 {len(bars)}')

    conti = []
    for be in beats:
        sp = spec_of(be, not a.no_jev)
        got = choose(sp, pools)
        line = f"({be['id']}) {sp['name']:<17} [{sp['by']}]"
        if not got:
            print(line + '  못 찾음')
            conti.append({'id': be['id'], 'pattern': sp['name'], 'by': sp['by'], 'text': be['text'][:200], 'png': None})
            continue
        got.update(by=sp['by'], text=be['text'][:200])
        png = os.path.join(a.out, f"{be['id']}.png")
        if not a.dry:
            capture(m, got, png)
            got['png'] = os.path.basename(png)
        conti.append(got)
        print(f"{line}  {got['symbol']} {got['period']} {got['from'][5:16]}~{got['to'][5:16]}  {got['note']}")

    with io.open(os.path.join(a.out, '콘티.json'), 'w', encoding='utf-8') as f:
        json.dump(conti, f, ensure_ascii=False, indent=1)
    md = ['# 차트 장면 콘티', '', '| 비트 | 장면 | 누가 골랐나 | 종목·주기 | 구간 | 지표 | 왜 | 대본 |', '|---|---|---|---|---|---|---|---|']
    for c in conti:
        if not c.get('symbol'):
            md.append(f"| {c['id']} | 못 찾음 | {c['by']} | | | | | {c['text'][:40]} |")
            continue
        img = f"![]({c['png']})" if c.get('png') else c['pattern']
        md.append(f"| {c['id']} | {img} | {c['by']} | {c['symbol']} {c['period']} | {c['from'][5:16]} ~ {c['to'][5:16]} "
                  f"| {','.join(c['indicators']) or '없음'}{' ⚠ ' + c['warn'] if c.get('warn') else ''} "
                  f"| {c['why']} · {c['note']} | {c['text'][:40]}… |")
    with io.open(os.path.join(a.out, '콘티.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(md) + '\n')
    print(f"\n콘티 {sum(1 for c in conti if c.get('symbol'))}/{len(conti)}장 → {a.out}")


if __name__ == '__main__':
    main()
