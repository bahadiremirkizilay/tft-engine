"""B4: recipes, active traits and item fit on the Set 18 knowledge base."""

import json
from itertools import combinations_with_replacement
from pathlib import Path

import pytest

from tft_engine.cli import main
from tft_engine.decision import Evaluator, Scenario
from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.decision.item_fit import best_items, item_fit, profile
from tft_engine.gamedata.entities import load_knowledge
from tft_engine.rules.items import RecipeBook, emblem_trait, stat_bonus
from tft_engine.rules.traits import _reached, active_traits, trait_counts

KB = load_knowledge("set18", "18.4")
BOOK = RecipeBook(KB)


def champ(name):
    return next(c["id"] for c in KB.champions.values() if c["name"] == name)


def by_name(traits):
    return {t.name: t for t in traits}


# --- recipes -------------------------------------------------------------------


def test_every_component_pair_makes_exactly_one_item():
    assert len(BOOK.components) == 10
    assert BOOK.complete
    pairs = list(combinations_with_replacement(BOOK.components, 2))
    assert len(pairs) == 55 and len(set(BOOK.recipes.values())) == 55
    kinds = {KB.items[i]["kind"] for i in BOOK.recipes.values()}
    assert kinds == {"completed", "emblem"}


def test_known_recipes_and_name_lookup():
    sword, glove = BOOK.item_id("B.F. Sword"), BOOK.item_id("sparring gloves")
    assert BOOK.name(BOOK.make(sword, glove)) == "Infinity Edge"
    assert BOOK.name(BOOK.make(sword, sword)) == "Deathblade"
    assert BOOK.recipe_of(BOOK.item_id("Infinity Edge")) == tuple(sorted((sword, glove)))
    with pytest.raises(KeyError):
        BOOK.item_id("Excalibur")


def test_options_missing_and_full_builds():
    sword, bow, tear = (
        BOOK.item_id(n) for n in ("B.F. Sword", "Recurve Bow", "Tear of the Goddess")
    )
    have = [sword, sword, bow, tear]
    names = {BOOK.name(b.item) for b in BOOK.options(have)}
    assert names == {"Deathblade", "Giant Slayer", "Spear of Shojin", "Void Staff"}
    assert BOOK.missing_for(BOOK.item_id("Infinity Edge"), have) == [
        BOOK.item_id("Sparring Gloves")
    ]
    builds = {tuple(BOOK.name(i) for i in b) for b in BOOK.full_builds(have)}
    assert builds == {("Deathblade", "Void Staff"), ("Giant Slayer", "Spear of Shojin")}
    # an odd count leaves one component out
    assert all(len(b) == 1 for b in BOOK.full_builds([sword, bow, tear]))


def test_every_emblem_names_its_trait():
    emblems = [i for i in KB.items.values() if i["kind"] == "emblem"]
    assert len(emblems) == 21
    assert all(emblem_trait(KB, e["id"]) in KB.traits for e in emblems)
    assert emblem_trait(KB, BOOK.item_id("Ravager Emblem")) == "DA_18_Slayer"


def test_stat_bonus_sums_and_keeps_the_weakest_status():
    b = stat_bonus(KB, [BOOK.item_id("Infinity Edge"), BOOK.item_id("Deathblade")])
    assert b.stats["ad_pct"] == 35 + 55 and b.stats["crit_pct"] == 35
    assert b.status == "third_party_unverified" and b.sources and not b.missing


# --- traits --------------------------------------------------------------------


def test_unique_champions_count_once():
    counts, _ = trait_counts(KB, [champ("Ahri"), champ("Ahri"), champ("Sett")])
    assert counts["DA_18_Blossom"] == 2


def test_avatar_counts_its_trait_twice():
    counts, _ = trait_counts(KB, ["DA_18_Lux_Elderwood", champ("Ornn")])
    assert counts["DA_18_Elderwood"] == 3  # Lux 2 + Ornn 1
    assert counts["DA_18_LuxUniqueTrait"] == 1
    t = by_name(active_traits(KB, counts))["Elderwood"]
    assert t.active and t.breakpoint == 3 and t.next_breakpoint == 5


