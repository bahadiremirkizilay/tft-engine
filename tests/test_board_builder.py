"""Board builder: legal boards from the engine's own rules (no templates)."""

from tft_engine.decision.board_builder import BoardBuilder
from tft_engine.gamedata.entities import load_knowledge
from tft_engine.rules.items import RecipeBook, emblem_trait

from .golden_check import assert_golden

KB = load_knowledge("set18", "18.4")
B = BoardBuilder(KB)


def check_legal(r, level):
    ids = [u for u, _ in r.units]
    assert len(ids) == level and len(set(ids)) == level
    assert B.allowed(ids, level)
    for holder, emblems in r.emblem_holders.items():
        for e in emblems:  # an emblem never sits on a unit that has its trait
            assert emblem_trait(KB, e) not in KB.champions[holder]["traits"]
        assert len(emblems) + len(r.items.get(holder, [])) <= 3


def test_one_emblem_board_is_legal(update_golden):
    r = B.build(8, [RecipeBook(KB).item_id("Blossom Emblem")])
    check_legal(r, 8)
    assert r.value > 0 and r.traits
    summary = {
        "units": sorted(f"{u} {s}*" for u, s in r.units),
        "emblems": r.emblem_holders,
        "items": r.items,
        "value": r.value,
        "traits": sorted(f"{t.name} {t.count}" for t in r.traits),
    }
    assert_golden("board_blossom_8", summary, update_golden)


def test_emblem_pool_board_is_legal_and_uses_only_useful_emblems():
    pool = sorted({i["id"] for i in KB.items.values() if i["kind"] == "emblem"})
    r = B.build_with_pool(7, pool)
    check_legal(r, 7)
    used = [e for es in r.emblem_holders.values() for e in es]
    assert used and len(used) <= 3 * 7
