import copy
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from tft_engine.gamedata import SchemaError
from tft_engine.gamedata.cdragon import KINDS, normalize
from tft_engine.gamedata.entities import (
    check_all,
    check_knowledge,
    diff_knowledge,
    load_knowledge,
)
from tft_engine.gamedata.sources import PatchCalendar, PatchInfo, Source, SourceRegistry
from tft_engine.gamedata.sources import load_calendar as _load_calendar

from .test_cdragon import RAW, RULES

ROOT = Path(__file__).resolve().parents[1]


def write_generated(root: Path, patch: str, raw=RAW) -> Path:
    recs = normalize(copy.deepcopy(raw), RULES, "setx", patch, "cdragon-test")
    out = root / "setx" / "generated" / patch
    out.mkdir(parents=True)
    for kind in KINDS:
        doc = {
            "set": "setx",
            "patch": patch,
            "kind": kind,
            "source_id": "cdragon-test",
            "patch_mapping": {"patch": patch, "status": "verified"},
            "records": recs[kind],
        }
        (out / f"{kind}.json").write_text(json.dumps(doc), encoding="utf-8")
    return root


REG = SourceRegistry(
    [
        Source.from_dict(
            {
                "id": "cdragon-test",
                "type": "game_file",
                "title": "t",
                "url": "https://example.org",
                "retrieved_at": "2026-10-20",
                "collected_by": "auto",
            }
        )
    ]
)
CAL = PatchCalendar("setx", [PatchInfo("1.1", dt.date(2026, 10, 1), "released", "x")], {})


def test_consistent_data_passes(tmp_path):
    kb = load_knowledge("setx", "1.1", write_generated(tmp_path, "1.1"))
    rep = check_knowledge(kb, REG, CAL)
    assert rep.ok, rep.errors
    assert kb.champion_by_name("sett")["cost"] == 4
    assert set(kb.champions) == {"X_Lux", "X_Lux_Fire", "X_Sett"}


def test_broken_links_are_errors(tmp_path):
    kb = load_knowledge("setx", "1.1", write_generated(tmp_path, "1.1"))
    kb.champions["X_Sett"]["traits"].append("X_Ghost")
    kb.items["X_Blade"]["recipe"] = ["X_Sword", "X_Junk"]
    kb.items["X_Vest"]["source_ids"] = ["nobody"]
    kb.traits["X_Brawler"]["units"].append("X_Lux")
    rep = check_knowledge(kb, REG, CAL)
    text = "\n".join(rep.errors)
    assert "unknown trait X_Ghost" in text
    assert "not a component" in text
    assert "unknown source 'nobody'" in text
    assert "lists X_Lux" in text


def test_stale_source_is_reported(tmp_path):
    kb = load_knowledge("setx", "1.1", write_generated(tmp_path, "1.1"))
    later = PatchCalendar(
        "setx",
        [
            PatchInfo("1.1", dt.date(2026, 9, 1), "released", "x"),
            PatchInfo("1.2", dt.date(2026, 10, 10), "released", "y"),
        ],
        {},
    )
    rep = check_knowledge(kb, REG, later)
    assert any("while 1.2 was live" in w for w in rep.warnings)


def test_header_must_match_requested_patch(tmp_path):
    write_generated(tmp_path, "1.1")
    (tmp_path / "setx" / "generated" / "1.1").rename(tmp_path / "setx" / "generated" / "1.2")
    with pytest.raises(SchemaError):
        load_knowledge("setx", "1.2", tmp_path)
    with pytest.raises(SchemaError):
        load_knowledge("setx", "9.9", tmp_path)


