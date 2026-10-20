"""Normalization of a CommunityDragon export, on a small made-up export (not TFT)."""

import copy
import json

import pytest

from tft_engine.gamedata import SchemaError
from tft_engine.gamedata.cdragon import classify_item, normalize, summary
from tft_engine.gamedata.hashes import hash_key

RULES = {
    "mutator": "TFTSetX",
    "champions": {
        "api_prefixes": ["X_"],
        "require_traits": True,
        "variant_groups": [{"trait": "X_Avatar", "base": "X_Lux"}],
    },
    "item_kinds": [
        {"kind": "component", "tag": "component"},
        {"kind": "wisp", "tag": "{aaaaaaaa}"},
        {"kind": "emblem", "tag": hash_key("TraitItem"), "tag_name": "TraitItem"},
        {"kind": "completed", "composition_len": 2},
        {"kind": "other"},
    ],
}


def champ(api, name, cost, traits, variables=()):
    return {
        "apiName": api,
        "name": name,
        "cost": cost,
        "traits": traits,
        "role": None,
        "stats": {"hp": 600.0, "armor": 40.0, "attackSpeed": 0.550000011920929},
        "ability": {"name": "A", "desc": "d", "variables": list(variables)},
    }


def item(api, name, tags=(), comp=(), effects=None, desc="", augment=False):
    return {
        "apiName": api,
        "name": name,
        "tags": list(tags),
        "composition": list(comp),
        "effects": effects or {},
        "desc": desc,
        "isAugment": augment,
        "unique": False,
        "associatedTraits": [],
        "incompatibleTraits": [],
    }


RAW = {
    "setData": [
        {
            "mutator": "TFTSetX",
            "number": 99,
            "traits": [
                {
                    "apiName": "X_Brawler",
                    "name": "Brawler",
                    "desc": "Gain @BrawlerTeamHealth@ and @BrawlerHealthPercent*100@%",
                    "effects": [
                        {
                            "minUnits": 2,
                            "maxUnits": 3,
                            "style": 1,
                            "variables": {
                                hash_key("BrawlerTeamHealth"): 120.0,
                                hash_key("BrawlerHealthPercent"): 0.4000000059604645,
                                "{12345678}": 1.0,
                            },
                        },
                        {"minUnits": 4, "maxUnits": 25000, "style": 3, "variables": {}},
                    ],
                },
                {"apiName": "X_Avatar", "name": "Avatar", "desc": "", "effects": []},
            ],
            "champions": [
                champ("X_Sett", "Sett", 4, ["Brawler"]),
                champ("X_Lux", "Lux", 5, ["Avatar"], [{"name": "Damage", "value": [1.0, 2.0]}]),
                champ("X_Lux_Fire", "Lux (Fire)", 5, ["Avatar", "Brawler"]),
                champ("TFT_Golem", "Golem", 1, []),
                champ("X_Dummy", "Dummy", 8, []),
            ],
            "items": [
                "X_Sword",
                "X_Vest",
                "X_Blade",
                "X_Emblem",
                "X_Charm",
                "X_Charm_Up",
                "X_Junk",
            ],
            "augments": ["X_Aug", "X_Aug_Plus"],
        }
    ],
    "items": [
        item("X_Sword", "Sword", ["component"]),
        item("X_Vest", "Vest", ["component"]),
        item("X_Blade", "Blade", ["{7ea41d13}"], ["X_Sword", "X_Sword"]),
        item("X_Emblem", "Brawler Emblem", [hash_key("TraitItem")], ["X_Sword", "X_Vest"]),
        item("X_Charm", "Drizzle", ["{aaaaaaaa}"], effects={"Mana": 10.0}, desc="@Mana@"),
        item("X_Charm_Up", "Drizzle", ["{aaaaaaaa}"], effects={"Mana": 20.0}, desc="@Mana@"),
        item("X_Junk", "Junk"),
        item("X_Aug", "Big Bag", effects={hash_key("Gold"): 2.0}, desc="@Gold@ gold", augment=True),
        item("X_Aug_Plus", "Big Bag", effects={"Gold": 4.0}, desc="@Gold@ gold", augment=True),
    ],
}


