import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tft_engine.gamedata import load_gamedata
from tft_engine.prob import (
    IndependentShopModel,
    RollQuery,
    Target,
    roll_down_exact,
    roll_down_sample,
)
from tft_engine.state import PoolBelief, PoolState

from .conftest import FIXTURE_SETS

SYN = load_gamedata("synthetic", "1.2", root=FIXTURE_SETS)
S18 = load_gamedata("set18", "18.4")


def pool_params(gd):
    cp = {int(k): v for k, v in gd.get("copies_per_champion").items()}
    cc = {int(k): v for k, v in gd.get("champions_per_cost").items()}
    return cp, cc


def test_closed_form_single_slot():
    # 1 slot, 100% tier 1, target is 1 of 2 copies in the tier, 3 shops affordable.
    model = IndependentShopModel({1: (100, 0, 0, 0, 0)}, slots=1)
    pool = PoolState((2, 0, 0, 0, 0), (("A", 1, 1),))
    q = RollQuery(level=1, gold=5, targets=(Target("A", 1),), roll_cost=2)
    r = roll_down_exact(q, PoolBelief.certain(pool), model)
    assert r.p_success == pytest.approx(1 - 0.5**3)
    # paid rolls: 0 if hit on shop 0 (p=.5), 1 if hit on shop 1 (p=.25), 2 otherwise (p=.25)
    assert r.expected_rolls == pytest.approx(0.25 * 1 + 0.25 * 2)
    assert sum(r.gold_left.values()) == pytest.approx(1.0)


def test_closed_form_two_copies_binomial_shop():
    # 5 slots, one shop only (gold 0 after free shop), need 1 of k=3 among T=30.
    model = IndependentShopModel({1: (100, 0, 0, 0, 0)}, slots=5)
    pool = PoolState((30, 0, 0, 0, 0), (("A", 1, 3),))
    q = RollQuery(level=1, gold=1, targets=(Target("A", 1),), roll_cost=2)
    r = roll_down_exact(q, PoolBelief.certain(pool), model)
    assert r.p_success == pytest.approx(1 - (27 / 30) ** 5)


def test_no_gold_to_buy_means_failure():
    model = IndependentShopModel({1: (100, 0, 0, 0, 0)}, slots=5)
    pool = PoolState((1, 0, 0, 0, 0), (("A", 1, 1),))
    q = RollQuery(level=1, gold=0, targets=(Target("A", 1),), roll_cost=2)
    assert roll_down_exact(q, PoolBelief.certain(pool), model).p_success == 0.0


def test_already_complete_target():
    model = IndependentShopModel.from_gamedata(SYN)
    pool = PoolState.build(*pool_params(SYN), {"A": 1})
    q = RollQuery(level=1, gold=10, targets=(Target("A", 0),), roll_cost=2)
    r = roll_down_exact(q, PoolBelief.certain(pool), model)
    assert r.p_success == 1.0 and r.expected_rolls == 0.0


