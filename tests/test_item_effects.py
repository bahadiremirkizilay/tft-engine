"""Item special effects (18.5): stacks with caps, Precision, Shred/Sunder, roles, item picks."""

import pytest

from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.decision.board_builder import BoardBuilder
from tft_engine.decision.board_power import board_power, unit_power
from tft_engine.decision.item_effects import ItemExtras
from tft_engine.gamedata import load_gamedata
from tft_engine.gamedata.entities import load_knowledge
from tft_engine.rules.board_stats import BoardStats
from tft_engine.rules.items import RecipeBook

KB = load_knowledge("set18", "18.5")
BS = BoardStats(KB, load_gamedata("set18", "18.5"))
BOOK = RecipeBook(KB)
A = AssumptionSet()
T = A["power_fight_seconds"]


def cid(name):
    return next(
        c["id"] for c in KB.champions.values() if c["name"] == name and not c.get("variant_of")
    )


def item(name):
    return BOOK.item_id(name)


def as_of(unit, items):
    return board_power(BS, [(unit, 2)], {unit: [item(n) for n in items]}).stats[0].attack_speed


def test_every_completed_item_with_stats_has_an_effect_record():
    for i in KB.items.values():
        if i.get("family") == "DA" and i["kind"] == "completed" and i.get("stats"):
            assert i["id"] in KB.item_effects, i["name"]


def test_guinsoo_stacks_without_a_cap_and_kraken_stops_at_15():
    aph = cid("Aphelios")
    base = KB.champions[aph]["stats"]["attackSpeed"]
    guinsoo = KB.items[item("Guinsoo's Rageblade")]["stats"]["as_pct"] / 100
    # +7% per second, no cap: the fight average is 7% x half the fight
    assert as_of(aph, ["Guinsoo's Rageblade"]) == pytest.approx(
        base * (1 + guinsoo + 0.07 * T / 2), rel=0.01
    )
    kraken = board_power(BS, [(aph, 2)], {aph: [item("Kraken's Fury")]}).stats[0]
    plain = board_power(BS, [(aph, 2)]).stats[0]
    bonus_ad = kraken.ad / plain.ad - 1 - KB.items[item("Kraken's Fury")]["stats"]["ad_pct"] / 100
    assert 0 < bonus_ad <= 15 * 0.035 + 1e-9


def test_last_whisper_sunders_and_physical_damage_gains():
    aph = cid("Aphelios")
    lw = board_power(BS, [(aph, 2)], {aph: [item("Last Whisper")]})
    assert lw.team.reduce_armor == pytest.approx(0.30)
    # same stats without the Sunder: compare the physical damage after enemy Armor
    raw = lw.units[0].physical
    armor = A["power_enemy_armor"]
    assert lw.units[0].dps == pytest.approx(
        raw * 100 / (100 + armor * 0.7) + lw.units[0].magic * 100 / (100 + A["power_enemy_mr"]),
        rel=1e-6,
    )


def test_precision_lets_ability_damage_crit():
    ez = cid("Ezreal")
    st = BS.compute([(ez, 2)])[0][0]
    plain = unit_power(KB, st, A)
    precise = unit_power(KB, st, A, ex=ItemExtras(precision=1))
    assert precise.dps > plain.dps
    assert precise.dps - plain.dps < plain.dps  # only the ability part grows


def test_adaptive_helm_depends_on_role():
    tank, carry = cid("Sentinel"), cid("Ahri")
    helm = [item("Adaptive Helm")]
    st = board_power(BS, [(tank, 1), (carry, 1)], {tank: helm, carry: helm}).stats
    base = board_power(BS, [(tank, 1), (carry, 1)]).stats
    item_mr = KB.items[item("Adaptive Helm")]["stats"]["mr"]
    assert st[0].armor - base[0].armor == pytest.approx(30)
    assert st[0].mr - base[0].mr == pytest.approx(30 + item_mr)
    assert st[1].ap - base[1].ap == pytest.approx(10)


def test_builder_picks_items_by_power_without_copies():
    b = BoardBuilder(KB)
    board = [cid(n) for n in ("Aphelios", "Sentinel", "Diana", "Kog'Maw", "Mama Beak")]
    items, notes = b.assign_items(board, 8, {})
    picked = [i for v in items.values() for i in v]
    assert len(picked) == len(set(picked)) == 8
    assert item("Thief's Gloves") not in picked
    assert notes[0].startswith("main carry")