def run(raw=RAW, rules=RULES):
    return normalize(copy.deepcopy(raw), rules, "setx", "1.1", "cdragon-test")


def test_only_playable_champions_with_trait_ids():
    recs = run()
    ids = [c["id"] for c in recs["champions"]]
    assert ids == ["X_Lux", "X_Lux_Fire", "X_Sett"]  # monsters, dummies dropped
    sett = next(c for c in recs["champions"] if c["id"] == "X_Sett")
    assert sett["traits"] == ["X_Brawler"]
    assert sett["stats"]["attackSpeed"] == 0.55  # float noise removed
    assert sett["ability"]["values_status"] == "missing"
    assert sett["source_ids"] == ["cdragon-test"] and sett["status"] == "community_extracted"


def test_forms_point_to_their_base_and_are_not_counted_twice():
    recs = run()
    fire = next(c for c in recs["champions"] if c["id"] == "X_Lux_Fire")
    assert fire["variant_of"] == "X_Lux"
    assert summary(recs)["champions_per_cost"] == {"4": 1, "5": 1}


def test_trait_values_resolved_from_description_names_only():
    t = next(t for t in run()["traits"] if t["id"] == "X_Brawler")
    bp = t["breakpoints"][0]
    assert bp["values"]["BrawlerTeamHealth"] == 120
    assert bp["values"]["BrawlerHealthPercent"] == 0.4
    assert t["unresolved_hashes"] == ["{12345678}"]
    assert t["breakpoints"][1]["max_units"] is None  # 25000 means "no upper limit"
    assert t["units"] == ["X_Lux_Fire", "X_Sett"]


def test_items_classified_in_rule_order_and_wisps_split_out():
    recs = run()
    kinds = {i["id"]: i["kind"] for i in recs["items"]}
    assert kinds == {
        "X_Sword": "component",
        "X_Vest": "component",
        "X_Blade": "completed",
        "X_Emblem": "emblem",  # emblem rule comes before the recipe rule
        "X_Junk": "other",
    }
    emblem = next(i for i in recs["items"] if i["id"] == "X_Emblem")
    assert emblem["tags"] == ["TraitItem"]  # known hash replaced by its name
    assert [w["id"] for w in recs["wisps"]] == ["X_Charm", "X_Charm_Up"]
    up = next(w for w in recs["wisps"] if w["id"] == "X_Charm_Up")
    assert up["variant_of"] == "X_Charm"


def test_augments_keep_values_and_unknown_tier():
    augs = {a["id"]: a for a in run()["augments"]}
    assert augs["X_Aug"]["effects"] == {"Gold": 2}
    assert augs["X_Aug_Plus"]["variant_of"] == "X_Aug"
    assert augs["X_Aug"]["tier"]["status"] == "unknown"


def test_output_is_deterministic():
    a = json.dumps(run(), sort_keys=True)
    raw = copy.deepcopy(RAW)
    raw["setData"][0]["champions"].reverse()
    raw["items"].reverse()
    assert json.dumps(run(raw), sort_keys=True) == a


def test_bad_inputs_are_errors():
    raw = copy.deepcopy(RAW)
    raw["setData"][0]["champions"].append(champ("X_New", "New", 1, ["Nope"]))
    with pytest.raises(SchemaError):
        run(raw)
    raw = copy.deepcopy(RAW)
    raw["setData"][0]["items"].append("X_Missing")
    with pytest.raises(SchemaError):
        run(raw)
    with pytest.raises(SchemaError):
        run(rules={**RULES, "mutator": "TFTSetY"})
    with pytest.raises(SchemaError):
        classify_item(item("Q", "q"), [{"kind": "component", "tag": "component"}])
