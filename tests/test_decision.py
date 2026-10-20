import json
import math
import time
from pathlib import Path

import pytest

from tft_engine.cli import main
from tft_engine.decision import DEFAULTS, AssumptionSet, Effect, Evaluator, Scenario, load_scenario
from tft_engine.decision.effects import combine
from tft_engine.decision.horizon import next_stage
from tft_engine.state import UnitInstance

SCEN_DIR = Path(__file__).resolve().parents[1] / "scenarios" / "p1"
PATHS = sorted(SCEN_DIR.glob("*.json"))
TRUST = {"exact", "data_estimated", "assumption"}


def test_at_least_ten_scenarios_and_five_obvious():
    scs = [load_scenario(p) for p in PATHS]
    assert len(scs) >= 10
    assert sum(1 for s in scs if s.expected) >= 5


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.stem)
def test_every_scenario_runs_with_trust_labels_in_time(path):
    sc = load_scenario(path)
    t0 = time.perf_counter()
    ev = Evaluator(sc)
    result = ev.evaluate()
    ev.sensitivity(result)
    ev.augments()
    assert time.perf_counter() - t0 < 10.0  # plan target: <= 10 s per scenario
    assert result.ranked, "at least one candidate must be available"
    for c in result.candidates:
        if not c.available:
            assert c.reason
            continue
        assert math.isfinite(c.score)
        assert c.metrics and all(m.trust in TRUST for m in c.metrics.values())
        if "p_hit" in c.metrics:
            assert c.metrics["p_hit"].trust == "exact"
            assert 0.0 <= c.metrics["p_hit"].value <= 1.0
        assert 0.0 <= c.metrics["p_elim"].value <= 1.0


OBVIOUS = [p for p in PATHS if load_scenario(p).expected]


@pytest.mark.parametrize("path", OBVIOUS, ids=lambda p: p.stem)
def test_obvious_scenarios_pick_the_obvious_side(path):
    sc = load_scenario(path)
    assert Evaluator(sc).evaluate().best.key in sc.expected["best_in"]


def test_same_input_same_output():
    sc = load_scenario(SCEN_DIR / "n1_roll_or_level_4_1.json")
    a = Evaluator(sc).evaluate()
    b = Evaluator(sc).evaluate()
    assert [(c.key, c.score) for c in a.candidates] == [(c.key, c.score) for c in b.candidates]


def _many_targets_scenario():
    d = json.loads((SCEN_DIR / "o2_nothing_to_hit_early.json").read_text(encoding="utf-8"))
    d["comps"][0]["units"] = [
        {"unit_id": f"2u{i}", "cost": 2, "star": 2} for i in range(4)
    ]  # 4 targets -> Monte Carlo path
    return Scenario.from_dict(d)


def test_monte_carlo_path_is_seeded():
    sc = _many_targets_scenario()
    a = Evaluator(sc).evaluate().by_key("A")
    b = Evaluator(sc).evaluate().by_key("A")
    assert a.roll.method == "monte_carlo"
    assert a.metrics["p_hit"].value == b.metrics["p_hit"].value
    assert "CI" in a.metrics["p_hit"].note


def test_no_copies_left_means_no_hit():
    sc = load_scenario(SCEN_DIR / "o3_carry_fully_contested.json")
    assert Evaluator(sc).evaluate().by_key("A").metrics["p_hit"].value == 0.0


def test_contest_prior_lowers_hit_chance():
    d = json.loads((SCEN_DIR / "n1_roll_or_level_4_1.json").read_text(encoding="utf-8"))
    with_prior = Evaluator(Scenario.from_dict(d)).evaluate().by_key("A")
    d["contest_prior"] = {}
    without = Evaluator(Scenario.from_dict(d)).evaluate().by_key("A")
    assert with_prior.metrics["p_hit"].value < without.metrics["p_hit"].value


def test_sensitivity_covers_every_varied_assumption():
    sc = load_scenario(SCEN_DIR / "o5_pivot_off_contested.json")
    ev = Evaluator(sc)
    rows = ev.sensitivity()
    assert {r.name for r in rows} == {k for k, a in DEFAULTS.items() if a.varied}
    assert rows[0].flips or rows[0].regret == max(r.regret for r in rows)