def test_diff_lists_added_removed_and_changed(tmp_path):
    raw2 = copy.deepcopy(RAW)
    block = raw2["setData"][0]
    block["champions"] = [c for c in block["champions"] if c["apiName"] != "X_Lux_Fire"]
    block["champions"][0]["cost"] = 3  # X_Sett
    write_generated(tmp_path, "1.1")
    write_generated(tmp_path, "1.2", raw2)
    d = diff_knowledge(
        load_knowledge("setx", "1.1", tmp_path), load_knowledge("setx", "1.2", tmp_path)
    )
    assert d["champions"]["removed"] == ["X_Lux_Fire"]
    assert d["champions"]["changed"]["X_Sett"]["cost"] == (4, 3)
    assert d["traits"]["changed"]["X_Brawler"]["units"] == (["X_Lux_Fire", "X_Sett"], ["X_Sett"])
    assert d["items"] == {"added": [], "removed": [], "changed": {}}


def test_set18_patch_18_4_knowledge_base_is_consistent():
    kb, rep = check_all("set18", "18.4")
    assert rep.ok, rep.errors
    base = [c for c in kb.champions.values() if not c["variant_of"]]
    assert len(base) == 65
    assert kb.champion_by_name("Sett")["traits"] == ["DA_18_Blossom", "DA_18_Brawler"]
    comps = [i for i in kb.items.values() if i["kind"] == "component" and i["family"] == "DA"]
    assert len(comps) == 10
    brawler = kb.traits["DA_18_Brawler"]["breakpoints"]
    assert [b["min_units"] for b in brawler] == [2, 4, 6]
    assert brawler[0]["values"]["BrawlerHealthPercent"] == 0.25


# --- tools/import_cdragon.py end to end, on the made-up export --------------------

spec = importlib.util.spec_from_file_location(
    "import_cdragon", ROOT / "tools" / "import_cdragon.py"
)
import_cdragon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(import_cdragon)


def make_data_root(tmp_path: Path, raw_bytes: bytes, registered_sha: str) -> tuple[Path, Path]:
    data, raw = tmp_path / "data", tmp_path / "raw"
    (raw / "9.1").mkdir(parents=True)
    (raw / "9.1" / "en_us.json").write_bytes(raw_bytes)
    (data / "sets" / "setx" / "curated").mkdir(parents=True)
    (data / "sets" / "setx" / "curated" / "cdragon_rules.json").write_text(json.dumps(RULES))
    (data / "sets" / "setx" / "calendar.json").write_text(
        json.dumps(
            {
                "set": "setx",
                "patches": [
                    {
                        "patch": "1.1",
                        "notes_published": "2026-10-01",
                        "status": "released",
                        "source_id": "cdragon-9.1",
                    }
                ],
                "cdragon_versions": {"9.1": {"patch": "1.1", "status": "verified"}},
            }
        )
    )
    source = {
        "id": "cdragon-9.1",
        "type": "game_file",
        "title": "t",
        "url": "https://example.org",
        "retrieved_at": "2026-10-20",
        "collected_by": "auto",
        "sha256": {"en_us.json": registered_sha},
    }
    (data / "sources.json").write_text(json.dumps({"sources": [source]}))
    return data, raw


def test_importer_writes_loadable_files_and_is_repeatable(tmp_path):
    raw_bytes = json.dumps(RAW).encode()
    data, raw = make_data_root(tmp_path, raw_bytes, hashlib.sha256(raw_bytes).hexdigest())
    info = import_cdragon.run("setx", "9.1", data, raw)
    assert info["summary"]["champions_per_cost"] == {"4": 1, "5": 1}
    out = data / "sets" / "setx" / "generated" / "1.1"
    first = {p.name: p.read_bytes() for p in out.iterdir()}
    import_cdragon.run("setx", "9.1", data, raw)
    assert {p.name: p.read_bytes() for p in out.iterdir()} == first  # byte-identical
    kb = load_knowledge("setx", "1.1", data / "sets")
    assert check_knowledge(kb, None, _load_calendar("setx", data / "sets")).ok


def test_importer_refuses_a_file_that_changed(tmp_path):
    data, raw = make_data_root(tmp_path, json.dumps(RAW).encode(), "0" * 64)
    with pytest.raises(SystemExit):
        import_cdragon.run("setx", "9.1", data, raw)
