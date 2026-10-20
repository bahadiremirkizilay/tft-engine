"""Set 18 augment models (curated/effects/augments.json) through the whole engine."""

import json
from collections import Counter
from pathlib import Path

import pytest

from tft_engine.decision import Evaluator, Scenario
from tft_engine.decision.effects import augment_offer
from tft_engine.gamedata.entities import load_knowledge
from tft_engine.rules import Rules
from tft_engine.rules.modifiers import build
from tft_engine.state import GameState

KB = load_knowledge("set18", "18.4")
SCEN = Path(__file__).resolve().parents[1] / "scenarios" / "p1" / "n1_roll_or_level_4_1.json"


def rules_with(set18, *ids):
    mods = [augment_offer(i, KB).modifiers for i in ids]
    out = mods[0]
    for m in mods[1:]:
        out = out.merged(m)
    return Rules(set18, modifiers=out)


def state(**kw):
    base = dict(stage="3-2", gold=30, level=5, xp=0, hp=80, streak=0)
    base.update(kw)
    return GameState(**base)


@pytest.mark.parametrize("aid", sorted(KB.augment_models))
def test_every_model_builds_from_its_augment_record(aid):
    m = KB.augment_models[aid]
    assert aid in KB.augments
    if m["model_status"] == "text_only":
        assert not m.get("events") and not m.get("modifiers")
        return
    mods = build(aid, m, KB.augments[aid]["effects"], "community_extracted")
    assert mods  # at least one modifier or event


def test_coverage_of_economy_xp_and_shop_augments():
    models = KB.augment_models.values()
    rule_changing = [m for m in models if m["category"] in ("economy", "xp", "shop")]
    status = Counter(m["model_status"] for m in rule_changing)
    assert len(rule_changing) >= 40
    # plan target: >= 90% modelled, or partial with the missing part stated
    assert (status["modelled"] + status["partial"]) / len(rule_changing) >= 0.9
    assert all(m.get("note") for m in rule_changing if m["model_status"] != "modelled")


def test_values_follow_the_patch_overrides():
    # Level Up! gives 10 XP now in 18.4 (the game file still says 6; curated override)
    offer = augment_offer("DA_LevelUp", KB)
    now = [e for e in offer.modifiers.events if e.on == "now"]
    assert now[0].do == (("gain_xp", 10),)


def test_upward_mobility_makes_xp_cheaper_everywhere(set18):
    r = rules_with(set18, "DA_UpwardMobility")
    s = r.buy_xp(state(gold=10))
    assert s.gold == 7
    # leveling up gives Health and 2 free rerolls (18.3 value)
    s = r.gain_xp(state(level=5), 20)
    assert (s.level, s.hp, s.free_rerolls) == (6, 82, 2)


def test_hedge_fund_and_hustler_change_interest(set18):
    assert rules_with(set18, "DA_HedgeFund").interest(100) == 10
    hustler = rules_with(set18, "DA_Hustler")
    assert hustler.interest(50) == 0
    after = hustler.end_round(state(gold=50), won=False, next_stage="3-3")
    plain = Rules(set18).end_round(state(gold=50), won=False, next_stage="3-3")
    assert after.gold == plain.gold - 5 + 3  # no interest, +3 at round start


def test_trade_sector_gives_a_free_reroll_each_round(set18):
    r = rules_with(set18, "DA_TradeSector")
    s = r.end_round(state(), won=True, next_stage="3-3")
    assert s.free_rerolls == 1


def test_explosive_growth_stops_after_its_rounds(set18):
    r = rules_with(set18, "DA_ExplosiveGrowth")
    s = state(level=3, stage="2-1")
    for nxt in ("2-2", "2-3", "2-5", "2-6", "2-7"):
        s = r.end_round(s, won=True, next_stage=nxt)
    assert (
        s.fired("DA_ExplosiveGrowth:round_start:1")
        == KB.augments["DA_ExplosiveGrowth"]["effects"]["rounds"]
    )


def test_real_augment_offers_are_ranked_in_a_scenario():
    d = json.loads(SCEN.read_text(encoding="utf-8"))
    d["augment_offers"] = [
        {"augment": "DA_LevelUp"},
        {"augment": "DA_TradeSector"},
        {"augment": "DA_TimeSkip"},
    ]
    rows = Evaluator(Scenario.from_dict(d)).augments()
    by_id = {r.offer_id.split(" ")[0]: r for r in rows}
    assert by_id["DA_LevelUp"].evaluated and by_id["DA_TradeSector"].evaluated
    assert not by_id["DA_TimeSkip"].evaluated  # text_only, and it says why
    assert by_id["DA_TimeSkip"].notes


def test_owned_augments_change_every_candidate():
    d = json.loads(SCEN.read_text(encoding="utf-8"))
    plain = Evaluator(Scenario.from_dict(d)).evaluate()
    d["state"]["augments"] = ["DA_UpwardMobility"]
    owned = Evaluator(Scenario.from_dict(d)).evaluate()
    b_plain, b_owned = plain.by_key("B"), owned.by_key("B")
    if b_plain.available and b_owned.available:
        # leveling costs less gold with the owned augment
        assert (
            b_owned.metrics["gold_after_action"].value > b_plain.metrics["gold_after_action"].value
        )
    assert any("xp_purchase changed by DA_UpwardMobility" in n for n in owned.notes)


def test_wisp_rebate_pays_back_when_buying_a_wisp(set18):
    r = rules_with(set18, "DA_18_WispRebatePlus")
    s = r.fire("wisp_bought", state(gold=10))
    assert s.gold == 12


def test_data_augments_command_prints_the_coverage(capsys):
    from tft_engine.cli import main

    assert main(["data", "augments", "--set", "set18", "--patch", "18.4", "--list"]) == 0
    out = capsys.readouterr().out
    assert "with a model" in out and "modelled" in out
    assert "[text_only] Time Skip" in out
