"""B5: comp templates, meta statistics, comp matching and item trios."""

import json

import pytest

from tft_engine.cli import main
from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.decision.comp_match import best_trio, match_comps, missing_components
from tft_engine.gamedata import SchemaError
from tft_engine.gamedata.entities import load_knowledge
from tft_engine.gamedata.sources import load_sources
from tft_engine.rules.comps import check_comps, load_comps
from tft_engine.rules.items import RecipeBook

KB = load_knowledge("set18", "18.4")
COMPS = load_comps("set18", "18.4")
BOOK = RecipeBook(KB)
A = AssumptionSet()


def item(name):
    return BOOK.item_id(name)


def test_templates_and_meta_load_and_link():
    assert len(COMPS.templates) >= 3
    assert check_comps(KB, COMPS, load_sources()) == []
    stats = COMPS.comp_stats("set18-18.4-riftbeast-pebbles-krug")
    # every number carries the site, rank filter, patch and definition (plan rule 10)
    assert stats and all(stats[0][k] for k in ("site", "rank_filter", "patch", "definition"))


def test_bad_references_are_reported():
    bad = load_comps("set18", "18.4")
    t = json.loads(json.dumps(bad.templates["set18-18.4-sprykin-azir-rammus"]))
    t["units"].append({"id": "DA_18_Nobody", "role": "core"})
    t["pivots"] = ["set18-18.4-missing"]
    bad.templates["x"] = t
    errors = check_comps(KB, bad, load_sources())
    assert any("unknown champion DA_18_Nobody" in e for e in errors)
    assert any("pivot to unknown comp" in e for e in errors)


def test_meta_files_need_their_context(tmp_path):
    folder = tmp_path / "setx" / "curated" / "meta" / "1.1"
    folder.mkdir(parents=True)
    (folder / "site.json").write_text(json.dumps({"site": "x", "patch": "1.1", "comps": []}))
    with pytest.raises(SchemaError, match="missing"):
        load_comps("setx", "1.1", root=tmp_path)


def test_missing_components_counts_held_items_and_components():
    build = [item("Hextech Gunblade"), item("Void Staff"), item("Giant Slayer")]
    have = [item(n) for n in ("Needlessly Large Rod", "Recurve Bow", "Tear of the Goddess")]
    miss = missing_components(BOOK, build, have, held=[item("Hextech Gunblade")])
    assert sorted(BOOK.name(c) for c in miss) == ["B.F. Sword", "Recurve Bow"]


def test_owned_units_and_components_rank_the_matching_comp_first():
    owned = [KB.champion_by_name("Krug")["id"], KB.champion_by_name("Pebbles")["id"]]
    have = [item("Needlessly Large Rod"), item("Recurve Bow")]
    ranked = match_comps(KB, COMPS, owned, have, A, BOOK)
    top = ranked[0]
    assert top.comp_id == "set18-18.4-riftbeast-pebbles-krug"
    assert len(top.owned) == 2 and top.item_uses and top.trust == "assumption"
    assert top.stats[0]["avg_place"] == 4.14  # shown apart from the score


def test_trio_uses_known_builds_first_then_rules():
    have = [item(n) for n in ("Needlessly Large Rod", "Recurve Bow", "Tear of the Goddess")]
    pebbles = best_trio(KB, COMPS, KB.champion_by_name("Pebbles")["id"], have, A, book=BOOK)
    assert pebbles[0].basis.startswith("meta: tactics.tools")
    rods = [item("Needlessly Large Rod")] * 2 + [item("Tear of the Goddess")] * 2
    # Alune has no known build: rule-based options
    alune = best_trio(KB, COMPS, KB.champion_by_name("Alune")["id"], rods, A, book=BOOK)
    assert alune[0].basis == "rule" and alune[0].score > 0
    assert len(alune[0].items) == 3
    ahri = best_trio(KB, COMPS, KB.champion_by_name("Ahri")["id"], rods, A, book=BOOK)
    assert ahri[0].basis.startswith("template ")  # TFT Academy build


def test_commands(capsys):
    args = ["--set", "set18", "--patch", "18.4"]
    assert main(["comps", *args, "--units", "Krug,Pebbles", "--have", "Recurve Bow"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("Riftbeast Reroll")
    assert "tier A (TFT Academy)" in out
    assert "site stats (tactics.tools 18.4b Diamond+)" in out
    assert main(["trio", "Pebbles", *args, "--have", "Needlessly Large Rod,Recurve Bow"]) == 0
    assert "missing:" in capsys.readouterr().out


def test_owned_units_beat_a_single_matching_component():
    # 3 Azir-comp units and one Rod: the Rod suits a Riftbeast carry, but units decide
    owned = [KB.champion_by_name(n)["id"] for n in ("Azir", "Teemo", "Veigar")]
    ranked = match_comps(KB, COMPS, owned, [item("Needlessly Large Rod")], A, BOOK)
    assert ranked[0].comp_id == "set18-18.4-sprykin-azir-rammus"
    assert ranked[0].items_known  # Azir's items from the TFT Academy page
    assert any("Azir" in use for use in ranked[0].item_uses)  # the Rod goes to Azir
    assert ranked[0].tiers[0]["tier"] == "S" and "opinion" in ranked[0].tiers[0]["definition"]


def test_templates_carry_guide_plans():
    t = COMPS.templates["set18-18.4-sprykin-azir-rammus"]
    stars = {u["id"]: u.get("star") for u in t["units"]}
    assert stars["DA_18_Azir"] == 3 and t["reroll_cost"] == 3
    assert any(p.get("level") == 7 for p in t["level_plan"])


def test_tftacademy_templates_are_complete_enough():
    assert len(COMPS.templates) >= 12
    for t in COMPS.templates.values():
        assert t["carry_items"], t["id"]
        assert all(len(b) == 3 for c in t["carry_items"] for b in c["builds"]), t["id"]
        assert len(t["item_priority"]) == 4 and t["level_plan"], t["id"]
    situational = [t for t in COMPS.templates.values() if t.get("situational")]
    assert {t["id"] for t in situational} == {
        "set18-18.4-coven-elise",
        "set18-18.4-bronze-for-life-ahri",
    }


def test_owner_corrections_are_in_the_templates():
    t = COMPS.templates
    azir = {u["id"]: u for u in t["set18-18.4-sprykin-azir-rammus"]["units"]}
    assert azir["DA_18_Teemo"].get("star_optional") and not azir["DA_18_Azir"].get("star_optional")
    solar = [u for u in t["set18-18.4-solar-karma-reroll"]["units"] if u.get("star") == 3]
    assert len(solar) == 5  # the Solar bonus needs five 3-star units
    util = t["set18-18.4-ahri-morgana"]["utility_items"][0]
    assert util["unit"] == "DA_18_Morgana" and len(util["items"]) == 2
