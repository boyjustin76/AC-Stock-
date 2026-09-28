# -*- coding: utf-8 -*-
"""batch_capture.choose — 종목·주기 고르기가 '봉이 많은 주기가 늘 이기는' 치우침에 빠지지 않는지 (MT5 없이).

09-22 차11: 점수 1등만 쓰니 35비트 중 34비트가 M1·M5 였다. 팀장은 M1 을 한 장도 안 썼다(US100 M15·H1·D1).
봉이 많으면 후보 구간이 많아 최고 점수가 우연히 높아진다. 그래서 1등의 NEAR_TIE 안은 동점으로 보고 회차 순서를 따른다.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'mt5'))
B = pytest.importorskip('batch_capture')


def test_right_edge_tolerance():
    """화면 오른쪽 끝 봉 검사 — 목표 봉이나 데이터상 **다음 봉**이면 맞다. 그보다 벌어지면 다른 구간."""
    want, nxt = '2026.09.21 11:32', '2026.09.21 11:33:00'
    assert B.near_enough(want, want, nxt)
    assert B.near_enough('2026.09.21 11:33', want, nxt), '다음 봉은 정상이어야 한다'
    assert not B.near_enough('2026.09.21 11:35', want, nxt), '세 봉 뒤를 정상으로 봤다'
    assert not B.near_enough('2026.09.22 11:32', want, nxt), '하루 뒤를 정상으로 봤다 (09-22 사고)'
    assert not B.near_enough('2026.09.28 05:07', want, nxt), '최신 화면(못 옮김)을 정상으로 봤다 (09-28 2-1)'
    assert not B.near_enough('2026.09.21 11:31', want, nxt), '목표보다 앞은 덜 옮겨진 것이다'
    assert not B.near_enough('', want, nxt) and not B.near_enough(None, want, nxt)
    # 주말 구멍 — 금 23:00 다음 봉이 월 01:00 이다. 시계로 세면 사흘이라 오탐이 났다(09-28 1-1)
    assert B.near_enough('2026.04.20 01:00', '2026.04.17 23:00', '2026.04.20 01:00:00')
    assert not B.near_enough('2026.04.20 02:00', '2026.04.17 23:00', '2026.04.20 01:00:00')


def test_box_script_does_not_get_trend_scene(monkeypatch):
    """대본이 횡보장을 말하는데 추세·돌파 장면이 걸리면 박스 계열에서 다시 고른다 (09-28 검수 4-4·5-9)."""
    asked = {}

    def fake_ask(beat, rules, allow_none=True, gate=None):
        asked['names'] = [r['name'] for r in rules]
        asked['allow_none'] = allow_none
        return next(r for r in rules if r['name'] == 'chop_box'), 0.3
    monkeypatch.setattr(B, 'is_sideways', lambda beat: (True, 0.9))
    monkeypatch.setattr(B, 'ask_jev', fake_ask)
    beat = {'id': '4-4', 'text': '이러한 횡보장에서 "20일선을 돌파했으니 매도한다" 는 원칙을 대입하면 손절만 반복됩니다'}
    sp = B.box_override(beat, {'name': 'ma_break_up', 'indicators': [], 'why': 'x', 'by': '규칙'}, True)
    assert sp['name'] == 'chop_box', f"횡보 대목에 {sp['name']} 이 그대로 남았다"
    assert set(asked['names']) <= set(B.BOXY), '박스 계열 밖의 선택지를 줬다'
    assert asked['allow_none'] is False, "'해당 없음' 을 남기면 그쪽으로 도망간다 (09-28: 0.70 → 0.31)"


def test_box_override_needs_sideways_judgement(monkeypatch):
    """'박스권이 아니라 추세장이면…' 같은 문장도 있다 — 낱말만으로 바꾸지 않는다."""
    monkeypatch.setattr(B, 'is_sideways', lambda beat: (False, 0.9))

    def fake_ask(beat, rules, allow_none=True, gate=None):
        raise AssertionError('횡보장이 아니라고 했으면 장면을 다시 묻지 않는다')
    monkeypatch.setattr(B, 'ask_jev', fake_ask)
    beat = {'id': '5-2', 'text': '박스권이 아니라 추세장이라면 20일선을 따라 끝까지 끌고 갑니다'}
    sp = B.box_override(beat, {'name': 'trend_burst', 'indicators': [], 'why': 'x', 'by': '규칙'}, True)
    assert sp['name'] == 'trend_burst'


def test_box_override_leaves_trend_script_alone(monkeypatch):
    """횡보 낱말이 없으면 건드리지 않는다 — Jev 에게 묻지도 않는다."""
    def fake_side(beat):
        raise AssertionError('묻지 말아야 한다')
    monkeypatch.setattr(B, 'is_sideways', fake_side)
    beat = {'id': '5-1', 'text': '가격이 20일선 위에서 강한 상승 추세를 이어 갑니다'}
    sp = B.box_override(beat, {'name': 'trend_burst', 'indicators': [], 'why': 'x', 'by': '규칙'}, True)
    assert sp['name'] == 'trend_burst'


def test_indicator_enumeration_is_read():
    """'5일, 20일, 60일선' 처럼 앞엣것에 '선' 이 안 붙는 나열도 읽는다 (09-28 4차 검수: 2-4 가 MA60 하나뿐이었다)."""
    got = B.S.indicators_of('주식 시장의 5일, 20일, 60일선 등을 그대로 띄워두고 매매합니다', 20)
    assert {'MA5', 'MA20', 'MA60'} <= set(got), got
    # 이평선 이야기가 아닌 숫자는 줍지 않는다
    assert not B.S.indicators_of('1단계 0.1계약, 2단계 0.2계약으로 늘립니다', None)


def test_symbol_follows_script():
    """대본이 부른 종목을 먼저 본다 (09-28 검수: 암호화폐 대목에 US100 이 뽑혔다)."""
    order = B.ORDER_DAILY_MA
    crypto = B.order_for({'text': '비트코인과 같은 암호화폐 시장은 주말 없이 돌아갑니다'}, order)
    assert crypto[0].startswith('BTCUSD'), crypto
    index = B.order_for({'text': '나스닥을 기준으로 본다면 개장 직후 변동성이 큽니다'}, order)
    assert index[0].startswith('US100'), index
    assert B.order_for({'text': '이동평균선은 한 달 평균 단가입니다'}, order) == order, '종목 말이 없으면 그대로 둔다'
    assert sorted(crypto) == sorted(order), '후보를 빠뜨리거나 더했다'


def test_indicators_survive_scene_override(monkeypatch):
    """장면을 바꿔도 회차 주제 지표는 남아야 한다 (09-28 검수: 4-4 가 whipsaw 로 바뀌며 MA20 이 사라졌다)."""
    monkeypatch.setattr(B, 'is_sideways', lambda beat: (True, 0.9))
    monkeypatch.setattr(B, 'ask_jev', lambda beat, rules, allow_none=True, gate=None:
                        (next(r for r in rules if r['name'] == 'whipsaw'), 0.4)
                        if all(r['name'] in B.BOXY for r in rules) else (None, 0.0))
    beat = {'id': '4-4', 'text': '이러한 횡보장에서 20일선을 돌파했으니 매도한다는 원칙을 대입하면 손절만 반복됩니다'}
    sp = B.spec_of(beat, True, episode_ma=20, always_on='MA20')
    assert sp['name'] == 'whipsaw'
    assert 'MA20' in sp['indicators'], f"장면을 바꾸며 지표가 날아갔다: {sp['indicators']}"


def fake_pools(scores, monkeypatch, ties=None):
    """가짜 후보 풀. choose 가 고른 뒤 '다음 봉 시각' 을 찾으므로 봉 두 개를 둔다."""
    ties = ties or {}
    pools = {k: {'bars': [{'time': f'{k[0]} t0'}, {'time': f'{k[0]} t1'}], 'used': []} for k in scores}
    by_bars = {id(p['bars']): k for k, p in pools.items()}

    def pick(sp, bars, used=None, step_sec=60, cache=None):
        k = by_bars[id(bars)]
        used.append((0, 1))
        return {'score': scores[k], 'ties': ties.get(k, 1), 'from': bars[0]['time'], 'to': bars[0]['time']}
    monkeypatch.setattr(B.S, 'pick', pick)
    return pools


def test_near_tie_follows_episode_order(monkeypatch):
    pools = fake_pools({('BTCUSD', 'M1'): 0.95, ('US100.', 'H1'): 0.90}, monkeypatch)
    got = B.choose({'name': 'x'}, pools, B.ORDER_DAILY_MA)
    assert (got['symbol'], got['period']) == ('US100.', 'H1'), '점수 차 5% 인데 M1 을 골랐다 — 회차 순서를 안 따른다'


def test_clear_winner_still_wins(monkeypatch):
    pools = fake_pools({('BTCUSD', 'M1'): 0.95, ('US100.', 'H1'): 0.50}, monkeypatch)
    got = B.choose({'name': 'x'}, pools, B.ORDER_DAILY_MA)
    assert got['period'] == 'M1', '점수 차가 큰데 순서만 따랐다'


def test_saturated_candidate_goes_last(monkeypatch):
    pools = fake_pools({('BTCUSD', 'M1'): 1.0, ('US100.', 'H1'): 0.6}, monkeypatch, ties={('BTCUSD', 'M1'): 9})
    got = B.choose({'name': 'x'}, pools, B.ORDER_PLAIN)
    assert got['period'] == 'H1', '점수가 몰린(가르지 못한) 후보를 골랐다'


def test_only_chosen_pool_records_used(monkeypatch):
    pools = fake_pools({('BTCUSD', 'M1'): 0.9, ('US100.', 'H1'): 0.1}, monkeypatch)
    B.choose({'name': 'x'}, pools, B.ORDER_PLAIN)
    assert pools[('BTCUSD', 'M1')]['used'] and not pools[('US100.', 'H1')]['used']
