"""B6 first step: unit stats with traits and items, and board power from them."""

import pytest

from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.decision.board_power import board_power, unit_power
from tft_engine.gamedata import load_gamedata
from tft_engine.gamedata.entities import load_knowledge
from tft_engine.rules.board_stats import BoardStats, check_trait_models, load_trait_models
from tft_engine.rules.items import RecipeBook

KB = load_knowledge("set18", "18.5")
DATA = load_gamedata("set18", "18.5")
BS = BoardStats(KB, DATA)
BOOK = RecipeBook(KB)


def cid(name):
    return next(
        c["id"] for c in KB.champions.values() if c["name"] == name and not c.get("variant_of")
    )


def stats_of(units, items=None, emblems=None):
    out, traits = BS.compute(units, items, emblems)
    return {s.unit: s for s in out}, {t.name: t for t in traits}


def test_every_trait_model_names_real_values():
    models = load_trait_models("set18")
    assert len(models) == len(KB.traits)
    assert check_trait_models(KB, models) == []


def test_star_multipliers_follow_the_data():
    one, _ = stats_of([(cid("Sett"), 1)])
    two, _ = stats_of([(cid("Sett"), 2)])
    sett = KB.champions[cid("Sett")]["stats"]
    assert one[cid("Sett")].hp == pytest.approx(sett["hp"])
    assert two[cid("Sett")].hp == pytest.approx(sett["hp"] * 1.8)
    assert two[cid("Sett")].ad == pytest.approx(sett["damage"] * 1.5)


def test_brawler_and_defender_values_reach_the_right_units():
    brawlers = [c["id"] for c in KB.champions.values() if "DA_18_Brawler" in c["traits"]][:2]
    other = cid("Ahri")
    st, traits = stats_of([(u, 1) for u in brawlers] + [(other, 1)])
    assert traits["Brawler"].count == 2
    team_hp = traits["Brawler"].values["BrawlerTeamHealth"]
    pct = traits["Brawler"].values["BrawlerHealthPercent"]
    ahri = KB.champions[other]["stats"]["hp"]
    assert st[other].hp == pytest.approx(ahri + team_hp)  # team part only
    b = KB.champions[brawlers[0]]["stats"]["hp"]
    assert st[brawlers[0]].hp == pytest.approx((b + team_hp) * (1 + pct))
    defenders = [c["id"] for c in KB.champions.values() if "DA_18_Defender" in c["traits"]][:2]
    st, traits = stats_of([(u, 1) for u in defenders] + [(other, 1)])
    gain = traits["Defender"].values
    assert st[other].armor == KB.champions[other]["stats"]["armor"] + gain["NonDefenderDefenseGain"]
    d0 = defenders[0]
    assert st[d0].armor == KB.champions[d0]["stats"]["armor"] + gain["DefenderDefenseGain"]


def test_items_add_their_stats_and_raise_damage():
    ahri = cid("Ahri")
    plain = board_power(BS, [(ahri, 2)])
    deathcap = BOOK.item_id("Rabadon's Deathcap")
    itemized = board_power(BS, [(ahri, 2)], {ahri: [deathcap]})
    ap = KB.items[deathcap]["stats"]["ap"]
    assert itemized.stats[0].ap == pytest.approx(100 + ap)
    assert itemized.dps > plain.dps and itemized.power > plain.power


def test_board_power_grows_with_stars_and_needs_both_halves():
    units = [(cid(n), 1) for n in ("Sett", "Ahri", "Ornn", "Karma")]
    one = board_power(BS, units)
    two = board_power(BS, [(u, 2) for u, _ in units])
    assert two.power > one.power
    assert one.power == pytest.approx((one.dps * one.ehp) ** 0.5)


# --- ability records (18.5, Blitz pastes) ---------------------------------------------


def ability_values(cid, index=0, form=None):
    rec = KB.ability(cid)
    parts = rec["forms"][form]["parts"] if form else rec["parts"]
    return parts[index]["values"]


def test_every_champion_has_an_ability_record_and_lux_forms_share_it():
    for c in KB.champions.values():
        assert KB.ability(c["id"]) is not None, c["name"]
    assert KB.ability(cid("Lux")) is KB.ability("DA_18_Lux_Fae")
    assert load_knowledge("set18", "18.4").abilities == {}


def test_records_match_the_18_5_note_changes():
    # new values from the official 18.5 notes (1-star / 2-star)
    assert ability_values(cid("Morgana"))[:2] == [70, 105]
    assert ability_values(cid("Malphite"))[:2] == [735, 885]
    assert ability_values(cid("Soraka"), 0)[:2] == [235, 355]
    assert ability_values(cid("Soraka"), 1)[:2] == [110, 165]
    assert ability_values(cid("Azir")) == [43, 65, 105]
    assert ability_values(cid("Kha'Zix")) == [250, 345, 500]
    assert ability_values(cid("Taric"), 1)[:2] == [130, 200]


def test_board_power_uses_records_on_18_5_and_the_stand_in_before():
    bp = board_power(BS, [(cid("Ahri"), 1)])
    assert bp.units[0].source == "record"
    kb4 = load_knowledge("set18", "18.4")
    bs4 = BoardStats(kb4, load_gamedata("set18", "18.4"))
    assert board_power(bs4, [(cid("Ahri"), 1)]).units[0].source == "stand-in"


def test_ability_damage_scales_with_ap_and_ad():
    a = AssumptionSet()
    ahri = cid("Ahri")
    plain, _ = BS.compute([(ahri, 1)])
    more_ap, _ = BS.compute([(ahri, 1)], {ahri: [BOOK.item_id("Rabadon's Deathcap")]})
    p0 = unit_power(KB, plain[0], a)
    p1 = unit_power(KB, more_ap[0], a)
    assert p1.dps > p0.dps
    varus = cid("Varus")
    plain, _ = BS.compute([(varus, 1)])
    more_ad, _ = BS.compute([(varus, 1)], {varus: [BOOK.item_id("Infinity Edge")]})
    assert unit_power(KB, more_ad[0], a).dps > unit_power(KB, plain[0], a).dps


def test_adaptor_forms():
    nid = cid("Nidalee")
    bp = board_power(BS, [(nid, 1)])
    assert bp.stats[0].form == "ad"  # owner plays Nidalee AD (assumption)
    assert bp.stats[0].hp == pytest.approx(1100)  # cougar stats from the record
    gromp = cid("Gromp")
    assert board_power(BS, [(gromp, 1)]).stats[0].form == "ap"
    kog = cid("Kog'Maw")
    with_ap = board_power(BS, [(kog, 2)], {kog: [BOOK.item_id("Rabadon's Deathcap")] * 2})
    with_ad = board_power(BS, [(kog, 2)], {kog: [BOOK.item_id("Infinity Edge")] * 2})
    assert with_ap.stats[0].form == "ap"
    assert with_ad.stats[0].form == "ad"
