import pytest
from hypothesis import given
from hypothesis import strategies as st

from tft_engine.gamedata import UnknownMechanicError, load_gamedata
from tft_engine.rules import Rules
from tft_engine.state import GameState

from .conftest import FIXTURE_SETS


def state(**kw):
    base = dict(stage="3-2", gold=30, level=3, xp=0, hp=80, streak=0)
    base.update(kw)
    return GameState(**base)


def test_interest_is_capped(synthetic):
    r = Rules(synthetic)
    assert r.interest(9) == 0
    assert r.interest(10) == 1
    assert r.interest(49) == 4
    assert r.interest(90) == 5


def test_streak_bonus_thresholds(synthetic):
    r = Rules(synthetic)
    assert [r.streak_bonus(s) for s in (0, 1, 2, 3, 4, -5, 6, 10)] == [0, 0, 1, 1, 2, 2, 3, 3]


def test_round_income_and_streak_update(synthetic):
    r = Rules(synthetic)
    s = state(gold=34, streak=3)
    after = r.end_round(s, won=True, next_stage="3-3")
    # base 5 + interest 3 + streak(3) 1 + win 1
    assert after.gold == 34 + 10
    assert after.streak == 4
    lost = r.end_round(after, won=False, next_stage="3-5")
    assert lost.streak == -1


def test_stage_specific_base_income(synthetic):
    assert Rules(synthetic).base_income("1-2") == 2


def test_xp_levels_up_and_caps(synthetic):
    r = Rules(synthetic)
    assert r.add_xp(1, 0, 2) == (2, 0)
    assert r.add_xp(2, 3, 4) == (3, 3)
    assert r.add_xp(4, 0, 100) == (5, 0)  # max level 5, xp reset


def test_buy_xp_and_reroll_cost_gold(synthetic):
    r = Rules(synthetic)
    s = r.buy_xp(state(gold=10, level=3, xp=6))
    assert (s.gold, s.level, s.xp) == (6, 4, 2)
    assert r.reroll(state(gold=10)).gold == 7  # reroll costs 3 after the 1.2 nerf
    with pytest.raises(ValueError):
        r.reroll(state(gold=2))


def test_buy_unit_combines_stars(synthetic):
    r = Rules(synthetic)
    s = state(gold=20)
    for _ in range(9):
        s = r.buy_unit(s, "A", 1)
    assert [(u.unit_id, u.star) for u in s.units] == [("A", 3)]
    assert s.gold == 11


SYN = load_gamedata("synthetic", "1.2", root=FIXTURE_SETS)


@given(st.integers(0, 200), st.booleans(), st.integers(-8, 8))
def test_gold_never_negative_after_round(gold, won, streak):
    s = Rules(SYN).end_round(state(gold=gold, streak=streak), won, "4-1")
    assert s.gold >= gold


def test_unknown_parameter_raises_and_override_is_tracked(set18):
    r = Rules(set18)
    with pytest.raises(UnknownMechanicError):
        r.base_income("3-2")
    r2 = Rules(set18, overrides={"base_income": {"default": 5}})
    assert r2.base_income("3-2") == 5
    assert r2.used["base_income"] == "assumption"
    assert r2.streak_bonus(5) == 2
    assert r2.used["streak_gold"] == "third_party_unverified"
    r2.interest(20)
    assert r2.used["interest_cap"] == "unverified"


def test_set18_xp_table_levels_up(set18):
    r = Rules(set18)
    assert r.add_xp(1, 0, 0) == (2, 0)  # 1 -> 2 is automatic
    assert r.add_xp(2, 0, 2) == (3, 0)
    assert r.add_xp(6, 30, 6) == (7, 0)  # 6 -> 7 needs 36
    assert r.add_xp(9, 0, 500) == (10, 0)  # capped at 10
