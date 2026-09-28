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
