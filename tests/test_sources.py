import datetime as dt

import pytest

from tft_engine.gamedata import SchemaError
from tft_engine.gamedata.sources import (
    PatchCalendar,
    PatchInfo,
    Source,
    SourceRegistry,
    load_calendar,
    load_sources,
)


def src(**kw):
    d = {
        "id": "s1",
        "type": "game_file",
        "title": "t",
        "url": "https://example.org",
        "retrieved_at": "2026-10-20",
        "collected_by": "auto",
    }
    d.update(kw)
    return Source.from_dict(d)


CAL = PatchCalendar(
    "x",
    [
        PatchInfo("18.3", dt.date(2026, 9, 22), "released", "n3"),
        PatchInfo("18.4", dt.date(2026, 10, 6), "released", "n4"),
        PatchInfo("18.5", dt.date(2026, 10, 21), "planned", "n5"),
    ],
    {},
)


def test_source_needs_core_fields_and_known_type():
    with pytest.raises(SchemaError):
        src(type="blog")
    with pytest.raises(SchemaError):
        src(collected_by="robot")
    with pytest.raises(SchemaError):
        src(retrieved_at="20/10/2026")
    with pytest.raises(SchemaError):
        src(extra_field=1)


def test_stats_sites_need_patch_and_filters():
    with pytest.raises(SchemaError):
        src(type="stats_site", collected_by="manual")
    s = src(
        type="stats_site", collected_by="manual", site_patch="18.4b", filters={"rank": "master+"}
    )
    assert s.filters["rank"] == "master+"


def test_registry_rejects_duplicates_and_unknown_ids():
    with pytest.raises(SchemaError):
        SourceRegistry([src(), src()])
    reg = SourceRegistry([src()])
    with pytest.raises(SchemaError):
        reg.check_ids(["nope"], "x")
    with pytest.raises(SchemaError):
        reg.check_ids([], "x")


def test_patch_on_uses_released_notes_and_flags_notes_day():
    assert CAL.patch_on(dt.date(2026, 10, 1)) == ("18.3", False)
    assert CAL.patch_on(dt.date(2026, 10, 6)) == ("18.4", True)
    # 18.5 is only planned, so it is never "live"
    assert CAL.patch_on(dt.date(2026, 10, 25)) == ("18.4", False)
    assert CAL.patch_on(dt.date(2026, 1, 1)) == (None, False)


def test_stale_data_guard():
    # taken while 18.3 was live, filed under 18.4: refused
    old = src(retrieved_at="2026-10-01")
    assert CAL.check_assignment(old, "18.4")
    # a source that names its patch is judged by that, b-patches included
    assert CAL.check_assignment(src(site_patch="18.4b"), "18.4") == []
    assert CAL.check_assignment(src(site_patch="18.3"), "18.4")
    assert CAL.check_assignment(src(retrieved_at="2026-10-06"), "18.4")  # ambiguous day
    assert CAL.check_assignment(src(retrieved_at="2026-10-20"), "18.4") == []


def test_calendar_must_be_in_date_order():
    with pytest.raises(SchemaError):
        PatchCalendar(
            "x",
            [
                PatchInfo("18.4", dt.date(2026, 10, 6), "released", "a"),
                PatchInfo("18.3", dt.date(2026, 9, 22), "released", "b"),
            ],
            {},
        )


def test_repo_registry_and_calendar_load_and_link():
    reg = load_sources()
    cal = load_calendar("set18")
    for p in cal.patches:
        assert p.source_id in reg
    assert cal.cdragon["16.20"]["patch"] == "18.4"
