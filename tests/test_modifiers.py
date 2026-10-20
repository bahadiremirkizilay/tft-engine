import itertools

import pytest

from tft_engine.gamedata import UnknownMechanicError
from tft_engine.rules.modifiers import Condition, Event, Modifier, ModifierSet, build, resolve


def mod(id_, target, op, value, priority=0):
    return Modifier(id_, "test", target, op, value, priority=priority)


def test_modifiers_apply_in_a_fixed_order_whatever_order_they_were_given():
    mods = [
        mod("a", "interest_cap", "add", 2),
        mod("b", "interest_cap", "mul", 2),
        mod("c", "interest_cap", "set", 10),
        mod("d", "interest_cap", "min", 15),
    ]
    results = set()
    for perm in itertools.permutations(mods):
        value, applied = ModifierSet(tuple(perm)).apply("interest_cap", 5)
        results.add((value, applied))
    # set 10, add 2, mul 2, min 15 -> 15, always
    assert results == {(15, ("c", "a", "b", "d"))}


def test_a_modifier_can_change_one_key_of_a_table_without_touching_the_original():
    table = {"gold": 4, "xp": 4}
    value, applied = ModifierSet((mod("m", "xp_purchase.gold", "add", -1),)).apply(
        "xp_purchase", table
    )
    assert value == {"gold": 3, "xp": 4}
    assert table == {"gold": 4, "xp": 4}
    assert applied == ("m",)


def test_other_parameters_are_left_alone():
    s = ModifierSet((mod("m", "interest_cap", "set", 10),))
    assert s.apply("reroll_cost", 2) == (2, ())


def test_bad_modifiers_and_events_are_rejected():
    with pytest.raises(ValueError, match="op must be"):
        mod("x", "interest_cap", "pow", 2)
    with pytest.raises(UnknownMechanicError):
        mod("x", "interest_cap", "set", None)
    with pytest.raises(ValueError, match="on must be"):
        Event("e", "test", "sometimes", (("gain_gold", 1),))
    with pytest.raises(ValueError, match="action must be"):
        Event("e", "test", "now", (("win_game", 1),))
    with pytest.raises(ValueError, match="unique"):
        ModifierSet((mod("x", "a", "set", 1), mod("x", "b", "set", 1)))


def test_events_respect_conditions_and_limits():
    events = (
        Event("late", "t", "round_start", (("gain_gold", 1),), Condition(from_stage="4-1")),
        Event("lvl9", "t", "level_up", (("gain_gold", 27),), Condition(level=9)),
        Event("twice", "t", "round_start", (("gain_xp", 2),), limit=2),
    )
    s = ModifierSet(events=events)
    assert [e.id for e in s.firing("round_start", "3-5", 7, {})] == ["twice"]
    assert [e.id for e in s.firing("round_start", "4-1", 7, {})] == ["late", "twice"]
    assert [e.id for e in s.firing("round_start", "4-1", 7, {"twice": 2})] == ["late"]
    assert [e.id for e in s.firing("level_up", "4-1", 8, {})] == []
    assert [e.id for e in s.firing("level_up", "4-1", 9, {})] == ["lvl9"]


def test_values_come_from_the_augment_effects():
    effects = {"InstantXP": 10, "ReducedXPCost": 1, "Hashed": None}
    assert resolve({"effect": "InstantXP"}, effects, "x") == 10
    assert resolve({"effect": "ReducedXPCost", "scale": -1}, effects, "x") == -1
    assert resolve(3, effects, "x") == 3
    with pytest.raises(UnknownMechanicError):
        resolve({"effect": "Hashed"}, effects, "x")
    with pytest.raises(UnknownMechanicError):
        resolve({"effect": "Missing"}, effects, "x")


def test_build_makes_a_modifier_set_from_a_curated_model():
    model = {
        "modifiers": [
            {"target": "xp_purchase.gold", "op": "add", "value": {"effect": "Cut", "scale": -1}}
        ],
        "events": [
            {"on": "level_up", "do": {"gain_free_rerolls": {"effect": "Rerolls"}}},
            {"on": "now", "do": {"gain_gold": 2}},
        ],
    }
    s = build("DA_X", model, {"Cut": 1, "Rerolls": 2}, "community_extracted")
    assert s.apply("xp_purchase", {"gold": 4, "xp": 4})[0] == {"gold": 3, "xp": 4}
    assert [e.do for e in s.firing("level_up", "3-1", 6, {})] == [(("gain_free_rerolls", 2),)]
    assert s.events[0].status == "community_extracted"