def test_augments_rank_evaluable_offers_and_flag_the_rest():
    sc = load_scenario(SCEN_DIR / "n2_augment_offers.json")
    rows = Evaluator(sc).augments()
    by_id = {r.offer_id: r for r in rows}
    assert not by_id["example_attack_speed"].evaluated
    assert by_id["example_gold_now"].evaluated and by_id["example_free_unit"].evaluated
    assert rows[-1].offer_id == "example_attack_speed"


def test_unknown_assumption_rejected():
    with pytest.raises(KeyError):
        AssumptionSet({"magic": 1})


def test_effect_validation():
    with pytest.raises(ValueError):
        Effect("x", "combat", "src", "synthetic", gold_now=3)
    with pytest.raises(ValueError):
        Effect.from_dict(
            {"id": "x", "type": "economy", "source": "s", "status": "synthetic", "hp": 1}
        )
    with pytest.raises(ValueError):
        Effect("x", "economy", " ", "synthetic")


def test_scenario_rejects_unit_with_two_costs():
    d = json.loads((SCEN_DIR / "o1_one_copy_from_3star.json").read_text(encoding="utf-8"))
    d["comps"][0]["units"][0]["cost"] = 2
    with pytest.raises(ValueError):
        Scenario.from_dict(d)


def test_combine_merges_three_copies():
    units = (UnitInstance("1a", 1), UnitInstance("1a", 1), UnitInstance("1a", 1))
    assert combine(units) == (UnitInstance("1a", 1, 2),)


def test_next_stage():
    assert next_stage("3-2") == "3-3"
    assert next_stage("3-7") == "4-1"


def test_decide_command(capsys):
    assert main(["decide", str(SCEN_DIR / "o1_one_copy_from_3star.json")]) == 0
    out = capsys.readouterr().out
    assert "Motorun tercihi: [A]" in out
    assert "UYUMLU" in out


def test_free_rerolls_in_the_state_raise_the_hit_chance():
    d = json.loads((SCEN_DIR / "n1_roll_or_level_4_1.json").read_text(encoding="utf-8"))
    plain = Evaluator(Scenario.from_dict(d)).evaluate().by_key("A")
    d["state"]["free_rerolls"] = 5
    free = Evaluator(Scenario.from_dict(d)).evaluate().by_key("A")
    assert free.metrics["p_hit"].value > plain.metrics["p_hit"].value


def _n3(**changes):
    d = json.loads((SCEN_DIR / "n3_three_star_3cost.json").read_text(encoding="utf-8"))
    d.update(changes)
    return d


def test_buying_a_wisp_first_is_tried_and_can_win():
    # Rolling for a 3-star with a Wisp costing nothing: buying it frees the slot.
    d = _n3(assumptions={"wisp_price": 0})
    a = Evaluator(Scenario.from_dict(d)).evaluate().by_key("A")
    assert "buying a Wisp first" in a.label
    assert a.roll.model == "independent+wisp_bought"
    # With 5 Blossom every shop shows a Wisp; never buying one loses a slot each shop.
    d = _n3(assumptions={"wisp_price": 0}, active_traits={"DA_18_Blossom": 5})
    ev = Evaluator(Scenario.from_dict(d))
    never = ev._roll_policy(
        "A", "x", ev.sc.state, ev.sc.comp(ev.sc.current_comp), ev_rules(ev), ev.base, False
    )
    bought = ev.evaluate().by_key("A")
    assert bought.metrics["p_hit"].value > never.metrics["p_hit"].value


def ev_rules(ev):
    from tft_engine.rules import Rules

    return Rules(ev.data)


def test_lux_form_share_comes_from_the_knowledge_base():
    from tft_engine.state import GameState

    d = _n3()
    d["comps"][0]["units"] = [{"unit_id": "DA_18_Lux_Elderwood", "cost": 5, "star": 1}]
    ev = Evaluator(Scenario.from_dict(d))
    nobody = GameState("4-3", 50, 8, 0, 50)
    assert ev._share("DA_18_Lux_Elderwood", nobody) == pytest.approx(1 / 9)
    coven = GameState("4-3", 50, 8, 0, 50, units=(UnitInstance("DA_18_Lux_Coven", 5, 1),))
    # an owned form locks the shop form: other forms cannot show until it is sold
    assert ev._share("DA_18_Lux_Elderwood", coven) == 0.0
    assert ev._share("DA_18_Lux_Coven", coven) == 1.0
    assert ev._share("3echo", nobody) == 1.0
