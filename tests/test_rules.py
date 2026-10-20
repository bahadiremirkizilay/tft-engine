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
    # base 5 + interest 3 + streak(4, after this win) 2 + win 1
    assert after.gold == 34 + 11
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
    with pytest.raises(UnknownMechanicError):
        set18.shop_rules["bad_luck_protection"].get()
    r2 = Rules(set18, overrides={"base_income": {"default": 4}})
    assert r2.base_income("3-2") == 4
    assert r2.used["base_income"] == "assumption"
    assert r2.streak_bonus(5) == 2
    assert r2.used["streak_gold"] == "third_party_unverified"
    r2.interest(20)
    assert r2.used["interest_cap"] == "third_party_unverified"


def test_set18_xp_table_levels_up(set18):
    r = Rules(set18)
    assert r.add_xp(1, 0, 0) == (2, 0)  # 1 -> 2 is automatic
    assert r.add_xp(2, 0, 2) == (3, 0)
    assert r.add_xp(6, 30, 6) == (7, 0)  # 6 -> 7 needs 36
    assert r.add_xp(9, 0, 500) == (10, 0)  # capped at 10


def test_set18_round_income_win_and_loss_streaks(set18):
    r = Rules(set18)
    assert r.base_income("1-3") == 2 and r.base_income("2-1") == 4 and r.base_income("4-2") == 5
    # 34 gold, 4-round win streak, wins again: base 5 + interest 3 + streak(5) 2 + win 1
    won = r.end_round(state(gold=34, streak=4), won=True, next_stage="4-2")
    assert (won.gold, won.streak) == (45, 5)
    # same gold on a 4-round loss streak, loses again: base 5 + interest 3 + streak(5) 2
    lost = r.end_round(state(gold=34, streak=-4), won=False, next_stage="4-2")
    assert (lost.gold, lost.streak) == (44, -5)
    # owner (18.4b): a 2-round streak pays nothing, 3 pays +1, 6 pays +3
    assert [r.streak_bonus(n) for n in (1, 2, 3, 4, 5, 6, -2, -3)] == [0, 0, 1, 1, 2, 3, 0, 1]


def test_set18_sell_values_follow_the_recorded_rule(set18):
    r = Rules(set18)
    assert r.sell_value(1, 1) == 1 and r.sell_value(1, 2) == 3  # 1-cost: full refund
    assert r.sell_value(4, 1) == 4 and r.sell_value(4, 2) == 11  # 2-star 4-cost: 12 - 1
    assert r.used["sell_value"] == "third_party_unverified"
    with pytest.raises(ValueError):
        r.sell_value(6, 1)


def test_selling_a_unit_returns_gold(set18):
    from tft_engine.state import UnitInstance

    r = Rules(set18)
    s = state(gold=10, units=(UnitInstance("Sett", 4, 2), UnitInstance("Akali", 1, 1)))
    after = r.sell_unit(s, "Sett", 2)
    assert after.gold == 21 and [u.unit_id for u in after.units] == ["Akali"]
    with pytest.raises(ValueError):
        r.sell_unit(s, "Sett", 1)


def test_set18_player_damage(set18):
    r = Rules(set18)
    assert r.player_damage(4, 3) == 11
    assert r.player_damage(2, 0) == 2
    with pytest.raises(ValueError):
        r.player_damage(9, 1)
