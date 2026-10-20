"""Hand-made layers applied on top of the generated knowledge base.

Game files give the structure (which items, augments and Wisps exist, recipes,
traits) but not everything: Set 18 item stats are missing from the export,
augment tiers are hashed, and balance numbers can lag the official patch
notes. Three curated files per patch fill these gaps, each record with sources:

    curated/item_stats/<patch>.json     stats and effect text of items
    curated/augment_tiers/<patch>.json  silver / gold / prismatic, by display name
    curated/overrides/<patch>.json      values the official notes changed

An override states the value it replaces (``old``). If the generated data does
not hold that value, loading fails: either the notes were already applied by a
newer export, or the override targets the wrong field. Nothing is replaced
silently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tft_engine.gamedata.schema import STATUSES, SchemaError

TIERS = ("silver", "gold", "prismatic")
STAT_KEYS = (
    "hp",
    "ad_pct",
    "ap",
    "as_pct",
    "armor",
    "mr",
    "crit_pct",
    "mana_regen",
    "omnivamp_pct",
    "damage_amp_pct",
    "damage_reduction_pct",
    "durability_pct",
)


def _read(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _check_record(r: dict[str, Any], where: str) -> None:
    if not r.get("source_ids"):
        raise SchemaError(f"{where}: needs source_ids")
    if r.get("status", "third_party_unverified") not in STATUSES:
        raise SchemaError(f"{where}: bad status {r.get('status')!r}")


def _step(cur: Any, part: str, path: str) -> Any:
    """One path step: a dict key, or a list index written as a number."""
    if isinstance(cur, dict) and part in cur:
        return cur[part]
    if isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
        return cur[int(part)]
    raise KeyError(path)


def _get_path(rec: dict[str, Any], path: str) -> Any:
    cur: Any = rec
    for part in path.split("."):
        cur = _step(cur, part, path)
    return cur


def _set_path(rec: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cur: Any = rec
    for part in parts[:-1]:
        cur = _step(cur, part, path)
    if isinstance(cur, list):
        cur[int(parts[-1])] = value
    else:
        cur[parts[-1]] = value


def apply_curated(
    records: dict[str, dict[str, dict[str, Any]]], folder: Path, patch: str
) -> list[str]:
    """Apply the curated files for this patch in place. Returns notes for the reader."""
    notes: list[str] = []

    doc = _read(folder / "item_stats" / f"{patch}.json")
    if doc:
        for r in doc["records"]:
            where = f"item_stats/{patch} {r.get('id')}"
            _check_record(r, where)
            item = records["items"].get(r["id"])
            if item is None:
                raise SchemaError(f"{where}: no such item in the generated data")
            unknown = set(r.get("stats", {})) - set(STAT_KEYS)
            if unknown:
                raise SchemaError(f"{where}: unknown stat keys {sorted(unknown)}")
            item["stats"] = dict(r.get("stats", {}))
            item["effect_text"] = r.get("effect", "")
            item["stats_status"] = r.get("status", "third_party_unverified")
            item["stats_source_ids"] = list(r["source_ids"])
            item["stats_note"] = r.get("note", "")
            if r.get("older_copy_check"):
                item["stats_check"] = r["older_copy_check"]
            for c in r.get("conflicts", []):
                if not c.get("source_ids"):
                    raise SchemaError(f"{where}: each conflict needs source_ids")
            item["stats_conflicts"] = list(r.get("conflicts", []))
        notes.append(f"item stats for {len(doc['records'])} items from curated/item_stats/{patch}")

    doc = _read(folder / "augment_tiers" / f"{patch}.json")
    if doc:
        by_name: dict[str, list[dict[str, Any]]] = {}
        for a in records["augments"].values():
            by_name.setdefault(a["name"], []).append(a)
        for r in doc["records"]:
            where = f"augment_tiers/{patch} {r.get('name')}"
            _check_record(r, where)
            if r["tier"] not in TIERS:
                raise SchemaError(f"{where}: tier must be one of {TIERS}")
            hits = by_name.get(r["name"])
            if not hits:
                raise SchemaError(f"{where}: no augment with this name in the generated data")
            for a in hits:
                a["tier"] = {
                    "value": r["tier"],
                    "status": r.get("status", "third_party_unverified"),
                    "source_ids": list(r["source_ids"]),
                    "note": r.get("note", "tier matched by display name"),
                }
                a["offered_in_set"] = {
                    "value": True,
                    "status": r.get("status", "third_party_unverified"),
                    "source_ids": list(r["source_ids"]),
                }
        notes.append(
            f"augment tiers for {len(doc['records'])} names from curated/augment_tiers/{patch}"
        )

    doc = _read(folder / "overrides" / f"{patch}.json")
    if doc:
        for r in doc["records"]:
            where = f"overrides/{patch} {r.get('kind')}/{r.get('id')}.{r.get('field')}"
            _check_record(r, where)
            rec = records.get(r["kind"], {}).get(r["id"])
            if rec is None:
                raise SchemaError(f"{where}: no such record")
            try:
                current = _get_path(rec, r["field"])
            except KeyError:
                raise SchemaError(f"{where}: field not found") from None
            if current != r["old"]:
                raise SchemaError(
                    f"{where}: expected old value {r['old']!r}, data has {current!r}; "
                    "the export may already include this change"
                )
            _set_path(rec, r["field"], r["new"])
            rec.setdefault("overrides", []).append(
                {k: r[k] for k in ("field", "old", "new", "source_ids") if k in r}
                | {"note": r.get("note", "")}
            )
        notes.append(f"{len(doc['records'])} values replaced from curated/overrides/{patch}")
    return notes