def _random_scenarios(n, seed):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        gd = S18 if i % 2 == 0 else SYN
        levels = sorted(int(k) for k in gd.get("shop_odds"))
        level = int(rng.choice(levels[2:]))
        odds = gd.get("shop_odds")[str(level)]
        tiers = [c for c in range(1, 6) if odds[c - 1] > 0]
        m = int(rng.integers(1, 4))
        tracked = {f"U{j}": int(rng.choice(tiers)) for j in range(m)}
        cp, cc = pool_params(gd)
        taken = {u: int(rng.integers(0, cp[c] // 2 + 1)) for u, c in tracked.items()}
        targets = tuple(Target(u, int(rng.integers(1, 4))) for u in tracked)
        pool = PoolState.build(cp, cc, tracked, taken=taken)
        if rng.random() < 0.4:  # a belief over how many copies an opponent holds
            alt = PoolState.build(
                cp, cc, tracked, taken={u: min(cp[c], taken[u] + 2) for u, c in tracked.items()}
            )
            belief = PoolBelief.mixture([(0.6, pool), (0.4, alt)], basis="prior")
        else:
            belief = PoolBelief.certain(pool)
        q = RollQuery(
            level=level,
            gold=int(rng.integers(5, 61)),
            targets=targets,
            roll_cost=gd.get("reroll_cost"),
            gold_floor=int(rng.choice([0, 0, 10, 20])),
            first_shop_free=bool(rng.random() < 0.7),
        )
        model = IndependentShopModel.from_gamedata(gd, wisp_takes_slot=bool(rng.random() < 0.3))
        out.append((q, belief, model))
    return out


SCENARIOS = _random_scenarios(30, seed=2026)
# Two-sided 99% with a Bonferroni correction over all scenarios and both checks.
Z = 3.84  # ~ normal quantile for 1 - 0.01 / (2 * 30 * 2)
N_MC = 20_000


@pytest.mark.parametrize("i", range(len(SCENARIOS)))
def test_monte_carlo_agrees_with_exact(i):
    q, belief, model = SCENARIOS[i]
    ex = roll_down_exact(q, belief, model)
    mc = roll_down_sample(q, belief, model, n=N_MC, seed=i)
    p = ex.p_success
    se = math.sqrt(max(p * (1 - p), 1e-12) / N_MC)
    assert abs(mc.p_success - p) <= Z * se + 1e-9, (i, p, mc.p_success)
    # expected gold left, using the exact distribution's spread
    mean = ex.expected_gold_left
    var = sum((g - mean) ** 2 * w for g, w in ex.gold_left.items())
    assert abs(mc.expected_gold_left - mean) <= Z * math.sqrt(var / N_MC) + 1e-9


def test_exact_distribution_sums_to_one():
    for q, belief, model in SCENARIOS:
        r = roll_down_exact(q, belief, model)
        assert sum(r.gold_left.values()) == pytest.approx(1.0)
        assert 0.0 <= r.p_success <= 1.0
        assert all(0 <= g <= q.gold for g in r.gold_left)


def test_sampler_is_reproducible():
    q, belief, model = SCENARIOS[0]
    a = roll_down_sample(q, belief, model, n=2000, seed=5)
    b = roll_down_sample(q, belief, model, n=2000, seed=5)
    assert a.p_success == b.p_success and a.gold_left == b.gold_left


CP18, CC18 = pool_params(S18)
MODEL18 = IndependentShopModel.from_gamedata(S18, wisp_takes_slot=False)


@settings(max_examples=40, deadline=None)
@given(st.integers(0, 15), st.integers(4, 8), st.integers(10, 60))
def test_more_contest_never_helps(taken, level, gold):
    """Opponents holding more copies of your unit can only lower your odds."""
    q = RollQuery(level=level, gold=gold, targets=(Target("A", 2),), roll_cost=2)

    def p(t):
        pool = PoolState.build(CP18, CC18, {"A": 3}, taken={"A": t})
        return roll_down_exact(q, PoolBelief.certain(pool), MODEL18).p_success

    assert p(taken + 1) <= p(taken) + 1e-12


@settings(max_examples=40, deadline=None)
@given(st.integers(0, 60), st.integers(4, 9))
def test_more_gold_never_hurts(gold, level):
    pool = PoolState.build(CP18, CC18, {"A": 4}, taken={"A": 3})

    def p(g):
        q = RollQuery(level=level, gold=g, targets=(Target("A", 2),), roll_cost=2)
        return roll_down_exact(q, PoolBelief.certain(pool), MODEL18).p_success

    assert p(gold + 1) >= p(gold) - 1e-12


def test_belief_is_a_mixture():
    a = PoolState.build(CP18, CC18, {"A": 3}, taken={"A": 2})
    b = PoolState.build(CP18, CC18, {"A": 3}, taken={"A": 8})
    q = RollQuery(level=7, gold=40, targets=(Target("A", 3),), roll_cost=2)
    pa = roll_down_exact(q, PoolBelief.certain(a), MODEL18).p_success
    pb = roll_down_exact(q, PoolBelief.certain(b), MODEL18).p_success
    mix = roll_down_exact(q, PoolBelief.mixture([(0.3, a), (0.7, b)], "prior"), MODEL18)
    assert mix.p_success == pytest.approx(0.3 * pa + 0.7 * pb)
    assert mix.pool_basis == "prior"


def test_wisp_variant_lowers_odds():
    pool = PoolState.build(CP18, CC18, {"A": 3}, taken={"A": 2})
    q = RollQuery(level=7, gold=40, targets=(Target("A", 3),), roll_cost=2)
    plain = roll_down_exact(q, PoolBelief.certain(pool), MODEL18)
    wisp = roll_down_exact(
        q, PoolBelief.certain(pool), IndependentShopModel.from_gamedata(S18, wisp_takes_slot=True)
    )
    assert wisp.p_success < plain.p_success
    assert any("Wisp" in a for a in wisp.assumptions)


def test_never_buys_more_copies_than_exist():
    # Only 1 copy left but 2 needed: success must be impossible, mass must stay 1.
    model = IndependentShopModel({1: (100, 0, 0, 0, 0)}, slots=5)
    pool = PoolState((2, 0, 0, 0, 0), (("A", 1, 1),))
    q = RollQuery(level=1, gold=30, targets=(Target("A", 2),), roll_cost=2)
    r = roll_down_exact(q, PoolBelief.certain(pool), model)
    assert r.p_success == 0.0
    assert sum(r.gold_left.values()) == pytest.approx(1.0)
    mc = roll_down_sample(q, PoolBelief.certain(pool), model, n=2000, seed=1)
    assert mc.p_success == 0.0


def test_set18_follows_wisp_rule_by_default():
    assert IndependentShopModel.from_gamedata(S18).wisp_takes_slot is True
    assert IndependentShopModel.from_gamedata(SYN).wisp_takes_slot is False
