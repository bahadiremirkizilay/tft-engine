import json

import pytest

from tft_engine.gamedata import Param, SchemaError, UnknownMechanicError, load_gamedata
from tft_engine.gamedata.loader import parse_patch

from .conftest import FIXTURE_SETS


def test_param_needs_source():
    with pytest.raises(SchemaError):
        Param("x", 1, "verified", "  ")


def test_param_unknown_status_must_have_null_value():
    with pytest.raises(SchemaError):
        Param("x", 3, "unknown", "src")
    with pytest.raises(SchemaError):
        Param("x", None, "verified", "src")


def test_param_rejects_bad_status():
    with pytest.raises(SchemaError):
        Param("x", 1, "probably", "src")


def test_unknown_value_raises_on_use():
    p = Param("x", None, "unknown", "src")
    with pytest.raises(UnknownMechanicError):
        p.get()


def test_patch_ordering():
    assert parse_patch("18.10") > parse_patch("18.9")
    assert parse_patch("18.6b") > parse_patch("18.6")
    assert parse_patch("19.1") > parse_patch("18.6b")


def test_patch_changes_apply_in_order():
    base = load_gamedata("synthetic", "1.1", root=FIXTURE_SETS)
    p12 = load_gamedata("synthetic", "1.2", root=FIXTURE_SETS)
    assert base.get("reroll_cost") == 2
    assert p12.get("reroll_cost") == 3
    with pytest.raises(UnknownMechanicError):
        base.get("mystery")
    assert p12.get("mystery") == 7
    assert [c.param for c in p12.changes_in("1.2")] == ["params.reroll_cost", "params.mystery"]
    assert p12.changes_in("1.2")[0].kind == "nerf"


def test_later_patch_keeps_earlier_changes_and_flags_unreviewed():
    p13 = load_gamedata("synthetic", "1.3", root=FIXTURE_SETS)
    assert p13.get("reroll_cost") == 3
    assert p13.unreviewed_patches == ["1.3"]


def test_missing_patch_file_is_an_error():
    with pytest.raises(SchemaError, match="no data file"):
        load_gamedata("synthetic", "1.9", root=FIXTURE_SETS)


def test_patch_before_set_start_is_an_error():
    with pytest.raises(SchemaError):
        load_gamedata("synthetic", "0.9", root=FIXTURE_SETS)


def test_change_without_source_rejected(tmp_path):
    set_dir = tmp_path / "s"
    (set_dir / "patches").mkdir(parents=True)
    base = json.loads((FIXTURE_SETS / "synthetic" / "base.json").read_text(encoding="utf-8"))
    base["set"] = "s"
    (set_dir / "base.json").write_text(json.dumps(base), encoding="utf-8")
    bad = {
        "patch": "1.2",
        "status": "reviewed",
        "changes": [
            {
                "param": "params.reroll_cost",
                "kind": "nerf",
                "new": {"value": 3, "status": "synthetic", "source": "x"},
            }
        ],
    }
    (set_dir / "patches" / "1.2.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(SchemaError, match="missing source"):
        load_gamedata("s", "1.2", root=tmp_path)


def test_set18_loads_and_reports_provenance(set18):
    report = set18.provenance_report()
    # only what the owner saw in game on 18.4b is verified; this must stay honest
    assert sorted(report["verified"]) == ["passive_xp_per_round", "reroll_cost", "xp_purchase"]
    assert "shop_odds" in report["community_extracted"]  # read from the game files
    assert "copies_per_champion" in report["community_extracted"]
    assert "riftbeast_shop" in report["unknown"]
    assert "xp_to_next_level" in report["third_party_unverified"]
    assert set18.unreviewed_patches == []


def test_set18_xp_table_follows_the_official_patch_history():
    xp = {p: load_gamedata("set18", p).get("xp_to_next_level") for p in ("18.1", "18.2", "18.2b")}
    assert [xp["18.1"][k] for k in "789"] == [60, 68, 68]
    assert [xp["18.2"][k] for k in "789"] == [56, 64, 64]
    assert [xp["18.2b"][k] for k in "789"] == [56, 68, 68]
    assert load_gamedata("set18", "18.4").get("xp_to_next_level") == xp["18.2b"]


def test_set18_level7_odds_follow_the_in_game_tooltip_and_keep_the_game_file_as_conflict(set18):
    p = set18.param("shop_odds")
    assert p.value["7"] == [16, 30, 43, 10, 1]
    assert "owner-ingame-2026-10-20" in p.source_ids
    assert p.conflicts[0]["value"]["7"] == [19, 30, 40, 10, 1]
    assert "riot-notes-17.1" in p.conflicts[0]["source_ids"]


def test_superseded_value_is_caught(tmp_path):
    import json

    from tft_engine.gamedata.entities import superseded_values

    d = tmp_path / "s" / "patches"
    d.mkdir(parents=True)
    base = {
        "set": "s",
        "valid_from_patch": "1.1",
        "params": {"xp": {"value": {"7": 60}, "status": "synthetic", "source": "t"}},
    }
    (tmp_path / "s" / "base.json").write_text(json.dumps(base))
    change = {
        "param": "params.xp",
        "kind": "adjustment",
        "source": "t",
        "old": {"7": 60},
        "new": {"value": {"7": 56}, "status": "synthetic", "source": "t"},
    }
    (d / "1.2.json").write_text(
        json.dumps({"patch": "1.2", "status": "reviewed", "changes": [change]})
    )
    assert superseded_values(load_gamedata("s", "1.2", root=tmp_path)) == []
    # a later file copies the outdated table: caught
    stale = dict(
        change, old={"9": 1}, new={"value": {"7": 60}, "status": "synthetic", "source": "t"}
    )
    (d / "1.3.json").write_text(
        json.dumps({"patch": "1.3", "status": "reviewed", "changes": [stale]})
    )
    assert superseded_values(load_gamedata("s", "1.3", root=tmp_path))


def test_param_conflicts_need_sources():
    from tft_engine.gamedata import Param

    with pytest.raises(SchemaError):
        Param.from_dict(
            "x", {"value": 1, "status": "synthetic", "source": "t", "conflicts": [{"value": 2}]}
        )
    p = Param.from_dict(
        "x",
        {
            "value": 1,
            "status": "synthetic",
            "source": "t",
            "source_ids": ["a"],
            "conflicts": [{"value": 2, "source_ids": ["b"]}],
        },
    )
    assert Param.from_dict("x", p.to_dict()) == p


def test_set18_odds_rows_sum_to_100(set18):
    for level, row in set18.get("shop_odds").items():
        assert sum(row) == 100, level
