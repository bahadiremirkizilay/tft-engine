"""Hand-made layers applied on top of the generated knowledge base.

Game files give the structure (which items, augments and Wisps exist, recipes,
traits) but not everything: Set 18 item stats are missing from the export,
augment tiers are hashed, and balance numbers can lag the official patch
notes. Three curated files per patch fill these gaps, each record with sources:

    curated/item_stats/<patch>.json     stats and effect text of items
    curated/augment_tiers/<patch>.json  silver / gold / prismatic, by display name
    curated/overrides/<patch>.json      values the official notes changed

One set-level file describes how augments change the rules (B3); it holds no
numbers of its own, only references to augment effect values:

    curated/effects/augments.json       augment models (modifiers and events)
    curated/champion_roles.json         champion roles (Tank, Fighter, ...), missing in the export

Ability values per patch (none in the Set 18 export):

    curated/abilities/<patch>.json      damage, shields and heals per star, by champion
    curated/item_effects/<patch>.json   item special effects as countable values

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
MODEL_CATEGORIES = ("economy", "xp", "shop", "other")
MODEL_STATUSES = ("modelled", "partial", "text_only")
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

    doc = _read(folder / "champion_roles.json")
    if doc:
        for r in doc["records"]:
            where = f"champion_roles {r.get('id')}"
            _check_record(r, where)
            champ = records.get("champions", {}).get(r["id"])
            if champ is None:
                raise SchemaError(f"{where}: no such champion")
            for c in records["champions"].values():
                if c["id"] == r["id"] or c.get("variant_of") == r["id"]:
                    c["role"] = r["role"]
                    c["role_source_ids"] = list(r["source_ids"])
        if doc["records"]:
            notes.append(f"roles for {len(doc['records'])} champions from curated/champion_roles")
    return notes


def read_augment_models(curated_folder: Path) -> dict[str, dict[str, Any]]:
    """Augment models by augment id (empty when the set has none). Structure only.

    Effect references are checked against the augment records by
    ``check_augment_models``; building them into modifiers is done by
    ``tft_engine.rules.modifiers.build``.
    """
    doc = _read(curated_folder / "effects" / "augments.json")
    if not doc:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for r in doc["records"]:
        where = f"effects/augments.json {r.get('id')}"
        if r.get("id") in out:
            raise SchemaError(f"{where}: duplicate id")
        if r.get("category") not in MODEL_CATEGORIES:
            raise SchemaError(f"{where}: category must be one of {MODEL_CATEGORIES}")
        if r.get("model_status") not in MODEL_STATUSES:
            raise SchemaError(f"{where}: model_status must be one of {MODEL_STATUSES}")
        if not r.get("source_ids"):
            raise SchemaError(f"{where}: needs source_ids")
        parts = r.get("modifiers", []) + r.get("events", [])
        if r["model_status"] == "text_only" and parts:
            raise SchemaError(f"{where}: a text_only model has no modifiers or events")
        if r["model_status"] != "modelled" and not r.get("note"):
            raise SchemaError(f"{where}: a {r['model_status']} model must say what is missing")
        out[r["id"]] = r
    return out


ABILITY_PART_KINDS = ("damage", "shield", "heal", "health", "attack_bonus", "attack_speed")
DAMAGE_TYPES = ("magic", "physical", "true")
ABILITY_HITS = ("single", "aoe", "line", "split")
ABILITY_PER = ("cast", "second", "attack", "fight")
ABILITY_TERM_STATS = ("hp", "armor", "mr", "ap")
ABILITY_RATIOS = ("ap", "ad", "as")
ABILITY_STAT_KEYS = ("hp", "armor", "magicResist", "damage", "attackSpeed", "range")


def _check_part(p: dict[str, Any], where: str) -> None:
    kind = p.get("kind")
    if kind not in ABILITY_PART_KINDS:
        raise SchemaError(f"{where}: part kind must be one of {ABILITY_PART_KINDS}")
    if kind in ("attack_bonus", "attack_speed"):
        if not isinstance(p.get("value"), int | float):
            raise SchemaError(f"{where}: {kind} needs a number value")
        return
    vals = p.get("values")
    if not (isinstance(vals, list) and len(vals) == 3):
        raise SchemaError(f"{where}: values must list 1/2/3-star numbers")
    if kind == "damage" and p.get("type") not in DAMAGE_TYPES:
        raise SchemaError(f"{where}: damage type must be one of {DAMAGE_TYPES}")
    hits = p.get("hits", "single")
    if hits not in ABILITY_HITS and not (isinstance(hits, int) and hits > 0):
        raise SchemaError(f"{where}: hits must be one of {ABILITY_HITS} or a count")
    if p.get("per", "cast") not in ABILITY_PER:
        raise SchemaError(f"{where}: per must be one of {ABILITY_PER}")
    for term in p.get("terms", []):
        if term.get("stat") not in ABILITY_TERM_STATS or len(term.get("values", [])) != 3:
            raise SchemaError(f"{where}: a term needs a stat in {ABILITY_TERM_STATS} and 3 values")
    for r in p.get("scales", []):
        if r not in ABILITY_RATIOS:
            raise SchemaError(f"{where}: scales must be among {ABILITY_RATIOS}")
    tpb = p.get("times_per_bonus_as")
    if tpb is not None and not (isinstance(tpb, int | float) and tpb > 0):
        raise SchemaError(f"{where}: times_per_bonus_as is a positive share of Attack Speed")
    over = p.get("over")
    if over is not None and not (isinstance(over, int | float) and over > 0):
        raise SchemaError(f"{where}: over is the seconds a damage-over-time part takes")
    chance = p.get("chance")
    if chance is not None and not isinstance(chance, int | float | str):
        raise SchemaError(f"{where}: chance is a number or an assumption name")


def read_abilities(curated_folder: Path, patch: str) -> dict[str, dict[str, Any]]:
    """Ability records of one patch by champion id (empty when the patch has none).

    Only files of kind ``abilities`` are read: the older 18.4 file holds pasted
    notes in another layout and is kept as a record, not as engine input.
    """
    doc = _read(curated_folder / "abilities" / f"{patch}.json")
    if not doc or doc.get("kind") != "abilities":
        return {}
    if doc.get("patch") != patch:
        raise SchemaError(f"abilities/{patch}.json is filed under patch {doc.get('patch')}")
    out: dict[str, dict[str, Any]] = {}
    for r in doc["records"]:
        where = f"abilities/{patch}.json {r.get('id')}"
        _check_record(r, where)
        if r["id"] in out:
            raise SchemaError(f"{where}: duplicate id")
        if r.get("model_status") not in ("modelled", "partial"):
            raise SchemaError(f"{where}: model_status must be modelled or partial")
        if r["model_status"] == "partial" and not r.get("note"):
            raise SchemaError(f"{where}: a partial record must say what is not counted")
        forms = r.get("forms") or {"": r}
        if "parts" not in r and not r.get("forms"):
            raise SchemaError(f"{where}: needs parts or forms")
        for name, form in forms.items():
            if name not in ("", "ap", "ad"):
                raise SchemaError(f"{where}: forms are ap and ad")
            for i, p in enumerate(form.get("parts", [])):
                _check_part(p, f"{where} {name} part {i}")
            for k in form.get("stats", {}):
                if k not in ABILITY_STAT_KEYS:
                    raise SchemaError(f"{where}: form stat {k!r} is not one of {ABILITY_STAT_KEYS}")
        out[r["id"]] = r
    return out


ITEM_EFFECT_KINDS = (
    "stat", "stack", "shield", "heal_once", "regen", "mana", "precision", "reduce", "burn",
    "damage_when_hit", "heal_damage", "crit_stack",
)  # fmt: skip
ITEM_STACK_PER = ("second", "attack", "attack_or_hit", "interval")


def read_item_effects(curated_folder: Path, patch: str) -> dict[str, dict[str, Any]]:
    """Item special effects of one patch by item id (empty when the patch has none)."""
    doc = _read(curated_folder / "item_effects" / f"{patch}.json")
    if not doc:
        return {}
    if doc.get("kind") != "item_effects" or doc.get("patch") != patch:
        raise SchemaError(f"item_effects/{patch}.json: wrong kind or patch in the header")
    out: dict[str, dict[str, Any]] = {}
    for r in doc["records"]:
        where = f"item_effects/{patch}.json {r.get('id')}"
        _check_record(r, where)
        if r["id"] in out:
            raise SchemaError(f"{where}: duplicate id")
        if r.get("model_status") not in MODEL_STATUSES:
            raise SchemaError(f"{where}: model_status must be one of {MODEL_STATUSES}")
        if r["model_status"] != "modelled" and not r.get("note"):
            raise SchemaError(f"{where}: a {r['model_status']} record must say what is missing")
        for e in r["effects"]:
            if e.get("kind") not in ITEM_EFFECT_KINDS:
                raise SchemaError(f"{where}: effect kind must be one of {ITEM_EFFECT_KINDS}")
            if e["kind"] == "stack" and e.get("per") not in ITEM_STACK_PER:
                raise SchemaError(f"{where}: stack per must be one of {ITEM_STACK_PER}")
            if e["kind"] == "reduce" and e.get("what") not in ("armor", "mr"):
                raise SchemaError(f"{where}: reduce what must be armor or mr")
        out[r["id"]] = r
    return out


def effect_refs(model: dict[str, Any]) -> list[str]:
    """Names of the augment effect values a model refers to."""
    refs: list[str] = []

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            if "effect" in v:
                refs.append(v["effect"])
            else:
                for x in v.values():
                    walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(model.get("modifiers", []))
    walk(model.get("events", []))
    return refs
