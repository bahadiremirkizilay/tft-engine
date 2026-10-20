"""Rules with modifiers and events (B3): one value per rule, everywhere."""

from tft_engine.rules import Rules
from tft_engine.rules.modifiers import Condition, Event, Modifier, ModifierSet
from tft_engine.state import GameState


def state(**kw):
    base = dict(stage="3-2", gold=30, level=5, xp=0, hp=80, streak=0)
    base.update(kw)
    return GameState(**base)


def mods(*items):
    return ModifierSet(
        tuple(i for i in items if isinstance(i, Modifier)),
        tuple(i for i in items if isinstance(i, Event)),
    )


def test_a_cheaper_xp_purchase_reaches_buy_xp_and_is_recorded(set18):
    cheap = Modifier("upward", "DA_UpwardMobility", "xp_purchase.gold", "add", -1)
    r = Rules(set18, modifiers=mods(cheap))
    after = r.buy_xp(state(gold=10))
    assert after.gold == 7  # 4 - 1
    assert r.applied["xp_purchase"] == ("upward",)
    assert r.used["xp_purchase"] == "verified"  # the base value's status is kept


def test_a_higher_interest_cap_changes_income(set18):
    r = Rules(set18, modifiers=mods(Modifier("hedge", "DA_HedgeFund", "interest_cap", "set", 10)))
    assert r.interest(100) == 10
    assert Rules(set18).interest(100) == 5


def test_round_start_events_fire_when_the_next_round_starts(set18):
    trade = Event("trade", "DA_TradeSector", "round_start", (("gain_free_rerolls", 1),))
    r = Rules(set18, modifiers=mods(trade))
    s = r.end_round(state(), won=True, next_stage="3-3")
    s = r.end_round(s, won=False, next_stage="3-5")
    assert s.free_rerolls == 2
    assert s.fired("trade") == 2


def test_win_and_loss_events_and_stage_start(set18):
    study = (
        Event("win", "DA_PatientStudy", "after_combat_win", (("gain_xp", 2),)),
        Event("loss", "DA_PatientStudy", "after_combat_loss", (("gain_xp", 3),)),
        Event("stage", "DA_MoneyHungry", "stage_start", (("gain_gold", 7),)),
    )
    r = Rules(set18, modifiers=mods(*study))
    base = Rules(set18)
    won = r.end_round(state(stage="3-7"), won=True, next_stage="4-1")
    plain = base.end_round(state(stage="3-7"), won=True, next_stage="4-1")
    assert won.gold == plain.gold + 7  # stage 4 starts
    assert (won.level, won.xp) == base.add_xp(5, 0, 2 + 2)  # passive 2 + win 2
    lost = r.end_round(state(stage="3-2"), won=False, next_stage="3-3")
    assert (lost.level, lost.xp) == base.add_xp(5, 0, 2 + 3)


def test_level_up_events_fire_once_per_level_with_conditions(set18):
    events = (
        Event("rolls", "DA_UpwardMobility", "level_up", (("gain_free_rerolls", 2),)),
        Event(
            "nine", "DA_LateGameSpecialist", "level_up", (("gain_gold", 27),), Condition(level=9)
        ),
    )
    r = Rules(set18, modifiers=mods(*events))
    # level 5 -> 7 needs 20 + 36 XP
    s = r.gain_xp(state(level=5, gold=0), 56)
    assert s.level == 7 and s.free_rerolls == 4 and s.gold == 0
    s = r.gain_xp(state(level=8, gold=0), 68)
    assert s.level == 9 and s.gold == 27


def test_buy_xp_event_adds_xp_on_every_purchase(set18):
    level_up = Event("extra", "DA_LevelUp", "buy_xp", (("gain_xp", 2),))
    r = Rules(set18, modifiers=mods(level_up))
    s = r.buy_xp(state(level=5, gold=4))
    assert (s.level, s.xp) == Rules(set18).add_xp(5, 0, 6)


def test_limited_events_stop_after_their_limit(set18):
    growth = Event("grow", "DA_ExplosiveGrowth", "round_start", (("gain_xp", 7),), limit=2)
    r = Rules(set18, modifiers=mods(growth))
    s = state(level=3)
    for nxt in ("3-3", "3-5", "3-6"):
        s = r.end_round(s, won=True, next_stage=nxt)
    assert s.fired("grow") == 2


def test_units_and_components_are_noted_not_valued(set18):
    bag = Event("bag", "DA_BigGrabBag", "round_start", (("gain_component", 3), ("gain_gold", 2)))
    r = Rules(set18, modifiers=mods(bag))
    s = r.end_round(state(), won=True, next_stage="3-3")
    assert any("gain_component" in n for n in r.notes)
    assert s.gold == Rules(set18).end_round(state(), True, "3-3").gold + 2


def test_no_modifiers_means_the_old_rules(set18):
    a, b = Rules(set18), Rules(set18, modifiers=ModifierSet())
    s = state(gold=34, streak=4)
    assert a.end_round(s, True, "4-2") == b.end_round(s, True, "4-2")
    assert a.buy_xp(s) == b.buy_xp(s)
