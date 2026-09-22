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


def fake_pools(scores, monkeypatch, ties=None):
    ties = ties or {}
    pools = {k: {'bars': [k], 'used': []} for k in scores}

    def pick(sp, bars, used=None, step_sec=60, cache=None):
        k = bars[0]
        used.append((0, 1))
        return {'score': scores[k], 'ties': ties.get(k, 1), 'from': 't', 'to': 't'}
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
