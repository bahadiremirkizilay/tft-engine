import pytest
from hypothesis import given
from hypothesis import strategies as st

from tft_engine.state import GameState, PoolBelief, PoolState, UnitInstance

CP = {1: 10, 2: 8, 3: 6, 4: 4, 5: 2}
CC = {1: 3, 2: 3, 3: 3, 4: 2, 5: 2}


def test_gamestate_roundtrip_and_hash_ignores_order():
    a = GameState("3-2", 30, 6, 4, 70, 2, (UnitInstance("X", 1, 2), UnitInstance("Y", 3)))
    b = GameState("3-2", 30, 6, 4, 70, 2, (UnitInstance("Y", 3), UnitInstance("X", 1, 2)))
    assert GameState.from_dict(a.to_dict()) == a
    assert a.state_hash() == b.state_hash()
    assert a.copies_owned("X") == 3


def test_gamestate_rejects_bad_values():
    with pytest.raises(ValueError):
        GameState("3-2", -1, 6, 0, 70)
    with pytest.raises(ValueError):
        GameState("32", 10, 6, 0, 70)


def test_pool_build_removes_taken_copies():
    pool = PoolState.build(CP, CC, {"A": 1, "B": 3}, taken={"A": 4}, taken_untracked={1: 2})
    assert pool.remaining("A") == 6
    assert pool.remaining("B") == 6
    assert pool.tier_remaining == (30 - 4 - 2, 24, 18, 8, 4)


def test_pool_rejects_overdraw():
    with pytest.raises(ValueError):
        PoolState.build(CP, CC, {"A": 1}, taken={"A": 11})


@given(st.integers(0, 10), st.integers(0, 10))
def test_pool_take_conserves_copies(taken, take):
    pool = PoolState.build(CP, CC, {"A": 1}, taken={"A": taken})
    if take > pool.remaining("A"):
        with pytest.raises(ValueError):
            pool.take("A", take)
        return
    after = pool.take("A", take)
    assert after.remaining("A") == pool.remaining("A") - take
    assert sum(pool.tier_remaining) - sum(after.tier_remaining) == take


def test_belief_weights_must_sum_to_one():
    pool = PoolState.build(CP, CC, {"A": 1})
    with pytest.raises(ValueError):
        PoolBelief(((0.5, pool),))
    mix = PoolBelief.mixture([(2, pool), (2, pool.take("A", 3))], basis="prior")
    assert [w for w, _ in mix.states] == [0.5, 0.5]
