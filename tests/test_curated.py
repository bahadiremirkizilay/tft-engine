import json

import pytest

from tft_engine.gamedata import SchemaError
from tft_engine.gamedata.entities import check_all, load_knowledge

from .test_entities import write_generated


def curated(root, kind, records, **extra):
    d = root / "setx" / "curated" / kind
    d.mkdir(parents=True, exist_ok=True)
    (d / "1.1.json").write_text(json.dumps({"records": records, **extra}))


def test_item_stats_are_attached_with_their_sources(tmp_path):
    root = write_generated(tmp_path, "1.1")
    curated(
        root,
        "item_stats",
        [{"id": "X_Blade", "stats": {"ad_pct": 55}, "effect": "big", "source_ids": ["page"]}],
    )
    item = load_knowledge("setx", "1.1", root).items["X_Blade"]
    assert item["stats"] == {"ad_pct": 55}
    assert item["stats_source_ids"] == ["page"]
    assert item["stats_status"] == "third_party_unverified"
    assert "stats" not in load_knowledge("setx", "1.1", root, curated=False).items["X_Blade"]


@pytest.mark.parametrize(
    "rec",
    [
        {"id": "X_Nope", "stats": {}, "source_ids": ["p"]},
        {"id": "X_Blade", "stats": {"mana_per_second": 1}, "source_ids": ["p"]},
        {"id": "X_Blade", "stats": {}},
    ],
)
def test_bad_item_stats_are_errors(tmp_path, rec):
    root = write_generated(tmp_path, "1.1")
    curated(root, "item_stats", [rec])
    with pytest.raises(SchemaError):
        load_knowledge("setx", "1.1", root)


def test_tiers_go_to_every_record_with_that_name(tmp_path):
    root = write_generated(tmp_path, "1.1")
    curated(root, "augment_tiers", [{"name": "Big Bag", "tier": "gold", "source_ids": ["p"]}])
    augs = load_knowledge("setx", "1.1", root).augments
    assert augs["X_Aug"]["tier"]["value"] == "gold"
    assert augs["X_Aug_Plus"]["tier"]["value"] == "gold"
    curated(root, "augment_tiers", [{"name": "Big Bag", "tier": "bronze", "source_ids": ["p"]}])
    with pytest.raises(SchemaError):
        load_knowledge("setx", "1.1", root)


def test_override_checks_the_old_value(tmp_path):
    root = write_generated(tmp_path, "1.1")
    rec = {
        "kind": "augments",
        "id": "X_Aug",
        "field": "effects.Gold",
        "old": 2,
        "new": 3,
        "source_ids": ["notes"],
    }
    curated(root, "overrides", [rec])
    aug = load_knowledge("setx", "1.1", root).augments["X_Aug"]
    assert aug["effects"]["Gold"] == 3
    assert aug["overrides"][0]["old"] == 2
    # the export already has a different value: refuse instead of overwriting
    curated(root, "overrides", [dict(rec, old=5)])
    with pytest.raises(SchemaError, match="expected old value"):
        load_knowledge("setx", "1.1", root)
    curated(root, "overrides", [dict(rec, field="effects.Nope")])
    with pytest.raises(SchemaError, match="field not found"):
        load_knowledge("setx", "1.1", root)


def test_set18_curated_layers():
    kb, rep = check_all("set18", "18.4")
    assert rep.ok, rep.errors
    bt = kb.items["DA_Bloodthirster"]
    assert bt["stats"]["ad_pct"] == 18  # 18.2 value
    assert kb.items["DA_Artifact_StatikkShiv"]["stats"]["ap"] == 25  # 18.3 change applied
    assert kb.items["DA_SpiritVisage"]["stats"]["durability_pct"] == 10  # 18.4 change applied
    assert kb.augments["DA_LevelUp"]["effects"]["InstantXP"] == 10  # 18.4 note over game file
    assert kb.augments["DA_18_SolarTraitAugment"]["tier"]["value"] == "silver"  # 18.4 tier move
    tiers = {}
    for a in kb.augments.values():
        if isinstance(a["tier"], dict) and a["tier"]["value"] and not a.get("variant_of"):
            tiers.setdefault(a["tier"]["value"], set()).add(a["name"])
    assert {k: len(v) > 50 for k, v in tiers.items()} == {
        "silver": True,
        "gold": True,
        "prismatic": True,
    }