def test_emblems_add_a_trait_unless_the_holder_has_it():
    blossom = BOOK.item_id("Blossom Emblem")
    counts, notes = trait_counts(KB, [champ("Ornn")], {champ("Ornn"): [blossom]})
    assert counts["DA_18_Blossom"] == 1 and not notes
    counts, notes = trait_counts(KB, [champ("Sett")], {champ("Sett"): [blossom]})
    assert counts["DA_18_Blossom"] == 1 and "adds nothing" in notes[0]
    counts, _ = trait_counts(KB, [champ("Sett")], {champ("Sett"): [blossom]}, True)
    assert counts["DA_18_Blossom"] == 2
    with pytest.raises(ValueError, match="not on the board"):
        trait_counts(KB, [champ("Sett")], {champ("Ornn"): [blossom]})


def test_breakpoint_values_follow_the_patch_overrides():
    lunar = [c["id"] for c in KB.champions.values() if "DA_18_Lunar" in c["traits"]]
    counts, _ = trait_counts(KB, lunar[:3])
    t = by_name(active_traits(KB, counts))["Lunar"]
    assert t.breakpoint == 3 and t.values["AbilityPower"] == 0.12  # 18.4 note value


def test_rows_with_the_same_minimum_are_told_apart_by_their_maximum():
    bps = [
        {"min_units": 1, "max_units": None, "values": {"a": 1}},
        {"min_units": 1, "max_units": 1, "values": {"b": 1}},
        {"min_units": 2, "max_units": None, "values": {"c": 1}},
    ]
    assert _reached(bps, 0) is None
    assert _reached(bps, 1)["values"] == {"b": 1}
    assert _reached(bps, 3)["values"] == {"c": 1}


# --- item fit ------------------------------------------------------------------


def test_profiles_come_from_ability_text_and_range():
    assert profile(KB, champ("Ahri")).tags == ("ap", "backline")
    assert profile(KB, champ("Draven")).tags == ("ad", "backline")
    assert profile(KB, champ("Sett")).tags == ("ad", "frontline")
    assert profile(KB, "DA_18_Kobuko").tags == ("tank", "frontline")  # role APTank in the export


def test_item_fit_prefers_matching_damage_and_explains_why():
    a = AssumptionSet()
    done = [i["id"] for i in KB.items.values() if i["kind"] == "completed" and i["family"] == "DA"]
    ahri = {KB.items[f.item]["name"] for f in best_items(KB, champ("Ahri"), a, done, 5)}
    assert "Rabadon's Deathcap" in ahri and "Deathblade" not in ahri
    fit = item_fit(KB, champ("Draven"), BOOK.item_id("Deathblade"), a)
    assert fit.score > 0 and fit.trust == "assumption" and any("ad_pct" in r for r in fit.reasons)
    worse = item_fit(KB, champ("Ahri"), BOOK.item_id("Deathblade"), a)
    assert worse.score < fit.score


# --- B3 link and commands ------------------------------------------------------


def test_active_traits_come_from_a_real_board():
    scen = Path(__file__).resolve().parents[1] / "scenarios" / "p1" / "n3_three_star_3cost.json"
    d = json.loads(scen.read_text(encoding="utf-8"))
    blossom = [c["id"] for c in KB.champions.values() if "DA_18_Blossom" in c["traits"]]
    blossom = [c for c in blossom if not KB.champions[c].get("variant_of")][:5]
    d["state"]["units"] = [
        {"unit_id": c, "cost": KB.champions[c]["cost"], "star": 1} for c in blossom
    ]
    ev = Evaluator(Scenario.from_dict(d))
    assert ev.active_traits["DA_18_Blossom"] == 5
    assert ev.model(ev.base).wisp_prob == 1.0  # 5 Blossom: a Wisp in every shop


def test_commands(capsys):
    args = ["--set", "set18", "--patch", "18.4"]
    assert main(["items", *args, "--have", "B.F. Sword,Sparring Gloves"]) == 0
    assert "Infinity Edge = B.F. Sword + Sparring Gloves" in capsys.readouterr().out
    assert main(["traits", *args, "--board", "Ornn,Lux (Elderwood)"]) == 0
    assert "Elderwood 3 (active at 3" in capsys.readouterr().out
    assert main(["items-for", "Ahri", *args, "--top", "3"]) == 0
    out = capsys.readouterr().out
    assert "ap, backline" in out and "trust: assumption" in out
